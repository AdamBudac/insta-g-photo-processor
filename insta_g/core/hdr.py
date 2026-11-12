"""HDR detection, colour-managed SDR renditions and native-resolution HDR tiles.

The working space is float32, linear BT.2020, with 1.0 = 203 cd/m².
Eight-bit gain-map base images are SDR renditions, never the HDR pixel data.
"""

from __future__ import annotations

import math
import struct
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Callable, Iterator

import imagecodecs
import numpy as np
import pillow_heif
from PIL import ExifTags, Image, ImageCms, ImageFilter, ImageOps

from .geometry import get_geometry
from .hdr_metadata import read_iso_gainmap_metadata, read_iso_structure
from .models import MAX_PREVIEW_EDGE, Settings
from .raster import bounded_crop
from .resources import ensure_memory

_APPLE_AUX = "urn:com:apple:photo:2020:aux:hdrgainmap"
_PRIMARIES = {
    1: (0.64, 0.33, 0.30, 0.60, 0.15, 0.06),
    9: (0.708, 0.292, 0.170, 0.797, 0.131, 0.046),
    12: (0.680, 0.320, 0.265, 0.690, 0.150, 0.060),
}
_D65 = (0.3127, 0.3290)
_SRGB = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()


@dataclass(frozen=True)
class HdrInfo:
    kind: str = "sdr"
    description: str = "SDR"
    error: str = ""

    @property
    def is_hdr(self) -> bool:
        return self.kind != "sdr"

    @property
    def supported(self) -> bool:
        return not self.error

    def to_dict(self) -> dict[str, str | bool]:
        return {**asdict(self), "is_hdr": self.is_hdr, "supported": self.supported}


@dataclass
class HdrImage:
    rgb: np.ndarray
    sdr: Image.Image
    info: HdrInfo

    @property
    def size(self) -> tuple[int, int]:
        return self.rgb.shape[1], self.rgb.shape[0]

    def close(self) -> None:
        self.sdr.close()
        self.rgb = np.empty((0, 0, 3), dtype=np.float32)

    def __enter__(self) -> HdrImage:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


@dataclass
class HdrTile:
    rgb: np.ndarray
    sdr: Image.Image

    def close(self) -> None:
        self.sdr.close()
        self.rgb = np.empty((0, 0, 3), dtype=np.float32)


def _boxes(data: bytes, start: int, end: int) -> Iterator[tuple[bytes, int, int]]:
    while start + 8 <= end:
        size, kind = struct.unpack_from(">I4s", data, start)
        header = 8
        if size == 1:
            if start + 16 > end:
                raise ValueError("Neúplná štruktúra HEIF.")
            size = struct.unpack_from(">Q", data, start + 8)[0]
            header = 16
        elif size == 0:
            size = end - start
        if size < header or start + size > end:
            raise ValueError("Neplatná veľkosť položky HEIF.")
        yield kind, start + header, start + size
        start += size


def _heif_meta(path: str | Path) -> bytes:
    """Read only the top-level metadata box, without reading photo payloads."""
    with Path(path).open("rb") as stream:
        total = Path(path).stat().st_size
        position = 0
        while position + 8 <= total:
            stream.seek(position)
            size, kind = struct.unpack(">I4s", stream.read(8))
            header = 8
            if size == 1:
                size = struct.unpack(">Q", stream.read(8))[0]
                header = 16
            elif size == 0:
                size = total - position
            if size < header or position + size > total:
                raise ValueError("Neplatná štruktúra HEIF.")
            if kind == b"meta":
                ensure_memory(size * 3, "Čítanie HDR metadát")
                return stream.read(size - header)
            position += size
    return b""


def _heif_has_tmap(path: str | Path) -> bool:
    metadata = _heif_meta(path)
    if len(metadata) < 4:
        return False
    for kind, start, end in _boxes(metadata, 4, len(metadata)):
        if kind != b"iinf":
            continue
        version = metadata[start]
        for item_kind, item_start, item_end in _boxes(metadata, start + (6 if version == 0 else 8), end):
            if item_kind == b"infe" and metadata[item_start] in (2, 3):
                offset = item_start + (8 if metadata[item_start] == 2 else 10)
                if metadata[offset:offset + 4] == b"tmap":
                    return True
    return False


def detect_hdr(path: str | Path) -> HdrInfo:
    """Cache metadata only until the source file's size or modification changes."""
    source = Path(path).resolve()
    stat = source.stat()
    return _detect_hdr_cached(str(source), stat.st_size, stat.st_mtime_ns)


def _jpeg_might_have_gainmap(path: str | Path) -> bool:
    with Path(path).open("rb") as stream:
        if stream.read(2) != b"\xff\xd8":
            return False
        while True:
            prefix = stream.read(1)
            if prefix != b"\xff":
                return False
            marker = stream.read(1)
            while marker == b"\xff":
                marker = stream.read(1)
            if not marker or marker in (b"\xda", b"\xd9"):
                return False
            if marker in (b"\x01", *[bytes([value]) for value in range(0xd0, 0xd8)]):
                continue
            length_bytes = stream.read(2)
            if len(length_bytes) != 2:
                return False
            length = int.from_bytes(length_bytes, "big") - 2
            if length < 0:
                return False
            payload = stream.read(length)
            if any(value in payload for value in (b"MPF\x00", b"hdr-gain-map", b"hdrgainmap", b"hdrgm:", b"urn:iso:std:iso:ts:21496")):
                return True


