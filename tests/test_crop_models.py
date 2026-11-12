"""Input crops use upright original pixels before any split/expand placement."""

from __future__ import annotations

import json

import pytest

from insta_g.core.geometry import get_geometry
from insta_g.core.models import ImageRecord, Settings


def test_crop_bounds_and_json_roundtrip_use_hashable_original_pixel_coordinates() -> None:
    settings = Settings.from_dict({"crop_box": [100, 50, 900, 450]})
    assert settings.crop_box == (100, 50, 900, 450)
    assert settings.source_bounds((1000, 500)) == (100, 50, 900, 450)
    assert settings.cropped_size((1000, 500)) == (800, 400)
    assert Settings.from_dict(json.loads(json.dumps(settings.to_dict()))) == settings
    assert hash(tuple(settings.export_dict().items()))
    assert Settings().source_bounds((1000, 500)) == (0, 0, 1000, 500)


@pytest.mark.parametrize("crop_box", [
    [], [0, 0, 1], [0, 0, 1, 1, 2], "0,0,1,1", {},
    [True, 0, 1, 1], [0, False, 1, 1], [0, 0, 1.0, 1], [0, 0, 1, "1"],
    [-1, 0, 1, 1], [0, -1, 1, 1], [1, 0, 1, 1], [0, 1, 1, 1],
    [2, 0, 1, 1], [0, 2, 1, 1],
])
def test_invalid_input_crop_is_rejected_without_silent_repair(crop_box: object) -> None:
    with pytest.raises(ValueError, match="[Vv]ýrez"):
        Settings.from_dict({"crop_box": crop_box})


@pytest.mark.parametrize("crop_box", [(0, 0, 1001, 500), (0, 0, 1000, 501), (1000, 0, 1001, 1)])
def test_crop_outside_original_is_rejected(crop_box: tuple[int, int, int, int]) -> None:
    settings = Settings(crop_box=crop_box)
    with pytest.raises(ValueError, match="[Vv]ýrez"):
        settings.source_bounds((1000, 500))
    with pytest.raises(ValueError, match="[Vv]ýrez"):
        get_geometry((1000, 500), settings)


@pytest.mark.parametrize("size", [(0, 500), (1000, 0), (-1, 500), (True, 500), (1000.0, 500)])
def test_crop_helpers_validate_original_size(size: tuple[int, int]) -> None:
    with pytest.raises(ValueError):
        Settings(crop_box=(0, 0, 1, 1)).source_bounds(size)


def test_crop_becomes_unscaled_foreground_with_original_retention_percentage() -> None:
    settings = Settings(
        mode="expand", ratio_mode="fixed", ratio=1,
        crop_box=(100, 50, 900, 450),
    )
    geometry = get_geometry((1000, 500), settings)
    assert geometry.original_size == (1000, 500)
    assert geometry.source_box == settings.crop_box
    assert geometry.foreground_box == (0, 200, 800, 600)
    assert geometry.canvas_size == (800, 800)
    assert geometry.retained_percentage == pytest.approx(64)
    settings.offset_y = 1
    assert get_geometry((1000, 500), settings).foreground_box == (0, 400, 800, 800)
    assert get_geometry((1000, 500), settings).retained_percentage == pytest.approx(64)


def test_auto_ratio_and_split_seams_are_based_on_crop_not_discarded_edges() -> None:
    settings = Settings(splits=2, crop_box=(100, 50, 900, 450), fit_mode="fit")
    geometry = get_geometry((1000, 500), settings)
    assert geometry.ratio == 1
    assert (geometry.tile_width, geometry.tile_height, geometry.count) == (400, 400, 2)
    assert geometry.canvas_size == (800, 400)
    assert geometry.foreground_box == (0, 0, 800, 400)
    assert geometry.source_box[0] + geometry.tile_width == 500
    assert geometry.source_box[0] + 2 * geometry.tile_width == geometry.source_box[2]


def test_fill_retention_accounts_for_input_crop_and_additional_canvas_crop() -> None:
    settings = Settings(
        splits=1, ratio_mode="fixed", ratio=1, fit_mode="fill",
        crop_box=(100, 50, 900, 450), offset_x=1,
    )
    geometry = get_geometry((1000, 500), settings)
    assert geometry.canvas_size == (400, 400)
    assert geometry.foreground_box == (-400, 0, 400, 400)
    assert geometry.retained_percentage == pytest.approx(32)


def test_odd_crop_rounding_only_adds_padding_for_fit_and_never_resamples() -> None:
    settings = Settings(
        splits=3, ratio_mode="fixed", ratio=1, fit_mode="fit",
        crop_box=(11, 17, 1012, 274),
    )
    geometry = get_geometry((1100, 300), settings)
    assert geometry.canvas_size == (1002, 334)
    left, top, right, bottom = geometry.foreground_box
    assert (right - left, bottom - top) == (1001, 257)
    assert 0 <= left < right <= geometry.canvas_size[0]
    assert 0 <= top < bottom <= geometry.canvas_size[1]
    assert geometry.retained_percentage == pytest.approx(100 * 1001 * 257 / (1100 * 300))


def test_uncropped_geometry_also_describes_original_source_bounds() -> None:
    geometry = get_geometry((1000, 500), Settings())
    assert geometry.original_size == (1000, 500)
    assert geometry.source_box == (0, 0, 1000, 500)


def test_crop_edits_invalidate_export_and_restoring_crop_restores_export() -> None:
    record = ImageRecord("source.png", previewed=True)
    record.exported_settings = record.settings.to_dict()
    assert record.status == "exported"
    record.settings.crop_box = (100, 50, 900, 450)
    assert record.status == "staging"
    record.exported_settings = record.settings.to_dict()
    assert record.status == "exported"
    restored = ImageRecord.from_dict(json.loads(json.dumps(record.to_dict())))
    assert restored == record and restored.status == "exported"
    record.settings.crop_box = (101, 50, 901, 450)
    assert record.status == "staging"
    record.settings.crop_box = (100, 50, 900, 450)
    assert record.status == "exported"


def test_legacy_export_snapshot_remains_green_when_no_input_crop_is_set() -> None:
    settings = Settings()
    snapshot = settings.to_dict()
    snapshot.pop("crop_box")
    record = ImageRecord("old.png", settings, exported_settings=snapshot)
    assert record.is_exported
