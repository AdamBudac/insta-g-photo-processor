"""Explicit input crops retain upright native pixels throughout every renderer."""

from dataclasses import replace
from threading import Event

import imagecodecs
import numpy as np
import pytest
from PIL import Image

from insta_g.core import hdr, imaging
from insta_g.core.export import export_records
from insta_g.core.geometry import get_geometry
from insta_g.core.imaging import iter_tiles, load_image, render_composite, render_region
from insta_g.core.models import ImageRecord, Settings
from insta_g.gui import preview_renderer, workers
from insta_g.gui.preview_renderer import PreviewRenderer
from insta_g.gui.workers import DetailRenderer


def pattern(size=(1000, 500)):
    y, x = np.indices((size[1], size[0]))
    return Image.fromarray(np.stack((x % 256, y % 256, (x * 7 + y * 11) % 256), axis=-1).astype(np.uint8))


def joined(tiles):
    return Image.fromarray(np.concatenate([np.asarray(tile) for tile in tiles], axis=1))


def test_user_800_by_400_crop_splits_without_interpolation_or_missing_pixels():
    settings = Settings(splits=2, ratio_mode="fixed", ratio=1, crop_box=(100, 50, 900, 450))
    with pattern() as source:
        before = source.tobytes()
        tiles = list(iter_tiles(source, settings))
        try:
            assert [tile.size for tile in tiles] == [(400, 400), (400, 400)]
            with joined(tiles) as result, source.crop(settings.crop_box) as expected:
                assert result.tobytes() == expected.tobytes()
            assert source.size == (1000, 500) and source.tobytes() == before
        finally:
            for tile in tiles:
                tile.close()


@pytest.mark.parametrize("target", [(400, 200), (137, 69), (25, 13)])
def test_downsampled_foreground_never_filters_discarded_border_colours(target):
    settings = Settings(splits=2, ratio_mode="fixed", ratio=1, crop_box=(100, 50, 900, 450))
    with Image.new("RGB", (1000, 500), "red") as source:
        source.paste("green", settings.crop_box)
        with render_region(source, settings, (0, 0, 800, 400), target) as result:
            assert np.all(np.asarray(result) == (0, 128, 0))
        with render_composite(source, settings, max_edge=target[0]) as result:
            assert np.all(np.asarray(result) == (0, 128, 0))


@pytest.mark.parametrize("rect", [(0, 0, 5, 5), (795, 395, 800, 400),
                                  (.25, .25, 4.25, 4.25), (795.75, 395.75, 799.75, 399.75)])
def test_high_zoom_crop_edges_do_not_filter_removed_pixels(rect):
    settings = Settings(splits=2, ratio_mode="fixed", ratio=1, crop_box=(100, 50, 900, 450))
    with Image.new("RGB", (1000, 500), "red") as source:
        source.paste("green", settings.crop_box)
        with render_region(source, settings, rect, (100, 100)) as result:
            assert np.all(np.asarray(result) == (0, 128, 0))


def test_crop_sampling_temporary_is_bounded_by_viewport_not_native_crop(monkeypatch):
    target = (83, 25)
    real_reduce = Image.Image.reduce
    sizes = []

    def recorded(source, *args, **kwargs):
        result = real_reduce(source, *args, **kwargs)
        sizes.append(result.size)
        assert result.width <= target[0] * 2 and result.height <= target[1] * 2
        return result

    monkeypatch.setattr(Image.Image, "reduce", recorded)
    with Image.new("RGB", (3000, 1000), "green") as source:
        with imaging._resize_crop_region(source, (20.25, 30.5, 2980.25, 970.5), target) as result:
            assert result.size == target and sizes
            assert np.all(np.asarray(result) == (0, 128, 0))


def test_native_crop_bypasses_contaminated_full_source_lod_and_counts_temporary_ram(tmp_path, monkeypatch):
    path = tmp_path / "border.png"
    settings = Settings(splits=2, ratio_mode="fixed", ratio=1)
    with Image.new("RGB", (1000, 500), "red") as source:
        source.paste("green", (100, 50, 900, 450))
        source.save(path)
    renderer = DetailRenderer()
    monkeypatch.setattr(workers, "available_memory", lambda: 2 * 1024 ** 3)
    try:
        with renderer.render(str(path), (1000, 500), settings,
                             (0, 0, 1000, 500), (100, 50), Event()):
            assert renderer._levels
            levels = list(renderer._levels.values())
        captured = []
        rendered_sources = []
        checked = renderer._within_budget
        render = workers.render_region

        def budget(estimate):
            captured.append(estimate)
            return checked(estimate)

        def recorded(source, *args, **kwargs):
            rendered_sources.append(source)
            return render(source, *args, **kwargs)

        monkeypatch.setattr(renderer, "_within_budget", budget)
        monkeypatch.setattr(workers, "render_region", recorded)
        cropped = replace(settings, crop_box=(100, 50, 900, 450))
        with renderer.render(str(path), (1000, 500), cropped,
                             (0, 0, 800, 400), (100, 50), Event()) as result:
            assert np.all(np.asarray(result) == (0, 128, 0))
        assert rendered_sources == [renderer._source]
        assert 100 * 50 * 40 in captured
        assert list(renderer._levels.values()) == levels
    finally:
        renderer.close()


