"""First-run setup and later launches touch only explicitly isolated paths."""

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QDialog

import insta_g.app as application
import insta_g.diagnostics as diagnostics
import insta_g.gui.window as window_module
from insta_g.gui.preferences_dialog import PreferencesDialog
from insta_g.i18n import get_language, set_language
from insta_g.preferences import PreferencesError, PreferencesStore


class ThemeRecorder:
    def __init__(self, app=None):
        self.themes = ["system"]
        self.is_dark = False

    def set_theme(self, theme):
        self.themes.append(theme)
        self.is_dark = theme == "dark"


@pytest.fixture(autouse=True)
def restore_language():
    previous = get_language()
    yield
    set_language(previous)


def choose_defaults(monkeypatch, qtbot, observed):
    def execute(dialog):
        qtbot.addWidget(dialog)
        observed.append(dialog._first_run)
        # Skip discards unfinished edits rather than persisting them.
        dialog.export_folder.setText("ignored relative path")
        dialog.theme_combo.setCurrentIndex(dialog.theme_combo.findData("dark"))
        dialog.language_combo.setCurrentIndex(dialog.language_combo.findData("cs"))
        dialog._skip()
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(PreferencesDialog, "exec", execute)


def test_first_run_skip_saves_defaults_and_initializes_export_once(tmp_path, monkeypatch, qtbot):
    store = PreferencesStore(tmp_path / "app" / "preferences.json")
    observed = []
    choose_defaults(monkeypatch, qtbot, observed)
    manager = ThemeRecorder()
    preferences = application.prepare_preferences(store, manager)
    assert observed == [True]
    assert preferences == replace(store.defaults(), onboarding_completed=True)
    assert preferences.language == "en" and preferences.theme == "system"
    assert Path(preferences.export_dir).is_dir()
    assert store.load() == preferences
    Path(preferences.export_dir).rmdir()
    reopened = application.prepare_preferences(store, manager)
    assert reopened == preferences
    assert observed == [True]
    assert not Path(preferences.export_dir).exists()


def test_first_run_applies_chosen_language_theme_and_does_not_create_custom_output(
    tmp_path, monkeypatch, qtbot,
):
    store = PreferencesStore(tmp_path / "state" / "preferences.json")
    custom = tmp_path / "custom-output"
    manager = ThemeRecorder()

    def execute(dialog):
        qtbot.addWidget(dialog)
        assert manager.themes[-1] == "system"
        dialog.export_folder.setText(str(custom))
        dialog.theme_combo.setCurrentIndex(dialog.theme_combo.findData("light"))
        dialog.language_combo.setCurrentIndex(dialog.language_combo.findData("sk"))
        dialog.accept()
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(PreferencesDialog, "exec", execute)
    preferences = application.prepare_preferences(store, manager)
    assert preferences.onboarding_completed
    assert preferences.export_dir == str(custom)
    assert preferences.language == get_language() == "sk"
    assert manager.themes[-1] == "light"
    assert not custom.exists()
    assert not Path(store.defaults().export_dir).exists()


def test_skip_resets_saved_unfinished_choices_without_recreating_deleted_folders(
    tmp_path, monkeypatch, qtbot,
):
    store = PreferencesStore(tmp_path / "app" / "preferences.json")
    custom = tmp_path / "deleted-custom-output"
    custom.mkdir()
    defaults = store.defaults()
    Path(defaults.export_dir).mkdir(parents=True)
    saved = replace(defaults, export_dir=str(custom), language="sk", theme="dark")
    store.save(saved)
    custom.rmdir()
    Path(defaults.export_dir).rmdir()
    observed = []
    choose_defaults(monkeypatch, qtbot, observed)
    manager = ThemeRecorder()

    selected = application.prepare_preferences(store, manager)

    assert observed == [True]
    assert selected == replace(defaults, onboarding_completed=True)
    assert store.load() == selected
    assert get_language() == "en" and manager.themes[-1] == "system"
    assert not custom.exists()
    assert not Path(defaults.export_dir).exists()


def test_cancel_first_run_creates_neither_preferences_nor_default_output(
    tmp_path, monkeypatch, qtbot,
):
    store = PreferencesStore(tmp_path / "state" / "preferences.json")

    def reject(dialog):
        qtbot.addWidget(dialog)
        dialog.reject()
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(PreferencesDialog, "exec", reject)
    assert application.prepare_preferences(store, ThemeRecorder()) is None
    assert not store.path.parent.exists()


