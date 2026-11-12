"""An input crop becomes the shared source for placement, preview and export."""

from dataclasses import replace
from threading import Event

import pytest
from PIL import Image, ImageDraw
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from insta_g.core.geometry import get_geometry
from insta_g.core.models import ImageRecord, Settings
from insta_g.gui.window import MainWindow
from insta_g.persistence import Session, SessionStore


def idle(qtbot, window):
    qtbot.waitUntil(lambda: not window._jobs and window._writer.is_idle
                   and not window._preview_timer.isActive()
                   and not window.preview._detail_timer.isActive()
                   and window._detail_pending is None, timeout=30000)


@pytest.fixture
def window(qtbot, tmp_path):
    path = tmp_path / "original.png"
    with Image.new("RGB", (1000, 500), "#D02020") as source:
        draw = ImageDraw.Draw(source)
        draw.rectangle((100, 50, 899, 449), fill="#20A040")
        draw.rectangle((400, 50, 599, 449), fill="#2040C0")
        source.save(path)
    settings = Settings(mode="expand", splits=2, ratio_mode="fixed", ratio=1,
                        background_mode="solid", background_color="#123456",
                        offset_x=.37, offset_y=-.4)
    record = ImageRecord(str(path), settings, checked=True, previewed=True,
                         exported_settings=settings.to_dict())
    widget = MainWindow(SessionStore(tmp_path / "session.json"),
                        Session([record], selected_path=str(path)))

    def close_safely(window):
        window.close()
        qtbot.waitUntil(lambda: not window._jobs and window._writer.is_idle, timeout=30000)
        window.close()

    qtbot.addWidget(widget, before_close_func=close_safely)
    widget.show()
    idle(qtbot, widget)
    return widget


def test_crop_moves_and_splits_at_original_pixel_scale_and_persists(window, qtbot, tmp_path):
    record = window._record()
    source = window._detail_renderer._source
    assert record.is_exported
    window.preview.set_zoom(500)
    window.settings.set_crop((100, 50, 900, 450))
    idle(qtbot, window)
    assert record.status == "staging" and record.checked
    assert window.preview.zoom_percent == 100
    assert window._detail_renderer._source is source
    geometry = window.preview._geometry
    assert geometry.original_size == (1000, 500)
    assert geometry.source_box == (100, 50, 900, 450)
    assert geometry.canvas_size == (800, 800)
    assert geometry.retained_percentage == 64
    assert window.store.load().records[0].settings.crop_box == (100, 50, 900, 450)
    assert record.settings.offset_x == .37 and record.settings.offset_y == -.4
    window._mouse_offsets(-.25, .65)
    idle(qtbot, window)
    left, top, right, bottom = window.preview._geometry.foreground_box
    assert (right - left, bottom - top) == (800, 400)
    point = window.preview._mapped(window.preview._scene()[1]).topLeft() + QPointF(5, 5)
    assert window.preview._sample(point).name().upper() == "#20A040"
    window.settings.split_button.click()
    idle(qtbot, window)
    assert window.preview._geometry.canvas_size == (800, 400)
    output = tmp_path / "export"
    output.mkdir()
    window.start_export(str(output))
    idle(qtbot, window)
    assert record.is_exported
    paths = sorted(output.glob("*.jpg"))
    assert len(paths) == 2
    for path, expected in zip(paths, ((32, 160, 64), (32, 64, 192)), strict=True):
        with Image.open(path) as tile:
            assert tile.size == (400, 400)
            assert tile.getpixel((10, 10)) == pytest.approx(expected, abs=3)
    window.settings.reset_crop_button.click()
    idle(qtbot, window)
    assert record.settings.crop_box is None and record.status == "staging"
    assert window.store.load().records[0].settings.crop_box is None


def test_live_source_mapping_and_picker_use_crop_before_worker_returns(window):
    preview = window.preview
    settings = replace(window._record().settings, crop_box=(100, 50, 900, 450))
    preview.update_geometry(get_geometry((1000, 500), settings), settings)
    preview._detail = None
    preview.reset_view()
    foreground = preview._scene()[1]
    point = preview._mapped(foreground).topLeft() + QPointF(8, 8)
    assert preview._sample(point).name().upper() == "#20A040"
    capture = preview.grab().toImage()
    density = preview.devicePixelRatioF()
    color = capture.pixelColor(round(point.x() * density), round(point.y() * density))
    assert color.name().upper() == "#20A040"
    assert preview._source_rect().getRect() == (100, 50, 800, 400)


