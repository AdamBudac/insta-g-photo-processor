"""Interactive composition viewport. Zoom and panning never change export pixels."""

from __future__ import annotations

from dataclasses import dataclass, replace

from PySide6.QtCore import QEvent, QLineF, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QImage,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QSlider, QSpinBox, QWidget

from insta_g.core.geometry import Geometry, get_geometry
from insta_g.core.models import Settings
from insta_g.i18n import tr

GRID_MODES = ("none", "thirds", "golden", "diagonal", "center")


@dataclass
class _CropDrag:
    """Keep original-pixel coordinates stable until one handle is released."""

    handle: str
    start: QPointF
    origin: QPointF
    scale: float
    original_size: tuple[int, int]
    initial_box: tuple[int, int, int, int]
    box: tuple[int, int, int, int]


_CROP_CURSORS = {
    "nw": Qt.CursorShape.SizeFDiagCursor, "se": Qt.CursorShape.SizeFDiagCursor,
    "ne": Qt.CursorShape.SizeBDiagCursor, "sw": Qt.CursorShape.SizeBDiagCursor,
    "n": Qt.CursorShape.SizeVerCursor, "s": Qt.CursorShape.SizeVerCursor,
    "w": Qt.CursorShape.SizeHorCursor, "e": Qt.CursorShape.SizeHorCursor,
}


def grid_lines(rect: QRectF, mode: str) -> list[QLineF]:
    """Composition lines in one complete output tile, including padding."""
    if mode in ("thirds", "golden"):
        fractions = (1 / 3, 2 / 3) if mode == "thirds" else (0.38196601125, 0.61803398875)
        return [line for fraction in fractions for line in (
            QLineF(rect.left() + rect.width() * fraction, rect.top(),
                   rect.left() + rect.width() * fraction, rect.bottom()),
            QLineF(rect.left(), rect.top() + rect.height() * fraction,
                   rect.right(), rect.top() + rect.height() * fraction),
        )]
    if mode == "diagonal":
        return [QLineF(rect.topLeft(), rect.bottomRight()),
                QLineF(rect.topRight(), rect.bottomLeft())]
    if mode == "center":
        return [QLineF(rect.center().x(), rect.top(), rect.center().x(), rect.bottom()),
                QLineF(rect.left(), rect.center().y(), rect.right(), rect.center().y())]
    return []


