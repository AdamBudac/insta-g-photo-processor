"""Pixel-level image and export contracts; all files are generated in tmp_path."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from PIL import Image, ImageCms, ImageDraw, JpegImagePlugin, PngImagePlugin

from insta_g.core import export as export_module
from insta_g.core import imaging as imaging_module
from insta_g.core.export import ExportReport, export_records
from insta_g.core.geometry import get_geometry
from insta_g.core.imaging import (
    SRGB_PROFILE,
    generate_tiles,
    iter_tiles,
    load_image,
    render_composite,
    source_size,
)
from insta_g.core.models import ImageRecord, Settings


def _pattern(size: tuple[int, int]) -> Image.Image:
    """Every horizontal location has changing colour and fine vertical detail."""
    width, height = size
    return Image.frombytes(
        "RGB", size,
        bytes(
            channel
            for y in range(height)
            for x in range(width)
            for channel in (x % 256, (x // 256 * 71 + y) % 256, (x * 7 + y * 3) % 256)
        ),
    )


def _quadrants() -> Image.Image:
    image = Image.new("RGB", (96, 64))
    painter = ImageDraw.Draw(image)
    painter.rectangle((0, 0, 47, 31), fill=(240, 20, 20))
    painter.rectangle((48, 0, 95, 31), fill=(20, 240, 20))
    painter.rectangle((0, 32, 47, 63), fill=(20, 20, 240))
    painter.rectangle((48, 32, 95, 63), fill=(240, 240, 20))
    return image


def _write_source(path: Path, size: tuple[int, int] = (768, 256)) -> Path:
    with _pattern(size) as image:
        image.save(path, format="PNG")
    return path


def _square_settings(**changes: object) -> Settings:
    values: dict[str, object] = {
        "ratio_mode": "fixed", "ratio": 1.0, "blur": 0, "fit_mode": "fit",
    }
    values.update(changes)
    return Settings.from_dict(values)


def _join_tiles(tiles: list[Image.Image]) -> Image.Image:
    joined = Image.new("RGB", (sum(tile.width for tile in tiles), tiles[0].height))
    position = 0
    for tile in tiles:
        joined.paste(tile, (position, 0))
        position += tile.width
    return joined


def test_settings_roundtrip_and_per_image_independence() -> None:
    first, second = ImageRecord("first.png"), ImageRecord("second.png")
    first.settings.blur = 999
    assert second.settings.blur == 40
    restored = ImageRecord.from_dict(first.to_dict())
    assert restored == first
    restored.settings.blur = 1
    assert first.settings.blur == 999


def test_new_split_uses_fill_but_saved_missing_choice_preserves_fit() -> None:
    assert Settings().fit_mode == Settings().effective_fit_mode == "fill"
    assert Settings(mode="expand").effective_fit_mode == "fit"
    assert Settings.from_dict({}).fit_mode == "fit"
    assert ImageRecord.from_dict({"path": "legacy.png"}).settings.fit_mode == "fit"
    assert Settings.from_dict({"fit_mode": "fill"}).fit_mode == "fill"


@pytest.mark.parametrize("checked", [False, True])
def test_record_status_tracks_preview_and_export_independently_of_checkbox(checked: bool) -> None:
    record = ImageRecord("source.png", checked=checked)
    assert record.previewed is False and record.status == "imported"
    record.previewed = True
    assert record.status == "staging"
    record.exported_settings = record.settings.to_dict()
    assert record.status == "exported"
    record.previewed = False
    assert record.status == "exported"
    record.checked = not checked
    assert record.status == "exported"


@pytest.mark.parametrize("previewed,expected", [(False, "imported"), (True, "staging")])
def test_stale_export_snapshot_uses_preview_status(previewed: bool, expected: str) -> None:
    record = ImageRecord("source.png", previewed=previewed)
    record.exported_settings = record.settings.to_dict()
    record.settings.blur += 1
    assert not record.is_exported and record.status == expected
    restored = ImageRecord.from_dict(record.to_dict())
    assert restored.previewed is previewed and restored.status == expected


def test_preview_state_roundtrip_and_positional_record_compatibility() -> None:
    settings = Settings()
    snapshot = settings.to_dict()
    positional = ImageRecord("source.png", settings, True, snapshot)
    assert positional.checked and positional.exported_settings == snapshot
    assert positional.previewed is False and positional.status == "exported"
    positional.previewed = True
    restored = ImageRecord.from_dict(positional.to_dict())
    assert restored == positional and restored.previewed is True
    legacy = ImageRecord.from_dict({"path": "legacy.png"})
    assert legacy.previewed is False and legacy.status == "imported"


def test_export_status_matches_snapshot_and_survives_independent_roundtrip() -> None:
    record = ImageRecord("source.png", checked=True)
    assert not record.is_exported
    record.exported_settings = record.settings.to_dict()
    assert record.is_exported
    record.checked = False
    assert record.is_exported
    restored = ImageRecord.from_dict(record.to_dict())
    assert restored == record and restored.is_exported
    assert restored.settings is not record.settings
    assert restored.exported_settings is not record.exported_settings
    record.settings.blur += 1
    assert not record.is_exported and restored.is_exported
    record.settings.blur -= 1
    assert record.is_exported
    restored.exported_settings["blur"] = 1
    assert record.exported_settings["blur"] == 40


def test_export_status_compares_canonical_legacy_settings() -> None:
    record = ImageRecord("legacy.png", Settings(fit_mode="fit"), exported_settings={})
    assert record.is_exported
    record.settings.fit_mode = "fill"
    assert not record.is_exported


@pytest.mark.parametrize("checked", [None, 0, 1, "true", [], {}])
def test_checked_state_requires_a_boolean(checked: object) -> None:
    with pytest.raises(ValueError, match="logická"):
        ImageRecord.from_dict({"path": "source.png", "checked": checked})
    with pytest.raises(ValueError, match="logická"):
        ImageRecord("source.png", checked=checked).to_dict()  # type: ignore[arg-type]


@pytest.mark.parametrize("previewed", [None, 0, 1, "true", [], {}])
def test_preview_state_requires_a_boolean(previewed: object) -> None:
    with pytest.raises(ValueError, match="logická"):
        ImageRecord.from_dict({"path": "source.png", "previewed": previewed})
    with pytest.raises(ValueError, match="logická"):
        ImageRecord("source.png", previewed=previewed).to_dict()  # type: ignore[arg-type]


@pytest.mark.parametrize("snapshot", [False, [], "settings", {"blur": -1}, {"extra": 1}])
def test_exported_snapshot_is_validated(snapshot: object) -> None:
    with pytest.raises(ValueError):
        ImageRecord.from_dict({"path": "source.png", "exported_settings": snapshot})
    with pytest.raises(ValueError):
        ImageRecord("source.png", exported_settings=snapshot).to_dict()  # type: ignore[arg-type]


def test_export_report_completed_default_is_independent_and_positional_compatible() -> None:
    first, second = ExportReport([], [], True), ExportReport()
    first.completed["first.png"] = Settings().to_dict()
    assert first.cancelled and not second.completed


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("mode", "crop"), ("ratio_mode", "unknown"), ("fit_mode", "unknown"),
        ("orientation", "diagonal"),
        ("splits", 0), ("splits", 21), ("splits", True), ("splits", 2.0),
        ("blur", -1), ("blur", 1001), ("blur", False), ("blur", 1.5),
        ("ratio", 0.74), ("ratio", 1.8),
        ("ratio", float("nan")), ("ratio", float("inf")),
        ("ratio", -float("inf")), ("ratio", True), ("ratio", "4:3"),
        ("offset_x", True), ("offset_y", "0"), ("offset_x", 1.01),
        ("offset_y", -1.01), ("offset_x", float("nan")), ("offset_y", float("inf")),
    ],
)
def test_invalid_settings_are_rejected(field: str, value: object) -> None:
    with pytest.raises(ValueError):
        Settings.from_dict({field: value})


@pytest.mark.parametrize("data", [[], None, {"unknown": 1}])
def test_invalid_settings_json_shape_is_rejected(data: object) -> None:
    with pytest.raises(ValueError):
        Settings.from_dict(data)  # type: ignore[arg-type]


@pytest.mark.parametrize("data", [{}, {"path": " "}, {"path": 3}, {"path": "a", "x": 1}])
def test_invalid_image_records_are_rejected(data: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        ImageRecord.from_dict(data)


@pytest.mark.parametrize(
    ("size", "splits", "expected"),
    [((3000, 1000), 3, 1.0), ((9000, 1000), 3, 16 / 9), ((500, 3000), 3, 0.75)],
)
def test_auto_ratio_uses_source_and_clamps_to_instagram(
    size: tuple[int, int], splits: int, expected: float,
) -> None:
    assert Settings(splits=splits).effective_ratio(*size) == pytest.approx(expected)


@pytest.mark.parametrize("fit_mode", ["fit", "fill"])
@pytest.mark.parametrize("size", [(1, 100), (100, 1), (1, 1), (257, 320)])
def test_auto_ratio_integer_dimensions_stay_instagram_compatible(
    fit_mode: str, size: tuple[int, int],
) -> None:
    geometry = get_geometry(size, Settings(splits=1, fit_mode=fit_mode))
    actual_ratio = geometry.tile_width / geometry.tile_height
    assert 0.75 <= actual_ratio <= 16 / 9


@pytest.mark.parametrize("size", [(257, 320), (1001, 257), (1, 1)])
@pytest.mark.parametrize("ratio", [0.75, 4 / 3, 16 / 9])
@pytest.mark.parametrize("fit_mode", ["fit", "fill"])
def test_native_geometry_contains_or_crops_without_resizing(
    size: tuple[int, int], ratio: float, fit_mode: str,
) -> None:
    settings = Settings(mode="split", splits=1, ratio_mode="fixed", ratio=ratio, fit_mode=fit_mode)
    geometry = get_geometry(size, settings)
    width, height = geometry.canvas_size
    if fit_mode == "fit":
        assert width >= size[0] and height >= size[1]
    else:
        assert width <= size[0] and height <= size[1]
    left, top, right, bottom = geometry.foreground_box
    assert (right - left, bottom - top) == size
    assert 0.75 <= geometry.tile_width / geometry.tile_height <= 16 / 9


@pytest.mark.parametrize(("old_ratio", "expected"), [(4 / 3, 0.75), (16 / 9, 0.75), (1.0, 1.0)])
def test_legacy_orientation_and_resize_migrate_to_actual_ratio(old_ratio: float, expected: float) -> None:
    settings = Settings.from_dict({"ratio": old_ratio, "orientation": "portrait", "export_width": 1080})
    assert settings.ratio == expected
    assert "orientation" not in settings.to_dict()
    assert "export_width" not in settings.to_dict()
    assert Settings.from_dict({"ratio": 3 / 4}).ratio == 3 / 4


@pytest.mark.parametrize("size", [(0, 10), (10, 0), (-1, 10)])
def test_invalid_source_dimensions_are_rejected(size: tuple[int, int]) -> None:
    with pytest.raises(ValueError):
        get_geometry(size, Settings())


def test_geometry_has_no_pixel_cap_and_preview_can_represent_huge_sources() -> None:
    geometry = get_geometry((100_000, 100_000), Settings(splits=20, fit_mode="fit"))
    assert geometry.canvas_size[0] * geometry.canvas_size[1] > 80_000_000
    with Image.new("RGB", (20, 20), "red") as thumbnail:
        thumbnail.info["source_size"] = (100_000, 100_000)
        with render_composite(thumbnail, Settings(splits=20, fit_mode="fit"), max_edge=2048) as preview:
            assert max(preview.size) == 2048


def test_exact_fit_splits_reconstruct_every_original_pixel_and_seam() -> None:
    with _pattern((768, 256)) as original:
        tiles = generate_tiles(original, _square_settings())
        try:
            assert [tile.size for tile in tiles] == [(256, 256)] * 3
            with _join_tiles(tiles) as joined:
                assert joined.tobytes() == original.tobytes()
            for index in range(2):
                boundary = (index + 1) * 256
                assert tiles[index].crop((255, 0, 256, 256)).tobytes() == original.crop(
                    (boundary - 1, 0, boundary, 256)
                ).tobytes()
                assert tiles[index + 1].crop((0, 0, 1, 256)).tobytes() == original.crop(
                    (boundary, 0, boundary + 1, 256)
                ).tobytes()
        finally:
            for tile in tiles:
                tile.close()


def test_odd_panorama_keeps_every_native_pixel_and_adds_minimum_padding() -> None:
    with _pattern((1001, 257)) as original:
        settings = _square_settings()
        tiles = generate_tiles(original, settings)
        try:
            with _join_tiles(tiles) as joined:
                assert joined.size == (1002, 334)
                assert joined.crop((0, 38, 1001, 295)).tobytes() == original.tobytes()
        finally:
            for tile in tiles:
                tile.close()


def test_expand_preserves_full_portrait_and_blur_changes_only_background() -> None:
    with _pattern((128, 256)) as original:
        settings = _square_settings(mode="expand")
        with render_composite(original, settings) as sharp:
            settings.blur = 1000
            with render_composite(original, settings) as blurred:
                assert sharp.size == blurred.size == (256, 256)
                assert sharp.crop((64, 0, 192, 256)).tobytes() == original.tobytes()
                assert blurred.crop((64, 0, 192, 256)).tobytes() == original.tobytes()
                assert sharp.crop((0, 0, 64, 256)).tobytes() != blurred.crop(
                    (0, 0, 64, 256)
                ).tobytes()


@pytest.mark.parametrize("offset", [-1.0, 0.0, 1.0])
def test_fill_crop_offsets_keep_exact_native_pixels(offset: float) -> None:
    with _pattern((1001, 257)) as original:
        settings = _square_settings(fit_mode="fill", offset_x=offset)
        geometry = get_geometry(original.size, settings)
        assert geometry.canvas_size == (771, 257)
        left = round((771 - 1001) * (1 + offset) / 2)
        assert geometry.foreground_box == (left, 0, left + 1001, 257)
        tiles = generate_tiles(original, settings)
        try:
            with _join_tiles(tiles) as joined:
                assert joined.tobytes() == original.crop((-left, 0, -left + 771, 257)).tobytes()
        finally:
            for tile in tiles:
                tile.close()


@pytest.mark.parametrize("offset", [-1.0, 0.0, 1.0])
def test_vertical_fill_and_fit_offsets_are_shared_with_render(offset: float) -> None:
    with _pattern((300, 301)) as original:
        fill = _square_settings(splits=3, fit_mode="fill", offset_y=offset)
        geometry = get_geometry(original.size, fill)
        assert geometry.canvas_size == (300, 100)
        top = geometry.foreground_box[1]
        with render_composite(original, fill) as rendered:
            assert rendered.tobytes() == original.crop((0, -top, 300, -top + 100)).tobytes()
        fit = _square_settings(splits=3, offset_x=offset)
        geometry = get_geometry(original.size, fit)
        with render_composite(original, fit) as rendered:
            assert rendered.crop(geometry.foreground_box).tobytes() == original.tobytes()


def test_expand_always_preserves_full_source_even_with_legacy_fill_setting() -> None:
    with _pattern((101, 257)) as original:
        settings = _square_settings(mode="expand", fit_mode="fill", offset_x=1)
        geometry = get_geometry(original.size, settings)
        assert geometry.canvas_size == (257, 257)
        with render_composite(original, settings) as rendered:
            assert rendered.crop(geometry.foreground_box).tobytes() == original.tobytes()


def test_tile_background_uses_the_same_global_mapping_as_whole_composite() -> None:
    with _pattern((391, 257)) as original:
        settings = _square_settings(splits=5, blur=7, offset_x=-0.3)
        tiles = generate_tiles(original, settings)
        try:
            with _join_tiles(tiles) as joined, render_composite(original, settings) as composite:
                assert joined.tobytes() == composite.tobytes()
        finally:
            for tile in tiles:
                tile.close()


def test_reduced_preview_cannot_be_accidentally_exported() -> None:
    with Image.new("RGB", (40, 20)) as thumbnail:
        thumbnail.info["source_size"] = (4000, 2000)
        with pytest.raises(ValueError, match="pôvodné"):
            list(iter_tiles(thumbnail, Settings()))


def test_preview_is_bounded_and_retains_original_geometry(tmp_path: Path) -> None:
    path = _write_source(tmp_path / "wide.png", (4097, 17))
    with load_image(path, max_edge=2048) as image:
        assert max(image.size) == 2048
        assert source_size(image) == (4097, 17)
        settings = Settings(splits=5, fit_mode="fit")
        with render_composite(image, settings, max_edge=2048) as preview:
            geometry = get_geometry((4097, 17), settings)
            assert preview.size == (2048, round(geometry.tile_height * 2048 / geometry.canvas_size[0]))
            assert max(preview.size) <= 2048


@pytest.mark.parametrize("max_edge", [0, -1, True, 1.5])
def test_invalid_preview_limit_is_rejected(tmp_path: Path, max_edge: object) -> None:
    path = _write_source(tmp_path / "input.png", (10, 10))
    with pytest.raises(ValueError):
        load_image(path, max_edge=max_edge)  # type: ignore[arg-type]
    with Image.new("RGB", (10, 10)) as image, pytest.raises(ValueError):
        render_composite(image, Settings(), max_edge=max_edge)  # type: ignore[arg-type]


@pytest.mark.parametrize(("suffix", "file_format"), [("jpg", "JPEG"), ("png", "PNG"), ("heic", "HEIF")])
@pytest.mark.parametrize("orientation", [1, 6, 8])
def test_real_codecs_apply_exif_orientation_and_normalize_srgb(
    tmp_path: Path, suffix: str, file_format: str, orientation: int,
) -> None:
    path = tmp_path / f"orient-{orientation}.{suffix}"
    with _quadrants() as original:
        exif = Image.Exif()
        exif[274] = orientation
        exif[270] = "private metadata"
        original.save(
            path, format=file_format, quality=99, exif=exif.tobytes(),
            icc_profile=SRGB_PROFILE,
        )
    # HEIC is actually encoded by libheif; there is no renamed PNG substitute.
    with Image.open(path) as encoded:
        assert encoded.format == file_format
    expected = {
        1: [(240, 20, 20), (20, 240, 20), (20, 20, 240), (240, 240, 20)],
        6: [(20, 20, 240), (240, 20, 20), (240, 240, 20), (20, 240, 20)],
        8: [(20, 240, 20), (240, 240, 20), (240, 20, 20), (20, 20, 240)],
    }[orientation]
    with load_image(path) as decoded:
        assert decoded.size == ((96, 64) if orientation == 1 else (64, 96))
        assert source_size(decoded) == decoded.size
        assert decoded.mode == "RGB"
        assert decoded.info["icc_profile"] == SRGB_PROFILE
        assert not decoded.getexif()
        sample_points = [
            (decoded.width // 4, decoded.height // 4),
            (decoded.width * 3 // 4, decoded.height // 4),
            (decoded.width // 4, decoded.height * 3 // 4),
            (decoded.width * 3 // 4, decoded.height * 3 // 4),
        ]
        for point, color in zip(sample_points, expected, strict=True):
            assert decoded.getpixel(point) == pytest.approx(color, abs=8)


@pytest.mark.parametrize("mode", ["RGBA", "P"])
def test_png_transparency_is_composited_on_white(tmp_path: Path, mode: str) -> None:
    path = tmp_path / "transparent.png"
    if mode == "RGBA":
        image = Image.new("RGBA", (2, 1))
        image.putdata([(255, 0, 0, 0), (255, 0, 0, 128)])
        expected = [(255, 255, 255), (255, 127, 127)]
    else:
        image = Image.new("P", (2, 1))
        image.putpalette([255, 0, 0, 0, 0, 255] + [0] * 762)
        image.putdata([0, 1])
        image.info["transparency"] = 0
        expected = [(255, 255, 255), (0, 0, 255)]
    with image:
        image.save(path)
    with load_image(path) as decoded:
        assert decoded.mode == "RGB"
        assert [decoded.getpixel((x, 0)) for x in range(2)] == expected


def test_icc_lab_colour_conversion_changes_pixels_to_srgb() -> None:
    # Neutral CIELAB L*=50 maps to roughly sRGB 119,119,119. This exercises
    # the colour transform rather than merely relabelling unchanged RGB data.
    lab_profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("LAB"))
    with Image.new("LAB", (8, 8), (128, 128, 128)) as lab:
        lab.info["icc_profile"] = lab_profile.tobytes()
        with imaging_module._srgb_rgb(lab) as converted:
            assert converted.mode == "RGB"
            assert converted.getpixel((4, 4)) == pytest.approx((119, 119, 119), abs=2)
            assert converted.info["icc_profile"] == SRGB_PROFILE


def test_invalid_icc_profile_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "broken-profile.png"
    with Image.new("RGB", (4, 4), "red") as image:
        image.save(path, icc_profile=b"not an ICC profile")
    with pytest.raises(ValueError, match="ICC"):
        load_image(path)


def test_bad_unsupported_and_missing_inputs_are_reported(tmp_path: Path) -> None:
    broken = tmp_path / "broken.jpg"
    broken.write_bytes(b"this is not a picture")
    unsupported = tmp_path / "bmp-disguised.jpg"
    with Image.new("RGB", (8, 8)) as image:
        image.save(unsupported, format="BMP")
    for path in (broken, unsupported, tmp_path / "missing.heic"):
        with pytest.raises(ValueError):
            load_image(path)


def test_decode_uses_dynamic_ram_guard_before_full_load(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _write_source(tmp_path / "small.png", (8, 8))
    requests: list[tuple[int, str]] = []

    def no_memory(required_bytes: int, operation: str) -> None:
        requests.append((required_bytes, operation))
        raise MemoryError("Nedostatok dostupnej RAM")

    monkeypatch.setattr(imaging_module, "ensure_memory", no_memory)
    with pytest.raises(MemoryError, match="RAM"):
        load_image(path)
    assert requests == [(8 * 8 * 12, "Dekódovanie fotografie")]
    assert Image.MAX_IMAGE_PIXELS is None


def test_export_creates_real_quality_99_jpegs_and_keeps_original(tmp_path: Path) -> None:
    path = _write_source(tmp_path / "panoráma.png")
    before = path.read_bytes()
    progress: list[tuple[int, int, str]] = []
    report = export_records(
        [ImageRecord(str(path), _square_settings())], tmp_path / "export",
        progress=lambda done, total, name: progress.append((done, total, name)),
    )
    assert not report.errors and not report.cancelled
    assert [p.name for p in report.paths] == [f"panoráma_{index:02d}.jpg" for index in (1, 2, 3)]
    assert [(done, total) for done, total, _ in progress] == [(1, 3), (2, 3), (3, 3)]
    for exported in report.paths:
        with Image.open(exported) as image:
            image.load()
            assert image.format == "JPEG" and image.size == (256, 256)
            assert image.mode == "RGB"
            assert JpegImagePlugin.get_sampling(image) == 0
            # Standard JPEG luminance table scaled for quality 99. Checking
            # both ends distinguishes the 99 output from quality 95 and 100.
            assert image.quantization[0][0] == 1
            assert image.quantization[0][63] == 2
            assert image.info["icc_profile"] == SRGB_PROFILE
            assert not image.getexif()
    assert path.read_bytes() == before
    assert not list((tmp_path / "export").glob(".insta-g-*.tmp"))


def test_export_strips_source_exif_metadata(tmp_path: Path) -> None:
    path = tmp_path / "private.png"
    with _quadrants() as image:
        exif = Image.Exif()
        exif[270] = "private description"
        exif[274] = 6
        image.save(path, exif=exif)
    report = export_records(
        [ImageRecord(str(path), _square_settings(mode="expand"))], tmp_path / "out",
    )
    assert not report.errors
    with Image.open(report.paths[0]) as exported:
        assert not exported.getexif()
        assert "exif" not in exported.info


def test_export_continues_after_bad_input_and_invalid_settings(tmp_path: Path) -> None:
    good = _write_source(tmp_path / "good.png", (256, 256))
    records = [
        ImageRecord(str(good), Settings(blur=-1)),
        ImageRecord(str(tmp_path / "missing.png"), _square_settings(mode="expand")),
        ImageRecord(str(good), _square_settings(mode="expand")),
    ]
    progress: list[tuple[int, int]] = []
    report = export_records(
        records, tmp_path / "out",
        progress=lambda done, total, _name: progress.append((done, total)),
    )
    assert len(report.errors) == 2
    assert len(report.paths) == 1 and report.paths[0].is_file()
    assert report.completed == {str(good): records[-1].settings.to_dict()}
    assert progress == [(1, 2), (2, 2)]


def test_export_uses_settings_snapshot_for_entire_batch(tmp_path: Path) -> None:
    path = _write_source(tmp_path / "source.png", (256, 256))
    settings = _square_settings(mode="expand")
    exported_settings = settings.to_dict()
    records = [ImageRecord(str(path), settings), ImageRecord(str(path), settings)]

    def change_source_settings(_done: int, _total: int, _name: str) -> None:
        settings.ratio = 16 / 9

    report = export_records(records, tmp_path / "out", progress=change_source_settings)
    assert not report.errors
    assert len(report.paths) == 2
    assert report.completed == {str(path): exported_settings}
    for path in report.paths:
        with Image.open(path) as image:
            assert image.size == (256, 256)


def test_failed_later_tile_does_not_mark_photo_complete_and_next_photo_exports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    partial = _write_source(tmp_path / "partial.png", (96, 32))
    complete = _write_source(tmp_path / "complete.png", (32, 32))
    original_save = export_module._save_jpeg_exclusive

    def fail_second_tile(image, directory, stem, index, cancelled):
        if stem == "partial" and index == 2:
            raise OSError("simulated second tile failure")
        return original_save(image, directory, stem, index, cancelled)

    monkeypatch.setattr(export_module, "_save_jpeg_exclusive", fail_second_tile)
    complete_record = ImageRecord(str(complete), _square_settings(mode="expand"))
    report = export_records(
        [ImageRecord(str(partial), _square_settings()), complete_record], tmp_path / "out",
    )
    assert len(report.errors) == 1 and len(report.paths) == 1
    assert report.completed == {str(complete): complete_record.settings.to_dict()}
    assert all(path.is_file() for path in report.paths)


def test_completed_photo_stays_reported_if_a_later_photo_fails(tmp_path: Path) -> None:
    source = _write_source(tmp_path / "complete.png", (32, 32))
    complete = ImageRecord(str(source), _square_settings(mode="expand"))
    report = export_records(
        [complete, ImageRecord(str(tmp_path / "missing.png"))], tmp_path / "out",
    )
    assert len(report.paths) == len(report.errors) == 1
    assert report.completed == {str(source): complete.settings.to_dict()}


def test_duplicate_path_reports_last_successful_snapshot_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _write_source(tmp_path / "repeat.png", (32, 32))
    records = [
        ImageRecord(str(source), _square_settings(mode="expand", ratio=ratio))
        for ratio in (1, 4 / 3, 16 / 9)
    ]
    original_save = export_module._save_jpeg_exclusive
    calls = 0

    def fail_third_export(image, directory, stem, index, cancelled):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise OSError("simulated final export failure")
        return original_save(image, directory, stem, index, cancelled)

    monkeypatch.setattr(export_module, "_save_jpeg_exclusive", fail_third_export)
    report = export_records(records, tmp_path / "out")
    assert len(report.paths) == 2 and len(report.errors) == 1
    assert report.completed == {str(source): records[1].settings.to_dict()}


def test_export_output_directory_error_is_reported(tmp_path: Path) -> None:
    occupied = tmp_path / "file"
    occupied.write_text("keep", encoding="utf-8")
    report = export_records([], occupied)
    assert report.errors and not report.paths
    assert occupied.read_text(encoding="utf-8") == "keep"


def test_cancellation_before_loading_does_not_touch_missing_input(tmp_path: Path) -> None:
    report = export_records(
        [ImageRecord(str(tmp_path / "missing.png"))], tmp_path / "out", cancelled=lambda: True,
    )
    assert report.cancelled and not report.errors and not report.paths
    assert not report.completed
    assert not list((tmp_path / "out").iterdir())


def test_cancellation_after_first_tile_removes_incomplete_series(tmp_path: Path) -> None:
    source = _write_source(tmp_path / "source.png")
    stop = False

    def progress(_done: int, _total: int, _name: str) -> None:
        nonlocal stop
        stop = True

    report = export_records(
        [ImageRecord(str(source), _square_settings())], tmp_path / "out",
        progress=progress, cancelled=lambda: stop,
    )
    assert report.cancelled and not report.errors
    assert not report.paths
    assert not report.completed
    assert not list((tmp_path / "out").iterdir())


def test_cancellation_preserves_photo_finished_before_next_photo(tmp_path: Path) -> None:
    source = _write_source(tmp_path / "complete.png", (32, 32))
    complete = ImageRecord(str(source), _square_settings(mode="expand"))
    stop = False

    def stop_after_photo(_done: int, _total: int, _name: str) -> None:
        nonlocal stop
        stop = True

    report = export_records(
        [complete, ImageRecord(str(tmp_path / "missing.png"))], tmp_path / "out",
        progress=stop_after_photo, cancelled=lambda: stop,
    )
    assert report.cancelled and not report.errors and len(report.paths) == 1
    assert report.completed == {str(source): complete.settings.to_dict()}


def test_cancellation_after_encoding_removes_unpublished_temp_file(tmp_path: Path) -> None:
    source = _write_source(tmp_path / "source.png", (256, 256))
    out = tmp_path / "out"
    report = export_records(
        [ImageRecord(str(source), _square_settings(mode="expand"))], out,
        cancelled=lambda: any(out.glob(".insta-g-*.tmp")),
    )
    assert report.cancelled and not report.errors and not report.paths
    assert not list(out.iterdir())


def test_existing_exports_are_never_overwritten(tmp_path: Path) -> None:
    source = _write_source(tmp_path / "source.png", (256, 256))
    out = tmp_path / "out"
    out.mkdir()
    first, second = out / "source_01.jpg", out / "source_01_2.jpg"
    first.write_bytes(b"existing original")
    second.write_bytes(b"existing second")
    report = export_records(
        [ImageRecord(str(source), _square_settings(mode="expand"))], out,
    )
    assert not report.errors
    assert report.paths == [out / "source_01_3.jpg"]
    assert first.read_bytes() == b"existing original"
    assert second.read_bytes() == b"existing second"
    with Image.open(report.paths[0]) as image:
        image.verify()


def test_collision_during_publication_is_exclusive_and_retried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _write_source(tmp_path / "source.png", (256, 256))
    out = tmp_path / "out"
    publish_method = "rename" if os.name == "nt" else "link"
    original_publish = getattr(export_module.os, publish_method)
    attempted: list[Path] = []

    def concurrent_publish(temporary: Path, target: Path) -> None:
        attempted.append(Path(target))
        if len(attempted) == 1:
            Path(target).write_bytes(b"concurrent writer wins this name")
        original_publish(temporary, target)

    monkeypatch.setattr(export_module.os, publish_method, concurrent_publish)
    report = export_records(
        [ImageRecord(str(source), _square_settings(mode="expand"))], out,
    )
    assert not report.errors
    assert report.paths == [out / "source_01_2.jpg"]
    assert (out / "source_01.jpg").read_bytes() == b"concurrent writer wins this name"
    assert len(attempted) == 2
    assert not list(out.glob(".insta-g-*.tmp"))


def test_failed_encoding_leaves_no_temp_or_partial_jpeg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _write_source(tmp_path / "source.png", (256, 256))

    def broken_encoder(_image: Image.Image, output: object, **_kwargs: object) -> None:
        output.write(b"partial jpeg")
        raise OSError("simulated encoder failure")

    monkeypatch.setattr(Image.Image, "save", broken_encoder)
    report = export_records(
        [ImageRecord(str(source), _square_settings(mode="expand"))], tmp_path / "out",
    )
    assert len(report.errors) == 1 and not report.paths
    assert not list((tmp_path / "out").iterdir())


def test_export_streams_over_80_megapixels_without_allocating_full_canvas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A narrow 42 kpx source creates 88.2 MP of padding across 20 tiles. The
    # encoded files are real; allocation traps reject a full panorama buffer.
    source = tmp_path / "native.png"
    with Image.new("RGB", (20, 2100), "#65a3b8") as image:
        image.save(source)
    settings = _square_settings(splits=20, blur=40)
    geometry = get_geometry((20, 2100), settings)
    assert geometry.canvas_size == (42_000, 2100)
    original_new, original_transform = Image.new, Image.Image.transform
    allocations: list[tuple[int, int]] = []

    def checked_new(mode: str, size: tuple[int, int], *args: object, **kwargs: object) -> Image.Image:
        allocations.append(size)
        assert size[0] * size[1] < 10_000_000, "Allocated a complete native panorama"
        return original_new(mode, size, *args, **kwargs)

    def checked_transform(image: Image.Image, size: tuple[int, int], *args: object, **kwargs: object) -> Image.Image:
        allocations.append(size)
        assert size[0] * size[1] < 10_000_000, "Transformed a complete native panorama"
        return original_transform(image, size, *args, **kwargs)

    def forbidden_composite(*_args: object, **_kwargs: object) -> Image.Image:
        raise AssertionError("Export called the full-canvas renderer")

    monkeypatch.setattr(Image, "new", checked_new)
    monkeypatch.setattr(Image.Image, "transform", checked_transform)
    monkeypatch.setattr(imaging_module, "render_composite", forbidden_composite)
    report = export_records([ImageRecord(str(source), settings)], tmp_path / "out")
    assert not report.errors and len(report.paths) == 20
    exported_pixels = 0
    for path in report.paths:
        with Image.open(path) as jpeg:
            assert jpeg.size == (2100, 2100)
            exported_pixels += jpeg.width * jpeg.height
    assert exported_pixels == 88_200_000
    assert max(width * height for width, height in allocations) == 4_410_000


def test_jpeg_edge_limit_is_checked_per_tile_not_whole_canvas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "wide.png"
    with Image.new("RGB", (70_000, 1), "red") as image:
        image.save(source)
    # The 70k-wide full canvas is legal if individual tiles are under 65500.
    settings = Settings(splits=2, ratio_mode="fixed", ratio=16 / 9, fit_mode="fill")
    assert get_geometry((70_000, 1), settings).canvas_size == (2, 1)
    assert not export_records([ImageRecord(str(source), settings)], tmp_path / "legal").errors
    settings = Settings(mode="expand", ratio_mode="fixed", ratio=1)
    geometry = get_geometry((70_000, 1), settings)
    assert geometry.tile_width == 70_000
    with load_image(source, max_edge=2048) as thumbnail:
        with render_composite(thumbnail, settings, max_edge=2048) as preview:
            assert preview.size == (2048, 2048)
    report = export_records([ImageRecord(str(source), settings)], tmp_path / "too-large")
    assert not report.paths and len(report.errors) == 1 and "65500" in report.errors[0]


def test_tile_memory_guard_precedes_tile_allocation(monkeypatch: pytest.MonkeyPatch) -> None:
    with Image.new("RGB", (300, 100)) as image:
        requests: list[int] = []

        def no_memory(required_bytes: int, _operation: str) -> None:
            requests.append(required_bytes)
            raise MemoryError("Nedostatok RAM pre diel")

        monkeypatch.setattr(imaging_module, "ensure_memory", no_memory)
        with pytest.raises(MemoryError, match="diel"):
            next(iter_tiles(image, _square_settings()))
        assert requests == [100 * 100 * 12]


@pytest.mark.parametrize("max_edge", [None, 2048])
def test_png_ram_guard_runs_before_metadata_can_trigger_decode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, max_edge: int | None,
) -> None:
    path = tmp_path / "no-exif.png"
    with Image.new("RGB", (20, 30), "red") as fixture:
        fixture.save(path)
    decoded: list[bool] = []
    original_load = PngImagePlugin.PngImageFile.load

    def track_load(image: Image.Image, *args: object, **kwargs: object) -> object:
        decoded.append(True)
        return original_load(image, *args, **kwargs)

    def reject_allocation(_required: int, _operation: str) -> None:
        raise MemoryError("PNG needs more RAM")

    monkeypatch.setattr(PngImagePlugin.PngImageFile, "load", track_load)
    monkeypatch.setattr(imaging_module, "ensure_memory", reject_allocation)
    with pytest.raises(MemoryError, match="PNG needs more RAM"):
        load_image(path, max_edge=max_edge)
    assert decoded == []
