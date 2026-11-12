"""Pillow preview layers and a single cached background, used by one worker."""

from collections.abc import Callable

from PIL import Image

from insta_g.core.geometry import get_geometry
from insta_g.core.imaging import (
    SRGB_PROFILE,
    _background_region,
    _make_background,
    _needs_background,
    _paste_foreground,
    source_size,
)
from insta_g.core.models import MAX_PREVIEW_EDGE, Settings
from insta_g.core.resources import ensure_memory


class PreviewRenderer:
    """Cache only source-dependent background work; offsets never change it."""

    def __init__(self) -> None:
        self._source: Image.Image | None = None
        self._background: Image.Image | None = None
        self._background_key: tuple[object, ...] | None = None

    def render(
        self, source: Image.Image, settings: Settings, *, max_edge: int = MAX_PREVIEW_EDGE,
        cancelled: Callable[[], bool] | None = None,
    ) -> tuple[Image.Image, Image.Image | None] | None:
        stopped = cancelled or (lambda: False)
        if stopped():
            return None
        geometry = get_geometry(source_size(source), settings)
        scale = min(1.0, max_edge / max(geometry.canvas_size))
        size = tuple(max(1, round(value * scale)) for value in geometry.canvas_size)
        multiplier = 40 if geometry.source_box != (0, 0, *source_size(source)) else 16
        ensure_memory(size[0] * size[1] * multiplier, "Vytvorenie náhľadu alebo kompozície")
        background = None
        if _needs_background(geometry):
            key = (geometry.canvas_size, geometry.source_box, settings.background_mode,
                   settings.background_color, settings.blur)
            if self._source is not source or self._background_key != key:
                prepared = _make_background(source, geometry, settings)
                if self._background is not None:
                    self._background.close()
                self._source, self._background, self._background_key = source, prepared, key
            if stopped():
                return None
            background = _background_region(self._background, geometry, size)
            result = background.copy()
        else:
            result = Image.new("RGB", size)
        try:
            _paste_foreground(result, source, geometry)
            result.info["icc_profile"] = SRGB_PROFILE
            if stopped():
                result.close()
                if background is not None:
                    background.close()
                return None
            return result, background
        except BaseException:
            result.close()
            if background is not None:
                background.close()
            raise

    def close(self) -> None:
        if self._background is not None:
            self._background.close()
        self._source = self._background = self._background_key = None
