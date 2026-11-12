"""Immediate Qt composition paints use current geometry and cached SDR pixels."""

from dataclasses import replace

import pytest
from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from insta_g.core.geometry import get_geometry
from insta_g.core.models import Settings
from insta_g.gui.preview import PreviewWidget
from insta_g.gui.widgets import SettingsPanel
from insta_g.i18n import get_language, set_language, tr


def solid(width, height, color):
    value = QImage(width, height, QImage.Format.Format_RGB32)
    value.fill(QColor(color))
    return value


def bands():
    source = solid(400, 100, "red")
    painter = QPainter(source)
    for index, color in enumerate(("#C02020", "#20A040", "#2040D0", "#D0A020")):
        painter.fillRect(index * 100, 0, 100, 100, QColor(color))
    painter.end()
    return source


@pytest.fixture
def preview(qtbot):
    widget = PreviewWidget()
    widget.resize(800, 500)
    qtbot.addWidget(widget)
    settings = Settings(splits=2, ratio_mode="fixed", ratio=1, fit_mode="fill")
    geometry = get_geometry((400, 100), settings)
    source = bands()
    widget.set_image(source.copy(100, 0, 200, 100), 2, 1, source, geometry, settings=settings)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


def native_color(preview, x, y):
    point = preview._mapped(QRectF(x, y, 0, 0)).topLeft().toPoint()
    return preview.grab().toImage().pixelColor(point).name().upper()


def test_live_fill_geometry_moves_cached_pixels_without_replacing_base_raster(preview):
    assert native_color(preview, 20, 60) == "#20A040"
    original = preview._pixmap.cacheKey()
    cached_source = preview._source_pixmap.cacheKey()
    settings = replace(preview._settings, offset_x=-1)
    geometry = get_geometry((400, 100), settings)
    preview.update_geometry(geometry, settings)
    assert preview._geometry == geometry
    assert preview._pending_geometry
    assert preview._pixmap.cacheKey() == original
    assert preview._source_pixmap.cacheKey() == cached_source
    assert native_color(preview, 20, 60) == "#C02020"
    assert native_color(preview, 120, 60) == "#20A040"


def test_drag_paints_current_source_placement_before_any_worker_result(preview):
    before = preview._geometry
    center = preview._area().center().toPoint()
    QTest.mousePress(preview, Qt.MouseButton.LeftButton, pos=center)
    QTest.mouseMove(preview, center + QPoint(70, 0))
    assert preview._geometry.foreground_box != before.foreground_box
    assert preview._pending_geometry
    assert preview._settings.offset_x < 0
    QTest.mouseRelease(preview, Qt.MouseButton.LeftButton, pos=center + QPoint(70, 0))


def test_live_fit_uses_clean_cached_background_without_old_foreground_ghost(preview):
    source = solid(200, 100, "#C02020")
    background = solid(200, 200, "#20B0B0")
    composite = background.copy()
    painter = QPainter(composite)
    painter.drawImage(0, 50, source)
    painter.end()
    settings = Settings(mode="expand", ratio_mode="fixed", ratio=1)
    geometry = get_geometry((200, 100), settings)
    preview.set_image(composite, 1, 1, source, geometry, settings=settings, background=background)
    assert native_color(preview, 40, 65) == "#C02020"
    changed = replace(settings, offset_y=1)
    preview.update_geometry(get_geometry((200, 100), changed), changed)
    assert native_color(preview, 40, 65) == "#20B0B0"
    assert native_color(preview, 40, 165) == "#C02020"
    changed = replace(changed, background_mode="solid", background_color="#D04090")
    preview.update_geometry(get_geometry((200, 100), changed), changed)
    assert native_color(preview, 40, 65) == "#D04090"


def test_pending_geometry_requests_and_accepts_native_detail_before_new_composite(preview, qtbot):
    requests = []
    preview.detailRequested.connect(requests.append)
    preview.set_zoom(800)
    changed = replace(preview._settings, offset_x=-.5)
    geometry = get_geometry((400, 100), changed)
    preview.update_geometry(geometry, changed)
    preview._request_detail()
    assert requests and preview._detail_timer.isActive()
    preview.set_detail(solid(*requests[-1]["target_size"], "white"), requests[-1]["native_rect"])
    detail = preview._detail
    assert detail is not None
    preview.set_image(solid(200, 100, "red"), 2, 1, source=bands(),
                      geometry=geometry, settings=changed)
    assert not preview._pending_geometry
    assert preview._detail is detail
    assert preview._detail_state == "native"


def test_grid_only_geometry_update_preserves_ready_native_detail(preview):
    preview.set_zoom(300)
    visible = preview._visible_native_region()
    scale = preview._mapping()[1] * preview.devicePixelRatioF()
    preview.set_detail(solid(round(visible.width() * scale), round(visible.height() * scale), "white"),
                       (visible.left(), visible.top(), visible.right(), visible.bottom()))
    detail = preview._detail
    settings = replace(preview._settings, grid="golden")
    preview.update_geometry(preview._geometry, settings)
    assert preview._detail is detail
    assert preview._detail_state == "native"
    assert not preview._pending_geometry
    assert preview._grid == "golden"


