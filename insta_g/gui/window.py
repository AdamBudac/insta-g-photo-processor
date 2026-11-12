"""Three-pane application with independent image settings and background jobs."""

from __future__ import annotations

import os
from collections import OrderedDict
from dataclasses import replace
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QSize, Qt, QThreadPool, QTimer
from PySide6.QtGui import QAction, QCloseEvent, QIcon, QImage, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from insta_g.branding import PRODUCT_NAME
from insta_g.core.export import ExportReport
from insta_g.core.geometry import get_geometry
from insta_g.core.models import ImageRecord, Settings
from insta_g.gui.dialogs import ExportSummaryDialog
from insta_g.gui.library import STATUS_ROLE, ImageList
from insta_g.gui.preferences_dialog import HelpDialog, PreferencesDialog
from insta_g.gui.preview_renderer import PreviewRenderer
from insta_g.gui.session_writer import SessionWriter
from insta_g.gui.themes import ThemeManager, stylesheet
from insta_g.gui.widgets import PreviewWidget, SettingsPanel
from insta_g.gui.workers import (
    DetailJob,
    DetailRenderer,
    ExportJob,
    ImportJob,
    Job,
    PreviewJob,
    to_qimage,
)
from insta_g.i18n import set_language, tr, translate_widget_tree
from insta_g.persistence import Session, SessionStore
from insta_g.preferences import AppPreferences, PreferencesError, PreferencesStore


