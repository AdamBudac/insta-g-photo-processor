"""Import review and checked export use only generated photos and isolated state."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from threading import Event

import pytest
from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QPushButton

from insta_g.core.export import ExportReport, export_records
from insta_g.core.models import ImageRecord
from insta_g.gui import workers
from insta_g.gui.library import STATUS_ROLE
from insta_g.gui.window import MainWindow
from insta_g.i18n import get_language, set_language
from insta_g.persistence import Session, SessionStore


@pytest.fixture(autouse=True)
def slovak_interface():
    previous = get_language()
    set_language("sk")
    yield
    set_language(previous)


@pytest.fixture
def window_factory(qtbot, tmp_path):
    windows = []

    def close_safely(window):
        # Finish deferred closing before pytest-qt deletes worker signals and pools.
        window.close()
        qtbot.waitUntil(lambda: not window._jobs and window._writer.is_idle, timeout=20000)
        window.close()

    def create(session=None):
        state = session if session is not None else Session()
        store = SessionStore(tmp_path / f"review-session-{len(windows)}.json")
        store.save(state)
        window = MainWindow(store, state)
        windows.append(window)
        qtbot.addWidget(window, before_close_func=close_safely)
        window.show()
        return window

    return create


def photographs(tmp_path: Path, count: int = 3) -> list[str]:
    paths = []
    for index in range(count):
        path = tmp_path / f"review-{index}.png"
        Image.new("RGB", (360, 120), (40 + 40 * index, 80, 120)).save(path)
        paths.append(str(path))
    return paths


def idle(qtbot, window, count: int) -> None:
    qtbot.waitUntil(lambda: len(window.session.records) == count, timeout=15000)
    qtbot.waitUntil(
        lambda: not window._jobs and not window._preview_timer.isActive()
        and not window._preview_pending and window._writer.is_idle, timeout=15000
    )


def saved_session(qtbot, window):
    qtbot.waitUntil(lambda: window._writer.is_idle, timeout=20000)
    return window.store.load()


def statuses(window) -> list[str]:
    return [window.image_list.item(row).data(STATUS_ROLE) for row in range(window.image_list.count())]


def click_row(qtbot, window, row: int) -> None:
    item = window.image_list.item(row)
    window.image_list.scrollToItem(item)
    qtbot.mouseClick(
        window.image_list.viewport(), Qt.MouseButton.LeftButton,
        pos=window.image_list.visualItemRect(item).center(),
    )


def test_imported_thumbnails_do_not_select_or_prepare_any_photo(window_factory, qtbot, tmp_path):
    window = window_factory()
    window.import_paths(photographs(tmp_path))
    idle(qtbot, window, 3)

    assert all(not window.image_list.item(row).icon().isNull() for row in range(3))
    assert window.image_list.currentRow() == -1
    assert window._record() is None
    assert window.session.selected_path is None
    assert window.preview._pixmap is None
    assert statuses(window) == ["imported"] * 3
    assert all(not record.previewed and record.status == "imported" for record in window.session.records)
    saved = saved_session(qtbot, window)
    assert saved.selected_path is None
    assert all(not record.previewed for record in saved.records)


def test_only_opened_photo_is_prepared_and_restored_without_automatic_selection(
    window_factory, qtbot, tmp_path,
):
    paths = photographs(tmp_path)
    window = window_factory()
    window.import_paths(paths)
    idle(qtbot, window, 3)

    click_row(qtbot, window, 1)
    qtbot.waitUntil(lambda: window.session.records[1].previewed, timeout=15000)
    idle(qtbot, window, 3)
    assert window._record().path == paths[1]
    assert window.preview._pixmap is not None
    assert statuses(window) == ["imported", "staging", "imported"]
    saved = saved_session(qtbot, window)
    assert [record.previewed for record in saved.records] == [False, True, False]
    assert saved.selected_path == paths[1]

    saved.selected_path = None
    restored = window_factory(saved)
    idle(qtbot, restored, 3)
    assert restored.image_list.currentRow() == -1
    assert restored.session.selected_path is None
    assert restored.preview._pixmap is None
    assert statuses(restored) == ["imported", "staging", "imported"]
    assert [record.previewed for record in saved_session(qtbot, restored).records] == [False, True, False]


def test_cancelled_old_preview_does_not_prepare_photo_after_selecting_another(
    window_factory, qtbot, tmp_path, monkeypatch,
):
    window = window_factory()
    window.import_paths(photographs(tmp_path, 2))
    idle(qtbot, window, 2)
    started = Event()
    release = Event()
    original_render = workers.PreviewRenderer.render

    def delayed_first_preview(renderer, image, settings, *, max_edge=2048, cancelled=None):
        if image.getpixel((0, 0)) == (40, 80, 120):
            started.set()
            if not release.wait(10):
                raise RuntimeError("Preview synchronization timed out")
        return original_render(renderer, image, settings, max_edge=max_edge, cancelled=cancelled)

    monkeypatch.setattr(workers.PreviewRenderer, "render", delayed_first_preview)
    try:
        click_row(qtbot, window, 0)
        qtbot.waitUntil(started.is_set, timeout=5000)
        old_job = window._preview_job
        assert not window.session.records[0].previewed
        click_row(qtbot, window, 1)
        assert old_job.cancel.is_set()
        release.set()
        idle(qtbot, window, 2)
        assert [record.previewed for record in window.session.records] == [False, True]
        assert statuses(window) == ["imported", "staging"]
        assert [record.previewed for record in saved_session(qtbot, window).records] == [False, True]
    finally:
        release.set()


def test_failed_preview_marks_failed_without_preparing_and_displays_error(
    window_factory, qtbot, tmp_path, monkeypatch,
):
    paths = photographs(tmp_path, 1)
    window = window_factory()
    window.import_paths(paths)
    idle(qtbot, window, 1)

    def fail_preview(renderer, image, settings, *, max_edge=2048, cancelled=None):
        raise ValueError("generated preview failure")

    monkeypatch.setattr(workers.PreviewRenderer, "render", fail_preview)
    click_row(qtbot, window, 0)
    qtbot.waitUntil(lambda: "generated preview failure" in window.notice.text(), timeout=10000)
    idle(qtbot, window, 1)
    assert window.notice.isVisible()
    assert ("preview", paths[0]) in window._notices
    assert window.preview._pixmap is None
    assert not window.session.records[0].previewed
    assert statuses(window) == ["failed"]
    assert not saved_session(qtbot, window).records[0].previewed


def test_checkboxes_do_not_prepare_photos_and_button_exports_only_checked(
    window_factory, qtbot, tmp_path, monkeypatch,
):
    paths = photographs(tmp_path)
    window = window_factory()
    button = window.findChild(QPushButton, "exportCheckedButton")
    assert button is window.export_checked_button
    assert not button.isEnabled()
    window.import_paths(paths)
    idle(qtbot, window, 3)
    assert not button.isEnabled()
    initial_settings = [record.settings.to_dict() for record in window.session.records]

    for row in (0, 2):
        item = window.image_list.item(row)
        rect = window.image_list.visualItemRect(item)
        qtbot.mouseClick(
            window.image_list.viewport(), Qt.MouseButton.LeftButton,
            pos=window.image_list.delegate.checkbox_rect(rect).center(),
        )
    assert not button.isEnabled()
    assert window.session.selected_path is None
    assert window.preview._pixmap is None
    assert [record.checked for record in window.session.records] == [True, False, True]
    assert statuses(window) == ["imported"] * 3
    assert all(not record.previewed for record in window.session.records)

    for row in (0, 2):
        click_row(qtbot, window, row)
        qtbot.waitUntil(lambda: window.session.records[row].previewed, timeout=15000)
        idle(qtbot, window, 3)
    assert button.isEnabled()
    assert [record.checked for record in window.session.records] == [True, False, True]
    assert statuses(window) == ["staging", "imported", "staging"]
    unseen = window.session.records[1].to_dict()

    directory = tmp_path / "checked-export"
    directory.mkdir()
    window.preferences.export_dir = str(directory)
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: window._export_job is None, timeout=20000)
    exported = list(directory.glob("*.jpg"))
    assert len(exported) == 6
    assert {path.stem.rsplit("_", 1)[0] for path in exported} == {Path(paths[0]).stem, Path(paths[2]).stem}
    assert statuses(window) == ["exported", "imported", "exported"]
    assert [record.is_exported for record in window.session.records] == [True, False, True]
    assert [record.previewed for record in window.session.records] == [True, False, True]
    assert window.session.records[1].to_dict() == unseen
    assert [record.settings.to_dict() for record in window.session.records] == initial_settings
    assert all(Path(path).exists() for path in paths)
    assert button.isEnabled()
    saved = saved_session(qtbot, window)
    assert [record.checked for record in saved.records] == [True, False, True]
    assert [record.is_exported for record in saved.records] == [True, False, True]
    assert [record.previewed for record in saved.records] == [True, False, True]
    assert saved.records[1].to_dict() == unseen


def test_checked_export_snapshots_selection_before_checkboxes_change(
    window_factory, qtbot, tmp_path, monkeypatch,
):
    paths = photographs(tmp_path)
    window = window_factory()
    window.import_paths(paths)
    idle(qtbot, window, 3)
    for row in (0, 2):
        click_row(qtbot, window, row)
        qtbot.waitUntil(lambda: window.session.records[row].previewed, timeout=15000)
        idle(qtbot, window, 3)
        window.image_list.item(row).setCheckState(Qt.CheckState.Checked)
    started = Event()
    release = Event()
    snapshot = {}

    def controlled_export(records, output_dir, progress=None, cancelled=None, **kwargs):
        snapshot.update((record.path, record.settings.to_dict()) for record in records)
        started.set()
        if not release.wait(10):
            raise RuntimeError("Export synchronization timed out")
        return ExportReport(completed=snapshot.copy())

    monkeypatch.setattr(workers, "export_records", controlled_export)
    try:
        (tmp_path / "snapshot-export").mkdir()
        window.start_export(str(tmp_path / "snapshot-export"), checked_only=True)
        qtbot.waitUntil(started.is_set, timeout=5000)
        assert set(snapshot) == {paths[0], paths[2]}
        assert not window.export_checked_button.isEnabled()
        window.image_list.item(0).setCheckState(Qt.CheckState.Unchecked)
        window.image_list.item(1).setCheckState(Qt.CheckState.Checked)
        assert [record.checked for record in window.session.records] == [False, True, True]
        assert not window.export_checked_button.isEnabled()
        release.set()
        qtbot.waitUntil(lambda: window._export_job is None, timeout=10000)
        assert statuses(window) == ["exported", "imported", "exported"]
        assert [record.is_exported for record in window.session.records] == [True, False, True]
        assert [record.previewed for record in window.session.records] == [True, False, True]
        assert window.export_checked_button.isEnabled()
        saved = saved_session(qtbot, window)
        assert [record.checked for record in saved.records] == [False, True, True]
        assert [record.is_exported for record in saved.records] == [True, False, True]
        assert [record.previewed for record in saved.records] == [True, False, True]
        window.image_list.item(2).setCheckState(Qt.CheckState.Unchecked)
        assert not window.export_checked_button.isEnabled()
        assert not window.export_checked_action.isEnabled()
        assert window.export_button.isEnabled()
        assert window.export_action.isEnabled()
    finally:
        release.set()


@pytest.mark.parametrize("check_all", [False, True])
def test_all_imported_photos_cannot_open_export_dialog_or_start_export(
    window_factory, qtbot, tmp_path, monkeypatch, check_all,
):
    window = window_factory()
    paths = photographs(tmp_path)
    window.import_paths(paths)
    idle(qtbot, window, 3)
    if check_all:
        for row in range(3):
            window.image_list.item(row).setCheckState(Qt.CheckState.Checked)
    before = asdict(window.session)
    original_bytes = {path: Path(path).read_bytes() for path in paths}

    assert statuses(window) == ["imported"] * 3
    for control in (
        window.export_button, window.export_checked_button,
        window.export_action, window.export_checked_action,
    ):
        assert not control.isEnabled()

    def unexpected_export(*args, **kwargs):
        pytest.fail("Imported photos must not open a dialog or start an export worker")

    monkeypatch.setattr(QFileDialog, "getExistingDirectory", unexpected_export)
    monkeypatch.setattr(workers, "export_records", unexpected_export)
    window.choose_export()
    window.choose_export_checked()
    for checked_only in (False, True):
        directory = tmp_path / f"blocked-{checked_only}"
        window.start_export(str(directory), checked_only=checked_only)
        assert window._export_job is None
        assert not window._jobs
        assert not directory.exists()
        assert asdict(window.session) == before
        assert asdict(saved_session(qtbot, window)) == before
    assert statuses(window) == ["imported"] * 3
    assert {path: Path(path).read_bytes() for path in paths} == original_bytes


def test_export_all_snapshots_only_prepared_and_exported_and_preserves_existing_jpegs(
    window_factory, qtbot, tmp_path, monkeypatch,
):
    paths = photographs(tmp_path)
    records = [
        ImageRecord(paths[0], checked=True),
        ImageRecord(paths[1], previewed=True),
        ImageRecord(paths[2], checked=True),
    ]
    records[2].exported_settings = records[2].settings.to_dict()
    directory = tmp_path / "mixed-all-export"
    previous = export_records([records[2]], directory)
    assert not previous.errors
    assert len(previous.paths) == 3
    previous_bytes = {path: Path(path).read_bytes() for path in previous.paths}
    window = window_factory(Session(records=records))
    idle(qtbot, window, 3)
    assert statuses(window) == ["imported", "staging", "exported"]
    assert [record.previewed for record in records] == [False, True, False]
    blue = records[0].to_dict()
    initial_settings = [record.settings.to_dict() for record in records]
    started = Event()
    release = Event()
    snapshot = {}

    def controlled_export(sources, output_dir, progress=None, cancelled=None, **kwargs):
        snapshot.update((record.path, record.settings.to_dict()) for record in sources)
        started.set()
        if not release.wait(10):
            raise RuntimeError("Export synchronization timed out")
        return export_records(sources, output_dir, progress=progress, cancelled=cancelled, **kwargs)

    monkeypatch.setattr(workers, "export_records", controlled_export)
    try:
        window.start_export(str(directory))
        qtbot.waitUntil(started.is_set, timeout=5000)
        assert set(snapshot) == {paths[1], paths[2]}
        assert statuses(window) == ["imported", "staging", "exported"]
        assert [record.checked for record in records] == [True, False, True]
        assert [record.previewed for record in records] == [False, True, False]
        release.set()
        qtbot.waitUntil(lambda: window._export_job is None, timeout=20000)
        assert len(list(directory.glob("*.jpg"))) == 9
        assert {path: Path(path).read_bytes() for path in previous.paths} == previous_bytes
        assert not list(directory.glob(f"{Path(paths[0]).stem}_*.jpg"))
        assert statuses(window) == ["imported", "exported", "exported"]
        assert [record.is_exported for record in records] == [False, True, True]
        assert [record.checked for record in records] == [True, False, True]
        assert [record.previewed for record in records] == [False, True, False]
        assert [record.settings.to_dict() for record in records] == initial_settings
        assert records[0].to_dict() == blue
        saved = saved_session(qtbot, window)
        assert [record.status for record in saved.records] == ["imported", "exported", "exported"]
        assert saved.records[0].to_dict() == blue
        assert [record.previewed for record in saved.records] == [False, True, False]
    finally:
        release.set()


def test_checked_export_excludes_checked_imported_and_unchecked_exported_photos(
    window_factory, qtbot, tmp_path, monkeypatch,
):
    paths = photographs(tmp_path)
    records = [
        ImageRecord(paths[0], checked=True),
        ImageRecord(paths[1], checked=True, previewed=True),
        ImageRecord(paths[2]),
    ]
    records[2].exported_settings = records[2].settings.to_dict()
    window = window_factory(Session(records=records))
    idle(qtbot, window, 3)
    unchanged = {row: records[row].to_dict() for row in (0, 2)}
    assert statuses(window) == ["imported", "staging", "exported"]
    directory = tmp_path / "mixed-checked-export"
    directory.mkdir()
    window.preferences.export_dir = str(directory)

    window.export_checked_action.trigger()
    qtbot.waitUntil(lambda: window._export_job is None, timeout=20000)
    exported = list(directory.glob("*.jpg"))
    assert len(exported) == 3
    assert {path.stem.rsplit("_", 1)[0] for path in exported} == {Path(paths[1]).stem}
    assert statuses(window) == ["imported", "exported", "exported"]
    assert [record.checked for record in records] == [True, True, False]
    assert [record.previewed for record in records] == [False, True, False]
    assert {row: records[row].to_dict() for row in (0, 2)} == unchanged
    assert [record.to_dict() for record in saved_session(qtbot, window).records] == [
        record.to_dict() for record in records
    ]


def test_photo_prepared_during_export_waits_for_next_batch(
    window_factory, qtbot, tmp_path, monkeypatch,
):
    paths = photographs(tmp_path, 2)
    window = window_factory()
    window.import_paths(paths)
    idle(qtbot, window, 2)
    click_row(qtbot, window, 0)
    qtbot.waitUntil(lambda: window.session.records[0].previewed, timeout=15000)
    idle(qtbot, window, 2)
    started = Event()
    release = Event()
    snapshot = {}

    def controlled_export(records, output_dir, progress=None, cancelled=None, **kwargs):
        snapshot.update((record.path, record.settings.to_dict()) for record in records)
        started.set()
        if not release.wait(10):
            raise RuntimeError("Export synchronization timed out")
        return export_records(records, output_dir, progress=progress, cancelled=cancelled, **kwargs)

    directory = tmp_path / "prepare-during-export"
    directory.mkdir()
    monkeypatch.setattr(workers, "export_records", controlled_export)
    try:
        window.start_export(str(directory))
        qtbot.waitUntil(started.is_set, timeout=5000)
        assert set(snapshot) == {paths[0]}
        click_row(qtbot, window, 1)
        qtbot.waitUntil(lambda: window.session.records[1].previewed, timeout=10000)
        assert statuses(window) == ["staging", "staging"]
        assert set(snapshot) == {paths[0]}
        release.set()
        qtbot.waitUntil(lambda: window._export_job is None, timeout=20000)
        exported = list(directory.glob("*.jpg"))
        assert len(exported) == 3
        assert {path.stem.rsplit("_", 1)[0] for path in exported} == {Path(paths[0]).stem}
        assert statuses(window) == ["exported", "staging"]
        assert [record.checked for record in window.session.records] == [False, False]
        assert [record.previewed for record in window.session.records] == [True, True]
        assert [record.status for record in saved_session(qtbot, window).records] == ["exported", "staging"]
    finally:
        release.set()
