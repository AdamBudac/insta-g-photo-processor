"""Codec handling and native-pixel Fit/Fill composition with bounded previews."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from io import BytesIO
from math import ceil, floor, isfinite
from pathlib import Path

from PIL import Image, ImageCms, ImageFilter, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener

from .geometry import Geometry, get_geometry
from .models import MAX_PREVIEW_EDGE, Settings
from .raster import bounded_crop as _bounded_crop
from .raster import source_size
from .resources import ensure_memory

register_heif_opener()
# Physical memory checks replace Pillow's arbitrary source pixel ceiling.
Image.MAX_IMAGE_PIXELS = None
_SRGB_COLOR_PROFILE = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))
SRGB_PROFILE = _SRGB_COLOR_PROFILE.tobytes()
SUPPORTED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".heic", ".heif"})


def _srgb_rgb(source: Image.Image) -> Image.Image:
    has_alpha = source.mode in ("RGBA", "LA") or "transparency" in source.info
    alpha = source.convert("RGBA").getchannel("A") if has_alpha else None
    color = source if source.mode in ("RGB", "CMYK", "LAB") else source.convert("RGB")
    profile_data = source.info.get("icc_profile")
    if profile_data:
        try:
            profile = ImageCms.ImageCmsProfile(BytesIO(profile_data))
            color = ImageCms.profileToProfile(color, profile, _SRGB_COLOR_PROFILE, outputMode="RGB")
        except (OSError, ValueError, TypeError, ImageCms.PyCMSError) as exc:
            raise ValueError("Vstupný farebný profil ICC sa nepodarilo previesť na sRGB.") from exc
    else:
        color = color.convert("RGB")
    if alpha is not None:
        matte = Image.new("RGB", color.size, "white")
        matte.paste(color, mask=alpha)
        color = matte
    color.info.clear()
    color.info["icc_profile"] = SRGB_PROFILE
    return color


def _validate_edge(max_edge: int | None) -> None:
    if max_edge is not None and (
        isinstance(max_edge, bool) or not isinstance(max_edge, int) or max_edge < 1
    ):
        raise ValueError("Maximálna hrana náhľadu musí byť kladné celé číslo.")


def load_image(path: str | Path, max_edge: int | None = None) -> Image.Image:
    """Reduce previews before costly orientation/color copies where possible.

    JPEG uses decoder draft reduction. PNG/HEIC can require a native-size decode,
    so RAM is checked first. ``source_size`` keeps oriented native dimensions.
    """
    _validate_edge(max_edge)
    from .hdr import detect_hdr, load_hdr_sdr

    try:
        hdr = detect_hdr(path)
        if hdr.is_hdr:
            return load_hdr_sdr(path, max_edge=max_edge)
        with Image.open(path) as opened:
            if opened.format not in {"JPEG", "PNG", "HEIF", "HEIC"}:
                raise ValueError("Podporovaný je iba JPEG, PNG a HEIC/HEIF.")
            original = opened.size
            if max_edge is not None and opened.format == "JPEG":
                opened.draft("RGB", (max_edge, max_edge))
            ensure_memory(opened.width * opened.height * 12, "Dekódovanie fotografie")
            # PNG getexif() may call load() when EXIF is absent. Check RAM
            # before metadata access too, not just before explicit load().
            orientation = opened.getexif().get(274, 1)
            native_size = original[::-1] if orientation in (5, 6, 7, 8) else original
            if max_edge is not None:
                opened.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
            else:
                opened.load()
            ImageOps.exif_transpose(opened, in_place=True)
            result = _srgb_rgb(opened)
        result.info["source_size"] = native_size
        return result
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"Obrázok „{Path(path).name}“ sa nepodarilo načítať: {exc}") from exc


def _needs_background(geometry: Geometry) -> bool:
    left, top, right, bottom = geometry.foreground_box
    width, height = geometry.canvas_size
    return left > 0 or top > 0 or right < width or bottom < height


def _prepare_background(image: Image.Image, geometry: Geometry, blur: int) -> Image.Image:
    """Prepare a bounded background from the retained input region only."""
    width, height = geometry.canvas_size
    scale = min(1.0, MAX_PREVIEW_EDGE / max(width, height))
    size = (max(1, round(width * scale)), max(1, round(height * scale)))
    source = image
    reduced: Image.Image | None = None
    native_width, native_height = source_size(image)
    if geometry.source_box != (0, 0, native_width, native_height):
        reduced = _bounded_crop(image, geometry.source_box)
        source = reduced
    elif max(image.size) > MAX_PREVIEW_EDGE:
        reduction = MAX_PREVIEW_EDGE / max(image.size)
        reduced = image.resize(
            (max(1, round(image.width * reduction)), max(1, round(image.height * reduction))),
            Image.Resampling.LANCZOS,
        )
        source = reduced
    try:
        background = ImageOps.fit(source, size, method=Image.Resampling.LANCZOS)
    finally:
        if reduced is not None:
            reduced.close()
    if blur:
        blurred = background.filter(ImageFilter.GaussianBlur(blur * scale))
        background.close()
        return blurred
    return background


def _make_background(image: Image.Image, geometry: Geometry, settings: Settings) -> Image.Image:
    if settings.background_mode == "solid":
        # A single globally mapped colour pixel needs no native-canvas allocation.
        return Image.new("RGB", (1, 1), settings.background_color)
    return _prepare_background(image, geometry, settings.blur)


def _background_region(
    background: Image.Image, geometry: Geometry, size: tuple[int, int], *,
    native_left: int = 0, native_width: int | None = None,
    native_top: float = 0, native_height: float | None = None,
) -> Image.Image:
    # One affine transform in global coordinates prevents restarting the blur
    # or rescaling its pattern at individual tile boundaries.
    x_scale = background.width / geometry.canvas_size[0]
    y_scale = background.height / geometry.canvas_size[1]
    width = native_width or geometry.canvas_size[0]
    height = native_height or geometry.canvas_size[1]
    if background.size == (1, 1):
        return Image.new(background.mode, size, background.getpixel((0, 0)))
    if (background.size == size and native_left == native_top == 0
            and (width, height) == geometry.canvas_size):
        return background.copy()
    return background.transform(
        size, Image.Transform.AFFINE,
        (x_scale * width / size[0], 0, native_left * x_scale,
         0, y_scale * height / size[1], native_top * y_scale),
        resample=Image.Resampling.BICUBIC,
    )


def _paste_foreground(
    destination: Image.Image, image: Image.Image, geometry: Geometry, *, native_left: int = 0,
    native_width: int | None = None,
    native_top: float = 0, native_height: float | None = None,
) -> None:
    """Crop native foreground directly; resize only for a reduced preview."""
    width = native_width or geometry.canvas_size[0]
    height = native_height or geometry.canvas_size[1]
    left, top, right, bottom = geometry.foreground_box
    overlap = (max(native_left, left), max(native_top, top),
               min(native_left + width, right), min(native_top + height, bottom))
    if overlap[0] >= overlap[2] or overlap[1] >= overlap[3]:
        return
    dx, dy = destination.width / width, destination.height / height
    target = (
        round((overlap[0] - native_left) * dx), round((overlap[1] - native_top) * dy),
        round((overlap[2] - native_left) * dx), round((overlap[3] - native_top) * dy),
    )
    if target[0] >= target[2] or target[1] >= target[3]:
        return
    source_width, source_height = source_size(image)
    source_left, source_top, _, _ = geometry.source_box
    box = (
        (source_left + overlap[0] - left) * image.width / source_width,
        (source_top + overlap[1] - top) * image.height / source_height,
        (source_left + overlap[2] - left) * image.width / source_width,
        (source_top + overlap[3] - top) * image.height / source_height,
    )
    if image.size == (source_width, source_height) and dx == dy == 1:
        foreground = image.crop(tuple(round(value) for value in box))
    elif geometry.source_box != (0, 0, source_width, source_height):
        foreground = _resize_crop_region(
            image, box, (target[2] - target[0], target[3] - target[1]),
        )
    else:
        foreground = image.resize(
            (target[2] - target[0], target[3] - target[1]), Image.Resampling.LANCZOS, box=box,
        )
    try:
        destination.paste(foreground, (target[0], target[1]))
    finally:
        foreground.close()


def _resize_crop_region(
    image: Image.Image, box: tuple[float, float, float, float], size: tuple[int, int],
) -> Image.Image:
    """Isolate retained pixels before filtering, with at most 2x oversampling.

    Lanczos applied directly to a source-region box samples beyond that box.
    Integer BOX reduction restricts input to the requested upright pixels and
    creates at most four viewport pixels of temporary storage per output pixel.
    The final Lanczos pass preserves fractional viewport coordinates, including
    high zoom where reduction is 1 and the small native region remains exact.
    """
    bounds = (max(0, floor(box[0])), max(0, floor(box[1])),
              min(image.width, ceil(box[2])), min(image.height, ceil(box[3])))
    factors = (max(1, ceil((bounds[2] - bounds[0]) / (2 * size[0]))),
               max(1, ceil((bounds[3] - bounds[1]) / (2 * size[1]))))
    with image.reduce(factors, box=bounds) as isolated:
        region = ((box[0] - bounds[0]) / factors[0], (box[1] - bounds[1]) / factors[1],
                  (box[2] - bounds[0]) / factors[0], (box[3] - bounds[1]) / factors[1])
        return isolated.resize(size, Image.Resampling.LANCZOS, box=region)


def _validate_region(
    native_rect: tuple[float, float, float, float], target_size: tuple[int, int],
) -> None:
    """Validate before source decoding or any viewport allocation."""
    if (
        len(native_rect) != 4
        or not all(isinstance(value, (int, float)) and not isinstance(value, bool)
                and isfinite(value) for value in native_rect)
        or len(target_size) != 2
        or not all(isinstance(value, int) and not isinstance(value, bool) for value in target_size)
        or min(target_size) < 1 or max(target_size) > 2 ** 31 - 1
    ):
        raise ValueError("Neplatná oblasť detailu náhľadu.")
    left, top, right, bottom = native_rect
    if (right <= left or bottom <= top or not isfinite(right - left)
            or not isfinite(bottom - top)):
        raise ValueError("Neplatná oblasť detailu náhľadu.")


def render_region(
    image: Image.Image, settings: Settings, native_rect: tuple[float, float, float, float],
    target_size: tuple[int, int], *, background: Image.Image | None = None,
    allow_reduced: bool = False,
) -> Image.Image:
    """Render only the viewport at its physical pixel size, guarded by RAM.

    The native renderer may pass an adequately sampled cached pyramid level;
    its ``source_size`` metadata retains the original geometry. Other callers
    still require native pixels, so an overview cannot masquerade as detail.
    """
    _validate_region(native_rect, target_size)
    left, top, right, bottom = native_rect
    if not allow_reduced and image.size != source_size(image):
        raise ValueError("Detail vyžaduje originálne rozlíšenie fotografie.")
    geometry = get_geometry(source_size(image), settings)
    multiplier = 40 if geometry.source_box != (0, 0, *source_size(image)) else 12
    ensure_memory(target_size[0] * target_size[1] * multiplier, "Vytvorenie detailu náhľadu")
    arguments = dict(native_left=left, native_top=top,
                     native_width=right - left, native_height=bottom - top)
    rgb = image if image.mode == "RGB" else _srgb_rgb(image)
    try:
        if _needs_background(geometry):
            if background is not None:
                result = _background_region(background, geometry, target_size, **arguments)
            else:
                with _make_background(rgb, geometry, settings) as prepared:
                    result = _background_region(prepared, geometry, target_size, **arguments)
        else:
            result = Image.new("RGB", target_size)
        _paste_foreground(result, rgb, geometry, **arguments)
        result.info.clear()
        result.info["icc_profile"] = SRGB_PROFILE
        return result
    finally:
        if rgb is not image:
            rgb.close()


def render_composite(image: Image.Image, settings: Settings, max_edge: int | None = None) -> Image.Image:
    """Render native geometry at full size or as a bounded preview.

    Batch export deliberately bypasses this full-canvas convenience function.
    """
    _validate_edge(max_edge)
    geometry = get_geometry(source_size(image), settings)
    scale = 1.0 if max_edge is None else min(1.0, max_edge / max(geometry.canvas_size))
    size = tuple(max(1, round(value * scale)) for value in geometry.canvas_size)
    multiplier = 40 if geometry.source_box != (0, 0, *source_size(image)) and scale < 1 else 12
    ensure_memory(size[0] * size[1] * multiplier, "Vytvorenie náhľadu alebo kompozície")
    rgb = image if image.mode == "RGB" else _srgb_rgb(image)
    try:
        if _needs_background(geometry):
            with _make_background(rgb, geometry, settings) as background:
                result = _background_region(background, geometry, size)
        else:
            result = Image.new("RGB", size)
        _paste_foreground(result, rgb, geometry)
        result.info.clear()
        result.info["icc_profile"] = SRGB_PROFILE
        return result
    finally:
        if rgb is not image:
            rgb.close()


def iter_tiles(
    image: Image.Image, settings: Settings, cancelled: Callable[[], bool] | None = None
) -> Iterator[Image.Image]:
    """Yield one native tile at a time; the caller owns each yielded image."""
    geometry = get_geometry(source_size(image), settings)
    if image.size != source_size(image):
        raise ValueError("Export vyžaduje pôvodné rozlíšenie fotografie, nie zmenšený náhľad.")
    is_cancelled = cancelled or (lambda: False)
    if is_cancelled():
        return
    rgb = image if image.mode == "RGB" else _srgb_rgb(image)
    background: Image.Image | None = None
    try:
        if _needs_background(geometry):
            background = _make_background(rgb, geometry, settings)
        for index in range(geometry.count):
            if is_cancelled():
                return
            ensure_memory(geometry.tile_width * geometry.tile_height * 12, "Vytvorenie exportného dielu")
            left = index * geometry.tile_width
            size = (geometry.tile_width, geometry.tile_height)
            if background is not None:
                tile = _background_region(background, geometry, size, native_left=left, native_width=geometry.tile_width)
            else:
                tile = Image.new("RGB", size)
            _paste_foreground(tile, rgb, geometry, native_left=left, native_width=geometry.tile_width)
            tile.info.clear()
            tile.info["icc_profile"] = SRGB_PROFILE
            yield tile
    finally:
        if background is not None:
            background.close()
        if rgb is not image:
            rgb.close()


def generate_tiles(image: Image.Image, settings: Settings) -> list[Image.Image]:
    """Compatibility helper; streaming export uses ``iter_tiles`` directly."""
    return list(iter_tiles(image, settings))
