"""Global preferences, kept separate from the per-photo editing session."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

Theme = Literal["system", "light", "dark"]
Language = Literal["en", "sk", "cs"]
SCHEMA_VERSION = 1
MAX_PREFERENCES_BYTES = 65_536


class PreferencesError(Exception):
    """Preferences could not be read, validated, or safely saved."""


@dataclass
class AppPreferences:
    export_dir: str
    theme: Theme = "system"
    language: Language = "en"
    onboarding_completed: bool = False

    def validate(self) -> None:
        if not isinstance(self.export_dir, str) or not self.export_dir.strip():
            raise ValueError("The export folder must be a non-empty absolute path.")
        if "\x00" in self.export_dir or not Path(self.export_dir).is_absolute():
            raise ValueError("The export folder must be an absolute path.")
        if self.theme not in ("system", "light", "dark") or not isinstance(self.theme, str):
            raise ValueError("Unsupported appearance preference.")
        if self.language not in ("en", "sk", "cs") or not isinstance(self.language, str):
            raise ValueError("Unsupported interface language.")
        if type(self.onboarding_completed) is not bool:
            raise ValueError("The onboarding flag must be a boolean.")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate preferences field: {key}")
        result[key] = value
    return result


class PreferencesStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._invalid = False
        self._checked = False

    def defaults(self) -> AppPreferences:
        """Calculate defaults without creating any folder or file."""
        return AppPreferences(export_dir=str((self.path.parent / "Export").resolve()))

    def load(self) -> AppPreferences:
        self._checked = True
        if not self.path.exists():
            self._invalid = False
            return self.defaults()
        try:
            if self.path.stat().st_size > MAX_PREFERENCES_BYTES:
                raise ValueError("The preferences file exceeds 64 KiB.")
            data = json.loads(self.path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
            fields = {"schema_version", "export_dir", "theme", "language", "onboarding_completed"}
            if not isinstance(data, dict) or set(data) != fields:
                raise ValueError("The preferences fields are missing or unrecognized.")
            if type(data["schema_version"]) is not int or data["schema_version"] != SCHEMA_VERSION:
                raise ValueError("Unsupported preferences schema version.")
            preferences = AppPreferences(**{key: value for key, value in data.items() if key != "schema_version"})
            preferences.validate()
            self._invalid = False
            return preferences
        except (OSError, UnicodeError, ValueError, TypeError, RecursionError) as error:
            self._invalid = True
            raise PreferencesError(f"Cannot load preferences: {self.path}\n{error}") from error

    def save(self, preferences: AppPreferences) -> None:
        temporary: str | None = None
        try:
            if not self._checked and self.path.exists():
                self.load()
            if self._invalid:
                raise ValueError("Back up the invalid preferences before saving new settings.")
            if not isinstance(preferences, AppPreferences):
                raise TypeError("Expected AppPreferences.")
            preferences.validate()
            payload = {"schema_version": SCHEMA_VERSION, **asdict(preferences)}
            encoded = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False)
            if len(encoded.encode("utf-8")) > MAX_PREFERENCES_BYTES:
                raise ValueError("The preferences file exceeds 64 KiB.")
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent,
                prefix=f".{self.path.name}.", suffix=".tmp", delete=False,
            ) as handle:
                temporary = handle.name
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            self._checked = True
        except (OSError, ValueError, TypeError, RecursionError) as error:
            raise PreferencesError(f"Cannot save preferences: {self.path}\n{error}") from error
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)

    def preserve_invalid(self) -> Path:
        """Move the exact invalid bytes aside before explicitly starting fresh."""
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup = self.path.with_name(f"preferences.corrupt-{stamp}.json")
        try:
            self.path.rename(backup)
        except OSError as error:
            raise PreferencesError(f"Cannot back up invalid preferences: {error}") from error
        self._invalid = False
        self._checked = True
        return backup
