"""GUI integration checks use generated photographs and temporary session stores."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from threading import Event

import pytest
from PIL import Image
from PySide6.QtCore import QMimeData, QPointF, Qt, QTimer, QUrl
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QWidget

from insta_g.core.export import ExportReport
from insta_g.core.geometry import get_geometry
from insta_g.core.models import ImageRecord, Settings
from insta_g.gui import workers
from insta_g.gui.library import STATUS_ROLE
from insta_g.gui.window import MainWindow
from insta_g.i18n import get_language, set_language
from insta_g.persistence import Session, SessionStore


@pytest.fixture(autouse=True)
def slovak_interface():
    previous = get_language()
    set_language("sk")
    yield
    set_language(previous)


@pytest.fixture
def window_factory(qtbot, tmp_path):
    windows = []

    def close_safely(window):
        # pytest-qt calls deleteLater immediately after close(). Let the application's
        # deferred close finish before the plugin destroys its thread pool and signals.
        window.close()
        qtbot.waitUntil(lambda: not window._jobs and window._writer.is_idle, timeout=20000)
        window.close()

    def create(session=None):
        state = session if session is not None else Session()
        store = SessionStore(tmp_path / f"session-{len(windows)}.json")
        store.save(state)
        window = MainWindow(store, state)
        windows.append(window)
        qtbot.addWidget(window, before_close_func=close_safely)
        window.show()
        return window

    return create


def photograph(path: Path, size=(500, 200), color=(100, 160, 70)) -> str:
    Image.new("RGB", size, color).save(path)
    return str(path)


def ready(qtbot, window, count=1):
    qtbot.waitUntil(lambda: len(window.session.records) == count, timeout=15000)
    if window.image_list.currentItem() is None:
        window.image_list.setCurrentRow(0)
    qtbot.waitUntil(lambda: window.preview._pixmap is not None, timeout=15000)
    qtbot.waitUntil(
        lambda: not window._jobs and window._writer.is_idle
        and not window._preview_timer.isActive() and not window._preview_pending,
        timeout=15000,
    )


def saved_session(qtbot, window):
    qtbot.waitUntil(lambda: window._writer.is_idle, timeout=20000)
    return window.store.load()


def test_async_import_individual_settings_preview_and_batch_export(window_factory, qtbot, tmp_path):
    panorama = photograph(tmp_path / "panorama.png", (3000, 900))
    portrait = photograph(tmp_path / "portrait.jpg", (400, 1000))
    window = window_factory()
    window.import_paths([panorama, portrait, panorama])
    ready(qtbot, window, 2)
    assert window.image_list.count() == 2
    assert max(window.preview._pixmap.width(), window.preview._pixmap.height()) <= 2048
    window.settings.splits.setValue(4)
    window.settings.blur_value.setValue(85)
    assert window.settings.ratio_label.text() == "0.833:1"
    saved = saved_session(qtbot, window)
    assert saved.records[0].settings.splits == 4
    assert saved.records[0].settings.blur == 85
    window.image_list.setCurrentRow(1)
    window.settings.expand_button.click()
    window.settings.ratio_buttons[0].click()
    assert window.session.records[1].settings.mode == "expand"
    window.settings.ratio.setValue(0)
    assert window.session.records[1].settings.ratio == 3 / 4
    assert not window.settings.warning.isVisible()
    window.settings.ratio.setValue(1000)
    assert window.session.records[1].settings.ratio == 16 / 9
    window.settings.ratio_buttons[4].click()
    window.settings.blur_value.setValue(0)
    ready(qtbot, window, 2)
    window.image_list.setCurrentRow(0)
    assert window.settings.splits.value() == 4
    assert window.settings.blur_value.value() == 85
    assert window.session.records[1].settings.blur == 0
    directory = tmp_path / "export"
    directory.mkdir()
    window.start_export(str(directory))
    qtbot.waitUntil(lambda: window._export_job is None, timeout=20000)
    results = list(directory.glob("*.jpg"))
    assert len(results) == 5
    for path in results:
        with Image.open(path) as exported:
            assert exported.format == "JPEG"
            assert exported.width in {750, 1000}
    assert "dokončený" in window.notice.text()
    assert (tmp_path / "panorama.png").exists()


def test_restore_selected_image_without_replacing_settings(window_factory, qtbot, tmp_path):
    first = photograph(tmp_path / "first.png")
    second = photograph(tmp_path / "second.png")
    session = Session(
        records=[
            ImageRecord(first, Settings(splits=5, blur=12)),
            ImageRecord(second, Settings(mode="expand", ratio_mode="fixed", blur=777)),
        ],
        selected_path=second,
    )
    window = window_factory(session)
    ready(qtbot, window, 2)
    assert window._record().path == second
    assert window.settings.blur_value.value() == 777
    assert window.settings.expand_button.isChecked()
    assert saved_session(qtbot, window).selected_path == second
    window.image_list.setCurrentRow(0)
    assert window.settings.splits.value() == 5
    assert window.settings.blur_value.value() == 12
    window.image_list.setCurrentRow(1)
    assert window.settings.blur_value.value() == 777


def test_native_geometry_fit_fill_offsets_and_ghost_preview(window_factory, qtbot, tmp_path):
    window = window_factory()
    window.import_paths([photograph(tmp_path / "panorama.png", (600, 100), (200, 100, 50))])
    ready(qtbot, window)
    window.settings.splits.setValue(2)
    window.settings.ratio_buttons[4].click()
    window.settings.fit_button.click()
    assert not window.settings.auto.isChecked()
    assert "Výstup 2 × 300 × 300 px" in window.settings.geometry_label.text()
    window.settings.offset_y.setValue(-100)
    assert get_geometry((600, 100), window._record().settings).foreground_box[1] == 0
    window.settings.offset_y.setValue(100)
    assert get_geometry((600, 100), window._record().settings).foreground_box[1] == 200
    window.settings.center_button.click()
    assert window._record().settings.offset_y == 0
    window.settings.fill_button.click()
    assert window._record().settings.fit_mode == "fill"
    assert "Výstup 2 × 100 × 100 px" in window.settings.geometry_label.text()
    assert window.settings.warning.isVisible()
    assert not window.settings.blur.isEnabled()
    window.settings.offset_x.setValue(-100)
    assert get_geometry((600, 100), window._record().settings).foreground_box[0] == 0
    window.settings.offset_x.setValue(100)
    assert get_geometry((600, 100), window._record().settings).foreground_box[0] == -400
    window.settings.center_button.click()
    qtbot.waitUntil(
        lambda: not window._preview_timer.isActive() and not window._jobs and window._writer.is_idle, timeout=10000
    )
    assert window.preview._geometry.foreground_box[0] == -200
    assert window.preview._source_pixmap is not None
    capture = window.preview.grab().toImage()
    ghost = capture.pixelColor(int(capture.width() * 0.2), capture.height() // 2)
    # The exact centre is the dark/dashed divider between the two tiles.
    # Sample inside the foreground, clear of the overlay itself.
    foreground = capture.pixelColor(capture.width() // 2 + 12, capture.height() // 2)
    assert 40 < ghost.red() < 120
    assert foreground.red() > 180
    window.settings.expand_button.click()
    assert not window.settings.fill_button.isEnabled()
    assert not window.settings.warning.isVisible()
    assert "Výstup 1 × 600 × 600 px" in window.settings.geometry_label.text()
    assert window.findChild(QWidget, "exportWidthSpin") is None
    assert window.findChild(QWidget, "orientationCombo") is None


def test_drag_and_drop_import_and_failure_notice(window_factory, qtbot, tmp_path):
    path = photograph(tmp_path / "drop.png")
    window = window_factory()
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(path)])
    event = QDropEvent(QPointF(20, 20), Qt.DropAction.CopyAction, mime,
                       Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    window.image_list.dropEvent(event)
    assert event.isAccepted()
    ready(qtbot, window)
    broken = tmp_path / "broken.png"
    broken.write_bytes(b"not a photograph")
    window.import_paths([str(broken)])
    qtbot.waitUntil(lambda: not window._jobs and window._writer.is_idle, timeout=15000)
    assert len(window.session.records) == 2
    assert window.session.records[1].status == "failed"
    assert "broken.png" in window.notice.text()
    assert window.notice.isVisible()


def test_preview_cache_is_bounded_and_reduced(window_factory, qtbot, tmp_path):
    window = window_factory()
    paths = [photograph(tmp_path / f"image-{index}.png", (2600, 800)) for index in range(8)]
    window.import_paths(paths)
    ready(qtbot, window, 8)
    assert len(window._sources) <= 6
    assert all(max(image.size) <= 2048 for image in window._sources.values())
    assert window.image_list.count() == 8


def test_late_preview_cannot_overwrite_new_settings(window_factory, qtbot, tmp_path, monkeypatch):
    window = window_factory()
    window.import_paths([photograph(tmp_path / "photo.png")])
    ready(qtbot, window)
    started = Event()
    release = Event()
    original = workers.PreviewRenderer.render

    def controlled_render(renderer, image, settings, *, max_edge=2048, cancelled=None):
        if settings.blur == 41:
            started.set()
            if not release.wait(10):
                raise RuntimeError("Preview synchronization timed out")
        return original(renderer, image, settings, max_edge=max_edge, cancelled=cancelled)

    monkeypatch.setattr(workers.PreviewRenderer, "render", controlled_render)
    try:
        window.settings.blur_value.setValue(41)
        qtbot.waitUntil(started.is_set, timeout=5000)
        old_job = window._preview_job
        window.settings.splits.setValue(5)
        window.settings.blur_value.setValue(42)
        assert old_job.cancel.is_set()
        release.set()
        ready(qtbot, window)
        assert window.preview._count == 5
        assert window._record().settings.blur == 42
    finally:
        release.set()


def test_export_snapshot_cancellation_and_responsive_gui(window_factory, qtbot, tmp_path, monkeypatch):
    window = window_factory()
    window.import_paths([photograph(tmp_path / "photo.png")])
    ready(qtbot, window)
    started = Event()
    release = Event()
    snapshot = []

    def controlled_export(records, output_dir, progress=None, cancelled=None, **kwargs):
        snapshot.extend(replace(record.settings) for record in records)
        started.set()
        release.wait(10)
        return ExportReport(paths=[], errors=[], cancelled=cancelled())

    monkeypatch.setattr(workers, "export_records", controlled_export)
    ticks = []
    timer = QTimer(window)
    timer.setInterval(5)
    timer.timeout.connect(lambda: ticks.append(True))
    try:
        (tmp_path / "cancelled-export").mkdir()
        window.start_export(str(tmp_path / "cancelled-export"))
        qtbot.waitUntil(started.is_set, timeout=5000)
        timer.start()
        window.settings.blur_value.setValue(99)
        qtbot.waitUntil(lambda: len(ticks) >= 3, timeout=5000)
        assert snapshot[0].blur == 40
        assert window._record().settings.blur == 99
        window.cancel_export()
        assert window._export_job.cancel.is_set()
        release.set()
        qtbot.waitUntil(lambda: window._export_job is None, timeout=10000)
        assert "zrušený" in window.notice.text()
    finally:
        timer.stop()
        release.set()


def test_save_failure_is_visible_and_changes_stay_in_memory(window_factory, qtbot, tmp_path, monkeypatch):
    window = window_factory()
    window.import_paths([photograph(tmp_path / "photo.png")])
    ready(qtbot, window)

    def fail_save(session):
        raise OSError("disk unavailable")

    monkeypatch.setattr(window.store, "save", fail_save)
    window.settings.blur_value.setValue(250)
    assert window._record().settings.blur == 250
    qtbot.waitUntil(lambda: "disk unavailable" in window.notice.text(), timeout=10000)
    assert "iba v pamäti" in window.notice.text()
    assert "disk unavailable" in window.notice.text()


@pytest.mark.parametrize("other_error", [None, "import", "export", "save"])
def test_successful_preview_clears_only_its_own_error(
    window_factory, qtbot, tmp_path, monkeypatch, other_error
):
    path = photograph(tmp_path / "photo.png")
    window = window_factory()
    window.import_paths([path])
    ready(qtbot, window)
    expected_error = None
    if other_error == "import":
        broken = tmp_path / "broken.png"
        broken.write_bytes(b"invalid")
        window.import_paths([str(broken)])
        qtbot.waitUntil(lambda: not window._jobs and window._writer.is_idle, timeout=10000)
        expected_error = "broken.png"
    elif other_error == "export":
        # A source file cannot also be an export directory.
        window.start_export(path)
        qtbot.waitUntil(lambda: window._export_job is None, timeout=10000)
        expected_error = window.notice.text()
        assert expected_error
    elif other_error == "save":
        def fail_save(session):
            raise OSError("save failure to preserve")
        monkeypatch.setattr(window.store, "save", fail_save)
        window.settings.offset_x.setValue(25)
        qtbot.waitUntil(
            lambda: not window._preview_timer.isActive() and not window._jobs and window._writer.is_idle, timeout=10000
        )
        expected_error = "save failure to preserve"
    original = workers.PreviewRenderer.render

    def transient_failure(renderer, image, settings, *, max_edge=2048, cancelled=None):
        if settings.blur == 41:
            raise ValueError("temporary preview failure")
        return original(renderer, image, settings, max_edge=max_edge, cancelled=cancelled)

    monkeypatch.setattr(workers.PreviewRenderer, "render", transient_failure)
    window.settings.blur_value.setValue(41)
    qtbot.waitUntil(lambda: "temporary preview failure" in window.notice.text(), timeout=10000)
    assert ("preview", path) in window._notices
    window.settings.blur_value.setValue(42)
    qtbot.waitUntil(
        lambda: not window._preview_timer.isActive() and not window._jobs and window._writer.is_idle, timeout=10000
    )
    assert ("preview", path) not in window._notices
    assert "temporary preview failure" not in window.notice.text()
    if expected_error is None:
        assert not window.notice.isVisible()
    else:
        assert expected_error in window.notice.text()
        assert window.notice.isVisible()


def test_close_waits_for_running_import_without_destroying_thread(window_factory, qtbot, tmp_path, monkeypatch):
    window = window_factory()
    path = photograph(tmp_path / "photo.png")
    started = Event()
    release = Event()
    original = workers.load_image

    def delayed_load(path, max_edge=None):
        started.set()
        release.wait(10)
        return original(path, max_edge=max_edge)

    monkeypatch.setattr(workers, "load_image", delayed_load)
    try:
        window.import_paths([path])
        qtbot.waitUntil(started.is_set, timeout=5000)
        window.close()
        assert window._closing
        assert window.isVisible()
        assert not window.isEnabled()
        release.set()
        qtbot.waitUntil(lambda: not window.isVisible(), timeout=10000)
        assert not window._jobs
    finally:
        release.set()


def test_checked_bulk_and_per_row_removal_keep_files(window_factory, qtbot, tmp_path):
    paths = [photograph(tmp_path / f"photo-{index}.png") for index in range(3)]
    window = window_factory()
    window.import_paths(paths)
    ready(qtbot, window, 3)
    for row in (1, 2):
        window.image_list.item(row).setCheckState(Qt.CheckState.Checked)
    assert window._record().path == paths[0]
    assert [record.checked for record in saved_session(qtbot, window).records] == [False, True, True]
    assert window.remove_checked_button.isEnabled()
    window.remove_checked_button.click()
    assert [record.path for record in window.session.records] == [paths[0]]
    assert all(Path(path).exists() for path in paths)
    window.image_list.removeRequested.emit(paths[0])
    assert window.session.records == []
    assert window.image_list.count() == 0
    assert saved_session(qtbot, window).records == []
    assert not window.remove_checked_button.isEnabled()
    assert all(Path(path).exists() for path in paths)


def test_export_colours_edit_and_remove_exported_are_persisted(window_factory, qtbot, tmp_path):
    paths = [photograph(tmp_path / f"photo-{index}.png", (360, 120)) for index in range(2)]
    window = window_factory()
    window.import_paths(paths)
    ready(qtbot, window, 2)
    assert [window.image_list.item(row).data(STATUS_ROLE) for row in range(2)] == ["staging", "imported"]
    window.image_list.setCurrentRow(1)
    ready(qtbot, window, 2)
    window.image_list.setCurrentRow(0)
    window.image_list.item(0).setCheckState(Qt.CheckState.Checked)
    directory = tmp_path / "export"
    directory.mkdir()
    window.start_export(str(directory))
    qtbot.waitUntil(lambda: window._export_job is None, timeout=20000)
    assert len(list(directory.glob("*.jpg"))) == 6  # Export all includes unchecked photographs.
    assert all(record.is_exported for record in window.session.records)
    assert all(window.image_list.item(row).data(STATUS_ROLE) == "exported" for row in range(2))
    assert all(record.is_exported for record in saved_session(qtbot, window).records)
    window.settings.blur_value.setValue(180)
    assert not window.session.records[0].is_exported
    assert window.image_list.item(0).data(STATUS_ROLE) == "staging"
    assert window.remove_exported_button.isEnabled()
    window.remove_exported_button.click()
    assert [record.path for record in window.session.records] == [paths[0]]
    assert window.session.records[0].checked
    assert not window.remove_exported_button.isEnabled()
    assert all(Path(path).exists() for path in paths)
    assert len(list(directory.glob("*.jpg"))) == 6
    restored = window_factory(saved_session(qtbot, window))
    ready(qtbot, restored)
    assert restored.image_list.item(0).checkState() == Qt.CheckState.Checked
    assert restored.image_list.item(0).data(STATUS_ROLE) == "staging"
    restored.remove_all_button.click()
    assert restored.session.records == []


def test_partial_batch_marks_only_successfully_completed_photograph(window_factory, qtbot, tmp_path):
    paths = [photograph(tmp_path / f"photo-{index}.png", (360, 120)) for index in range(2)]
    window = window_factory()
    window.import_paths(paths)
    ready(qtbot, window, 2)
    window.image_list.setCurrentRow(1)
    ready(qtbot, window, 2)
    window.image_list.setCurrentRow(0)
    Path(paths[1]).unlink()  # Generated fixture disappears after import.
    (tmp_path / "export").mkdir()
    window.start_export(str(tmp_path / "export"))
    qtbot.waitUntil(lambda: window._export_job is None, timeout=20000)
    assert window.session.records[0].is_exported
    assert not window.session.records[1].is_exported
    assert window.image_list.item(0).data(STATUS_ROLE) == "exported"
    assert window.image_list.item(1).data(STATUS_ROLE) == "failed"
    assert "zlyhal" in window.notice.text()


def test_reimport_during_snapshot_export_does_not_mark_new_record(window_factory, qtbot, tmp_path, monkeypatch):
    path = photograph(tmp_path / "photo.png")
    window = window_factory()
    window.import_paths([path])
    ready(qtbot, window)
    original_record = window.session.records[0]
    started = Event()
    release = Event()

    def controlled_export(records, output_dir, progress=None, cancelled=None, **kwargs):
        snapshot = records[0].settings.to_dict()
        started.set()
        release.wait(10)
        return ExportReport(completed={path: snapshot})

    monkeypatch.setattr(workers, "export_records", controlled_export)
    try:
        (tmp_path / "export").mkdir()
        window.start_export(str(tmp_path / "export"))
        qtbot.waitUntil(started.is_set, timeout=5000)
        window.remove_path(path)
        window.import_paths([path])
        qtbot.waitUntil(lambda: len(window.session.records) == 1, timeout=10000)
        assert window.session.records[0] is not original_record
        release.set()
        qtbot.waitUntil(lambda: window._export_job is None, timeout=10000)
        assert not window.session.records[0].is_exported
    finally:
        release.set()


def test_remove_all_during_pending_import_ignores_old_result(window_factory, qtbot, tmp_path, monkeypatch):
    path = photograph(tmp_path / "photo.png")
    window = window_factory()
    started = Event()
    release = Event()
    original = workers.load_image
    calls = []

    def first_decode_waits(path, max_edge=None):
        calls.append(path)
        if len(calls) == 1:
            started.set()
            release.wait(10)
        return original(path, max_edge=max_edge)

    monkeypatch.setattr(workers, "load_image", first_decode_waits)
    try:
        window.import_paths([path])
        qtbot.waitUntil(started.is_set, timeout=5000)
        assert window.remove_all_button.isEnabled()
        window.remove_all_button.click()
        assert window.session.records == []
        window.import_paths([path])
        qtbot.waitUntil(lambda: len(window.session.records) == 1, timeout=10000)
        release.set()
        qtbot.waitUntil(lambda: not window._jobs and window._writer.is_idle, timeout=10000)
        assert window.image_list.count() == 1
        assert len(window.session.records) == 1
        assert Path(path).exists()
    finally:
        release.set()


@pytest.mark.parametrize("removal", ["all", "row"])
def test_late_import_error_for_removed_photo_is_ignored(window_factory, qtbot, tmp_path, monkeypatch, removal):
    path = photograph(tmp_path / "photo.png")
    started = Event()
    release = Event()

    def deferred_failure(path, max_edge=None):
        started.set()
        release.wait(10)
        raise ValueError("obsolete removed import failure")

    monkeypatch.setattr(workers, "load_image", deferred_failure)
    window = window_factory(Session(records=[ImageRecord(path)], selected_path=path))
    try:
        qtbot.waitUntil(started.is_set, timeout=5000)
        if removal == "all":
            window.remove_all_button.click()
        else:
            window.image_list.removeRequested.emit(path)
        release.set()
        qtbot.waitUntil(lambda: not window._jobs and window._writer.is_idle, timeout=10000)
        assert window.session.records == []
        assert "obsolete removed import failure" not in window.notice.text()
        assert not window._import_errors
    finally:
        release.set()
