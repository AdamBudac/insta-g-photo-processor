"""Background image work; Qt widgets and QPixmap stay on the GUI thread."""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from threading import Event

from PIL import Image
from PySide6.QtCore import QObject, QRunnable, Signal
from PySide6.QtGui import QImage

from insta_g.core.export import export_records
from insta_g.core.geometry import get_geometry
from insta_g.core.imaging import (
    _make_background,
    _needs_background,
    _validate_region,
    load_image,
    render_region,
)
from insta_g.core.models import ImageRecord, Settings
from insta_g.core.palette import dominant_colors
from insta_g.core.resources import available_memory, ensure_memory
from insta_g.gui.preview_renderer import PreviewRenderer
from insta_g.i18n import tr


def to_qimage(image: Image.Image) -> QImage:
    """Detach the Qt image from the short-lived Pillow byte buffer."""
    rgb = image if image.mode == "RGB" else image.convert("RGB")
    try:
        return QImage(
            rgb.tobytes(), rgb.width, rgb.height, rgb.width * 3, QImage.Format.Format_RGB888
        ).copy()
    finally:
        if rgb is not image:
            rgb.close()


class WorkerSignals(QObject):
    imported = Signal(str, object, object, object)
    import_failed = Signal(str, str)
    preview = Signal(int, str, object, object, object)
    detail = Signal(int, str, object, object)
    detail_status = Signal(int, str, str, str)
    error = Signal(str)
    progress = Signal(int, int, str)
    exported = Signal(object)
    finished = Signal(object)


class Job(QRunnable):
    def __init__(self) -> None:
        super().__init__()
        self.signals = WorkerSignals()
        self.cancel = Event()


class ImportJob(Job):
    def __init__(self, paths: list[str]) -> None:
        super().__init__()
        self.paths = paths

    def run(self) -> None:
        try:
            for path in self.paths:
                if self.cancel.is_set():
                    break
                try:
                    source = load_image(path, max_edge=2048)
                    source.info["dominant_colors"] = dominant_colors(source)
                    size = source.info.get("source_size", source.size)
                    thumbnail = source.copy()
                    thumbnail.thumbnail((256, 160), Image.Resampling.LANCZOS)
                    self.signals.imported.emit(path, size, to_qimage(thumbnail), source)
                except Exception as error:
                    if not self.cancel.is_set():
                        self.signals.import_failed.emit(path, f"{Path(path).name}: {tr(str(error))}")
        finally:
            self.signals.finished.emit(self)


class PreviewJob(Job):
    def __init__(
        self, generation: int, path: str, settings: Settings, source: Image.Image | None,
        renderer: PreviewRenderer | None = None,
    ) -> None:
        super().__init__()
        self.generation = generation
        self.path = path
        self.settings = settings
        self.source = source
        self.renderer = renderer or PreviewRenderer()

    def run(self) -> None:
        try:
            if self.cancel.is_set():
                return
            source = self.source or load_image(self.path, max_edge=2048)
            if "dominant_colors" not in source.info:
                source.info["dominant_colors"] = dominant_colors(source)
            if self.cancel.is_set():
                return
            frame = self.renderer.render(source, self.settings, max_edge=2048, cancelled=self.cancel.is_set)
            if frame is not None:
                result, background = frame
                try:
                    if not self.cancel.is_set():
                        self.signals.preview.emit(self.generation, self.path, to_qimage(result), source,
                                                  to_qimage(background) if background is not None else None)
                finally:
                    result.close()
                    if background is not None:
                        background.close()
        except Exception as error:
            if not self.cancel.is_set():
                self.signals.error.emit(tr("Preview {name}: {error}", name=Path(self.path).name, error=tr(str(error))))
        finally:
            self.signals.finished.emit(self)


class ExportJob(Job):
    def __init__(self, records: list[ImageRecord], output_dir: str) -> None:
        super().__init__()
        self.records = records
        self.output_dir = output_dir

    def run(self) -> None:
        try:
            report = export_records(
                self.records,
                self.output_dir,
                progress=self.signals.progress.emit,
                cancelled=self.cancel.is_set,
                create_output=False,
            )
            self.signals.exported.emit(report)
        except Exception as error:
            self.signals.error.emit(tr("Export failed: {error}", error=tr(str(error))))
        finally:
            self.signals.finished.emit(self)


