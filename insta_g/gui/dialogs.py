"""Export result details, presented without blocking worker signal delivery."""

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from insta_g.core.export import ExportReport
from insta_g.i18n import tr


class ExportSummaryDialog(QDialog):
    def __init__(self, report: ExportReport, directory: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("exportSummaryDialog")
        self.setWindowTitle(tr("Export cancelled" if report.cancelled else "Export completed"))
        self.setMinimumWidth(460)
        self.directory = directory
        layout = QVBoxLayout(self)
        form = QFormLayout()
        for label, value, name in (
            ("Originals processed", report.processed_count, "summaryProcessed"),
            ("Output images created", len(report.paths), "summaryOutputs"),
            ("Failed originals", len(report.failed), "summaryFailed"),
        ):
            field = QLabel(str(value))
            field.setObjectName(name)
            form.addRow(tr(label), field)
        layout.addLayout(form)
        folder = QLabel(directory)
        folder.setWordWrap(True)
        layout.addWidget(folder)
        if report.errors:
            errors = QPlainTextEdit("\n".join(tr(error) for error in report.errors))
            errors.setObjectName("summaryErrors")
            errors.setReadOnly(True)
            errors.setMinimumHeight(150)
            layout.addWidget(errors)
        buttons = QDialogButtonBox()
        self.ok_button = buttons.addButton(tr("OK"), QDialogButtonBox.ButtonRole.AcceptRole)
        self.ok_button.setObjectName("summaryOkButton")
        self.ok_button.setDefault(True)
        self.open_button = buttons.addButton(tr("Open export folder"), QDialogButtonBox.ButtonRole.ActionRole)
        self.open_button.setObjectName("summaryOpenFolderButton")
        self.open_button.setEnabled(Path(directory).is_dir())
        self.open_button.clicked.connect(self.open_folder)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def open_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.directory))
