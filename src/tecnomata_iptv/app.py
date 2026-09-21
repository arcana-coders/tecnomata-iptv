import argparse
import subprocess
import sys
import json
import os
import time
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Qt, QTimer, QSettings, QSize
from PySide6.QtGui import QShortcut, QKeySequence, QFont, QFontDatabase
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QLineEdit, QComboBox, QListWidget, QGridLayout, QSizePolicy,
    QListWidgetItem, QSplitter, QSlider, QDialog, QFormLayout, QDialogButtonBox, QCheckBox, QStackedWidget)

from .xtream import Account, XtreamClient, ServiceError
from .player import VideoWidget
from .catalog import CatalogCache, KINDS
from .accounts import AccountStore, StorageError
from .library import LibraryStore, LibraryError, account_scope
from .collection_row import CollectionRow
from .progress import track_choice, resolve_track
from .mpris import MprisBridge
from .themes import THEMES, stylesheet, illustration
from .media import describe_video, track_label
from .widgets import (CategoryComboBox, ChosenContentDelegate, CHOSEN_ROLE, FAVORITE_ROLE, COLLECTION_ROLE,
                      LIVE_ROLE, IN_LIST_ROLE, LIST_BUTTON_X, HomeTile, DonutBadge, FavoriteList, TimelineSlider)
from .quality import probe_stream, TIERS
from .covers import CoverCache
from .details import CoverGridView, ContentDetailDialog
from .i18n import t, LANGUAGES, current_language, set_language


class Signals(QObject):
    done = Signal(object)
    error = Signal(str)


class Job(QRunnable):
    def __init__(self, function):
        super().__init__()
        self.function = function
        self.signals = Signals()

    def run(self):
        try:
            self.signals.done.emit(self.function())
        except (ServiceError, StorageError) as exc:
            self.signals.error.emit(str(exc))
        except Exception:
            # Never expose exception text: HTTP URLs contain account secrets.
            self.signals.error.emit(t('error_generic_operation'))


class Login(QDialog):
    def __init__(self, parent, account=None):
        super().__init__(parent)
        self.setWindowTitle(t('login_title'))
        self.setMinimumWidth(440)
        form = QFormLayout(self)
        form.addRow(QLabel(t('login_intro')))
        self.server = QLineEdit()
        self.server.setPlaceholderText("http://servidor:puerto")
        self.user = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        for label, widget in [(t('login_server'), self.server), (t('login_user'), self.user), (t('login_password'), self.password)]:
            form.addRow(label, widget)
        if account:
            self.server.setText(account.server)
            self.user.setText(account.username)
            self.password.setText(account.password)
        self.remember = QCheckBox(t('login_remember'))
        self.remember.setChecked(True)
        form.addRow(self.remember)
        self.error = QLabel()
        self.error.setWordWrap(True)
        form.addRow(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(t('login_connect'))
        buttons.accepted.connect(self.validate)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def validate(self):
        try:
            self.account = Account(self.server.text(), self.user.text(), self.password.text())
            self.accept()
        except (ServiceError, ValueError) as exc:
            self.error.setText(str(exc) if isinstance(exc, ServiceError) else t('error_invalid_server'))


class ListNameDialog(QDialog):
    def __init__(self, parent, title, initial=''):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(320)
        form = QFormLayout(self)
        self.name_edit = QLineEdit(initial)
        form.addRow(t('list_name_label'), self.name_edit)
        self.error = QLabel()
        self.error.setWordWrap(True)
        form.addRow(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.validate)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def validate(self):
        if not self.name_edit.text().strip():
            self.error.setText(t('list_name_label'))
            return
        self.accept()


class ConfirmDialog(QDialog):
    def __init__(self, parent, title, text, confirm_label):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(320)
        layout = QVBoxLayout(self)
        label = QLabel(text)
        label.setWordWrap(True)
        layout.addWidget(label)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        confirm = buttons.addButton(confirm_label, QDialogButtonBox.ButtonRole.DestructiveRole)
        confirm.clicked.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class ListMembershipDialog(QDialog):
    """Checkbox per existing list plus an inline field to create and add at once."""
    def __init__(self, parent, lists, membership, on_toggle, on_create, channel_name):
        super().__init__(parent)
        self.setWindowTitle(t('list_membership_dialog_title', name=channel_name))
        self.setMinimumWidth(320)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(t('list_membership_intro')))
        self.checks_layout = QVBoxLayout()
        layout.addLayout(self.checks_layout)
        self.empty_label = QLabel(t('list_membership_empty'))
        layout.addWidget(self.empty_label)
        self.checks = {}
        self.on_toggle = on_toggle
        for item in lists:
            self.add_row(item['list_id'], item['name'], item['list_id'] in membership)
        new_row = QHBoxLayout()
        self.new_name = QLineEdit()
        self.new_name.setPlaceholderText(t('list_membership_new_placeholder'))
        self.create_button = QPushButton(t('list_membership_new_button'))
        self.create_button.clicked.connect(lambda: self._create(on_create))
        new_row.addWidget(self.new_name, 1)
        new_row.addWidget(self.create_button)
        layout.addLayout(new_row)
        self.error = QLabel()
        self.error.setWordWrap(True)
        layout.addWidget(self.error)
        done_button = QPushButton(t('list_membership_close'))
        done_button.clicked.connect(self.accept)
        layout.addWidget(done_button)
        self._sync_empty()

    def add_row(self, list_id, name, checked):
        box = QCheckBox(name)
        box.setChecked(checked)
        box.toggled.connect(lambda state, list_id=list_id: self.on_toggle(list_id, state))
        self.checks_layout.addWidget(box)
        self.checks[list_id] = box
        self._sync_empty()

    def _sync_empty(self):
        self.empty_label.setVisible(not self.checks)

    def _create(self, on_create):
        name = self.new_name.text().strip()
        if not name:
            return
        try:
            list_id = on_create(name)
        except LibraryError as exc:
            self.error.setText(str(exc))
            return
        self.new_name.clear()
        self.error.clear()
        self.add_row(list_id, name, True)


