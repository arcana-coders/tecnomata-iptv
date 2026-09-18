"""Compact, accessible movie/episode cards for the existing library list."""
from math import cos, sin, pi
from PySide6.QtCore import Qt, QSize, QRectF
from PySide6.QtGui import QPainter, QPainterPath, QPen, QColor
from PySide6.QtWidgets import QWidget, QPushButton, QLabel, QProgressBar, QHBoxLayout, QVBoxLayout, QSizePolicy
from .themes import THEMES
from .i18n import t


def timestamp(seconds):
    minutes, seconds = divmod(max(0,int(seconds or 0)),60)
    hours, minutes = divmod(minutes,60)
    return f'{hours}:{minutes:02}:{seconds:02}' if hours else f'{minutes}:{seconds:02}'


class ElidedLabel(QLabel):
    def __init__(self,text):
        super().__init__()
        self.full_text = text
        self.setToolTip(text)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)

    def resizeEvent(self,event):
        self.setText(self.fontMetrics().elidedText(self.full_text,Qt.TextElideMode.ElideRight,self.width()))
        super().resizeEvent(event)


class FavoriteButton(QPushButton):
    def __init__(self,favorite):
        super().__init__()
        self.setCheckable(True); self.setChecked(favorite)
        self.setFixedSize(30,28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName(t('remove_from_favorites') if favorite else t('add_to_favorites'))
        self.setToolTip(self.accessibleName())

    def paintEvent(self,event):
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        key = getattr(self.window(),'theme_key','springfield')
        accent = QColor(THEMES[key][2]); filled = self.isChecked()
        painter.setPen(QPen(accent if filled else QColor('#b0b0b0'),1))
        painter.setBrush(accent if filled else QColor(THEMES[key][4]))
        painter.drawRoundedRect(QRectF(1,1,28,26),7,7)
        path = QPainterPath()
        for n in range(10):
            radius = 9 if n%2 == 0 else 4
            angle = -pi/2+n*pi/5
            point = (15+cos(angle)*radius,14+sin(angle)*radius)
            if n == 0: path.moveTo(*point)
            else: path.lineTo(*point)
        path.closeSubpath()
        color = QColor('#101010') if filled else QColor('white')
        painter.setPen(QPen(color,1.4)); painter.setBrush(color if filled else Qt.BrushStyle.NoBrush)
        painter.drawPath(path)


class CollectionRow(QWidget):
    def __init__(self,title,favorite,series=False):
        super().__init__()
        self.setObjectName('collectionRow')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground,True)
        self.series = series
        layout = QVBoxLayout(self); layout.setContentsMargins(5,5,8,5); layout.setSpacing(3)
        header = QHBoxLayout(); header.setSpacing(5)
        self.star = FavoriteButton(favorite)
        self.title = ElidedLabel(title)
        header.addWidget(self.star); header.addWidget(self.title,1)
        layout.addLayout(header)
        body = QVBoxLayout(); body.setSpacing(3); body.setContentsMargins(0,0,0,0)
        self.status = ElidedLabel(t('not_started'))
        self.status.setObjectName('collectionStatus')
        self.progress_bar = QProgressBar(); self.progress_bar.setRange(0,1000)
        self.progress_bar.setTextVisible(False); self.progress_bar.setFixedHeight(5)
        self.progress_bar.setAccessibleName(t('progress_of', title=title))
        body.addWidget(self.progress_bar); body.addWidget(self.status)
        actions = QHBoxLayout(); actions.setSpacing(5)
        self.continue_button = QPushButton(t('continue_button'))
        self.restart_button = QPushButton(t('restart_button'))
        for button in (self.continue_button,self.restart_button):
            button.setObjectName('collectionAction'); button.setCursor(Qt.CursorShape.PointingHandCursor)
            actions.addWidget(button)
        body.addLayout(actions); layout.addLayout(body)
        self.set_progress(None)

    def sizeHint(self):
        return QSize(250,94)

    def resizeEvent(self,event):
        for button in (self.continue_button,self.restart_button):
            button.setMinimumWidth(button.fontMetrics().horizontalAdvance(button.text())+12)
        super().resizeEvent(event)

    def set_chosen(self,chosen):
        self.setProperty('chosen',bool(chosen))
        self.style().unpolish(self); self.style().polish(self)

    def set_progress(self,saved,episode_name=''):
        duration = saved['duration'] if saved else 0
        completed = bool(saved and saved['completed'])
        position = duration if completed else saved['position'] if saved else 0
        value = max(0,min(1000,round(1000*position/duration))) if duration else 0
        self.progress_bar.setValue(value)
        text = t('watched_full') if completed else f'{timestamp(position)} / {timestamp(duration)} · {value/10:.0f}%' if duration else t('not_started')
        if episode_name: text = f'{episode_name} · {text}'
        self.status.full_text = text
        self.status.setToolTip(text)
        self.status.setText(self.status.fontMetrics().elidedText(text,Qt.TextElideMode.ElideRight,self.status.width()))
        self.progress_bar.setToolTip(text)
        self.continue_button.setText(t('view_episodes') if self.series and not saved else t('continue_button'))
        self.continue_button.setEnabled(bool(saved and not completed and position>0) or self.series and not saved)
        self.restart_button.setEnabled(not self.series or bool(saved))
        self.restart_button.setVisible(not self.series or bool(saved))
        self.continue_button.setAccessibleName(f'{self.continue_button.text()}: {self.title.full_text}')
        self.restart_button.setAccessibleName(f'{t("restart_button")}: {self.title.full_text}')