@lru_cache(maxsize=512)
def _detect_hdr_cached(path: str, _size: int, _mtime: int) -> HdrInfo:
    """Detect actual transfer/gain-map signalling, never HDR-looking colours."""
    suffix = Path(path).suffix.lower()
    if suffix in {".heic", ".heif"}:
        heif = pillow_heif.open_heif(path, convert_hdr_to_8bit=False)
        aux = heif.info.get("aux", {})
        if _heif_has_tmap(path):
            return HdrInfo("iso_gainmap", "HEIC · ISO HDR gain map")
        if _APPLE_AUX in aux:
            return HdrInfo("apple_gainmap", "HEIC · Apple HDR gain map")
        profile = heif.info.get("nclx_profile", {})
        transfer = profile.get("transfer_characteristics")
        if transfer is None:
            transfer = profile.get("transfer_characteristic")
        if transfer in (16, 18):
            kind = "heif_pq" if transfer == 16 else "heif_hlg"
            error = ""
            if profile.get("color_primaries") not in _PRIMARIES:
                error = "HDR HEIC má nepodporované farebné primárne zložky."
            if heif.info.get("bit_depth", 8) < 10:
                error = "HDR HEIC musí obsahovať aspoň 10-bitové obrazové dáta."
            return HdrInfo(kind, "HEIC · " + ("PQ HDR" if transfer == 16 else "HLG HDR"), error)
        if any("hdr" in key.lower() or "gainmap" in key.lower() for key in aux):
            return HdrInfo("unsupported", "Neznáma HEIC HDR gain mapa", "Tento typ HDR gain mapy zatiaľ nie je podporovaný.")
        return HdrInfo()
    if suffix in {".jpg", ".jpeg"}:
        if not _jpeg_might_have_gainmap(path):
            return HdrInfo()
        ensure_memory(Path(path).stat().st_size * 4, "Čítanie JPEG HDR metadát")
        data = Path(path).read_bytes()
        if imagecodecs.ultrahdr_check(data):
            return HdrInfo("ultrahdr", "JPEG · HDR gain map")
        if any(marker in data for marker in (b"hdr-gain-map", b"hdrgainmap", b"hdrgm:", b"urn:iso:std:iso:ts:21496")):
            return HdrInfo("unsupported", "Neplatná JPEG HDR gain mapa", "JPEG obsahuje HDR metadáta, ale platnú HDR gain mapu sa nepodarilo dekódovať.")
    return HdrInfo()


@lru_cache(maxsize=8)
def _linear_profile(primaries: int = 9) -> bytes:
    return imagecodecs.cms_profile("rgb", whitepoint=_D65, primaries=_PRIMARIES[primaries], gamma=1.0)


def _profile_with_linear_trc(profile: bytes) -> bytes:
    """Keep the ICC colourants/adaptation; replace only the RGB transfer curves."""
    if len(profile) < 132 or profile[16:20] != b"RGB ":
        raise ValueError("HDR má nepodporovaný alebo poškodený farebný profil ICC.")
    result = bytearray(profile)
    count = struct.unpack_from(">I", profile, 128)[0]
    if 132 + count * 12 > len(profile):
        raise ValueError("Poškodená tabuľka farebného profilu HDR.")
    found = set()
    for index in range(count):
        entry = 132 + index * 12
        tag, offset, size = struct.unpack_from(">4sII", profile, entry)
        if tag in {b"rTRC", b"gTRC", b"bTRC"}:
            if size < 12 or offset + size > len(profile):
                raise ValueError("Poškodená prenosová krivka farebného profilu HDR.")
            result[offset:offset + 12] = b"curv" + bytes(8)
            struct.pack_into(">I", result, entry + 8, 12)
            found.add(tag)
    if len(found) != 3:
        raise ValueError("HDR farebný profil musí obsahovať RGB prenosové krivky.")
    return bytes(result)


def _transform_linear(rgb: np.ndarray, source_profile: bytes) -> np.ndarray:
    return imagecodecs.cms_transform(
        np.ascontiguousarray(rgb, dtype=np.float32),
        _profile_with_linear_trc(source_profile), _linear_profile(),
        outdtype=np.float32, intent="RELATIVE_COLORIMETRIC",
    )


def _srgb_image(image: Image.Image) -> Image.Image:
    rgb = image.convert("RGB")
    profile = image.info.get("icc_profile")
    if profile:
        try:
            converted = ImageCms.profileToProfile(rgb, ImageCms.ImageCmsProfile(BytesIO(profile)), ImageCms.ImageCmsProfile(BytesIO(_SRGB)), outputMode="RGB")
        except (OSError, ValueError, TypeError, ImageCms.PyCMSError) as exc:
            rgb.close()
            raise ValueError("Farebný profil HDR bázy sa nepodarilo previesť do sRGB.") from exc
        rgb.close()
        rgb = converted
    rgb.info.clear()
    rgb.info["icc_profile"] = _SRGB
    return rgb