class DetailRenderer:
    """One native SDR source, accessed only by a single-thread worker pool.

    Decode peaks use a share of currently available RAM, without a fixed pixel
    or cache-size ceiling. A reduced preview remains visible during decoding.
    """

    def __init__(self) -> None:
        self._source: Image.Image | None = None
        self._key: tuple[str, int, int] | None = None
        self._background: Image.Image | None = None
        self._background_key: tuple[object, ...] | None = None
        self._levels: OrderedDict[int, Image.Image] = OrderedDict()
        self.last_reason = ""

    def close(self) -> None:
        """Release the single native source after detail jobs have finished."""
        if self._source is not None:
            self._source.close()
        if self._background is not None:
            self._background.close()
        for level in self._levels.values():
            level.close()
        self._levels.clear()
        self._source, self._key = None, None
        self._background, self._background_key = None, None

    def _within_budget(self, estimate: int) -> bool:
        """Check incremental work; already resident source/cache is not copied."""
        available = available_memory()
        if available is not None:
            budget = available * 2 // 5
            if estimate > budget:
                mib = 1024 * 1024
                self.last_reason = tr(
                    "Native detail needs approximately {required} MiB; its current memory budget is {budget} MiB. The reduced preview remains visible.",
                    required=(estimate + mib - 1) // mib, budget=budget // mib,
                )
                return False
        ensure_memory(estimate, "Vytvorenie detailu náhľadu")
        return True

    def _viewport_source(
        self, rect: tuple[float, float, float, float], target: tuple[int, int],
        working_bytes: int, cancelled: Event,
    ) -> Image.Image:
        """Lazily cache up to two sufficiently sampled levels of one source.

        A level has at least 1.25 source pixels per requested screen pixel.
        Zooming to native pixels always uses the original. The cache occupies
        at most a third of one native RGB raster, never another full image.
        """
        source = self._source
        assert source is not None
        ratio = min((rect[2] - rect[0]) / target[0], (rect[3] - rect[1]) / target[1])
        factor = 1
        while factor * 2 <= ratio / 1.25 and factor * 2 <= min(source.size):
            factor *= 2
        if factor == 1:
            return source
        if factor in self._levels:
            self._levels.move_to_end(factor)
            return self._levels[factor]
        size = (max(1, (source.width + factor - 1) // factor),
                max(1, (source.height + factor - 1) // factor))
        level_bytes = size[0] * size[1] * 4
        cache_budget = source.width * source.height * 4 // 3
        if level_bytes > cache_budget:
            return source
        while self._levels and (len(self._levels) >= 2 or
                sum(level.width * level.height * 4 for level in self._levels.values())
                + level_bytes > cache_budget):
            self._levels.popitem(last=False)[1].close()
        # Caches are optional: insufficient pyramid RAM must not prevent a
        # viewport which can still be rendered directly from the native source.
        reason = self.last_reason
        reduction = max(1, factor // 3)
        # Pillow can hold an integer-reduced source and a horizontal Lanczos
        # intermediate before producing the level. Count both allocations,
        # rather than estimating just the final small level.
        preparation = level_bytes * 2 + source.height * size[0] * 4
        if reduction > 1:
            preparation += ((source.width + reduction - 1) // reduction
                            * ((source.height + reduction - 1) // reduction) * 4)
        try:
            if not self._within_budget(working_bytes + preparation):
                self.last_reason = reason
                return source
            if cancelled.is_set():
                return source
            level = source.resize(size, Image.Resampling.LANCZOS, reducing_gap=3.0)
        except MemoryError:
            # A failed optional optimization does not reduce image quality.
            self.last_reason = reason
            return source
        level.info["source_size"] = source.size
        self._levels[factor] = level
        return level

    def render(self, path: str, size: tuple[int, int], settings: Settings,
               rect: tuple[float, float, float, float], target: tuple[int, int],
               cancelled: Event) -> Image.Image | None:
        self.last_reason = ""
        if cancelled.is_set():
            return None
        _validate_region(rect, target)
        settings.validate()
        cropped = settings.source_bounds(size) != (0, 0, *size)
        working_bytes = target[0] * target[1] * (40 if cropped else 16)
        stat = Path(path).stat()
        key = (path, stat.st_mtime_ns, stat.st_size)
        if key != self._key:
            from insta_g.core.hdr import detect_hdr, sdr_decode_bytes_per_pixel
            ensure_memory(stat.st_size * 4, "Čítanie HDR metadát")
            multiplier = sdr_decode_bytes_per_pixel(path, detect_hdr(path))
            # A source can be replaced after import. Recheck the current header
            # before decoding, rather than trusting the old library dimensions.
            with Image.open(path) as header:
                pixels = max(size[0] * size[1], header.width * header.height)
            estimate = pixels * multiplier + stat.st_size * 4 + working_bytes
            if not self._within_budget(estimate):
                return None
            if cancelled.is_set():
                return None
            # Keep the previous source during preflight. Release it immediately
            # before decoding so the cache never holds two native photographs.
            self.close()
            source = load_image(path)
            if source.size != size:
                source.close()
                self.last_reason = tr("The source dimensions changed. Reimport the photo to load native detail.")
                return None
            # A cancelled decode can still serve the latest pending viewport.
            self._source, self._key = source, key
        if cancelled.is_set() or self._source is None:
            return None
        if self._source.size != size:
            self.last_reason = tr("The source dimensions changed. Reimport the photo to load native detail.")
            return None
        geometry = get_geometry(size, settings)
        # Target conversion to QImage/QPixmap and foreground intermediates are
        # budgeted on every request, including a hit in the native-source cache.
        if not self._within_budget(working_bytes):
            return None
        background = None
        if _needs_background(geometry):
            background_key = (self._key, geometry.canvas_size, geometry.source_box, settings.blur,
                              settings.background_mode, settings.background_color)
            if background_key != self._background_key:
                # Backgrounds remain bounded; neither Fit nor a large viewport
                # ever allocates the whole expanded native canvas.
                scale = min(1.0, 2048 / max(geometry.canvas_size))
                background_pixels = (max(1, round(geometry.canvas_size[0] * scale))
                                     * max(1, round(geometry.canvas_size[1] * scale)))
                source_left, source_top, source_right, source_bottom = geometry.source_box
                crop_width, crop_height = source_right - source_left, source_bottom - source_top
                source_scale = min(1.0, 2048 / max(crop_width, crop_height))
                sampled_width = max(1, round(crop_width * source_scale))
                sampled_height = max(1, round(crop_height * source_scale))
                background_work = background_pixels * 16
                if geometry.source_box != (0, 0, *self._source.size):
                    # Explicit crops have their own bounded sampling raster,
                    # including when no source reduction was otherwise needed.
                    background_work += sampled_width * sampled_height * 8
                if source_scale < 1:
                    # Reducing a tall native source also holds a horizontal
                    # resampling intermediate, larger than the final background.
                    background_work += self._source.height * sampled_width * 4
                if settings.background_mode != "solid" and not self._within_budget(
                    working_bytes + background_work
                ):
                    return None
                prepared = _make_background(self._source, geometry, settings)
                if self._background is not None:
                    self._background.close()
                self._background, self._background_key = prepared, background_key
            background = self._background
        if cancelled.is_set():
            return None
        # Full-source levels have already mixed discarded border pixels into
        # the crop edges. Crop-specific bounded sampling happens in render_region.
        source = self._source if cropped else self._viewport_source(rect, target, working_bytes, cancelled)
        if cancelled.is_set():
            return None
        return render_region(source, settings, rect, target, background=background,
                             allow_reduced=source is not self._source)


class DetailJob(Job):
    def __init__(self, renderer: DetailRenderer, generation: int, path: str,
                 size: tuple[int, int], settings: Settings, request: dict[str, object]) -> None:
        super().__init__()
        self.renderer, self.generation, self.path = renderer, generation, path
        self.size, self.settings, self.request = size, settings, request

    def run(self) -> None:
        try:
            if self.cancel.is_set():
                return
            self.signals.detail_status.emit(self.generation, self.path, "loading", "")
            image = self.renderer.render(
                self.path, self.size, self.settings, tuple(self.request["native_rect"]),
                tuple(self.request["target_size"]), self.cancel,
            )
            if image is not None:
                try:
                    if not self.cancel.is_set():
                        self.signals.detail.emit(self.generation, self.path, to_qimage(image), self.request["native_rect"])
                        self.signals.detail_status.emit(self.generation, self.path, "native", "")
                finally:
                    image.close()
            elif not self.cancel.is_set():
                reason = self.renderer.last_reason or tr("Native detail is unavailable. The reduced preview remains visible.")
                self.signals.detail_status.emit(self.generation, self.path, "reduced", reason)
        except Exception as error:
            # Native detail is an enhancement; report why it was unavailable
            # without invalidating a successful preview or export state.
            if not self.cancel.is_set():
                self.renderer.last_reason = tr(str(error))
                self.signals.detail_status.emit(self.generation, self.path, "reduced", self.renderer.last_reason)
        finally:
            self.signals.finished.emit(self)
