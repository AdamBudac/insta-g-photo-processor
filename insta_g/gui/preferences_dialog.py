"""Reversible global preferences, first-run setup and bundled user guide."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from insta_g.i18n import tr
from insta_g.preferences import AppPreferences


class PreferencesDialog(QDialog):
    def __init__(
        self, preferences: AppPreferences, parent: QWidget | None = None,
        first_run: bool = False, defaults: AppPreferences | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("preferencesDialog")
        self._original = replace(preferences)
        self._defaults = replace(defaults) if defaults is not None else AppPreferences(
            export_dir=preferences.export_dir,
        )
        self._first_run = first_run
        self.result_preferences: AppPreferences | None = None
        self.setWindowTitle(tr("Welcome to Insta G Photo Processor" if first_run else "Preferences"))
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(18)
        if first_run:
            intro = QLabel(tr("Choose your export folder, appearance and language. You can change these later in Preferences."))
            intro.setObjectName("setupIntroduction")
            intro.setWordWrap(True)
            layout.addWidget(intro)
        form = QFormLayout()
        form.setSpacing(14)
        folder_row = QHBoxLayout()
        self.export_folder = QLineEdit(preferences.export_dir)
        self.export_folder.setObjectName("preferencesExportFolder")
        self.export_folder.setMinimumWidth(270)
        self.browse_button = QPushButton(tr("Browse…"))
        self.browse_button.setObjectName("preferencesBrowseButton")
        self.browse_button.clicked.connect(self._browse)
        folder_row.addWidget(self.export_folder, 1)
        folder_row.addWidget(self.browse_button)
        form.addRow(tr("Default export folder"), folder_row)
        self.theme_combo = QComboBox()
        self.theme_combo.setObjectName("preferencesTheme")
        for source, value in (("Follow system", "system"), ("Light", "light"), ("Dark", "dark")):
            self.theme_combo.addItem(tr(source), value)
        self.theme_combo.setCurrentIndex(self.theme_combo.findData(preferences.theme))
        form.addRow(tr("Appearance"), self.theme_combo)
        self.language_combo = QComboBox()
        self.language_combo.setObjectName("preferencesLanguage")
        for label, code in (("English", "en"), ("Slovenčina", "sk"), ("Čeština", "cs")):
            self.language_combo.addItem(label, code)
        self.language_combo.setCurrentIndex(self.language_combo.findData(preferences.language))
        form.addRow(tr("Language"), self.language_combo)
        layout.addLayout(form)
        hint = QLabel(tr("Choose an existing folder. The application will not recreate a deleted export folder."))
        hint.setObjectName("secondaryText")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.error = QLabel()
        self.error.setObjectName("preferencesError")
        self.error.setWordWrap(True)
        self.error.hide()
        layout.addWidget(self.error)
        self.buttons = QDialogButtonBox()
        self.save_button = self.buttons.addButton(tr("OK"), QDialogButtonBox.ButtonRole.AcceptRole)
        self.save_button.setObjectName("preferencesSaveButton")
        self.save_button.setDefault(True)
        self.cancel_button = self.buttons.addButton(tr("Cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        self.cancel_button.setObjectName("preferencesCancelButton")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        if first_run:
            self.skip_button = self.buttons.addButton(tr("Use defaults / Skip"), QDialogButtonBox.ButtonRole.ResetRole)
            self.skip_button.setObjectName("preferencesSkipButton")
            self.skip_button.clicked.connect(self._skip)
        layout.addWidget(self.buttons)

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, tr("Choose export folder"), self.export_folder.text())
        if folder:
            self.export_folder.setText(folder)

    def _skip(self) -> None:
        self.result_preferences = replace(self._defaults, onboarding_completed=True)
        super().accept()

    def accept(self) -> None:
        candidate = AppPreferences(
            export_dir=self.export_folder.text().strip(),
            theme=self.theme_combo.currentData(),
            language=self.language_combo.currentData(),
            onboarding_completed=True if self._first_run else self._original.onboarding_completed,
        )
        try:
            candidate.validate()
        except (TypeError, ValueError):
            self.error.setText(tr("Export folder must be an absolute path."))
            self.error.show()
            self.export_folder.setFocus()
            return
        self.result_preferences = candidate
        super().accept()

    def reject(self) -> None:
        self.result_preferences = None
        super().reject()

    def preferences(self) -> AppPreferences:
        """Return a copy; cancelling never changes the original object."""
        return replace(self.result_preferences if self.result_preferences is not None else self._original)


def user_guide_path(language: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    filename = {"sk": "README-user-sk.md", "cs": "README-user-cz.md"}.get(
        language, "README-user.md",
    )
    localized = root / filename
    return localized if localized.is_file() else root / "README-user.md"


class HelpDialog(QDialog):
    def __init__(self, language: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("userGuideDialog")
        self.setWindowTitle(tr("User guide"))
        self.resize(780, 720)
        self.setMinimumSize(500, 400)
        layout = QVBoxLayout(self)
        self.browser = QTextBrowser()
        self.browser.setObjectName("userGuideBrowser")
        self.browser.setOpenExternalLinks(True)
        guide = user_guide_path(language)
        self.browser.document().setBaseUrl(QUrl.fromLocalFile(str(guide.parent) + "/"))
        try:
            self.browser.setMarkdown(guide.read_text(encoding="utf-8"))
        except (OSError, UnicodeError):
            self.browser.setPlainText(tr("The user guide could not be loaded."))
        layout.addWidget(self.browser, 1)
        buttons = QDialogButtonBox()
        self.close_button = buttons.addButton(tr("Close"), QDialogButtonBox.ButtonRole.RejectRole)
        self.close_button.setObjectName("closeUserGuideButton")
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
