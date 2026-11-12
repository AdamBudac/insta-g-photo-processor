"""Product identity and non-destructive compatibility with existing app data."""

from __future__ import annotations

from pathlib import Path

PRODUCT_NAME = "Insta G Photo Processor"
APP_SLUG = "insta-g-photo-processor"
EXECUTABLE_NAME = "InstaGPhotoProcessor"
LEGACY_APP_SLUG = "insta-g-image-resizer"


def resolve_data_directory(documents: Path) -> Path:
    """Use the new name for new installs without hiding an existing session.

    A renamed installation keeps using its old state directory until the user
    explicitly moves it. No state, export, or input photograph is moved or copied.
    An empty new directory does not take precedence over existing legacy data;
    existing state under the new name always takes precedence, even if invalid,
    so its normal recovery flow can report the problem instead of hiding it.
    """
    current = Path(documents) / APP_SLUG
    legacy = Path(documents) / LEGACY_APP_SLUG
    for directory in (current, legacy):
        if any((directory / name).exists() for name in ("session.json", "preferences.json")):
            return directory
    return current
