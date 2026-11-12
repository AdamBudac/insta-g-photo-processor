"""Catalog integrity, legacy strings and live translation without data loss."""

from __future__ import annotations

from string import Formatter

import pytest
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QComboBox, QLabel, QPushButton, QVBoxLayout, QWidget

from insta_g.i18n import CATALOG, get_language, set_language, tr, translate_widget_tree


@pytest.fixture(autouse=True)
def restore_language():
    previous = get_language()
    set_language("en")
    yield
    set_language(previous)


def test_default_english_accepts_legacy_slovak_keys() -> None:
    assert tr("Export selected") == "Export selected"
    assert tr("Exportovať vybrané") == "Export selected"
    assert tr("Pridať fotografie") == "Add photos"


def test_switching_languages_and_unknown_text() -> None:
    set_language("sk")
    assert tr("Export selected") == "Exportovať vybrané"
    set_language("cs")
    assert tr("Exportovať vybrané") == "Exportovat vybrané"
    assert tr("my-photo.jpg") == "my-photo.jpg"
    with pytest.raises(ValueError):
        set_language("de")
    assert get_language() == "cs"


def test_placeholders_are_consistent_in_every_translation() -> None:
    for row in CATALOG.values():
        fields = [{name for _, name, _, _ in Formatter().parse(text) if name is not None} for text in row]
        assert fields[0] == fields[1] == fields[2], row[0]
        assert all(text.strip() for text in row)


def test_named_values_and_formatted_templates() -> None:
    set_language("cs")
    assert tr("Errors: {count}", count=3) == "Chyby: 3"
    assert tr("Errors: {count}").format(count=4) == "Chyby: 4"
    assert tr("{count} tiles · tile ratio {ratio:.3f}:1", count=3, ratio=1.25) == "3 dílů · poměr dílu 1.250:1"


def test_existing_dynamic_errors_are_translated_without_damaging_values() -> None:
    assert tr("Obrázok „portrét {1}.heic“ sa nepodarilo načítať: decoder failed\nsecond line") == "Could not load image “portrét {1}.heic”: decoder failed\nsecond line"
    assert tr("Výstupný priečinok „C:/my export“ nie je dostupný: access denied") == "Output folder “C:/my export” is unavailable: access denied"
    set_language("cs")
    assert tr("Export „image.jpg“ zlyhal: failed") == "Export „image.jpg“ selhal: failed"
    assert tr("Original 6000 × 4000 px") == "Originál 6000 × 4000 px"


def test_nested_error_values_are_translated_with_canonical_templates() -> None:
    assert tr("Export failed: {error}", error="Podporovaný je iba JPEG, PNG a HEIC/HEIF.") == "Export failed: Only JPEG, PNG and HEIC/HEIF are supported."
    set_language("cs")
    assert tr("Cannot save preferences: C:/data/preferences.json\nUnsupported interface language.") == "Nastavení aplikace nelze uložit: C:/data/preferences.json\nNepodporovaný jazyk rozhraní."


def test_legacy_filename_prefixes_translate_nested_errors_without_translating_names() -> None:
    set_language("cs")
    source = "Pridať fotografie: outer.jpg: inner.heic: Only JPEG, PNG and HEIC/HEIF are supported."
    assert tr(source) == "Pridať fotografie: outer.jpg: inner.heic: Podporován je pouze JPEG, PNG a HEIC/HEIF."
    assert tr("broken.png: Could not load image “broken.png”: Unsupported interface language.") == "broken.png: Obrázek „broken.png“ se nepodařilo načíst: Nepodporovaný jazyk rozhraní."


@pytest.mark.parametrize("path", [
    "C:/Photos/Pridať fotografie/Dark.jpg",
    r"C:\Photos\Pridať fotografie\Dark.jpg",
    "C:/Photos/unknown.jpg: unknown decoder text",
])
def test_plain_windows_paths_and_unknown_errors_stay_unchanged(path) -> None:
    set_language("cs")
    assert tr(path) == path


def test_excessive_nested_prefixes_are_bounded_and_preserved() -> None:
    set_language("cs")
    source = "outer.jpg: " * 500 + "Unsupported interface language."
    assert tr(source) == source


def test_widget_tree_translates_repeatedly_and_preserves_combo_data(qtbot) -> None:
    root = QWidget()
    qtbot.addWidget(root)
    layout = QVBoxLayout(root)
    label = QLabel("Vaše fotografie")
    button = QPushButton("Exportovať vybrané")
    button.setToolTip("Odstrániť fotografiu z knižnice")
    filename = QLabel("Panoráma.jpg")
    combo = QComboBox()
    combo.addItem("Follow system", "system")
    combo.addItem("Dark", "dark")
    combo.setCurrentIndex(1)
    action = QAction("Pomocník", root)
    root.addAction(action)
    for widget in (label, button, filename, combo):
        layout.addWidget(widget)
    translate_widget_tree(root)
    assert label.text() == "Your photos" and button.text() == "Export selected"
    set_language("cs")
    translate_widget_tree(root)
    assert label.text() == "Vaše fotografie" and button.text() == "Exportovat vybrané"
    assert action.text() == "Nápověda"
    assert combo.currentData() == "dark" and combo.currentText() == "Tmavý"
    set_language("en")
    translate_widget_tree(root)
    assert label.text() == "Your photos" and combo.currentText() == "Dark"
    assert filename.text() == "Panoráma.jpg"
    # A dynamic filename replacing a former empty-state label must stay intact.
    label.setText("new-photo.heic")
    set_language("sk")
    translate_widget_tree(root)
    assert label.text() == "new-photo.heic"
