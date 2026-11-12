"""Save ordering and snapshot isolation use generated records and temporary files."""

from __future__ import annotations

import threading
from dataclasses import replace
from pathlib import Path
from threading import Event

from PySide6.QtCore import QThread

from insta_g.core.models import ImageRecord, Settings
from insta_g.gui.session_writer import SessionWriter
from insta_g.persistence import Session, SessionStore


class ControlledStore(SessionStore):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.started = Event()
        self.release = Event()
        self.snapshots: list[Session] = []
        self.threads: list[int] = []
        self.fail_revisions: set[int] = set()

    def save(self, session: Session) -> None:
        self.started.set()
        if not self.release.wait(10):
            raise TimeoutError("controlled writer was not released")
        self.threads.append(threading.get_ident())
        self.snapshots.append(session)
        if len(self.snapshots) in self.fail_revisions:
            raise OSError("simulated save failure")
        super().save(session)


def test_every_revision_is_saved_in_order_with_independent_settings(qtbot, tmp_path):
    store = ControlledStore(tmp_path / "session.json")
    writer = SessionWriter(store)
    record = ImageRecord(str(tmp_path / "generated.jpg"), Settings(blur=40))
    session = Session([record], record.path, str(tmp_path / "output"))
    saved = []
    idle = []
    writer.saved.connect(saved.append)
    writer.idleChanged.connect(idle.append)
    try:
        revisions = [writer.submit(session)]
        qtbot.waitUntil(store.started.is_set)
        for value in range(41, 61):
            record.settings = replace(record.settings, blur=value)
            revisions.append(writer.submit(session, changed=record))
        record.settings.blur = 999
        assert writer.pending_count == len(revisions) and not writer.is_idle
        store.release.set()
        qtbot.waitUntil(lambda: writer.is_idle, timeout=15000)
        assert saved == revisions == list(range(1, 22))
        assert [snapshot.records[0].settings.blur for snapshot in store.snapshots] == list(range(40, 61))
        assert store.load().records[0].settings.blur == 60
        assert writer.pending_count == 0 and idle == [False, True]
    finally:
        store.release.set()
        qtbot.waitUntil(lambda: writer.is_idle, timeout=15000)


def test_changed_hint_reuses_frozen_records_but_copies_mutable_fields(qtbot, tmp_path):
    store = ControlledStore(tmp_path / "session.json")
    writer = SessionWriter(store)
    first = ImageRecord(str(tmp_path / "first.jpg"))
    second = ImageRecord(str(tmp_path / "second.jpg"))
    second.exported_settings = second.settings.to_dict()
    session = Session([first, second])
    try:
        writer.submit(session)
        first.settings.offset_x = .375
        writer.submit(session, changed=first)
        first.settings.offset_x = .99
        second.settings.blur = 777
        second.exported_settings["blur"] = 888
        store.release.set()
        qtbot.waitUntil(lambda: writer.is_idle, timeout=10000)
        before, after = store.snapshots
        assert before.records[0] is not after.records[0]
        assert before.records[1] is after.records[1]
        assert before.records[0].settings.offset_x == 0
        assert after.records[0].settings.offset_x == .375
        assert after.records[1].settings.blur == 40
        assert after.records[1].exported_settings["blur"] == 40
        assert after.records[1].settings is not second.settings
        assert after.records[1].exported_settings is not second.exported_settings
    finally:
        store.release.set()
        qtbot.waitUntil(lambda: writer.is_idle, timeout=10000)


def test_bulk_refresh_and_membership_changes_never_reuse_removed_records(qtbot, tmp_path):
    store = ControlledStore(tmp_path / "session.json")
    writer = SessionWriter(store)
    first = ImageRecord(str(tmp_path / "first.jpg"))
    second = ImageRecord(str(tmp_path / "second.jpg"))
    session = Session([first, second], first.path, "old-output")
    try:
        writer.submit(session)
        first.checked = True
        second.settings.blur = 93
        session.selected_path = second.path
        session.export_dir = "new-output"
        writer.submit(session)
        session.records[:] = [second]
        writer.submit(session, changed=second)
        assert id(first) not in writer._records
        replacement = ImageRecord(first.path, Settings(blur=17))
        session.records.append(replacement)
        writer.submit(session, changed=second)
        store.release.set()
        qtbot.waitUntil(lambda: writer.is_idle, timeout=10000)
        before, bulk, removed, added = store.snapshots
        assert not before.records[0].checked
        assert bulk.records[0].checked and bulk.records[1].settings.blur == 93
        assert bulk.selected_path == second.path and bulk.export_dir == "new-output"
        assert before.selected_path == first.path and before.export_dir == "old-output"
        assert [record.path for record in removed.records] == [second.path]
        assert added.records[1].settings.blur == 17
        assert len(writer._records) == 2
    finally:
        store.release.set()
        qtbot.waitUntil(lambda: writer.is_idle, timeout=10000)


def test_failure_is_reported_by_revision_and_later_success_recovers(qtbot, tmp_path):
    store = ControlledStore(tmp_path / "session.json")
    store.fail_revisions = {1}
    writer = SessionWriter(store)
    session = Session([ImageRecord(str(tmp_path / "image.jpg"))])
    saved = []
    errors = []
    writer.saved.connect(saved.append)
    writer.error.connect(lambda revision, message: errors.append((revision, message)))
    try:
        writer.submit(session)
        session.records[0].checked = True
        writer.submit(session, changed=session.records[0])
        store.release.set()
        qtbot.waitUntil(lambda: writer.is_idle, timeout=10000)
        assert saved == [2]
        assert errors == [(1, "simulated save failure")]
        assert store.load().records[0].checked
        assert len(store.snapshots) == 2
    finally:
        store.release.set()
        qtbot.waitUntil(lambda: writer.is_idle, timeout=10000)


def test_store_runs_off_gui_thread_and_public_signals_return_on_gui_thread(qtbot, qapp, tmp_path):
    store = ControlledStore(tmp_path / "session.json")
    store.release.set()
    writer = SessionWriter(store)
    callbacks = []
    writer.saved.connect(lambda revision: callbacks.append(QThread.currentThread()))
    writer.idleChanged.connect(lambda idle: callbacks.append(QThread.currentThread()))
    writer.submit(Session())
    qtbot.waitUntil(lambda: writer.is_idle, timeout=10000)
    assert store.threads and all(thread != threading.get_ident() for thread in store.threads)
    assert callbacks and all(thread is qapp.thread() for thread in callbacks)


def test_writer_can_restart_after_idle_and_reentrant_saved_callback(qtbot, tmp_path):
    store = ControlledStore(tmp_path / "session.json")
    store.release.set()
    writer = SessionWriter(store)
    session = Session([ImageRecord(str(tmp_path / "image.jpg"))])
    idle = []
    revisions = []
    writer.idleChanged.connect(idle.append)

    def saved(revision):
        revisions.append(revision)
        if revision == 1:
            session.records[0].checked = True
            writer.submit(session, changed=session.records[0])

    writer.saved.connect(saved)
    writer.submit(session)
    qtbot.waitUntil(lambda: writer.is_idle, timeout=10000)
    assert revisions == [1, 2] and idle == [False, True]
    writer.submit(session)
    qtbot.waitUntil(lambda: writer.is_idle, timeout=10000)
    assert revisions == [1, 2, 3] and idle == [False, True, False, True]
