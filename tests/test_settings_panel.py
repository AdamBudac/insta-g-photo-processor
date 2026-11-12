"""Per-photo controls keep mode changes explicit and saved choices intact."""

from __future__ import annotations

from dataclasses import replace

import pytest

from insta_g.core.models import Settings
from insta_g.gui.widgets import SettingsPanel


@pytest.fixture
def panel(qtbot):
    widget = SettingsPanel()
    qtbot.addWidget(widget)
    widget.set_record(Settings(), "fotografia.jpg")
    widget.show()
    return widget


def test_mode_buttons_are_exclusive_and_fit_labels_are_explicit(panel):
    assert panel.mode_buttons.exclusive()
    assert panel.mode_buttons.buttons() == [panel.split_button, panel.expand_button]
    assert panel.split_button.isChecked()
    assert not panel.expand_button.isChecked()
    assert panel.fit_button.text() == "Fit / Padding"
    assert panel.fill_button.text() == "Fill / Crop"
    assert len(panel.ratio_buttons) == 7
    assert [button.text() for button in panel.ratio_buttons] == [
        "16:9", "3:2", "4:3", "5:4", "1:1", "4:5", "3:4",
    ]
    panel.expand_button.click()
    assert panel.expand_button.isChecked()
    assert not panel.split_button.isChecked()
    assert panel.fit_button.isChecked()
    assert not panel.fill_button.isEnabled()


@pytest.mark.parametrize(
    "saved",
    [
        Settings(mode="split", fit_mode="fit"),
        Settings(mode="split", fit_mode="fill"),
        Settings(mode="expand", fit_mode="fill", ratio_mode="fixed"),
        Settings(mode="expand", fit_mode="fit", ratio_mode="fixed"),
    ],
)
def test_loading_saved_settings_preserves_choices_without_emitting(panel, saved):
    changes = []
    panel.settingsChanged.connect(changes.append)
    panel.set_record(saved, "ulozena.jpg")
    assert not changes
    assert panel._settings == saved
    assert panel._settings is not saved
    assert panel.split_button.isChecked() == (saved.mode == "split")
    assert panel.expand_button.isChecked() == (saved.mode == "expand")
    assert panel.fit_button.isChecked() == (saved.effective_fit_mode == "fit")
    assert panel.fill_button.isChecked() == (saved.effective_fit_mode == "fill")
    panel.set_record(replace(saved, blur=123), "dalsia.jpg")
    assert not changes
    assert panel._settings.fit_mode == saved.fit_mode
    assert panel._settings.mode == saved.mode


def test_mode_switches_set_fit_defaults_and_preserve_other_adjustments(panel):
    saved = Settings(
        mode="split", fit_mode="fit", splits=5, ratio_mode="fixed", ratio=1.25,
        blur=132, offset_x=0.27, offset_y=-0.63,
    )
    panel.set_record(saved, "uprava.jpg")
    changes = []
    panel.settingsChanged.connect(changes.append)

    panel.expand_button.click()
    assert changes == [replace(saved, mode="expand", fit_mode="fit")]
    assert panel.fit_button.isChecked()
    assert not panel.fill_button.isChecked()
    assert panel.blur.isEnabled()

    panel.split_button.click()
    split = replace(saved, fit_mode="fill")
    assert changes == [replace(saved, mode="expand", fit_mode="fit"), split]
    assert panel.fill_button.isChecked()
    assert not panel.fit_button.isChecked()
    assert not panel.blur.isEnabled()

    panel.fit_button.click()
    assert len(changes) == 3
    assert changes[-1] == saved
    assert panel.fit_button.isChecked()
    assert panel.blur.isEnabled()

    # Selecting the active mode must not overwrite a deliberate Fit choice.
    panel.split_button.click()
    assert len(changes) == 3
    assert panel._settings == saved


def test_auto_ratio_is_disabled_once_when_switching_to_expand(panel):
    panel.set_record(Settings(mode="split", ratio_mode="auto", fit_mode="fill"))
    changes = []
    panel.settingsChanged.connect(changes.append)
    panel.expand_button.click()
    assert len(changes) == 1
    assert changes[0].mode == "expand"
    assert changes[0].fit_mode == "fit"
    assert changes[0].ratio_mode == "fixed"
    assert not panel.auto.isChecked()


def test_mode_and_fit_rows_fit_the_minimum_panel_width(panel, qtbot):
    panel.resize(panel.minimumWidth(), panel.sizeHint().height())
    qtbot.waitUntil(lambda: panel.width() == panel.minimumWidth())
    for first, second in (
        (panel.split_button, panel.expand_button),
        (panel.fit_button, panel.fill_button),
    ):
        assert first.geometry().top() == second.geometry().top()
        assert first.geometry().right() < second.geometry().left()
        assert first.width() > 0
        assert second.geometry().right() < panel.controls.width()
