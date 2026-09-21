"""Floating detail modal dialog and cover grid for movies and series."""
from PySide6.QtCore import Qt, QSize, QRectF, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPainterPath, QPixmap
from PySide6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QProgressBar, QListWidget, QListView,
                               QStyledItemDelegate, QStyleOptionViewItem, QStyle,
                               QScrollArea, QFrame, QSizePolicy)

from .i18n import t
from .themes import THEMES

POSTER_WIDTH = 150
POSTER_HEIGHT = 225
ITEM_WIDTH = 156
ITEM_HEIGHT = 275


class PosterDelegate(QStyledItemDelegate):
    def __init__(self, parent, cover_cache, theme_getter):
        super().__init__(parent)
        self.cover_cache = cover_cache
        self.theme_getter = theme_getter

    def sizeHint(self, option, index):
        return QSize(ITEM_WIDTH, ITEM_HEIGHT)

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        row = index.data(Qt.ItemDataRole.UserRole) or {}
        theme_key = self.theme_getter()
        theme = THEMES.get(theme_key, THEMES["springfield"])
        accent = QColor(theme[2])
        panel = QColor(theme[4])

        rect = option.rect
        poster_rect = QRectF(rect.x() + (rect.width() - POSTER_WIDTH) / 2, rect.y() + 4,
                             POSTER_WIDTH, POSTER_HEIGHT)

        # Highlight if selected or hovered
        is_selected = bool(option.state & QStyle.StateFlag.State_Selected)
        is_hover = bool(option.state & QStyle.StateFlag.State_MouseOver)

        # Get poster image
        url = row.get("stream_icon") or row.get("cover")
        title = str(row.get("name", t("unnamed_category")))

        pixmap = self.cover_cache.get(url)
        if not pixmap or pixmap.isNull():
            pixmap = self.cover_cache.placeholder(title, theme_key, QSize(POSTER_WIDTH, POSTER_HEIGHT))

        clip_path = QPainterPath()
        clip_path.addRoundedRect(poster_rect, 8, 8)
        painter.save()
        painter.setClipPath(clip_path)
        scaled = pixmap.scaled(QSize(int(POSTER_WIDTH), int(POSTER_HEIGHT)),
                               Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                               Qt.TransformationMode.SmoothTransformation)
        # Center the scaled image in the poster box
        ox = poster_rect.x() + (POSTER_WIDTH - scaled.width()) / 2
        oy = poster_rect.y() + (POSTER_HEIGHT - scaled.height()) / 2
        painter.drawPixmap(int(ox), int(oy), scaled)
        painter.restore()

        # Border
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if is_selected:
            painter.setPen(QPen(accent, 2.5))
            painter.drawRoundedRect(poster_rect, 8, 8)
        elif is_hover:
            painter.setPen(QPen(accent.lighter(130), 1.5))
            painter.drawRoundedRect(poster_rect, 8, 8)
        else:
            painter.setPen(QPen(panel.lighter(120), 1))
            painter.drawRoundedRect(poster_rect, 8, 8)

        # Rating badge in top-right if present
        rating = str(row.get("rating", "")).strip()
        if rating and rating not in ("0", "0.0", "None", ""):
            try:
                r_val = float(rating)
                if r_val > 0:
                    badge_rect = QRectF(poster_rect.right() - 48, poster_rect.top() + 6, 42, 20)
                    painter.setBrush(QColor(0, 0, 0, 190))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawRoundedRect(badge_rect, 4, 4)
                    font = QFont()
                    font.setPixelSize(11)
                    font.setBold(True)
                    painter.setFont(font)
                    painter.setPen(accent)
                    painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, f"★ {r_val:.1f}")
            except ValueError:
                pass

        # Title underneath
        title_rect = QRectF(rect.x() + 4, poster_rect.bottom() + 6, rect.width() - 8,
                            ITEM_HEIGHT - POSTER_HEIGHT - 10)
        font = QFont()
        font.setPixelSize(12)
        font.setBold(is_selected)
        painter.setFont(font)
        painter.setPen(accent if is_selected else QColor("#e2e8f0"))
        elided = painter.fontMetrics().elidedText(title, Qt.TextElideMode.ElideRight, int(title_rect.width()))
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, elided)

        painter.restore()