def _orient_array(rgb: np.ndarray, orientation: int) -> np.ndarray:
    transforms = {
        2: lambda a: a[:, ::-1], 3: lambda a: a[::-1, ::-1],
        4: lambda a: a[::-1], 5: lambda a: a.transpose(1, 0, 2),
        6: lambda a: np.rot90(a, 3), 7: lambda a: a.transpose(1, 0, 2)[::-1, ::-1],
        8: lambda a: np.rot90(a, 1),
    }
    return np.ascontiguousarray(transforms[orientation](rgb) if orientation in transforms else rgb)


def _gainmap_jpeg(path: str | Path, *, pixels: bool) -> tuple[np.ndarray | None, Image.Image]:
    data = Path(path).read_bytes()
    base, gainmap, metadata = imagecodecs.ultrahdr_decode_jpeg(data)
    with Image.open(BytesIO(base)) as image:
        ensure_memory(image.width * image.height * (72 if pixels else 16), "Dekódovanie HDR fotografie")
        orientation = image.getexif().get(274, 1)
        sdr = _srgb_image(ImageOps.exif_transpose(image))
        base_profile = image.info.get("icc_profile", _SRGB)
    with Image.open(BytesIO(gainmap)) as image:
        profile = base_profile if metadata["use_base_cg"] else image.info.get("icc_profile")
    if not profile:
        sdr.close()
        raise ValueError("HDR gain mapa neurčuje svoj výstupný farebný gamut.")
    # Validate even the SDR preview so a malformed HDR profile cannot look ready.
    _profile_with_linear_trc(profile)
    if not pixels:
        return None, sdr
    try:
        decoded = imagecodecs.ultrahdr_decode(data, dtype=np.float16)
        rgb = _transform_linear(decoded[..., :3], profile)
        rgb = _orient_array(rgb, orientation)
        return rgb, sdr
    except Exception:
        sdr.close()
        raise


def _pq_to_linear(value: np.ndarray) -> np.ndarray:
    m1, m2 = 2610 / 16384, 2523 / 32
    c1, c2, c3 = 3424 / 4096, 2413 / 128, 2392 / 128
    powered = np.maximum(value, 0) ** (1 / m2)
    return ((np.maximum(powered - c1, 0) / np.maximum(c2 - c3 * powered, 1e-12)) ** (1 / m1) * (10000 / 203)).astype(np.float32)


def _linear_to_pq(value: np.ndarray) -> np.ndarray:
    powered = np.maximum(value * (203 / 10000), 0) ** (2610 / 16384)
    return ((3424 / 4096 + (2413 / 128) * powered) / (1 + (2392 / 128) * powered)) ** (2523 / 32)


def _hlg_to_linear(value: np.ndarray, primaries: int) -> np.ndarray:
    a, b, c = 0.17883277, 0.28466892, 0.55991073
    scene = np.where(value <= 0.5, value * value / 3, (np.exp((value - c) / a) + b) / 12)
    # BT.2100 reference HLG display: 1000 cd/m² peak, system gamma 1.2.
    luminance = scene @ _rgb_to_xyz(primaries)[1]
    return (scene * np.maximum(luminance, 0)[..., None] ** 0.2 * (1000 / 203)).astype(np.float32)


@lru_cache(maxsize=3)
def _rgb_to_xyz(primaries: int) -> np.ndarray:
    xy = np.asarray(_PRIMARIES[primaries], dtype=np.float64).reshape(3, 2)
    matrix = np.stack((xy[:, 0] / xy[:, 1], np.ones(3), (1 - xy.sum(axis=1)) / xy[:, 1]))
    white = np.array([_D65[0] / _D65[1], 1, (1 - sum(_D65)) / _D65[1]])
    return matrix * np.linalg.solve(matrix, white)


def _change_gamut(rgb: np.ndarray, source: int, destination: int = 9) -> np.ndarray:
    matrix = np.linalg.solve(_rgb_to_xyz(destination), _rgb_to_xyz(source))
    return np.asarray(rgb @ matrix.T, dtype=np.float32)


def _tone_map(rgb: np.ndarray) -> Image.Image:
    """Global extended Reinhard luminance mapping, followed by gamut compression."""
    ensure_memory(rgb.shape[0] * rgb.shape[1] * 112, "Prevádzanie HDR do SDR")
    luminance = np.maximum(rgb @ _rgb_to_xyz(9)[1].astype(np.float32), 0)
    white = max(1.0, float(luminance.max()))
    mapped = luminance * (1 + luminance / (white * white)) / (1 + luminance)
    scale = np.divide(mapped, luminance, out=np.zeros_like(mapped), where=luminance > 1e-10)
    color = _change_gamut(rgb * scale[..., None], 9, 1)
    neutral = mapped[..., None]
    delta = color - neutral
    limits = np.ones_like(delta)
    np.divide(1 - neutral, delta, out=limits, where=delta > 1e-10)
    np.divide(-neutral, delta, out=limits, where=delta < -1e-10)
    color = neutral + delta * np.minimum(1, np.min(limits, axis=2))[..., None]
    color = np.clip(color, 0, 1)
    encoded = np.where(color <= 0.0031308, color * 12.92, 1.055 * color ** (1 / 2.4) - 0.055)
    image = Image.fromarray(np.rint(encoded * 255).astype(np.uint8))
    image.info["icc_profile"] = _SRGB
    return image


