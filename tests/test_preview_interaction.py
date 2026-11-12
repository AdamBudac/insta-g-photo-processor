"""Real Qt gestures exercise view-only zoom, source placement and colours."""

from dataclasses import replace

import pytest
from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QColorDialog

from insta_g.core.geometry import get_geometry
from insta_g.core.models import Settings
from insta_g.gui.preview import GRID_MODES, PreviewWidget, grid_lines
from insta_g.gui.widgets import SettingsPanel


def image(width, height, color="#304050"):
    value = QImage(width, height, QImage.Format.Format_RGB32)
    value.fill(QColor(color))
    return value


@pytest.fixture
def preview(qtbot):
    widget = PreviewWidget()
    widget.resize(800, 500)
    qtbot.addWidget(widget)
    settings = Settings(splits=3, ratio_mode="fixed", ratio=1, fit_mode="fill")
    geometry = get_geometry((600, 100), settings)
    widget.set_image(image(*geometry.canvas_size), 3, 1, image(600, 100), geometry)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


def test_drag_uses_native_margin_and_does_not_move_zero_margin_axis(preview, qtbot):
    changes = []
    preview.offsetsChanged.connect(lambda x, y: changes.append((x, y)))
    center = preview._mapped(preview._scene()[0]).center().toPoint()
    scale = preview._mapping()[1]
    QTest.mousePress(preview, Qt.MouseButton.LeftButton, pos=center)
    QTest.mouseMove(preview, center + QPoint(60, 35))
    QTest.mouseRelease(preview, Qt.MouseButton.LeftButton, pos=center + QPoint(60, 35))
    assert changes[-1][0] == pytest.approx(2 * 60 / (scale * -300))
    assert changes[-1][1] == 0
    assert preview.zoom_percent == 100
    assert preview._geometry.canvas_size == (300, 100)


def test_drag_clamps_and_double_click_centers_without_resetting_zoom(preview):
    preview.set_zoom(250)
    changes = []
    preview.offsetsChanged.connect(lambda x, y: changes.append((x, y)))
    center = preview._area().center().toPoint()
    QTest.mousePress(preview, Qt.MouseButton.LeftButton, pos=center)
    QTest.mouseMove(preview, center + QPoint(2000, 0))
    QTest.mouseRelease(preview, Qt.MouseButton.LeftButton, pos=center + QPoint(2000, 0))
    assert changes[-1] == (-1, 0)
    QTest.mouseDClick(preview, Qt.MouseButton.LeftButton, pos=center)
    assert changes[-1] == (0, 0)
    assert preview.zoom_percent == 250


def test_fit_drag_moves_source_within_padding_and_preserves_unavailable_axis(preview):
    geometry = get_geometry((100, 50), Settings(mode="expand", ratio_mode="fixed", ratio=1))
    preview.set_image(image(100, 100), 1, 1, image(100, 50), geometry)
    preview.set_offsets(.4, 0)
    changes = []
    preview.offsetsChanged.connect(lambda x, y: changes.append((x, y)))
    center = preview._mapped(preview._scene()[0]).center().toPoint()
    scale = preview._mapping()[1]
    QTest.mousePress(preview, Qt.MouseButton.LeftButton, pos=center)
    QTest.mouseMove(preview, center + QPoint(25, 30))
    QTest.mouseRelease(preview, Qt.MouseButton.LeftButton, pos=center + QPoint(25, 30))
    assert changes[-1] == pytest.approx((.4, 2 * 30 / (scale * 50)))


def test_wheel_preserves_native_pixel_under_cursor_and_zoom_limits(preview):
    anchor = QPointF(450, 200)
    origin, scale = preview._mapping()
    native = (anchor - origin) / scale
    event = QWheelEvent(anchor, preview.mapToGlobal(anchor.toPoint()), QPoint(), QPoint(0, 120),
                        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                        Qt.ScrollPhase.NoScrollPhase, False)
    QApplication.sendEvent(preview, event)
    assert preview.zoom_percent == pytest.approx(120)
    new_origin, new_scale = preview._mapping()
    assert (new_origin + native * new_scale - anchor).manhattanLength() < 0.001
    preview.set_zoom(10000)
    assert preview.zoom_slider.value() == preview.zoom_spin.value() == 1000
    preview.set_zoom(1)
    assert preview.zoom_percent == 100
    assert preview._geometry.canvas_size == (300, 100)


