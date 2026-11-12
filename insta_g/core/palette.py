"""Small, deterministic photo palettes without GUI or persistent state."""

from __future__ import annotations

from math import sqrt

from PIL import Image


def _lab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    """sRGB -> D65 CIELAB (IEC sRGB transfer and CIE 1976 coordinates)."""
    values = [v / 255 for v in rgb]
    r, g, b = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
               for v in values]
    xyz = (
        (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047,
        0.2126729 * r + 0.7151522 * g + 0.0721750 * b,
        (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883,
    )
    x, y, z = [v ** (1 / 3) if v > (6 / 29) ** 3 else v / (3 * (6 / 29) ** 2) + 4 / 29
               for v in xyz]
    return 116 * y - 16, 500 * (x - y), 200 * (y - z)


def dominant_colors(image: Image.Image, count: int = 5) -> list[str]:
    """Return up to ``count`` frequent, perceptually separated sRGB colours.

    Small thumbnails and palette quantization bound the work. Transparent pixels
    are excluded. A monochrome image deliberately returns one colour rather
    than inventing a palette; near-identical shades do not fill empty slots.
    """
    if count <= 0:
        return []
    sample = image.copy()
    sample.thumbnail((192, 192), Image.Resampling.LANCZOS)
    rgba = sample.convert("RGBA")
    access = rgba.load()
    pixels = [access[x, y][:3] for y in range(rgba.height) for x in range(rgba.width)
              if access[x, y][3] >= 128]
    if not pixels:
        return []
    opaque = Image.new("RGB", (len(pixels), 1))
    opaque.putdata(pixels)
    quantized = opaque.quantize(colors=64, method=Image.Quantize.MEDIANCUT)
    palette = quantized.getpalette()
    if palette is None:
        return []
    candidates = []
    for population, index in quantized.getcolors() or []:
        if population < max(1, len(pixels) * 0.003):
            continue
        rgb = tuple(palette[index * 3:index * 3 + 3])
        candidates.append((population, rgb, _lab(rgb)))
    candidates.sort(key=lambda item: (-item[0], item[1]))
    selected = candidates[:1]
    candidates = candidates[1:]
    while candidates and len(selected) < min(count, 64):
        choices = []
        for candidate in candidates:
            distance = min(sqrt(sum((a - b) ** 2 for a, b in zip(candidate[2], old[2])))
                           for old in selected)
            if distance >= 12:
                choices.append((candidate[0] ** 0.5 * distance, candidate))
        if not choices:
            break
        winner = max(choices, key=lambda item: (item[0], item[1][0], item[1][1]))[1]
        selected.append(winner)
        candidates.remove(winner)
    return ["#%02X%02X%02X" % item[1] for item in selected]
