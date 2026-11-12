"""Right-button viewport gestures never alter per-photo export composition."""

from dataclasses import replace

import pytest
from PIL import Image
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtTest import QTest

from insta_g.core.geometry import get_geometry
from insta_g.core.models import ImageRecord, Settings
from insta_g.gui.preview import PreviewWidget
from insta_g.gui.window import MainWindow
from insta_g.persistence import Session, SessionStore


def image(width, height, color="#2468AB"):
    result = QImage(width, height, QImage.Format.Format_RGB32)
    result.fill(QColor(color))
    return result


@pytest.fixture
def preview(qtbot):
    widget = PreviewWidget()
    widget.resize(800, 500)
    qtbot.addWidget(widget)
    settings = Settings(splits=3, ratio_mode="fixed", ratio=1,
                        fit_mode="fill", offset_x=.37, offset_y=-.4)
    geometry = get_geometry((600, 100), settings)
    widget.set_image(image(*geometry.canvas_size), 3, 1, image(600, 100), geometry,
                     settings=settings)
    widget.set_offsets(settings.offset_x, settings.offset_y)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


@pytest.mark.parametrize("zoom", [100, 250])
def test_right_drag_pans_viewport_and_preserves_photo_geometry_and_settings(preview, zoom):
    preview.set_zoom(zoom)
    changed = []
    preview.offsetsChanged.connect(lambda *values: changed.append(values))
    settings = replace(preview._settings)
    geometry = preview._geometry
    origin, scale = preview._mapping()
    pan = QPointF(preview._pan)
    start = preview._area().center().toPoint()
    delta = QPoint(54, 31)
    QTest.mousePress(preview, Qt.MouseButton.RightButton, pos=start)
    QTest.mouseMove(preview, start + delta)
    QTest.mouseRelease(preview, Qt.MouseButton.RightButton, pos=start + delta)
    assert preview._pan == pan + QPointF(delta)
    after_origin, after_scale = preview._mapping()
    assert after_origin == origin + QPointF(delta)
    assert after_scale == scale
    assert preview._geometry == geometry
    assert preview._settings == settings
    assert preview._offsets == (settings.offset_x, settings.offset_y)
    assert preview.zoom_percent == zoom
    assert not changed
    assert preview._drag is None
    QTest.mouseMove(preview, start + delta + QPoint(40, 20))
    assert preview._pan == pan + QPointF(delta)


@pytest.mark.parametrize("zoom", [100, 250, 1000])
def test_right_double_click_matches_fit_view_and_preserves_photo(preview, zoom):
    preview.set_zoom(zoom)
    preview._pan = QPointF(71, -28)
    settings = replace(preview._settings)
    geometry = preview._geometry
    changes = []
    preview.offsetsChanged.connect(lambda *values: changes.append(values))
    point = preview._area().center().toPoint()
    # The real double-click sequence starts with a regular press/release.
    QTest.mouseClick(preview, Qt.MouseButton.RightButton, pos=point)
    QTest.mouseDClick(preview, Qt.MouseButton.RightButton, pos=point)
    QTest.mouseMove(preview, point + QPoint(25, 15))
    QTest.mouseRelease(preview, Qt.MouseButton.RightButton, pos=point)
    assert preview._pan.isNull()
    assert preview._settings == settings
    assert preview._geometry == geometry
    assert preview._offsets == (settings.offset_x, settings.offset_y)
    assert not changes
    assert preview.zoom_percent == 100
    assert preview._drag is None
    assert preview._drag_button == Qt.MouseButton.NoButton
    assert preview.zoom_slider.value() == preview.zoom_spin.value() == 100
    assert preview._area().adjusted(-.001, -.001, .001, .001).contains(
        preview._mapped(preview._scene()[2]))
    camera = (preview._mapping(), QPointF(preview._camera_center))
    preview.zoom_fit_button.click()
    assert (preview._mapping(), preview._camera_center) == camera


def test_right_pan_during_eyedropper_keeps_picker_armed_and_does_not_pick_color(preview):
    picked, changes = [], []
    preview.colorPicked.connect(picked.append)
    preview.offsetsChanged.connect(lambda *values: changes.append(values))
    preview.start_color_pick()
    point = preview._area().center().toPoint()
    delta = QPoint(45, 25)
    QTest.mousePress(preview, Qt.MouseButton.RightButton, pos=point)
    QTest.mouseMove(preview, point + delta)
    QTest.mouseRelease(preview, Qt.MouseButton.RightButton, pos=point + delta)
    assert preview._pan == QPointF(delta)
    assert preview._picking
    assert preview.cursor().shape() == Qt.CursorShape.CrossCursor
    assert not picked and not changes
    QTest.mouseDClick(preview, Qt.MouseButton.RightButton, pos=point)
    QTest.mouseRelease(preview, Qt.MouseButton.RightButton, pos=point)
    assert preview._pan.isNull() and preview.zoom_percent == 100
    assert preview._picking and preview.cursor().shape() == Qt.CursorShape.CrossCursor
    assert not picked and not changes
    # The following left click still picks after restoring the view.
    QTest.mouseClick(preview, Qt.MouseButton.LeftButton, pos=point + delta)
    assert picked == ["#2468AB"]
    assert not preview._picking
    assert not changes


