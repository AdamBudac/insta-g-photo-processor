"""Self-contained source/frozen smoke checks that never open personal data."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

import imagecodecs
import numpy as np
import PIL
import pillow_heif
import PySide6
from PIL import Image, ImageCms, ImageDraw, JpegImagePlugin
from PySide6.QtCore import (
    QCoreApplication,
    QEvent,
    QEventLoop,
    QPointF,
    Qt,
    QThread,
    qVersion,
)
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from insta_g import __version__
from insta_g.core.export import export_records
from insta_g.core.geometry import get_geometry
from insta_g.core.hdr import HdrInfo, HdrTile, detect_hdr, encode_hdr_tile, load_hdr
from insta_g.core.imaging import SRGB_PROFILE, generate_tiles, load_image, render_composite
from insta_g.core.models import ImageRecord, Settings
from insta_g.gui.preferences_dialog import HelpDialog
from insta_g.gui.window import MainWindow
from insta_g.persistence import Session, SessionStore
from insta_g.preferences import PreferencesStore


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _pump_until(app: QApplication, predicate: Callable[[], bool], seconds: float = 20) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 30)
        if predicate():
            return
        QThread.msleep(5)
    raise TimeoutError("Qt operácia nebola dokončená v časovom limite.")


def _write_report(path: Path, report: dict[str, Any]) -> None:
    temporary: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", prefix=".smoke-", suffix=".tmp",
            dir=path.parent, delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def run_smoke(report_path: Path, app: QApplication, hdr_directory: Path | None = None) -> int:
    """Check real codecs, export, temporary state and the actual three-pane GUI.

    This entry point must run before normal session discovery. All photographs,
    session files and JPEG outputs live in one disposable temporary directory.
    Only the explicitly requested JSON report and its sibling PNG survive.
    """
    report_path = Path(report_path).resolve()
    external_hdr = [] if hdr_directory is None else sorted(
        path for path in Path(hdr_directory).iterdir()
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".heic", ".heif"}
    )
    report: dict[str, Any] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "frozen": bool(getattr(sys, "frozen", False)),
        "platform": platform.platform(),
        "versions": {
            "application": __version__,
            "python": platform.python_version(),
            "pyside6": PySide6.__version__,
            "qt": qVersion(),
            "pillow": PIL.__version__,
            "pillow_heif": pillow_heif.__version__,
            "imagecodecs": imagecodecs.__version__,
            "numpy": np.__version__,
            "ultrahdr": imagecodecs.ultrahdr_version(),
        },
        "checks": {},
        "errors": [],
    }

    def check(name: str, operation: Callable[[], Any]) -> None:
        started = time.monotonic()
        try:
            details = operation()
            report["checks"][name] = {
                "ok": True, "seconds": round(time.monotonic() - started, 3),
                "details": details,
            }
        except Exception as exc:
            message = f"{name}: {type(exc).__name__}: {exc}"
            report["checks"][name] = {
                "ok": False, "seconds": round(time.monotonic() - started, 3),
                "error": message,
            }
            report["errors"].append(message)

    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="insta-g-smoke-") as directory:
            root = Path(directory)
            jpeg_path, png_path, heic_path = (
                root / "smoke-orientation.jpg", root / "smoke-alpha.png", root / "smoke-heic.heic"
            )
            output = root / "export"
            records = [
                ImageRecord(str(jpeg_path), Settings(mode="expand", ratio_mode="fixed", ratio=3 / 4)),
                ImageRecord(str(png_path), Settings(mode="expand", ratio_mode="fixed")),
                ImageRecord(str(heic_path), Settings(splits=3)),
            ]

            def jpeg_codec() -> dict[str, Any]:
                with Image.new("RGB", (640, 320), "#39749c") as image:
                    draw = ImageDraw.Draw(image)
                    draw.rectangle((0, 0, 40, 319), fill="#f04155")
                    exif = Image.Exif()
                    exif[274] = 6
                    exif[315] = "Disposable smoke fixture"
                    image.save(jpeg_path, "JPEG", quality=99, exif=exif, icc_profile=SRGB_PROFILE)
                with load_image(jpeg_path, max_edge=512) as decoded:
                    _require(decoded.size == (256, 512), "JPEG orientácia alebo zmenšenie náhľadu nesedí.")
                    _require(decoded.info["source_size"] == (320, 640), "Chýbajú pôvodné orientované rozmery JPEG.")
                    _require(decoded.mode == "RGB" and not decoded.getexif(), "JPEG nie je RGB bez EXIF.")
                    return {"preview_size": decoded.size, "source_size": decoded.info["source_size"]}

            def png_codec() -> dict[str, Any]:
                with Image.new("RGBA", (120, 360), (255, 0, 0, 0)) as image:
                    ImageDraw.Draw(image).rectangle((30, 30, 90, 330), fill=(0, 0, 255, 128))
                    image.save(png_path, "PNG")
                with load_image(png_path) as decoded:
                    _require(decoded.mode == "RGB", "PNG sa nepreviedlo na RGB.")
                    _require(decoded.getpixel((0, 0)) == (255, 255, 255), "Priehľadnosť PNG sa nedoplnila bielou.")
                    _require(decoded.getpixel((60, 60)) == (127, 127, 255), "Polopriehľadnosť PNG nesedí.")
                    return {"source_size": decoded.size, "alpha_matte": "white"}

            def heic_codec() -> dict[str, Any]:
                with Image.new("RGB", (960, 320), "#69bca2") as image:
                    ImageDraw.Draw(image).rectangle((750, 20, 939, 299), fill="#ebad53")
                    pillow_heif.from_pillow(image).save(heic_path, quality=90)
                _require(b"ftyp" in heic_path.read_bytes()[:32], "Fixture nie je skutočný HEIC kontajner.")
                with Image.open(heic_path) as encoded:
                    _require(encoded.format == "HEIF", "HEIC kodek nebol zaregistrovaný.")
                with load_image(heic_path) as decoded:
                    _require(decoded.size == (960, 320) and decoded.mode == "RGB", "Dekódovanie HEIC zlyhalo.")
                    return {"source_size": decoded.size, "bytes": heic_path.stat().st_size}

            def geometry_and_preview() -> dict[str, Any]:
                settings = Settings(splits=3, ratio_mode="fixed", ratio=4 / 3, blur=40, fit_mode="fit")
                with load_image(heic_path) as image:
                    geometry = get_geometry(image.size, settings)
                    with render_composite(image, settings, max_edge=512) as preview:
                        _require(max(preview.size) <= 512, "Náhľad prekročil maximálnu hranu.")
                        preview_size = preview.size
                    with render_composite(image, settings) as composite:
                        tiles = generate_tiles(image, settings)
                        try:
                            _require(len(tiles) == 3, "Nesprávny počet dielov.")
                            with Image.new("RGB", composite.size) as joined:
                                for index, tile in enumerate(tiles):
                                    _require(tile.size == (geometry.tile_width, geometry.tile_height), "Diely nemajú rovnaké rozmery.")
                                    joined.paste(tile, (index * geometry.tile_width, 0))
                                _require(joined.tobytes() == composite.tobytes(), "Diely na seba nenadväzujú.")
                        finally:
                            for tile in tiles:
                                tile.close()
                    left, top, right, bottom = geometry.foreground_box
                    _require(0 <= left < right <= geometry.canvas_size[0], "Zdroj presahuje šírku plátna.")
                    _require(0 <= top < bottom <= geometry.canvas_size[1], "Zdroj presahuje výšku plátna.")
                    _require((right - left, bottom - top) == image.size, "Fit zmenil pôvodnú mierku fotografie.")
                    with render_composite(image, settings) as native_fit:
                        with native_fit.crop(geometry.foreground_box) as foreground:
                            _require(foreground.tobytes() == image.tobytes(), "Fit prepočítal pixely originálu.")
                    fill_settings = Settings(splits=3, ratio_mode="fixed", ratio=3 / 4, fit_mode="fill", offset_x=1)
                    with render_composite(image, fill_settings) as fill:
                        _require(fill.size == (720, 320), "Fill nepoužil natívny výrez.")
                        with image.crop((240, 0, 960, 320)) as expected:
                            _require(fill.tobytes() == expected.tobytes(), "Posun Fill sa nezhoduje s originálnym výrezom.")
                return {"canvas_size": geometry.canvas_size, "preview_size": preview_size, "tiles": 3}

            def export_jpeg() -> dict[str, Any]:
                exported = export_records(records, output)
                _require(not exported.errors and not exported.cancelled, f"Dávkový export zlyhal: {exported.errors}")
                _require(len(exported.paths) == 5, "Dávkový export nevytvoril päť JPEG dielov.")
                reference_data = BytesIO()
                with Image.new("RGB", (16, 16)) as reference:
                    reference.save(reference_data, "JPEG", quality=99, subsampling=0)
                reference_data.seek(0)
                with Image.open(reference_data) as reference:
                    expected_quantization = reference.quantization
                hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in exported.paths}
                for path in exported.paths:
                    with Image.open(path) as image:
                        image.load()
                        _require(image.format == "JPEG" and image.mode == "RGB", "Export nie je RGB JPEG.")
                        _require(not image.getexif(), "Export obsahuje EXIF metadáta.")
                        _require(JpegImagePlugin.get_sampling(image) == 0, "JPEG nepoužíva 4:4:4 subsampling.")
                        _require(image.quantization == expected_quantization, "JPEG nemá kvantizáciu kvality 99.")
                        profile = ImageCms.ImageCmsProfile(BytesIO(image.info.get("icc_profile", b"")))
                        _require("srgb" in ImageCms.getProfileName(profile).lower(), "Export nemá sRGB profil.")
                repeated = export_records(records, output)
                _require(not repeated.errors and len(repeated.paths) == 5, "Opakovaný export zlyhal.")
                _require(not set(exported.paths) & set(repeated.paths), "Export prepísal existujúce názvy.")
                _require(all(hashlib.sha256(path.read_bytes()).hexdigest() == digest for path, digest in hashes.items()), "Opakovaný export zmenil existujúce súbory.")
                _require(not list(output.glob(".insta-g-*.tmp")), "Po exporte zostali dočasné súbory.")
                return {"jpeg_count": len(exported.paths), "collision_count": len(repeated.paths), "quality": 99, "sampling": "4:4:4"}

            def persistence() -> dict[str, Any]:
                store = SessionStore(root / "state" / "session.json")
                session = Session(records, str(heic_path), str(output))
                store.save(session)
                restored = store.load()
                _require([record.to_dict() for record in restored.records] == [record.to_dict() for record in records], "Obnovený stav sa nezhoduje.")
                _require(restored.selected_path == str(heic_path) and restored.export_dir == str(output), "Výber alebo cieľ exportu sa neobnovil.")
                _require(not list(store.path.parent.glob("*.tmp")), "Po uložení stavu zostali dočasné súbory.")
                return {"records": len(restored.records), "atomic_temporary_cleanup": True}

            def gui() -> dict[str, Any]:
                previous_quit = app.quitOnLastWindowClosed()
                app.setQuitOnLastWindowClosed(False)
                window: MainWindow | None = None
                try:
                    window = MainWindow(SessionStore(root / "gui" / "session.json"), Session())
                    window.showMaximized()
                    window.import_paths([str(jpeg_path), str(png_path), str(heic_path)])
                    _pump_until(
                        app,
                        lambda: len(window.session.records) == 3 and not window._jobs and window._writer.is_idle,
                    )
                    _require(window.image_list.currentItem() is None and window.preview._pixmap is None, "Import automaticky otvoril fotografiu.")
                    _require(all(record.status == "imported" for record in window.session.records), "Nové fotografie nie sú v modrom stave Importované.")
                    window.image_list.item(0).setCheckState(Qt.CheckState.Checked)
                    _require(not window.export_button.isEnabled() and not window.export_checked_button.isEnabled(), "Importované fotografie povolili export.")
                    blocked_output = root / "blocked-imported-export"
                    window.start_export(str(blocked_output))
                    window.start_export(str(blocked_output), checked_only=True)
                    _require(window._export_job is None and not blocked_output.exists(), "Importované fotografie sa začali exportovať.")
                    window.image_list.setCurrentRow(0)
                    _pump_until(app, lambda: not window._jobs and window._writer.is_idle and not window._preview_timer.isActive()
                                and window.preview._pixmap is not None)
                    _require([record.previewed for record in window.session.records] == [True, False, False], "Náhľad označil aj nezobrazené fotografie.")
                    _require(window.session.records[0].status == "staging", "Úspešný náhľad nenastavil žltý stav.")
                    _require(not window._import_errors and not window._last_save_error, "GUI import alebo autosave zlyhal.")
                    _require(window.splitter.count() == 3, "Hlavné okno nemá tri panely.")
                    _require(window.isMaximized(), "Hlavné okno nie je maximalizované.")
                    _require(window.settings.split_button.isChecked(), "Chýba tlačidlo režimu Split.")
                    window.image_list.item(0).setCheckState(Qt.CheckState.Checked)
                    window.image_list.item(1).setCheckState(Qt.CheckState.Checked)
                    _require(window.session.records[0].checked, "Checkbox fotografie neaktualizoval stav.")
                    (root / "gui-checked-export").mkdir()
                    window.start_export(str(root / "gui-checked-export"), checked_only=True)
                    _pump_until(app, lambda: window._export_job is None and not window._jobs and window._writer.is_idle)
                    _require([record.is_exported for record in window.session.records] == [True, False, False], "Export vybraných spracoval aj neoznačené fotografie.")
                    _require(window._summary_dialog is not None, "Chýba súhrn exportu.")
                    window._summary_dialog.accept()
                    skipped_output = root / "gui-export-skipped-imports"
                    skipped_output.mkdir()
                    window.start_export(str(skipped_output))
                    _pump_until(app, lambda: window._export_job is None and not window._jobs and window._writer.is_idle)
                    _require([record.status for record in window.session.records] == ["exported", "imported", "imported"], "Export všetkých zmenil neotvorené fotografie.")
                    _require(len(list(skipped_output.glob("*.jpg"))) == 3, "Export všetkých nepreskočil importované fotografie.")
                    window._summary_dialog.accept()
                    for row in (1, 2):
                        window.image_list.setCurrentRow(row)
                        _pump_until(app, lambda: window.session.records[row].previewed
                                    and not window._jobs and window._writer.is_idle and not window._preview_timer.isActive())
                    (root / "gui-export").mkdir()
                    window.start_export(str(root / "gui-export"))
                    _pump_until(app, lambda: window._export_job is None and not window._jobs and window._writer.is_idle)
                    _require(all(record.is_exported for record in window.session.records), "Úspešný export neoznačil všetky fotografie zeleným stavom.")
                    _require(all(record.is_exported for record in window.store.load().records), "Exportný stav sa neuložil do JSON.")
                    window._summary_dialog.accept()
                    current = window._record()
                    window._settings_changed(replace(current.settings, grid="golden"))
                    _require(current.is_exported, "Mriežka zneplatnila úspešný export.")
                    window.preview.set_zoom(1000)
                    _pump_until(app, lambda: window.preview.zoom_percent == 1000 and not window._jobs and window._writer.is_idle)
                    window.preview.reset_view()
                    broken = root / "broken.png"
                    broken.write_bytes(b"diagnostic broken image")
                    window.import_paths([str(broken)])
                    _pump_until(app, lambda: not window._jobs and window._writer.is_idle and not window._pending_paths)
                    _require(window.session.records[-1].status == "failed", "Chybný import nemá červený stav.")
                    _require(bool(window.image_list.item(3).toolTip()), "Chýba dôvod chyby v tooltipe.")
                    window.remove_failed()
                    _require(len(window.session.records) == 3 and broken.exists(), "Odstránenie chyby zmazalo vstup.")
                    _pump_until(app, lambda: not window._jobs and window._writer.is_idle and not window._preview_timer.isActive()
                                and window.preview._pixmap is not None)
                    pattern_path = root / "native-detail-pattern.png"
                    stripes = np.broadcast_to((np.arange(4096) % 2 * 255).astype(np.uint8), (2048, 4096))
                    with Image.fromarray(stripes).convert("RGB") as native_pattern:
                        native_pattern.save(pattern_path)
                    window.import_paths([str(pattern_path)])
                    _pump_until(app, lambda: not window._jobs and window._writer.is_idle)
                    window.image_list.setCurrentRow(3)
                    _pump_until(app, lambda: not window._jobs and window._writer.is_idle
                                and not window._preview_timer.isActive() and window.preview._pixmap is not None)
                    window._settings_changed(replace(window._record().settings, mode="expand", ratio_mode="fixed", ratio=16 / 9))
                    _pump_until(app, lambda: not window._jobs and window._writer.is_idle
                                and not window._preview_timer.isActive()
                                and not window.preview._detail_timer.isActive()
                                and window.preview._detail_state == "native")
                    _require(window.preview.zoom_percent == 100 and window.preview._detail is not None,
                             "Originál sa nepripravil už pri základnom pohľade.")
                    warmed_source = window._detail_renderer._source
                    window.preview.set_zoom(1000)
                    _pump_until(app, lambda: window.preview._detail_state == "native" and not window._jobs
                                and not window.preview._detail_timer.isActive())
                    _require(window._detail_renderer._source.size == (4096, 2048), "Detail nebol dekódovaný z originálu.")
                    _require(window._detail_renderer._source is warmed_source,
                             "Zoom zbytočne znovu dekódoval aktívny originál.")
                    native_detail = window.preview._detail[0].toImage()
                    samples = [native_detail.pixelColor(x, native_detail.height() // 2).red() for x in range(native_detail.width())]
                    # At 1000% of a narrow fit viewport, the native source may
                    # still be downsampled. It must nevertheless recover detail
                    # missing from the uniformly grey 2048px thumbnail.
                    _require(max(samples) - min(samples) > 10, "Hi-res náhľad neobnovil jemný detail originálu.")
                    settings_before_pan = window._record().settings.to_dict()
                    state_before_pan = window.store.path.read_bytes()
                    pan_before = QPointF(window.preview._pan)
                    start = window.preview._area().center()
                    end = start + QPointF(50, 25)
                    for event_type, point, button, buttons in (
                        (QEvent.Type.MouseButtonPress, start, Qt.MouseButton.RightButton, Qt.MouseButton.RightButton),
                        (QEvent.Type.MouseMove, end, Qt.MouseButton.NoButton, Qt.MouseButton.RightButton),
                        (QEvent.Type.MouseButtonRelease, end, Qt.MouseButton.RightButton, Qt.MouseButton.NoButton),
                    ):
                        event = QMouseEvent(event_type, point, QPointF(window.preview.mapToGlobal(point.toPoint())),
                                            button, buttons, Qt.KeyboardModifier.NoModifier)
                        QApplication.sendEvent(window.preview, event)
                    _require(window.preview._pan == pan_before + QPointF(50, 25), "Pravé tlačidlo neposunulo viewport.")
                    _require(window.preview._detail is not None, "Pohyb zahodil dostupný natívny detail.")
                    _require(window._record().settings.to_dict() == settings_before_pan
                             and window.store.path.read_bytes() == state_before_pan,
                             "Pravý posun zmenil nastavenia fotografie alebo reláciu.")
                    _require(window.settings.grid_buttons[3].text() == "φ", "Chýba symbol zlatého rezu φ.")
                    _require(len({button.height() for button in window.settings.grid_buttons}) == 1,
                             "Tlačidlá kompozície nemajú rovnakú výšku.")
                    for event_type in (QEvent.Type.MouseButtonDblClick, QEvent.Type.MouseButtonRelease):
                        event = QMouseEvent(event_type, start, QPointF(window.preview.mapToGlobal(start.toPoint())),
                                            Qt.MouseButton.RightButton,
                                            Qt.MouseButton.RightButton if event_type == QEvent.Type.MouseButtonDblClick
                                            else Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
                        QApplication.sendEvent(window.preview, event)
                    _require(window.preview.zoom_percent == 100, "Pravý dvojklik neobnovil základný zoom.")
                    _require(window.preview._pan.isNull(), "Odzoomovanie nevycentrovalo zobrazenie.")
                    _require(window._record().settings.to_dict() == settings_before_pan
                             and window.store.path.read_bytes() == state_before_pan,
                             "Pravý dvojklik zmenil nastavenia fotografie alebo reláciu.")
                    for corner, target_original in (("nw", (100, 50)), ("se", (900, 450))):
                        preview = window.preview
                        geometry = preview._geometry
                        position = preview._crop_handle_positions(preview._crop_rect())[corner]
                        origin, scale = preview._mapping()
                        left, top, _, _ = geometry.foreground_box
                        source_left, source_top, _, _ = geometry.source_box
                        end = origin + QPointF(left + target_original[0] - source_left,
                                              top + target_original[1] - source_top) * scale
                        for event_type, point, button, buttons in (
                            (QEvent.Type.MouseButtonPress, position, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton),
                            (QEvent.Type.MouseMove, end, Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton),
                            (QEvent.Type.MouseButtonRelease, end, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton),
                        ):
                            event = QMouseEvent(event_type, point, QPointF(preview.mapToGlobal(point.toPoint())),
                                                button, buttons, Qt.KeyboardModifier.NoModifier)
                            QApplication.sendEvent(preview, event)
                        _pump_until(app, lambda: not window._jobs and window._writer.is_idle
                                    and not window._preview_timer.isActive()
                                    and not preview._detail_timer.isActive())
                    _require(window._record().settings.crop_box == (100, 50, 900, 450), "Úchyty náhľadu nepoužili správny vstupný výrez.")
                    _require(QApplication.activeModalWidget() is None, "Pri výreze sa otvoril neželaný dialóg.")
                    _require(window.store.load().records[3].settings.crop_box == (100, 50, 900, 450), "Výrez sa neuložil do relácie.")
                    original_view = preview._mapped(preview._original_rect())
                    _require(preview._area().adjusted(-.001, -.001, .001, .001).contains(original_view),
                             "Po výreze sa náhľad priblížil a skryl pôvodné okraje fotografie.")
                    window.settings.reset_crop_button.click()
                    _pump_until(app, lambda: not window._jobs and window._writer.is_idle
                                and not window._preview_timer.isActive()
                                and not window.preview._detail_timer.isActive())
                    _require(window._record().settings.crop_box is None, "Obnova celého záberu neodstránila výrez.")
                    window.remove_path(str(pattern_path))
                    window.image_list.setCurrentRow(0)
                    _pump_until(app, lambda: not window._jobs and window._writer.is_idle and not window._preview_timer.isActive()
                                and window.preview._pixmap is not None)
                    _require(not window.preview._pixmap.isNull(), "GUI náhľad je prázdny.")
                    _require(max(window.preview._pixmap.width(), window.preview._pixmap.height()) <= 2048, "GUI náhľad je príliš veľký.")
                    _require(os.name != "nt" or app.platformName() == "windows", "Qt nepoužíva Windows platform plugin.")
                    screenshot = report_path.with_suffix(".png")
                    capture = window.grab()
                    _require(not capture.isNull() and capture.save(str(screenshot), "PNG"), "Qt screenshot sa nepodarilo uložiť.")
                    details = {
                        "platform_plugin": app.platformName(), "panes": window.splitter.count(),
                        "imported_images": len(window.session.records),
                        "maximized": window.isMaximized(), "exported_records": len(window.session.records),
                        "initial_imported_records": 3, "previewed_records": 3, "selected_export_records": 1,
                        "all_export_skipped_imported": 2, "blocked_imported_only_export": True,
                        "zoom_max": 1000, "grid_preserves_export": True,
                        "failed_row_and_summary": True,
                        "native_detail_original_width": 4096, "zoom_out_centered": True,
                        "native_warmed_at_fit": True, "native_reused_during_pan": True,
                        "viewport_device_pixel_ratio": window.preview.devicePixelRatioF(),
                        "right_pan_preserves_settings": True, "composition_symbol": "φ",
                        "right_double_click_fits_view": True,
                        "inline_crop_handles": True, "source_crop_size": [800, 400],
                        "whole_original_visible_after_crop": True,
                        "screenshot": str(screenshot), "screenshot_size": [capture.width(), capture.height()],
                    }
                finally:
                    try:
                        if window is not None:
                            window.close()
                            _pump_until(app, lambda: not window._jobs and window._writer.is_idle and not window.isVisible(), seconds=20)
                            _require(window._pool.waitForDone(5000), "Qt workery sa neukončili.")
                            _require(window._pool.activeThreadCount() == 0, "Qt worker stále beží.")
                            window.deleteLater()
                            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
                    finally:
                        app.setQuitOnLastWindowClosed(previous_quit)
                return details

            def hdr_codec(kind: str) -> dict[str, Any]:
                rgb = np.empty((64, 128, 3), dtype=np.float32)
                rgb[:] = (4, 1, .5)
                sdr = Image.new("RGB", (128, 64), "#e7a67a")
                tile = HdrTile(rgb, sdr)
                try:
                    extension = ".jpg" if kind == "ultrahdr" else ".heic"
                    source = root / (kind + extension)
                    source.write_bytes(encode_hdr_tile(tile, HdrInfo(kind)))
                finally:
                    tile.close()
                info = detect_hdr(source)
                _require(info.is_hdr and info.supported, "Chýba platný HDR signál.")
                with load_hdr(source) as decoded:
                    maximum = float(decoded.rgb.max())
                    _require(maximum > 3.5, "HDR jasový rozsah sa stratil.")
                with load_image(source, max_edge=48) as preview:
                    _require(preview.mode == "RGB" and max(preview.size) <= 48, "Náhľad HDR nie je zmenšené SDR.")
                settings = Settings(mode="expand", ratio_mode="fixed", ratio=1, hdr_mode="hdr")
                hdr_report = export_records([ImageRecord(str(source), settings)], root / (kind + "-out"))
                _require(not hdr_report.errors and len(hdr_report.paths) == 1, "HDR export zlyhal.")
                _require(hdr_report.paths[0].name.endswith("_HDR_01" + extension), "Chýba HDR prípona.")
                _require(detect_hdr(hdr_report.paths[0]).is_hdr, "Výstup nie je skutočné HDR.")
                sdr_report = export_records([ImageRecord(str(source), replace(settings, hdr_mode="sdr"))], root / (kind + "-out"))
                _require(not sdr_report.errors and sdr_report.paths[0].name.endswith("_SDR_01.jpg"), "SDR konverzia zlyhala.")
                with Image.open(sdr_report.paths[0]) as output_image:
                    _require(not output_image.getexif() and bool(output_image.info.get("icc_profile")), "SDR výstupné metadáta nesedia.")
                return {"input": info.description, "linear_peak": round(maximum, 3), "hdr_extension": extension, "sdr_export": True}

            def preferences_help() -> dict[str, Any]:
                store = PreferencesStore(root / "preferences" / "preferences.json")
                preferences = replace(store.defaults(), language="cs", theme="light", onboarding_completed=True)
                store.save(preferences)
                _require(store.load() == preferences, "Globálne nastavenia sa neobnovili.")
                for language in ("en", "sk", "cs"):
                    dialog = HelpDialog(language)
                    try:
                        _require(len(dialog.browser.toPlainText()) > 3000, "Chýba pribalený používateľský návod.")
                    finally:
                        dialog.close()
                return {"preferences_roundtrip": True, "bundled_guides": ["en", "sk", "cs"]}

            def series_rollback() -> dict[str, Any]:
                from insta_g.core import export as module

                original = module._save_jpeg_exclusive
                calls = 0

                def injected(*args: Any, **kwargs: Any) -> Path:
                    nonlocal calls
                    calls += 1
                    if calls == 2:
                        raise OSError("Injected second-tile failure")
                    return original(*args, **kwargs)

                module._save_jpeg_exclusive = injected
                try:
                    result = export_records([
                        ImageRecord(str(heic_path), Settings(splits=3)),
                        ImageRecord(str(png_path), Settings(mode="expand")),
                    ], root / "rollback")
                finally:
                    module._save_jpeg_exclusive = original
                _require(len(result.failed) == 1 and len(result.paths) == 1, "Chyba nezachovala úplné série.")
                _require(not list((root / "rollback").glob("smoke-heic*")), "Po chybe zostali diely neúplnej série.")
                return {"failed_originals": 1, "later_photo_completed": True, "partial_files_removed": True}

            def real_hdr_fixture(path: Path) -> dict[str, Any]:
                info = detect_hdr(path)
                _require(info.is_hdr and info.supported, "Vzorka nie je podporované HDR.")
                with load_hdr(path) as image:
                    size = image.size
                    maximum = float(image.rgb.max())
                settings = Settings(splits=3, hdr_mode="hdr")
                result = export_records([ImageRecord(str(path), settings)], root / ("real-" + path.stem))
                _require(not result.errors and len(result.paths) == 3, "Export skutočnej HDR vzorky zlyhal: " + "; ".join(result.errors))
                with load_hdr(result.paths[0]) as image:
                    exported_peak = float(image.rgb.max())
                    _require(image.size == (get_geometry(size, settings).tile_width, get_geometry(size, settings).tile_height), "HDR výstup zmenil mierku.")
                return {"source": path.name, "kind": info.kind, "native_size": size,
                        "source_linear_peak": maximum, "first_tile_linear_peak": exported_peak,
                        "hdr_outputs": 3}

            def source_crop_export() -> dict[str, Any]:
                path = root / "input-crop.png"
                with Image.new("RGB", (1000, 500), "#D02020") as image:
                    draw = ImageDraw.Draw(image)
                    draw.rectangle((100, 50, 899, 449), fill="#20A040")
                    image.save(path)
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                settings = Settings(mode="expand", ratio_mode="fixed", ratio=1,
                                    crop_box=(100, 50, 900, 450), offset_y=1,
                                    background_mode="solid", background_color="#FFFFFF")
                with load_image(path) as source, render_composite(source, settings) as image:
                    _require(image.size == (800, 800), "Výrez zmenil mierku originálnych pixelov.")
                    _require(image.getpixel((5, 405)) == (32, 160, 64), "Náhľad obsahuje nesprávne pixely výrezu.")
                    _require(image.getpixel((5, 5)) == (255, 255, 255), "Posun výrezu a padding nesedia.")
                result = export_records([ImageRecord(str(path), settings, previewed=True)], root / "crop-export")
                _require(not result.errors and len(result.paths) == 1, "Export vstupného výrezu zlyhal.")
                with Image.open(result.paths[0]) as image:
                    _require(image.size == (800, 800), "Export má nesprávne rozmery výrezu.")
                    _require(all(abs(a - b) <= 3 for a, b in zip(image.getpixel((5, 405)), (32, 160, 64))),
                             "Export nezodpovedá pixelom výrezu.")
                _require(hashlib.sha256(path.read_bytes()).hexdigest() == digest, "Výrez zmenil vstupný súbor.")
                return {"original": [1000, 500], "crop": [800, 400], "output": [800, 800],
                        "native_pixels": True, "offset_and_padding": True, "original_unchanged": True}

            check("jpeg_orientation_srgb", jpeg_codec)
            check("png_transparency", png_codec)
            check("heic_encode_decode", heic_codec)
            check("geometry_preview_seams", geometry_and_preview)
            check("jpeg_batch_export_collision_metadata", export_jpeg)
            check("temporary_session_roundtrip", persistence)
            check("qt_main_window_workers_screenshot", gui)
            check("ultrahdr_jpeg_roundtrip_export", lambda: hdr_codec("ultrahdr"))
            check("pq_heic_roundtrip_export", lambda: hdr_codec("heif_pq"))
            check("preferences_and_bundled_help", preferences_help)
            check("failed_series_rollback_and_continue", series_rollback)
            check("source_crop_preview_export", source_crop_export)
            for index, path in enumerate(external_hdr, 1):
                check(f"real_hdr_fixture_{index}_{path.stem}", lambda path=path: real_hdr_fixture(path))
    except Exception as exc:
        report["errors"].append(f"Diagnostika: {type(exc).__name__}: {exc}")
    report["ok"] = not report["errors"] and len(report["checks"]) == 12 + len(external_hdr)
    try:
        _write_report(report_path, report)
    except OSError as exc:
        if sys.stderr is not None:
            print(f"Smoke report sa nepodarilo zapísať: {exc}", file=sys.stderr)
        return 1
    return 0 if report["ok"] else 1
