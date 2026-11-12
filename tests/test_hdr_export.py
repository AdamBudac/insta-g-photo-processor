"""End-to-end HDR/SDR publication, naming and per-original rollback."""

from io import BytesIO

import imagecodecs
import numpy as np
import pillow_heif
import pytest
from PIL import Image, ImageCms

from insta_g.core import hdr
from insta_g.core.export import export_records
from insta_g.core.geometry import get_geometry
from insta_g.core.models import ImageRecord, Settings


@pytest.fixture
def hdr_source(tmp_path):
    path = tmp_path / "panorama.jpg"
    rgba = np.ones((64, 192, 4), dtype=np.float16)
    rgba[..., :3] = (4, 1, 0.5)
    sdr = np.full((64, 192, 4), 128, dtype=np.uint8)
    sdr[..., 3] = 255
    path.write_bytes(imagecodecs.ultrahdr_encode(
        rgba, sdr=sdr, gamut="BT_2100", transfer="LINEAR", level=99,
        gainmap_level=99, scale=1, multichannel=True,
    ))
    return path


def _settings(hdr_mode):
    return Settings(splits=3, ratio_mode="fixed", ratio=1, fit_mode="fill", hdr_mode=hdr_mode)


def test_hdr_jpeg_exports_native_splits_with_hdr_before_index(hdr_source, tmp_path):
    original = hdr_source.read_bytes()
    output = tmp_path / "export"
    record = ImageRecord(str(hdr_source), settings=_settings("hdr"))
    report = export_records([record], output)
    assert not report.errors and not report.failed
    assert report.completed[record.path] == record.settings.to_dict()
    assert [path.name for path in report.paths] == [f"panorama_HDR_{index:02d}.jpg" for index in range(1, 4)]
    for path in report.paths:
        data = path.read_bytes()
        assert imagecodecs.ultrahdr_check(data)
        decoded = imagecodecs.ultrahdr_decode(data)
        assert decoded.shape == (64, 64, 4)
        assert float(decoded[..., :3].max()) > 3.8
    assert hdr_source.read_bytes() == original


def test_hdr_source_sdr_export_has_sdr_suffix_srgb_and_no_exif(hdr_source, tmp_path):
    output = tmp_path / "export"
    record = ImageRecord(str(hdr_source), settings=_settings("sdr"))
    report = export_records([record], output)
    assert not report.errors
    assert [path.name for path in report.paths] == [f"panorama_SDR_{index:02d}.jpg" for index in range(1, 4)]
    for path in report.paths:
        data = path.read_bytes()
        assert not imagecodecs.ultrahdr_check(data)
        with Image.open(BytesIO(data)) as image:
            assert image.size == (64, 64)
            assert image.mode == "RGB" and not image.getexif()
            profile = ImageCms.ImageCmsProfile(BytesIO(image.info["icc_profile"]))
            assert "sRGB" in ImageCms.getProfileDescription(profile)
            assert image.getpixel((12, 12)) == (128, 128, 128)


def test_native_sdr_export_never_invents_hdr_or_suffix(tmp_path):
    path = tmp_path / "normal.png"
    with Image.new("RGB", (192, 64), "green") as image:
        image.save(path)
    report = export_records([ImageRecord(str(path), settings=_settings("hdr"))], tmp_path / "export")
    assert not report.errors
    assert [result.name for result in report.paths] == [f"normal_{index:02d}.jpg" for index in range(1, 4)]
    assert all(not imagecodecs.ultrahdr_check(result.read_bytes()) for result in report.paths)


def test_heic_hdr_export_is_ten_bit_pq_and_preserves_native_geometry(hdr_source, tmp_path):
    source = tmp_path / "photo.heic"
    with hdr.load_hdr(hdr_source) as image:
        tile = hdr.HdrTile(image.rgb.copy(), image.sdr.copy())
        try:
            source.write_bytes(hdr.encode_hdr_tile(tile, hdr.HdrInfo("heif_pq")))
        finally:
            tile.close()
    settings = _settings("hdr")
    expected = get_geometry((192, 64), settings)
    report = export_records([ImageRecord(str(source), settings=settings)], tmp_path / "export")
    assert not report.errors
    assert [result.name for result in report.paths] == [f"photo_HDR_{index:02d}.heic" for index in range(1, 4)]
    for result in report.paths:
        heif = pillow_heif.open_heif(result, convert_hdr_to_8bit=False)
        assert heif.size == (expected.tile_width, expected.tile_height)
        assert heif.info["bit_depth"] == 10
        assert heif.info["nclx_profile"]["transfer_characteristics"] == 16
        assert heif.info["nclx_profile"]["color_primaries"] == 9
        with hdr.load_hdr(result) as decoded:
            assert float(decoded.rgb.max()) > 3.7


def test_failed_hdr_second_tile_rolls_back_original_and_continues(hdr_source, tmp_path, monkeypatch):
    later = tmp_path / "later.png"
    with Image.new("RGB", (192, 64), "red") as image:
        image.save(later)
    output = tmp_path / "export"
    output.mkdir()
    existing = output / "panorama_HDR_01.jpg"
    existing.write_bytes(b"Existing export must survive")
    original = hdr_source.read_bytes()
    encode = hdr.encode_hdr_tile
    calls = 0

    def fail_second(tile, info):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("Simulated HDR encoder failure")
        return encode(tile, info)

    monkeypatch.setattr(hdr, "encode_hdr_tile", fail_second)
    first = ImageRecord(str(hdr_source), settings=_settings("hdr"))
    second = ImageRecord(str(later), settings=_settings("sdr"))
    report = export_records([first, second], output)
    assert first.path in report.failed and first.path not in report.completed
    assert second.path in report.completed
    assert report.processed_count == 2
    assert [path.name for path in report.paths] == [f"later_{index:02d}.jpg" for index in range(1, 4)]
    assert existing.read_bytes() == b"Existing export must survive"
    assert sorted(path.name for path in output.iterdir()) == sorted([existing.name, *[path.name for path in report.paths]])
    assert hdr_source.read_bytes() == original
