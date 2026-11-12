"""Opt-in real large-image regression, separate from the lightweight suite."""

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path
from threading import Event

import pytest
from PIL import Image, ImageDraw

from insta_g.core.export import export_records
from insta_g.core.geometry import get_geometry
from insta_g.core.imaging import load_image, render_composite, source_size
from insta_g.core.models import ImageRecord, Settings
from insta_g.gui.workers import DetailRenderer


@pytest.mark.skipif(
    os.environ.get("INSTA_G_TEST_LARGE") != "1",
    reason="84 MP integration: enable explicitly with INSTA_G_TEST_LARGE=1",
)
def test_real_84_megapixel_jpeg_preview_and_native_export(tmp_path: Path) -> None:
    path = tmp_path / "84-megapixel-panorama.jpg"
    colors = [(220, 30, 40), (30, 200, 60), (35, 70, 220)]
    with Image.new("RGB", (12000, 7000)) as image:
        draw = ImageDraw.Draw(image)
        for index, color in enumerate(colors):
            draw.rectangle((index * 4000, 0, (index + 1) * 4000 - 1, 6999), fill=color)
        del draw
        image.save(path, "JPEG", quality=99, subsampling=0)
    settings = Settings(splits=3, ratio_mode="fixed", ratio=1, fit_mode="fit", blur=30)
    geometry = get_geometry((12000, 7000), settings)
    assert geometry.canvas_size == (21000, 7000)
    assert geometry.canvas_size[0] * geometry.canvas_size[1] > 80_000_000
    with load_image(path, max_edge=2048) as reduced:
        assert source_size(reduced) == (12000, 7000)
        assert max(reduced.size) <= 2048
        with render_composite(reduced, settings, max_edge=2048) as preview:
            assert max(preview.size) <= 2048
    detail_renderer = DetailRenderer()
    detail = None
    try:
        with detail_renderer.render(
            str(path), (12000, 7000), settings,
            (0, 0, *geometry.canvas_size), (3840, 1280), Event(),
        ) as overview:
            assert overview.size == (3840, 1280)
            assert max(detail_renderer._background.size) <= 2048
            assert len(detail_renderer._levels) <= 2
        warmed_source = detail_renderer._source
        left, top, _, _ = geometry.foreground_box
        detail = detail_renderer.render(
            str(path), (12000, 7000), settings,
            (left + 500, top + 3000, left + 1500, top + 4000), (1000, 1000), Event(),
        )
        assert detail is not None, detail_renderer.last_reason
        assert detail_renderer._source.size == (12000, 7000)
        assert detail_renderer._source is warmed_source
        assert detail.getpixel((500, 500)) == pytest.approx(colors[0], abs=4)
        cropped = replace(settings, crop_box=(1000, 1000, 11000, 6000))
        cropped_geometry = get_geometry((12000, 7000), cropped)
        assert cropped_geometry.canvas_size == (15000, 5000)
        with detail_renderer.render(
            str(path), (12000, 7000), cropped,
            (0, 0, *cropped_geometry.canvas_size), (3840, 1280), Event(),
        ) as crop_overview:
            assert crop_overview.size == (3840, 1280)
            assert detail_renderer._source is warmed_source
        crop_left, crop_top, _, _ = cropped_geometry.foreground_box
        with detail_renderer.render(
            str(path), (12000, 7000), cropped,
            (crop_left + 500, crop_top + 1000, crop_left + 1500, crop_top + 2000),
            (1000, 1000), Event(),
        ) as crop_detail:
            assert crop_detail.getpixel((500, 500)) == pytest.approx(colors[0], abs=4)
            assert detail_renderer._source is warmed_source
    finally:
        if detail is not None:
            detail.close()
        detail_renderer.close()
    report = export_records([ImageRecord(str(path), settings)], tmp_path / "export")
    assert report.errors == [] and not report.cancelled
    assert len(report.paths) == 3
    for tile_path in report.paths:
        with Image.open(tile_path) as tile:
            assert tile.size == (7000, 7000)
    left, top, _, _ = geometry.foreground_box
    for (source_x, source_y), expected in zip(
        [(1000, 3500), (6000, 3500), (11000, 3500)], colors, strict=True,
    ):
        global_x = left + source_x
        tile_index, local_x = divmod(global_x, geometry.tile_width)
        with Image.open(report.paths[tile_index]) as tile:
            assert tile.getpixel((local_x, top + source_y)) == pytest.approx(expected, abs=4)
