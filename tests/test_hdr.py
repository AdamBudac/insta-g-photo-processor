"""Verify real HDR pixels, colour interpretation and native streaming geometry."""

import struct
from io import BytesIO
from pathlib import Path

import imagecodecs
import numpy as np
import pillow_heif
import pytest
from PIL import Image

from insta_g.core import hdr
from insta_g.core.geometry import get_geometry
from insta_g.core.hdr_metadata import read_iso_gainmap_metadata, read_iso_structure
from insta_g.core.imaging import load_image
from insta_g.core.models import Settings


def _ultrahdr(path: Path, *, gamut: str = "BT_2100", sdr: bool = True) -> np.ndarray:
    rgba = np.ones((48, 64, 4), dtype=np.float16)
    rgba[:, :32, :3] = (4, 1, 0.5)
    rgba[:, 32:, :3] = (0.2, 1.5, 3)
    companion = np.full(rgba.shape, 128, dtype=np.uint8)
    companion[..., 3] = 255
    path.write_bytes(imagecodecs.ultrahdr_encode(
        rgba, level=99, gamut=gamut, transfer="LINEAR", scale=1,
        gainmap_level=99, multichannel=True, sdr=companion if sdr else None,
    ))
    return rgba[..., :3].astype(np.float32)


def test_ultrahdr_keeps_real_headroom_and_alternate_gamut(tmp_path):
    path = tmp_path / "hdr.jpg"
    expected = _ultrahdr(path)
    info = hdr.detect_hdr(path)
    assert info.is_hdr and info.supported and info.kind == "ultrahdr"
    with hdr.load_hdr(path) as image:
        assert image.size == (64, 48)
        assert image.rgb.dtype == np.float32
        assert image.rgb.max() > 3.8
        np.testing.assert_allclose(image.rgb[12, 12], expected[12, 12], rtol=0.04, atol=0.01)
        np.testing.assert_allclose(image.rgb[12, 52], expected[12, 52], rtol=0.04, atol=0.01)
        # Camera-authored SDR companion is a real rendition, not clipped HDR.
        assert image.sdr.getpixel((12, 12)) == (128, 128, 128)
    with load_image(path, max_edge=24) as preview:
        assert preview.size == (24, 18)
        assert preview.mode == "RGB"
        assert preview.info["source_size"] == (64, 48)
        assert preview.info["hdr_info"]["is_hdr"] is True


def test_base_display_p3_gamut_is_converted_to_linear_bt2020(tmp_path):
    path = tmp_path / "p3.jpg"
    expected = _ultrahdr(path, gamut="DISPLAY_P3", sdr=False)
    with hdr.load_hdr(path) as image:
        correct = hdr._change_gamut(expected, 12)
        np.testing.assert_allclose(image.rgb[12, 12], correct[12, 12], rtol=0.04, atol=0.01)


def test_hdr_jpeg_reencode_keeps_gain_map_and_strips_exif(tmp_path):
    source = tmp_path / "hdr.jpg"
    _ultrahdr(source)
    with hdr.load_hdr(source) as image:
        tile = hdr.HdrTile(image.rgb.copy(), image.sdr.copy())
        try:
            encoded = hdr.encode_hdr_tile(tile, image.info)
        finally:
            tile.close()
    assert imagecodecs.ultrahdr_check(encoded)
    decoded = imagecodecs.ultrahdr_decode(encoded)
    assert decoded[..., :3].max() > 3.8
    with Image.open(BytesIO(encoded)) as output:
        assert not output.getexif()
        assert "icc_profile" in output.info


def test_pq_heic_contains_ten_bit_pq_bt2020_and_round_trips(tmp_path):
    source = tmp_path / "hdr.jpg"
    _ultrahdr(source)
    target = tmp_path / "hdr.heic"
    with hdr.load_hdr(source) as image:
        tile = hdr.HdrTile(image.rgb.copy(), image.sdr.copy())
        try:
            target.write_bytes(hdr.encode_hdr_tile(tile, hdr.HdrInfo("heif_pq")))
        finally:
            tile.close()
    heif = pillow_heif.open_heif(target, convert_hdr_to_8bit=False)
    assert heif.info["bit_depth"] == 10
    assert heif.info["nclx_profile"]["color_primaries"] == 9
    assert heif.info["nclx_profile"]["transfer_characteristics"] == 16
    assert heif.info["exif"] is None
    assert hdr.detect_hdr(target).kind == "heif_pq"
    with hdr.load_hdr(target) as image:
        np.testing.assert_allclose(image.rgb[12, 12], (4, 1, 0.5), rtol=0.05, atol=0.02)
        assert image.sdr.mode == "RGB"
    with load_image(target, max_edge=20) as preview:
        assert max(preview.size) == 20
        assert preview.info["source_size"] == (64, 48)