class MainWindow(QMainWindow):
    def __init__(self, store: SessionStore, session: Session,
                 preferences: AppPreferences | None = None,
                 preferences_store: PreferencesStore | None = None,
                 theme_manager: ThemeManager | None = None) -> None:
        super().__init__()
        self.setObjectName("mainWindow")
        self.setWindowTitle(PRODUCT_NAME)
        self.resize(1330, 850)
        self.setMinimumSize(1080, 690)
        self.store = store
        self.session = session
        self.preferences_store = preferences_store or PreferencesStore(store.path.parent / "preferences.json")
        self.preferences = preferences or self.preferences_store.defaults()
        self.theme_manager = theme_manager
        self._summary_dialog: ExportSummaryDialog | None = None
        self._help_dialog: HelpDialog | None = None
        dark = theme_manager.is_dark if theme_manager is not None else QApplication.instance().property("theme_dark")
        self.setStyleSheet(stylesheet(True if dark is None else bool(dark)))
        if theme_manager is not None:
            theme_manager.changed.connect(self._theme_changed)
        self._sizes: dict[str, tuple[int, int]] = {}
        self._sources: OrderedDict[str, Image.Image] = OrderedDict()
        self._jobs: set[Job] = set()
        self._pending_paths: set[str] = set()
        self._import_jobs: dict[str, ImportJob] = {}
        self._removed_paths: set[str] = set()
        self._export_sources: dict[str, ImageRecord] = {}
        self._generation = 0
        self._crop_origin: tuple[ImageRecord, ImageRecord] | None = None
        self._preview_job: PreviewJob | None = None
        self._export_job: ExportJob | None = None
        self._detail_generation = 0
        self._detail_job: DetailJob | None = None
        self._detail_renderer = DetailRenderer()
        self._detail_pending: tuple[object, ...] | None = None
        self._detail_pool = QThreadPool(self)
        self._detail_pool.setMaxThreadCount(1)
        self._preview_renderer = PreviewRenderer()
        self._preview_pool = QThreadPool(self)
        self._preview_pool.setMaxThreadCount(1)
        self._preview_pending = False
        self._closing = False
        self._last_save_error = ""
        self._import_errors: list[str] = []
        self._notices: OrderedDict[tuple[str, str | None], tuple[str, bool]] = OrderedDict()
        self._writer = SessionWriter(self.store, self)
        self._writer.saved.connect(self._saved)
        self._writer.error.connect(self._save_error)
        self._writer.idleChanged.connect(self._save_idle_changed)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(2)
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(60)
        self._preview_timer.timeout.connect(self._render_preview)
        self._build_ui()
        self._build_menu()
        translate_widget_tree(self)
        self._restore_library()

    @staticmethod
    def _key(path: str) -> str:
        return os.path.normcase(os.path.abspath(path))

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 14, 18, 8)
        root.setSpacing(14)
        heading = QHBoxLayout()
        brand = QVBoxLayout()
        title = QLabel(PRODUCT_NAME)
        title.setObjectName("brandTitle")
        subtitle = QLabel("CELÝ ZÁBER. KAŽDÝ DETAIL.")
        subtitle.setObjectName("brandAccent")
        brand.addWidget(title)
        brand.addWidget(subtitle)
        heading.addLayout(brand)
        heading.addStretch()
        description = QLabel("Panorámy na carousel. Portréty bez orezania.")
        description.setObjectName("secondaryText")
        heading.addWidget(description)
        root.addLayout(heading)
        self.notice = QLabel()
        self.notice.setObjectName("errorNotice")
        self.notice.setWordWrap(True)
        self.notice.setTextFormat(Qt.TextFormat.PlainText)
        self.notice.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.notice.hide()
        root.addWidget(self.notice)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setObjectName("mainSplitter")
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(4)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 12, 0)
        label = QLabel("Vaše fotografie")
        label.setObjectName("panelHeading")
        left_layout.addWidget(label)
        self.import_button = QPushButton("+  Pridať fotografie")
        self.import_button.setObjectName("importButton")
        self.import_button.clicked.connect(self.choose_import)
        left_layout.addWidget(self.import_button)
        hint = QLabel("JPEG · PNG · HEIC\nSúbory môžete presunúť priamo sem.")
        hint.setObjectName("secondaryText")
        hint.setWordWrap(True)
        left_layout.addWidget(hint)
        self.image_list = ImageList()
        self.image_list.pathsDropped.connect(self.import_paths)
        self.image_list.removeRequested.connect(self.remove_path)
        self.image_list.checkedChanged.connect(self._checked_changed)
        self.image_list.currentItemChanged.connect(self._selection_changed)
        left_layout.addWidget(self.image_list, 1)
        self.remove_checked_button = QPushButton("Odstrániť vybrané")
        self.remove_checked_button.setObjectName("removeCheckedButton")
        self.remove_checked_button.clicked.connect(self.remove_checked)
        self.remove_all_button = QPushButton("Odstrániť všetky")
        self.remove_all_button.setObjectName("removeAllButton")
        self.remove_all_button.clicked.connect(self.remove_all)
        self.export_checked_button = QPushButton("Exportovať vybrané")
        self.export_checked_button.setObjectName("exportCheckedButton")
        self.export_checked_button.clicked.connect(self.choose_export_checked)
        self.export_button = QPushButton("Exportovať všetky")
        self.export_button.setObjectName("exportButton")
        self.export_button.clicked.connect(self.choose_export)
        self.remove_exported_button = QPushButton("Odstrániť exportované")
        self.remove_exported_button.setObjectName("removeExportedButton")
        self.remove_exported_button.clicked.connect(self.remove_exported)
        self.retry_failed_button = QPushButton(tr("Retry failed"))
        self.retry_failed_button.setObjectName("retryFailedButton")
        self.retry_failed_button.clicked.connect(self.retry_failed)
        self.remove_failed_button = QPushButton(tr("Remove failed"))
        self.remove_failed_button.setObjectName("removeFailedButton")
        self.remove_failed_button.clicked.connect(self.remove_failed)
        for button in (self.remove_checked_button, self.remove_all_button,
                       self.export_checked_button, self.export_button, self.remove_exported_button,
                       self.retry_failed_button, self.remove_failed_button):
            left_layout.addWidget(button)
        for button in (self.remove_checked_button, self.remove_all_button, self.remove_exported_button):
            button.setToolTip("Odstráni položky iba z knižnice. Súbory na disku zostanú zachované.")
        self.splitter.addWidget(left)
        middle = QWidget()
        center = QVBoxLayout(middle)
        center.setContentsMargins(10, 0, 10, 0)
        center_heading = QHBoxLayout()
        label = QLabel("Kompozícia")
        label.setObjectName("panelHeading")
        center_heading.addWidget(label)
        center_heading.addStretch()
        label = QLabel("ADAPTIVE PREVIEW")
        label.setObjectName("secondaryText")
        center_heading.addWidget(label)
        center.addLayout(center_heading)
        self.preview = PreviewWidget()
        self.preview.offsetsChanged.connect(self._mouse_offsets)
        self.preview.cropChanged.connect(self._mouse_crop)
        self.preview.cropFinished.connect(self._crop_finished)
        self.preview.colorPicked.connect(self._picked_color)
        self.preview.detailRequested.connect(self._request_detail)
        center.addWidget(self.preview, 1)
        self.splitter.addWidget(middle)
        self.settings = SettingsPanel()
        self.settings.settingsChanged.connect(self._settings_changed)
        self.settings.requestColorPick.connect(self.preview.start_color_pick)
        scroll = QScrollArea()
        scroll.setObjectName("settingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(self.settings)
        scroll.setMinimumWidth(355)
        self.splitter.addWidget(scroll)
        self.splitter.setSizes([305, 590, 365])
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 0)
        root.addWidget(self.splitter, 1)
        footer = QHBoxLayout()
        self.library_count = QLabel()
        self.library_count.setObjectName("libraryCount")
        footer.addWidget(self.library_count)
        self.progress = QProgressBar()
        self.progress.setObjectName("exportProgress")
        self.progress.hide()
        footer.addWidget(self.progress, 1)
        footer.addStretch()
        self.cancel_button = QPushButton("Zrušiť export")
        self.cancel_button.setObjectName("cancelExportButton")
        self.cancel_button.clicked.connect(self.cancel_export)
        self.cancel_button.hide()
        footer.addWidget(self.cancel_button)
        root.addLayout(footer)
        self.setCentralWidget(central)
        self.statusBar().showMessage(tr("Pripravené. Originálne súbory sa nemenia."))
        self._update_count()

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("Súbor")
        self.import_action = QAction("Pridať fotografie…", self)
        self.import_action.setObjectName("importAction")
        self.import_action.setShortcut(QKeySequence.StandardKey.Open)
        self.import_action.triggered.connect(self.choose_import)
        file_menu.addAction(self.import_action)
        self.export_checked_action = QAction("Exportovať vybrané…", self)
        self.export_checked_action.setObjectName("exportCheckedAction")
        self.export_checked_action.triggered.connect(self.choose_export_checked)
        file_menu.addAction(self.export_checked_action)
        self.export_action = QAction("Exportovať všetky…", self)
        self.export_action.setObjectName("exportAction")
        self.export_action.setShortcut("Ctrl+E")
        self.export_action.triggered.connect(self.choose_export)
        file_menu.addAction(self.export_action)
        remove = QAction("Odstrániť označené fotografie", self)
        remove.setShortcut(QKeySequence.StandardKey.Delete)
        remove.triggered.connect(self.remove_checked)
        file_menu.addAction(remove)
        file_menu.addSeparator()
        self.preferences_action = QAction(tr("Preferences…"), self)
        self.preferences_action.setObjectName("preferencesAction")
        self.preferences_action.triggered.connect(self.show_preferences)
        file_menu.addAction(self.preferences_action)
        quit_action = QAction("Ukončiť", self)
        quit_action.setShortcut("Alt+F4")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        help_menu = self.menuBar().addMenu("Pomocník")
        guide = QAction(tr("User guide…"), self)
        guide.setObjectName("helpAction")
        guide.setShortcut(QKeySequence.StandardKey.HelpContents)
        guide.triggered.connect(self.show_help)
        help_menu.addAction(guide)
        about = QAction("O aplikácii", self)
        about.setObjectName("aboutAction")
        about.triggered.connect(self._about)
        help_menu.addAction(about)
        self._update_count()

    def _restore_library(self) -> None:
        selected_row = -1
        for index, record in enumerate(self.session.records):
            self._append_item(record.path)
            if record.path == self.session.selected_path:
                selected_row = index
        if self.session.records:
            paths = [record.path for record in self.session.records]
            self._pending_paths.update(self._key(path) for path in paths)
            self.image_list.setCurrentRow(selected_row)
            self._start_import(paths)
        self._update_count()

    def _append_item(self, path: str) -> QListWidgetItem:
        item = QListWidgetItem(Path(path).name)
        item.setData(Qt.ItemDataRole.UserRole, path)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        record = next(record for record in self.session.records if record.path == path)
        item.setCheckState(Qt.CheckState.Checked if record.checked else Qt.CheckState.Unchecked)
        item.setData(STATUS_ROLE, record.status)
        self._set_item_tooltip(item, record)
        item.setSizeHint(QSize(280, 88))
        had_selection = self.image_list.currentItem() is not None
        blocked = self.image_list.blockSignals(True)
        try:
            self.image_list.addItem(item)
            if not had_selection:
                self.image_list.setCurrentRow(-1)
        finally:
            self.image_list.blockSignals(blocked)
        return item

    def _checked_changed(self, path: str, checked: bool) -> None:
        record = next((record for record in self.session.records if record.path == path), None)
        if record is not None and record.checked != checked:
            record.checked = checked
            self._persist(changed=record)
            self._update_count()

    def _refresh_item_status(self, record: ImageRecord) -> None:
        item = self._item_for_path(record.path)
        if item is not None:
            item.setData(STATUS_ROLE, record.status)
            self._set_item_tooltip(item, record)

    def _set_item_tooltip(self, item: QListWidgetItem, record: ImageRecord) -> None:
        size = self._sizes.get(record.path)
        parts = [record.path]
        if size:
            parts.append(f"{size[0]} × {size[1]} px")
        if record.last_error:
            parts.append(tr(record.last_error))
        item.setToolTip("\n".join(parts))

    def _item_for_path(self, path: str) -> QListWidgetItem | None:
        for index in range(self.image_list.count()):
            item = self.image_list.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == path:
                return item
        return None

    def _record(self) -> ImageRecord | None:
        item = self.image_list.currentItem()
        if item is None:
            return None
        path = item.data(Qt.ItemDataRole.UserRole)
        return next((record for record in self.session.records if record.path == path), None)

    def choose_import(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, tr("Pridať fotografie"), "",
            tr("Fotografie (*.jpg *.jpeg *.png *.heic *.heif);;Všetky súbory (*)"),
        )
        self.import_paths(paths)

    def import_paths(self, paths: list[str]) -> None:
        """Import public API, also used by drag-and-drop and integration checks."""
        known = {self._key(record.path) for record in self.session.records}
        accepted: list[str] = []
        unsupported: list[str] = []
        for path in paths:
            resolved = os.path.abspath(path)
            key = self._key(resolved)
            if key in known or key in self._pending_paths:
                continue
            if Path(path).suffix.lower() not in {".jpg", ".jpeg", ".png", ".heic", ".heif"}:
                unsupported.append(Path(path).name)
                continue
            accepted.append(resolved)
            self._removed_paths.discard(key)
            self._pending_paths.add(key)
        if unsupported:
            self._show_error(tr("Nepodporované súbory: {names}", names=", ".join(unsupported[:8])), "import")
        if accepted:
            self.statusBar().showMessage(tr("Načítavam {count} fotografií…", count=len(accepted)))
            self._start_import(accepted)
            self._update_count()

    def _start_import(self, paths: list[str]) -> None:
        job = ImportJob(paths)
        for path in paths:
            self._import_jobs[self._key(path)] = job
        job.signals.imported.connect(self._imported)
        job.signals.import_failed.connect(self._import_error)
        self._start_job(job)

    def _import_error(self, path: str, message: str) -> None:
        key = self._key(path)
        sender = self.sender()
        job = next((job for job in self._jobs if job.signals is sender), None)
        if (key in self._removed_paths or self._closing
                or isinstance(job, ImportJob) and (
                    job.cancel.is_set() or self._import_jobs.get(key) is not job
                )):
            return
        self._import_errors.append(message)
        record = next((record for record in self.session.records if record.path == path), None)
        if record is None:
            record = ImageRecord(path=path, settings=Settings())
            self.session.records.append(record)
            self._append_item(path)
        record.last_error, record.failure_stage = message, "import"
        self._refresh_item_status(record)
        self._persist(changed=record)
        self._update_count()
        self._show_error(message, "import", path)
        record = self._record()
        if record is not None and record.path not in self._sources:
            self.preview.set_busy(False)

    def _start_job(self, job: Job) -> None:
        self._jobs.add(job)
        job.signals.finished.connect(self._job_finished)
        self._pool.start(job)

    def _job_finished(self, job: Job) -> None:
        self._jobs.discard(job)
        if job is self._preview_job:
            self._preview_job = None
            if self._preview_pending and not self._closing and not self._preview_timer.isActive():
                self._render_preview()
        if job is self._detail_job:
            self._detail_job = None
            if self._detail_pending is not None and not self._closing:
                self._start_detail_pending()
        if isinstance(job, ImportJob):
            for path in job.paths:
                key = self._key(path)
                if self._import_jobs.get(key) is job:
                    self._import_jobs.pop(key)
                    self._pending_paths.discard(key)
            if not self._pending_paths and not self._notices:
                self.statusBar().showMessage(tr("Import dokončený."), 4000)
            self._update_count()
        if job is self._export_job:
            self._export_job = None
            self._export_sources.clear()
            self.progress.hide()
            self.cancel_button.hide()
            self._update_count()
        if self._closing and not self._jobs and self._writer.is_idle:
            QTimer.singleShot(0, self.close)

    def _cache(self, path: str, source: Image.Image) -> None:
        self._sources[path] = source
        self._sources.move_to_end(path)
        while len(self._sources) > 6:
            self._sources.popitem(last=False)

    def _imported(self, path: str, size: tuple[int, int], thumbnail: QImage, source: Image.Image) -> None:
        if self._closing or self._key(path) in self._removed_paths:
            return
        sender = self.sender()
        job = next((job for job in self._jobs if job.signals is sender), None)
        if isinstance(job, ImportJob) and (
            job.cancel.is_set() or self._import_jobs.get(self._key(path)) is not job
        ):
            return
        self._pending_paths.discard(self._key(path))
        record = next((record for record in self.session.records if record.path == path), None)
        if record is None:
            record = ImageRecord(path=path, settings=Settings())
            self.session.records.append(record)
            item = self._append_item(path)
        else:
            item = self._item_for_path(path)
        self._sizes[path] = tuple(size)
        if record.failure_stage in ("import", "preview"):
            record.last_error, record.failure_stage = None, None
        self._clear_notice("import", path)
        self._cache(path, source)
        if item is not None:
            item.setIcon(QIcon(QPixmap.fromImage(thumbnail)))
            self._refresh_item_status(record)
        current = self._record()
        if current is not None and current.path == path:
            self.settings.set_geometry(tuple(size))
            self._set_source_options(source)
            self._queue_preview()
        self._persist(changed=record)
        self._update_count()

    def _selection_changed(self, *_: object) -> None:
        self._crop_origin = None
        self._generation += 1
        self._preview_pending = False
        self._cancel_detail()
        self._preview_timer.stop()
        if self._preview_job is not None:
            self._preview_job.cancel.set()
        self.preview.clear()
        record = self._record()
        for kind, path in list(self._notices):
            if kind == "preview" and (record is None or path != record.path):
                self._clear_notice(kind, path)
        self.session.selected_path = record.path if record is not None else None
        if record is None:
            self.settings.set_record(None)
            self.settings.set_geometry(None)
        else:
            self.settings.set_record(record.settings, Path(record.path).name)
            self.settings.set_geometry(self._sizes.get(record.path))
            self.preview.set_overlay_grid(record.settings.grid)
            self._set_source_options(self._sources.get(record.path))
            self.preview.set_busy()
            if self._key(record.path) not in self._pending_paths:
                self._queue_preview()
        self._persist()

    def _settings_changed(self, settings: Settings) -> None:
        record = self._record()
        if record is None:
            return
        previous_status = record.status
        crop_changed = record.settings.crop_box != settings.crop_box
        changed_export = record.settings.export_dict() != settings.export_dict()
        if changed_export:
            record.exported_settings = None
            if record.failure_stage == "export":
                record.last_error, record.failure_stage = None, None
        record.settings = settings
        self.preview.set_overlay_grid(settings.grid)
        self.preview.set_offsets(settings.offset_x, settings.offset_y)
        size = self._sizes.get(record.path)
        self.settings.set_geometry(size)
        if changed_export and size is not None and not self.preview.is_cropping:
            try:
                self.preview.update_geometry(get_geometry(size, settings), settings)
                if crop_changed:
                    self.preview.reset_view()
            except ValueError:
                # The worker reports invalid composition in the usual error flow.
                pass
        self._persist(changed=record)
        if previous_status != record.status:
            self._refresh_item_status(record)
            self._update_count()
        if changed_export and not self.preview.is_cropping:
            self._queue_preview()

    def _mouse_offsets(self, x: float, y: float) -> None:
        record = self._record()
        if record is not None:
            self.settings.set_offsets(x, y)
            self._settings_changed(replace(record.settings, offset_x=x, offset_y=y))

    def _picked_color(self, color: str) -> None:
        self.settings.set_picked_color(color)

    def _mouse_crop(self, crop_box: tuple[int, int, int, int] | None) -> None:
        """Persist every handle move; the gesture keeps a stable visual frame."""
        record = self._record()
        if record is None:
            return
        if self._crop_origin is None:
            self._crop_origin = (record, replace(
                record, settings=replace(record.settings),
                exported_settings=(record.exported_settings.copy()
                                   if record.exported_settings is not None else None),
            ))
            self._generation += 1
            self._preview_timer.stop()
            self._preview_pending = False
            if self._preview_job is not None:
                self._preview_job.cancel.set()
            self._cancel_detail()
        self.settings.set_crop(crop_box)

    def _crop_finished(self) -> None:
        origin, self._crop_origin = self._crop_origin, None
        record = self._record()
        if origin is None or record is not origin[0] or self._closing:
            return
        _, initial = origin
        same_settings = record.settings.export_dict() == initial.settings.export_dict()
        same_error = (record.last_error, record.failure_stage) == (initial.last_error, initial.failure_stage)
        if same_settings and (record.last_error is None or same_error):
            record.exported_settings = initial.exported_settings
            record.last_error, record.failure_stage = initial.last_error, initial.failure_stage
            self._refresh_item_status(record)
            self._update_count()
            self._persist(changed=record)
        size = self._sizes.get(record.path)
        if size is not None:
            try:
                self.preview.update_geometry(get_geometry(size, record.settings), record.settings)
                self.preview.reset_view()
            except ValueError:
                pass
        self._queue_preview()

    def _set_source_options(self, source: Image.Image | None) -> None:
        self.settings.set_dominant_colors(source.info.get("dominant_colors", []) if source is not None else [])
        self.settings.set_hdr_info(source.info.get("hdr_info", {}) if source is not None else {})

    def _cancel_detail(self) -> None:
        self._detail_generation += 1
        self._detail_pending = None
        if self._detail_job is not None:
            self._detail_job.cancel.set()

    def _request_detail(self, request: dict[str, object]) -> None:
        record = self._record()
        if record is None or self._closing or record.path not in self._sizes:
            return
        # Complete the active viewport instead of starving it during continuous
        # gestures. Its foreground pixels remain reusable at the new placement;
        # only the newest waiting request is retained.
        self._detail_generation += 1
        self._detail_pending = (self._detail_generation, record.path, self._sizes[record.path],
                                replace(record.settings), dict(request))
        if self._detail_job is None:
            self._start_detail_pending()

    def _start_detail_pending(self) -> None:
        if self._detail_pending is None or self._closing:
            return
        job = DetailJob(self._detail_renderer, *self._detail_pending)
        self._detail_pending = None
        self._detail_job = job
        self._jobs.add(job)
        job.signals.finished.connect(self._job_finished)
        job.signals.detail.connect(self._detail_ready)
        job.signals.detail_status.connect(self._detail_status)
        self._detail_pool.start(job)

    def _detail_status(self, generation: int, path: str, state: str, reason: str) -> None:
        record = self._record()
        if (not self._closing and record is not None and record.path == path
                and generation == self._detail_generation):
            # The camera may move between request emission and completion,
            # before the throttle emits its next request. The widget knows
            # whether the accepted pixels still cover this physical viewport.
            if state == "native" and not self.preview._detail_covers_viewport():
                state = "loading"
            self.preview.set_detail_status(state, reason)

    def _detail_ready(self, generation: int, path: str, image: QImage, rect: object) -> None:
        record = self._record()
        if self._closing or record is None or record.path != path:
            return
        job = self._detail_job
        if isinstance(job, DetailJob) and generation == job.generation:
            if job.cancel.is_set() or job.path != path:
                return
            # A completed older viewport is useful while the newest one waits.
            # Attach its original geometry so only its foreground is translated;
            # an obsolete background must never move with the photograph.
            self.preview.set_detail(image, rect, geometry=get_geometry(job.size, job.settings),
                                    settings=job.settings)
        elif generation == self._detail_generation:
            self.preview.set_detail(image, rect)

    def _queue_preview(self) -> None:
        self._generation += 1
        self._preview_pending = True
        if self._preview_job is not None:
            self._preview_job.cancel.set()
        self.preview.set_busy()
        self._preview_timer.start()

    def _render_preview(self) -> None:
        record = self._record()
        if record is None or self._closing:
            self._preview_pending = False
            return
        if self._preview_job is not None:
            return
        self._preview_pending = False
        source = self._sources.get(record.path)
        if source is not None:
            self._sources.move_to_end(record.path)
        job = PreviewJob(self._generation, record.path, replace(record.settings), source,
                         renderer=self._preview_renderer)
        self._preview_job = job
        job.signals.preview.connect(self._preview_ready)
        job.signals.error.connect(self._preview_error)
        self._jobs.add(job)
        job.signals.finished.connect(self._job_finished)
        self._preview_pool.start(job)

    def _preview_error(self, message: str) -> None:
        sender = self.sender()
        if self._preview_job is not None and sender is self._preview_job.signals:
            if not self._preview_job.cancel.is_set():
                self.preview.set_busy(False)
                record = self._record()
                if (record is not None and record.path == self._preview_job.path
                        and record.failure_stage != "export"):
                    record.last_error, record.failure_stage = message, "preview"
                    self._refresh_item_status(record)
                    self._persist(changed=record)
                    self._update_count()
                self._show_error(message, "preview", self._preview_job.path)

    def _preview_ready(self, generation: int, path: str, image: QImage, source: Image.Image,
                       background: QImage | None = None) -> None:
        record = self._record()
        if (self._closing or self.preview.is_cropping or generation != self._generation
                or record is None or record.path != path):
            return
        self._cache(path, source)
        size = tuple(source.info.get("source_size", source.size))
        self._sizes[path] = size
        geometry = get_geometry(size, record.settings)
        source_image = to_qimage(source) if self.preview._source_pixmap is None else None
        self.preview.set_image(image, geometry.count, geometry.ratio, source_image, geometry,
                               settings=record.settings, background=background)
        self.preview.set_offsets(record.settings.offset_x, record.settings.offset_y)
        self.preview.set_overlay_grid(record.settings.grid)
        self._set_source_options(source)
        changed = not record.previewed
        if record.failure_stage in ("preview", "import"):
            record.last_error, record.failure_stage = None, None
            changed = True
        if changed:
            record.previewed = True
            self._refresh_item_status(record)
            self._persist(changed=record)
            self._update_count()
        self.settings.set_geometry(size)
        self._clear_notice("preview", path)

    def remove_path(self, path: str) -> None:
        self._remove_paths({path})

    def remove_checked(self) -> None:
        self._remove_paths({record.path for record in self.session.records if record.checked})

    def remove_exported(self) -> None:
        self._remove_paths({record.path for record in self.session.records if record.is_exported})

    def remove_failed(self) -> None:
        self._remove_paths({record.path for record in self.session.records if record.status == "failed"})

    def retry_failed(self) -> None:
        if self._export_job is not None:
            return
        imports = [record.path for record in self.session.records
                   if record.status == "failed" and record.failure_stage != "export"
                   and self._key(record.path) not in self._pending_paths]
        if imports:
            self._pending_paths.update(self._key(path) for path in imports)
            self._start_import(imports)
        self.start_export(self.preferences.export_dir, failed_only=True)
        self._update_count()

    def remove_all(self) -> None:
        for job in self._jobs:
            if isinstance(job, ImportJob):
                job.cancel.set()
        self._removed_paths.update(self._pending_paths)
        self._pending_paths.clear()
        self._import_jobs.clear()
        self._remove_paths({record.path for record in self.session.records}, force_refresh=True)

    def _remove_paths(self, paths: set[str], *, force_refresh: bool = False) -> None:
        if not paths and not force_refresh:
            return
        current_path = self.session.selected_path
        self.session.records[:] = [record for record in self.session.records if record.path not in paths]
        blocked = self.image_list.blockSignals(True)
        try:
            for path in paths:
                key = self._key(path)
                self._removed_paths.add(key)
                self._import_jobs.pop(key, None)
                self._pending_paths.discard(key)
                self._sources.pop(path, None)
                self._sizes.pop(path, None)
                self._clear_notice("import", path)
                self._clear_notice("preview", path)
            for row in range(self.image_list.count() - 1, -1, -1):
                if self.image_list.item(row).data(Qt.ItemDataRole.UserRole) in paths:
                    self.image_list.takeItem(row)
            selected = self._item_for_path(current_path) if current_path is not None else None
            if selected is not None:
                self.image_list.setCurrentItem(selected)
            else:
                self.image_list.setCurrentRow(-1)
        finally:
            self.image_list.blockSignals(blocked)
        self._selection_changed()
        self._update_count()

    def _persist(self, changed: ImageRecord | None = None) -> None:
        if self._closing:
            return
        try:
            self._writer.submit(self.session, changed=changed)
        except Exception as error:
            self._save_error(0, str(error))

    def _saved(self, revision: int) -> None:
        if self._last_save_error:
            self._last_save_error = ""
            self._clear_notice("save")
            self.statusBar().showMessage(tr("Automatické ukladanie opäť funguje."), 5000)

    def _save_error(self, revision: int, error: str) -> None:
        resume_preview = self._closing
        if self._closing:
            # Keep an unsaved session visible instead of silently closing after
            # a final disk error. The user can correct the destination/problem.
            self._closing = False
            self.setEnabled(True)
        message = tr("Nastavenia sa nepodarilo uložiť. Zmeny sú iba v pamäti. {error}", error=tr(error))
        if message != self._last_save_error:
            self._show_error(message, "save")
            self._last_save_error = message
        if resume_preview and self._record() is not None:
            self._queue_preview()

    def _save_idle_changed(self, idle: bool) -> None:
        if idle and self._closing and not self._jobs:
            QTimer.singleShot(0, self.close)

    def _show_error(self, message: str, kind: str = "general", context: str | None = None) -> None:
        self._show_notice(message, kind, context, error=True)

    def _show_notice(
        self, message: str, kind: str, context: str | None = None, error: bool = False
    ) -> None:
        if self._closing:
            return
        key = (kind, context)
        self._notices[key] = (message, error)
        self._notices.move_to_end(key)
        self._refresh_notice()

    def _clear_notice(self, kind: str, context: str | None = None) -> None:
        if self._notices.pop((kind, context), None) is not None:
            self._refresh_notice()

    def _refresh_notice(self) -> None:
        if not self._notices:
            self.notice.clear()
            self.notice.hide()
            self.statusBar().showMessage(tr("Náhľad je aktuálny."), 3000)
            return
        message, error = next(reversed(self._notices.values()))
        self.notice.setText(tr(message))
        dark = QApplication.instance().property("theme_dark") is not False
        background, color = (("#442b2b", "#ffd2c9") if dark else ("#fde7e9", "#8c1f32")) if error else (
            ("#203b35", "#bceee0") if dark else ("#d4eee3", "#164b3f")
        )
        self.notice.setStyleSheet(
            f"background: {background}; color: {color}; padding: 10px; border-radius: 6px;"
        )
        self.notice.show()
        self.statusBar().showMessage(tr(message))

    def _update_count(self) -> None:
        count = len(self.session.records)
        checked = sum(record.checked for record in self.session.records)
        statuses = [record.status for record in self.session.records]
        exported = statuses.count("exported")
        imported = statuses.count("imported")
        failed = statuses.count("failed")
        prepared = count - imported - exported - failed
        self.library_count.setText(
            tr("Photos: {count}  ·  checked: {checked}  ·  imported: {imported}  ·  ready: {prepared}  ·  exported: {exported}  ·  failed: {failed}",
               count=count, checked=checked, imported=imported, prepared=prepared, exported=exported, failed=failed)
        )
        available = any(status in ("staging", "exported") for status in statuses) and self._export_job is None
        checked_available = any(record.checked and status in ("staging", "exported")
                                for record, status in zip(self.session.records, statuses)) and self._export_job is None
        self.export_button.setEnabled(available)
        self.export_checked_button.setEnabled(checked_available)
        self.export_button.setToolTip(
            tr("Exportuje všetky pripravené a už exportované fotografie. Importované preskočí.")
        )
        self.export_checked_button.setToolTip(
            tr("Exportuje označené pripravené a už exportované fotografie. Importované preskočí.")
        )
        if hasattr(self, "export_action"):
            self.export_action.setEnabled(available)
        if hasattr(self, "export_checked_action"):
            self.export_checked_action.setEnabled(checked_available)
        self.remove_checked_button.setEnabled(checked > 0)
        self.remove_all_button.setEnabled(count > 0 or bool(self._pending_paths))
        self.remove_exported_button.setEnabled(exported > 0)
        self.retry_failed_button.setEnabled(failed > 0 and self._export_job is None)
        self.remove_failed_button.setEnabled(failed > 0)

    def choose_export(self) -> None:
        self._choose_export(checked_only=False)

    def choose_export_checked(self) -> None:
        self._choose_export(checked_only=True)

    def _export_candidates(self, *, checked_only: bool = False) -> list[ImageRecord]:
        """Use the same readiness rule for buttons, menus, dialogs and jobs."""
        return [
            record for record in self.session.records
            if record.status in ("staging", "exported") and (not checked_only or record.checked)
        ]

    def _choose_export(self, *, checked_only: bool) -> None:
        records = self._export_candidates(checked_only=checked_only)
        if not records or self._export_job is not None:
            return
        self.start_export(self.preferences.export_dir, checked_only=checked_only)

    def start_export(self, directory: str, *, checked_only: bool = False, failed_only: bool = False) -> None:
        """Export a snapshot; edits made during the batch apply to the next export."""
        sources = ([record for record in self.session.records
                    if record.status == "failed" and record.failure_stage == "export"]
                   if failed_only else self._export_candidates(checked_only=checked_only))
        if not sources or self._export_job is not None:
            return
        if not Path(directory).is_dir():
            self._show_error(tr("Export folder does not exist: {directory}. Choose another folder in Preferences.", directory=directory), "export")
            return
        self.session.export_dir = directory
        self._persist()
        records = [ImageRecord(path=record.path, settings=replace(record.settings)) for record in sources]
        self._export_sources = {record.path: record for record in sources}
        job = ExportJob(records, directory)
        self._export_job = job
        job.signals.progress.connect(self._export_progress)
        job.signals.exported.connect(self._export_complete)
        job.signals.error.connect(self._export_error)
        self.progress.setRange(0, len(records))
        self.progress.setValue(0)
        self.progress.show()
        self.cancel_button.setEnabled(True)
        self.cancel_button.show()
        self.statusBar().showMessage(tr("Exportujem fotografie z originálov…"))
        self._update_count()
        self._start_job(job)

    def cancel_export(self) -> None:
        if self._export_job is not None:
            self._export_job.cancel.set()
            self.cancel_button.setEnabled(False)
            self.statusBar().showMessage(tr("Dokončujem aktuálny diel a ruším export…"))

    def _export_error(self, message: str) -> None:
        self._show_error(message, "export")

    def _export_progress(self, done: int, total: int, message: str) -> None:
        self.progress.setRange(0, max(1, total))
        self.progress.setValue(done)
        self.statusBar().showMessage(message)

    def _export_complete(self, report: ExportReport) -> None:
        if self._closing:
            return
        for record in self.session.records:
            snapshot = report.completed.get(record.path)
            if (snapshot is not None and self._export_sources.get(record.path) is record
                    and record.settings.export_dict() == Settings.from_dict(snapshot).export_dict()):
                record.exported_settings = snapshot.copy()
                record.last_error, record.failure_stage = None, None
                self._refresh_item_status(record)
            elif record.path in report.failed and self._export_sources.get(record.path) is record:
                source = next((item for item in self._export_job.records if item.path == record.path), None) if self._export_job else None
                if source is not None and record.settings.export_dict() == source.settings.export_dict():
                    record.last_error = report.failed[record.path]
                    record.failure_stage = "export"
                    record.exported_settings = None
                    self._refresh_item_status(record)
        self._persist()
        self._update_count()
        prefix = tr("Export cancelled" if report.cancelled else "Export completed")
        message = tr("{prefix}. Output images: {count}.", prefix=prefix, count=len(report.paths))
        self.statusBar().showMessage(message)
        if report.errors:
            self._show_error(message + "\n" + "\n".join(tr(error) for error in report.errors[:8]), "export")
        else:
            self._clear_notice("export")
            self._show_notice(message + f"\n{self.session.export_dir}", "export_info")
        if self._summary_dialog is not None:
            self._summary_dialog.close()
        self._summary_dialog = ExportSummaryDialog(report, self.session.export_dir, self)
        self._summary_dialog.open()

    def _theme_changed(self, dark: bool) -> None:
        self.setStyleSheet(stylesheet(dark))
        self.image_list.viewport().update()
        self.preview.update()
        self._refresh_notice()

    def show_preferences(self) -> None:
        dialog = PreferencesDialog(self.preferences, self)
        if dialog.exec() != dialog.DialogCode.Accepted or dialog.result_preferences is None:
            return
        preferences = dialog.result_preferences
        try:
            self.preferences_store.save(preferences)
        except PreferencesError as error:
            self._show_error(tr(str(error)), "preferences")
            return
        self.preferences = preferences
        set_language(preferences.language)
        if self.theme_manager is not None:
            self.theme_manager.set_theme(preferences.theme)
        translate_widget_tree(self)
        self.settings.retranslate_ui()
        self.preview.retranslate_ui()
        self.image_list.retranslate_ui()
        for record in self.session.records:
            self._refresh_item_status(record)
        self._update_count()
        self._clear_notice("preferences")
        self._refresh_notice()

    def show_help(self) -> None:
        self._help_dialog = HelpDialog(self.preferences.language, self)
        self._help_dialog.open()

    def _about(self) -> None:
        QMessageBox.about(
            self, tr("O aplikácii"), "<h3>" + PRODUCT_NAME + "</h3><p>" +
            tr("Panoramas for carousels. Portraits without cropping.") + "</p><p>" +
            tr("Local processing. Originals remain unchanged.") + "</p><p>" +
            "PySide6 · Pillow · pillow-heif · NumPy · imagecodecs</p>",
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.preview.is_cropping:
            self.preview._finish_crop()
        self.preview._detail_timer.stop()
        self._preview_timer.stop()
        self._preview_pending = False
        self._detail_pending = None
        if self._jobs or not self._writer.is_idle:
            self._closing = True
            for job in self._jobs:
                job.cancel.set()
            self.setEnabled(False)
            self.statusBar().showMessage(tr("Ukončujem spracovanie…"))
            event.ignore()
            return
        self._closing = True
        self._preview_renderer.close()
        self._detail_renderer.close()
        event.accept()
