"""Bounded category overlay and persistent content indication."""
from PySide6.QtCore import Qt, QEvent, QPoint
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QListView, QSizePolicy, QStyledItemDelegate,
    QStyleOptionViewItem, QStyle, QWidget)

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
            self.popup.setStyleSheet("QFrame#categoryPopup { background: #17263d; border: 1px solid #f5cc39; border-radius: 8px; } QPushButton { padding: 6px 10px; }")
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
        painter.fillRect(option.rect, QColor("#f5cc39"))
        painter.fillRect(option.rect.adjusted(0, 0, -option.rect.width() + 4, 0), QColor("#00e5ff"))
        styled = QStyleOptionViewItem(option)
        self.initStyleOption(styled, index)
        styled.state &= ~QStyle.StateFlag.State_Selected
        styled.font.setBold(True)
        painter.setFont(styled.font)
        painter.setPen(QColor("#192333"))
        rect = option.rect.adjusted(12, 0, -10, 0)
        text = styled.fontMetrics.elidedText("● " + styled.text, Qt.TextElideMode.ElideRight, rect.width())
        painter.drawText(rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
        painter.restore()


class HomeTile(QPushButton):
    """Metro tile; an optional decoded-frame preview stays entirely in memory."""
    def __init__(self, text, color):
        super().__init__(text)
        self.color = QColor(color)
        self.preview = None
        self.example = None
        self.preview_title = ''

    def set_example(self, image):
        self.example = image
        self.update()

    def sizeHint(self):
        from PySide6.QtCore import QSize
        return QSize(200, 180)

    def minimumSizeHint(self):
        from PySide6.QtCore import QSize
        return QSize(160, 140)

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QFont, QPainterPath, QLinearGradient
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        clip = QPainterPath()
        clip.addRoundedRect(self.rect(), 14, 14)
        painter.setClipPath(clip)
        painter.fillRect(self.rect(), self.color)
        image = self.preview if self.preview is not None and not self.preview.isNull() else self.example
        if image is not None and not image.isNull():
            scaled = image.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                         Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap((self.width()-scaled.width())//2, (self.height()-scaled.height())//2, scaled)
            shade = QLinearGradient(0, 0, 0, self.height())
            shade.setColorAt(0, QColor(10, 20, 35, 0))
            shade.setColorAt(.45, QColor(10, 20, 35, 30))
            shade.setColorAt(1, QColor(10, 20, 35, 240))
            painter.fillRect(self.rect(), shade)
        font = QFont(self.font())
        font.setPixelSize(20)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor('white'))
        lines = [line for line in self.text().splitlines() if line]
        rect = self.rect().adjusted(20, self.height()-110, -16, -70)
        painter.drawText(rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         painter.fontMetrics().elidedText(lines[0], Qt.TextElideMode.ElideRight, rect.width()))
        font.setPixelSize(14)
        font.setBold(False)
        painter.setFont(font)
        rect = self.rect().adjusted(20, self.height()-70, -16, -20)
        details = lines[-1] + ('\n' + self.preview_title if self.preview_title else '')
        painter.drawText(rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         '\n'.join(painter.fontMetrics().elidedText(line, Qt.TextElideMode.ElideRight, rect.width()) for line in details.splitlines()))
        if self.hasFocus() or self.underMouse():
            painter.setPen(QColor('#00e5ff'))
            painter.drawRect(self.rect().adjusted(1, 1, -2, -2))


class DonutBadge(QWidget):
    """Small code-native brand mark, drawn independently of emoji fonts."""
    def __init__(self):
        super().__init__()
        self.setFixedSize(30, 30)
        self.setToolTip('Un sofá, una dona y algo bueno para ver')

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QPen
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor('#302335'), 2))
        painter.setBrush(QColor('#d29a58'))
        painter.drawEllipse(2, 2, 26, 26)
        painter.setBrush(QColor('#ee87ad'))
        painter.drawEllipse(3, 3, 24, 22)
        painter.setBrush(QColor('#172235'))
        painter.drawEllipse(11, 10, 8, 8)
        for color, x, y in (('#ffda45', 7, 8), ('#7ac9e9', 20, 7), ('#ffda45', 19, 21), ('#91dbab', 6, 20)):
            painter.setPen(QPen(QColor(color), 2))
            painter.drawLine(x, y, x+3, y+1)
