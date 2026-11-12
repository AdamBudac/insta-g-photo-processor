"""End-to-end failures, preferences and viewport edits use generated local files."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QLabel

from insta_g.gui import workers
from insta_g.gui.library import STATUS_ROLE
from insta_g.gui.preferences_dialog import PreferencesDialog
from insta_g.gui.window import MainWindow
from insta_g.i18n import get_language, set_language
from insta_g.persistence import Session, SessionStore
from insta_g.preferences import PreferencesStore


@pytest.fixture
def window(qtbot, tmp_path: Path):
    previous_language = get_language()
    set_language("en")
    export = tmp_path / "output"
    export.mkdir()
    prefs_store = PreferencesStore(tmp_path / "preferences.json")
    preferences = replace(prefs_store.defaults(), export_dir=str(export), onboarding_completed=True)
    prefs_store.save(preferences)
    store = SessionStore(tmp_path / "session.json")
    result = MainWindow(store, Session(), preferences, prefs_store)

    def close_safely(widget):
        widget.close()
        qtbot.waitUntil(lambda: not widget._jobs and widget._writer.is_idle, timeout=20000)
        widget.close()

    qtbot.addWidget(result, before_close_func=close_safely)
    result.show()
    yield result
    result.close()
    qtbot.waitUntil(lambda: not result._jobs and result._writer.is_idle, timeout=20000)
    set_language(previous_language)


def image(path: Path, size: tuple[int, int] = (600, 200)) -> str:
    Image.new("RGB", size, (70, 130, 190)).save(path)
    return str(path)


def idle(qtbot, window) -> None:
    qtbot.waitUntil(
        lambda: not window._jobs and not window._preview_timer.isActive()
        and not window._preview_pending and window._writer.is_idle,
        timeout=20000,
    )


def saved_session(qtbot, window):
    qtbot.waitUntil(lambda: window._writer.is_idle, timeout=20000)
    return window.store.load()


def prepare(qtbot, window, paths: list[str]) -> None:
    window.import_paths(paths)
    idle(qtbot, window)
    for row in range(len(paths)):
        window.image_list.setCurrentRow(row)
        qtbot.waitUntil(lambda: window.session.records[row].previewed, timeout=20000)
        idle(qtbot, window)


def test_failed_import_is_persisted_red_and_retry_keeps_settings(window, qtbot, tmp_path):
    broken = tmp_path / "broken.png"
    broken.write_bytes(b"not a photo")
    window.import_paths([str(broken)])
    idle(qtbot, window)
    record = window.session.records[0]
    record.settings.splits = 5
    assert record.status == "failed" and record.failure_stage == "import"
    assert window.image_list.item(0).data(STATUS_ROLE) == "failed"
    assert "Could not load image" in window.image_list.item(0).toolTip()
    assert saved_session(qtbot, window).records[0].status == "failed"
    assert not window.export_button.isEnabled()
    assert window.retry_failed_button.isEnabled()
    image(broken)
    window.retry_failed_button.click()
    idle(qtbot, window)
    assert window.session.records == [record]
    assert record.status == "imported" and record.last_error is None
    assert record.settings.splits == 5
    assert window.image_list.currentRow() == -1
    assert not window.export_button.isEnabled()
    assert saved_session(qtbot, window).records[0].settings.splits == 5
    assert not window.retry_failed_button.isEnabled()


def test_remove_failed_keeps_sources_and_successful_rows(window, qtbot, tmp_path):
    broken = tmp_path / "broken.png"
    broken.write_bytes(b"invalid")
    good = image(tmp_path / "good.png")
    window.import_paths([str(broken), good])
    idle(qtbot, window)
    window.remove_failed_button.click()
    assert [record.path for record in window.session.records] == [good]
    assert broken.read_bytes() == b"invalid" and Path(good).exists()
    assert not window.remove_failed_button.isEnabled()
    assert not window.notice.isVisible()
    assert [record.path for record in saved_session(qtbot, window).records] == [good]


def test_export_summary_counts_originals_and_outputs_separately(window, qtbot, tmp_path, monkeypatch):
    paths = [image(tmp_path / f"photo-{index}.png") for index in range(2)]
    prepare(qtbot, window, paths)
    window.export_button.click()
    idle(qtbot, window)
    summary = window._summary_dialog
    assert summary is not None and summary.isVisible()
    assert summary.findChild(QLabel, "summaryProcessed").text() == "2"
    assert summary.findChild(QLabel, "summaryOutputs").text() == "6"
    assert summary.findChild(QLabel, "summaryFailed").text() == "0"
    assert len(list(Path(window.preferences.export_dir).glob("*.jpg"))) == 6
    opened = []
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: opened.append(url.toLocalFile()) or True)
    summary.open_button.click()
    assert [Path(path) for path in opened] == [Path(window.preferences.export_dir)]
    summary.ok_button.click()
    assert not summary.isVisible()


def test_export_failure_can_be_retried_after_source_is_restored(window, qtbot, tmp_path):
    source = tmp_path / "recover.png"
    prepare(qtbot, window, [image(source)])
    source.unlink()
    window.export_button.click()
    idle(qtbot, window)
    record = window.session.records[0]
    assert record.status == "failed" and record.failure_stage == "export"
    assert window._summary_dialog.findChild(QLabel, "summaryFailed").text() == "1"
    assert not list(Path(window.preferences.export_dir).iterdir())
    window._summary_dialog.accept()
    image(source)
    window.retry_failed_button.click()
    idle(qtbot, window)
    assert record.status == "exported" and record.last_error is None
    assert len(list(Path(window.preferences.export_dir).glob("*.jpg"))) == 3
    assert saved_session(qtbot, window).records[0].is_exported


def test_deleted_configured_export_folder_is_reported_and_not_recreated(window, qtbot, tmp_path):
    prepare(qtbot, window, [image(tmp_path / "photo.png")])
    export = Path(window.preferences.export_dir)
    export.rmdir()
    window.export_button.click()
    assert not export.exists()
    assert window._export_job is None
    assert "Export folder does not exist" in window.notice.text()
    assert window.session.records[0].status == "staging"


def test_grid_change_preserves_export_and_mouse_drag_persists_offsets(window, qtbot, tmp_path):
    prepare(qtbot, window, [image(tmp_path / "wide.png", (600, 100))])
    window.settings.splits.setValue(2)
    window.settings.ratio_buttons[4].click()
    idle(qtbot, window)
    window.export_button.click()
    idle(qtbot, window)
    window._summary_dialog.accept()
    record = window.session.records[0]
    assert record.is_exported
    window.settings.grid_buttons[2].click()
    assert record.settings.grid == "thirds" and record.is_exported
    assert window.image_list.item(0).data(STATUS_ROLE) == "exported"
    assert saved_session(qtbot, window).records[0].is_exported
    preview = window.preview
    start = preview.rect().center()
    qtbot.mousePress(preview, Qt.MouseButton.LeftButton, pos=start)
    qtbot.mouseMove(preview, pos=start + QPoint(29, 0))
    qtbot.mouseRelease(preview, Qt.MouseButton.LeftButton, pos=start + QPoint(29, 0))
    idle(qtbot, window)
    assert record.settings.offset_x != 0
    assert not record.is_exported
    assert saved_session(qtbot, window).records[0].settings.offset_x == record.settings.offset_x
    qtbot.mouseDClick(preview, Qt.MouseButton.LeftButton, pos=start)
    idle(qtbot, window)
    assert record.settings.offset_x == record.settings.offset_y == 0
    assert window.settings.offset_x.value() == window.settings.offset_y.value() == 0


def test_preferences_apply_live_and_cancel_keeps_previous_values(window, monkeypatch):
    original = replace(window.preferences)

    def cancel(dialog):
        dialog.language_combo.setCurrentIndex(dialog.language_combo.findData("sk"))
        dialog.theme_combo.setCurrentIndex(dialog.theme_combo.findData("dark"))
        dialog.reject()
        return dialog.DialogCode.Rejected

    monkeypatch.setattr(PreferencesDialog, "exec", cancel)
    window.show_preferences()
    assert window.preferences == original and get_language() == "en"
    assert window.preferences_store.load() == original

    def accept(dialog):
        dialog.language_combo.setCurrentIndex(dialog.language_combo.findData("cs"))
        dialog.theme_combo.setCurrentIndex(dialog.theme_combo.findData("light"))
        dialog.accept()
        return dialog.DialogCode.Accepted

    monkeypatch.setattr(PreferencesDialog, "exec", accept)
    window.show_preferences()
    assert get_language() == "cs" and window.preferences.language == "cs"
    assert window.preferences.theme == "light"
    assert window.export_button.text() == "Exportovat všechny"
    assert window.preferences_store.load() == window.preferences


def test_language_change_retranslates_existing_import_notice_and_tooltip(
    window, qtbot, tmp_path, monkeypatch,
):
    broken = tmp_path / "broken.png"
    broken.write_bytes(b"not an image")
    window.import_paths([str(broken)])
    idle(qtbot, window)
    assert "Could not load image" in window.notice.text()

    def accept(dialog):
        dialog.language_combo.setCurrentIndex(dialog.language_combo.findData("cs"))
        dialog.accept()
        return dialog.DialogCode.Accepted

    monkeypatch.setattr(PreferencesDialog, "exec", accept)
    window.show_preferences()

    assert "se nepodařilo načíst" in window.notice.text()
    assert "se nepodařilo načíst" in window.statusBar().currentMessage()
    assert "se nepodařilo načíst" in window.image_list.item(0).toolTip()
    assert "Could not load image" not in window.notice.text()


def test_preview_failure_and_recovery_preserve_existing_export_failure(
    window, qtbot, tmp_path, monkeypatch,
):
    source = tmp_path / "photo.png"
    prepare(qtbot, window, [image(source)])
    source.unlink()
    window.export_button.click()
    idle(qtbot, window)
    window._summary_dialog.accept()
    record = window.session.records[0]
    export_error = record.last_error
    assert record.failure_stage == "export" and export_error
    original_render = workers.PreviewRenderer.render

    def fail_preview(*args, **kwargs):
        raise ValueError("unrelated temporary preview failure")

    monkeypatch.setattr(workers.PreviewRenderer, "render", fail_preview)
    window._queue_preview()
    idle(qtbot, window)
    assert ("preview", str(source)) in window._notices
    assert record.failure_stage == "export" and record.last_error == export_error

    monkeypatch.setattr(workers.PreviewRenderer, "render", original_render)
    window._queue_preview()
    idle(qtbot, window)
    assert ("preview", str(source)) not in window._notices
    assert record.failure_stage == "export" and record.last_error == export_error
    assert record.status == "failed"
    assert window.image_list.item(0).data(STATUS_ROLE) == "failed"
    restored = saved_session(qtbot, window).records[0]
    assert restored.last_error == export_error and restored.failure_stage == "export"
    assert window.retry_failed_button.isEnabled()
    assert not window.export_button.isEnabled()
    assert "unrelated temporary preview failure" not in window.notice.text()
