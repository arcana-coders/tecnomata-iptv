"""Bounded category overlay and persistent content indication."""
from PySide6.QtCore import Qt, QEvent, QPoint, Signal, QRectF
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QListView, QSizePolicy, QStyledItemDelegate,
    QStyleOptionViewItem, QStyle, QWidget, QListWidget, QSlider)
from .i18n import t

CHOSEN_ROLE = int(Qt.ItemDataRole.UserRole) + 1
FAVORITE_ROLE = CHOSEN_ROLE + 1
COLLECTION_ROLE = FAVORITE_ROLE + 1


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

            layout = QVBoxLayout(self.popup)
            header = QHBoxLayout()
            header.addWidget(QLabel(t('categories_title')))
            self.close_button = QPushButton(t('categories_close'))
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


class FavoriteList(QListWidget):
    favorite_clicked = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):
        self.viewport().setCursor(Qt.CursorShape.PointingHandCursor if event.position().x() < 38 else Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        item = self.itemAt(event.position().toPoint())
        if item and event.button() == Qt.MouseButton.LeftButton and event.position().x() < 38:
            self.favorite_clicked.emit(item)
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.position().x() < 38:
            return
        super().mouseDoubleClickEvent(event)


class ChosenContentDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        painter.save()
        styled = QStyleOptionViewItem(option)
        self.initStyleOption(styled, index)
        chosen = bool(index.data(CHOSEN_ROLE))
        from .themes import THEMES
        key = getattr(self.parent().window(), 'theme_key', 'springfield')
        accent = QColor(THEMES[key][2])
        if chosen:
            painter.fillRect(option.rect, accent)
            painter.setPen(QColor('#101010'))
        else:
            if styled.state & QStyle.StateFlag.State_Selected:
                painter.fillRect(option.rect, QColor(THEMES[key][4]).lighter(135))
            painter.setPen(styled.palette.text().color())
        if index.data(COLLECTION_ROLE):
            painter.restore()
            return  # CollectionRow provides accessible title/progress/buttons.
        styled.font.setBold(chosen)
        painter.setFont(styled.font)
        from PySide6.QtGui import QPainterPath, QPen
        from math import sin, cos, pi
        favorite = bool(index.data(FAVORITE_ROLE))
        button = QRectF(option.rect.x()+5, option.rect.center().y()-14, 30, 28)
        painter.setRenderHint(painter.RenderHint.Antialiasing)
        painter.setPen(QPen(accent if favorite else QColor('#8292a5') if key != 'dog-eyes' else QColor('#b0b0b0'), 1))
        painter.setBrush(QColor('#101010') if chosen else accent if favorite else QColor(THEMES[key][4]))
        painter.drawRoundedRect(button, 7, 7)
        path = QPainterPath()
        center = button.center()
        for n in range(10):
            radius = 9 if n % 2 == 0 else 4
            angle = -pi/2 + n*pi/5
            x, y = center.x()+cos(angle)*radius, center.y()+sin(angle)*radius
            if n == 0: path.moveTo(x,y)
            else: path.lineTo(x,y)
        path.closeSubpath()
        star_color = accent if chosen else QColor('#101010') if favorite else QColor('white')
        painter.setPen(QPen(star_color, 1.4))
        painter.setBrush(star_color if favorite else Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        painter.setPen(QColor('#101010') if chosen else styled.palette.text().color())
        text = styled.text.replace('★ ', '').replace('☆ ', '')
        rect = option.rect.adjusted(40,0,-10,0)
        painter.drawText(rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                         styled.fontMetrics.elidedText(text, Qt.TextElideMode.ElideRight, rect.width()))
        painter.restore()


class HomeTile(QPushButton):
    """Metro tile; an optional decoded-frame preview stays entirely in memory."""
    def __init__(self, text, color):
        super().__init__(text)
        self.color = QColor(color)
        self.monochrome = False
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
            if self.monochrome:
                from PySide6.QtGui import QImage, QPixmap
                image = QPixmap.fromImage(image.toImage().convertToFormat(QImage.Format.Format_Grayscale8))
            scaled = image.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                         Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap((self.width()-scaled.width())//2, (self.height()-scaled.height())//2, scaled)
            shade = QLinearGradient(0, 0, 0, self.height())
            shade.setColorAt(0, QColor(0, 0, 0, 0) if self.monochrome else QColor(10, 20, 35, 0))
            shade.setColorAt(.45, QColor(0, 0, 0, 30) if self.monochrome else QColor(10, 20, 35, 30))
            shade.setColorAt(1, QColor(0, 0, 0, 240) if self.monochrome else QColor(10, 20, 35, 240))
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
            painter.setPen(QColor('white') if self.monochrome else QColor('#00e5ff'))
            painter.drawRect(self.rect().adjusted(1, 1, -2, -2))


class DonutBadge(QWidget):
    """Small code-native brand mark, drawn independently of emoji fonts."""
    def __init__(self):
        super().__init__()
        self.setFixedSize(30, 30)
        self.setToolTip(t('donut_tooltip'))

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QPen
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor('#302335'), 2))
        theme = getattr(self, 'theme', 'springfield')
        if theme != 'springfield':
            from .themes import THEMES
            painter.setPen(QPen(QColor(THEMES[theme][2]), 2))
            painter.setBrush(QColor(THEMES[theme][4]))
            painter.drawRoundedRect(2,2,26,26,6,6)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, {'mcfly':'88','retro':'♫','dog-eyes':'◉'}[theme])
            return
        painter.setBrush(QColor('#d29a58'))
        painter.drawEllipse(2, 2, 26, 26)
        painter.setBrush(QColor('#ee87ad'))
        painter.drawEllipse(3, 3, 24, 22)
        painter.setBrush(QColor('#172235'))
        painter.drawEllipse(11, 10, 8, 8)
        for color, x, y in (('#ffda45', 7, 8), ('#7ac9e9', 20, 7), ('#ffda45', 19, 21), ('#91dbab', 6, 20)):
            painter.setPen(QPen(QColor(color), 2))
            painter.drawLine(x, y, x+3, y+1)


class TimelineSlider(QSlider):
    committed = Signal(int)

    def keyReleaseEvent(self, event):
        super().keyReleaseEvent(event)
        if self.isEnabled():
            self.committed.emit(self.value())

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            value = round(max(0, min(1, event.position().x()/max(1,self.width()))) * self.maximum())
            self.setValue(value)
            self.committed.emit(value)