@pytest.mark.parametrize("space", [False, True])
def test_viewport_pan_does_not_emit_image_offsets(preview, space):
    changes = []
    preview.offsetsChanged.connect(lambda *values: changes.append(values))
    preview.set_zoom(200)
    center = preview._area().center().toPoint()
    if space:
        QTest.keyPress(preview, Qt.Key.Key_Space)
    button = Qt.MouseButton.LeftButton if space else Qt.MouseButton.MiddleButton
    QTest.mousePress(preview, button, pos=center)
    QTest.mouseMove(preview, center + QPoint(40, 25))
    QTest.mouseRelease(preview, button, pos=center + QPoint(40, 25))
    if space:
        QTest.keyRelease(preview, Qt.Key.Key_Space)
    assert preview._pan == QPointF(40, 25)
    assert not changes
    preview.zoom_fit_button.click()
    assert preview.zoom_percent == 100
    assert preview._pan.isNull()


def test_picker_samples_source_and_canvas_padding(preview):
    settings = Settings(mode="expand", ratio_mode="fixed", ratio=1)
    geometry = get_geometry((100, 50), settings)
    preview.set_image(image(100, 100, "#a1b2c3"), 1, 1,
                      image(100, 50, "#123456"), geometry)
    colors = []
    preview.colorPicked.connect(colors.append)
    preview.start_color_pick()
    source_point = preview._mapped(QRectF(40, 40, 1, 1)).center().toPoint()
    QTest.mouseClick(preview, Qt.MouseButton.LeftButton, pos=source_point)
    assert colors == ["#123456"]
    preview.start_color_pick()
    padding_point = preview._mapped(QRectF(10, 10, 1, 1)).center().toPoint()
    QTest.mouseClick(preview, Qt.MouseButton.LeftButton, pos=padding_point)
    assert colors[-1] == "#A1B2C3"
    preview.start_color_pick()
    QTest.keyClick(preview, Qt.Key.Key_Escape)
    QTest.mouseClick(preview, Qt.MouseButton.LeftButton, pos=padding_point)
    assert len(colors) == 2


def test_grid_geometry_covers_each_tile_and_has_exact_modes(preview):
    assert len(GRID_MODES) == 5
    rect = QRectF(100, 30, 180, 120)
    for mode, count in zip(GRID_MODES, (0, 4, 4, 2, 2)):
        lines = grid_lines(rect, mode)
        assert len(lines) == count
        assert all(rect.adjusted(-.001, -.001, .001, .001).contains(point)
                   for line in lines for point in (line.p1(), line.p2()))
    assert grid_lines(rect, "golden")[0].x1() == pytest.approx(100 + 180 * .38196601125)


def test_grid_is_clipped_to_output_and_drawn_over_padding(preview):
    geometry = get_geometry((100, 50), Settings(mode="expand", ratio_mode="fixed", ratio=1))
    preview.set_image(image(100, 100), 1, 1, image(100, 50), geometry)
    plain = preview.grab().toImage()
    preview.set_overlay_grid("thirds")
    overlaid = preview.grab().toImage()
    target = preview._mapped(preview._scene()[0])
    point = QPoint(round(target.left() + target.width() / 3), round(target.top() + 20))
    assert plain.pixelColor(point) != overlaid.pixelColor(point)
    outside = QPoint(point.x(), round(target.top() - 6))
    assert plain.pixelColor(outside) == overlaid.pixelColor(outside)


def test_grid_repeats_inside_each_carousel_tile(preview):
    plain = preview.grab().toImage()
    preview.set_overlay_grid("thirds")
    overlaid = preview.grab().toImage()
    target = preview._mapped(preview._scene()[0])
    tile_width = target.width() / 3
    for index in range(3):
        point = QPoint(round(target.left() + tile_width * (index + 1 / 3)),
                       round(target.top() + target.height() * .2))
        assert plain.pixelColor(point) != overlaid.pixelColor(point)