def test_ten_bit_sdr_heic_is_not_misclassified_as_hdr(tmp_path):
    path = tmp_path / "sdr.heic"
    data = np.full((32, 32, 3), 20000, dtype="<u2")
    heif = pillow_heif.from_bytes("RGB;16", (32, 32), data.tobytes())
    heif.save(path, color_primaries=9, transfer_characteristics=13)
    assert not hdr.detect_hdr(path).is_hdr
    with pytest.raises(ValueError, match="SDR"):
        hdr.load_hdr(path)


def test_pq_curve_uses_absolute_luminance_and_is_reversible():
    relative = np.array([0, 0.01, 1, 1000 / 203, 10000 / 203], dtype=np.float32)
    encoded = hdr._linear_to_pq(relative)
    assert encoded[2] == pytest.approx(0.58069, abs=0.0001)
    np.testing.assert_allclose(hdr._pq_to_linear(encoded), relative, rtol=0.0003, atol=0.0001)


def test_hlg_reference_display_is_1000_nits():
    value = hdr._hlg_to_linear(np.ones((1, 1, 3), dtype=np.float32), 9)
    np.testing.assert_allclose(value, 1000 / 203, rtol=0.0001)


@pytest.mark.parametrize("offset_x, offset_y", [(-1, -1), (0, 0), (1, 1)])
def test_hdr_fit_preserves_every_native_foreground_pixel(offset_x, offset_y):
    rgb = np.arange(100 * 80 * 3, dtype=np.float32).reshape(80, 100, 3) / 6000
    image = hdr.HdrImage(rgb, Image.new("RGB", (100, 80), "gray"), hdr.HdrInfo("ultrahdr"))
    settings = Settings(splits=3, ratio_mode="fixed", ratio=4 / 3, fit_mode="fit", background_mode="solid", background_color="#3080C0", offset_x=offset_x, offset_y=offset_y)
    geometry = get_geometry(image.size, settings)
    tiles = list(hdr.iter_hdr_tiles(image, settings))
    try:
        panorama = np.concatenate([tile.rgb for tile in tiles], axis=1)
        left, top, right, bottom = geometry.foreground_box
        np.testing.assert_array_equal(panorama[top:bottom, left:right], rgb)
        expected = hdr._change_gamut(np.where(np.array([48, 128, 192], dtype=np.float32) / 255 <= 0.04045, np.array([48, 128, 192], dtype=np.float32) / (255 * 12.92), ((np.array([48, 128, 192], dtype=np.float32) / 255 + .055) / 1.055) ** 2.4), 1)
        assert np.any(np.all(np.isclose(panorama, expected), axis=2))
    finally:
        for tile in tiles:
            tile.close()
        image.close()


def test_hdr_blur_preserves_values_above_sdr_and_cancel_skips_render(monkeypatch):
    rgb = np.full((40, 80, 3), 4, dtype=np.float32)
    image = hdr.HdrImage(rgb, Image.new("RGB", (80, 40), "gray"), hdr.HdrInfo("ultrahdr"))
    settings = Settings(mode="expand", ratio=3 / 4, blur=8)
    tiles = list(hdr.iter_hdr_tiles(image, settings))
    try:
        assert np.min(tiles[0].rgb) > 3.99
        monkeypatch.setattr(hdr, "_backgrounds", lambda *_args: pytest.fail("Cancelled rendering started"))
        assert list(hdr.iter_hdr_tiles(image, settings, lambda: True)) == []
    finally:
        for tile in tiles:
            tile.close()
        image.close()


def test_real_iso_heic_hidden_gainmap_decodes_without_source_writes():
    path = Path(__file__).parent / "fixtures/hdr/gainmap_hevc_16x16.heic"
    before = path.read_bytes()
    assert hdr.detect_hdr(path).kind == "iso_gainmap"
    structure = read_iso_structure(before)
    metadata = read_iso_gainmap_metadata(structure.metadata)
    assert structure.gainmap_id != structure.base_id
    assert metadata["channels"][0][1] == pytest.approx(2.3004484)
    with hdr.load_hdr(path) as image:
        assert image.size == (16, 16)
        assert np.isfinite(image.rgb).all()
        assert image.rgb.max() == pytest.approx(0.24941, abs=0.002)
    assert path.read_bytes() == before


def test_invalid_iso_metadata_denominator_is_rejected():
    # version 0, single channel, common denominator present and zero.
    with pytest.raises(ValueError, match="menovateľ"):
        read_iso_gainmap_metadata(struct.pack(">HHBIII", 0, 0, 8, 0, 0, 0))