class CoverGridView(QListWidget):
    poster_activated = Signal(object)  # emits row dict

    def __init__(self, cover_cache, theme_getter, parent=None):
        super().__init__(parent)
        self.cover_cache = cover_cache
        self.theme_getter = theme_getter
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setMovement(QListView.Movement.Static)
        self.setSpacing(14)
        self.setUniformItemSizes(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setStyleSheet("QListWidget { background: transparent; border: none; }")
        self.setItemDelegate(PosterDelegate(self, cover_cache, theme_getter))
        self.cover_cache.cover_loaded.connect(lambda _u: self.viewport().update())
        self.itemActivated.connect(self._on_activated)
        self.itemClicked.connect(self._on_activated)

    def _on_activated(self, item):
        row = item.data(Qt.ItemDataRole.UserRole)
        if row:
            self.poster_activated.emit(row)


class ContentDetailDialog(QDialog):
    """Floating detail card showing synopsis, metadata, and action buttons."""
    def __init__(self, parent, row, kind, cover_cache, theme_key="springfield",
                 progress_data=None, is_fav=False, on_play=None, on_restart=None,
                 on_toggle_favorite=None, on_episodes=None):
        super().__init__(parent)
        self.row = row
        self.kind = kind
        self.on_play = on_play
        self.on_restart = on_restart
        self.on_toggle_favorite = on_toggle_favorite
        self.on_episodes = on_episodes
        self.is_fav = is_fav

        title = str(row.get("name", t("unnamed_category")))
        self.setWindowTitle(title)
        self.setMinimumWidth(620)
        self.setMaximumWidth(720)
        self.setModal(True)

        theme = THEMES.get(theme_key, THEMES["springfield"])
        accent = theme[2]
        bg = theme[3]
        panel = theme[4]
        border_color = QColor(panel).lighter(135).name()

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: #e2e8f0;
                border: 1px solid {panel};
                border-radius: 8px;
            }}
            QLabel {{ color: #e2e8f0; }}
            QLabel#detailTitle {{
                font-size: 20px;
                font-weight: bold;
                color: {accent};
            }}
            QLabel#badge {{
                background-color: {panel};
                border: 1px solid {accent};
                border-radius: 4px;
                padding: 3px 8px;
                font-weight: bold;
                font-size: 11px;
                color: {accent};
            }}
            QPushButton#primaryBtn {{
                background-color: {accent};
                color: #101010;
                font-weight: bold;
                font-size: 13px;
                border-radius: 6px;
                padding: 8px 18px;
            }}
            QPushButton#primaryBtn:hover {{
                background-color: #ffffff;
            }}
            QPushButton#secondaryBtn {{
                background-color: {panel};
                color: #e2e8f0;
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 8px 14px;
            }}
            QPushButton#secondaryBtn:hover {{
                border-color: {accent};
                color: {accent};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        content_row = QHBoxLayout()
        content_row.setSpacing(20)

        # Left: Poster
        self.poster_label = QLabel()
        self.poster_label.setFixedSize(170, 255)
        self.poster_label.setScaledContents(True)
        url = row.get("stream_icon") or row.get("cover")
        pix = cover_cache.get(url, lambda u, p: self._update_poster(p))
        if not pix or pix.isNull():
            pix = cover_cache.placeholder(title, theme_key, QSize(170, 255))
        self._update_poster(pix)
        content_row.addWidget(self.poster_label)

        # Right: Details
        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("detailTitle")
        title_lbl.setWordWrap(True)
        right_col.addWidget(title_lbl)

        # Badges row (Rating, Year, Duration, Genre)
        badges_layout = QHBoxLayout()
        badges_layout.setSpacing(8)

        rating = str(row.get("rating", "")).strip()
        if rating and rating not in ("0", "0.0", "None"):
            try:
                r_val = float(rating)
                badge = QLabel(f"★ {r_val:.1f}")
                badge.setObjectName("badge")
                badges_layout.addWidget(badge)
            except ValueError:
                pass

        release = str(row.get("releaseDate") or row.get("year") or "").strip()
        if release:
            badge = QLabel(release[:4])
            badge.setObjectName("badge")
            badges_layout.addWidget(badge)

        duration = row.get("duration") or row.get("episode_run_time")
        if duration:
            badge = QLabel(f"{duration} min" if str(duration).isdigit() else str(duration))
            badge.setObjectName("badge")
            badges_layout.addWidget(badge)

        genre = str(row.get("genre", "")).strip()
        if genre:
            badge = QLabel(genre.split(",")[0].strip())
            badge.setObjectName("badge")
            badges_layout.addWidget(badge)

        badges_layout.addStretch(1)
        right_col.addLayout(badges_layout)

        # Director and Cast
        director = str(row.get("director", "")).strip()
        if director:
            d_lbl = QLabel(t("detail_director", director=director))
            d_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
            right_col.addWidget(d_lbl)

        cast = str(row.get("cast", "")).strip()
        if cast:
            c_lbl = QLabel(t("detail_cast", cast=cast[:90] + ("…" if len(cast) > 90 else "")))
            c_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
            c_lbl.setWordWrap(True)
            right_col.addWidget(c_lbl)

        # Plot / Synopsis
        plot = str(row.get("plot", "")).strip()
        plot_scroll = QScrollArea()
        plot_scroll.setWidgetResizable(True)
        plot_scroll.setFrameShape(QFrame.Shape.NoFrame)
        plot_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        plot_lbl = QLabel(plot if plot else t("detail_no_plot"))
        plot_lbl.setWordWrap(True)
        plot_lbl.setStyleSheet("color: #cbd5e1; font-size: 13px; line-height: 1.4;")
        plot_scroll.setWidget(plot_lbl)
        right_col.addWidget(plot_scroll, 1)

        # Progress bar if partially watched
        if progress_data and not progress_data.get("completed"):
            pos = float(progress_data.get("position", 0))
            dur = float(progress_data.get("duration", 1))
            if dur > 0 and pos > 0:
                p_layout = QVBoxLayout()
                pct = int(min(100, max(0, (pos / dur) * 100)))
                m_pos, s_pos = int(pos // 60), int(pos % 60)
                m_dur, s_dur = int(dur // 60), int(dur % 60)
                time_str = f"{m_pos:02d}:{s_pos:02d} / {m_dur:02d}:{s_dur:02d}"
                p_lbl = QLabel(f"Progreso: {pct}% ({time_str})")
                p_lbl.setStyleSheet(f"color: {accent}; font-size: 11px;")
                bar = QProgressBar()
                bar.setRange(0, 100)
                bar.setValue(pct)
                bar.setTextVisible(False)
                bar.setFixedHeight(5)
                bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {accent}; border-radius: 2px; }}")
                p_layout.addWidget(p_lbl)
                p_layout.addWidget(bar)
                right_col.addLayout(p_layout)

        content_row.addLayout(right_col, 1)
        layout.addLayout(content_row, 1)

        # Buttons footer
        footer = QHBoxLayout()
        footer.setSpacing(10)

        # Favorite button
        self.fav_btn = QPushButton(f"★ {t('favorite_button')}" if is_fav else f"☆ {t('favorite_button')}")
        self.fav_btn.setObjectName("secondaryBtn")
        self.fav_btn.clicked.connect(self._toggle_fav)
        footer.addWidget(self.fav_btn)

        footer.addStretch(1)

        # Restart button if progress exists
        if progress_data and float(progress_data.get("position", 0)) > 10:
            restart_btn = QPushButton(t("detail_restart"))
            restart_btn.setObjectName("secondaryBtn")
            restart_btn.clicked.connect(self._restart)
            footer.addWidget(restart_btn)

        # Main Play / Episodes button
        if kind == "series":
            play_btn = QPushButton(t("detail_episodes"))
            play_btn.setObjectName("primaryBtn")
            play_btn.clicked.connect(self._episodes)
            footer.addWidget(play_btn)
        else:
            label = t("detail_play")
            if progress_data and not progress_data.get("completed") and float(progress_data.get("position", 0)) > 10:
                pos = float(progress_data.get("position", 0))
                m, s = int(pos // 60), int(pos % 60)
                label = t("detail_resume", time=f"{m:02d}:{s:02d}")
            play_btn = QPushButton(label)
            play_btn.setObjectName("primaryBtn")
            play_btn.clicked.connect(self._play)
            footer.addWidget(play_btn)

        close_btn = QPushButton(t("detail_close"))
        close_btn.setObjectName("secondaryBtn")
        close_btn.clicked.connect(self.reject)
        footer.addWidget(close_btn)

        layout.addLayout(footer)

    def _update_poster(self, pix):
        if pix and not pix.isNull():
            self.poster_label.setPixmap(pix.scaled(170, 255, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                                  Qt.TransformationMode.SmoothTransformation))

    def _play(self):
        self.accept()
        if self.on_play:
            self.on_play(restart=False)

    def _restart(self):
        self.accept()
        if self.on_restart:
            self.on_restart()
        elif self.on_play:
            self.on_play(restart=True)

    def _episodes(self):
        self.accept()
        if self.on_episodes:
            self.on_episodes()

    def _toggle_fav(self):
        if self.on_toggle_favorite:
            self.is_fav = self.on_toggle_favorite()
            self.fav_btn.setText(f"★ {t('favorite_button')}" if self.is_fav else f"☆ {t('favorite_button')}")