class PreviewWidget(QWidget):
    offsetsChanged = Signal(float, float)
    colorPicked = Signal(str)
    zoomChanged = Signal(float)
    detailRequested = Signal(object)
    cropChanged = Signal(object)
    cropFinished = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("imagePreview")
        self.setMinimumSize(300, 300)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        self._pixmap: QPixmap | None = None
        self._source_pixmap: QPixmap | None = None
        self._geometry: Geometry | None = None
        self._settings: Settings | None = None
        self._background_pixmap: QPixmap | None = None
        self._pending_geometry = False
        self._detail_state = "reduced"
        self._detail_reason = ""
        self._detail: tuple[QPixmap, QRectF] | None = None
        self._detail_geometry: Geometry | None = None
        self._detail_settings: Settings | None = None
        self._count, self._ratio = 1, 1.0
        self._busy = False
        self._grid = "none"
        self._zoom = 100.0
        self._pan = QPointF()
        self._camera_center: QPointF | None = None
        self._offsets = (0.0, 0.0)
        self._drag: tuple[str, QPointF, object, float] | None = None
        self._drag_button = Qt.MouseButton.NoButton
        self._crop_drag: _CropDrag | None = None
        self._space = False
        self._picking = False
        self._last_detail_request: object = None
        self._detail_timer = QTimer(self)
        self._detail_timer.setSingleShot(True)
        self._detail_timer.setInterval(33)
        self._detail_timer.timeout.connect(self._request_detail)
        self.toolbar = QWidget(self)
        self.toolbar.setObjectName("previewZoomToolbar")
        row = QHBoxLayout(self.toolbar)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        self.zoom_fit_button = QPushButton()
        self.zoom_fit_button.setObjectName("zoomFitButton")
        self.zoom_fit_button.setMinimumWidth(0)
        self.zoom_fit_button.clicked.connect(self.reset_view)
        self.zoom_out_button = QPushButton("−")
        self.zoom_out_button.setObjectName("zoomOutButton")
        self.zoom_out_button.setFixedWidth(28)
        self.zoom_out_button.setStyleSheet("padding: 0; font-size: 18px;")
        self.zoom_out_button.clicked.connect(lambda: self.set_zoom(self._zoom / 1.2))
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setObjectName("zoomSlider")
        self.zoom_slider.setRange(100, 1000)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setMinimumWidth(35)
        self.zoom_slider.valueChanged.connect(self.set_zoom)
        self.zoom_spin = QSpinBox()
        self.zoom_spin.setObjectName("zoomSpin")
        self.zoom_spin.setRange(100, 1000)
        self.zoom_spin.setSuffix(" %")
        self.zoom_spin.setValue(100)
        self.zoom_spin.setFixedWidth(82)
        self.zoom_spin.valueChanged.connect(self.set_zoom)
        self.zoom_in_button = QPushButton("+")
        self.zoom_in_button.setObjectName("zoomInButton")
        self.zoom_in_button.setFixedWidth(28)
        self.zoom_in_button.setStyleSheet("padding: 0; font-size: 18px;")
        self.zoom_in_button.clicked.connect(lambda: self.set_zoom(self._zoom * 1.2))
        for control in (self.zoom_fit_button, self.zoom_out_button, self.zoom_slider,
                        self.zoom_spin, self.zoom_in_button):
            row.addWidget(control, 1 if control is self.zoom_slider else 0)
        self.retranslate_ui()

    @property
    def zoom_percent(self) -> float:
        return self._zoom

    @property
    def is_cropping(self) -> bool:
        return self._crop_drag is not None

    def retranslate_ui(self) -> None:
        self.zoom_fit_button.setText(tr("Fit view"))
        self.zoom_fit_button.setToolTip(tr("Fit view"))
        self.zoom_out_button.setToolTip(tr("Zoom out"))
        self.zoom_in_button.setToolTip(tr("Zoom in"))
        self.zoom_slider.setToolTip(tr("Preview zoom"))
        self.zoom_spin.setToolTip(tr("Preview zoom"))
        self.setToolTip(self._detail_description())
        self.update()

    def set_image(self, image: QImage, count: int, ratio: float,
                  source: QImage | None = None, geometry: Geometry | None = None,
                  *, settings: Settings | None = None, background: QImage | None = None) -> None:
        if self.is_cropping:
            return
        known_source = (source is not None or
                        (settings is not None and self._source_pixmap is not None))
        same_frame = (known_source and geometry is not None and self._geometry == geometry
                      and (self._settings.export_dict() if self._settings is not None else None)
                      == (settings.export_dict() if settings is not None else None))
        previous_canvas_size = self._scene()[0].size()
        self._pixmap = QPixmap.fromImage(image)
        if source is not None:
            self._source_pixmap = QPixmap.fromImage(source)
        self._geometry = geometry
        self._settings = replace(settings) if settings is not None else None
        self._background_pixmap = QPixmap.fromImage(background) if background is not None else None
        self._pending_geometry = False
        if not known_source or geometry is None:
            # Legacy callers without a source cannot identify which photograph
            # a previous native snapshot belonged to. MainWindow clears on a
            # real photo switch. Its subsequent composites reuse the source
            # layer, so an omitted source with settings is the same photograph.
            self._detail = None
            self._detail_geometry = self._detail_settings = None
            self._last_detail_request = None
        self._count, self._ratio = count, ratio
        self._center_changed_canvas(previous_canvas_size)
        self._busy = False
        if self._detail is None and not same_frame:
            self.set_detail_status("reduced")
        elif self._detail is not None and not self._detail_is_current():
            self.set_detail_status("loading")
        if geometry is not None:
            left, top, right, bottom = geometry.foreground_box
            margins = (geometry.canvas_size[0] - (right - left),
                       geometry.canvas_size[1] - (bottom - top))
            self._offsets = tuple(max(-1., min(1., 2 * pos / margin - 1)) if margin else 0.
                                  for pos, margin in zip((left, top), margins))
        self._schedule_detail()
        self.update()

    def update_geometry(self, geometry: Geometry, settings: Settings) -> None:
        """Show current source placement immediately while a worker refines it.

        Qt immediately transforms the cached source and any accepted native
        foreground. A worker refines only the visible region. The separately
        cached background never contains an old foreground image.
        """
        if self.is_cropping:
            return
        if self._geometry == geometry and self._settings == settings:
            return
        if (self._geometry == geometry and self._settings is not None
                and self._settings.export_dict() == settings.export_dict()):
            self._settings = replace(settings)
            self._grid = settings.grid
            self.update()
            return
        previous_canvas_size = self._scene()[0].size()
        if self._geometry is not None and self._geometry.source_box != geometry.source_box:
            # A new input region has different pixels at the same canvas
            # coordinates. Its old background is not a usable live layer.
            self._background_pixmap = None
        self._geometry = geometry
        self._settings = replace(settings)
        self._count, self._ratio = geometry.count, geometry.ratio
        self._center_changed_canvas(previous_canvas_size)
        self._offsets = (settings.offset_x, settings.offset_y)
        self._grid = settings.grid
        self._pending_geometry = True
        if self._detail is not None:
            self.set_detail_status("loading")
        self._schedule_detail()
        self.update()

    def _detail_description(self) -> str:
        if self._detail_state == "native":
            return tr("Native detail")
        if self._detail_state == "loading":
            return tr("Loading detail…")
        if self._detail_reason:
            return tr("Reduced preview — {reason}", reason=tr(self._detail_reason))
        return tr("Reduced preview")

    def set_detail_status(self, state: str, reason: str = "") -> None:
        if state not in ("loading", "native", "reduced"):
            raise ValueError(f"Unknown preview detail state: {state}")
        self._detail_state, self._detail_reason = state, reason
        description = self._detail_description()
        self.setToolTip(description)
        self.setAccessibleDescription(description)
        self.update()

    def set_busy(self, busy: bool = True) -> None:
        self._busy = busy
        self.update()

    def clear(self) -> None:
        self._crop_drag = None
        self._pixmap = self._source_pixmap = None
        self._geometry = None
        self._settings = None
        self._background_pixmap = None
        self._pending_geometry = False
        self._camera_center = None
        self._detail = None
        self._detail_geometry = self._detail_settings = None
        self._last_detail_request = None
        self._busy = self._picking = False
        self._detail_timer.stop()
        self._drag = None
        self._drag_button = Qt.MouseButton.NoButton
        self.unsetCursor()
        self.reset_view()

    def set_overlay_grid(self, mode: str) -> None:
        if mode not in GRID_MODES:
            raise ValueError(f"Unknown composition grid: {mode}")
        self._grid = mode
        self.update()

    def set_offsets(self, x: float, y: float) -> None:
        self._offsets = (max(-1., min(1., x)), max(-1., min(1., y)))

    def reset_view(self) -> None:
        self._pan = QPointF()
        self.set_zoom(100)
        self.update()

    def _area(self) -> QRectF:
        return QRectF(self.rect().adjusted(28, 52, -28, -44))

    def _original_rect(self) -> QRectF:
        """The entire original in canvas coordinates, including discarded pixels."""
        if self._geometry is None:
            return QRectF()
        left, top, _, _ = self._geometry.foreground_box
        source_left, source_top, _, _ = self._geometry.source_box
        return QRectF(left - source_left, top - source_top, *self._geometry.original_size)

    def _original_mapping(self) -> tuple[QPointF, float]:
        if self._crop_drag is not None:
            return self._crop_drag.origin, self._crop_drag.scale
        origin, scale = self._mapping()
        return origin + self._original_rect().topLeft() * scale, scale

    def _scene(self) -> tuple[QRectF, QRectF, QRectF]:
        if self._geometry is not None:
            canvas = QRectF(0, 0, *self._geometry.canvas_size)
            left, top, right, bottom = self._geometry.foreground_box
            foreground = QRectF(left, top, right - left, bottom - top)
            return canvas, foreground, canvas.united(self._original_rect())
        canvas = QRectF(self._pixmap.rect()) if self._pixmap is not None else QRectF(0, 0, 1, 1)
        return canvas, canvas, canvas

    def _mapping(self) -> tuple[QPointF, float]:
        _, _, scene = self._scene()
        area = self._area()
        scale = max(0.000001, min(area.width() / scene.width(), area.height() / scene.height()))
        scale *= self._zoom / 100
        # The fit camera encloses both original and output. Offset-only changes
        # retain this camera, keeping the output frame still during a drag.
        center = area.center() + self._pan
        native_center = self._camera_center if self._camera_center is not None else scene.center()
        return center - native_center * scale, scale

    def _center_changed_canvas(self, previous_size: object) -> None:
        canvas, _, scene = self._scene()
        if self._camera_center is None or (self._zoom == 100 and canvas.size() != previous_size):
            self._camera_center = scene.center()
            self._pan = QPointF()

    def _mapped(self, rect: QRectF) -> QRectF:
        origin, scale = self._mapping()
        return QRectF(origin.x() + rect.x() * scale, origin.y() + rect.y() * scale,
                      rect.width() * scale, rect.height() * scale)

    def set_zoom(self, percent: float, anchor: QPointF | None = None) -> None:
        if self.is_cropping:
            return
        value = max(100., min(1000., float(percent)))
        if anchor is None:
            anchor = self._area().center()
        else:
            anchor = QPointF(anchor)
        origin, old_scale = self._mapping()
        native = (anchor - origin) / old_scale
        changed = abs(value - self._zoom) > 0.0001
        self._zoom = value
        if value == 100:
            self._pan = QPointF()
            self._camera_center = (self._scene()[2].center()
                                   if self._pixmap is not None or self._geometry is not None else None)
        else:
            new_origin, new_scale = self._mapping()
            self._pan += anchor - (new_origin + native * new_scale)
        for control in (self.zoom_slider, self.zoom_spin):
            blocked = control.blockSignals(True)
            control.setValue(round(value))
            control.blockSignals(blocked)
        if changed:
            self.zoomChanged.emit(value)
        self._schedule_detail()
        self.update()

    def wheelEvent(self, event: object) -> None:
        if self.is_cropping:
            event.accept()
            return
        if self._pixmap is None:
            return
        delta = event.angleDelta().y() or event.pixelDelta().y()
        self.set_zoom(self._zoom * 1.2 ** (delta / 120), event.position())
        event.accept()

    def start_color_pick(self) -> None:
        if self._pixmap is not None:
            self._picking = True
            self.setFocus()
            self.setCursor(Qt.CursorShape.CrossCursor)

    def _sample(self, position: QPointF) -> QColor | None:
        origin, scale = self._mapping()
        native = (position - origin) / scale
        canvas, foreground, _ = self._scene()
        original = self._original_rect() if self._geometry is not None else foreground
        if self._source_pixmap is not None and original.contains(native):
            image = self._source_pixmap.toImage()
            x = (native.x() - original.left()) / original.width() * image.width()
            y = (native.y() - original.top()) / original.height() * image.height()
        elif self._pixmap is not None and canvas.contains(native):
            if self._pending_geometry and self._settings is not None:
                if self._settings.background_mode == "solid":
                    return QColor(self._settings.background_color)
                if self._background_pixmap is not None:
                    image = self._background_pixmap.toImage()
                    x = native.x() / canvas.width() * image.width()
                    y = native.y() / canvas.height() * image.height()
                elif self._source_pixmap is not None:
                    image = self._source_pixmap.toImage()
                    cover = self._source_cover_rect(canvas.width() / canvas.height())
                    x = cover.left() + native.x() / canvas.width() * cover.width()
                    y = cover.top() + native.y() / canvas.height() * cover.height()
                else:
                    return None
            else:
                image = self._pixmap.toImage()
                x = native.x() / canvas.width() * image.width()
                y = native.y() / canvas.height() * image.height()
        else:
            return None
        return image.pixelColor(min(image.width() - 1, max(0, int(x))),
                                min(image.height() - 1, max(0, int(y))))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.setFocus()
        if self._drag is not None or self.is_cropping:
            event.accept()
            return
        if self._picking and event.button() == Qt.MouseButton.LeftButton:
            color = self._sample(event.position())
            if color is not None:
                self._picking = False
                self.unsetCursor()
                self.colorPicked.emit(color.name().upper())
            event.accept()
            return
        if self._pixmap is None:
            return
        if event.button() in (Qt.MouseButton.RightButton, Qt.MouseButton.MiddleButton) or (
            event.button() == Qt.MouseButton.LeftButton and self._space
        ):
            self._drag = ("pan", event.position(), QPointF(self._pan), self._mapping()[1])
            self._drag_button = event.button()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.LeftButton and self._geometry is not None:
            handle = self._crop_handle_at(event.position())
            if handle is not None:
                origin, scale = self._original_mapping()
                self._crop_drag = _CropDrag(
                    handle, QPointF(event.position()), origin,
                    scale, self._geometry.original_size,
                    self._geometry.source_box, self._geometry.source_box,
                )
                self._detail_timer.stop()
                self.setCursor(_CROP_CURSORS[handle])
                self.update()
                event.accept()
                return
            canvas, foreground, _ = self._scene()
            if self._mapped(canvas.united(foreground)).contains(event.position()):
                self._drag = ("image", event.position(), self._offsets, self._mapping()[1])
                self._drag_button = event.button()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._crop_drag is not None:
            self._move_crop(event.position())
            event.accept()
            return
        if self._drag is None:
            self._update_hover_cursor(event.position())
            return
        mode, start, initial, scale = self._drag
        delta = event.position() - start
        if mode == "pan":
            self._pan = initial + delta
            self._schedule_detail()
        elif self._geometry is not None:
            canvas, foreground, _ = self._scene()
            margins = (canvas.width() - foreground.width(), canvas.height() - foreground.height())
            values = tuple(max(-1., min(1., old + 2 * distance / (scale * margin)))
                           if margin else old for old, distance, margin
                           in zip(initial, (delta.x(), delta.y()), margins))
            if values != self._offsets:
                self._offsets = values
                self._show_offsets(*values)
                self.offsetsChanged.emit(*values)
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._crop_drag is not None:
            if event.button() == Qt.MouseButton.LeftButton:
                self._move_crop(event.position())
                self._finish_crop()
            event.accept()
            return
        if self._drag is not None:
            if event.button() != self._drag_button:
                event.accept()
                return
            self.mouseMoveEvent(event)
            self._end_drag()
            event.accept()

    def _end_drag(self) -> None:
        self._drag = None
        self._drag_button = Qt.MouseButton.NoButton
        if self._picking:
            self.setCursor(Qt.CursorShape.CrossCursor)
        elif self._space:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.unsetCursor()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if self.is_cropping:
            event.accept()
            return
        if event.button() == Qt.MouseButton.RightButton:
            self._end_drag()
            self.reset_view()
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton and self._geometry is not None and not self._picking:
            self._drag = None
            self._drag_button = Qt.MouseButton.NoButton
            self._offsets = (0., 0.)
            self._show_offsets(0., 0.)
            self.offsetsChanged.emit(0., 0.)
            event.accept()

    def _show_offsets(self, x: float, y: float) -> None:
        if self._settings is None or self._geometry is None:
            return
        settings = replace(self._settings, offset_x=x, offset_y=y)
        self.update_geometry(get_geometry(self._geometry.original_size, settings), settings)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Space:
            self._space = True
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
        elif event.key() == Qt.Key.Key_Escape:
            if self._crop_drag is not None:
                initial = self._crop_drag.initial_box
                if self._crop_drag.box != initial:
                    self._crop_drag.box = initial
                    self.cropChanged.emit(self._canonical_crop(initial))
                self._finish_crop()
            self._picking = False
            self._drag = None
            self._drag_button = Qt.MouseButton.NoButton
            self.unsetCursor()
            event.accept()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Space:
            self._space = False
            if not self._picking:
                self.unsetCursor()
            event.accept()
        else:
            super().keyReleaseEvent(event)

    def focusOutEvent(self, event: object) -> None:
        self._finish_crop()
        self._space = False
        self._drag = None
        self._drag_button = Qt.MouseButton.NoButton
        if not self._picking:
            self.unsetCursor()
        super().focusOutEvent(event)

    def resizeEvent(self, event: object) -> None:
        self.toolbar.setGeometry(12, 8, max(0, self.width() - 24), 32)
        self._schedule_detail()
        super().resizeEvent(event)

    def event(self, event: QEvent) -> bool:
        # Moving a window between monitors may change physical pixel density
        # without changing its logical QWidget size.
        if (event.type() == QEvent.Type.DevicePixelRatioChange
                and hasattr(self, "_detail_timer")):
            self._schedule_detail()
        return super().event(event)

    def _schedule_detail(self) -> None:
        if (not self.is_cropping and self._pixmap is not None and self._geometry is not None
                and not self._detail_timer.isActive()):
            # Throttle rather than debounce: a continuous gesture must still
            # request current native pixels, instead of postponing them forever.
            self._detail_timer.start()

    def _visible_native_region(self) -> QRectF:
        area = self._area()
        if area.isEmpty():
            return QRectF()
        origin, scale = self._mapping()
        return QRectF((area.topLeft() - origin) / scale,
                      (area.bottomRight() - origin) / scale).intersected(self._scene()[2])

    def _request_detail(self) -> None:
        if self.is_cropping or self._pixmap is None or self._geometry is None:
            return
        visible = self._visible_native_region()
        if visible.isEmpty():
            return
        scale = self._mapping()[1]
        rect = (visible.left(), visible.top(), visible.right(), visible.bottom())
        density = max(1., self.devicePixelRatioF())
        width, height = visible.width() * scale * density, visible.height() * scale * density
        target = (max(1, round(width)), max(1, round(height)))
        settings_key = (tuple(self._settings.export_dict().items())
                        if self._settings is not None else None)
        key = (self._geometry, settings_key, tuple(round(v, 4) for v in rect), target, density)
        if key != self._last_detail_request:
            self._last_detail_request = key
            self.set_detail_status("loading")
            self.detailRequested.emit({"native_rect": rect, "target_size": target})

    def set_detail(self, image: QImage, native_rect: tuple[float, float, float, float],
                   *, geometry: Geometry | None = None, settings: Settings | None = None) -> None:
        if self.is_cropping:
            return
        left, top, right, bottom = native_rect
        self._detail = (QPixmap.fromImage(image), QRectF(left, top, right - left, bottom - top))
        self._detail_geometry = geometry if geometry is not None else self._geometry
        snapshot_settings = settings if settings is not None else self._settings
        self._detail_settings = replace(snapshot_settings) if snapshot_settings is not None else None
        self.set_detail_status("native" if self._detail_covers_viewport() else "loading")
        self.update()

    def _detail_is_current(self) -> bool:
        if self._detail_geometry != self._geometry:
            return False
        old = self._detail_settings.export_dict() if self._detail_settings is not None else None
        current = self._settings.export_dict() if self._settings is not None else None
        return old == current

    def _detail_covers_viewport(self) -> bool:
        if self._detail is None or not self._detail_is_current():
            return False
        detail, native = self._detail
        visible = self._visible_native_region()
        if visible.isEmpty():
            return True
        if not native.adjusted(-.0001, -.0001, .0001, .0001).contains(visible):
            return False
        scale = self._mapping()[1] * max(1., self.devicePixelRatioF())
        # Rounding a physical target may lose half a pixel. A former fit raster
        # nevertheless must not claim complete native detail after zooming in.
        return (detail.width() + 1 >= native.width() * scale
                and detail.height() + 1 >= native.height() * scale)

    def _paint_detail(self, painter: QPainter, canvas: QRectF, foreground: QRectF) -> None:
        """Reuse old native foreground while the next visible region renders.

        A composite's old background cannot move with the photograph. Only the
        part known to lie inside its old foreground is mapped into the current
        foreground; the ordinary live background stays in canvas coordinates.
        """
        if self._detail is None:
            return
        if (self._detail_geometry is not None and self._geometry is not None
                and self._detail_geometry.source_box != self._geometry.source_box):
            return
        detail, native = self._detail
        if native.isEmpty():
            return
        current_snapshot = self._detail_is_current()
        destination, source = native, QRectF(detail.rect())
        if not current_snapshot and self._detail_geometry is not None:
            left, top, right, bottom = self._detail_geometry.foreground_box
            old_foreground = QRectF(left, top, right - left, bottom - top)
            available = old_foreground.intersected(native)
            if available.isEmpty():
                return
            source = QRectF((available.left() - native.left()) / native.width() * detail.width(),
                            (available.top() - native.top()) / native.height() * detail.height(),
                            available.width() / native.width() * detail.width(),
                            available.height() / native.height() * detail.height())
            relative_x = foreground.width() / old_foreground.width()
            relative_y = foreground.height() / old_foreground.height()
            destination = QRectF(foreground.left() + (available.left() - left) * relative_x,
                                 foreground.top() + (available.top() - top) * relative_y,
                                 available.width() * relative_x, available.height() * relative_y)
        elif not current_snapshot:
            return
        painter.save()
        painter.setClipRect(self._mapped(canvas), Qt.ClipOperation.IntersectClip)
        if not current_snapshot:
            painter.setClipRect(self._mapped(foreground), Qt.ClipOperation.IntersectClip)
        painter.drawPixmap(self._mapped(destination), detail, source)
        painter.restore()
        if not canvas.contains(foreground):
            # Preserve the dimmed original outside a Fill/Crop frame, including
            # native pixels while the user inspects an otherwise cropped area.
            outside = QPainterPath()
            outside.setFillRule(Qt.FillRule.OddEvenFill)
            outside.addRect(self._mapped(foreground))
            outside.addRect(self._mapped(foreground.intersected(canvas)))
            painter.save()
            painter.setClipPath(outside, Qt.ClipOperation.IntersectClip)
            # Replace the reduced layer rather than alpha-compositing the same
            # photograph twice at 30% opacity.
            painter.fillRect(self._mapped(destination), QColor("#10131b"))
            painter.setOpacity(.30)
            painter.drawPixmap(self._mapped(destination), detail, source)
            painter.restore()

    def _paint_live_canvas(self, painter: QPainter, target: QRectF, foreground: QRectF) -> None:
        """Paint a geometry-only update using existing rasters and bounded clips."""
        canvas = self._scene()[0]
        needs_background = not foreground.contains(canvas)
        if not needs_background:
            pass
        elif self._settings is not None and self._settings.background_mode == "solid":
            painter.fillRect(target, QColor(self._settings.background_color))
        elif self._background_pixmap is not None:
            painter.drawPixmap(target, self._background_pixmap, QRectF(self._background_pixmap.rect()))
        elif self._source_pixmap is not None:
            # Compatibility with legacy set_image callers without a separate BG:
            # use a fresh source cover, never a composite with an old foreground.
            source = self._source_cover_rect(target.width() / target.height())
            painter.drawPixmap(target, self._source_pixmap, source)
        if self._source_pixmap is not None:
            painter.save()
            painter.setClipRect(target, Qt.ClipOperation.IntersectClip)
            painter.drawPixmap(self._mapped(foreground), self._source_pixmap,
                               self._source_rect())
            painter.restore()

    def _source_rect(self) -> QRectF:
        """The selected original pixels mapped into the small source cache."""
        if self._source_pixmap is None:
            return QRectF()
        if self._geometry is None:
            return QRectF(self._source_pixmap.rect())
        width, height = self._geometry.original_size
        left, top, right, bottom = self._geometry.source_box
        sx, sy = self._source_pixmap.width() / width, self._source_pixmap.height() / height
        return QRectF(left * sx, top * sy, (right - left) * sx, (bottom - top) * sy)

    def _source_cover_rect(self, ratio: float) -> QRectF:
        if self._source_pixmap is None:
            return QRectF()
        source = self._source_rect()
        center = source.center()
        if source.width() / source.height() > ratio:
            source.setWidth(source.height() * ratio)
        else:
            source.setHeight(source.width() / ratio)
        source.moveCenter(center)
        return source

    @staticmethod
    def _crop_handle_positions(rect: QRectF) -> dict[str, QPointF]:
        center = rect.center()
        return {
            "nw": rect.topLeft(), "ne": rect.topRight(),
            "sw": rect.bottomLeft(), "se": rect.bottomRight(),
            "n": QPointF(center.x(), rect.top()),
            "s": QPointF(center.x(), rect.bottom()),
            "w": QPointF(rect.left(), center.y()),
            "e": QPointF(rect.right(), center.y()),
        }

    def _crop_rect(self) -> QRectF:
        if self._crop_drag is not None:
            drag = self._crop_drag
            left, top, right, bottom = drag.box
            return QRectF(drag.origin + QPointF(left, top) * drag.scale,
                          drag.origin + QPointF(right, bottom) * drag.scale)
        return self._mapped(self._scene()[1])

    def _crop_handle_at(self, point: QPointF) -> str | None:
        if (self._source_pixmap is None or self._geometry is None
                or not self._area().adjusted(-.001, -.001, .001, .001).contains(point)):
            return None
        distances = ((name, (position - point).manhattanLength())
                     for name, position in self._crop_handle_positions(self._crop_rect()).items())
        handle, distance = min(distances, key=lambda value: value[1])
        return handle if distance <= 11 else None

    def _update_hover_cursor(self, point: QPointF) -> None:
        if self._picking:
            self.setCursor(Qt.CursorShape.CrossCursor)
        elif self._space:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        elif (handle := self._crop_handle_at(point)) is not None:
            self.setCursor(_CROP_CURSORS[handle])
        else:
            self.unsetCursor()

    def _canonical_crop(self, box: tuple[int, int, int, int]) -> tuple[int, int, int, int] | None:
        size = (self._crop_drag.original_size if self._crop_drag is not None
                else self._geometry.original_size if self._geometry is not None else None)
        return None if size is not None and box == (0, 0, *size) else box

    def _move_crop(self, point: QPointF) -> None:
        drag = self._crop_drag
        if drag is None:
            return
        dx = round((point.x() - drag.start.x()) / drag.scale)
        dy = round((point.y() - drag.start.y()) / drag.scale)
        left, top, right, bottom = drag.initial_box
        width, height = drag.original_size
        if "w" in drag.handle:
            left = max(0, min(right - 1, left + dx))
        if "e" in drag.handle:
            right = max(left + 1, min(width, right + dx))
        if "n" in drag.handle:
            top = max(0, min(bottom - 1, top + dy))
        if "s" in drag.handle:
            bottom = max(top + 1, min(height, bottom + dy))
        box = (left, top, right, bottom)
        if box != drag.box:
            drag.box = box
            self.cropChanged.emit(self._canonical_crop(box))
            self.update()

    def _finish_crop(self) -> None:
        if self._crop_drag is None:
            return
        self._crop_drag = None
        self._last_detail_request = None
        self._end_drag()
        self.cropFinished.emit()
        self._schedule_detail()
        self.update()

    def _paint_crop_handles(self, painter: QPainter, rect: QRectF) -> None:
        if self._source_pixmap is None or self._geometry is None:
            return
        painter.setPen(QPen(QColor(130, 228, 217, 215), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)
        painter.setPen(QPen(QColor("#163c40"), 1))
        painter.setBrush(QColor("#f2fffd"))
        for center in self._crop_handle_positions(rect).values():
            painter.drawRect(QRectF(center.x() - 4, center.y() - 4, 8, 8))

    def _paint_crop_drag(self, painter: QPainter) -> None:
        drag = self._crop_drag
        if drag is None or self._source_pixmap is None:
            return
        width, height = drag.original_size
        image_rect = QRectF(drag.origin, drag.origin + QPointF(width, height) * drag.scale)
        source = QRectF(self._source_pixmap.rect())
        # Reveal pixels discarded by the previous crop as well. The original
        # coordinate transform remains fixed, so a handle never escapes the
        # pointer because a changed ratio re-fits or re-centres the composition.
        painter.setOpacity(.25)
        painter.drawPixmap(image_rect, self._source_pixmap, source)
        painter.setOpacity(1)
        painter.save()
        painter.setClipRect(self._crop_rect(), Qt.ClipOperation.IntersectClip)
        painter.drawPixmap(image_rect, self._source_pixmap, source)
        painter.restore()
        self._paint_crop_detail(painter)
        self._paint_crop_handles(painter, self._crop_rect())

    def _paint_crop_detail(self, painter: QPainter) -> None:
        """Keep accepted native foreground at the original-pixel map.

        A detail raster is an old composite in canvas coordinates. Its source
        crop and foreground identify the actual original pixels it contains;
        its padding must never move or appear as newly revealed photo pixels.
        """
        geometry = self._detail_geometry
        if (self._detail is None or geometry is None or self._geometry is None
                or geometry.original_size != self._geometry.original_size):
            return
        detail, native = self._detail
        if native.isEmpty():
            return
        left, top, right, bottom = geometry.foreground_box
        foreground = QRectF(left, top, right - left, bottom - top)
        available = foreground.intersected(native)
        if available.isEmpty():
            return
        source = QRectF((available.left() - native.left()) / native.width() * detail.width(),
                        (available.top() - native.top()) / native.height() * detail.height(),
                        available.width() / native.width() * detail.width(),
                        available.height() / native.height() * detail.height())
        # Foreground retains the original 1:1 pixel scale, including a previous
        # input crop. Undo its canvas placement before applying the preview transform.
        source_left, source_top, _, _ = geometry.source_box
        original = available.translated(source_left - left, source_top - top)
        origin, scale = self._original_mapping()
        destination = QRectF(origin + original.topLeft() * scale,
                             origin + original.bottomRight() * scale)
        painter.save()
        # Replace the dimmed reduced layer rather than blending the same photo
        # twice. Discarded native pixels receive exactly the overview's opacity.
        painter.setOpacity(1)
        painter.fillRect(destination, QColor("#10131b"))
        painter.setOpacity(.25)
        painter.drawPixmap(destination, detail, source)
        painter.setOpacity(1)
        painter.setClipRect(self._crop_rect(), Qt.ClipOperation.IntersectClip)
        painter.drawPixmap(destination, detail, source)
        painter.restore()

    def _paint_discarded_original(self, painter: QPainter) -> None:
        """Keep cropped-out pixels visible even where they overlap canvas padding."""
        if (self._source_pixmap is None or self._geometry is None
                or self._geometry.source_box == (0, 0, *self._geometry.original_size)):
            return
        original = self._mapped(self._original_rect())
        outside = QPainterPath()
        outside.setFillRule(Qt.FillRule.OddEvenFill)
        outside.addRect(original)
        outside.addRect(self._crop_rect())
        painter.save()
        painter.setClipPath(outside, Qt.ClipOperation.IntersectClip)
        # An opaque base prevents bright padding or a former composite from
        # changing the dimming strength of the discarded original pixels.
        painter.fillRect(original, QColor("#10131b"))
        painter.setOpacity(.25)
        painter.drawPixmap(original, self._source_pixmap, QRectF(self._source_pixmap.rect()))
        painter.setOpacity(1)
        self._paint_crop_detail(painter)
        painter.restore()

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.fillRect(self.rect(), QColor("#10131b"))
        if self._pixmap is None:
            painter.setPen(QColor("#d9e0ee"))
            font = painter.font()
            font.setPointSize(17)
            painter.setFont(font)
            painter.drawText(self.rect().adjusted(25, -22, -25, -22), Qt.AlignmentFlag.AlignCenter,
                             tr("Ready for your next carousel"))
            font.setPointSize(10)
            painter.setFont(font)
            painter.setPen(QColor("#8590a7"))
            text = tr("Loading photo…") if self._busy else tr(
                "Add or select a photo in the left panel.\nOriginal files are unchanged.")
            painter.drawText(self.rect().adjusted(30, 52, -30, 52), Qt.AlignmentFlag.AlignCenter, text)
            return
        if self.is_cropping:
            painter.save()
            painter.setClipRect(self._area())
            self._paint_crop_drag(painter)
            painter.restore()
            return
        canvas, foreground, _ = self._scene()
        target = self._mapped(canvas)
        painter.save()
        painter.setClipRect(self._area())
        if self._source_pixmap is not None and not canvas.contains(foreground):
            painter.setOpacity(0.30)
            painter.drawPixmap(self._mapped(foreground), self._source_pixmap,
                               self._source_rect())
            painter.setOpacity(1)
        if self._pending_geometry and self._source_pixmap is not None:
            self._paint_live_canvas(painter, target, foreground)
        else:
            painter.drawPixmap(target, self._pixmap, QRectF(self._pixmap.rect()))
        self._paint_detail(painter, canvas, foreground)
        self._paint_discarded_original(painter)
        painter.save()
        painter.setClipRect(target, Qt.ClipOperation.IntersectClip)
        painter.setPen(QPen(QColor(235, 239, 245, 100), 1))
        for index in range(self._count):
            tile = QRectF(target.left() + target.width() * index / self._count, target.top(),
                          target.width() / self._count, target.height())
            for line in grid_lines(tile, self._grid):
                painter.drawLine(line)
        painter.restore()
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(target)
        for index in range(1, self._count):
            x = target.left() + target.width() * index / self._count
            painter.setPen(QPen(QColor(0, 0, 0, 130), 3))
            painter.drawLine(QPointF(x, target.top()), QPointF(x, target.bottom()))
            painter.setPen(QPen(QColor("#ffffff"), 1, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(x, target.top()), QPointF(x, target.bottom()))
        for index in range(self._count):
            x = target.left() + target.width() * (index + 0.5) / self._count
            badge = QRectF(x - 12, target.top() + 9, 24, 22)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(14, 22, 31, 210))
            painter.drawRoundedRect(badge, 6, 6)
            painter.setPen(QColor("#ffffff"))
            painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, str(index + 1))
        self._paint_crop_handles(painter, self._crop_rect())
        painter.restore()
        painter.setPen(QColor("#93a1bb"))
        caption = tr("{count} tiles · tile ratio {ratio}:1", count=self._count,
                     ratio=f"{self._ratio:.3f}")
        if self._busy:
            caption += " · " + tr("Updating…")
        caption += " · " + self._detail_description()
        caption = painter.fontMetrics().elidedText(caption, Qt.TextElideMode.ElideRight,
                                                   max(1, self.width() - 30))
        painter.drawText(self.rect().adjusted(15, 0, -15, -12),
                         Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, caption)
