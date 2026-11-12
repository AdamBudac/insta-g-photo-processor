"""Inline original-pixel crop handles coexist with composition and camera gestures."""

from dataclasses import replace

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFocusEvent, QImage, QMouseEvent, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from insta_g.core.geometry import get_geometry
from insta_g.core.models import Settings
from insta_g.gui.preview import PreviewWidget


def image(width, height, color="#426789"):
    result = QImage(width, height, QImage.Format.Format_RGB32)
    result.fill(QColor(color))
    return result


@pytest.fixture
def preview(qtbot):
    widget = PreviewWidget()
    widget.resize(1056, 596)
    qtbot.addWidget(widget)
    settings = Settings(splits=2, ratio_mode="fixed", ratio=1, fit_mode="fit")
    geometry = get_geometry((1000, 500), settings)
    widget.set_image(image(*geometry.canvas_size), geometry.count, geometry.ratio,
                     image(1000, 500), geometry, settings=settings)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


def handle(preview, name):
    return preview._crop_handle_positions(preview._crop_rect())[name].toPoint()


def drag(preview, start, delta, button=Qt.MouseButton.LeftButton):
    QTest.mousePress(preview, button, pos=start)
    QTest.mouseMove(preview, start + delta)
    QTest.mouseRelease(preview, button, pos=start + delta)


@pytest.mark.parametrize(("name", "delta", "expected"), [
    ("nw", QPoint(80, 40), (80, 40, 1000, 500)),
    ("ne", QPoint(-80, 40), (0, 40, 920, 500)),
    ("sw", QPoint(80, -40), (80, 0, 1000, 460)),
    ("se", QPoint(-80, -40), (0, 0, 920, 460)),
    ("w", QPoint(80, 40), (80, 0, 1000, 500)),
    ("e", QPoint(-80, 40), (0, 0, 920, 500)),
    ("n", QPoint(80, 40), (0, 40, 1000, 500)),
    ("s", QPoint(80, -40), (0, 0, 1000, 460)),
])
def test_eight_handles_crop_original_pixels_without_changing_offsets(preview, name, delta, expected):
    changes, offsets, finished = [], [], []
    preview.cropChanged.connect(changes.append)
    preview.offsetsChanged.connect(lambda *values: offsets.append(values))
    preview.cropFinished.connect(lambda: finished.append(preview.is_cropping))
    initial_geometry = preview._geometry
    drag(preview, handle(preview, name), delta)
    assert changes == [expected]
    assert finished == [False]
    assert not offsets
    assert not preview.is_cropping
    assert preview._geometry == initial_geometry  # MainWindow composes once after release.


def test_handle_on_fractional_viewport_boundary_remains_clickable(preview):
    preview.resize(2706, 1151)
    settings = Settings(splits=6, fit_mode="fill")
    geometry = get_geometry((5000, 1000), settings)
    preview.set_image(image(500, 100), geometry.count, geometry.ratio,
                      image(500, 100), geometry, settings=settings)
    start = preview._crop_handle_positions(preview._crop_rect())["nw"]
    # A mathematically exact viewport edge can round to 27.99999999999997.
    assert abs(start.x() - preview._area().left()) < .001
    assert preview._crop_handle_at(start) == "nw"
    end = start + QPointF(100, 100) * preview._mapping()[1]
    changes = []
    preview.cropChanged.connect(changes.append)
    for kind, point, button, buttons in (
        (QEvent.Type.MouseButtonPress, start, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton),
        (QEvent.Type.MouseMove, end, Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton),
        (QEvent.Type.MouseButtonRelease, end, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton),
    ):
        QApplication.sendEvent(preview, QMouseEvent(
            kind, point, QPointF(preview.mapToGlobal(point.toPoint())),
            button, buttons, Qt.KeyboardModifier.NoModifier,
        ))
    assert changes == [(100, 100, 5000, 1000)]