@pytest.mark.parametrize("fit", ["fit", "fill"])
@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_crop_precedes_fit_fill_and_offsets_without_moving_crop_window(fit, offset):
    settings = Settings(splits=3, ratio_mode="fixed", ratio=1, fit_mode=fit,
                        offset_x=offset, offset_y=offset, crop_box=(17, 11, 137, 71),
                        background_mode="solid", background_color="#123456")
    geometry = get_geometry((180, 90), settings)
    with pattern((180, 90)) as source, source.crop(settings.crop_box) as crop:
        crop_settings = replace(settings, crop_box=None)
        with render_composite(source, settings) as result, render_composite(crop, crop_settings) as expected:
            assert result.tobytes() == expected.tobytes()
            assert result.size == geometry.canvas_size
        assert geometry.source_box == settings.crop_box


@pytest.mark.parametrize("fit", ["fit", "fill"])
def test_native_viewport_equals_complete_crop_composition_including_outside_canvas(fit):
    settings = Settings(splits=3, ratio_mode="fixed", ratio=1, fit_mode=fit,
                        offset_x=.4, offset_y=-.3, blur=5, crop_box=(31, 17, 271, 137))
    geometry = get_geometry((300, 160), settings)
    left, top, right, bottom = geometry.foreground_box
    # Include cut-off foreground outside the output canvas as live preview does.
    rect = (min(-5, left), min(-5, top), max(geometry.canvas_size[0] + 5, right),
            max(geometry.canvas_size[1] + 5, bottom))
    target = (rect[2] - rect[0], rect[3] - rect[1])
    with pattern((300, 160)) as source, source.crop(settings.crop_box) as cropped:
        with render_region(source, settings, rect, target) as result:
            with render_region(cropped, replace(settings, crop_box=None), rect, target) as expected:
                assert result.tobytes() == expected.tobytes()


def test_reduced_roi_keeps_full_original_metadata_and_samples_crop_origin():
    settings = Settings(mode="expand", ratio=1, crop_box=(100, 80, 700, 400))
    with pattern((900, 600)) as source, source.resize((450, 300)) as reduced:
        reduced.info["source_size"] = source.size
        rect = (50, 190, 250, 290)
        with render_region(reduced, settings, rect, (100, 50), allow_reduced=True) as result:
            # Expand is 600x600; foreground starts at y=140.
            with reduced.resize((100, 50), Image.Resampling.LANCZOS,
                                box=(75, 65, 175, 115)) as expected:
                assert result.tobytes() == expected.tobytes()
        assert reduced.info["source_size"] == (900, 600)


def test_png_transparency_is_composited_before_native_crop(tmp_path):
    path = tmp_path / "transparent.png"
    with Image.new("RGBA", (100, 80), (20, 80, 140, 128)) as source:
        source.save(path)
    settings = Settings(mode="expand", ratio=1, crop_box=(20, 10, 80, 70))
    with load_image(path) as source:
        tiles = list(iter_tiles(source, settings))
        try:
            assert len(tiles) == 1 and tiles[0].size == (60, 60)
            with source.crop(settings.crop_box) as expected:
                assert tiles[0].tobytes() == expected.tobytes()
            assert tiles[0].getpixel((0, 0)) == (137, 167, 197)
        finally:
            for tile in tiles:
                tile.close()


def test_real_heic_crop_uses_upright_decoded_coordinates(tmp_path):
    path = tmp_path / "oriented.heic"
    exif = Image.Exif()
    exif[274] = 6
    with pattern((96, 64)) as source:
        source.save(path, quality=99, exif=exif.tobytes())
    settings = Settings(mode="expand", ratio=3 / 4, crop_box=(8, 16, 56, 80))
    with load_image(path) as source:
        assert source.size == (64, 96)
        assert source.info["source_size"] == (64, 96)
        with render_composite(source, settings) as result, source.crop(settings.crop_box) as expected:
            assert result.size == (48, 64)
            assert result.tobytes() == expected.tobytes()


