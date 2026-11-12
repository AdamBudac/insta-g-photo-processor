"""Windows desktop application entry point."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QStandardPaths
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox

from insta_g import __version__
from insta_g.branding import PRODUCT_NAME, resolve_data_directory
from insta_g.gui.preferences_dialog import PreferencesDialog
from insta_g.gui.themes import ThemeManager
from insta_g.i18n import set_language, tr
from insta_g.persistence import Session, SessionStore, StateError
from insta_g.preferences import AppPreferences, PreferencesError, PreferencesStore


def prepare_preferences(
    store: PreferencesStore, theme_manager: ThemeManager,
) -> AppPreferences | None:
    """Load global settings and complete setup before opening the main window.

    The default Export directory is created only for a genuinely new preferences
    file. Recovering an older file or reopening a deleted output directory never
    silently recreates a user's previous export location.
    """
    first_initialization = not store.path.exists()
    try:
        preferences = store.load()
    except PreferencesError as error:
        backup = store.preserve_invalid()
        QMessageBox.warning(
            None, tr("Preferences recovery"),
            tr("{error}\n\nThe original preferences were preserved in:\n{backup}\n"
               "The application will open first-run setup.", error=str(error), backup=backup),
        )
        preferences = store.defaults()
    set_language(preferences.language)
    theme_manager.set_theme(preferences.theme)
    if not preferences.onboarding_completed:
        dialog = PreferencesDialog(preferences, first_run=True, defaults=store.defaults())
        if dialog.exec() != dialog.DialogCode.Accepted or dialog.result_preferences is None:
            return None
        candidate = replace(dialog.result_preferences, onboarding_completed=True)
        default = store.defaults()
        if first_initialization and Path(candidate.export_dir) == Path(default.export_dir):
            try:
                Path(default.export_dir).mkdir(parents=True, exist_ok=True)
            except OSError as error:
                raise PreferencesError(tr("Cannot create the default export folder:\n{error}",
                                          error=str(error))) from error
        store.save(candidate)
        preferences = candidate
        set_language(preferences.language)
        theme_manager.set_theme(preferences.theme)
    return preferences


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=PRODUCT_NAME)
    parser.add_argument("images", nargs="*", help="Fotografie na import")
    parser.add_argument("--data-dir", type=Path, help="Alternatívny priečinok relácie")
    parser.add_argument("--smoke-test", type=Path, metavar="REPORT", help="Izolovaná diagnostika; výsledok do JSON")
    parser.add_argument("--smoke-hdr-dir", type=Path, help="Voliteľný priečinok HDR vzoriek iba na čítanie pre diagnostiku")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)
    app = QApplication.instance() or QApplication([sys.argv[0]])
    app.setApplicationName(PRODUCT_NAME)
    app.setOrganizationName("Insta G")
    app.setApplicationVersion(__version__)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    set_language("en")
    theme_manager = ThemeManager(app)
    if args.smoke_test is not None:
        from insta_g.diagnostics import run_smoke

        if args.smoke_hdr_dir is not None:
            return run_smoke(args.smoke_test, app, hdr_directory=args.smoke_hdr_dir)
        return run_smoke(args.smoke_test, app)
    documents = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
    if args.data_dir is None and not documents:
        QMessageBox.critical(None, tr("Session folder"),
                             tr("Windows did not provide a Documents folder path."))
        return 1
    directory = args.data_dir or resolve_data_directory(Path(documents))
    preferences_store = PreferencesStore(directory / "preferences.json")
    try:
        preferences = prepare_preferences(preferences_store, theme_manager)
    except PreferencesError as error:
        QMessageBox.critical(None, tr("Preferences"), tr(str(error)))
        return 1
    if preferences is None:
        return 0
    store = SessionStore(directory / "session.json")
    try:
        session = store.load()
    except StateError as exc:
        try:
            backup = store.preserve_invalid()
        except StateError as backup_error:
            QMessageBox.critical(None, tr("Cannot open session"), tr(str(backup_error)))
            return 1
        QMessageBox.warning(
            None, tr("Session recovery"),
            tr("{error}\n\nThe original data were preserved in:\n{backup}\n"
               "The application will open a new empty session.", error=str(exc), backup=backup),
        )
        session = Session()
    from insta_g.gui.window import MainWindow

    window = MainWindow(store, session, preferences=preferences,
                        preferences_store=preferences_store, theme_manager=theme_manager)
    window.showMaximized()
    if args.images:
        window.import_paths(args.images)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