def test_active_crop_freezes_mapping_and_emits_each_distinct_revision(preview):
    changes = []
    preview.cropChanged.connect(changes.append)
    start = handle(preview, "nw")
    mapping = preview._mapping()
    QTest.mousePress(preview, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(preview, start + QPoint(100, 50))
    QTest.mouseMove(preview, start + QPoint(150, 70))
    QTest.mouseMove(preview, start + QPoint(150, 70))
    assert preview.is_cropping
    assert preview._mapping() == mapping
    assert changes == [(100, 50, 1000, 500), (150, 70, 1000, 500)]
    QTest.mouseRelease(preview, Qt.MouseButton.LeftButton, pos=start + QPoint(150, 70))
    assert len(changes) == 2


def test_reopening_crop_can_restore_pixels_outside_previous_crop(preview):
    settings = replace(preview._settings, crop_box=(100, 50, 900, 450))
    geometry = get_geometry((1000, 500), settings)
    preview.update_geometry(geometry, settings)
    preview.reset_view()
    changes = []
    preview.cropChanged.connect(changes.append)
    scale = preview._mapping()[1]
    drag(preview, handle(preview, "nw"), QPoint(round(-100 * scale), round(-50 * scale)))
    assert changes[-1] == (0, 0, 900, 450)


def test_restoring_full_original_emits_none(preview):
    settings = replace(preview._settings, crop_box=(0, 0, 800, 400))
    preview.update_geometry(get_geometry((1000, 500), settings), settings)
    preview.reset_view()
    changes = []
    preview.cropChanged.connect(changes.append)
    scale = preview._mapping()[1]
    drag(preview, handle(preview, "se"), QPoint(round(200 * scale), round(100 * scale)))
    assert changes[-1] is None


@pytest.mark.parametrize(("name", "delta", "expected"), [
    ("nw", QPoint(3000, 3000), (999, 499, 1000, 500)),
    ("se", QPoint(-3000, -3000), (0, 0, 1, 1)),
    ("nw", QPoint(-3000, -3000), None),
    ("se", QPoint(3000, 3000), None),
])
def test_crop_edges_are_clamped_to_original_and_minimum_one_pixel(preview, name, delta, expected):
    changes = []
    preview.cropChanged.connect(changes.append)
    drag(preview, handle(preview, name), delta)
    assert (changes[-1] if changes else None) == expected


def test_escape_restores_initial_crop_before_finishing(preview):
    changes, finished = [], []
    preview.cropChanged.connect(changes.append)
    preview.cropFinished.connect(lambda: finished.append(preview.is_cropping))
    start = handle(preview, "nw")
    QTest.mousePress(preview, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(preview, start + QPoint(100, 50))
    QTest.keyClick(preview, Qt.Key.Key_Escape)
    QTest.mouseRelease(preview, Qt.MouseButton.LeftButton, pos=start + QPoint(100, 50))
    assert changes == [(100, 50, 1000, 500), None]
    assert finished == [False]
    assert preview._geometry.source_box == (0, 0, 1000, 500)


def test_press_release_without_movement_does_not_change_crop(preview):
    changes = []
    preview.cropChanged.connect(changes.append)
    QTest.mouseClick(preview, Qt.MouseButton.LeftButton, pos=handle(preview, "nw"))
    assert not changes
    assert not preview.is_cropping


@pytest.mark.parametrize("button", [Qt.MouseButton.RightButton, Qt.MouseButton.MiddleButton])
def test_camera_pan_has_priority_at_crop_handles(preview, button):
    changes = []
    preview.cropChanged.connect(changes.append)
    drag(preview, handle(preview, "nw"), QPoint(50, 20), button)
    assert preview._pan == QPointF(50, 20)
    assert not changes


def test_space_left_pan_has_priority_at_crop_handles(preview):
    changes = []
    preview.cropChanged.connect(changes.append)
    QTest.keyPress(preview, Qt.Key.Key_Space)
    drag(preview, handle(preview, "nw"), QPoint(50, 20))
    QTest.keyRelease(preview, Qt.Key.Key_Space)
    assert preview._pan == QPointF(50, 20)
    assert not changes


def test_picker_has_priority_at_crop_handles(preview):
    crops, colors = [], []
    preview.cropChanged.connect(crops.append)
    preview.colorPicked.connect(colors.append)
    preview.start_color_pick()
    QTest.mouseClick(preview, Qt.MouseButton.LeftButton, pos=handle(preview, "nw"))
    assert colors == ["#426789"]
    assert not crops
    assert not preview.is_cropping


def test_image_interior_continues_to_move_composition(preview):
    settings = replace(preview._settings, fit_mode="fill", ratio=.75)
    preview.update_geometry(get_geometry((1000, 500), settings), settings)
    crops, offsets = [], []
    preview.cropChanged.connect(crops.append)
    preview.offsetsChanged.connect(lambda *values: offsets.append(values))
    start = preview._mapped(preview._scene()[0]).center().toPoint()
    drag(preview, start, QPoint(40, 20))
    assert offsets
    assert not crops


@pytest.mark.parametrize(("name", "cursor"), [
    ("nw", Qt.CursorShape.SizeFDiagCursor), ("ne", Qt.CursorShape.SizeBDiagCursor),
    ("w", Qt.CursorShape.SizeHorCursor), ("n", Qt.CursorShape.SizeVerCursor),
])
def test_hover_uses_directional_resize_cursor(preview, qtbot, name, cursor):
    point = QPointF(handle(preview, name))
    event = QMouseEvent(QEvent.Type.MouseMove, point, preview.mapToGlobal(point.toPoint()),
                        Qt.MouseButton.NoButton, Qt.MouseButton.NoButton,
                        Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(preview, event)
    assert preview.hasMouseTracking()
    assert preview.cursor().shape() == cursor


def test_native_results_and_requests_wait_until_crop_finishes(preview):
    requests = []
    preview.detailRequested.connect(requests.append)
    preview.set_detail(image(1000, 500), (0, 0, 1000, 500))
    detail = preview._detail
    start = handle(preview, "nw")
    QTest.mousePress(preview, Qt.MouseButton.LeftButton, pos=start)
    preview._request_detail()
    preview.set_detail(image(100, 100, "#FF0000"), (0, 0, 100, 100))
    assert not requests
    assert preview._detail is detail
    QTest.mouseRelease(preview, Qt.MouseButton.LeftButton, pos=start)
    preview._request_detail()
    assert requests


def test_focus_out_safely_finishes_and_clearing_does_not_emit_for_another_photo(preview):
    finished = []
    preview.cropFinished.connect(lambda: finished.append(True))
    start = handle(preview, "nw")
    QTest.mousePress(preview, Qt.MouseButton.LeftButton, pos=start)
    preview.focusOutEvent(QFocusEvent(QFocusEvent.Type.FocusOut))
    assert finished == [True]
    QTest.mousePress(preview, Qt.MouseButton.LeftButton, pos=start)
    assert preview.is_cropping
    preview.clear()
    QTest.mouseRelease(preview, Qt.MouseButton.LeftButton, pos=start)
    assert finished == [True]
    assert not preview.is_cropping


def test_crop_paints_unselected_original_pixels_and_keeps_handle_size_at_zoom(preview):
    settings = replace(preview._settings, crop_box=(100, 50, 900, 450))
    preview.update_geometry(get_geometry((1000, 500), settings), settings)
    preview.reset_view()
    start = handle(preview, "nw")
    QTest.mousePress(preview, Qt.MouseButton.LeftButton, pos=start)
    rect = preview._crop_rect()
    raster = preview.grab().toImage()
    point = QPoint(round(rect.left() + 25), round(rect.top() + 25))
    density = preview.devicePixelRatioF()
    assert raster.pixelColor(QPoint(round(point.x() * density), round(point.y() * density))) == QColor("#426789")
    QTest.mouseRelease(preview, Qt.MouseButton.LeftButton, pos=start)
    preview.set_zoom(200)
    rect = preview._crop_rect()
    positions = preview._crop_handle_positions(rect)
    assert len(positions) == 8
    assert positions["w"].y() == rect.center().y()


def crop_pixel(preview, raster, x, y):
    frozen = preview._crop_drag
    point = frozen.origin + QPointF(x, y) * frozen.scale
    density = preview.devicePixelRatioF()
    return raster.pixelColor(round(point.x() * density), round(point.y() * density))


def assert_dimmed(color, original, opacity=.25):
    background = QColor("#10131b")
    original = QColor(original)
    expected = tuple(round(old * (1 - opacity) + new * opacity)
                     for old, new in zip(background.getRgb()[:3], original.getRgb()[:3]))
    assert all(abs(channel - target) <= 1
               for channel, target in zip(color.getRgb()[:3], expected))


def original_rect(preview):
    geometry = preview._geometry
    left, top, _, _ = geometry.foreground_box
    source_left, source_top, _, _ = geometry.source_box
    return QRectF(left - source_left, top - source_top, *geometry.original_size)


@pytest.mark.parametrize("fit", ["fit", "fill"])
@pytest.mark.parametrize("box", [(0, 0, 100, 50), (300, 150, 700, 350)])
def test_fit_view_keeps_whole_original_after_crop(preview, fit, box):
    settings = replace(preview._settings, crop_box=box, fit_mode=fit)
    preview.update_geometry(get_geometry((1000, 500), settings), settings)
    preview.reset_view()
    entire = preview._mapped(original_rect(preview))
    assert preview._area().adjusted(-.001, -.001, .001, .001).contains(entire)
    assert preview._mapping()[1] == pytest.approx(1)


@pytest.mark.parametrize("name", ["nw", "ne", "sw", "se", "w", "e", "n", "s"])
def test_cropped_edge_restores_to_visible_original_in_one_gesture(preview, name):
    settings = replace(preview._settings, crop_box=(200, 100, 800, 400))
    preview.update_geometry(get_geometry((1000, 500), settings), settings)
    preview.reset_view()
    original = preview._mapped(original_rect(preview))
    destination = preview._crop_handle_positions(original)[name]
    assert preview._area().adjusted(-.001, -.001, .001, .001).contains(destination)
    changes = []
    preview.cropChanged.connect(changes.append)
    start = handle(preview, name)
    drag(preview, start, destination.toPoint() - start)
    assert changes[-1] == (
        0 if "w" in name else 200, 0 if "n" in name else 100,
        1000 if "e" in name else 800, 500 if "s" in name else 400,
    )


@pytest.mark.parametrize("pending", [False, True])
def test_discarded_original_stays_dimmed_after_release_even_over_padding(preview, pending):
    settings = replace(preview._settings, mode="expand", ratio=1,
                       crop_box=(100, 50, 900, 450))
    geometry = get_geometry((1000, 500), settings)
    preview.set_image(image(*geometry.canvas_size, "#F0B020"), geometry.count, geometry.ratio,
                      geometry=geometry, settings=settings)
    if pending:
        settings = replace(settings, background_color="#FFFFFF")
        preview.update_geometry(geometry, settings)
    preview.reset_view()
    raster = preview.grab().toImage()
    original = original_rect(preview)
    density = preview.devicePixelRatioF()
    for x, y in ((50, 250), (950, 250), (300, 25), (300, 475)):
        point = preview._mapped(original).topLeft() + QPointF(x, y) * preview._mapping()[1]
        color = raster.pixelColor(round(point.x() * density), round(point.y() * density))
        assert_dimmed(color, "#426789")
        assert preview._sample(point) == QColor("#426789")


def test_discarded_pixels_reuse_previous_native_original_without_its_padding(preview):
    native = image(1200, 700, "#FF00FF")
    painter = QPainter(native)
    painter.fillRect(100, 100, 1000, 500, QColor("#1ADE44"))
    painter.end()
    preview.set_detail(native, (-100, -100, 1100, 600))
    settings = replace(preview._settings, mode="expand", ratio=1,
                       crop_box=(100, 50, 900, 450))
    preview.update_geometry(get_geometry((1000, 500), settings), settings)
    preview.reset_view()
    raster = preview.grab().toImage()
    origin = preview._mapped(original_rect(preview)).topLeft()
    density = preview.devicePixelRatioF()
    for x, y in ((50, 250), (300, 25), (950, 250), (300, 475)):
        point = origin + QPointF(x, y) * preview._mapping()[1]
        color = raster.pixelColor(round(point.x() * density), round(point.y() * density))
        assert_dimmed(color, "#1ADE44")


def test_crop_keeps_accepted_native_foreground_and_dims_discarded_native_pixels(preview):
    # The reduced layer deliberately has a different colour. This detects
    # replacing native pixels with the source overview during a crop gesture.
    native = image(1200, 700, "#FF00FF")
    painter = QPainter(native)
    painter.fillRect(100, 100, 1000, 500, QColor("#1ADE44"))
    painter.end()
    preview.set_detail(native, (-100, -100, 1100, 600))
    requests = []
    preview.detailRequested.connect(requests.append)
    start = handle(preview, "nw")
    QTest.mousePress(preview, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(preview, start + QPoint(100, 50))
    raster = preview.grab().toImage()
    assert crop_pixel(preview, raster, 200, 100) == QColor("#1ADE44")
    assert_dimmed(crop_pixel(preview, raster, 50, 25), "#1ADE44")
    preview._request_detail()
    assert not requests
    QTest.mouseRelease(preview, Qt.MouseButton.LeftButton, pos=start + QPoint(100, 50))


def test_crop_maps_previous_native_crop_to_original_and_excludes_composite_background(preview):
    settings = replace(preview._settings, mode="expand", ratio=1,
                       crop_box=(100, 50, 900, 450))
    geometry = get_geometry((1000, 500), settings)
    preview.update_geometry(geometry, settings)
    preview.reset_view()
    native = image(*geometry.canvas_size, "#FF00FF")
    left, top, right, bottom = geometry.foreground_box
    painter = QPainter(native)
    painter.fillRect(QRectF(left, top, right - left, bottom - top), QColor("#1ADE44"))
    painter.end()
    preview.set_detail(native, (0, 0, *geometry.canvas_size))
    start = handle(preview, "nw")
    scale = preview._mapping()[1]
    delta = QPoint(round(-50 * scale), round(-25 * scale))
    QTest.mousePress(preview, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(preview, start + delta)
    raster = preview.grab().toImage()
    assert crop_pixel(preview, raster, 200, 100) == QColor("#1ADE44")
    # Newly revealed pixels are absent from this native foreground. Its old
    # magenta padding must never replace the original cache in those pixels.
    assert crop_pixel(preview, raster, 200, 35) == QColor("#426789")
    assert crop_pixel(preview, raster, 70, 150) == QColor("#426789")
    assert_dimmed(crop_pixel(preview, raster, 950, 470), "#426789")
    QTest.mouseRelease(preview, Qt.MouseButton.LeftButton, pos=start + delta)


@pytest.mark.parametrize("density", [1, 2])
def test_crop_reuses_partial_native_roi_using_its_original_geometry(preview, density):
    settings = replace(preview._settings, mode="expand", ratio=1,
                       crop_box=(100, 50, 900, 450), offset_y=-.5)
    geometry = get_geometry((1000, 500), settings)
    preview.update_geometry(geometry, settings)
    # The accepted region starts inside the photograph and ends inside it;
    # its physical pixels differ from original pixels by this test's density.
    left, top, _, _ = geometry.foreground_box
    rect = (left + 120, top + 20, left + 520, top + 220)
    native = image(400 * density, 200 * density, "#1ADE44")
    painter = QPainter(native)
    painter.fillRect(200 * density, 0, 200 * density, 200 * density, QColor("#1A44DE"))
    painter.end()
    preview.set_detail(native, rect)
    # Camera/image placement changed after the accepted native result. The
    # remembered source_box/foreground must determine its original pixels.
    settings = replace(settings, offset_y=.5)
    preview.update_geometry(get_geometry((1000, 500), settings), settings)
    preview.reset_view()
    start = handle(preview, "nw")
    scale = preview._mapping()[1]
    delta = QPoint(round(40 * scale), round(20 * scale))
    QTest.mousePress(preview, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(preview, start + delta)
    raster = preview.grab().toImage()
    assert crop_pixel(preview, raster, 250, 100) == QColor("#1ADE44")
    assert crop_pixel(preview, raster, 550, 100) == QColor("#1A44DE")
    assert crop_pixel(preview, raster, 200, 100) == QColor("#426789")
    QTest.mouseRelease(preview, Qt.MouseButton.LeftButton, pos=start + delta)
