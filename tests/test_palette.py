"""Photo palette sampling stays deterministic and does not invent colours."""

from PIL import Image, ImageDraw

from insta_g.core.palette import dominant_colors


def test_monochrome_palette_contains_only_the_real_color():
    image = Image.new("RGB", (300, 200), "#31a0c2")
    assert dominant_colors(image) == ["#31A0C2"]
    assert image.getpixel((0, 0)) == (49, 160, 194)


def test_palette_returns_five_different_dominant_hues():
    image = Image.new("RGB", (500, 100))
    draw = ImageDraw.Draw(image)
    colors = ("#ff0000", "#00ff00", "#0000ff", "#ffffff", "#000000")
    for index, color in enumerate(colors):
        draw.rectangle((index * 100, 0, index * 100 + 99, 99), fill=color)
    result = dominant_colors(image)
    assert len(result) == len(set(result)) == 5
    assert set(result) == {color.upper() for color in colors}
    assert result == dominant_colors(image)


def test_nearly_identical_shades_do_not_fill_palette_slots():
    image = Image.new("RGB", (100, 100), (240, 30, 30))
    ImageDraw.Draw(image).rectangle((50, 0, 99, 99), fill=(242, 31, 31))
    assert len(dominant_colors(image)) == 1


def test_transparency_is_not_a_dominant_background_color():
    image = Image.new("RGBA", (100, 100), (255, 0, 0, 0))
    ImageDraw.Draw(image).rectangle((40, 40, 60, 60), fill=(0, 0, 255, 255))
    assert dominant_colors(image) == ["#0000FF"]
    assert dominant_colors(Image.new("RGBA", (10, 10))) == []
    assert dominant_colors(image, count=0) == []


def test_palette_supports_grayscale_and_requested_count():
    image = Image.new("L", (20, 20), 128)
    assert dominant_colors(image, count=1) == ["#808080"]
