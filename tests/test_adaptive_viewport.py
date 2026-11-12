"""Native viewport pixels remain useful across edits, pan and high DPI."""

from dataclasses import replace

import pytest
from PySide6.QtCore import QEvent, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from insta_g.core.geometry import get_geometry
from insta_g.core.models import Settings
from insta_g.gui.preview import PreviewWidget


def solid(width, height, color):
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(QColor(color))
    return image


class PhysicalViewport(PreviewWidget):
    density = 1.0

    def devicePixelRatioF(self):
        return self.density


@pytest.fixture
def preview(qtbot):
    widget = PhysicalViewport()
    qtbot.addWidget(widget)
    widget.resize(900, 600)
    settings = Settings(mode="expand", ratio_mode="fixed", ratio=1,
                        background_mode="solid", background_color="#204060")
    geometry = get_geometry((200, 100), settings)
    source = solid(200, 100, "#406080")
    background = solid(200, 200, "#204060")
    widget.set_image(background, 1, 1, source, geometry,
                     settings=settings, background=background)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


def pixel_at(preview, x, y):
    point = preview._mapped(QRectF(x, y, 0, 0)).topLeft().toPoint()
    return preview.grab().toImage().pixelColor(point).name().upper()


def test_fit_view_requests_native_pixels_immediately_after_selection(preview, qtbot):
    requests = []
    preview.detailRequested.connect(requests.append)
    preview._last_detail_request = None
    preview._schedule_detail()
    qtbot.waitUntil(lambda: bool(requests))
    assert preview.zoom_percent == 100
    assert requests[-1]["native_rect"] == (0, 0, 200, 200)
    assert requests[-1]["target_size"] == (504, 504)


def test_detail_uses_physical_viewport_above_2048_and_refreshes_dpi(preview):
    requests = []
    preview.detailRequested.connect(requests.append)
    preview.resize(1800, 1400)
    preview.density = 2.0
    QApplication.sendEvent(preview, QEvent(QEvent.Type.DevicePixelRatioChange))
    preview._request_detail()
    assert requests[-1]["target_size"] == (2608, 2608)
    assert preview._detail_timer.isActive()
    preview.density = 1.5
    QApplication.sendEvent(preview, QEvent(QEvent.Type.DevicePixelRatioChange))
    preview._request_detail()
    assert requests[-1]["target_size"] == (1956, 1956)


def test_same_image_composite_refresh_keeps_accepted_native_detail(preview):
    preview.set_detail(solid(504, 504, "#30A060"), (0, 0, 200, 200))
    accepted = preview._detail
    preview.set_image(solid(200, 200, "#204060"), 1, 1, solid(200, 100, "#406080"),
                      preview._geometry, settings=replace(preview._settings),
                      background=solid(200, 200, "#204060"))
    assert preview._detail is accepted
    assert preview._detail_state == "native"
    preview.clear()
    assert preview._detail is None
    assert preview._detail_geometry is None


def test_composite_can_reuse_existing_source_without_clearing_native_pixels(preview):
    preview.set_detail(solid(504, 504, "#30A060"), (0, 0, 200, 200))
    accepted = preview._detail
    settings = replace(preview._settings, offset_y=1)
    geometry = get_geometry((200, 100), settings)
    preview.update_geometry(geometry, settings)
    preview.set_image(solid(200, 200, "#204060"), 1, 1, geometry=geometry,
                      settings=settings, background=solid(200, 200, "#204060"))
    assert preview._detail is accepted
    assert not preview._pending_geometry
    assert pixel_at(preview, 60, 165) == "#30A060"


def test_old_viewport_does_not_claim_full_native_coverage_after_zoom(preview):
    preview.set_detail(solid(504, 504, "#30A060"), (0, 0, 200, 200))
    assert preview._detail_state == "native"
    preview.set_zoom(300)
    # A late result for the previous physical target remains reusable, but it
    # cannot claim to satisfy the newly enlarged viewport's sampling density.
    preview.set_detail(solid(504, 504, "#30A060"), (0, 0, 200, 200))
    assert preview._detail_state == "loading"


