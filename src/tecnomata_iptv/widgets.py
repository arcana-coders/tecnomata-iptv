"""Bounded category overlay and persistent content indication."""
from PySide6.QtCore import Qt, QEvent, QPoint
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QListView, QSizePolicy, QStyledItemDelegate,
    QStyleOptionViewItem, QStyle)

CHOSEN_ROLE = int(Qt.ItemDataRole.UserRole) + 1


class CategoryComboBox(QComboBox):
    """Overlay stays inside the application, including on native Wayland."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.setMinimumContentsLength(12)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.popup = None

    def showPopup(self):
        if self.popup is None:
            self.popup = QFrame(self.window())
            self.popup.setObjectName("categoryPopup")
            self.popup.setStyleSheet("QFrame#categoryPopup { background: #182438; border: 1px solid #72dac7; border-radius: 7px; } QPushButton { padding: 6px 10px; }")
            layout = QVBoxLayout(self.popup)
            header = QHBoxLayout()
            header.addWidget(QLabel("Categorías"))
            self.close_button = QPushButton("Cerrar ×")
            self.close_button.clicked.connect(self.hidePopup)
            header.addWidget(self.close_button)
            layout.addLayout(header)
            self.popup_list = QListView()
            self.popup_list.setModel(self.model())
            self.popup_list.setTextElideMode(Qt.TextElideMode.ElideRight)
            self.popup_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.popup_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.popup_list.setUniformItemSizes(True)
            self.popup_list.clicked.connect(self.choose)
            self.popup_list.activated.connect(self.choose)
            layout.addWidget(self.popup_list)
            QApplication.instance().installEventFilter(self)
        host = self.window()
        point = self.mapTo(host, QPoint(0, self.height()))
        width = min(self.width(), host.width() - 16)
        height = min(340, host.height() - 16)
        x = max(8, min(point.x(), host.width() - width - 8))
        y = max(8, min(point.y(), host.height() - height - 8))
        self.popup.setGeometry(x, y, width, height)
        self.popup.show()
        self.popup.raise_()
        index = self.model().index(self.currentIndex(), 0)
        self.popup_list.setCurrentIndex(index)
        self.popup_list.scrollTo(index)
        self.popup_list.setFocus()

    def choose(self, index):
        self.setCurrentIndex(index.row())
        self.hidePopup()
        self.setFocus()

    def hidePopup(self):
        if self.popup:
            self.popup.hide()
        super().hidePopup()

    def eventFilter(self, watched, event):
        if self.popup and self.popup.isVisible():
            if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
                self.hidePopup()
                self.setFocus()
                return True
            if event.type() == QEvent.Type.MouseButtonPress:
                point = self.popup.mapFromGlobal(event.globalPosition().toPoint())
                if not self.popup.rect().contains(point):
                    self.hidePopup()
            if watched is self.window() and event.type() in (QEvent.Type.Resize, QEvent.Type.WindowDeactivate):
                self.hidePopup()
        return super().eventFilter(watched, event)


class ChosenContentDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        if not index.data(CHOSEN_ROLE):
            return super().paint(painter, option, index)
        painter.save()
        painter.fillRect(option.rect, QColor("#17685e"))
        painter.fillRect(option.rect.adjusted(0, 0, -option.rect.width() + 4, 0), QColor("#72dac7"))
        styled = QStyleOptionViewItem(option)
        self.initStyleOption(styled, index)
        styled.state &= ~QStyle.StateFlag.State_Selected
        styled.font.setBold(True)
        painter.setFont(styled.font)
        painter.setPen(QColor("#ffffff"))
        rect = option.rect.adjusted(12, 0, -10, 0)
        text = styled.fontMetrics.elidedText("● " + styled.text, Qt.TextElideMode.ElideRight, rect.width())
        painter.drawText(rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
        painter.restore()
