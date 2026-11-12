"""Product rename preserves state and the user's existing export destination."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from insta_g.branding import APP_SLUG, LEGACY_APP_SLUG, resolve_data_directory
from insta_g.persistence import Session, SessionStore, StateError
from insta_g.preferences import PreferencesStore


def test_new_install_uses_new_name_without_creating_folders(tmp_path: Path) -> None:
    directory = resolve_data_directory(tmp_path)
    assert directory == tmp_path / APP_SLUG
    assert not directory.exists()
    assert list(tmp_path.iterdir()) == []


def test_rename_restores_existing_state_and_keeps_export_location(tmp_path: Path) -> None:
    legacy = tmp_path / LEGACY_APP_SLUG
    sessions = SessionStore(legacy / "session.json")
    sessions.save(Session())
    preferences = PreferencesStore(legacy / "preferences.json")
    export = tmp_path / "my-selected-export"
    original = replace(
        preferences.defaults(), export_dir=str(export), language="sk", theme="dark",
        onboarding_completed=True,
    )
    preferences.save(original)
    before = {name: (legacy / name).read_bytes() for name in ("session.json", "preferences.json")}

    directory = resolve_data_directory(tmp_path)

    assert directory == legacy
    assert SessionStore(directory / "session.json").load() == Session()
    assert PreferencesStore(directory / "preferences.json").load() == original
    assert all((legacy / name).read_bytes() == payload for name, payload in before.items())
    assert not (tmp_path / APP_SLUG).exists()
    assert not export.exists()


def test_empty_new_folder_does_not_hide_legacy_session(tmp_path: Path) -> None:
    current = tmp_path / APP_SLUG
    current.mkdir()
    legacy = tmp_path / LEGACY_APP_SLUG
    SessionStore(legacy / "session.json").save(Session())
    assert resolve_data_directory(tmp_path) == legacy


def test_new_state_takes_precedence_over_legacy_state(tmp_path: Path) -> None:
    current = tmp_path / APP_SLUG
    legacy = tmp_path / LEGACY_APP_SLUG
    for directory in (current, legacy):
        SessionStore(directory / "session.json").save(Session())
    assert resolve_data_directory(tmp_path) == current


@pytest.mark.parametrize("slug", [APP_SLUG, LEGACY_APP_SLUG])
def test_corrupt_existing_state_is_selected_for_visible_recovery(
    tmp_path: Path, slug: str,
) -> None:
    directory = tmp_path / slug
    directory.mkdir()
    path = directory / "session.json"
    path.write_bytes(b"invalid session bytes")
    assert resolve_data_directory(tmp_path) == directory
    with pytest.raises(StateError):
        SessionStore(path).load()
    assert path.read_bytes() == b"invalid session bytes"