def _apple_headroom(exif: bytes | None) -> float:
    if not exif:
        raise ValueError("Apple HDR gain mape chýbajú expozičné metadáta.")
    parsed = Image.Exif()
    parsed.load(exif)
    maker = parsed.get_ifd(ExifTags.IFD.Exif).get(37500, b"")
    if not isinstance(maker, bytes) or not maker.startswith(b"Apple iOS\x00") or len(maker) < 16:
        raise ValueError("Apple HDR gain mapa nemá platné Apple MakerNote metadáta.")
    endian = ">" if maker[12:14] == b"MM" else "<" if maker[12:14] == b"II" else ""
    if not endian:
        raise ValueError("Neznáme poradie bajtov Apple HDR metadát.")
    count = struct.unpack_from(endian + "H", maker, 14)[0]
    if 16 + count * 12 > len(maker):
        raise ValueError("Poškodené Apple HDR metadáta.")
    values = {}
    for index in range(count):
        tag, datatype, length, offset = struct.unpack_from(endian + "HHII", maker, 16 + index * 12)
        if tag not in (33, 48):
            continue
        if length != 1:
            continue
        if datatype == 10 and offset + 8 <= len(maker):
            numerator, denominator = struct.unpack_from(endian + "ii", maker, offset)
            if denominator:
                values[tag] = numerator / denominator
        elif datatype == 11:
            values[tag] = struct.unpack_from(endian + "f", maker, 24 + index * 12)[0]
    if set(values) != {33, 48} or not all(math.isfinite(value) for value in values.values()):
        raise ValueError("Apple HDR gain mape chýbajú platné hodnoty 33/48 pre jasový rozsah.")
    # Apple AppKit: Applying Apple HDR effect to your photos.
    first, second = values[33], values[48]
    if first < 1:
        stops = -20 * second + 1.8 if second <= 0.01 else -0.101 * second + 1.601
    else:
        stops = -70 * second + 3 if second <= 0.01 else -0.303 * second + 2.303
    headroom = 2 ** max(stops, 0)
    if not math.isfinite(headroom) or headroom > 10000 / 203:
        raise ValueError("Apple HDR gain mapa má neplatný jasový rozsah.")
    return headroom


def _apple_parameters(exif: bytes | None, metadata: list[dict]) -> tuple[float, bool]:
    values: dict[str, str] = {}
    namespace = "{http://ns.apple.com/HDRGainMap/1.0/}"
    for item in metadata:
        if item.get("type") != "mime" or item.get("content_type") != "application/rdf+xml":
            continue
        xml = item.get("data", b"")
        if not isinstance(xml, bytes) or b"<!DOCTYPE" in xml.upper() or b"<!ENTITY" in xml.upper():
            raise ValueError("Neplatné XML metadáta Apple HDR gain mapy.")
        try:
            root = ET.fromstring(xml)
        except ET.ParseError as exc:
            raise ValueError("Poškodené XML metadáta Apple HDR gain mapy.") from exc
        for element in root.iter():
            if element.tag.startswith(namespace) and element.text:
                values[element.tag[len(namespace):]] = element.text.strip()
            for key, value in element.attrib.items():
                if key.startswith(namespace):
                    values[key[len(namespace):]] = value.strip()
    version = values.get("HDRGainMapVersion")
    if version == "65536":
        return _apple_headroom(exif), False
    if version == "131072":
        try:
            stops = float(values["HDRGainMapHeadroom"])
        except (KeyError, ValueError) as exc:
            raise ValueError("Apple HDR gain mape chýba platný HDRGainMapHeadroom.") from exc
        if not math.isfinite(stops) or not 0 <= stops <= math.log2(10000 / 203):
            raise ValueError("Apple HDR gain mapa má neplatný jasový rozsah.")
        # libultrahdr jpegrutils.cpp: Apple v2 headroom is log2 stops.
        return 2 ** stops, True
    raise ValueError("Nepodporovaná alebo chýbajúca verzia Apple HDR gain mapy.")