def test_malformed_hdr_jpeg_never_silently_becomes_sdr(tmp_path):
    path = tmp_path / "broken.jpg"
    with Image.new("RGB", (16, 16)) as image:
        image.save(path)
    data = path.read_bytes()
    marker = b"http://ns.adobe.com/hdr-gain-map/1.0/"
    path.write_bytes(data[:2] + b"\xff\xe1" + struct.pack(">H", len(marker) + 2) + marker + data[2:])
    info = hdr.detect_hdr(path)
    assert info.is_hdr and not info.supported
    with pytest.raises(ValueError, match="platnú HDR"):
        load_image(path)


def test_sdr_jpeg_detection_does_not_decode_gainmap_or_read_whole_file(tmp_path, monkeypatch):
    path = tmp_path / "sdr.jpg"
    with Image.new("RGB", (64, 48), "green") as image:
        image.save(path)
    monkeypatch.setattr(imagecodecs, "ultrahdr_check", lambda *_args: pytest.fail("SDR entered gainmap codec"))
    assert not hdr.detect_hdr(path).is_hdr
    # Cached result also avoids reopening an unchanged source.
    monkeypatch.setattr(Path, "open", lambda *_args, **_kwargs: pytest.fail("Unchanged detection was not cached"))
    assert not hdr.detect_hdr(path).is_hdr


def test_jpeg_hdr_exif_orientation_rotates_both_renditions(tmp_path):
    source = tmp_path / "oriented.jpg"
    _ultrahdr(source)
    with hdr.load_hdr(source) as original:
        expected = np.rot90(original.rgb, 3).copy()
    exif = Image.Exif()
    exif[274] = 6
    payload = exif.tobytes()
    data = source.read_bytes()
    source.write_bytes(data[:2] + b"\xff\xe1" + struct.pack(">H", len(payload) + 2) + payload + data[2:])
    with hdr.load_hdr(source) as rotated:
        assert rotated.size == (48, 64)
        assert rotated.sdr.size == rotated.size
        np.testing.assert_array_equal(rotated.rgb, expected)


def _apple_xmp(version, headroom=None):
    extra = f"<h:HDRGainMapHeadroom>{headroom}</h:HDRGainMapHeadroom>" if headroom is not None else ""
    xml = f'<root xmlns:h="http://ns.apple.com/HDRGainMap/1.0/"><h:HDRGainMapVersion>{version}</h:HDRGainMapVersion>{extra}</root>'
    return [{"type": "mime", "content_type": "application/rdf+xml", "data": xml.encode()}]


def test_apple_v1_reads_real_tiff_makernote_calibration():
    # Apple tags 33 = 2 and 48 = 0 imply 3 stops = 8x headroom.
    maker = b"Apple iOS\x00\x00\x01MM" + struct.pack(">H", 2)
    maker += struct.pack(">HHIIHHII", 33, 10, 1, 40, 48, 10, 1, 48)
    maker += struct.pack(">iiii", 2, 1, 0, 1)
    exif = Image.Exif()
    exif[34665] = {37500: maker}
    headroom, logarithmic = hdr._apple_parameters(exif.tobytes(), _apple_xmp(65536))
    assert headroom == 8 and logarithmic is False


def test_apple_v2_reads_log2_headroom_and_rejects_unknown_versions():
    assert hdr._apple_parameters(None, _apple_xmp(131072, 2)) == (4, True)
    with pytest.raises(ValueError, match="verzia"):
        hdr._apple_parameters(None, _apple_xmp(999999))
    with pytest.raises(ValueError, match="jasový rozsah"):
        hdr._apple_parameters(None, _apple_xmp(131072, "nan"))


def test_sdr_tone_mapping_keeps_distinct_hdr_highlights():
    rgb = np.repeat(np.array([0.1, 1, 10], dtype=np.float32)[None, :, None], 3, axis=2)
    with hdr._tone_map(rgb) as image:
        values = [image.getpixel((index, 0))[0] for index in range(3)]
        assert 0 < values[0] < values[1] < values[2] <= 255


def test_hdr_encoder_rejects_values_outside_pq_luminance_range():
    tile = hdr.HdrTile(np.full((16, 16, 3), 100, dtype=np.float32), Image.new("RGB", (16, 16)))
    try:
        with pytest.raises(ValueError, match="10000"):
            hdr.encode_hdr_tile(tile, hdr.HdrInfo("heif_pq"))
    finally:
        tile.close()