@pytest.mark.parametrize("renderer_kind", ["overview", "native"])
def test_background_rebuilds_for_equal_size_crop_at_a_different_origin(tmp_path, monkeypatch, renderer_kind):
    path = tmp_path / "two-regions.png"
    with Image.new("RGB", (200, 100), "red") as source:
        source.paste("blue", (100, 0, 200, 100))
        source.save(path)
        settings = Settings(mode="expand", ratio=1, blur=0, crop_box=(10, 0, 90, 100))
        shifted = replace(settings, crop_box=(110, 0, 190, 100))
        renderer = PreviewRenderer() if renderer_kind == "overview" else DetailRenderer()
        module = preview_renderer if renderer_kind == "overview" else workers
        make_background = module._make_background
        calls = []

        def recorded(*args):
            calls.append(args[1].source_box)
            return make_background(*args)

        monkeypatch.setattr(module, "_make_background", recorded)
        try:
            results = []
            for current in (settings, replace(settings, offset_x=-1), shifted):
                if renderer_kind == "overview":
                    result, background = renderer.render(source, current)
                    background.close()
                else:
                    result = renderer.render(str(path), source.size, current,
                                             (0, 0, 100, 100), (100, 100), Event())
                with result:
                    results.append(result.getpixel((0, 50)))
            assert calls == [settings.crop_box, shifted.crop_box]
            assert results[0] == (255, 0, 0) and results[-1] == (0, 0, 255)
            if renderer_kind == "native":
                assert renderer._source.size == (200, 100)
        finally:
            renderer.close()


def test_native_source_and_pyramid_are_reused_across_crop_changes(tmp_path, monkeypatch):
    path = tmp_path / "source.png"
    with pattern((1600, 800)) as source:
        source.save(path)
    real_load = workers.load_image
    loads = []

    def counted(path):
        loads.append(path)
        return real_load(path)

    monkeypatch.setattr(workers, "load_image", counted)
    renderer = DetailRenderer()
    settings = Settings(splits=2, ratio_mode="fixed", ratio=1, crop_box=(200, 100, 1400, 700))
    try:
        with renderer.render(str(path), (1600, 800), settings, (0, 0, 1200, 600), (150, 75), Event()):
            native = renderer._source
            levels = list(renderer._levels.values())
        changed = replace(settings, crop_box=(100, 50, 1300, 650))
        with renderer.render(str(path), (1600, 800), changed, (0, 0, 1200, 600), (150, 75), Event()):
            assert renderer._source is native
            assert list(renderer._levels.values()) == levels
        with renderer.render(str(path), (1600, 800), changed, (10, 20, 30, 40), (20, 20), Event()) as result:
            with native.crop((110, 70, 130, 90)) as expected:
                assert result.tobytes() == expected.tobytes()
        assert loads == [str(path)]
    finally:
        renderer.close()


def test_background_crop_is_bounded_without_allocating_native_crop(monkeypatch):
    settings = Settings(mode="expand", ratio=1, blur=4, crop_box=(200, 100, 2800, 700))
    with Image.new("RGB", (3000, 800), "red") as source:
        source.paste("#204060", settings.crop_box)
        geometry = get_geometry(source.size, settings)
        monkeypatch.setattr(source, "crop", lambda *_args: pytest.fail("Native input crop allocated"))
        with imaging._make_background(source, geometry, settings) as background:
            assert max(background.size) <= 2048
            assert np.all(np.asarray(background) == (32, 64, 96))


def test_native_background_budget_includes_bounded_crop_even_on_skinny_canvas(tmp_path, monkeypatch):
    path = tmp_path / "square.png"
    with Image.new("RGB", (1600, 1600), "#204060") as source:
        source.save(path)
    monkeypatch.setattr(workers, "available_memory", lambda: 2 * 1024 ** 3)
    renderer = DetailRenderer()
    try:
        with renderer.render(str(path), (1600, 1600), Settings(splits=1, ratio=1),
                             (0, 0, 10, 10), (10, 10), Event()):
            native = renderer._source
        settings = Settings(splits=20, ratio_mode="fixed", ratio=16 / 9, fit_mode="fit",
                            crop_box=(30, 30, 1570, 1570))
        geometry = get_geometry((1600, 1600), settings)
        # The skinny bounded output is tiny, but the separate bounded crop
        # still needs memory and must be checked before background allocation.
        assert geometry.canvas_size[0] > geometry.canvas_size[1] * 30
        monkeypatch.setattr(workers, "available_memory", lambda: 20 * 1024 ** 2)
        monkeypatch.setattr(workers, "_make_background", lambda *_args: pytest.fail("Crop exceeded RAM budget"))
        assert renderer.render(str(path), (1600, 1600), settings,
                               (0, 0, *geometry.canvas_size), (100, 3), Event()) is None
        assert renderer._source is native and renderer.last_reason
    finally:
        renderer.close()