class Window(QMainWindow):
    def __init__(self, demo=False, demo_files=(), restore=True, account_store=None, library_store=None, mpris_enabled=None):
        super().__init__()
        self.setWindowTitle("Tecnomata IPTV")
        self.setObjectName("tecnomata-iptv")
        self.resize(1200, 760)
        self.mpris = None
        self.playback_status = "Stopped"
        self.mpris_track = 0
        self.position_info = {}
        self.library_error = None
        try:
            self.library = library_store or LibraryStore(':memory:' if demo else None)
        except LibraryError as exc:
            self.library = None
            self.library_error = str(exc)
        self.library_scope = 'demo' if demo else None
        self.collection_view = None
        self.pending_history = None
        self.progress_context = None
        self.pending_resume = None
        self.resume_target = None
        self.progress_blocked = False
        self.visible_rows = []
        self.list_names = {}
        self.scan_active = False
        self.scan_cancel_requested = False
        self.scan_queue = []
        self.scan_total = 0
        self.scan_tally = {'sd': [], 'hd': [], 'fullhd': [], 'unknown': 0}
        self.scan_context_label = ''
        self.restoring_progress = False
        self.last_checkpoint = 0
        self.progress_snapshot = None
        self.current_series_name = ''
        self.cover_cache = CoverCache()
        self.client = None
        self.cache = None
        self.account_store = account_store or AccountStore()
        self.saved_account = None
        self.foreground_jobs = set()
        self.pending_section = None
        self.failed_sections = set()
        self.category_choices = {}
        self.chosen = {}
        self.current_series_id = None
        self.playing_kind = None
        self.demo = demo
        self.demo_files = list(demo_files)
        self.kind = "live"
        self.rows = []
        self.in_episodes = False
        self.jobs = set()
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        top = QHBoxLayout()
        self.theme_badge = DonutBadge()
        top.addWidget(self.theme_badge)
        title = QLabel("TECNOMATA IPTV")
        title.setObjectName("brand")
        top.addWidget(title)
        nav_header = QWidget()
        nav_header.setObjectName('topNav')
        pivots = QHBoxLayout(nav_header)
        pivots.setContentsMargins(4, 4, 4, 4)
        pivots.setSpacing(2)
        top.addWidget(nav_header)
        self.home_button = QPushButton(t('nav_home'))
        self.home_button.setCheckable(True)
        self.home_button.clicked.connect(self.show_home)
        pivots.addWidget(self.home_button)
        self.player_button = QPushButton(t('nav_watch'))
        self.player_button.setCheckable(True)
        self.player_button.clicked.connect(self.show_player)
        pivots.addWidget(self.player_button)
        self.list_button = QPushButton("☷")
        self.list_button.setObjectName("listToggle")
        self.list_button.setAccessibleName(t('list_toggle_accessible'))
        self.list_button.setCheckable(True)
        self.list_button.setChecked(True)
        self.list_button.setToolTip(t('list_toggle_tooltip'))
        self.list_button.clicked.connect(self.toggle_list)
        top.addWidget(self.list_button)
        top.addStretch()
        self.connect_button = QPushButton(t('connect_service'))
        self.connect_button.clicked.connect(self.login)
        top.addWidget(self.connect_button)
        self.forget_button = QPushButton(t('forget_account'))
        self.forget_button.clicked.connect(self.forget_account)
        self.forget_button.hide()
        top.addWidget(self.forget_button)
        layout.addLayout(top)
        self.navigation = QWidget()
        nav = QHBoxLayout(self.navigation)
        nav.setContentsMargins(0, 0, 0, 0)
        nav.setSpacing(2)
        self.tabs = {}
        for kind, name in [("live", t('tab_live')), ("vod", t('tab_vod')), ("series", t('tab_series'))]:
            button = QPushButton(name)
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, kind=kind: self.section(kind))
            self.tabs[kind] = button
            nav.addWidget(button)
        filters = QVBoxLayout()
        filters.setSpacing(6)
        self.category = CategoryComboBox()
        self.category.addItem(t('all_categories'), None)
        self.category.currentIndexChanged.connect(self.load_catalog)
        self.search = QLineEdit()
        self.search.setClearButtonEnabled(True)
        self.search.setPlaceholderText(t('search_section'))
        self.search.textChanged.connect(self.filter_rows)
        self.back = QPushButton(t('back_to_series'))
        self.back.clicked.connect(lambda: self.section("series"))
        self.back.hide()
        filters.addWidget(self.category)
        filters.addWidget(self.search)
        filters.addWidget(self.back)
        self.refresh_button = QPushButton(t('refresh_lists'))
        self.refresh_button.clicked.connect(self.refresh_catalogs)
        self.refresh_button.setEnabled(False)
        top.addWidget(self.refresh_button)
        self.splitter = QSplitter()
        self.items = FavoriteList()
        self.items.favorite_clicked.connect(self.favorite_clicked)
        self.items.list_button_clicked.connect(self.open_list_membership)
        self.items.setItemDelegate(ChosenContentDelegate(self.items))
        self.items.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.items.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.items.itemActivated.connect(self.activate)
        self.left_panel = QWidget()
        self.left_panel.setObjectName("sidebar")
        sidebar_layout = QHBoxLayout(self.left_panel)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        sidebar_content = QWidget()
        sidebar_layout.addWidget(sidebar_content, 1)
        left = QVBoxLayout(sidebar_content)
        left.setContentsMargins(8, 8, 8, 8)
        left.setSpacing(6)
        self.scan_button = QPushButton(t('scan_quality_button'))
        self.scan_button.setToolTip(t('scan_quality_tooltip'))
        self.scan_button.clicked.connect(self.toggle_quality_scan)
        self.scan_button.setEnabled(False)
        self.scan_button.hide()
        left.addWidget(self.scan_button)
        self.list_heading = QLabel(t('heading_live'))
        self.list_heading.setObjectName("listHeading")
        left.addWidget(self.list_heading)
        left.addWidget(self.navigation)
        left.addLayout(filters)
        collections = QHBoxLayout()
        self.favorites_button = QPushButton(t('favorites_button'))
        self.recent_button = QPushButton(t('recent_button'))
        for button, view in ((self.favorites_button, 'favorites'), (self.recent_button, 'recent')):
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, view=view: self.show_collection(view))
            collections.addWidget(button)
        left.addLayout(collections)
        lists_row = QHBoxLayout()
        self.lists_combo = QComboBox()
        self.lists_combo.addItem(t('lists_combo_placeholder'), None)
        self.lists_combo.currentIndexChanged.connect(self.choose_list)
        self.new_list_button = QPushButton(t('new_list_button'))
        self.new_list_button.setToolTip(t('new_list_tooltip'))
        self.new_list_button.clicked.connect(self.create_list_dialog)
        self.rename_list_button = QPushButton(t('rename_list_button'))
        self.rename_list_button.setToolTip(t('rename_list_tooltip'))
        self.rename_list_button.setEnabled(False)
        self.rename_list_button.clicked.connect(self.rename_list_dialog)
        self.delete_list_button = QPushButton(t('delete_list_button'))
        self.delete_list_button.setToolTip(t('delete_list_tooltip'))
        self.delete_list_button.setEnabled(False)
        self.delete_list_button.clicked.connect(self.delete_list_dialog)
        lists_row.addWidget(self.lists_combo, 1)
        lists_row.addWidget(self.new_list_button)
        lists_row.addWidget(self.rename_list_button)
        lists_row.addWidget(self.delete_list_button)
        left.addLayout(lists_row)
        left.addWidget(self.items, 1)
        hide_rail = QVBoxLayout()
        hide_rail.setContentsMargins(0, 0, 3, 0)
        hide_rail.addStretch()
        self.hide_list_button = QPushButton('‹')
        self.hide_list_button.setObjectName('sidebarReveal')
        self.hide_list_button.setFixedSize(30, 72)
        self.hide_list_button.setAccessibleName(t('hide_list_accessible'))
        self.hide_list_button.setToolTip(t('hide_list_tooltip'))
        self.hide_list_button.clicked.connect(lambda: self.set_list_visible(False))
        hide_rail.addWidget(self.hide_list_button)
        hide_rail.addStretch()
        sidebar_layout.addLayout(hide_rail)
        self.items.currentItemChanged.connect(self.sync_favorite)
        self.splitter.addWidget(self.left_panel)
        self.sidebar_sizes = [350, 0, 800]
        self.hidden_list_rail = QWidget()
        self.hidden_list_rail.setFixedWidth(36)
        rail = QVBoxLayout(self.hidden_list_rail)
        rail.setContentsMargins(0, 0, 0, 0)
        rail.addStretch()
        self.reveal_button = QPushButton(t('reveal_list_text'))
        self.reveal_button.setObjectName("sidebarReveal")
        self.reveal_button.setAccessibleName(t('reveal_list_accessible'))
        self.reveal_button.setToolTip(t('reveal_list_tooltip'))
        self.reveal_button.clicked.connect(self.toggle_list)
        rail.addWidget(self.reveal_button)
        rail.addStretch()
        self.splitter.addWidget(self.hidden_list_rail)
        self.hidden_list_rail.hide()
        self.player_container = QWidget()
        video_layout = QVBoxLayout(self.player_container)
        video_layout.setContentsMargins(8, 0, 0, 0)
        self.now = QLabel(t('select_content_prompt'))
        self.now.setWordWrap(True)
        video_layout.addWidget(self.now)
        self.video = VideoWidget()
        self.video.failed.connect(self.show_error)
        self.video.state_changed.connect(self.playback_state)
        video_layout.addWidget(self.video, 1)
        self.player_controls = QWidget()
        self.player_controls.setObjectName('playerControls')
        control_layout = QVBoxLayout(self.player_controls)
        control_layout.setContentsMargins(12, 10, 12, 10)
        control_layout.setSpacing(8)
        video_layout.addWidget(self.player_controls)
        self.timeline = QWidget()
        self.timeline.setObjectName("controlGroup")
        timeline_layout = QHBoxLayout(self.timeline)
        timeline_layout.setContentsMargins(0, 0, 0, 0)
        self.elapsed = QLabel('00:00')
        self.total_time = QLabel('00:00')
        self.seek_slider = TimelineSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.setAccessibleName(t('position_accessible'))
        self.seek_slider.committed.connect(self.seek_fraction)
        timeline_layout.addWidget(self.elapsed)
        timeline_layout.addWidget(self.seek_slider, 1)
        timeline_layout.addWidget(self.total_time)
        self.restart_button = QPushButton(t('from_start'))
        self.restart_button.clicked.connect(self.restart_content)
        timeline_layout.addWidget(self.restart_button)
        control_layout.addWidget(self.timeline)
        self.timeline.hide()
        self.seek_duration = 0
        self.video.clicked.connect(self.toggle_timeline)
        self.video.position_changed.connect(self.update_position)
        controls = QHBoxLayout()
        controls.setSpacing(6)
        self.pause_button = QPushButton(t('pause_button'))
        self.pause_button.setObjectName('primaryPlayback')
        self.pause_button.clicked.connect(self.video.toggle_pause)
        controls.addWidget(self.pause_button)
        for name, tip, function in [('■', t('stop_tooltip'), self.stop_playback),
                                    ('⛶', t('fullscreen_tooltip'), self.fullscreen)]:
            button = QPushButton(name)
            button.setObjectName('transportButton')
            button.setFixedSize(36, 34)
            button.setToolTip(tip)
            button.setAccessibleName(tip)
            button.clicked.connect(function)
            controls.addWidget(button)
        self.to_covers_button = QPushButton(t('to_covers_button'))
        self.to_covers_button.setToolTip(t('to_covers_tooltip'))
        self.to_covers_button.clicked.connect(self.show_covers_view)
        self.to_covers_button.hide()
        controls.addWidget(self.to_covers_button)
        controls.addStretch(1)
        self.live_button = QPushButton(t('catch_up_live'))
        self.live_button.setToolTip(t('catch_up_live_tooltip'))
        self.live_button.clicked.connect(self.catch_up_live)
        self.live_button.hide()
        volume_group = QWidget()
        volume_group.setObjectName("controlGroup")
        volume_layout = QHBoxLayout(volume_group)
        volume_layout.setContentsMargins(0, 0, 0, 0)
        volume_layout.setSpacing(6)
        volume = self.volume = QSlider(Qt.Orientation.Horizontal)
        volume.setRange(0, 100)
        volume.setValue(65)
        volume.setFixedWidth(100)
        volume.valueChanged.connect(self.video.set_volume)
        self.volume_percent = QLabel("65%")
        self.volume_percent.setFixedWidth(40)
        volume.valueChanged.connect(lambda value: self.volume_percent.setText(f"{value}%"))
        volume_layout.addWidget(QLabel(t('volume_label')))
        volume_layout.addWidget(volume)
        volume_layout.addWidget(self.volume_percent)
        controls.addWidget(volume_group)
        control_layout.addLayout(controls)
        self.quality = QLabel(t('no_playback'))
        self.quality.setObjectName("streamInfo")
        self.quality.setWordWrap(True)
        self.quality.setToolTip(t('quality_tooltip'))
        info_row = QHBoxLayout()
        info_row.addWidget(self.quality, 1)
        info_row.addWidget(self.live_button)
        control_layout.addLayout(info_row)
        tracks = QHBoxLayout()
        self.audio_tracks = QComboBox()
        self.subtitle_tracks = QComboBox()
        for label, box, kind in ((t('audio_label'), self.audio_tracks, "audio"),
                                 (t('subtitle_label'), self.subtitle_tracks, "sub")):
            box.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            box.setMinimumContentsLength(10)
            box.setMaximumWidth(400)
            box.activated.connect(lambda index, box=box, kind=kind:
                                  self.video.select_track(kind, box.itemData(index)))
            group = QWidget()
            group.setObjectName("controlGroup")
            pair = QVBoxLayout(group)
            pair.setContentsMargins(0, 0, 0, 0)
            pair.setSpacing(6)
            track_label_widget = QLabel(label.upper())
            track_label_widget.setObjectName("controlCaption")
            caption = QHBoxLayout()
            caption.addWidget(track_label_widget, 1)
            if kind == 'sub':
                self.sub_smaller = QPushButton('A−')
                self.sub_larger = QPushButton('A+')
                self.sub_size_label = QLabel('100%')
                for button, delta, tip in ((self.sub_smaller,-10,t('sub_smaller_tooltip')), (self.sub_larger,10,t('sub_larger_tooltip'))):
                    button.setObjectName('subtitleSize')
                    button.setFixedSize(28,24)
                    button.setToolTip(tip)
                    button.setAccessibleName(tip)
                    button.clicked.connect(lambda checked=False, delta=delta:self.adjust_subtitle_size(delta))
                caption.addWidget(self.sub_smaller)
                caption.addWidget(self.sub_size_label)
                caption.addWidget(self.sub_larger)
            pair.addLayout(caption)
            pair.addWidget(box, 1)
            tracks.addWidget(group, 1)
        control_layout.addLayout(tracks)
        self.video.media_changed.connect(self.update_media)
        self.sub_size_percent = 100
        if not demo:
            try:
                self.sub_size_percent = max(50,min(250,int(QSettings('Tecnomata','IPTV').value('subtitleSizePercent',100))))
            except (ValueError,TypeError):
                pass
        self.video.set_subtitle_scale(self.sub_size_percent/100)
        self.sub_size_label.setText(f'{self.sub_size_percent}%')
        self.update_media({})
        self.covers_container = QWidget()
        covers_layout = QVBoxLayout(self.covers_container)
        covers_layout.setContentsMargins(8, 0, 0, 0)
        covers_layout.setSpacing(8)

        covers_header = QHBoxLayout()
        covers_header.setSpacing(10)
        self.covers_header_label = QLabel(t('covers_header_all'))
        self.covers_header_label.setObjectName("listHeading")
        covers_header.addWidget(self.covers_header_label, 1)

        self.back_to_player_button = QPushButton(t('back_to_player'))
        self.back_to_player_button.setToolTip(t('back_to_player_tooltip'))
        self.back_to_player_button.clicked.connect(self.show_player_view)
        covers_header.addWidget(self.back_to_player_button)
        covers_layout.addLayout(covers_header)

        self.cover_grid = CoverGridView(self.cover_cache, lambda: getattr(self, 'theme_key', 'springfield'), parent=self.covers_container)
        self.cover_grid.poster_activated.connect(self.open_content_detail)
        covers_layout.addWidget(self.cover_grid, 1)

        self.right_stack = QStackedWidget()
        self.right_stack.addWidget(self.player_container)
        self.right_stack.addWidget(self.covers_container)

        self.splitter.addWidget(self.right_stack)
        self.splitter.setSizes([350, 0, 800])
        # Sin esto, un resize externo (tiling de Hyprland, snap a media pantalla en
        # ultrawide) reparte el ancho de forma impredecible: la lista puede no
        # ajustarse y los controles del reproductor quedan sin espacio y se recortan.
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setStretchFactor(2, 1)
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(2, False)
        self.left_panel.setMinimumWidth(280)
        self.left_panel.setMaximumWidth(480)
        self.right_stack.setMinimumWidth(480)
        self.setMinimumSize(280 + 480, 480)
        self.home = self.build_home()
        layout.addWidget(self.home, 1)
        layout.addWidget(self.splitter, 1)
        self.home.hide()
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.preload_status = QLabel()
        self.preload_status.setWordWrap(True)
        layout.addWidget(self.preload_status)
        self.account_note = QLabel()
        self.account_note.setWordWrap(True)
        layout.addWidget(self.account_note)
        self.escape = QShortcut(QKeySequence("Escape"), self)
        self.escape.activated.connect(self.exit_fullscreen)
        self.fkey = QShortcut(QKeySequence("F"), self)
        self.fkey.activated.connect(self.fullscreen)
        self.diagnostic_timer = QTimer(self)
        self.diagnostic_timer.timeout.connect(self.save_diagnostic)
        self.diagnostic_timer.start(1000)
        self.refresh_lists_combo()
        self.section("live")
        self.show_home()
        saved_theme = 'springfield' if demo else QSettings('Tecnomata', 'IPTV').value('theme', 'springfield')
        self.theme_selector.setCurrentIndex(max(0, self.theme_selector.findData(saved_theme)))
        self.change_theme()
        if self.library_error:
            self.account_note.setText(self.library_error)
        self.hide_list_key = QShortcut(QKeySequence("F4"), self)
        self.hide_list_key.activated.connect(self.toggle_list)
        self.search_key = QShortcut(QKeySequence("Ctrl+K"), self)
        self.search_key.activated.connect(self.focus_search)
        self.volume.valueChanged.connect(lambda _:self.publish_mpris())
        enable_mpris = mpris_enabled if mpris_enabled is not None else not demo
        if enable_mpris:
            self.mpris = MprisBridge(self)
            self.mpris.requested.connect(self.mpris_request)
            self.publish_mpris()
        if restore and not self.demo:
            QTimer.singleShot(0, self.restore_account)

    def refresh_lists_combo(self):
        if not self.library or not self.library_scope:
            return
        try:
            lists = self.library.lists(self.library_scope)
        except LibraryError as exc:
            self.show_error(str(exc))
            return
        current_id = self.lists_combo.currentData()
        self.lists_combo.blockSignals(True)
        self.lists_combo.clear()
        self.lists_combo.addItem(t('lists_combo_placeholder'), None)
        self.list_names = {}
        selected_index = 0
        for idx, item in enumerate(lists, start=1):
            self.list_names[item['list_id']] = item['name']
            label = f"{item['name']} ({item['count']})"
            self.lists_combo.addItem(label, item['list_id'])
            if item['list_id'] == current_id:
                selected_index = idx
        self.lists_combo.setCurrentIndex(selected_index)
        self.lists_combo.blockSignals(False)
        has_list = selected_index > 0
        self.rename_list_button.setEnabled(has_list)
        self.delete_list_button.setEnabled(has_list)

    def choose_list(self, index):
        list_id = self.lists_combo.itemData(index)
        has_list = bool(list_id)
        self.rename_list_button.setEnabled(has_list)
        self.delete_list_button.setEnabled(has_list)
        if not list_id:
            if isinstance(self.collection_view, tuple) and self.collection_view[0] == 'list':
                self.section(self.kind or 'live')
            return
        name = self.list_names.get(list_id, '')
        self.show_collection(('list', list_id, name))

    def create_list_dialog(self):
        if not self.library or not self.library_scope:
            return
        dialog = ListNameDialog(self, t('new_list_dialog_title'))
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        name = dialog.name_edit.text().strip()
        try:
            list_id = self.library.create_list(self.library_scope, name)
        except LibraryError as exc:
            self.show_error(str(exc))
            return
        self.refresh_lists_combo()
        index = self.lists_combo.findData(list_id)
        if index >= 0:
            self.lists_combo.setCurrentIndex(index)
        self.status.setText(t('list_created_status', name=name))

    def rename_list_dialog(self):
        list_id = self.lists_combo.currentData()
        if not list_id or not self.library or not self.library_scope:
            self.show_error(t('choose_list_first'))
            return
        current_name = self.list_names.get(list_id, '')
        dialog = ListNameDialog(self, t('rename_list_dialog_title'), current_name)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        new_name = dialog.name_edit.text().strip()
        try:
            self.library.rename_list(self.library_scope, list_id, new_name)
        except LibraryError as exc:
            self.show_error(str(exc))
            return
        self.refresh_lists_combo()
        index = self.lists_combo.findData(list_id)
        if index >= 0:
            self.lists_combo.setCurrentIndex(index)
        if isinstance(self.collection_view, tuple) and self.collection_view[0] == 'list':
            self.list_heading.setText(t('heading_list', name=new_name))
        self.status.setText(t('list_renamed_status', name=new_name))

    def delete_list_dialog(self):
        list_id = self.lists_combo.currentData()
        if not list_id or not self.library or not self.library_scope:
            self.show_error(t('choose_list_first'))
            return
        name = self.list_names.get(list_id, '')
        dialog = ConfirmDialog(self, t('delete_list_confirm_title'),
                               t('delete_list_confirm_text', name=name),
                               t('confirm_delete'))
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.library.delete_list(self.library_scope, list_id)
        except LibraryError as exc:
            self.show_error(str(exc))
            return
        self.refresh_lists_combo()
        self.section('live')
        self.status.setText(t('list_deleted_status', name=name))

    def open_list_membership(self, item):
        row = item.data(Qt.ItemDataRole.UserRole)
        if not row or not self.library or not self.library_scope:
            return
        name = row.get('name', '')
        try:
            all_lists = self.library.lists(self.library_scope)
            current_membership = self.library.list_membership(self.library_scope, 'live', row)
        except LibraryError as exc:
            self.show_error(str(exc))
            return

        def toggle(list_id, checked):
            try:
                self.library.set_list_membership(self.library_scope, list_id, 'live', row, member=checked)
                self.refresh_lists_combo()
                self.filter_rows()
            except LibraryError as exc:
                self.show_error(str(exc))

        def create_and_add(new_name):
            new_id = self.library.create_list(self.library_scope, new_name)
            self.library.set_list_membership(self.library_scope, new_id, 'live', row, member=True)
            self.refresh_lists_combo()
            self.filter_rows()
            return new_id

        dialog = ListMembershipDialog(self, all_lists, current_membership, toggle, create_and_add, name)
        dialog.exec()

    def build_home(self):
        home = QWidget()
        layout = QVBoxLayout(home)
        layout.setContentsMargins(8, 12, 8, 8)
        title = QLabel(t('tagline_springfield'))
        title.setObjectName("homeTitle")
        title.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.home_title = title
        heading = QHBoxLayout()
        heading.addWidget(title, 1)
        heading.addWidget(QLabel(t('theme_label')))
        self.theme_selector = QComboBox()
        for key, values in THEMES.items():
            self.theme_selector.addItem(values[0], key)
        self.theme_selector.setAccessibleName(t('theme_accessible'))
        self.theme_selector.currentIndexChanged.connect(self.change_theme)
        heading.addWidget(self.theme_selector)
        heading.addWidget(QLabel(t('language_label')))
        self.active_language = current_language()
        self.language_selector = QComboBox()
        for code, name in LANGUAGES.items():
            self.language_selector.addItem(name, code)
        self.language_selector.setAccessibleName(t('language_accessible'))
        self.language_selector.setCurrentIndex(max(0, self.language_selector.findData(current_language())))
        self.language_selector.currentIndexChanged.connect(self.change_language)
        heading.addWidget(self.language_selector)
        self.apply_language_button = QPushButton(t('apply_restart'))
        self.apply_language_button.setToolTip(t('apply_restart_tooltip'))
        self.apply_language_button.clicked.connect(self.restart_app)
        self.apply_language_button.hide()
        heading.addWidget(self.apply_language_button)
        layout.addLayout(heading)
        self.home_note = QLabel(t('home_note_default'))
        self.home_note.setWordWrap(True)
        self.home_note.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.home_note)
        grid = QGridLayout()
        self.home_grid = grid
        self.collection_layout_state = None
        grid.setSpacing(12)
        self.home_tiles = {}
        for column, (kind, name, object_name) in enumerate((('live', t('home_tile_live'), 'homeLive'),
                ('vod', t('home_tile_movies'), 'homeMovies'), ('series', t('home_tile_series'), 'homeSeries'))):
            button = HomeTile(name, {"live": "#0078d7", "vod": "#d83b01", "series": "#107c41"}[kind])
            button.setObjectName(object_name)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            button.clicked.connect(lambda checked=False, kind=kind: self.section(kind))
            grid.addWidget(button, 0, column)
            self.home_tiles[kind] = button
        self.home_favorites = HomeTile(t('heading_favorites'), "#876086")
        self.home_favorites.setObjectName("homeFavorites")
        self.home_favorites.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.home_favorites.clicked.connect(lambda: self.show_collection('favorites'))
        grid.addWidget(self.home_favorites, 1, 0)
        self.home_recent = HomeTile(t('last_played_title'), "#335778")
        self.home_recent.setObjectName("homeRecent")
        self.home_recent.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.home_recent.clicked.connect(lambda: self.show_collection('recent'))
        grid.addWidget(self.home_recent, 1, 1, 1, 2)
        for column in range(3):
            grid.setColumnStretch(column, (4, 3, 2)[column])
        for row in range(2):
            grid.setRowStretch(row, 1)
        layout.addLayout(grid, 1)
        for kind, tile in self.home_tiles.items():
            tile.set_example(illustration('springfield', kind))
        return home

    def show_home(self):
        if self.video.renderer and self.video.pending_url and self.playing_kind in self.home_tiles:
            from PySide6.QtGui import QPixmap
            tile = self.home_tiles[self.playing_kind]
            tile.preview = QPixmap.fromImage(self.video.grabFramebuffer())
            tile.preview_title = self.now.text()
        self.splitter.hide()
        self.list_button.hide()
        self.home_button.setChecked(True)
        self.player_button.setChecked(False)
        self.home.show()
        self.update_home()

    def show_player(self):
        if hasattr(self, 'home'):
            self.home.hide()
        self.splitter.show()
        self.list_button.show()
        self.home_button.setChecked(False)
        self.player_button.setChecked(True)

    def show_player_view(self):
        if hasattr(self, 'right_stack'):
            self.right_stack.setCurrentIndex(0)
            self.sync_to_covers_button()

    def show_covers_view(self):
        if hasattr(self, 'right_stack'):
            self.right_stack.setCurrentIndex(1)
            self.sync_to_covers_button()
            self.sync_back_to_player_button()

    def sync_to_covers_button(self):
        if hasattr(self, 'to_covers_button') and hasattr(self, 'right_stack'):
            in_player = self.right_stack.currentIndex() == 0
            is_vod_series = self.kind in ('vod', 'series') and not self.in_episodes
            self.to_covers_button.setVisible(in_player and is_vod_series)

    def sync_back_to_player_button(self):
        if hasattr(self, 'back_to_player_button'):
            if self.playback_status in ('Playing', 'Paused'):
                name = self.now.text().strip()
                if len(name) > 24:
                    name = name[:24] + "…"
                self.back_to_player_button.setText(f"◀ {t('back_to_player')} ({name})" if name else f"◀ {t('back_to_player')}")
            else:
                self.back_to_player_button.setText(t('back_to_player'))

    def toggle_list(self):
        self.set_list_visible(self.left_panel.isHidden())

    def set_list_visible(self, visible):
        if not visible and not self.left_panel.isHidden():
            sizes = self.splitter.sizes()
            if sizes[0] > 0:
                self.sidebar_sizes = sizes
        self.left_panel.setVisible(visible)
        self.hidden_list_rail.setVisible(not visible)
        self.list_button.setChecked(visible)
        if visible:
            self.splitter.setSizes(self.sidebar_sizes)
        else:
            self.splitter.setSizes([0, 36, max(1, sum(self.sidebar_sizes) - 36)])

    def focus_search(self):
        self.show_player()
        self.set_list_visible(True)
        self.search.setFocus()
        self.search.selectAll()

    def library_rows(self, view):
        if not self.library or not self.library_scope:
            return []
        try:
            if isinstance(view, tuple) and view[0] == 'list':
                return self.library.list_rows(self.library_scope, view[1])
            return self.library.rows(self.library_scope, view)
        except LibraryError as exc:
            self.show_error(str(exc))
            return []

    def clear_home_previews(self):
        for tile in self.home_tiles.values():
            tile.preview = None
            tile.preview_title = ""
            tile.update()

    def update_home(self):
        if not hasattr(self, 'home_tiles'):
            return
        labels = {'live': t('home_tile_live'), 'vod': t('home_tile_movies'), 'series': t('home_tile_series')}
        for kind, button in self.home_tiles.items():
            section = self.cache.sections.get(kind) if self.cache else None
            count = len(section.rows) if section else None
            if self.demo:
                count = 2 if kind == 'live' else 1
            button.setText(t('home_tile_available', labels=labels[kind], count=f"{count:,}") if count is not None
                           else t('home_tile_not_loaded', labels=labels[kind]))
        favorites = self.library_rows('favorites')
        recent = self.library_rows('recent')
        self.home_favorites.setText(t('home_favorites_saved', count=len(favorites)))
        self.home_favorites.setVisible(bool(favorites))
        self.home_recent.setVisible(bool(recent))
        self.home_grid.setRowStretch(1, 1 if favorites or recent else 0)
        state = (bool(favorites), bool(recent))
        if state != self.collection_layout_state:
            self.home_grid.removeWidget(self.home_favorites)
            self.home_grid.removeWidget(self.home_recent)
            self.home_grid.addWidget(self.home_favorites, 1, 0, 1, 3 if favorites and not recent else 1)
            self.home_grid.addWidget(self.home_recent, 1, 0 if recent and not favorites else 1,
                                     1, 3 if recent and not favorites else 2)
            self.collection_layout_state = state
        for tile, entries in ((self.home_favorites, favorites), (self.home_recent, recent)):
            if entries:
                kind = 'series' if entries[0]['_kind'] == 'episode' else entries[0]['_kind']
                tile.set_example(self.home_tiles[kind].example)
                tile.preview = self.home_tiles[kind].preview if self.home_tiles[kind].preview_title == str(entries[0]['name']) else None
                tile.preview_title = str(entries[0]['name'])
            else:
                tile.preview = None
                tile.set_example(None)
                tile.preview_title = ''
        name = str(recent[0]['name']) if recent else t('no_history_yet')
        self.home_recent.setText(t('home_recent_text', title=t('last_played_title'),
                                   name=name[:48] + '…' if len(name) > 48 else name))
        self.home_note.setText(t('demo_fictional_content') if self.demo else
            t('service_connected_note') if self.client else
            t('home_note_default'))

    def row_source(self, row):
        kind = row.get('_kind') or ('episode' if self.in_episodes else self.kind)
        parent = row.get('_parent', self.current_series_id if kind == 'episode' else '')
        name = row.get('_series_name', self.current_series_name if kind == 'episode' else '')
        return kind, parent or '', name or ''

    def favorite_for(self, row):
        if not self.library or not self.library_scope:
            return False
        kind, parent, _ = self.row_source(row)
        try:
            return self.library.is_favorite(self.library_scope, kind, row, parent)
        except LibraryError:
            return False

    def sync_favorite(self, *_args):
        self.items.viewport().update()

    def favorite_clicked(self, item):
        if self.foreground_jobs:
            return
        self.items.setCurrentItem(item)
        self.toggle_favorite()

    def change_theme(self, *_args):
        key = self.theme_selector.currentData()
        self.theme_key = key
        self.setStyleSheet(stylesheet(STYLE, key))
        self.theme_badge.theme = key
        self.theme_badge.update()
        self.home_title.setText(t(f'tagline_{key}'))
        for kind, tile in self.home_tiles.items():
            tile.monochrome = key == 'dog-eyes'
            tile.set_example(illustration(key, kind))
        for tile in (self.home_favorites, self.home_recent):
            tile.monochrome = key == 'dog-eyes'
        self.update_home()
        if not self.demo:
            QSettings('Tecnomata', 'IPTV').setValue('theme', key)

    def change_language(self, *_args):
        code = self.language_selector.currentData()
        set_language(code)
        changed = code != self.active_language
        self.apply_language_button.setVisible(changed)
        if changed:
            self.home_note.setText(t('restart_to_apply_language'))

    def restart_app(self):
        if not self.close():
            return  # closeEvent lo rechazó (hay una consulta en curso); reintentar luego.
        subprocess.Popen(sys.argv, close_fds=True, start_new_session=True)
        QApplication.instance().quit()

    def toggle_favorite_for_row(self, row):
        if not row or not self.library or not self.library_scope:
            return False
        kind, parent, series_name = self.row_source(row)
        try:
            self.library.toggle(self.library_scope, kind, row, parent, series_name)
            is_fav = self.favorite_for(row)
            if self.collection_view:
                self.rows = self.library_rows(self.collection_view)
            self.filter_rows()
            self.update_home()
            self.status.setText(t('favorite_added') if is_fav else t('favorite_removed'))
            return is_fav
        except LibraryError as exc:
            self.show_error(str(exc))
            return False

    def toggle_favorite(self):
        item = self.items.currentItem()
        if not item:
            return
        row = item.data(Qt.ItemDataRole.UserRole)
        identity = self.content_id(row)
        self.toggle_favorite_for_row(row)
        for index in range(self.items.count()):
            if self.content_id(self.items.item(index).data(Qt.ItemDataRole.UserRole)) == identity:
                self.items.setCurrentRow(index)
                break

    def show_collection(self, view):
        self.show_player()
        self.show_player_view()
        self.collection_view = view
        is_list = isinstance(view, tuple) and view[0] == 'list'
        name = view[2] if is_list else ''
        self.search.setPlaceholderText(t('search_list', name=name) if is_list else
                                       t('search_favorites') if view == "favorites" else t('search_recent'))
        self.in_episodes = False
        self.back.hide()
        for button in self.tabs.values():
            button.setChecked(False)
        self.favorites_button.setChecked(view == 'favorites')
        self.recent_button.setChecked(view == 'recent')
        self.scan_button.hide()
        if not is_list:
            self.lists_combo.blockSignals(True)
            self.lists_combo.setCurrentIndex(0)
            self.lists_combo.blockSignals(False)
        self.list_heading.setText(t('heading_list', name=name) if is_list else
                                  t('heading_favorites') if view == 'favorites' else t('heading_recent'))
        self.category.hidePopup()
        self.search.clear()
        self.sync_busy()
        self.set_rows(self.library_rows(view))
        if not self.rows:
            self.status.setText(t('list_empty_hint') if is_list else
                                t('favorites_empty_hint') if view == 'favorites' else t('recent_empty_hint'))

    def collection_details(self, row):
        kind, parent, _ = self.row_source(row)
        if not self.library or not self.library_scope:
            return row, None
        if kind == 'series':
            result = self.library.latest_episode(self.library_scope,row)
            return result if result else (row,None)
        return row, self.library.progress(self.library_scope,kind,row,parent)

    def collection_action(self, row, restart=False):
        if self.foreground_jobs:
            return
        if not self.client and not self.demo:
            self.show_error(t('connect_to_open'))
            return
        # Flush the playing episode before querying a series' latest checkpoint.
        self.save_progress(force=True)
        try:
            target, _ = self.collection_details(row)
        except LibraryError as exc:
            self.show_error(str(exc)); return
        if target.get('_kind') == 'series':
            self.open_library_row(target)
            return
        kind, parent, series_name = self.row_source(target)
        self.play_content(target,kind,parent,series_name,start_over=restart)
        # A series card remains chosen when it resumes its episode directly.
        if row.get('_kind') == 'series':
            self.choose_content(row)

    def refresh_collection_progress(self):
        if not self.collection_view:
            return
        for index in range(self.items.count()):
            item = self.items.item(index)
            widget = self.items.itemWidget(item)
            if isinstance(widget,CollectionRow):
                try:
                    row = item.data(Qt.ItemDataRole.UserRole)
                    target,saved = self.collection_details(row)
                    widget.set_progress(saved,target.get('name','') if row.get('_kind') == 'series' and saved else '')
                except LibraryError:
                    pass  # Preserve the last displayed checkpoint if storage becomes unavailable.

    def open_library_row(self, row):
        if not self.client and not self.demo:
            self.show_error(t('connect_to_open'))
            return
        kind = row['_kind']
        # Keep favorites/recent visible while changing channel or movie.
        if kind != 'series':
            self.play_content(row, kind, row.get('_parent', ''), row.get('_series_name', ''))
        else:
            self.section('series')
            item = QListWidgetItem(row['name'])
            item.setData(Qt.ItemDataRole.UserRole, row)
            self.activate(item)

    def save_progress(self, force=False, completed=False):
        if not self.progress_context or self.pending_resume or self.resume_target is not None or self.restoring_progress or self.progress_blocked:
            return
        if not completed and (not self.video.media_ready or not self.video.pending_url):
            return
        now = time.monotonic()
        if not force and now - self.last_checkpoint < 5:
            return
        info = dict(self.position_info)
        if self.video.engine and self.video.media_ready and not completed:
            try:
                info.update(position=self.video.engine.time_pos, duration=self.video.engine.duration)
            except Exception:
                return
        if info.get('duration') and info.get('position') is not None:
            self.progress_snapshot = info
        elif completed:
            info = self.progress_snapshot or {}
        if not info.get('duration') or info.get('position') is None:
            return
        try:
            self.library.save_progress(*self.progress_context, position=info['position'], duration=info['duration'],
                audio=track_choice(self.video.media_info,'audio'), subtitle=track_choice(self.video.media_info,'sub'),
                subtitle_size=self.sub_size_percent, completed=completed)
            self.last_checkpoint = now
            self.refresh_collection_progress()
        except LibraryError as exc:
            self.show_error(str(exc))

    def restore_progress(self, info):
        if self.resume_target is not None:
            if abs(info.get('position',0) - self.resume_target) < 1:
                self.resume_target = None
            elif time.monotonic() > self.resume_deadline:
                self.resume_target = None
                self.progress_blocked = True
                self.status.setText(t('resume_failed'))
            return
        if not self.pending_resume or not self.video.media_ready or not info.get('duration'):
            return
        saved = self.pending_resume
        self.pending_resume = None
        self.restoring_progress = True
        try:
            self.adjust_subtitle_size(saved['subtitle_size'] - self.sub_size_percent)
            for key, kind in (('audio','audio'),('subtitle','sub')):
                track = resolve_track(saved[key],self.video.media_info.get(kind,[]))
                if track is not None:
                    self.video.select_track(kind,track)
            if not saved['completed'] and saved['position'] > 0:
                target = min(saved['position'],info['duration'])
                self.resume_target = target
                self.resume_deadline = time.monotonic()+5
                if not info.get('seekable') or not self.video.seek_to(target):
                    self.resume_target = None
                    self.progress_blocked = True
                    self.status.setText(t('resume_not_supported'))
        finally:
            self.restoring_progress = False

    def restart_content(self):
        if self.playing_kind not in ('vod','series') or not self.video.seek_to(0):
            return
        self.pending_resume = None
        self.progress_blocked = False
        self.resume_target = 0
        self.resume_deadline = time.monotonic()+5

    def toggle_timeline(self):
        if self.playing_kind in ('vod', 'series') and self.video.pending_url:
            self.timeline.setVisible(self.timeline.isHidden())

    def update_position(self, info):
        self.position_info = dict(info)
        self.restore_progress(info)
        self.save_progress()
        self.publish_mpris()
        def stamp(value):
            value = max(0, int(value or 0))
            hours, remainder = divmod(value, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f'{hours}:{minutes:02}:{seconds:02}' if hours else f'{minutes:02}:{seconds:02}'
        self.seek_duration = info.get('duration', 0) or 0
        self.seek_slider.setEnabled(bool(info.get('seekable') and self.seek_duration > 0 and self.playing_kind in ('vod','series')))
        self.restart_button.setEnabled(self.seek_slider.isEnabled())
        self.seek_slider.setToolTip(t('seek_tooltip') if self.seek_slider.isEnabled() else t('seek_disabled_tooltip'))
        self.elapsed.setText(stamp(info.get('position', 0)))
        self.total_time.setText(stamp(self.seek_duration))
        if not self.seek_slider.isSliderDown():
            self.seek_slider.setValue(round(1000 * info.get('position', 0) / self.seek_duration) if self.seek_duration else 0)
        if not info:
            self.timeline.hide()

    def seek_fraction(self, value):
        if self.playing_kind in ('vod', 'series') and self.seek_slider.isEnabled():
            self.video.seek_to(self.seek_duration * value / 1000)

    def publish_mpris(self):
        if not self.mpris:
            return
        active = bool(self.video.pending_url and self.video.diagnostic.get('state') in ('loading','playing','paused'))
        self.mpris.publish(title=self.now.text() if active else '', state=self.playback_status if active else 'Stopped',
            position=self.position_info.get('position',0), duration=self.position_info.get('duration',0),
            seekable=active and self.playing_kind in ('vod','series') and self.position_info.get('seekable',False) and self.position_info.get('duration',0)>0,
            volume=self.volume.value()/100, track=self.mpris_track)

    def mpris_request(self, operation, value):
        if operation == 'raise':
            self.showNormal(); self.raise_(); self.activateWindow()
        elif operation == 'stop':
            self.stop_playback()
        elif operation == 'volume':
            self.volume.setValue(round(value*100))
        elif operation == 'seek' and self.playing_kind in ('vod','series'):
            self.video.seek_to(value)
        elif operation in ('toggle','pause','play') and self.video.pending_url and self.video.engine:
            if operation == 'toggle': self.video.toggle_pause()
            else: self.video.engine.pause = operation == 'pause'

    def adjust_subtitle_size(self, delta):
        self.sub_size_percent = max(50,min(250,self.sub_size_percent+delta))
        self.video.set_subtitle_scale(self.sub_size_percent/100)
        self.sub_size_label.setText(f'{self.sub_size_percent}%')
        if not self.demo:
            QSettings('Tecnomata','IPTV').setValue('subtitleSizePercent',self.sub_size_percent)
        self.save_progress(force=True)

    def playback_state(self, code):
        if code == 'paused':
            self.save_progress(force=True)
        elif code == 'ended':
            self.save_progress(force=True, completed=True)
            self.progress_context = None
        self.playback_status = 'Paused' if code == 'paused' else 'Playing' if code == 'playing' else 'Stopped'
        self.publish_mpris()
        self.sync_back_to_player_button()
        self.pause_button.setText(t('resume_button') if code == 'paused' else t('pause_button'))
        self.status.setText(t(f'status_{code}'))
        if code == 'playing' and self.pending_history:
            kind, row, parent, series_name = self.pending_history
            self.pending_history = None
            if self.library and self.library_scope:
                try:
                    self.library.played(self.library_scope, kind, row, parent, series_name)
                    self.update_home()
                    if self.collection_view == 'recent':
                        self.set_rows(self.library_rows('recent'))
                except LibraryError as exc:
                    self.show_error(str(exc))

    def stop_playback(self):
        self.save_progress(force=True)
        self.progress_context = None
        self.pending_resume = None
        self.resume_target = None
        self.pending_history = None
        self.video.stop()
        self.playing_kind = None
        self.live_button.hide()
        self.now.setText(t('select_content_prompt'))

    def catch_up_live(self):
        # Use the playing source, not the tab being browsed or highlighted row.
        if self.playing_kind == "live" and self.video.pending_url:
            self.video.reconnect_current()

    def update_media(self, info):
        for button in (self.sub_smaller,self.sub_larger):
            button.setEnabled(bool(info.get("sub")))
        self.quality.setText(describe_video(info))
        for kind, box, selected in (("audio", self.audio_tracks, "aid"),
                                    ("sub", self.subtitle_tracks, "sid")):
            box.blockSignals(True)
            box.clear()
            rows = info.get(kind, [])
            if kind == "sub":
                box.addItem(t('track_disabled') if rows else t('track_unavailable_plural'), "no")
            elif not rows:
                box.addItem(t('track_unavailable'), None)
            for track in rows:
                box.addItem(track_label(track), track["id"])
            index = box.findData(info.get(selected))
            box.setCurrentIndex(max(0, index))
            box.setEnabled(bool(rows))
            box.setToolTip(box.currentText())
            box.blockSignals(False)

        self.save_progress(force=True)

    def sync_busy(self):
        # Preloading must not lock browsing or playback of loaded sections.
        foreground = bool(self.foreground_jobs)
        for widget in (self.navigation, self.items, self.back, self.favorites_button, self.recent_button,
                       self.home, self.lists_combo, self.new_list_button):
            widget.setEnabled(not foreground)
        self.category.setEnabled(not foreground and not self.in_episodes and not self.collection_view)
        self.connect_button.setEnabled(not self.jobs)
        self.forget_button.setEnabled(not self.jobs)
        self.refresh_button.setEnabled(self.client is not None and not self.jobs)
        self.scan_button.setEnabled(self.client is not None and not foreground)
        self.sync_favorite()

    def submit(self, function, callback, background=False, on_error=None):
        job = Job(function)
        self.jobs.add(job)
        if not background:
            self.foreground_jobs.add(job)
            self.status.setText(t('loading'))
        self.sync_busy()
        def finish(result=None, error=None):
            self.jobs.discard(job)
            self.foreground_jobs.discard(job)
            self.sync_busy()
            if error:
                (on_error or self.show_error)(error)
            else:
                if not background:
                    self.status.setText("")
                callback(result)
        job.signals.done.connect(lambda result: finish(result))
        job.signals.error.connect(lambda message: finish(error=message))
        self.pool.start(job)

    def show_error(self, message):
        self.status.setText(message)
        self.publish_mpris()

    def save_diagnostic(self):
        # Strictly whitelisted engine state: no account, URLs, names or raw logs.
        path = Path(__file__).resolve().parents[2] / "runtime/playback-status.json"
        data = {key: value for key, value in self.video.diagnostic.items()
                if key in ("state", "failure", "http_status")}
        data.update({"engine_initialized": self.video.engine is not None,
                     "renderer_initialized": self.video.renderer is not None,
                     "closed": self.video.closed, "frames": self.video.frames})
        try:
            path.parent.mkdir(exist_ok=True)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as output:
                json.dump(data, output)
        except OSError:
            pass

    def login(self):
        dialog = Login(self, self.client.account if self.client else self.saved_account)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        account = dialog.account
        remember = dialog.remember.isChecked()
        dialog.password.clear()
        dialog.deleteLater()
        self.connect_account(account, remember, update_store=True)

    def restore_account(self):
        def loaded(account):
            if account:
                self.saved_account = account
                self.forget_button.show()
                self.connect_account(account, True)
        self.submit(self.account_store.load, loaded,
                    on_error=lambda message: self.account_note.setText(message))

    def connect_account(self, account, remember=True, update_store=False):
        client = XtreamClient(account)
        def connect():
            try:
                client.authenticate()
                note = t('account_remembered') if remember else t('account_session_only')
                remembered = remember
                forget_failed = False
                if update_store:
                    try:
                        if remember:
                            self.account_store.save(account)
                        else:
                            self.account_store.forget()
                    except StorageError as exc:
                        note = str(exc)
                        remembered = False
                        forget_failed = not remember
                return client, note, remembered, forget_failed
            except Exception:
                client.close()
                raise
        def connected(result):
            was_home = not self.home.isHidden()
            new_client, note, remembered, forget_failed = result
            self.stop_playback()
            if self.client:
                self.client.close()
            self.client = new_client
            self.cache = CatalogCache(new_client)
            self.library_scope = account_scope(account)
            self.saved_account = account if remembered else None
            self.account_note.setText(note)
            self.forget_button.setVisible(remembered or forget_failed)
            self.failed_sections.clear()
            self.category_choices.clear()
            self.chosen.clear()
            self.clear_home_previews()
            self.demo = False
            self.connect_button.setText(t('change_service'))
            self.refresh_lists_combo()
            self.section(self.kind)
            self.update_home()
            if was_home:
                self.show_home()
        self.submit(connect, connected)

    def forget_account(self):
        def forgotten(_):
            self.stop_playback()
            if self.client:
                self.client.close()
            self.client = None
            self.cache = None
            self.saved_account = None
            self.library_scope = None
            self.failed_sections.clear()
            self.category_choices.clear()
            self.chosen.clear()
            self.clear_home_previews()
            self.forget_button.hide()
            self.account_note.setText(t('account_forgotten'))
            self.connect_button.setText(t('connect_service'))
            self.preload_status.clear()
            self.refresh_lists_combo()
            self.section("live")
            self.update_home()
            self.sync_busy()
        self.submit(self.account_store.forget, forgotten)

    def refresh_catalogs(self):
        if self.client and not self.jobs:
            self.cache = CatalogCache(self.client)
            self.failed_sections.clear()
            self.refresh_lists_combo()
            self.section(self.kind)

    def current_scan_context(self):
        query = self.search.text().strip()
        if query:
            return query
        category = self.category.currentData()
        if category is not None:
            return self.category.currentText()
        return None

    def toggle_quality_scan(self):
        if self.scan_active:
            self.cancel_quality_scan()
        else:
            self.start_quality_scan()

    def start_quality_scan(self):
        if not self.client or self.foreground_jobs or self.scan_active:
            if not self.client:
                self.show_error(t('scan_requires_connection'))
            return
        context = self.current_scan_context()
        if not context:
            self.show_error(t('scan_all_channels_forbidden'))
            return
        rows = list(self.visible_rows)
        if not rows:
            self.show_error(t('scan_no_channels'))
            return
        dialog = ConfirmDialog(self, t('scan_confirm_title'),
                               t('scan_confirm_text', count=len(rows)), t('scan_confirm_button'))
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.scan_active = True
        self.scan_cancel_requested = False
        self.scan_queue = rows
        self.scan_total = len(rows)
        self.scan_tally = {'sd': [], 'hd': [], 'fullhd': [], 'unknown': 0}
        self.scan_context_label = context
        self.scan_button.setText(t('scan_cancel_button'))
        self.status.setText(t('scan_progress', done=0, total=self.scan_total))
        self.scan_next()

    def cancel_quality_scan(self):
        self.scan_cancel_requested = True

    def scan_next(self):
        if self.scan_cancel_requested or not self.scan_queue or not self.client:
            self.finish_quality_scan(cancelled=self.scan_cancel_requested or not self.client)
            return
        row = self.scan_queue.pop(0)
        try:
            url = self.client.stream_url('live', row.get('stream_id'), row.get('container_extension'))
        except ServiceError:
            url = None

        def probe():
            return probe_stream(url) if url else (None, None, None)

        def done(result):
            width, height, tier = result
            if tier and self.library and self.library_scope:
                try:
                    self.library.save_quality(self.library_scope, 'live', row, tier, width, height)
                except LibraryError as exc:
                    self.show_error(str(exc))
            if tier:
                self.scan_tally[tier].append(row)
            else:
                self.scan_tally['unknown'] += 1
            done_count = self.scan_total - len(self.scan_queue)
            self.status.setText(t('scan_progress', done=done_count, total=self.scan_total))
            self.filter_rows()
            self.scan_next()

        self.submit(probe, done, background=True, on_error=lambda _msg: done((None, None, None)))

    def finish_quality_scan(self, cancelled=False):
        self.scan_active = False
        self.scan_button.setText(t('scan_quality_button'))
        done_count = self.scan_total - len(self.scan_queue)
        if cancelled:
            self.status.setText(t('scan_cancelled', done=done_count, total=self.scan_total))
            return
        created = []
        if self.library and self.library_scope:
            for tier in TIERS:
                tier_rows = self.scan_tally.get(tier) or []
                if not tier_rows:
                    continue
                context_name = f"{self.scan_context_label} · {t(f'quality_tier_{tier}')}"
                tier_name = t(f'quality_tier_{tier}')
                try:
                    context_list_id = (self.library.list_by_name(self.library_scope, context_name)
                                        or self.library.create_list(self.library_scope, context_name))
                    self.library.replace_list_members(self.library_scope, context_list_id,
                                                       [('live', tier_row, '') for tier_row in tier_rows])
                    created.append(context_name)
                    # A running "all channels seen as HD/SD/Full HD" list, across every search scanned so far.
                    tier_list_id = (self.library.list_by_name(self.library_scope, tier_name)
                                     or self.library.create_list(self.library_scope, tier_name))
                    for tier_row in tier_rows:
                        for other in TIERS:
                            if other == tier:
                                continue
                            other_id = self.library.list_by_name(self.library_scope, t(f'quality_tier_{other}'))
                            if other_id:
                                self.library.set_list_membership(self.library_scope, other_id, 'live', tier_row, member=False)
                        self.library.set_list_membership(self.library_scope, tier_list_id, 'live', tier_row, member=True)
                except LibraryError as exc:
                    self.show_error(str(exc))
            self.refresh_lists_combo()
        summary = t('scan_done', total=done_count, fullhd=len(self.scan_tally['fullhd']),
                   hd=len(self.scan_tally['hd']), sd=len(self.scan_tally['sd']), unknown=self.scan_tally['unknown'])
        if created:
            summary += t('scan_lists_updated', names=', '.join(created))
        self.status.setText(summary)

    def preload_next(self):
        if not self.cache or self.pending_section:
            return
        pending = [kind for kind in dict.fromkeys((self.kind, *KINDS))
                   if kind not in self.cache.sections and kind not in self.failed_sections]
        if not pending:
            self.preload_status.setText(t('lists_preloaded') if not self.failed_sections else
                                        t('some_list_failed_preload'))
            return
        kind = pending[0]
        self.pending_section = kind
        labels = {"live": t('preloading_live'), "vod": t('preloading_vod'), "series": t('preloading_series')}
        self.preload_status.setText(t('preloading_status', label=labels[kind]))
        def loaded(section):
            self.pending_section = None
            if self.kind == kind and not self.in_episodes and not self.collection_view:
                self.display_section(section)
            self.update_home()
            self.preload_next()
        def failed(message):
            self.pending_section = None
            self.failed_sections.add(kind)
            if self.kind == kind:
                self.show_error(message)
            self.preload_next()
        cache = self.cache
        self.submit(lambda: cache.section(kind), loaded, background=True, on_error=failed)

    def display_section(self, section):
        selected = self.category_choices.get(self.kind)
        self.category.blockSignals(True)
        self.category.clear()
        self.category.addItem(t('all_categories'), None)
        for row in section.categories:
            self.category.addItem(str(row.get("category_name", t('unnamed_category'))), row.get("category_id"))
        index = self.category.findData(selected)
        self.category.setCurrentIndex(max(0, index))
        self.category.blockSignals(False)
        self.set_rows(section.filtered(self.category.currentData()))

    def section(self, kind):
        self.collection_view = None
        self.favorites_button.setChecked(False)
        self.recent_button.setChecked(False)
        self.lists_combo.blockSignals(True)
        self.lists_combo.setCurrentIndex(0)
        self.lists_combo.blockSignals(False)
        self.scan_button.setVisible(kind == 'live')
        self.list_heading.setText({'live': t('heading_live'), 'vod': t('heading_vod'), 'series': t('heading_series')}[kind])
        self.show_player()
        self.kind = kind
        if kind in ('vod', 'series') and self.playback_status == 'Stopped':
            self.show_covers_view()
        else:
            self.show_player_view()
        self.search.setPlaceholderText({"live": t('search_channel'), "vod": t('search_movie'), "series": t('search_series')}[kind])
        self.in_episodes = False
        self.sync_busy()
        self.back.hide()
        self.search.clear()
        for key, button in self.tabs.items():
            button.setChecked(key == kind)
        self.category.blockSignals(True)
        self.category.clear()
        self.category.addItem(t('all_categories'), None)
        self.category.blockSignals(False)
        self.rows = []
        self.filter_rows()
        if self.demo:
            labels = {"live": ["Canal de prueba A", "Canal de prueba B"],
                      "vod": ["Película de prueba"], "series": ["Serie de prueba"]}
            self.rows = [{"name": name, "stream_id": index + 1,
                          "series_id": index + 1} for index, name in enumerate(labels[kind])]
            self.filter_rows()
            self.status.setText(t('demo_catalog_msg'))
        elif self.client:
            if kind in self.cache.sections:
                self.display_section(self.cache.sections[kind])
            else:
                self.status.setText(t('failed_load_list')
                                    if kind in self.failed_sections else t('list_preloading'))
            self.preload_next()
        else:
            self.status.setText(t('connect_prompt_long'))

    def load_catalog(self):
        if not self.client or self.in_episodes or self.collection_view:
            return
        category = self.category.currentData()
        self.category_choices[self.kind] = category
        if self.kind in self.cache.sections:
            self.set_rows(self.cache.sections[self.kind].filtered(category))

    def set_rows(self, rows):
        self.rows = rows
        self.filter_rows()
        self.status.setText(t('items_count_hint', count=len(rows)))

    def content_context(self):
        if self.collection_view:
            return self.collection_view
        return ("episodes", self.current_series_id) if self.in_episodes else self.kind

    def content_id(self, row):
        if self.collection_view:
            kind = row.get('_kind', self.kind)
            identity = row.get('series_id') if kind == 'series' else row.get('stream_id')
            return (kind, str(identity), str(row.get('_parent', '')))
        key = "series_id" if self.kind == "series" and not self.in_episodes else "stream_id"
        return str(row.get(key))

    def choose_content(self, row):
        self.chosen[self.content_context()] = self.content_id(row)
        for index in range(self.items.count()):
            item = self.items.item(index)
            selected = self.content_id(item.data(Qt.ItemDataRole.UserRole)) == self.content_id(row)
            item.setData(CHOSEN_ROLE, selected)
            item.setToolTip(t('chosen_tooltip') if selected else item.text())
            widget = self.items.itemWidget(item)
            if isinstance(widget,CollectionRow):
                widget.set_chosen(selected)
            if selected:
                self.items.setCurrentItem(item)

    def filter_rows(self):
        collection = bool(self.collection_view)
        if self.items.property('collection') != collection:
            self.items.setProperty('collection',collection)
            self.items.style().unpolish(self.items)
            self.items.style().polish(self.items)
        query = self.search.text().casefold().strip()
        self.items.blockSignals(True)
        self.items.clear()
        chosen_item = None
        visible_rows = []
        favorites = {(entry['_kind'], str(entry.get('series_id') if entry['_kind'] == 'series' else entry.get('stream_id')), entry['_parent'])
                     for entry in self.library_rows('favorites')}
        membership_map, quality_map = {}, {}
        if self.library and self.library_scope:
            try:
                membership_map = self.library.list_membership_map(self.library_scope, 'live')
                quality_map = self.library.quality_map(self.library_scope, 'live')
            except LibraryError as exc:
                self.show_error(str(exc))
        for row in self.rows:
            name = str(row.get("name", t('unnamed_category')))
            if query in name.casefold():
                source, parent, series_name = self.row_source(row)
                visible_rows.append(row)
                favorite = (source, str(row.get("series_id") if source == "series" else row.get("stream_id")), str(parent)) in favorites
                live = source == 'live'
                identity = str(row.get('stream_id')) if live else None
                tier = quality_map.get(identity) if live else None
                label = (t(f'quality_badge_{tier}') if tier else '') + ('★ ' if favorite else '☆ ') + name
                if self.collection_view:
                    prefix = {'live':t('prefix_live'), 'vod':t('prefix_vod'), 'series':t('prefix_series'), 'episode':t('prefix_episode')}[source]
                    if source == 'episode' and series_name:
                        label = f'{series_name} · {label}'
                    label = f'{prefix} · {label}'
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, row)
                selected = self.chosen.get(self.content_context()) == self.content_id(row)
                item.setData(CHOSEN_ROLE, selected)
                item.setData(FAVORITE_ROLE, favorite)
                if live:
                    item.setData(LIVE_ROLE, True)
                    item.setData(IN_LIST_ROLE, identity in membership_map)
                item.setToolTip(t('chosen_tooltip') if selected else name)
                self.items.addItem(item)
                if self.collection_view:
                    item.setSizeHint(QSize(250,34))
                if self.collection_view and source in ('vod','episode','series'):
                    item.setData(COLLECTION_ROLE,True)
                    title = label.replace('★ ','').replace('☆ ','')
                    widget = CollectionRow(title,favorite,source == 'series')
                    try:
                        target, saved = self.collection_details(row)
                        widget.set_progress(saved,target.get('name','') if source == 'series' and saved else '')
                    except LibraryError as exc:
                        self.show_error(str(exc))
                    widget.set_chosen(selected)
                    widget.star.clicked.connect(lambda checked=False, item=item: self.favorite_clicked(item))
                    widget.continue_button.clicked.connect(lambda checked=False, row=row: self.collection_action(row))
                    widget.restart_button.clicked.connect(lambda checked=False, row=row: self.collection_action(row,restart=True))
                    item.setSizeHint(widget.sizeHint())
                    self.items.setItemWidget(item,widget)
                if selected:
                    chosen_item = item
        if chosen_item:
            self.items.setCurrentItem(chosen_item)
        self.items.blockSignals(False)
        self.visible_rows = visible_rows
        self.sync_favorite()
        self.update_cover_grid(visible_rows)

    def update_cover_grid(self, rows):
        if not hasattr(self, 'cover_grid'):
            return
        self.cover_grid.blockSignals(True)
        self.cover_grid.clear()
        if self.kind in ('vod', 'series') and not self.in_episodes:
            for row in rows:
                item = QListWidgetItem()
                item.setData(Qt.ItemDataRole.UserRole, row)
                self.cover_grid.addItem(item)
            cat_name = self.category.currentText()
            heading = self.list_heading.text()
            if cat_name and cat_name != t('all_categories'):
                self.covers_header_label.setText(f"{heading} · {cat_name} ({len(rows)})")
            else:
                self.covers_header_label.setText(f"{heading} ({len(rows)})")
        else:
            self.covers_header_label.setText(f"{self.list_heading.text()} ({len(rows)})")
        self.cover_grid.blockSignals(False)

    def open_series(self, row):
        def loaded(episodes):
            self.choose_content(row)
            self.current_series_id = str(row.get("series_id"))
            self.current_series_name = str(row.get("name", ""))
            self.in_episodes = True
            self.search.setPlaceholderText(t('search_episode'))
            self.sync_busy()
            self.back.show()
            self.search.clear()
            self.set_rows(episodes)
            self.show_player_view()

        if self.demo:
            loaded([{"name": "T1 · E1 · Episodio de prueba", "stream_id": 1}])
        else:
            series_id = row.get("series_id")
            if str(series_id) in self.cache.episode_lists:
                loaded(self.cache.episode_lists[str(series_id)])
            else:
                cache = self.cache
                self.submit(lambda: cache.episodes(series_id), loaded)

    def open_content_detail(self, row):
        if not row:
            return
        source, parent, series_name = self.row_source(row)
        favorites = {(entry['_kind'], str(entry.get('series_id') if entry['_kind'] == 'series' else entry.get('stream_id')), str(entry['_parent']))
                     for entry in self.library_rows('favorites')}
        target_id = str(row.get('series_id') if self.kind == 'series' else row.get('stream_id'))
        is_fav = (self.kind, target_id, str(parent)) in favorites

        progress_data = None
        if self.library and self.library_scope and self.kind in ('vod', 'series'):
            try:
                if self.kind == 'vod':
                    progress_data = self.library.progress(self.library_scope, 'vod', row, parent)
                elif self.kind == 'series':
                    target, saved = self.collection_details(row)
                    progress_data = saved
            except Exception:
                progress_data = None

        def on_play(restart=False):
            self.show_player_view()
            if self.kind == 'series':
                try:
                    target, saved = self.collection_details(row)
                    if target:
                        self.play_content(target, 'episode', str(row.get('series_id')), str(row.get('name', '')), start_over=restart)
                        return
                except Exception:
                    pass
                self.open_series(row)
            else:
                self.play_content(row, 'vod', parent, series_name, start_over=restart)

        def on_episodes():
            self.open_series(row)

        def on_toggle_favorite():
            return self.toggle_favorite_for_row(row)

        theme = getattr(self, 'theme_key', 'springfield')
        dialog = ContentDetailDialog(
            parent=self,
            row=row,
            kind=self.kind,
            cover_cache=self.cover_cache,
            theme_key=theme,
            progress_data=progress_data,
            is_fav=is_fav,
            on_play=on_play,
            on_restart=lambda: on_play(restart=True),
            on_toggle_favorite=on_toggle_favorite,
            on_episodes=on_episodes,
        )
        dialog.exec()

    def activate(self, item):
        row = item.data(Qt.ItemDataRole.UserRole)
        if self.collection_view:
            self.open_library_row(row)
            return
        if self.kind == "series" and not self.in_episodes:
            self.open_series(row)
            return
        source, parent, series_name = self.row_source(row)
        self.play_content(row, source, parent, series_name)

    def play_content(self, row, source, parent='', series_name='', start_over=False):
        self.show_player_view()
        play_kind = 'series' if source == 'episode' else source
        if self.demo:
            index = int(row.get("stream_id", 1)) - 1
            if not self.demo_files:
                self.status.setText(t('demo_only_msg'))
                return
            url = str(Path(self.demo_files[index % len(self.demo_files)]).resolve())
        else:
            try:
                url = self.client.stream_url(play_kind, row.get("stream_id"), row.get("container_extension"))
            except ServiceError as exc:
                self.show_error(str(exc))
                return
        self.save_progress(force=True)
        self.progress_context = (self.library_scope, source, dict(row), parent) if source in ('vod','episode') and self.library and self.library_scope else None
        self.pending_resume = None
        self.resume_target = None
        self.progress_blocked = False
        self.progress_snapshot = None
        self.last_checkpoint = 0
        if self.progress_context:
            try:
                self.pending_resume = self.library.progress(*self.progress_context)
                if start_over and self.pending_resume:
                    self.pending_resume = dict(self.pending_resume, position=0, completed=False)
            except LibraryError as exc:
                self.progress_blocked = True
                self.show_error(str(exc))
        self.choose_content(row)
        self.now.setText(str(row.get("name", t('status_playing'))))
        self.timeline.hide()
        self.playing_kind = play_kind
        self.live_button.setVisible(self.playing_kind == "live")
        self.pending_history = (source, dict(row), parent, series_name)
        self.mpris_track += 1
        self.video.play(url)

    def fullscreen(self):
        if self.isFullScreen():
            self.exit_fullscreen()
        else:
            self.showFullScreen()

    def exit_fullscreen(self):
        self.showNormal()

    def closeEvent(self, event):
        if self.jobs:
            self.status.setText(t('wait_query_close'))
            event.ignore()
            return
        self.save_progress(force=True)
        if self.mpris:
            self.mpris.close()
        self.video.dispose()
        if self.client:
            self.client.close()
        if self.library:
            self.library.close()
        event.accept()


