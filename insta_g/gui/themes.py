"""Application-wide light, dark and automatically updating system appearance."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QApplication


def stylesheet(dark: bool) -> str:
    colors = {
        "window": "#171c27" if dark else "#f4f6fa",
        "text": "#e5ebf7" if dark else "#192337",
        "muted": "#a6b3c9" if dark else "#52627a",
        "base": "#111925" if dark else "#ffffff",
        "panel": "#1e2635" if dark else "#ffffff",
        "menu": "#131823" if dark else "#e9eef5",
        "border": "#38465e" if dark else "#a8b7c9",
        "button": "#29364b" if dark else "#e2e9f2",
        "hover": "#354864" if dark else "#d2dfed",
        "pressed": "#1b293e" if dark else "#bccfe2",
        "disabled": "#202838" if dark else "#e8ecf1",
        "disabled_text": "#8491a6" if dark else "#798699",
        "accent": "#71dec8" if dark else "#146e5c",
        "accent_bg": "#27564f" if dark else "#cceee5",
        "accent_text": "#b9f7e6" if dark else "#124c40",
        "groove": "#334158" if dark else "#c4cfdd",
        "handle": "#8ee6d1" if dark else "#237c69",
        "list": "#141a25" if dark else "#edf1f7",
        "selection": "#263f48" if dark else "#d0ebe6",
        "warning_bg": "#32291e" if dark else "#fff0cd",
        "warning_text": "#f5c579" if dark else "#714b06",
        "error_bg": "#43262e" if dark else "#fde7e9",
        "error_text": "#ffd6dc" if dark else "#8c1f32",
    }
    sheet = """
