"""One geometry calculation shared by the preview and full-resolution export."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor

from .models import MAX_INSTAGRAM_RATIO, MIN_INSTAGRAM_RATIO, Settings


@dataclass(frozen=True)
class Geometry:
    tile_width: int
    tile_height: int
    count: int
    ratio: float
    canvas_size: tuple[int, int]
    foreground_box: tuple[int, int, int, int]
    original_size: tuple[int, int]
    source_box: tuple[int, int, int, int]

    @property
    def retained_percentage(self) -> float:
        """Percentage of original foreground pixels included in the canvas."""
        left, top, right, bottom = self.foreground_box
        visible_width = max(0, min(self.canvas_size[0], right) - max(0, left))
        visible_height = max(0, min(self.canvas_size[1], bottom) - max(0, top))
        original_width, original_height = self.original_size
        return min(100.0, 100.0 * visible_width * visible_height / (original_width * original_height))


def get_geometry(size: tuple[int, int], settings: Settings) -> Geometry:
    """Enclose the source (Fit) or crop inside it (Fill), without resampling."""
    source_box = settings.source_bounds(size)
    width = source_box[2] - source_box[0]
    height = source_box[3] - source_box[1]
    ratio = settings.effective_ratio(width, height)
    count = settings.count
    if settings.effective_fit_mode == "fit":
        if width / (count * height) > ratio:
            tile_width = ceil(width / count)
            tile_height = ceil(tile_width / ratio)
        else:
            tile_height = height
            tile_width = ceil(height * ratio)
        # Correct integer rounding by adding padding, never cropping pixels.
        tile_width = max(tile_width, ceil(tile_height * MIN_INSTAGRAM_RATIO))
        tile_height = max(tile_height, ceil(tile_width / MAX_INSTAGRAM_RATIO))
    else:
        if width < count:
            raise ValueError("Fotografia je príliš úzka pre zvolený počet dielov bez zväčšenia.")
        if width / (count * height) > ratio:
            tile_height = height
            tile_width = min(width // count, max(1, floor(height * ratio)))
        else:
            tile_width = width // count
            tile_height = min(height, max(1, floor(tile_width / ratio)))
        # Fill corrects rounding by removing pixels, never by enlarging.
        tile_height = min(tile_height, max(1, floor(tile_width / MIN_INSTAGRAM_RATIO)))
        tile_width = min(tile_width, max(1, floor(tile_height * MAX_INSTAGRAM_RATIO)))
    canvas_width, canvas_height = tile_width * count, tile_height
    left = round((canvas_width - width) * (1 + settings.offset_x) / 2)
    top = round((canvas_height - height) * (1 + settings.offset_y) / 2)
    return Geometry(
        tile_width=tile_width,
        tile_height=tile_height,
        count=count,
        ratio=ratio,
        canvas_size=(canvas_width, canvas_height),
        foreground_box=(left, top, left + width, top + height),
        original_size=size,
        source_box=source_box,
    )
