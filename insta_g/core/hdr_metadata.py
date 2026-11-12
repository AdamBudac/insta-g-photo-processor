"""Bounded ISO BMFF and ISO 21496-1 gain-map metadata readers.

Only container bytes are changed in memory when selecting a hidden gain image;
the source file is never written. Numeric layout follows libultrahdr's
gainmapmetadata.cpp and libheif's ISO tmap implementation.
"""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from typing import Iterator


def boxes(data: bytes, start: int, end: int) -> Iterator[tuple[bytes, int, int]]:
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


class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.position = 0

    def number(self, size: int, signed: bool = False) -> int:
        if size < 0 or size > 8 or self.position + size > len(self.data):
            raise ValueError("Neúplné metadáta HDR HEIC.")
        result = int.from_bytes(self.data[self.position:self.position + size], "big", signed=signed)
        self.position += size
        return result


@dataclass(frozen=True)
class IsoGainmap:
    base_id: int
    gainmap_id: int
    primary_position: int
    primary_size: int
    gainmap_flags_position: int
    metadata: bytes
    alternate_icc: bytes | None
    alternate_primaries: int | None

    def select_gainmap(self, data: bytes) -> bytes:
        promoted = bytearray(data)
        promoted[self.primary_position:self.primary_position + self.primary_size] = self.gainmap_id.to_bytes(self.primary_size, "big")
        promoted[self.gainmap_flags_position] &= 0xfe
        return bytes(promoted)


def read_iso_structure(data: bytes) -> IsoGainmap:
    metadata_boxes = [(start, end) for kind, start, end in boxes(data, 0, len(data)) if kind == b"meta"]
    if len(metadata_boxes) != 1:
        raise ValueError("HEIC musí mať práve jednu tabuľku metadát.")
    meta_start, meta_end = metadata_boxes[0]
    children = list(boxes(data, meta_start + 4, meta_end))
    items: dict[int, bytes] = {}
    item_flags: dict[int, int] = {}
    references: dict[int, list[int]] = {}
    locations: dict[int, tuple[int, list[tuple[int, int]]]] = {}
    properties: list[tuple[bytes, bytes]] = [(b"", b"")]
    associations: dict[int, list[int]] = {}
    primary = None
    idat_start = None
    for kind, start, end in children:
        if kind == b"pitm":
            primary_size = 2 if data[start] == 0 else 4
            primary_position = start + 4
            primary = int.from_bytes(data[primary_position:primary_position + primary_size], "big")
        elif kind == b"idat":
            idat_start = start
        elif kind == b"iinf":
            for item_kind, item_start, item_end in boxes(data, start + (6 if data[start] == 0 else 8), end):
                if item_kind != b"infe" or data[item_start] not in (2, 3):
                    continue
                size = 2 if data[item_start] == 2 else 4
                item_id = int.from_bytes(data[item_start + 4:item_start + 4 + size], "big")
                items[item_id] = data[item_start + 6 + size:item_start + 10 + size]
                item_flags[item_id] = item_start + 3
        elif kind == b"iref":
            id_size = 2 if data[start] == 0 else 4
            for ref_kind, ref_start, ref_end in boxes(data, start + 4, end):
                if ref_kind != b"dimg":
                    continue
                reader = Reader(data[ref_start:ref_end])
                source, count = reader.number(id_size), reader.number(2)
                references[source] = [reader.number(id_size) for _ in range(count)]
        elif kind == b"iloc":
            reader = Reader(data[start:end])
            version = reader.number(1)
            reader.number(3)
            first, second = reader.number(1), reader.number(1)
            offset_size, length_size = first >> 4, first & 15
            base_size, index_size = second >> 4, second & 15 if version in (1, 2) else 0
            count = reader.number(4 if version == 2 else 2)
            for _ in range(count):
                item_id = reader.number(4 if version == 2 else 2)
                method = reader.number(2) & 15 if version in (1, 2) else 0
                if reader.number(2) != 0:
                    raise ValueError("HDR HEIC nesmie používať externé obrazové dáta.")
                base = reader.number(base_size)
                extents = []
                for _ in range(reader.number(2)):
                    if index_size:
                        reader.number(index_size)
                    offset, length = reader.number(offset_size), reader.number(length_size)
                    extents.append((base + offset, length))
                locations[item_id] = method, extents
        elif kind == b"iprp":
            for prop_kind, prop_start, prop_end in boxes(data, start, end):
                if prop_kind == b"ipco":
                    properties.extend((tag, data[a:b]) for tag, a, b in boxes(data, prop_start, prop_end))
                elif prop_kind == b"ipma":
                    reader = Reader(data[prop_start:prop_end])
                    version, flags = reader.number(1), reader.number(3)
                    for _ in range(reader.number(4)):
                        item_id = reader.number(2 if version < 1 else 4)
                        size, mask = (2, 0x7fff) if flags & 1 else (1, 0x7f)
                        associations[item_id] = [reader.number(size) & mask for _ in range(reader.number(1))]
    tmap_ids = [item_id for item_id, kind in items.items() if kind == b"tmap" and references.get(item_id, [None])[0] == primary]
    if len(tmap_ids) != 1 or primary is None:
        raise ValueError("HDR HEIC nemá jednoznačnú ISO gain mapu priradenú k fotografii.")
    tmap = tmap_ids[0]
    refs = references[tmap]
    if len(refs) != 2 or refs[0] == refs[1] or refs[1] not in items:
        raise ValueError("Neplatné referencie ISO HDR gain mapy.")
    if tmap not in locations:
        raise ValueError("ISO HDR gain mape chýbajú metadáta.")
    method, extents = locations[tmap]
    payload = bytearray()
    for offset, length in extents:
        if method == 1 and idat_start is not None:
            offset += idat_start
        elif method != 0:
            raise ValueError("Nepodporované uloženie ISO HDR metadát.")
        if not length or offset + length > len(data):
            raise ValueError("Poškodené ISO HDR metadáta.")
        payload.extend(data[offset:offset + length])
    if not payload or payload[0] != 0:
        raise ValueError("Nepodporovaná verzia tmap HDR metadát.")
    icc, primaries = None, None
    for index in associations.get(tmap, []):
        if not 0 < index < len(properties):
            raise ValueError("Neplatný farebný profil ISO HDR.")
        kind, value = properties[index]
        if kind == b"colr" and value[:4] in (b"prof", b"rICC"):
            icc = value[4:]
        elif kind == b"colr" and value[:4] == b"nclx" and len(value) >= 11:
            primaries = int.from_bytes(value[4:6], "big")
    return IsoGainmap(primary, refs[1], primary_position, primary_size, item_flags[refs[1]], bytes(payload[1:]), icc, primaries)


