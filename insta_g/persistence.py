"""Versioned, atomic session storage independent of the graphical interface."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from insta_g.core.models import ImageRecord

SCHEMA_VERSION = 6
MAX_RECORDS = 10000
MAX_STATE_BYTES = 5_000_000


class StateError(Exception):
    """A session could not be read or safely persisted."""


@dataclass
class Session:
    records: list[ImageRecord] = field(default_factory=list)
    selected_path: str | None = None
    export_dir: str = ""


class SessionStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._legacy_bytes: bytes | None = None
        self._legacy_version: int | None = None
        self._legacy_backup: Path | None = None

    def load(self) -> Session:
        self._legacy_bytes = None
        self._legacy_version = None
        self._legacy_backup = None
        if not self.path.exists():
            return Session()
        try:
            if self.path.stat().st_size > MAX_STATE_BYTES:
                raise ValueError("Súbor relácie presahuje 5 MB.")
            raw = self.path.read_bytes()
            data = json.loads(raw.decode("utf-8"))
            if not isinstance(data, dict) or type(data.get("schema_version")) is not int:
                raise ValueError("Chýba verzia schémy relácie.")
            if data["schema_version"] not in (1, 2, 3, 4, 5, SCHEMA_VERSION):
                raise ValueError("Nepodporovaná verzia schémy relácie.")
            raw_records = data.get("records")
            if not isinstance(raw_records, list) or len(raw_records) > MAX_RECORDS:
                raise ValueError("Neplatný zoznam fotografií.")
            records = [ImageRecord.from_dict(item) for item in raw_records]
            keys = [os.path.normcase(os.path.abspath(record.path)) for record in records]
            if len(keys) != len(set(keys)):
                raise ValueError("Relácia obsahuje duplicitné fotografie.")
            selected = data.get("selected_path")
            export_dir = data.get("export_dir", "")
            if selected is not None and not isinstance(selected, str):
                raise ValueError("Neplatný výber fotografie.")
            if not isinstance(export_dir, str):
                raise ValueError("Neplatný exportný priečinok.")
            if selected is not None and selected not in [record.path for record in records]:
                selected = records[0].path if records else None
            if data["schema_version"] < SCHEMA_VERSION:
                self._legacy_bytes = raw
                self._legacy_version = data["schema_version"]
            return Session(records, selected, export_dir)
        except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
            raise StateError(f"Reláciu nemožno načítať: {self.path}\n{exc}") from exc

    def save(self, session: Session) -> None:
        temporary: str | None = None
        try:
            if len(session.records) > MAX_RECORDS:
                raise ValueError("Relácia môže obsahovať najviac 10 000 fotografií.")
            payload = {
                "schema_version": SCHEMA_VERSION,
                "records": [record.to_dict() for record in session.records],
                "selected_path": session.selected_path,
                "export_dir": session.export_dir,
            }
            encoded = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False)
            if len(encoded.encode("utf-8")) > MAX_STATE_BYTES:
                raise ValueError("Súbor relácie presahuje 5 MB.")
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if self._legacy_bytes is not None and self._legacy_backup is None:
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
                backup = self.path.with_name(f"session.v{self._legacy_version}-backup-{stamp}.json")
                with backup.open("xb") as handle:
                    handle.write(self._legacy_bytes)
                    handle.flush()
                    os.fsync(handle.fileno())
                self._legacy_backup = backup
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent,
                prefix=f".{self.path.name}.", suffix=".tmp", delete=False,
            ) as handle:
                temporary = handle.name
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            self._legacy_bytes = None
            self._legacy_version = None
        except (OSError, ValueError, TypeError, RecursionError) as exc:
            raise StateError(f"Reláciu nemožno uložiť: {self.path}\n{exc}") from exc
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)

    def preserve_invalid(self) -> Path:
        """Keep the exact invalid file before a fresh session can be saved."""
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup = self.path.with_name(f"session.corrupt-{stamp}.json")
        try:
            self.path.rename(backup)
        except OSError as exc:
            raise StateError(f"Poškodenú reláciu nemožno bezpečne zálohovať: {exc}") from exc
        return backup
