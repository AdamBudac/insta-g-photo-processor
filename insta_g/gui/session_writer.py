"""Ordered asynchronous session writes with privately frozen record snapshots."""

from __future__ import annotations

from collections import deque
from dataclasses import replace
from threading import Lock

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from insta_g.core.models import ImageRecord
from insta_g.persistence import Session, SessionStore


class _WriteQueue:
    """Worker-owned persistence and a synchronized FIFO; no widget references."""

    def __init__(self, store: SessionStore) -> None:
        self.store = store
        self.lock = Lock()
        self.snapshots: deque[tuple[int, Session]] = deque()
        self.running = False


class _WriterSignals(QObject):
    completed = Signal(int, object)


class _DrainWrites(QRunnable):
    def __init__(self, state: _WriteQueue, signals: _WriterSignals) -> None:
        super().__init__()
        self.state = state
        self.signals = signals

    def run(self) -> None:
        while True:
            with self.state.lock:
                if not self.state.snapshots:
                    self.state.running = False
                    return
                revision, snapshot = self.state.snapshots.popleft()
            error: str | None = None
            try:
                self.state.store.save(snapshot)
            except Exception as exception:
                error = str(exception) or type(exception).__name__
            self.signals.completed.emit(revision, error)


class SessionWriter(QObject):
    """Capture on the GUI thread and persist every revision in order.

    ``changed`` identifies the only record whose fields changed. Other records
    reuse private copies made by an earlier submission. Pass ``None`` after
    bulk changes or arbitrary external mutation to refresh every record.

    Keep this object alive until ``is_idle`` before destroying its parent. No
    pending revision is discarded, including after a failed write.
    """

    saved = Signal(int)
    error = Signal(int, str)
    idleChanged = Signal(bool)

    def __init__(self, store: SessionStore, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._state = _WriteQueue(store)
        self._signals = _WriterSignals(self)
        self._signals.completed.connect(self._completed)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self._revision = 0
        self._pending: set[int] = set()
        self._reported_idle = True
        # Retain the source identity as well as its frozen copy. An object's id
        # can otherwise be reused when library entries are removed and added.
        self._records: dict[int, tuple[ImageRecord, ImageRecord]] = {}

    @property
    def is_idle(self) -> bool:
        return not self._pending

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    @staticmethod
    def _freeze(record: ImageRecord) -> ImageRecord:
        return replace(
            record,
            settings=replace(record.settings),
            exported_settings=(
                record.exported_settings.copy() if record.exported_settings is not None else None
            ),
        )

    def submit(self, session: Session, changed: ImageRecord | None = None) -> int:
        """Enqueue a snapshot without JSON serialization or filesystem access."""
        records: list[ImageRecord] = []
        current: dict[int, tuple[ImageRecord, ImageRecord]] = {}
        for record in session.records:
            identity = id(record)
            cached = self._records.get(identity)
            if changed is None or record is changed or cached is None or cached[0] is not record:
                cached = record, self._freeze(record)
            current[identity] = cached
            records.append(cached[1])
        self._records = current
        snapshot = Session(records, session.selected_path, session.export_dir)
        self._revision += 1
        revision = self._revision
        self._pending.add(revision)
        with self._state.lock:
            self._state.snapshots.append((revision, snapshot))
            start_worker = not self._state.running
            if start_worker:
                self._state.running = True
        if self._reported_idle:
            self._reported_idle = False
            self.idleChanged.emit(False)
        if start_worker:
            self._pool.start(_DrainWrites(self._state, self._signals))
        return revision

    @Slot(int, object)
    def _completed(self, revision: int, error: object) -> None:
        self._pending.discard(revision)
        if error is None:
            self.saved.emit(revision)
        else:
            self.error.emit(revision, str(error))
        if not self._pending and not self._reported_idle:
            self._reported_idle = True
            self.idleChanged.emit(True)
