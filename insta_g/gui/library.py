"""Painted photo-library rows with independent export checks and status colours."""

from __future__ import annotations

from PySide6.QtCore import (
    QAbstractItemModel,
    QEvent,
    QModelIndex,
    QPersistentModelIndex,
    QPoint,
    QRect,
    QRectF,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QHelpEvent,
    QIcon,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QListWidget,
    QListWidgetItem,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionButton,
    QStyleOptionViewItem,
    QToolTip,
    QWidget,
)

from insta_g.i18n import tr

PATH_ROLE = int(Qt.ItemDataRole.UserRole)
STATUS_ROLE = PATH_ROLE + 1

IMPORTED_BACKGROUND = QColor("#24334a")
IMPORTED_HOVER_BACKGROUND = QColor("#3c5f85")
STAGING_BACKGROUND = QColor("#39301b")
STAGING_HOVER_BACKGROUND = QColor("#65552b")
EXPORTED_BACKGROUND = QColor("#1c382c")
EXPORTED_HOVER_BACKGROUND = QColor("#33694c")
FAILED_BACKGROUND = QColor("#4a242b")
FAILED_HOVER_BACKGROUND = QColor("#783946")
IMPORTED_ACCENT = QColor("#a7c9f2")
STAGING_ACCENT = QColor("#e7c66c")
EXPORTED_ACCENT = QColor("#7bdaa7")
FAILED_ACCENT = QColor("#ff9ca6")
TRASH_COLOR = QColor("#ff767d")

_DARK_COLORS = {
    "imported": (IMPORTED_BACKGROUND, IMPORTED_HOVER_BACKGROUND, IMPORTED_ACCENT),
    "staging": (STAGING_BACKGROUND, STAGING_HOVER_BACKGROUND, STAGING_ACCENT),
    "exported": (EXPORTED_BACKGROUND, EXPORTED_HOVER_BACKGROUND, EXPORTED_ACCENT),
    "failed": (FAILED_BACKGROUND, FAILED_HOVER_BACKGROUND, FAILED_ACCENT),
}
_LIGHT_COLORS = {
    "imported": (QColor("#e5effc"), QColor("#c1d8f3"), QColor("#234f83")),
    "staging": (QColor("#fff3cc"), QColor("#f6df93"), QColor("#705716")),
    "exported": (QColor("#dff2e7"), QColor("#b3dfc6"), QColor("#236443")),
    "failed": (QColor("#fce3e5"), QColor("#f4b8bf"), QColor("#9d2733")),
}
_STATUS_LABELS = {"imported": "Imported", "staging": "Ready", "exported": "Exported",
                  "failed": "Failed"}


def status_colors(status: str, dark: bool, hovered: bool = False) -> tuple[QColor, QColor]:
    """State colours survive selection and have a visible theme-specific hover."""
    colors = _DARK_COLORS if dark else _LIGHT_COLORS
    background, hover, accent = colors.get(status, colors["imported"])
    return (hover if hovered else background), accent