@pytest.mark.parametrize("fit", ["fit", "fill"])
@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_hdr_crop_keeps_linear_values_and_sdr_companion_at_identical_coordinates(fit, offset):
    rgb = np.arange(96 * 64 * 3, dtype=np.float32).reshape((64, 96, 3)) / 1000
    with pattern((96, 64)) as sdr:
        image = hdr.HdrImage(rgb, sdr.copy(), hdr.HdrInfo("ultrahdr"))
    settings = Settings(splits=3, ratio_mode="fixed", ratio=1, fit_mode=fit,
                        crop_box=(11, 13, 75, 45), offset_x=offset, offset_y=offset,
                        background_mode="solid", background_color="#123456")
    geometry = get_geometry(image.size, settings)
    tiles = list(hdr.iter_hdr_tiles(image, settings))
    try:
        result = np.concatenate([tile.rgb for tile in tiles], axis=1)
        with joined([tile.sdr for tile in tiles]) as companion:
            foreground = geometry.foreground_box
            left, top = max(0, foreground[0]), max(0, foreground[1])
            right, bottom = min(result.shape[1], foreground[2]), min(result.shape[0], foreground[3])
            x0, y0 = 11 + left - foreground[0], 13 + top - foreground[1]
            x1, y1 = x0 + right - left, y0 + bottom - top
            np.testing.assert_array_equal(result[top:bottom, left:right], rgb[y0:y1, x0:x1])
            with companion.crop((left, top, right, bottom)) as visible, image.sdr.crop((x0, y0, x1, y1)) as expected:
                assert visible.tobytes() == expected.tobytes()
        assert np.max(result) > 1
    finally:
        for tile in tiles:
            tile.close()
        image.close()


def test_hdr_background_uses_only_crop_and_a_numpy_view(monkeypatch):
    rgb = np.full((64, 128, 3), 1, dtype=np.float32)
    rgb[16:48, 32:96] = 4
    image = hdr.HdrImage(rgb, Image.new("RGB", (128, 64), "red"), hdr.HdrInfo("ultrahdr"))
    image.sdr.paste("blue", (32, 16, 96, 48))
    resize_float = hdr._resize_float
    seen = []

    def recorded(source, *args, **kwargs):
        seen.append(np.shares_memory(source, image.rgb))
        assert source.shape == (32, 64, 3)
        return resize_float(source, *args, **kwargs)

    monkeypatch.setattr(hdr, "_resize_float", recorded)
    try:
        linear, sdr = hdr._backgrounds(image, (64, 64), 0, (32, 16, 96, 48))
        with sdr:
            assert seen == [True]
            np.testing.assert_allclose(linear, 4)
            assert np.all(np.asarray(sdr) == (0, 0, 255))
    finally:
        image.close()


@pytest.mark.parametrize("mode", ["hdr", "sdr"])
def test_real_gainmap_crop_export_preserves_dimensions_suffix_and_range(tmp_path, mode):
    path = tmp_path / "source.jpg"
    rgba = np.ones((64, 128, 4), dtype=np.float16)
    rgba[..., :3] = (.5, 1, 2)
    rgba[8:56, 16:112, :3] = (4, 1, .5)
    companion = np.full((64, 128, 4), 128, dtype=np.uint8)
    companion[..., 3] = 255
    path.write_bytes(imagecodecs.ultrahdr_encode(
        rgba, sdr=companion, gamut="BT_2100", transfer="LINEAR", level=99,
        gainmap_level=99, scale=1, multichannel=True,
    ))
    before = path.read_bytes()
    settings = Settings(splits=2, ratio_mode="fixed", ratio=1, hdr_mode=mode,
                        crop_box=(16, 8, 112, 56))
    report = export_records([ImageRecord(str(path), settings)], tmp_path / "export")
    assert not report.errors and len(report.paths) == 2
    for index, output in enumerate(report.paths, 1):
        assert output.name == f"source_{mode.upper()}_{index:02d}.jpg"
        with Image.open(output) as result:
            assert result.size == (48, 48)
            assert result.getpixel((24, 24)) == (128, 128, 128)
            assert not result.getexif()
        if mode == "hdr":
            decoded = imagecodecs.ultrahdr_decode(output.read_bytes())
            np.testing.assert_allclose(decoded[24, 24, :3], (4, 1, .5), rtol=.05)
        else:
            assert not imagecodecs.ultrahdr_check(output.read_bytes())
    assert path.read_bytes() == before