@pytest.mark.parametrize("cancel", [False, True])
def test_inline_handles_persist_revisions_and_compose_after_release(window, qtbot, cancel):
    original = replace(window._record().settings)
    preview = window.preview
    before_geometry = preview._geometry
    start = preview._crop_handle_positions(preview._crop_rect())["nw"].toPoint()
    scale = preview._mapping()[1]
    changes = []
    preview.cropChanged.connect(changes.append)
    first_revision = window._writer._revision
    QTest.mousePress(preview, Qt.MouseButton.LeftButton, pos=start)
    for x, y in ((50, 25), (100, 50)):
        delta = QPoint(round(x * scale), round(y * scale))
        QTest.mouseMove(preview, start + delta)
        assert preview.is_cropping
        assert preview._geometry == before_geometry
    assert len(changes) == 2
    assert window._writer._revision == first_revision + 2
    qtbot.waitUntil(lambda: window._writer.is_idle, timeout=10000)
    assert window.store.load().records[0].settings.crop_box == changes[-1]
    assert window._record().status == "staging"
    if cancel:
        QTest.keyClick(preview, Qt.Key.Key_Escape)
    QTest.mouseRelease(preview, Qt.MouseButton.LeftButton, pos=start + delta)
    idle(qtbot, window)
    assert not preview.is_cropping
    assert QApplication.activeModalWidget() is None
    if cancel:
        assert window._record().settings == original
        assert window._record().is_exported
    else:
        assert window._record().settings.crop_box == changes[-1]
        assert preview._geometry.source_box == changes[-1]
        assert preview.zoom_percent == 100
    assert window.store.load().records[0].settings == window._record().settings


def test_reset_crop_sits_directly_under_center_image(window):
    panel = window.settings
    layout = panel.controls.layout()
    assert layout.indexOf(panel.reset_crop_button) == layout.indexOf(panel.center_button) + 1
    assert panel.findChild(type(panel.reset_crop_button), "cropPhotoButton") is None


def test_release_keeps_original_visible_and_second_gesture_restores_it(window, qtbot):
    preview = window.preview
    original = replace(window._record().settings)
    start = preview._crop_handle_positions(preview._crop_rect())["se"].toPoint()
    scale = preview._mapping()[1]
    end = start - QPoint(round(800 * scale), round(400 * scale))
    QTest.mousePress(preview, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(preview, end)
    QTest.mouseRelease(preview, Qt.MouseButton.LeftButton, pos=end)
    idle(qtbot, window)
    crop = window._record().settings.crop_box
    assert crop is not None and crop[2] < 210 and crop[3] < 110
    entire = preview._mapped(preview._original_rect())
    assert preview._area().adjusted(-.001, -.001, .001, .001).contains(entire)
    assert preview.zoom_percent == 100
    assert window.store.load().records[0].settings.crop_box == crop
    start = preview._crop_handle_positions(preview._crop_rect())["se"].toPoint()
    end = entire.bottomRight().toPoint() + QPoint(1, 1)
    QTest.mousePress(preview, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(preview, end)
    QTest.mouseRelease(preview, Qt.MouseButton.LeftButton, pos=end)
    idle(qtbot, window)
    assert window._record().settings == original
    assert window.store.load().records[0].settings.crop_box is None


def test_cancel_restores_previous_export_failure_but_preserves_a_new_failure(window, qtbot):
    record = window._record()
    record.last_error, record.failure_stage = "original export error", "export"
    window._mouse_crop((50, 25, 950, 475))
    assert record.last_error is None
    window._mouse_crop(None)
    window._crop_finished()
    idle(qtbot, window)
    assert record.last_error == "original export error" and record.status == "failed"
    window._mouse_crop((50, 25, 950, 475))
    record.last_error, record.failure_stage = "new export error", "export"
    window._mouse_crop(None)
    # Restoring via a setting also invalidates the export error. Simulate a
    # newly reported failure after that final change, before gesture completion.
    record.last_error, record.failure_stage = "new export error", "export"
    window._crop_finished()
    idle(qtbot, window)
    assert record.last_error == "new export error" and record.status == "failed"


def test_close_during_crop_keeps_current_geometry_when_final_save_fails(
    window, qtbot, monkeypatch,
):
    entered, release = Event(), Event()
    save = window.store.save

    def fail_save(snapshot):
        entered.set()
        release.wait(10)
        raise OSError("generated crop close failure")

    monkeypatch.setattr(window.store, "save", fail_save)
    preview = window.preview
    start = preview._crop_handle_positions(preview._crop_rect())["nw"].toPoint()
    try:
        QTest.mousePress(preview, Qt.MouseButton.LeftButton, pos=start)
        QTest.mouseMove(preview, start + QPoint(20, 15))
        qtbot.waitUntil(entered.is_set, timeout=10000)
        crop = window._record().settings.crop_box
        assert preview.is_cropping
        window.close()
        assert window._closing
        assert not preview.is_cropping
        assert preview._geometry.source_box == crop
    finally:
        release.set()
    qtbot.waitUntil(lambda: window._writer.is_idle and not window._closing, timeout=10000)
    assert window.isVisible() and window.isEnabled()
    assert preview._geometry.source_box == crop
    assert "generated crop close failure" in window.notice.text()
    monkeypatch.setattr(window.store, "save", save)
    window._persist(changed=window._record())
    idle(qtbot, window)