class ImageItemDelegate(QStyledItemDelegate):
    """Draw rows without creating a widget for every imported photograph."""

    removeRequested = Signal(str)
    ROW_HEIGHT = 88

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pressed: tuple[QPersistentModelIndex, str] | None = None

    @staticmethod
    def checkbox_rect(rect: QRect) -> QRect:
        return QRect(rect.left() + 10, rect.center().y() - 10, 20, 20)

    @staticmethod
    def trash_rect(rect: QRect) -> QRect:
        return QRect(rect.right() - 36, rect.center().y() - 17, 30, 34)

    @staticmethod
    def thumbnail_rect(rect: QRect) -> QRect:
        return QRect(rect.left() + 40, rect.top() + 10, 72, rect.height() - 20)

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        return QSize(280, self.ROW_HEIGHT)

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex,
    ) -> None:
        item_option = QStyleOptionViewItem(option)
        self.initStyleOption(item_option, index)
        status = index.data(STATUS_ROLE)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        application = QApplication.instance()
        dark_setting = application.property("theme_dark") if application is not None else None
        dark = True if dark_setting is None else bool(dark_setting)
        background, accent = status_colors(status, dark, hovered)
        status_text = tr(_STATUS_LABELS.get(status, "Imported"))
        painter.save()
        painter.setClipRect(option.rect)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(accent if selected or hovered else background.lighter(125),
                            2 if selected or hovered else 1))
        painter.setBrush(background)
        painter.drawRoundedRect(QRectF(option.rect.adjusted(1, 1, -2, -2)), 7, 7)

        checkbox = QStyleOptionButton()
        checkbox.rect = self.checkbox_rect(option.rect)
        checkbox.state = QStyle.StateFlag.State_Enabled if (
            index.flags() & Qt.ItemFlag.ItemIsEnabled
            and option.state & QStyle.StateFlag.State_Enabled
        ) else QStyle.StateFlag.State_None
        checked = index.data(Qt.ItemDataRole.CheckStateRole) in (
            Qt.CheckState.Checked, Qt.CheckState.Checked.value,
        )
        checkbox.state |= QStyle.StateFlag.State_On if checked else QStyle.StateFlag.State_Off
        style = option.widget.style() if option.widget else QApplication.style()
        style.drawPrimitive(QStyle.PrimitiveElement.PE_IndicatorCheckBox,
                            checkbox, painter, option.widget)

        thumbnail = self.thumbnail_rect(option.rect)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#131c24" if dark else "#f7f9fc"))
        painter.drawRoundedRect(thumbnail, 4, 4)
        icon = item_option.icon
        if not icon.isNull():
            icon.paint(painter, thumbnail.adjusted(1, 1, -1, -1),
                       Qt.AlignmentFlag.AlignCenter, QIcon.Mode.Normal, QIcon.State.Off)

        text_left = thumbnail.right() + 11
        text_width = max(0, self.trash_rect(option.rect).left() - text_left - 6)
        filename_rect = QRect(text_left, option.rect.top() + 21, text_width, 25)
        painter.setFont(item_option.font)
        painter.setPen(QColor("#f2f3f6" if dark else "#172432"))
        filename = str(index.data(Qt.ItemDataRole.DisplayRole) or "").split("\n", 1)[0]
        painter.drawText(filename_rect, Qt.AlignmentFlag.AlignVCenter,
                         painter.fontMetrics().elidedText(
                             filename, Qt.TextElideMode.ElideMiddle, text_width))
        status_font = painter.font()
        status_font.setPointSizeF(max(8.0, status_font.pointSizeF() - 1.0))
        painter.setFont(status_font)
        painter.setPen(accent)
        painter.drawText(QRect(text_left, option.rect.top() + 47, text_width, 20),
                         Qt.AlignmentFlag.AlignVCenter,
                         painter.fontMetrics().elidedText(
                             status_text, Qt.TextElideMode.ElideRight, text_width))
        self._paint_trash(painter, self.trash_rect(option.rect), dark)
        painter.restore()

    @staticmethod
    def _paint_trash(painter: QPainter, rect: QRect, dark: bool = True) -> None:
        painter.save()
        painter.translate(rect.center().x() - 12, rect.center().y() - 13)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(TRASH_COLOR if dark else QColor("#c52e42"), 1.8, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        body = QPainterPath()
        body.moveTo(5, 8)
        body.lineTo(6, 23)
        body.lineTo(18, 23)
        body.lineTo(19, 8)
        painter.drawPath(body)
        painter.drawLine(3, 7, 21, 7)
        painter.drawLine(9, 3, 15, 3)
        painter.drawLine(9, 3, 8, 7)
        painter.drawLine(15, 3, 16, 7)
        painter.drawLine(10, 11, 10, 19)
        painter.drawLine(14, 11, 14, 19)
        painter.restore()

    def action_at(self, rect: QRect, index: QModelIndex, point: QPoint) -> str | None:
        if not index.isValid() or not index.flags() & Qt.ItemFlag.ItemIsEnabled:
            return None
        if self.trash_rect(rect).contains(point) and index.data(PATH_ROLE):
            return "trash"
        if self.checkbox_rect(rect).contains(point) and (
            index.flags() & Qt.ItemFlag.ItemIsUserCheckable
        ):
            return "check"
        return None

    @staticmethod
    def _toggle_check(model: QAbstractItemModel, index: QModelIndex) -> bool:
        checked = index.data(Qt.ItemDataRole.CheckStateRole) in (
            Qt.CheckState.Checked, Qt.CheckState.Checked.value,
        )
        state = Qt.CheckState.Unchecked if checked else Qt.CheckState.Checked
        return model.setData(index, state.value, Qt.ItemDataRole.CheckStateRole)

    def editorEvent(
        self, event: QEvent, model: QAbstractItemModel,
        option: QStyleOptionViewItem, index: QModelIndex,
    ) -> bool:
        if isinstance(event, QKeyEvent) and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Select) and (
                index.flags() & Qt.ItemFlag.ItemIsEnabled
                and index.flags() & Qt.ItemFlag.ItemIsUserCheckable
            ):
                return self._toggle_check(model, index)
        if isinstance(event, QMouseEvent) and event.button() == Qt.MouseButton.LeftButton:
            action = self.action_at(option.rect, index, event.position().toPoint())
            if event.type() == QEvent.Type.MouseButtonPress:
                self._pressed = (QPersistentModelIndex(index), action) if action else None
                return action is not None
            if event.type() == QEvent.Type.MouseButtonDblClick:
                self._pressed = None
                return action is not None
            if event.type() == QEvent.Type.MouseButtonRelease:
                pressed = self._pressed
                self._pressed = None
                if pressed is not None and pressed == (QPersistentModelIndex(index), action):
                    if action == "trash":
                        self.removeRequested.emit(str(index.data(PATH_ROLE)))
                    elif action == "check":
                        self._toggle_check(model, index)
                    return True
                return action is not None
        return super().editorEvent(event, model, option, index)

    def helpEvent(
        self, event: QHelpEvent, view: QAbstractItemView,
        option: QStyleOptionViewItem, index: QModelIndex,
    ) -> bool:
        action = self.action_at(option.rect, index, event.pos())
        if action:
            text = tr("Remove photo from library" if action == "trash" else "Select for export")
            QToolTip.showText(event.globalPos(), text, view.viewport())
            return True
        return super().helpEvent(event, view, option, index)


