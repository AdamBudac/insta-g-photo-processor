"""Cancellable JPEG batch export with exclusive, complete-file publication."""

from __future__ import annotations

import os
import re
import tempfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image

from .geometry import get_geometry
from .imaging import SRGB_PROFILE, iter_tiles, load_image, source_size
from .models import ImageRecord


@dataclass
class ExportReport:
    paths: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    cancelled: bool = False
    completed: dict[str, dict[str, Any]] = field(default_factory=dict)
    failed: dict[str, str] = field(default_factory=dict)
    processed_count: int = 0


class _ExportCancelled(Exception):
    pass


MAX_JPEG_DIMENSION = 65500


def _safe_stem(path: str) -> str:
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", Path(path).stem).strip(" .")
    return (stem or "obrazok")[:160]


def _publish_exclusive(temporary: Path, directory: Path, stem: str, index: int, extension: str) -> Path:
    suffix = 1
    while True:
        collision = "" if suffix == 1 else f"_{suffix}"
        target = directory / f"{stem}_{index:02d}{collision}{extension}"
        try:
            if os.name == "nt":
                os.rename(temporary, target)
            else:
                os.link(temporary, target)
            return target
        except FileExistsError:
            suffix += 1


def _save_bytes_exclusive(
    data: bytes, directory: Path, stem: str, index: int,
    extension: str, cancelled: Callable[[], bool],
) -> Path:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".insta-g-", suffix=".tmp", dir=directory, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if cancelled():
            raise _ExportCancelled
        return _publish_exclusive(temporary, directory, stem, index, extension)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _save_jpeg_exclusive(
    image: Image.Image,
    directory: Path,
    stem: str,
    index: int,
    cancelled: Callable[[], bool],
) -> Path:
    """Publish a complete temp file; an existing target is never replaced."""
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".insta-g-", suffix=".tmp", dir=directory, delete=False) as handle:
            temporary = Path(handle.name)
            image.save(
                handle, format="JPEG", quality=99, subsampling=0,
                optimize=True, icc_profile=SRGB_PROFILE,
            )
            handle.flush()
            os.fsync(handle.fileno())
        if cancelled():
            raise _ExportCancelled
        return _publish_exclusive(temporary, directory, stem, index, ".jpg")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def export_records(
    records: Iterable[ImageRecord],
    output_dir: str | Path,
    progress: Callable[[int, int, str], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
    *,
    create_output: bool = True,
) -> ExportReport:
    """Export a settings snapshot, loading each original image independently.

    A failed input does not stop later inputs. Failure or cancellation rolls
    back only the newly created files of the current original. Completed
    originals and files that existed before this batch are never removed.
    """
    report = ExportReport()
    snapshots: list[ImageRecord] = []
    for record in records:
        try:
            snapshots.append(ImageRecord.from_dict(record.to_dict()))
        except (TypeError, ValueError, AttributeError) as exc:
            report.errors.append(f"Neplatné nastavenia obrázka: {exc}")
    total = sum(record.settings.count for record in snapshots)
    done = 0
    is_cancelled = cancelled or (lambda: False)
    directory = Path(output_dir)
    try:
        if create_output:
            directory.mkdir(parents=True, exist_ok=True)
        if not directory.is_dir():
            raise OSError("Priečinok neexistuje. V nastaveniach vyberte iný exportný priečinok.")
    except OSError as exc:
        report.errors.append(f"Výstupný priečinok „{directory}“ nie je dostupný: {exc}")
        return report
    for record in snapshots:
        if is_cancelled():
            report.cancelled = True
            break
        completed = 0
        saved: list[Path] = []
        succeeded = False
        report.processed_count += 1
        try:
            from .hdr import detect_hdr, encode_hdr_tile, hdr_extension, iter_hdr_tiles, load_hdr

            hdr = detect_hdr(record.path)
            if hdr.is_hdr and record.settings.hdr_mode == "hdr":
                with load_hdr(record.path, hdr) as image:
                    geometry = get_geometry(image.size, record.settings)
                    extension = hdr_extension(hdr)
                    if extension == ".jpg" and max(geometry.tile_width, geometry.tile_height) > MAX_JPEG_DIMENSION:
                        raise ValueError(f"JPEG podporuje najviac {MAX_JPEG_DIMENSION} pixelov na jednej hrane dielu.")
                    tiles = iter_hdr_tiles(image, record.settings, cancelled=is_cancelled)
                    try:
                        for index, tile in enumerate(tiles, 1):
                            try:
                                if is_cancelled():
                                    raise _ExportCancelled
                                data = encode_hdr_tile(tile, hdr)
                                target = _save_bytes_exclusive(data, directory, _safe_stem(record.path) + "_HDR", index, extension, is_cancelled)
                            finally:
                                tile.close()
                            saved.append(target)
                            done += 1
                            completed += 1
                            if progress is not None:
                                progress(done, total, target.name)
                    finally:
                        tiles.close()
                if completed < geometry.count:
                    if is_cancelled():
                        raise _ExportCancelled
                    raise ValueError("HDR export nevytvoril úplnú sériu dielov.")
                report.completed[record.path] = record.settings.to_dict()
                report.paths.extend(saved)
                succeeded = True
                continue
            with load_image(record.path) as image:
                geometry = get_geometry(source_size(image), record.settings)
                if max(geometry.tile_width, geometry.tile_height) > MAX_JPEG_DIMENSION:
                    raise ValueError(
                        f"JPEG podporuje najviac {MAX_JPEG_DIMENSION} pixelov na jednej hrane dielu. "
                        "Zvoľte viac dielov alebo iný pomer strán."
                    )
                tiles = iter_tiles(image, record.settings, cancelled=is_cancelled)
                try:
                    for index, tile in enumerate(tiles):
                        with tile:
                            if is_cancelled():
                                raise _ExportCancelled
                            stem = _safe_stem(record.path) + ("_SDR" if hdr.is_hdr else "")
                            target = _save_jpeg_exclusive(tile, directory, stem, index + 1, is_cancelled)
                        saved.append(target)
                        done += 1
                        completed += 1
                        if progress is not None:
                            progress(done, total, target.name)
                finally:
                    tiles.close()
                if is_cancelled() and completed < geometry.count:
                    raise _ExportCancelled
                if completed == geometry.count:
                    report.completed[record.path] = record.settings.to_dict()
                    report.paths.extend(saved)
                    succeeded = True
                elif not is_cancelled():
                    raise ValueError("Export nevytvoril úplnú sériu dielov.")
        except _ExportCancelled:
            report.cancelled = True
            break
        except Exception as exc:
            message = f"Export „{Path(record.path).name}“ zlyhal: {exc}"
            report.errors.append(message)
            report.failed[record.path] = message
            done += record.settings.count - completed
            if progress is not None:
                progress(done, total, f"Chyba: {Path(record.path).name}")
        finally:
            if not succeeded:
                for target in saved:
                    try:
                        target.unlink(missing_ok=True)
                    except OSError as exc:
                        message = f"Neúplný export „{target.name}“ sa nepodarilo odstrániť: {exc}"
                        report.errors.append(message)
                        report.failed[record.path] = message
    return report