def test_same_image_refresh_preserves_explained_native_fallback(preview):
    preview.set_detail_status("reduced", "RAM budget")
    preview.set_image(solid(200, 200, "#204060"), 1, 1, solid(200, 100, "#406080"),
                      preview._geometry, settings=replace(preview._settings))
    assert preview._detail_state == "reduced"
    assert "RAM budget" in preview.toolTip()


def test_native_roi_includes_dimmed_original_outside_crop_frame(preview):
    settings = Settings(splits=2, ratio_mode="fixed", ratio=1, fit_mode="fill")
    geometry = get_geometry((400, 100), settings)
    preview.set_image(solid(200, 100, "#D00000"), 2, 1, solid(400, 100, "#D00000"),
                      geometry, settings=settings)
    requests = []
    preview.detailRequested.connect(requests.append)
    preview._request_detail()
    assert requests[-1]["native_rect"] == (-100, 0, 300, 100)
    preview.set_detail(solid(*requests[-1]["target_size"], "#20E060"),
                       requests[-1]["native_rect"])
    color = QColor(pixel_at(preview, -50, 65))
    assert color.green() > color.red() * 2
    assert color.green() < 100  # Cropped-off original retains its dim overlay.


def test_native_snapshot_moves_only_its_foreground_and_never_old_padding(preview):
    native = solid(200, 200, "#F020D0")
    painter = QPainter(native)
    painter.fillRect(0, 50, 200, 100, QColor("#20E060"))
    painter.end()
    preview.set_detail(native, (0, 0, 200, 200))
    snapshot = preview._detail
    settings = replace(preview._settings, offset_y=1)
    preview.update_geometry(get_geometry((200, 100), settings), settings)
    assert preview._detail is snapshot
    assert preview._pending_geometry
    assert pixel_at(preview, 60, 65) == "#204060"
    assert pixel_at(preview, 60, 165) == "#20E060"
    # A late worker result also carries its original settings; it must not put
    # the old image/background back in its former position.
    old_settings = replace(settings, offset_y=0)
    preview.set_detail(native, (0, 0, 200, 200),
                       geometry=get_geometry((200, 100), old_settings), settings=old_settings)
    assert pixel_at(preview, 60, 65) == "#204060"
    assert pixel_at(preview, 60, 165) == "#20E060"
    assert preview._detail_state == "loading"


def test_native_snapshot_survives_zoom_pan_and_return_to_fit(preview):
    preview.set_detail(solid(200, 200, "#20E060"), (0, 0, 200, 200))
    accepted = preview._detail
    preview.set_zoom(300)
    center = preview._area().center().toPoint()
    QTest.mousePress(preview, Qt.MouseButton.RightButton, pos=center)
    QTest.mouseMove(preview, center + QPointF(45, 20).toPoint())
    QTest.mouseRelease(preview, Qt.MouseButton.RightButton, pos=center + QPointF(45, 20).toPoint())
    assert preview._detail is accepted
    assert preview._pan == QPointF(45, 20)
    preview.set_zoom(100)
    assert preview._detail is accepted
    assert preview._pan.isNull()
    assert preview._detail_timer.isActive()


def test_continuous_edits_do_not_postpone_native_requests_until_release(preview, qtbot):
    preview._detail_timer.stop()
    requests = []
    preview.detailRequested.connect(requests.append)
    for step in range(20):
        settings = replace(preview._settings, offset_y=step / 20)
        preview.update_geometry(get_geometry((200, 100), settings), settings)
        qtbot.wait(6)
    assert len(requests) >= 2
    assert preview._pending_geometry
    assert all(request["target_size"][0] > 0 for request in requests)


def test_request_key_tracks_settings_even_when_roi_and_target_are_unchanged(preview):
    requests = []
    preview.detailRequested.connect(requests.append)
    preview._last_detail_request = None
    preview._request_detail()
    first = requests[-1]
    settings = replace(preview._settings, background_color="#B03080")
    preview.update_geometry(preview._geometry, settings)
    preview._request_detail()
    assert len(requests) == 2
    assert requests[-1] == first
    preview._request_detail()
    assert len(requests) == 2
