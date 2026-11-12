"""Global defaults, transactional settings and safe recovery use temporary data."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from PySide6.QtCore import Qt

import insta_g.preferences as persistence
from insta_g.gui.preferences_dialog import HelpDialog, PreferencesDialog, user_guide_path
from insta_g.gui.themes import ThemeManager
from insta_g.i18n import tr
from insta_g.preferences import PreferencesError, PreferencesStore


def test_defaults_are_english_system_and_create_nothing(tmp_path: Path) -> None:
    store = PreferencesStore(tmp_path / "not-created" / "preferences.json")
    defaults = store.load()
    assert defaults.export_dir == str((store.path.parent / "Export").resolve())
    assert defaults.theme == "system" and defaults.language == "en"
    assert not defaults.onboarding_completed
    assert not store.path.parent.exists()


def test_round_trip_is_separate_from_session_and_does_not_create_export(tmp_path: Path) -> None:
    store = PreferencesStore(tmp_path / "data" / "preferences.json")
    export = tmp_path / "never-create-this"
    preferences = replace(store.defaults(), export_dir=str(export), theme="dark", language="cs", onboarding_completed=True)
    store.save(preferences)
    assert store.load() == preferences
    assert not export.exists()
    assert not (store.path.parent / "session.json").exists()
    assert json.loads(store.path.read_text(encoding="utf-8"))["schema_version"] == 1


def test_deleted_export_folder_stays_deleted(tmp_path: Path) -> None:
    store = PreferencesStore(tmp_path / "preferences.json")
    export = tmp_path / "export"
    export.mkdir()
    store.save(replace(store.defaults(), export_dir=str(export), onboarding_completed=True))
    export.rmdir()
    loaded = store.load()
    store.save(loaded)
    assert loaded.export_dir == str(export)
    assert not export.exists()


@pytest.mark.parametrize("field,value", [
    ("schema_version", True), ("schema_version", 2),
    ("export_dir", "relative"), ("export_dir", ""), ("export_dir", None),
    ("export_dir", "C:\\bad\x00path"),
    ("theme", "auto"), ("theme", 2), ("theme", []),
    ("language", "de"), ("language", None),
    ("onboarding_completed", 1), ("onboarding_completed", "true"),
])
def test_invalid_preferences_are_reported_and_never_overwritten(
    tmp_path: Path, field: str, value: object,
) -> None:
    store = PreferencesStore(tmp_path / "preferences.json")
    store.save(store.defaults())
    payload = json.loads(store.path.read_text(encoding="utf-8"))
    payload[field] = value
    original = json.dumps(payload).encode("utf-8")
    store.path.write_bytes(original)
    with pytest.raises(PreferencesError):
        store.load()
    assert store.path.read_bytes() == original
    with pytest.raises(PreferencesError, match="Back up"):
        store.save(store.defaults())
    assert store.path.read_bytes() == original
    backup = store.preserve_invalid()
    assert backup.read_bytes() == original
    assert not store.path.exists()
    store.save(store.defaults())
    assert store.load() == store.defaults()


@pytest.mark.parametrize("contents", ["{invalid", "[]", '{"schema_version":1,"theme":"light","theme":"dark"}', "[" * 1500 + "0" + "]" * 1500])
def test_corrupt_or_duplicate_json_is_preserved(tmp_path: Path, contents: str) -> None:
    store = PreferencesStore(tmp_path / "preferences.json")
    store.path.write_text(contents, encoding="utf-8")
    with pytest.raises(PreferencesError):
        store.save(store.defaults())
    assert store.path.read_text(encoding="utf-8") == contents


def test_missing_or_unknown_fields_are_rejected(tmp_path: Path) -> None:
    store = PreferencesStore(tmp_path / "preferences.json")
    store.save(store.defaults())
    valid = json.loads(store.path.read_text(encoding="utf-8"))
    for payload in ({**valid, "unknown": 1}, {key: value for key, value in valid.items() if key != "language"}):
        store.path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(PreferencesError):
            store.load()


def test_atomic_save_failure_keeps_previous_bytes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = PreferencesStore(tmp_path / "preferences.json")
    store.save(store.defaults())
    before = store.path.read_bytes()

    def denied(*args: object) -> None:
        raise PermissionError("locked preferences")

    monkeypatch.setattr(persistence.os, "replace", denied)
    with pytest.raises(PreferencesError, match="locked preferences"):
        store.save(replace(store.defaults(), language="sk"))
    assert store.path.read_bytes() == before
    assert not list(tmp_path.glob("*.tmp"))


def test_preferences_dialog_cancel_is_reversible(qtbot, tmp_path: Path) -> None:
    original = PreferencesStore(tmp_path / "preferences.json").defaults()
    dialog = PreferencesDialog(original)
    qtbot.addWidget(dialog)
    assert dialog.save_button.text() == tr("OK")
    assert dialog.cancel_button.text() == tr("Cancel")
    dialog.export_folder.setText(str(tmp_path / "changed"))
    dialog.theme_combo.setCurrentIndex(dialog.theme_combo.findData("dark"))
    dialog.language_combo.setCurrentIndex(dialog.language_combo.findData("cs"))
    dialog.reject()
    assert dialog.result_preferences is None
    assert dialog.preferences() == original
    assert original.theme == "system" and original.language == "en"
    assert not list(tmp_path.iterdir())


def test_preferences_dialog_save_and_skip_return_copies(qtbot, tmp_path: Path) -> None:
    original = PreferencesStore(tmp_path / "preferences.json").defaults()
    dialog = PreferencesDialog(original, first_run=True)
    qtbot.addWidget(dialog)
    dialog.theme_combo.setCurrentIndex(dialog.theme_combo.findData("dark"))
    dialog.language_combo.setCurrentIndex(dialog.language_combo.findData("sk"))
    dialog.accept()
    assert dialog.result_preferences == replace(original, theme="dark", language="sk", onboarding_completed=True)
    assert dialog.preferences() is not dialog.result_preferences
    assert not original.onboarding_completed
    skipped = PreferencesDialog(original, first_run=True)
    qtbot.addWidget(skipped)
    skipped.export_folder.setText(str(tmp_path / "ignored"))
    skipped.theme_combo.setCurrentIndex(skipped.theme_combo.findData("light"))
    qtbot.mouseClick(skipped.skip_button, Qt.MouseButton.LeftButton)
    assert skipped.result_preferences == replace(original, onboarding_completed=True)
    assert not list(tmp_path.iterdir())


def test_invalid_dialog_path_stays_open(qtbot, tmp_path: Path) -> None:
    dialog = PreferencesDialog(PreferencesStore(tmp_path / "preferences.json").defaults())
    qtbot.addWidget(dialog)
    dialog.export_folder.setText("relative/path")
    dialog.accept()
    assert dialog.result_preferences is None
    assert not dialog.error.isHidden()


def test_skip_uses_explicit_defaults_instead_of_original_unfinished_choices(qtbot, tmp_path):
    defaults = PreferencesStore(tmp_path / "preferences.json").defaults()
    original = replace(defaults, export_dir=str(tmp_path / "custom"), language="cs", theme="dark")
    dialog = PreferencesDialog(original, first_run=True, defaults=defaults)
    qtbot.addWidget(dialog)
    dialog._skip()
    assert dialog.result_preferences == replace(defaults, onboarding_completed=True)
    assert original.language == "cs" and original.theme == "dark"
    assert not original.onboarding_completed and not defaults.onboarding_completed
    assert not list(tmp_path.iterdir())


def test_all_help_languages_are_bundled_and_scrollable(qtbot) -> None:
    for language, title, filename in (
        ("en", "User guide", "README-user.md"),
        ("sk", "Návod na použitie", "README-user-sk.md"),
        ("cs", "Návod k použití", "README-user-cz.md"),
    ):
        path = user_guide_path(language)
        assert path.is_file()
        assert path.name == filename
        dialog = HelpDialog(language)
        qtbot.addWidget(dialog)
        assert title in dialog.browser.toPlainText()
        assert len(dialog.browser.toPlainText()) > 3000


def test_theme_switches_and_system_changes_are_live(qapp, monkeypatch: pytest.MonkeyPatch) -> None:
    previous_sheet = qapp.styleSheet()
    previous_dark = qapp.property("theme_dark")
    manager = ThemeManager(qapp)
    try:
        manager.set_theme("dark")
        assert manager.is_dark and qapp.property("theme_dark")
        dark = qapp.styleSheet()
        manager.set_theme("light")
        assert not manager.is_dark and qapp.styleSheet() != dark
        monkeypatch.setattr(manager, "_system_dark", lambda: True)
        manager.set_theme("system")
        assert manager.is_dark
        monkeypatch.setattr(manager, "_system_dark", lambda: False)
        manager._system_changed()
        assert not manager.is_dark
        with pytest.raises(ValueError):
            manager.set_theme("unknown")
    finally:
        qapp.styleHints().colorSchemeChanged.disconnect(manager._system_changed)
        qapp.setStyleSheet(previous_sheet)
        qapp.setProperty("theme_dark", previous_dark)
        manager.deleteLater()