@pytest.mark.parametrize("control", ["wheel", "slider", "spin", "button", "direct"])
def test_every_zoom_out_route_centers_fit_at_100_percent(preview, control):
    preview.set_zoom(101 if control == "wheel" else 250)
    preview._pan = QPointF(135, 42)
    if control == "slider":
        preview.zoom_slider.setValue(100)
    elif control == "spin":
        preview.zoom_spin.setValue(100)
    elif control == "button":
        for _ in range(8):
            preview.zoom_out_button.click()
    elif control == "wheel":
        point = QPointF(600, 300)
        event = QWheelEvent(point, preview.mapToGlobal(point.toPoint()), QPoint(), QPoint(0, -120),
                            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                            Qt.ScrollPhase.NoScrollPhase, False)
        QApplication.sendEvent(preview, event)
    else:
        preview.set_zoom(100, QPointF(600, 300))
    assert preview.zoom_percent == 100
    assert preview._pan.isNull()
    assert preview._mapped(preview._scene()[0]).center() == preview._area().center()
    assert preview._detail_timer.isActive()


@pytest.mark.parametrize("language,heading,none", [
    ("en", "Composition", "None"), ("sk", "Kompozícia", "Žiadna"),
    ("cs", "Kompozice", "Žádná"),
])
def test_composition_controls_have_new_order_and_descriptive_accessibility(
    qtbot, language, heading, none,
):
    previous = get_language()
    try:
        set_language(language)
        panel = SettingsPanel()
        qtbot.addWidget(panel)
        panel.set_record(Settings())
        assert panel.composition_label.text() == heading
        assert [button.text() for button in panel.grid_buttons] == [none, "2×2", "3×3", "φ", "X"]
        assert [button.objectName() for button in panel.grid_buttons] == [
            "grid_none", "grid_center", "grid_thirds", "grid_golden", "grid_diagonal",
        ]
        for button, mode in zip(panel.grid_buttons, ("none", "center", "thirds", "golden", "diagonal")):
            assert button.toolTip() and button.accessibleName() == button.toolTip()
            button.click()
            assert panel._settings.grid == mode
        panel.set_record(Settings(grid="center"))
        assert panel.grid_buttons[1].isChecked()
    finally:
        set_language(previous)


def test_detail_status_caption_tooltip_is_translated_and_does_not_affect_geometry(preview):
    previous = get_language()
    settings = replace(preview._settings)
    try:
        set_language("sk")
        for state, expected in (("loading", "Načítavam detail…"), ("native", "Detail z originálu"),
                                ("reduced", "Zmenšený náhľad")):
            preview.set_detail_status(state)
            assert preview.toolTip() == expected
            assert preview.accessibleDescription() == expected
        preview.set_detail_status("reduced", "RAM budget")
        assert preview.toolTip() == tr("Reduced preview — {reason}", reason="RAM budget")
        assert preview._settings == settings
    finally:
        set_language(previous)


@pytest.mark.parametrize("offset", [-1., 1.])
def test_fit_view_encloses_off_center_original_and_canvas_after_zoom_out(preview, offset):
    settings = Settings(splits=3, ratio_mode="fixed", ratio=1, fit_mode="fill", offset_x=offset)
    geometry = get_geometry((1600, 400), settings)
    preview.set_image(solid(1200, 400, "red"), 3, 1, solid(1600, 400, "red"), geometry,
                      settings=settings)
    preview.resize(1100, 650)
    assert preview._area().adjusted(-.01, -.01, .01, .01).contains(preview._mapped(preview._scene()[2]))
    preview.set_zoom(400, QPointF(700, 250))
    preview._pan += QPointF(160, 80)
    preview.set_zoom(100, QPointF(700, 250))
    assert preview._pan.isNull()
    assert preview._area().adjusted(-.01, -.01, .01, .01).contains(preview._mapped(preview._scene()[2]))


def test_offset_drag_holds_camera_but_aspect_change_at_fit_recenters_canvas(preview):
    original_center = QPointF(preview._camera_center)
    frame_center = preview._mapped(preview._scene()[0]).center()
    changed = replace(preview._settings, offset_x=-1)
    preview.update_geometry(get_geometry((400, 100), changed), changed)
    assert preview._camera_center == original_center
    assert preview._mapped(preview._scene()[0]).center() == frame_center
    changed = replace(changed, mode="expand", ratio=3 / 4)
    preview.update_geometry(get_geometry((400, 100), changed), changed)
    assert preview._mapped(preview._scene()[0]).center() == preview._area().center()


def test_picker_uses_live_solid_and_clean_background_during_pending_geometry(preview):
    settings = Settings(mode="expand", ratio_mode="fixed", ratio=1, offset_y=1,
                        background_mode="solid", background_color="#D04090")
    geometry = get_geometry((200, 100), settings)
    preview.set_image(solid(200, 200, "red"), 1, 1, solid(200, 100, "red"),
                      get_geometry((200, 100), replace(settings, offset_y=0)),
                      settings=replace(settings, offset_y=0), background=solid(200, 200, "#20B0B0"))
    preview.update_geometry(geometry, settings)
    point = preview._mapped(QRectF(40, 65, 0, 0)).topLeft()
    assert preview._sample(point).name().upper() == "#D04090"
    settings = replace(settings, background_mode="blur")
    preview.update_geometry(geometry, settings)
    assert preview._sample(point).name().upper() == "#20B0B0"