@pytest.mark.parametrize("shape,sigma", [((5, 7, 3), 2.3), ((2, 3, 3), 1000), ((1, 9, 3), 8)])
def test_hdr_blur_matches_edge_extended_reference_without_radius_sized_padding(shape, sigma, monkeypatch):
    original = np.random.default_rng(42).uniform(1.5, 9, shape).astype(np.float32)
    expected = original.copy()
    width = max(1, int(np.sqrt(4 * sigma * sigma + 1)))
    width = width if width % 2 else width - 1
    radius = width // 2
    # Independent, literal edge-extended windows are practical for tiny rasters.
    for _ in range(3):
        for axis in (0, 1):
            padding = [(0, 0)] * 3
            padding[axis] = (radius, radius)
            padded = np.pad(expected, padding, mode="edge")
            result = np.empty_like(expected)
            for index in range(shape[axis]):
                window = [slice(None)] * 3
                window[axis] = slice(index, index + width)
                target = [slice(None)] * 3
                target[axis] = index
                result[tuple(target)] = padded[tuple(window)].mean(axis=axis, dtype=np.float64)
            expected = result
    monkeypatch.setattr(hdr.np, "pad", lambda *_args, **_kwargs: pytest.fail("HDR blur allocated radius-sized padding"))
    actual = hdr._blur_float(original, sigma)
    assert actual.dtype == np.float32 and actual.min() > 1
    np.testing.assert_allclose(actual, expected, rtol=1e-6, atol=1e-6)


def test_hdr_blur_memory_estimate_is_independent_of_radius(monkeypatch):
    image = np.linspace(2, 8, 2000 * 3, dtype=np.float32).reshape(1, 2000, 3)
    estimates = []
    monkeypatch.setattr(hdr, "ensure_memory", lambda required, _operation: estimates.append(required))
    small = hdr._blur_float(image, 8)
    smaller_kernel_estimates = estimates.copy()
    estimates.clear()
    large = hdr._blur_float(image, 1000)
    assert estimates == smaller_kernel_estimates
    assert max(estimates) < 1024 * 1024
    assert small.shape == large.shape == image.shape
    assert np.isfinite(large).all() and large.min() > 1


def test_hdr_fill_skips_background_and_keeps_exact_native_crop(monkeypatch):
    rgb = np.arange(25 * 101 * 3, dtype=np.float32).reshape(25, 101, 3) / 1000
    image = hdr.HdrImage(rgb, Image.new("RGB", (101, 25), "gray"), hdr.HdrInfo("ultrahdr"))
    settings = Settings(splits=3, ratio_mode="fixed", ratio=1, fit_mode="fill")
    geometry = get_geometry(image.size, settings)
    monkeypatch.setattr(hdr, "_backgrounds", lambda *_args: pytest.fail("Fill rendered an unused HDR background"))
    tiles = list(hdr.iter_hdr_tiles(image, settings))
    try:
        panorama = np.concatenate([tile.rgb for tile in tiles], axis=1)
        left, top, _, _ = geometry.foreground_box
        width, height = geometry.canvas_size
        np.testing.assert_array_equal(panorama, rgb[-top:-top + height, -left:-left + width])
        assert panorama.max() > 1
    finally:
        for tile in tiles:
            tile.close()
        image.close()


def test_iso_native_sdr_preview_matches_authored_base_without_hdr_float(monkeypatch):
    path = Path(__file__).parent / "fixtures/hdr/gainmap_hevc_16x16.heic"
    with hdr.load_hdr(path) as decoded:
        expected = decoded.sdr.copy()
    monkeypatch.setattr(hdr, "load_hdr", lambda *_args, **_kwargs: pytest.fail("Authored SDR base reconstructed HDR pixels"))
    try:
        assert hdr.sdr_decode_bytes_per_pixel(path) == 16
        with hdr.load_hdr_sdr(path) as actual:
            assert actual.size == expected.size
            assert actual.tobytes() == expected.tobytes()
            assert actual.info["icc_profile"] == expected.info["icc_profile"]
            assert actual.info["hdr_info"]["kind"] == "iso_gainmap"
    finally:
        expected.close()


def test_iso_authored_sdr_rejects_unknown_hdr_gamut(monkeypatch):
    from dataclasses import replace

    path = Path(__file__).parent / "fixtures/hdr/gainmap_hevc_16x16.heic"
    real_structure = hdr.read_iso_structure(path.read_bytes())
    monkeypatch.setattr(hdr, "read_iso_structure", lambda _data: replace(real_structure, alternate_primaries=999, alternate_icc=None))
    with pytest.raises(ValueError, match="gamut"):
        hdr.load_hdr_sdr(path)