def test_detail_request_is_native_visible_roi_and_viewport_sized(preview, qtbot):
    requests = []
    preview.detailRequested.connect(requests.append)
    preview.set_zoom(800)
    qtbot.waitUntil(lambda: bool(requests))
    payload = requests[-1]
    left, top, right, bottom = payload["native_rect"]
    assert 0 <= left < right <= 300
    assert 0 <= top < bottom <= 100
    assert payload["target_size"] == (round(preview._area().width() * preview.devicePixelRatioF()),
                                      round(preview._area().height() * preview.devicePixelRatioF()))
    preview.set_detail(image(*payload["target_size"], "#ff0000"), payload["native_rect"])
    assert preview._detail is not None
    preview.set_image(image(300, 100), 3, 1, geometry=preview._geometry)
    assert preview._detail is None
    assert preview.zoom_percent == 800


@pytest.fixture
def panel(qtbot):
    widget = SettingsPanel()
    qtbot.addWidget(widget)
    widget.set_record(Settings(fit_mode="fit"))
    return widget


def test_background_palette_and_grid_preserve_other_photo_settings(panel, monkeypatch):
    saved = Settings(fit_mode="fit", grid="golden", offset_x=.234, background_color="#012345")
    panel.set_record(saved)
    changes = []
    panel.settingsChanged.connect(changes.append)
    panel.background_buttons[1].click()
    assert changes[-1] == replace(saved, background_mode="solid", background_color="#FFFFFF")
    assert not panel.blur.isEnabled()
    panel.set_dominant_colors(["#123456", "#ABCDEF"])
    assert [button.isEnabled() for button in panel.dominant_color_buttons] == [True, True, False, False, False]
    panel.dominant_color_buttons[1].click()
    assert changes[-1].background_color == "#ABCDEF"
    before = replace(panel._settings)
    monkeypatch.setattr(QColorDialog, "getColor", lambda *args: QColor())
    panel.background_buttons[4].click()
    assert panel._settings == before
    assert len(changes) == 2
    panel.grid_buttons[4].click()
    assert changes[-1] == replace(before, grid="diagonal")


def test_hdr_controls_and_retained_percentage(panel):
    panel.set_hdr_info({"is_hdr": False})
    assert not panel.hdr_button.isEnabled()
    assert panel._settings.hdr_mode == "sdr"
    panel.set_hdr_info({"is_hdr": True, "supported": True})
    panel.hdr_button.click()
    assert panel._settings.hdr_mode == "hdr"
    panel.set_hdr_info({"is_hdr": True, "supported": False, "error": "unsupported"})
    assert not panel.hdr_button.isEnabled()
    assert panel._settings.hdr_mode == "hdr"
    panel.set_record(Settings(splits=3, ratio_mode="fixed", ratio=1, fit_mode="fit"))
    panel.set_geometry((600, 100))
    assert "100%" in panel.retained_label.text()
    panel.set_record(Settings(splits=3, ratio_mode="fixed", ratio=1, fit_mode="fill"))
    panel.set_geometry((600, 100))
    assert "50%" in panel.retained_label.text()


def test_eyedropper_request_and_custom_dialog_apply_rgb_color(panel, monkeypatch):
    requests = []
    changes = []
    panel.requestColorPick.connect(lambda: requests.append(True))
    panel.settingsChanged.connect(changes.append)
    panel.background_buttons[3].click()
    assert requests == [True]
    assert not changes
    calls = []

    def choose_color(initial, parent, title, options):
        calls.append(options)
        return QColor(17, 34, 51)

    monkeypatch.setattr(QColorDialog, "getColor", choose_color)
    panel.background_buttons[4].click()
    assert panel._settings.background_color == "#112233"
    assert panel._settings.background_mode == "solid"
    assert calls == [QColorDialog.ColorDialogOption.DontUseNativeDialog]
    assert len(changes) == 1