def read_iso_gainmap_metadata(data: bytes) -> dict:
    reader = Reader(data)
    if reader.number(2) != 0:
        raise ValueError("Nepodporovaná verzia ISO 21496 HDR metadát.")
    reader.number(2)  # Writer version is intentionally forward compatible.
    flags = reader.number(1)
    channels = 3 if flags & 0x80 else 1
    common = reader.number(4) if flags & 8 else None

    def fraction(signed: bool = False) -> float:
        numerator = reader.number(4, signed)
        denominator = common if common is not None else reader.number(4)
        if not denominator:
            raise ValueError("ISO HDR metadáta obsahujú nulový menovateľ.")
        return numerator / denominator

    base_headroom, alternate_headroom = fraction(), fraction()
    values = []
    for _ in range(channels):
        low, high, gamma, base_offset, alternate_offset = fraction(True), fraction(True), fraction(), fraction(True), fraction(True)
        if high < low or gamma <= 0 or max(abs(low), abs(high)) > 32:
            raise ValueError("Neplatný rozsah alebo gamma ISO HDR gain mapy.")
        values.append((low, high, gamma, base_offset, alternate_offset))
    if channels == 1:
        values *= 3
    if max(base_headroom, alternate_headroom) > math.log2(10000 / 203) + 0.01:
        raise ValueError("ISO HDR jasový rozsah prekračuje 10000 cd/m².")
    return {"channels": values, "use_base_cg": bool(flags & 0x40), "backward": bool(flags & 4),
            "base_headroom": base_headroom, "alternate_headroom": alternate_headroom}