def test_other_button_press_and_release_do_not_take_over_right_pan(preview):
    changes = []
    preview.offsetsChanged.connect(lambda *values: changes.append(values))
    before = replace(preview._settings)
    point = preview._area().center().toPoint()
    QTest.mousePress(preview, Qt.MouseButton.RightButton, pos=point)
    QTest.mouseMove(preview, point + QPoint(20, 10))
    QTest.mousePress(preview, Qt.MouseButton.LeftButton, pos=point + QPoint(20, 10))
    QTest.mouseRelease(preview, Qt.MouseButton.LeftButton, pos=point + QPoint(20, 10))
    QTest.mouseMove(preview, point + QPoint(55, 35))
    assert preview._pan == QPointF(55, 35)
    assert preview._drag is not None
    QTest.mouseRelease(preview, Qt.MouseButton.RightButton, pos=point + QPoint(55, 35))
    assert preview._drag is None
    assert preview._settings == before
    assert not changes


def test_escape_stops_right_pan_and_fit_recenters_view_without_changing_photo(preview):
    before = replace(preview._settings)
    point = preview._area().center().toPoint()
    QTest.mousePress(preview, Qt.MouseButton.RightButton, pos=point)
    QTest.mouseMove(preview, point + QPoint(50, 30))
    QTest.keyClick(preview, Qt.Key.Key_Escape)
    QTest.mouseMove(preview, point + QPoint(90, 60))
    QTest.mouseRelease(preview, Qt.MouseButton.RightButton, pos=point + QPoint(90, 60))
    assert preview._pan == QPointF(50, 30)
    assert preview._drag is None
    preview.set_zoom(100)
    assert preview._pan.isNull()
    assert preview._settings == before
    assert preview._area().adjusted(-.001, -.001, .001, .001).contains(
        preview._mapped(preview._scene()[2]))


def test_right_pan_is_suppressed_when_no_photo_is_loaded(qtbot):
    preview = PreviewWidget()
    qtbot.addWidget(preview)
    preview.resize(500, 400)
    preview.show()
    point = preview._area().center().toPoint()
    QTest.mousePress(preview, Qt.MouseButton.RightButton, pos=point)
    QTest.mouseMove(preview, point + QPoint(50, 30))
    QTest.mouseRelease(preview, Qt.MouseButton.RightButton, pos=point + QPoint(50, 30))
    assert preview._pan.isNull()
    assert preview._drag is None


@pytest.mark.parametrize("reset", [False, True])
def test_right_pan_preserves_real_session_bytes_and_successful_export(qtbot, tmp_path, monkeypatch, reset):
    path = tmp_path / "generated.png"
    Image.new("RGB", (600, 100), "#2468AB").save(path)
    settings = Settings(splits=3, ratio_mode="fixed", ratio=1, offset_x=.37, offset_y=-.4)
    record = ImageRecord(str(path), settings, exported_settings=settings.to_dict(), previewed=True)
    store = SessionStore(tmp_path / "session.json")
    store.save(Session([record], selected_path=record.path))
    window = MainWindow(store, store.load())

    def close_safely(widget):
        widget.close()
        qtbot.waitUntil(lambda: not widget._jobs and widget._writer.is_idle, timeout=15000)
        widget.close()

    qtbot.addWidget(window, before_close_func=close_safely)
    window.show()
    qtbot.waitUntil(lambda: window.preview._pixmap is not None and not window._jobs
                   and not window._preview_timer.isActive() and not window._preview_pending
                   and window._writer.is_idle, timeout=15000)
    current = window._record()
    before_record = current.to_dict()
    before_bytes = store.path.read_bytes()
    persist_calls = []
    monkeypatch.setattr(window, "_persist", lambda *args, **kwargs: persist_calls.append(True))
    preview = window.preview
    preview.set_zoom(250)
    start = preview._area().center().toPoint()
    initial_pan = QPointF(preview._pan)
    QTest.mousePress(preview, Qt.MouseButton.RightButton, pos=start)
    QTest.mouseMove(preview, start + QPoint(52, 34))
    QTest.mouseRelease(preview, Qt.MouseButton.RightButton, pos=start + QPoint(52, 34))
    if reset:
        QTest.mouseDClick(preview, Qt.MouseButton.RightButton, pos=start)
        QTest.mouseMove(preview, start + QPoint(25, 15))
        QTest.mouseRelease(preview, Qt.MouseButton.RightButton, pos=start)
    qtbot.waitUntil(lambda: not preview._detail_timer.isActive() and not window._jobs
                   and window._writer.is_idle, timeout=15000)
    assert preview._pan == (QPointF() if reset else initial_pan + QPointF(52, 34))
    assert preview.zoom_percent == (100 if reset else 250)
    assert current.to_dict() == before_record
    assert current.is_exported
    assert store.path.read_bytes() == before_bytes
    assert store.load().records[0].is_exported
    assert not persist_calls