def _heif_pixels(path: str | Path, info: HdrInfo) -> tuple[np.ndarray, Image.Image]:
    heif = pillow_heif.open_heif(path, convert_hdr_to_8bit=False)
    ensure_memory(heif.size[0] * heif.size[1] * 80, "Dekódovanie HDR HEIC")
    if info.kind == "iso_gainmap":
        return _iso_heif_pixels(path)
    if info.kind == "apple_gainmap":
        ids = heif.info.get("aux", {}).get(_APPLE_AUX, [])
        if len(ids) != 1 or heif.mode not in {"RGB", "RGBA"}:
            raise ValueError("Apple HDR vyžaduje jednu gain mapu a 8-bitovú SDR bázu.")
        auxiliary = heif[heif.primary_index].get_aux_image(ids[0])
        gain_image = auxiliary.to_pillow().convert("L")
        if abs(gain_image.width / gain_image.height - heif.size[0] / heif.size[1]) > 0.02:
            gain_image.close()
            raise ValueError("Orientácia Apple HDR gain mapy nezodpovedá fotografii.")
        headroom, logarithmic = _apple_parameters(heif.info.get("exif"), auxiliary._c_image.metadata)
        with heif.to_pillow() as base:
            profile = base.info.get("icc_profile")
            if not profile:
                gain_image.close()
                raise ValueError("Apple HDR báze chýba farebný profil ICC.")
            rgb = imagecodecs.cms_transform(np.asarray(base.convert("RGB")), profile, _linear_profile(), outdtype=np.float32, intent="RELATIVE_COLORIMETRIC")
            sdr = _srgb_image(base)
        with gain_image:
            with gain_image.resize(heif.size, Image.Resampling.BILINEAR) as resized:
                gain = np.asarray(resized, dtype=np.float32) / 255
        if logarithmic:
            rgb *= headroom ** gain[..., None]
        else:
            # Apple v1: Rec.709 map transfer and linear headroom blend.
            gain = np.where(gain < 0.081, gain / 4.5, ((gain + 0.099) / 1.099) ** (1 / 0.45))
            rgb *= 1 + (headroom - 1) * gain[..., None]
        return rgb, sdr
    channels = 4 if heif.mode.startswith("RGBA") else 3
    if ";16" not in heif.mode:
        raise ValueError("HDR HEIC dekóder neposkytol vysokobitové dáta.")
    samples = np.frombuffer(heif.data, dtype="<u2").reshape(heif.size[1], heif.stride // 2)[:, :heif.size[0] * channels]
    bit_depth = heif.info["bit_depth"]
    # pillow-heif shifts native 10/12-bit samples into a 16-bit word; it does
    # not rescale the largest code to 65535. Undo that shift exactly.
    maximum_code = ((1 << bit_depth) - 1) << (16 - bit_depth)
    samples = samples.reshape(heif.size[1], heif.size[0], channels)[..., :3].astype(np.float32) / maximum_code
    profile = heif.info["nclx_profile"]
    primaries = profile["color_primaries"]
    rgb = _pq_to_linear(samples) if info.kind == "heif_pq" else _hlg_to_linear(samples, primaries)
    rgb = _change_gamut(rgb, primaries)
    return rgb, _tone_map(rgb)


def _iso_heif_pixels(path: str | Path) -> tuple[np.ndarray, Image.Image]:
    data = Path(path).read_bytes()
    structure = read_iso_structure(data)
    metadata = read_iso_gainmap_metadata(structure.metadata)
    heif = pillow_heif.open_heif(data, convert_hdr_to_8bit=False)
    primary = heif[heif.primary_index]
    if metadata["backward"]:
        transfer = primary.info.get("nclx_profile", {}).get("transfer_characteristics")
        primaries = primary.info.get("nclx_profile", {}).get("color_primaries")
        if transfer not in (16, 18) or primaries not in _PRIMARIES:
            raise ValueError("HDR báza ISO HEIC nemá podporovaný PQ/HLG farebný profil.")
        # The primary itself contains the full HDR intent. SDR is tone-mapped
        # from that intent, so no unsupported inverse-map assumption is needed.
        return _heif_pixels(path, HdrInfo("heif_pq" if transfer == 16 else "heif_hlg"))
    if primary.mode not in {"RGB", "RGBA"}:
        raise ValueError("ISO HDR gain mapa vyžaduje podporovanú 8-bitovú SDR bázu.")
    ensure_memory(primary.size[0] * primary.size[1] * 96 + len(data) * 4, "Rekonštrukcia ISO HDR HEIC")
    with primary.to_pillow() as base:
        profile = base.info.get("icc_profile")
        if not profile:
            raise ValueError("SDR báze ISO HDR HEIC chýba farebný profil ICC.")
        if metadata["use_base_cg"]:
            application_profile = _profile_with_linear_trc(profile)
        elif structure.alternate_icc:
            application_profile = _profile_with_linear_trc(structure.alternate_icc)
        elif structure.alternate_primaries in _PRIMARIES:
            application_profile = _linear_profile(structure.alternate_primaries)
        else:
            raise ValueError("ISO HDR gain mapa neurčuje podporovaný výstupný farebný gamut.")
        rgb = imagecodecs.cms_transform(np.asarray(base.convert("RGB")), profile, application_profile, outdtype=np.float32, intent="RELATIVE_COLORIMETRIC")
        sdr = _srgb_image(base)
    gain_image = None
    try:
        auxiliaries = {item for ids in primary.info.get("aux", {}).values() for item in ids}
        if structure.gainmap_id in auxiliaries:
            gain_image = primary.get_aux_image(structure.gainmap_id).to_pillow()
        else:
            promoted = pillow_heif.open_heif(structure.select_gainmap(data))
            gain_image = promoted[promoted.primary_index].to_pillow()
        if abs(gain_image.width / gain_image.height - primary.size[0] / primary.size[1]) > 0.02:
            raise ValueError("Orientácia ISO HDR gain mapy nezodpovedá fotografii.")
        with gain_image.convert("RGB") as color:
            with color.resize(primary.size, Image.Resampling.BILINEAR) as resized:
                gain = np.asarray(resized, dtype=np.float32) / 255
        values = np.asarray(metadata["channels"], dtype=np.float32)
        low, high, gamma, base_offset, alternate_offset = values.T
        log_gain = low + (high - low) * gain ** (1 / gamma)
        rgb = (rgb + base_offset) * np.exp2(log_gain) - alternate_offset
        rgb = imagecodecs.cms_transform(np.ascontiguousarray(rgb), application_profile, _linear_profile(), outdtype=np.float32, intent="RELATIVE_COLORIMETRIC")
        return rgb, sdr
    except Exception:
        sdr.close()
        raise
    finally:
        if gain_image is not None:
            gain_image.close()


def _iso_sdr_base(path: str | Path) -> Image.Image | None:
    """Read the authored SDR primary without reconstructing the HDR rendition."""
    ensure_memory(Path(path).stat().st_size * 4, "Čítanie HDR metadát")
    data = Path(path).read_bytes()
    structure = read_iso_structure(data)
    metadata = read_iso_gainmap_metadata(structure.metadata)
    if metadata["backward"]:
        return None
    heif = pillow_heif.open_heif(data, convert_hdr_to_8bit=False)
    primary = heif[heif.primary_index]
    if primary.mode not in {"RGB", "RGBA"}:
        raise ValueError("ISO HDR gain mapa vyžaduje podporovanú 8-bitovú SDR bázu.")
    ensure_memory(primary.size[0] * primary.size[1] * 16, "Dekódovanie SDR náhľadu HDR HEIC")
    with primary.to_pillow() as base:
        profile = base.info.get("icc_profile")
        if not profile:
            raise ValueError("SDR báze ISO HDR HEIC chýba farebný profil ICC.")
        # Validate the HDR interpretation too; an unknown gain-map colour space
        # must not silently become an apparently supported SDR-only source.
        if metadata["use_base_cg"]:
            _profile_with_linear_trc(profile)
        elif structure.alternate_icc:
            _profile_with_linear_trc(structure.alternate_icc)
        elif structure.alternate_primaries not in _PRIMARIES:
            raise ValueError("ISO HDR gain mapa neurčuje podporovaný výstupný farebný gamut.")
        return _srgb_image(base)


def sdr_decode_bytes_per_pixel(path: str | Path, info: HdrInfo | None = None) -> int:
    """Estimate peak native SDR decoding, distinguishing authored gain-map bases."""
    info = info or detect_hdr(path)
    if not info.supported:
        raise ValueError(info.error)
    if info.kind in {"sdr", "ultrahdr", "apple_gainmap"}:
        return 16
    if info.kind == "iso_gainmap":
        ensure_memory(Path(path).stat().st_size * 4, "Čítanie HDR metadát")
        structure = read_iso_structure(Path(path).read_bytes())
        metadata = read_iso_gainmap_metadata(structure.metadata)
        return 112 if metadata["backward"] else 16
    return 112


def load_hdr(path: str | Path, info: HdrInfo | None = None) -> HdrImage:
    info = info or detect_hdr(path)
    if not info.is_hdr:
        raise ValueError("SDR fotografiu nie je možné exportovať ako HDR.")
    if not info.supported:
        raise ValueError(info.error)
    if info.kind == "ultrahdr":
        rgb, sdr = _gainmap_jpeg(path, pixels=True)
        assert rgb is not None
    else:
        rgb, sdr = _heif_pixels(path, info)
    if not np.isfinite(rgb).all() or np.min(rgb) < -0.01:
        sdr.close()
        raise ValueError("Dekódované HDR dáta obsahujú neplatné hodnoty.")
    return HdrImage(rgb, sdr, info)


def load_hdr_sdr(path: str | Path, max_edge: int | None = None, info: HdrInfo | None = None) -> Image.Image:
    info = info or detect_hdr(path)
    if not info.supported:
        raise ValueError(info.error)
    if info.kind == "ultrahdr":
        _, result = _gainmap_jpeg(path, pixels=False)
    elif info.kind == "iso_gainmap":
        result = _iso_sdr_base(path)
        if result is None:
            with load_hdr(path, info) as loaded:
                result = loaded.sdr.copy()
    elif info.kind == "apple_gainmap":
        # Use the camera-authored SDR rendition without reconstructing HDR.
        heif = pillow_heif.open_heif(path)
        ensure_memory(heif.size[0] * heif.size[1] * 16, "Dekódovanie SDR náhľadu HDR HEIC")
        with heif.to_pillow() as base:
            result = _srgb_image(base)
        ids = heif.info.get("aux", {}).get(_APPLE_AUX, [])
        if len(ids) != 1:
            result.close()
            raise ValueError("Apple HDR vyžaduje jednu jednoznačnú gain mapu.")
        auxiliary = heif[heif.primary_index].get_aux_image(ids[0])
        _apple_parameters(heif.info.get("exif"), auxiliary._c_image.metadata)
    else:
        with load_hdr(path, info) as loaded:
            result = loaded.sdr.copy()
    native_size = result.size
    if max_edge is not None:
        if isinstance(max_edge, bool) or not isinstance(max_edge, int) or max_edge < 1:
            result.close()
            raise ValueError("Maximálna hrana náhľadu musí byť kladné celé číslo.")
        result.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    result.info["source_size"] = native_size
    result.info["hdr_info"] = info.to_dict()
    return result


def _resize_float(rgb: np.ndarray, size: tuple[int, int], *, box: tuple[float, float, float, float] | None = None) -> np.ndarray:
    result = np.empty((size[1], size[0], 3), dtype=np.float32)
    for channel in range(3):
        with Image.fromarray(rgb[..., channel]) as plane:
            with plane.resize(size, Image.Resampling.BICUBIC, box=box) as resized:
                result[..., channel] = np.asarray(resized)
    return np.maximum(result, 0)


def _box_mean_axis(rgb: np.ndarray, radius: int, axis: int) -> np.ndarray:
    """Edge-extended mean with storage independent of the kernel radius."""
    length = rgb.shape[axis]
    if length == 1:
        return rgb
    # Prefix, two gathered planes, edge-weight temporaries and float32 output.
    # The extra prefix row/column and index vectors are covered separately.
    ensure_memory(rgb.nbytes * 10 + length * 48, "Vytvorenie lineárneho HDR pozadia")
    shape = list(rgb.shape)
    shape[axis] += 1
    integral = np.empty(shape, dtype=np.float64)
    first, rest = [slice(None)] * 3, [slice(None)] * 3
    first[axis], rest[axis] = 0, slice(1, None)
    integral[tuple(first)] = 0
    np.cumsum(rgb, axis=axis, dtype=np.float64, out=integral[tuple(rest)])
    indices = np.arange(length, dtype=np.int64)
    lower = np.maximum(indices - radius, 0)
    upper = np.minimum(indices + radius + 1, length)
    means = np.take(integral, upper, axis=axis)
    means -= np.take(integral, lower, axis=axis)
    del integral
    weight_shape = [1] * 3
    weight_shape[axis] = length
    edge = [slice(None)] * 3
    edge[axis] = slice(0, 1)
    means += np.maximum(radius - indices, 0).reshape(weight_shape) * rgb[tuple(edge)]
    edge[axis] = slice(-1, None)
    means += np.maximum(indices + radius - length + 1, 0).reshape(weight_shape) * rgb[tuple(edge)]
    means /= 2 * radius + 1
    return means.astype(np.float32)


def _blur_float(rgb: np.ndarray, sigma: float) -> np.ndarray:
    if sigma <= 0:
        return rgb
    # Three separable box passes approximate a Gaussian in linear light.
    width = max(1, int(math.sqrt(4 * sigma * sigma + 1)))
    width = width if width % 2 else width - 1
    radius = width // 2
    if not radius:
        return rgb
    for _pass in range(3):
        for axis in (0, 1):
            rgb = _box_mean_axis(rgb, radius, axis)
    return rgb


def _backgrounds(
    image: HdrImage, canvas: tuple[int, int], blur: int,
    source_box: tuple[int, int, int, int] | None = None,
) -> tuple[np.ndarray, Image.Image]:
    scale = min(1.0, MAX_PREVIEW_EDGE / max(canvas))
    size = tuple(max(1, round(value * scale)) for value in canvas)
    ensure_memory(size[0] * size[1] * 128, "Vytvorenie lineárneho HDR pozadia")
    left, top, right, bottom = source_box or (0, 0, *image.size)
    width, height = right - left, bottom - top
    source_ratio, target_ratio = width / height, size[0] / size[1]
    crop_width, crop_height = (height * target_ratio, height) if source_ratio > target_ratio else (width, width / target_ratio)
    box = ((width - crop_width) / 2, (height - crop_height) / 2, (width + crop_width) / 2, (height + crop_height) / 2)
    # Slicing is a view; neither the full HDR photograph nor a full native
    # crop is copied before the bounded background is generated.
    linear = _blur_float(_resize_float(image.rgb[top:bottom, left:right], size, box=box), blur * scale)
    if (left, top, right, bottom) == (0, 0, *image.size):
        sdr = ImageOps.fit(image.sdr, size, method=Image.Resampling.LANCZOS)
    else:
        with bounded_crop(image.sdr, (left, top, right, bottom)) as cropped:
            sdr = ImageOps.fit(cropped, size, method=Image.Resampling.LANCZOS)
    if blur:
        blurred = sdr.filter(ImageFilter.GaussianBlur(blur * scale))
        sdr.close()
        sdr = blurred
    return linear, sdr


def iter_hdr_tiles(image: HdrImage, settings: Settings, cancelled: Callable[[], bool] | None = None) -> Iterator[HdrTile]:
    geometry = get_geometry(image.size, settings)
    stopped = cancelled or (lambda: False)
    if stopped():
        return
    foreground = geometry.foreground_box
    width, height = geometry.tile_width, geometry.tile_height
    background_rgb = None
    background_sdr = None
    need_background = (
        foreground[0] > 0 or foreground[1] > 0
        or foreground[2] < geometry.canvas_size[0]
        or foreground[3] < geometry.canvas_size[1]
    )
    if need_background and getattr(settings, "background_mode", "blur") == "blur":
        background_rgb, background_sdr = _backgrounds(
            image, geometry.canvas_size, settings.blur, geometry.source_box,
        )
    try:
        for index in range(geometry.count):
            if stopped():
                return
            ensure_memory(width * height * 64, "Vytvorenie HDR exportného dielu")
            left = index * width
            if background_rgb is not None and background_sdr is not None:
                box = (left * background_rgb.shape[1] / geometry.canvas_size[0], 0,
                       (left + width) * background_rgb.shape[1] / geometry.canvas_size[0], background_rgb.shape[0])
                rgb = _resize_float(background_rgb, (width, height), box=box)
                sdr = background_sdr.resize((width, height), Image.Resampling.BICUBIC, box=box)
            else:
                color = getattr(settings, "background_color", "#000000")
                sdr = Image.new("RGB", (width, height), color)
                sample = np.asarray(Image.new("RGB", (1, 1), color), dtype=np.float32) / 255
                linear = np.where(sample <= 0.04045, sample / 12.92, ((sample + 0.055) / 1.055) ** 2.4)
                rgb = np.empty((height, width, 3), dtype=np.float32)
                rgb[:] = _change_gamut(linear, 1)
            overlap = (max(left, foreground[0]), max(0, foreground[1]), min(left + width, foreground[2]), min(height, foreground[3]))
            if overlap[0] < overlap[2] and overlap[1] < overlap[3]:
                x0, y0, x1, y1 = (round(overlap[0] - foreground[0]), round(overlap[1] - foreground[1]), round(overlap[2] - foreground[0]), round(overlap[3] - foreground[1]))
                dx, dy = round(overlap[0] - left), round(overlap[1])
                source_left, source_top, _, _ = geometry.source_box
                x0, x1 = x0 + source_left, x1 + source_left
                y0, y1 = y0 + source_top, y1 + source_top
                rgb[dy:dy + y1 - y0, dx:dx + x1 - x0] = image.rgb[y0:y1, x0:x1]
                with image.sdr.crop((x0, y0, x1, y1)) as crop:
                    sdr.paste(crop, (dx, dy))
            sdr.info["icc_profile"] = _SRGB
            yield HdrTile(rgb, sdr)
    finally:
        if background_sdr is not None:
            background_sdr.close()


def hdr_extension(info: HdrInfo) -> str:
    return ".jpg" if info.kind == "ultrahdr" else ".heic"


def encode_hdr_tile(tile: HdrTile, info: HdrInfo) -> bytes:
    height, width = tile.rgb.shape[:2]
    ensure_memory(width * height * 64, "Kódovanie HDR exportu")
    if not np.isfinite(tile.rgb).all() or np.min(tile.rgb) < -0.01 or np.max(tile.rgb) > 10000 / 203 + 0.01:
        raise ValueError("HDR export obsahuje neplatné hodnoty alebo prekračuje jasový limit 10000 cd/m².")
    if hdr_extension(info) == ".jpg":
        rgba = np.ones((height, width, 4), dtype=np.float16)
        rgba[..., :3] = tile.rgb
        companion = np.asarray(tile.sdr.convert("RGBA"))
        try:
            encoded = imagecodecs.ultrahdr_encode(rgba, level=99, sdr=companion, gamut="BT_2100", transfer="LINEAR", gainmap_level=99, multichannel=True, scale=1)
        except imagecodecs.UltrahdrError as exc:
            if "8192" in str(exc):
                raise ValueError("Dostupný HDR JPEG kodek podporuje najviac 8192 pixelov na jednej hrane dielu. Zvoľte viac dielov alebo iný pomer strán.") from exc
            raise ValueError(f"HDR JPEG sa nepodarilo zakódovať: {exc}") from exc
        if not imagecodecs.ultrahdr_check(encoded):
            raise ValueError("Kodek nevytvoril platný HDR JPEG s gain mapou.")
        return encoded
    encoded_rgb = np.rint(np.clip(_linear_to_pq(tile.rgb), 0, 1) * 65535).astype("<u2")
    heif = pillow_heif.from_bytes("RGB;16", (width, height), encoded_rgb.tobytes())
    output = BytesIO()
    heif.save(output, quality=99, chroma=444, color_primaries=9, transfer_characteristics=16,
              matrix_coefficients=9, full_range_flag=1, save_nclx_profile=True, exif=None, xmp=None,
              content_light_level={"max_content_light_level": min(10000, round(float(np.max(tile.rgb)) * 203)), "max_pic_average_light_level": min(10000, round(float(np.mean(tile.rgb @ _rgb_to_xyz(9)[1])) * 203))})
    return output.getvalue()