class ImageList(QListWidget):
    pathsDropped = Signal(list)
    removeRequested = Signal(str)
    checkedChanged = Signal(str, bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("imageList")
        self.setAcceptDrops(True)
        self.setIconSize(QSize(88, 72))
        self.setSpacing(4)
        self.setUniformItemSizes(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setMinimumWidth(280)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.retranslate_ui()
        self.delegate = ImageItemDelegate(self)
        self.setItemDelegate(self.delegate)
        self.delegate.removeRequested.connect(self.removeRequested)
        self._interactive_press = False
        self._check_states: dict[int, tuple[QListWidgetItem, Qt.CheckState]] = {}
        self.model().rowsInserted.connect(self._remember_rows)
        self.model().rowsAboutToBeRemoved.connect(self._forget_rows)
        self.model().modelReset.connect(self._check_states.clear)
        self.model().dataChanged.connect(self._data_changed)

    def retranslate_ui(self) -> None:
        self.setToolTip(tr("Drop JPEG, PNG or HEIC photos here."))
        self.viewport().update()

    def _remember_rows(self, parent: QModelIndex, first: int, last: int) -> None:
        for row in range(first, last + 1):
            item = self.item(row)
            self._check_states[id(item)] = (item, item.checkState())

    def _forget_rows(self, parent: QModelIndex, first: int, last: int) -> None:
        for row in range(first, last + 1):
            self._check_states.pop(id(self.item(row)), None)

    def _data_changed(
        self, first: QModelIndex, last: QModelIndex, roles: list[int],
    ) -> None:
        # itemChanged also fires for thumbnails, labels and export-status updates.
        # Use the model's role information so only a real checkbox change is relayed.
        if roles and Qt.ItemDataRole.CheckStateRole not in roles:
            return
        for row in range(first.row(), last.row() + 1):
            item = self.item(row)
            previous = self._check_states.get(id(item), (item, Qt.CheckState.Unchecked))[1]
            current = item.checkState()
            self._check_states[id(item)] = (item, current)
            path = item.data(PATH_ROLE)
            if previous != current and path:
                self.checkedChanged.emit(str(path), current == Qt.CheckState.Checked)

    def _event_option(self, index: QModelIndex) -> QStyleOptionViewItem:
        option = QStyleOptionViewItem()
        self.initViewItemOption(option)
        option.rect = self.visualRect(index)
        option.widget = self.viewport()
        return option

    def mousePressEvent(self, event: QMouseEvent) -> None:
        index = self.indexAt(event.position().toPoint())
        option = self._event_option(index)
        if event.button() == Qt.MouseButton.LeftButton and self.delegate.action_at(
            option.rect, index, event.position().toPoint(),
        ):
            self._interactive_press = True
            self.delegate.editorEvent(event, self.model(), option, index)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._interactive_press and event.button() == Qt.MouseButton.LeftButton:
            self._interactive_press = False
            index = self.indexAt(event.position().toPoint())
            self.delegate.editorEvent(event, self.model(), self._event_option(index), index)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        index = self.indexAt(event.position().toPoint())
        option = self._event_option(index)
        if event.button() == Qt.MouseButton.LeftButton and self.delegate.action_at(
            option.rect, index, event.position().toPoint(),
        ):
            self._interactive_press = True
            self.delegate.editorEvent(event, self.model(), option, index)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self.pathsDropped.emit(paths)
            event.acceptProposedAction()
        else:
            event.ignore()
