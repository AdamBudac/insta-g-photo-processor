"""Composition controls and their tooltips share the same inherited font."""

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QToolTip

from insta_g.core.models import Settings
from insta_g.gui.themes import stylesheet
from insta_g.gui.widgets import SettingsPanel
from insta_g.i18n import get_language, set_language


@pytest.fixture(autouse=True)
def restore_application_style(qapp):
    previous = qapp.styleSheet()
    previous_language = get_language()
    yield
    QToolTip.hideText()
    qapp.setStyleSheet(previous)
    set_language(previous_language)


@pytest.mark.parametrize("dark", [True, False])
@pytest.mark.parametrize("language", ["en", "sk", "cs"])
def test_golden_ratio_has_common_button_geometry_and_tooltip_font(qtbot, dark, language):
    set_language(language)
    QApplication.instance().setStyleSheet(stylesheet(dark))
    panel = SettingsPanel()
    qtbot.addWidget(panel)
    panel.setStyleSheet(stylesheet(dark))
    panel.set_record(Settings())
    panel.show()
    qtbot.waitExposed(panel)
    buttons = panel.grid_buttons
    golden = buttons[3]
    assert golden.text() == "φ"
    assert len({button.height() for button in buttons}) == 1
    assert abs(golden.width() - buttons[2].width()) <= 1
    assert len({button.font().toString() for button in buttons}) == 1
    assert all(button.styleSheet() == "" for button in buttons)
    tooltip_fonts = []
    tooltip_heights = []
    try:
        for button in (buttons[2], golden, buttons[4]):
            QToolTip.hideText()
            QTest.mouseMove(button, button.rect().center())
            QApplication.processEvents()
            QToolTip.showText(button.mapToGlobal(QPoint(0, button.height())), button.toolTip(), button)
            qtbot.waitUntil(QToolTip.isVisible, timeout=2000)
            qtbot.wait(10)  # Let the reused native tooltip finish style polish/resize.
            tooltip = next(widget for widget in QApplication.topLevelWidgets()
                           if widget.windowType() == Qt.WindowType.ToolTip and widget.isVisible())
            tooltip_fonts.append(tooltip.font().toString())
            tooltip_heights.append(tooltip.height())
        assert len(set(tooltip_fonts)) == 1
        assert len(set(tooltip_heights)) == 1
    finally:
        QToolTip.hideText()