def test_corrupt_preferences_are_backed_up_and_warning_names_backup(
    tmp_path, monkeypatch, qtbot,
):
    store = PreferencesStore(tmp_path / "preferences.json")
    original = b"{invalid-preferences-that-must-survive"
    store.path.write_bytes(original)
    warnings = []
    monkeypatch.setattr(application.QMessageBox, "warning", lambda *args: warnings.append(args))
    choose_defaults(monkeypatch, qtbot, [])
    preferences = application.prepare_preferences(store, ThemeRecorder())
    backups = list(tmp_path.glob("preferences.corrupt-*.json"))
    assert len(backups) == 1 and backups[0].read_bytes() == original
    assert len(warnings) == 1 and str(backups[0]) in warnings[0][2]
    assert store.load() == preferences
    # Recovery is a later initialization, so it must not recreate missing output.
    assert not Path(preferences.export_dir).exists()


def test_backup_failure_preserves_invalid_bytes_and_stops_before_setup(tmp_path, monkeypatch):
    store = PreferencesStore(tmp_path / "preferences.json")
    store.path.write_bytes(b"corrupt")

    def cannot_preserve():
        raise PreferencesError("backup denied")

    def unexpected_dialog(*args, **kwargs):
        raise AssertionError("setup must not start before backup")

    monkeypatch.setattr(store, "preserve_invalid", cannot_preserve)
    monkeypatch.setattr(application, "PreferencesDialog", unexpected_dialog)
    with pytest.raises(PreferencesError, match="backup denied"):
        application.prepare_preferences(store, ThemeRecorder())
    assert store.path.read_bytes() == b"corrupt"


@pytest.fixture
def fake_runtime(monkeypatch):
    calls = []
    fake_app = SimpleNamespace(
        setApplicationName=lambda value: None,
        setOrganizationName=lambda value: None,
        setApplicationVersion=lambda value: None,
        setStyle=lambda value: None,
        setFont=lambda value: None,
        exec=lambda: 17,
    )
    monkeypatch.setattr(application, "QApplication", SimpleNamespace(instance=lambda: fake_app))
    monkeypatch.setattr(application, "ThemeManager", ThemeRecorder)
    monkeypatch.setattr(application.QMessageBox, "critical", lambda *args: calls.append(("critical", args)))

    class Window:
        def __init__(self, store, session, **kwargs):
            calls.append(("window", store, session, kwargs))

        def showMaximized(self):
            calls.append(("maximized",))

        def import_paths(self, paths):
            calls.append(("import", paths))

    monkeypatch.setattr(window_module, "MainWindow", Window)
    return calls, fake_app


def test_main_passes_global_preferences_to_window_without_recreating_missing_output(
    tmp_path, monkeypatch, fake_runtime,
):
    store = PreferencesStore(tmp_path / "preferences.json")
    saved = replace(store.defaults(), language="cs", theme="dark", onboarding_completed=True)
    store.save(saved)
    monkeypatch.setattr(application.QStandardPaths, "writableLocation", lambda _: "")
    calls, _ = fake_runtime
    assert application.main(["--data-dir", str(tmp_path), "generated.jpg"]) == 17
    invocation = next(call for call in calls if call[0] == "window")
    assert invocation[1].path == tmp_path / "session.json"
    assert invocation[3]["preferences"] == saved
    assert invocation[3]["preferences_store"].path == store.path
    assert invocation[3]["theme_manager"].themes[-1] == "dark"
    assert get_language() == "cs"
    assert ("import", ["generated.jpg"]) in calls
    assert ("maximized",) in calls
    assert not Path(saved.export_dir).exists()


def test_main_reports_save_failure_and_keeps_previous_preferences(
    tmp_path, monkeypatch, qtbot, fake_runtime,
):
    store = PreferencesStore(tmp_path / "preferences.json")
    store.save(store.defaults())
    original = store.path.read_bytes()
    choose_defaults(monkeypatch, qtbot, [])

    def denied(self, candidate):
        raise PreferencesError("injected preferences save failure")

    monkeypatch.setattr(PreferencesStore, "save", denied)
    calls, _ = fake_runtime
    assert application.main(["--data-dir", str(tmp_path)]) == 1
    assert store.path.read_bytes() == original
    assert not any(call[0] == "window" for call in calls)
    assert "injected preferences save failure" in calls[-1][1][2]
    assert not Path(store.defaults().export_dir).exists()


def test_smoke_bypasses_documents_preferences_and_onboarding(tmp_path, monkeypatch, fake_runtime):
    def forbidden(*args, **kwargs):
        raise AssertionError("smoke must not discover personal state or onboarding")

    monkeypatch.setattr(application.QStandardPaths, "writableLocation", forbidden)
    monkeypatch.setattr(application, "prepare_preferences", forbidden)
    monkeypatch.setattr(application, "SessionStore", forbidden)
    reports = []
    monkeypatch.setattr(diagnostics, "run_smoke", lambda path, app: reports.append((path, app)) or 23)
    calls, fake_app = fake_runtime
    report = tmp_path / "smoke.json"
    assert application.main(["--smoke-test", str(report)]) == 23
    assert reports == [(report, fake_app)]
    assert not calls
