from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog
from tecnomata_iptv.app import Window, ListNameDialog, ConfirmDialog, ListMembershipDialog
from tecnomata_iptv.widgets import LIVE_ROLE, IN_LIST_ROLE, LIST_BUTTON_X


def accept_with_name(cls, name):
    class Fake(cls):
        def exec(self):
            self.name_edit.setText(name)
            return QDialog.DialogCode.Accepted
    return Fake


def accepting(cls):
    class Fake(cls):
        def exec(self):
            return QDialog.DialogCode.Accepted
    return Fake


def rejecting(cls):
    class Fake(cls):
        def exec(self):
            return QDialog.DialogCode.Rejected
    return Fake


def test_live_rows_expose_live_role_but_vod_rows_do_not():
    app = QApplication.instance() or QApplication([])
    window = Window(demo=True, restore=False)
    window.section('live')
    assert window.items.item(0).data(LIVE_ROLE)
    assert not window.items.item(0).data(IN_LIST_ROLE)
    window.section('vod')
    assert not window.items.item(0).data(LIVE_ROLE)
    window.close()


def test_clicking_the_list_zone_emits_signal_only_for_live_rows(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr('tecnomata_iptv.app.ListMembershipDialog', accepting(ListMembershipDialog))
    window = Window(demo=True, restore=False)
    window.show()
    window.section('live')
    app.processEvents()
    seen = []
    window.items.list_button_clicked.connect(lambda item: seen.append(item))
    rect = window.items.visualItemRect(window.items.item(0))
    x = (LIST_BUTTON_X[0] + LIST_BUTTON_X[1]) // 2
    point = QPoint(x, rect.center().y())
    QTest.mouseClick(window.items.viewport(), Qt.MouseButton.LeftButton, pos=point)
    assert len(seen) == 1 and seen[0] is window.items.item(0)
    assert window.video.pending_url is None  # The list button must not start playback.
    window.section('vod')
    app.processEvents()
    QTest.mouseClick(window.items.viewport(), Qt.MouseButton.LeftButton, pos=point)
    assert len(seen) == 1  # VOD rows have no list button, so the click falls through.
    window.close()


def test_create_rename_and_delete_list_from_the_combo(monkeypatch):
    app = QApplication.instance() or QApplication([])
    window = Window(demo=True, restore=False)
    window.section('live')
    monkeypatch.setattr('tecnomata_iptv.app.ListNameDialog', accept_with_name(ListNameDialog, 'Deportes'))
    window.create_list_dialog()
    assert window.lists_combo.count() == 2
    list_id = window.lists_combo.itemData(1)
    assert window.library.lists(window.library_scope) == [{'list_id': list_id, 'name': 'Deportes', 'count': 0}]
    window.lists_combo.setCurrentIndex(1)
    assert window.collection_view == ('list', list_id, 'Deportes')
    assert window.rename_list_button.isEnabled() and window.delete_list_button.isEnabled()

    monkeypatch.setattr('tecnomata_iptv.app.ListNameDialog', accept_with_name(ListNameDialog, 'Deportes MX'))
    window.rename_list_dialog()
    assert window.library.lists(window.library_scope)[0]['name'] == 'Deportes MX'
    assert window.list_heading.text() == '☰  Deportes MX'

    monkeypatch.setattr('tecnomata_iptv.app.ConfirmDialog', rejecting(ConfirmDialog))
    window.delete_list_dialog()
    assert window.library.lists(window.library_scope) != []  # Rejecting the confirm keeps the list.

    monkeypatch.setattr('tecnomata_iptv.app.ConfirmDialog', accepting(ConfirmDialog))
    window.delete_list_dialog()
    assert window.library.lists(window.library_scope) == []
    assert window.lists_combo.count() == 1  # Back to just the placeholder.
    assert window.kind == 'live'  # Deleting the list being viewed returns to Live.
    window.close()


def test_list_button_dialog_toggles_membership_and_creates_new_lists(monkeypatch):
    app = QApplication.instance() or QApplication([])
    window = Window(demo=True, restore=False)
    window.section('live')
    row = window.items.item(0).data(Qt.ItemDataRole.UserRole)

    captured = {}
    class SpyDialog(ListMembershipDialog):
        def __init__(self, parent, lists, membership, on_toggle, on_create, channel_name):
            super().__init__(parent, lists, membership, on_toggle, on_create, channel_name)
            captured['dialog'] = self
        def exec(self):
            return QDialog.DialogCode.Accepted
    monkeypatch.setattr('tecnomata_iptv.app.ListMembershipDialog', SpyDialog)

    window.open_list_membership(window.items.item(0))
    dialog = captured['dialog']
    assert dialog.checks == {}  # No lists exist yet.
    dialog.new_name.setText('Deportes')
    QTest.mouseClick(dialog.create_button, Qt.MouseButton.LeftButton)
    assert len(dialog.checks) == 1
    list_id = next(iter(dialog.checks))
    assert dialog.checks[list_id].isChecked()
    assert window.library.list_membership(window.library_scope, 'live', row) == {list_id}
    assert window.lists_combo.count() == 2  # Placeholder plus the new list.
    assert window.items.item(0).data(IN_LIST_ROLE)

    dialog.checks[list_id].setChecked(False)
    assert window.library.list_membership(window.library_scope, 'live', row) == set()
    assert not window.items.item(0).data(IN_LIST_ROLE)
    window.close()