STYLE = """
QWidget#collectionRow { background: #17263d; border-bottom: 1px solid #314660; }
QWidget#collectionRow[chosen="true"] { border-left: 3px solid #ffda45; background: #20334f; }
QWidget#collectionRow QLabel { background: transparent; }
QLabel#collectionStatus { font-size: 10px; color: #bac8dc; }
QPushButton#collectionAction { font-size: 11px; padding: 2px 5px; min-height: 18px; }
QWidget#collectionRow QProgressBar { border: none; background: #314660; border-radius: 2px; }
QWidget#collectionRow QProgressBar::chunk { background: #ffda45; border-radius: 2px; }
QWidget#playerControls { background: #17263d; border: 1px solid #314660; border-radius: 12px; }
QWidget#controlGroup, QWidget#playerControls QLabel { background: transparent; }
QWidget#playerControls QComboBox { background: #0c0e14; }
QLabel#controlCaption { color: #bac8dc; font-size: 10px; font-weight: bold; }
QPushButton#primaryPlayback { background: #ffda45; color: #16243a; font-weight: bold; min-width: 90px; }
QPushButton#subtitleSize { padding: 0px; font-size: 11px; min-height: 0px; }
QPushButton#transportButton { padding: 0px; font-size: 18px; }
QSlider::groove:horizontal { height: 4px; background: #314660; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #ffda45; border-radius: 2px; }
QSlider::handle:horizontal { background: #e2e7f0; width: 10px; margin: -4px 0px; border-radius: 5px; }
QWidget { background: #111d30; color: #e2e7f0; font-size: 14px; }
QLabel#brand { color: #ffda45; font-size: 18px; font-weight: bold; }
QFrame#categoryPopup { background: #17263d; border: 1px solid #ffda45; border-radius: 8px; }
QWidget#sidebar { background: #17263d; border: 1px solid #314660; border-radius: 12px; }
QLabel#listHeading { color: #e2e7f0; font-weight: bold; padding: 4px; }
QPushButton { background: #20334f; border: 1px solid #3b536e; border-radius: 8px; padding: 7px 10px; min-height: 16px; }
QPushButton:hover { background: #2c4260; border-color: #f6cc3b; }
QPushButton:checked { background: #ffda45; border-color: #ffda45; color: #16243a; }
QPushButton:disabled { color: #738197; }
QLineEdit, QComboBox { background: #0c0e14; border: 1px solid #2d3748; border-radius: 8px; padding: 7px; }
QLineEdit:focus, QComboBox:focus { border-color: #00e5ff; }
QListWidget { background: #17263d; border: none; }
QListWidget::item { padding: 8px 10px; border-bottom: 1px solid #222838; }
QListWidget::item:selected { background: #1f344b; }
QListWidget[collection="true"]::item { padding: 0px; border: none; }
QLabel#streamInfo { color: #00e5ff; font-size: 12px; font-family: 'JetBrains Mono'; }
QPushButton#homeLive { background: #0078d7; font-size: 22px; text-align: left; padding: 24px; border: none; }
QPushButton#homeMovies { background: #d83b01; font-size: 22px; text-align: left; padding: 24px; border: none; }
QPushButton#homeSeries { background: #107c41; font-size: 22px; text-align: left; padding: 24px; border: none; }
QPushButton#homeFavorites { background: #007f76; font-size: 20px; text-align: left; padding: 20px; border: none; }
QPushButton#homeRecent { background: #161b26; font-size: 20px; text-align: left; padding: 20px; border: 1px solid #2d3748; }
QLabel#homeTitle { font-size: 28px; font-weight: 600; color: #ffe681; }
QWidget#topNav { background: #1e3049; border: 1px solid #3b536e; border-radius: 16px; }
QWidget#topNav QPushButton { border: none; border-radius: 12px; padding: 7px 16px; background: transparent; color: #bac8dc; }
QWidget#topNav QPushButton:hover { background: #2b415d; color: white; }
QWidget#topNav QPushButton:checked { background: #ffda45; color: #17263d; font-weight: bold; }
QPushButton#listToggle { border-radius: 15px; font-size: 18px; padding: 3px 10px; }
QPushButton#sidebarReveal { background: #ffda45; color: #17263d; font-size: 11px; font-weight: bold; padding: 4px 0px; border-radius: 8px; min-height: 64px; border: none; }
QPushButton#sidebarReveal:hover { background: #ffe787; }
QScrollBar:vertical { background: #11141d; width: 8px; margin: 0px; }
QScrollBar::handle:vertical { background: #0078d7; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
"""


def configure_appearance(app):
    for font_path in (Path(__file__).parent / 'assets/fonts').glob('*.ttf'):
        QFontDatabase.addApplicationFont(str(font_path))
    available = set(QFontDatabase.families())
    family = next((name for name in ("Inter Variable", "Inter", "SF Pro Text", "SF Pro Display", "Adwaita Sans", "Helvetica Neue", "Noto Sans")
                   if name in available), app.font().family())
    font = QFont(family)
    font.setPointSizeF(10.5)
    app.setFont(font)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--demo-file", action="append", default=[])
    parser.add_argument("--quit-after", type=int, help=t('cli_quit_after_help'))
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setApplicationName("Tecnomata IPTV")
    app.setDesktopFileName("tecnomata-iptv")
    configure_appearance(app)
    window = Window(args.demo or bool(args.demo_file), args.demo_file)
    window.show()
    if args.quit_after:
        QTimer.singleShot(args.quit_after, window.close)
        window.destroyed.connect(app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