QMainWindow, QWidget { background: %(window)s; color: %(text)s; font-family: 'Segoe UI'; font-size: 10pt; }
QMenuBar { background: %(menu)s; padding: 4px; }
QMenuBar::item { padding: 5px 11px; background: transparent; }
QMenuBar::item:selected, QMenu::item:selected { background: %(hover)s; }
QMenu { background: %(panel)s; border: 1px solid %(border)s; padding: 5px; }
QMenu::item { padding: 7px 28px; }
QLabel#brandTitle { font-size: 20pt; font-weight: 650; }
QLabel#brandAccent { color: %(accent)s; font-size: 10pt; font-weight: 600; }
QLabel#secondaryText, QLabel#selectedFilename, QLabel#geometryLabel { color: %(muted)s; }
QLabel#panelHeading { font-size: 12pt; font-weight: 650; }
QPushButton { background: %(button)s; border: 1px solid %(border)s; border-radius: 6px; padding: 9px 13px; font-weight: 600; }
QPushButton:hover { background: %(hover)s; border-color: %(accent)s; }
QPushButton:pressed { background: %(pressed)s; }
QPushButton:disabled { color: %(disabled_text)s; background: %(disabled)s; border-color: %(groove)s; }
QPushButton:checked { background: %(accent_bg)s; color: %(accent_text)s; border-color: %(accent)s; }
QPushButton[compact="true"] { padding: 7px 2px; font-size: 9pt; }
QPushButton#exportButton, QPushButton#exportCheckedButton { background: #6be0c6; color: #102922; border-color: #3cbda0; padding: 11px 25px; }
QPushButton#exportButton:hover, QPushButton#exportCheckedButton:hover { background: #91eedb; }
QPushButton#exportButton:disabled, QPushButton#exportCheckedButton:disabled { background: %(disabled)s; color: %(disabled_text)s; border-color: %(groove)s; }
QListWidget { background: %(list)s; border: 1px solid %(border)s; border-radius: 7px; outline: none; padding: 5px; }
QListWidget::item { border: 1px solid transparent; border-radius: 6px; padding: 7px; }
QListWidget::item:selected { background: %(selection)s; border-color: %(accent)s; }
QListWidget::item:hover:!selected { background: %(hover)s; }
QLineEdit, QTextEdit, QTextBrowser, QComboBox, QSpinBox, QDoubleSpinBox { background: %(base)s; border: 1px solid %(border)s; border-radius: 5px; padding: 7px; min-height: 18px; selection-background-color: %(accent_bg)s; selection-color: %(accent_text)s; }
QComboBox:disabled, QSpinBox:disabled, QLineEdit:disabled { color: %(disabled_text)s; border-color: %(groove)s; }
QComboBox QAbstractItemView { background: %(panel)s; color: %(text)s; selection-background-color: %(accent_bg)s; selection-color: %(accent_text)s; }
QComboBox::drop-down { width: 20px; border: none; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid %(border)s; border-radius: 3px; background: %(base)s; }
QCheckBox::indicator:checked { background: %(accent)s; border-color: %(accent)s; image: none; }
QSlider::groove:horizontal { height: 5px; background: %(groove)s; border-radius: 2px; }
QSlider::sub-page:horizontal { background: %(accent)s; border-radius: 2px; }
QSlider::handle:horizontal { width: 15px; margin: -5px 0; background: %(handle)s; border-radius: 7px; }
QSlider::handle:horizontal:disabled { background: %(disabled_text)s; }
QSplitter::handle { background: %(menu)s; }
QSplitter::handle:hover { background: %(accent)s; }
QScrollArea { border: none; }
QScrollBar:vertical { width: 10px; background: %(menu)s; }
QScrollBar::handle:vertical { background: %(border)s; min-height: 30px; border-radius: 4px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QProgressBar { border: 1px solid %(border)s; border-radius: 5px; text-align: center; min-height: 20px; }
QProgressBar::chunk { background: %(accent)s; border-radius: 4px; }
QStatusBar { color: %(muted)s; background: %(menu)s; }
QToolTip { background: %(panel)s; border: 1px solid %(border)s; color: %(text)s; padding: 5px; }
QLabel#ratioWarning { color: %(warning_text)s; background: %(warning_bg)s; padding: 9px; border-radius: 6px; }
QLabel#errorNotice, QLabel#preferencesError { color: %(error_text)s; background: %(error_bg)s; padding: 9px; border-radius: 6px; }
QDialogButtonBox { background: transparent; }
""" % colors
    assets = (Path(__file__).resolve().parents[1] / "assets").as_posix()
    sheet += f"""
QComboBox::down-arrow {{ image: url("{assets}/chevron-down.svg"); width: 12px; height: 10px; }}
QSpinBox::up-arrow {{ image: url("{assets}/chevron-up.svg"); width: 10px; height: 8px; }}
QSpinBox::down-arrow {{ image: url("{assets}/chevron-down.svg"); width: 10px; height: 8px; }}
QSpinBox::up-button {{ width: 20px; subcontrol-origin: border; subcontrol-position: top right; }}
QSpinBox::down-button {{ width: 20px; subcontrol-origin: border; subcontrol-position: bottom right; }}
"""
    return sheet


class ThemeManager(QObject):
    changed = Signal(bool)

    def __init__(self, app: QApplication) -> None:
        super().__init__(app)
        self.app = app
        self.theme = "system"
        self.is_dark = self._system_dark()
        app.styleHints().colorSchemeChanged.connect(self._system_changed)
        self.set_theme("system")

    def _system_dark(self) -> bool:
        scheme = self.app.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Unknown:
            return self.app.palette().window().color().lightness() < 128
        return scheme == Qt.ColorScheme.Dark

    def _system_changed(self, *_: object) -> None:
        if self.theme == "system":
            self.set_theme("system")

    def set_theme(self, theme: str) -> None:
        if theme not in ("system", "light", "dark"):
            raise ValueError(f"Unsupported appearance: {theme}")
        self.theme = theme
        self.is_dark = self._system_dark() if theme == "system" else theme == "dark"
        self.app.setProperty("theme_dark", self.is_dark)
        self.app.setStyleSheet(stylesheet(self.is_dark))
        for widget in self.app.topLevelWidgets():
            widget.update()
        self.changed.emit(self.is_dark)
