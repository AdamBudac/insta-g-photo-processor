"""Small raster helpers shared by SDR and HDR, without codec dependencies."""

from PIL import Image

from .models import MAX_PREVIEW_EDGE


def source_size(image: Image.Image) -> tuple[int, int]:
    size = image.info.get("source_size", image.size)
    if not isinstance(size, (tuple, list)) or len(size) != 2:
        return image.size
    return int(size[0]), int(size[1])


def bounded_crop(image: Image.Image, bounds: tuple[int, int, int, int]) -> Image.Image:
    """Sample a background crop without allocating a native crop copy."""
    native_width, native_height = source_size(image)
    left, top, right, bottom = bounds
    box = (left * image.width / native_width, top * image.height / native_height,
           right * image.width / native_width, bottom * image.height / native_height)
    region_width, region_height = box[2] - box[0], box[3] - box[1]
    reduction = min(1.0, MAX_PREVIEW_EDGE / max(region_width, region_height))
    # BOX averages only retained pixels, without sampling discarded margins.
    return image.resize(
        (max(1, round(region_width * reduction)), max(1, round(region_height * reduction))),
        Image.Resampling.BOX if reduction < 1 else Image.Resampling.LANCZOS, box=box,
    )
