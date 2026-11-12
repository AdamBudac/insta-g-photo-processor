"""Metadata discovery never silently changes a saved Original HDR selection."""

from dataclasses import replace

import imagecodecs
import numpy as np
import pytest
from PIL import Image

from insta_g.core.hdr import detect_hdr
from insta_g.core.models import ImageRecord, Settings
from insta_g.gui.widgets import SettingsPanel
from insta_g.gui.window import MainWindow
from insta_g.persistence import Session, SessionStore


@pytest.mark.parametrize("metadata", [
    None, {}, {"description": "Decoding…"}, {"is_hdr": False},
    {"is_hdr": True, "supported": False, "error": "unsupported codec"},
])
def test_metadata_capability_updates_preserve_saved_hdr_choice(qtbot, metadata):
    panel = SettingsPanel()
    qtbot.addWidget(panel)
    saved = Settings(hdr_mode="hdr", blur=41)
    panel.set_record(saved, "saved-hdr.jpg")
    changes = []
    panel.settingsChanged.connect(changes.append)
    panel.set_hdr_info(metadata)
    assert not changes
    assert panel._settings == saved
    assert panel.hdr_button.isChecked()
    assert not panel.hdr_button.isEnabled()
    panel.blur_value.setValue(42)
    assert changes == [replace(saved, blur=42)]
    # An explicit user choice remains available while decoding is pending.
    panel.sdr_button.click()
    assert changes[-1].hdr_mode == "sdr"


@pytest.fixture
def hdr_photo(tmp_path):
    path = tmp_path / "saved-hdr.jpg"
    pixels = np.ones((48, 96, 4), dtype=np.float16)
    pixels[..., :3] = (4, 1, .5)
    companion = np.full((48, 96, 4), 128, dtype=np.uint8)
    companion[..., 3] = 255
    path.write_bytes(imagecodecs.ultrahdr_encode(
        pixels, sdr=companion, gamut="BT_2100", transfer="LINEAR", level=99,
        gainmap_level=99, scale=1, multichannel=True,
    ))
    assert detect_hdr(path).is_hdr
    return path


@pytest.fixture
def window_factory(qtbot, tmp_path):
    def close_safely(window):
        window.close()
        qtbot.waitUntil(lambda: not window._jobs, timeout=15000)
        window.close()

    def create(records, selected):
        store = SessionStore(tmp_path / "state" / "session.json")
        store.save(Session(records, selected_path=selected))
        window = MainWindow(store, store.load())
        qtbot.addWidget(window, before_close_func=close_safely)
        window.show()
        return window

    return create


def ready(qtbot, window):
    qtbot.waitUntil(lambda: window.preview._pixmap is not None and not window._jobs
                   and not window._preview_timer.isActive(), timeout=15000)


def test_actual_hdr_restore_keeps_choice_before_metadata_arrives(
    qtbot, window_factory, hdr_photo,
):
    record = ImageRecord(str(hdr_photo), Settings(hdr_mode="hdr"), previewed=True)
    window = window_factory([record], record.path)
    restored = window._record()
    # This is the cache-miss interval between restoring JSON and completing import.
    assert restored.settings.hdr_mode == window.settings._settings.hdr_mode == "hdr"
    window.settings.blur_value.setValue(53)
    assert restored.settings.hdr_mode == "hdr"
    assert window.store.load().records[0].settings.hdr_mode == "hdr"
    ready(qtbot, window)
    assert window.settings.hdr_button.isChecked() and window.settings.hdr_button.isEnabled()
    assert restored.settings.hdr_mode == "hdr"


def test_hdr_choice_survives_sdr_selection_cache_eviction_and_return(
    qtbot, window_factory, hdr_photo, tmp_path,
):
    sdr = tmp_path / "plain-sdr.png"
    Image.new("RGB", (100, 50), "#345678").save(sdr)
    records = [ImageRecord(str(hdr_photo), Settings(hdr_mode="hdr"), previewed=True),
               ImageRecord(str(sdr), Settings(), previewed=True)]
    window = window_factory(records, records[0].path)
    ready(qtbot, window)
    window.image_list.setCurrentRow(1)
    ready(qtbot, window)
    assert window.settings._settings.hdr_mode == "sdr"
    assert not window.settings.hdr_button.isEnabled()
    # Exercise the actual six-source LRU rather than just passing {} to the panel.
    for index in range(6):
        window._cache(f"generated-lru-{index}", Image.new("RGB", (8, 8)))
    assert records[0].path not in window._sources
    window.image_list.setCurrentRow(0)
    assert window.settings._settings.hdr_mode == "hdr"
    assert window._record().settings.hdr_mode == "hdr"
    window.settings.grid_buttons[1].click()
    assert window.store.load().records[0].settings.hdr_mode == "hdr"
    assert window.store.load().records[1].settings.hdr_mode == "sdr"
    ready(qtbot, window)
    assert window.settings.hdr_button.isEnabled() and window.settings.hdr_button.isChecked()
    assert window._record().settings.hdr_mode == "hdr"
