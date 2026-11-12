"""Library interaction and painting checks use items without personal photographs."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QEvent, QMimeData, QPoint, QPointF, QRect, Qt, QUrl
from PySide6.QtGui import (
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QHoverEvent,
    QIcon,
    QImage,
    QPainter,
    QPixmap,
)
from PySide6.QtWidgets import QApplication, QListWidgetItem, QStyle, QStyleOptionViewItem

from insta_g.gui.library import (
    EXPORTED_BACKGROUND,
    EXPORTED_HOVER_BACKGROUND,
    FAILED_BACKGROUND,
    FAILED_HOVER_BACKGROUND,
    IMPORTED_BACKGROUND,
    IMPORTED_HOVER_BACKGROUND,
    PATH_ROLE,
    STAGING_BACKGROUND,
    STAGING_HOVER_BACKGROUND,
    STATUS_ROLE,
    ImageList,
    status_colors,
)
from insta_g.i18n import get_language, set_language, tr


@pytest.fixture
def image_list(qtbot):
    application = QApplication.instance()
    previous_dark = application.property("theme_dark")
    application.setProperty("theme_dark", True)
    view = ImageList()
    for number in range(2):
        item = QListWidgetItem(f"Fotografia {number}.jpg")
        item.setData(PATH_ROLE, f"C:/generated/photo-{number}.jpg")
        item.setData(STATUS_ROLE, "staging")
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Unchecked)
        view.addItem(item)
    view.resize(380, 260)
    qtbot.addWidget(view)
    view.show()
    view.setCurrentRow(0)
    yield view
    application.setProperty("theme_dark", previous_dark)


def test_checkbox_mouse_and_keyboard_are_independent_of_current_photo(image_list, qtbot):
    changes = []
    image_list.checkedChanged.connect(lambda path, checked: changes.append((path, checked)))
    second = image_list.item(1)
    checkbox = image_list.delegate.checkbox_rect(image_list.visualItemRect(second))
    qtbot.mouseClick(image_list.viewport(), Qt.MouseButton.LeftButton, pos=checkbox.center())
    assert image_list.currentRow() == 0
    assert second.checkState() == Qt.CheckState.Checked
    assert changes == [(second.data(PATH_ROLE), True)]

    # Normal row clicks change the preview selection without changing the check.
    row = image_list.visualItemRect(second)
    qtbot.mouseClick(image_list.viewport(), Qt.MouseButton.LeftButton,
                     pos=QPoint(row.left() + 140, row.center().y()))
    assert image_list.currentRow() == 1
    assert second.checkState() == Qt.CheckState.Checked
    qtbot.keyClick(image_list, Qt.Key.Key_Space)
    assert second.checkState() == Qt.CheckState.Unchecked
    assert changes == [(second.data(PATH_ROLE), True), (second.data(PATH_ROLE), False)]
    assert all(image_list.itemWidget(image_list.item(row)) is None for row in range(2))


def test_dragging_off_checkbox_does_not_toggle_or_select(image_list, qtbot):
    second = image_list.item(1)
    rect = image_list.visualItemRect(second)
    checkbox = image_list.delegate.checkbox_rect(rect)
    qtbot.mousePress(image_list.viewport(), Qt.MouseButton.LeftButton, pos=checkbox.center())
    qtbot.mouseRelease(image_list.viewport(), Qt.MouseButton.LeftButton,
                       pos=QPoint(rect.left() + 145, rect.center().y()))
    assert image_list.currentRow() == 0
    assert second.checkState() == Qt.CheckState.Unchecked


def test_trash_emits_once_without_selecting_or_checking_photo(image_list, qtbot):
    removals = []
    changes = []
    image_list.removeRequested.connect(removals.append)
    image_list.checkedChanged.connect(lambda *args: changes.append(args))
    second = image_list.item(1)
    trash = image_list.delegate.trash_rect(image_list.visualItemRect(second))
    qtbot.mousePress(image_list.viewport(), Qt.MouseButton.LeftButton, pos=trash.center())
    assert removals == []
    qtbot.mouseRelease(image_list.viewport(), Qt.MouseButton.LeftButton, pos=trash.center())
    assert removals == [second.data(PATH_ROLE)]
    assert image_list.currentRow() == 0
    assert second.checkState() == Qt.CheckState.Unchecked
    assert changes == []
    qtbot.mouseDClick(image_list.viewport(), Qt.MouseButton.LeftButton, pos=trash.center())
    qtbot.mouseRelease(image_list.viewport(), Qt.MouseButton.LeftButton, pos=trash.center())
    assert removals == [second.data(PATH_ROLE)]


def test_only_real_check_changes_emit_including_blocked_programmatic_updates(image_list):
    changes = []
    image_list.checkedChanged.connect(lambda *args: changes.append(args))
    item = image_list.item(0)
    pixmap = QPixmap(20, 20)
    pixmap.fill(Qt.GlobalColor.red)
    item.setIcon(QIcon(pixmap))
    item.setData(STATUS_ROLE, "exported")
    item.setText("Nový názov.jpg")
    assert changes == []
    item.setCheckState(Qt.CheckState.Checked)
    item.setCheckState(Qt.CheckState.Checked)
    item.setData(STATUS_ROLE, "staging")
    assert changes == [(item.data(PATH_ROLE), True)]
    blocked = image_list.blockSignals(True)
    item.setCheckState(Qt.CheckState.Unchecked)
    image_list.blockSignals(blocked)
    item.setData(STATUS_ROLE, "exported")
    assert len(changes) == 1
    item.setCheckState(Qt.CheckState.Checked)
    assert changes[-1] == (item.data(PATH_ROLE), True)
    assert len(changes) == 2


@pytest.mark.parametrize("status,background,hover_background,label", [
    ("imported", IMPORTED_BACKGROUND, IMPORTED_HOVER_BACKGROUND, "Imported"),
    ("staging", STAGING_BACKGROUND, STAGING_HOVER_BACKGROUND, "Ready"),
    ("exported", EXPORTED_BACKGROUND, EXPORTED_HOVER_BACKGROUND, "Exported"),
    ("failed", FAILED_BACKGROUND, FAILED_HOVER_BACKGROUND, "Failed"),
])
@pytest.mark.parametrize("hovered", [False, True])
@pytest.mark.parametrize("selected", [False, True])
def test_status_background_is_preserved_for_hover_and_selection(
    image_list, monkeypatch, status, background, hover_background, label, hovered, selected,
):
    item = image_list.item(0)
    item.setData(STATUS_ROLE, status)
    painted_text = []
    draw_text = QPainter.drawText

    def record_text(painter, rect, alignment, text):
        painted_text.append(text)
        return draw_text(painter, rect, alignment, text)

    monkeypatch.setattr(QPainter, "drawText", record_text)
    image = QImage(360, 88, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.magenta)
    option = QStyleOptionViewItem()
    option.initFrom(image_list)
    option.rect = QRect(0, 0, 360, 88)
    option.widget = image_list
    option.state = QStyle.StateFlag.State_Enabled
    if hovered:
        option.state |= QStyle.StateFlag.State_MouseOver
    if selected:
        option.state |= QStyle.StateFlag.State_Selected
    painter = QPainter(image)
    image_list.delegate.paint(painter, option, image_list.indexFromItem(item))
    painter.end()
    expected = hover_background if hovered else background
    assert image.pixelColor(150, 76) == expected
    assert painted_text == ["Fotografia 0.jpg", tr(label)]


@pytest.mark.parametrize("status", [None, "unknown"])
def test_unset_or_unknown_status_is_painted_as_imported(image_list, monkeypatch, status):
    item = image_list.item(0)
    item.setData(STATUS_ROLE, status)
    painted_text = []
    draw_text = QPainter.drawText

    def record_text(painter, rect, alignment, text):
        painted_text.append(text)
        return draw_text(painter, rect, alignment, text)

    monkeypatch.setattr(QPainter, "drawText", record_text)
    image = QImage(360, 88, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.magenta)
    option = QStyleOptionViewItem()
    option.initFrom(image_list)
    option.rect = QRect(0, 0, 360, 88)
    option.widget = image_list
    option.state = QStyle.StateFlag.State_Enabled
    painter = QPainter(image)
    image_list.delegate.paint(painter, option, image_list.indexFromItem(item))
    painter.end()
    assert image.pixelColor(150, 76) == IMPORTED_BACKGROUND
    assert painted_text == ["Fotografia 0.jpg", tr("Imported")]


@pytest.mark.parametrize("status", ["imported", "staging", "exported", "failed"])
@pytest.mark.parametrize("hovered", [False, True])
def test_light_theme_uses_readable_state_colors_and_stronger_hover(image_list, status, hovered):
    application = QApplication.instance()
    application.setProperty("theme_dark", False)
    item = image_list.item(0)
    item.setData(STATUS_ROLE, status)
    image = QImage(360, 88, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.magenta)
    option = QStyleOptionViewItem()
    option.initFrom(image_list)
    option.rect = QRect(0, 0, 360, 88)
    option.widget = image_list
    option.state = QStyle.StateFlag.State_Enabled | QStyle.StateFlag.State_Selected
    if hovered:
        option.state |= QStyle.StateFlag.State_MouseOver
    painter = QPainter(image)
    image_list.delegate.paint(painter, option, image_list.indexFromItem(item))
    painter.end()
    background, accent = status_colors(status, False, hovered)
    assert image.pixelColor(150, 76) == background
    assert background.lightness() > accent.lightness()
    assert status_colors(status, False, False)[0] != status_colors(status, False, True)[0]
    assert background != status_colors(status, True, hovered)[0]


@pytest.mark.parametrize("language", ["en", "sk", "cs"])
def test_status_labels_follow_current_language_without_replacing_items(
    image_list, monkeypatch, language,
):
    previous_language = get_language()
    try:
        set_language(language)
        item = image_list.item(0)
        item.setData(STATUS_ROLE, "failed")
        painted_text = []
        draw_text = QPainter.drawText

        def record_text(painter, rect, alignment, text):
            painted_text.append(text)
            return draw_text(painter, rect, alignment, text)

        monkeypatch.setattr(QPainter, "drawText", record_text)
        image = QImage(360, 88, QImage.Format.Format_ARGB32)
        option = image_list._event_option(image_list.indexFromItem(item))
        option.rect = QRect(0, 0, 360, 88)
        painter = QPainter(image)
        image_list.delegate.paint(painter, option, image_list.indexFromItem(item))
        painter.end()
        assert painted_text[-1] == tr("Failed")
        image_list.retranslate_ui()
        assert image_list.toolTip() == tr("Drop JPEG, PNG or HEIC photos here.")
        assert image_list.item(0) is item
    finally:
        set_language(previous_language)


def test_live_hover_changes_status_shade_after_scrolling(image_list, qtbot):
    for number in range(2, 12):
        item = QListWidgetItem(f"Photo {number}.jpg")
        item.setData(PATH_ROLE, f"C:/generated/photo-{number}.jpg")
        item.setData(STATUS_ROLE, "exported")
        item.setCheckState(Qt.CheckState.Unchecked)
        image_list.addItem(item)
    image_list.scrollToBottom()
    item = image_list.item(image_list.count() - 1)
    row = image_list.visualItemRect(item)
    point = QPoint(row.left() + 150, row.center().y())
    # Dispatch the hover directly: other parallel GUI suites can move the Windows cursor.
    hover = QHoverEvent(QEvent.Type.HoverMove, QPointF(point),
                        QPointF(image_list.viewport().mapToGlobal(point)), QPointF(-1, -1))
    QApplication.sendEvent(image_list.viewport(), hover)
    qtbot.waitUntil(lambda: image_list.viewport().grab().toImage().pixelColor(
        row.left() + 150, row.bottom() - 12,
    ) == EXPORTED_HOVER_BACKGROUND)


def test_drag_and_drop_preserves_local_jpeg_png_and_heic_paths(image_list):
    paths = [f"C:/generated/{name}" for name in ("photo.jpg", "photo.png", "photo.heic")]
    mime = QMimeData()
    mime.setUrls([*(QUrl.fromLocalFile(path) for path in paths), QUrl("https://example.org/x.jpg")])
    dropped = []
    image_list.pathsDropped.connect(dropped.append)
    arguments = (Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton,
                 Qt.KeyboardModifier.NoModifier)
    enter = QDragEnterEvent(QPointF(10, 10), *arguments)
    move = QDragMoveEvent(QPointF(15, 15), *arguments)
    image_list.dragEnterEvent(enter)
    image_list.dragMoveEvent(move)
    drop = QDropEvent(QPointF(20, 20), *arguments)
    image_list.dropEvent(drop)
    assert enter.isAccepted() and move.isAccepted() and drop.isAccepted()
    assert dropped == [paths]


def test_text_drag_and_remote_only_drop_are_ignored(image_list):
    mime = QMimeData()
    mime.setText("plain text")
    enter = QDragEnterEvent(QPointF(10, 10), Qt.DropAction.CopyAction, mime,
                            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    image_list.dragEnterEvent(enter)
    assert not enter.isAccepted()
    mime.setUrls([QUrl("https://example.org/photo.jpg")])
    drop = QDropEvent(QPointF(20, 20), Qt.DropAction.CopyAction, mime,
                      Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    image_list.dropEvent(drop)
    assert not drop.isAccepted()
