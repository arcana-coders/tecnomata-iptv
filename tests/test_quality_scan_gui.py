import time
import httpx
import pytest
from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtTest import QTest
from tecnomata_iptv import app as ui
from tecnomata_iptv.library import LibraryStore
from tecnomata_iptv.accounts import AccountStore
from tecnomata_iptv.xtream import Account, XtreamClient
from tecnomata_iptv.i18n import t


class MemoryBackend:
    def get_password(self, *args):
        return None

    def set_password(self, *args):
        pass

    def delete_password(self, *args):
        pass


LIVE_ROWS = [
    {"name": "HBO", "category_id": "1", "stream_id": 10, "container_extension": "ts"},
    {"name": "HBO 2", "category_id": "1", "stream_id": 11, "container_extension": "ts"},
]


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication(["tecnomata-iptv-quality-test"])


def wait_until(predicate):
    deadline = time.monotonic() + 8
    while not predicate():
        assert time.monotonic() < deadline, "Qt worker did not finish"
        QTest.qWait(10)


def accepting_confirm():
    class Fake:
        def __init__(self, *args, **kwargs):
            pass
        def exec(self):
            return QDialog.DialogCode.Accepted
    return Fake


@pytest.fixture
def environment(qapp, monkeypatch):
    def handler(request):
        action = request.url.params.get("action", "authenticate")
        if action == "authenticate":
            return httpx.Response(200, json={"user_info": {"auth": 1, "status": "Active"}})
        if action.endswith("_categories"):
            return httpx.Response(200, json=[{"category_id": "1", "category_name": "Deportes"}])
        if action == "get_live_streams":
            return httpx.Response(200, json=LIVE_ROWS)
        if action == "get_series_info":
            return httpx.Response(200, json={"episodes": {}})
        return httpx.Response(200, json=[])
    monkeypatch.setattr(ui, "XtreamClient", lambda account: XtreamClient(account, httpx.MockTransport(handler)))
    monkeypatch.setattr(ui, "LibraryStore", lambda path=None: LibraryStore(":memory:"))
    store = AccountStore(MemoryBackend())
    windows = []
    yield store, windows
    for window in windows:
        wait_until(lambda: not window.jobs)
        window.close()
        window.deleteLater()


def test_scan_context_and_safety_guard_on_all_channels(environment):
    store, windows = environment
    window = ui.Window(restore=False, account_store=store)
    windows.append(window)
    window.connect_account(Account("https://example.invalid", "u", "p"))
    wait_until(lambda: window.client is not None and not window.jobs)
    window.section('live')

    # Viewing all channels with no filter returns None to prevent accidental bulk scanning.
    assert window.current_scan_context() is None
    window.start_quality_scan()
    assert not window.scan_active
    assert window.status.text() == t('scan_all_channels_forbidden')

    window.category.setCurrentIndex(window.category.findData('1'))
    assert window.current_scan_context() == 'Deportes'
    window.search.setText('hbo')
    assert window.current_scan_context() == 'hbo'


def test_quality_scan_classifies_saves_and_generates_lists(environment, monkeypatch):
    store, windows = environment
    window = ui.Window(restore=False, account_store=store)
    windows.append(window)
    window.connect_account(Account("https://example.invalid", "u", "p"))
    wait_until(lambda: window.client is not None and not window.jobs)
    window.section('live')
    assert not window.scan_button.isHidden()
    assert len(window.visible_rows) == 2
    window.search.setText('hbo')
    assert len(window.visible_rows) == 2
    assert window.current_scan_context() == 'hbo'

    results = {
        window.client.stream_url('live', 10, 'ts'): (1920, 1080, 'fullhd'),
        window.client.stream_url('live', 11, 'ts'): (1280, 720, 'hd'),
    }
    monkeypatch.setattr(ui, 'probe_stream', lambda url, **kw: results[url])
    monkeypatch.setattr(ui, 'ConfirmDialog', lambda *a, **k: accepting_confirm()())

    window.start_quality_scan()
    wait_until(lambda: not window.scan_active)

    assert window.library.quality_of(window.library_scope, 'live', {'stream_id': 10}) == 'fullhd'
    assert window.library.quality_of(window.library_scope, 'live', {'stream_id': 11}) == 'hd'
    lists_by_name = {item['name']: item for item in window.library.lists(window.library_scope)}
    assert set(lists_by_name) == {'hbo · Full HD', 'hbo · HD', 'Full HD', 'HD'}
    assert lists_by_name['Full HD']['count'] == 1  # The running "all channels ever seen as X" list.
    assert lists_by_name['HD']['count'] == 1
    window.filter_rows()
    labels = [window.items.item(i).text() for i in range(window.items.count())]
    assert any(label.startswith('[FHD] ') for label in labels)
    assert any(label.startswith('[HD] ') for label in labels)
    assert window.status.text() == t('scan_done', total=2, fullhd=1, hd=1, sd=0, unknown=0) + t(
        'scan_lists_updated', names='hbo · HD, hbo · Full HD')

    # Rescanning with a different result must move the channel between the global tier lists, not duplicate it.
    results[window.client.stream_url('live', 11, 'ts')] = (720, 480, 'sd')
    window.start_quality_scan()
    wait_until(lambda: not window.scan_active)
    lists_by_name = {item['name']: item for item in window.library.lists(window.library_scope)}
    assert lists_by_name['HD']['count'] == 0
    assert lists_by_name['SD']['count'] == 1
    assert lists_by_name['Full HD']['count'] == 1

    # Generated lists (per-search and the running global ones) are ordinary, deletable lists.
    window.library.delete_list(window.library_scope, lists_by_name['SD']['list_id'])
    assert 'SD' not in {item['name'] for item in window.library.lists(window.library_scope)}


def test_quality_scan_can_be_cancelled_and_saves_nothing_extra(environment, monkeypatch):
    store, windows = environment
    window = ui.Window(restore=False, account_store=store)
    windows.append(window)
    window.connect_account(Account("https://example.invalid", "u", "p"))
    wait_until(lambda: window.client is not None and not window.jobs)
    window.section('live')
    window.category.setCurrentIndex(window.category.findData('1'))

    calls = []
    def slow_probe(url, **kw):
        calls.append(url)
        return (1920, 1080, 'fullhd')
    monkeypatch.setattr(ui, 'probe_stream', slow_probe)
    monkeypatch.setattr(ui, 'ConfirmDialog', lambda *a, **k: accepting_confirm()())

    window.start_quality_scan()
    window.cancel_quality_scan()
    wait_until(lambda: not window.scan_active)

    assert len(calls) == 1
    assert window.library.lists(window.library_scope) == []
    assert window.status.text() == t('scan_cancelled', done=1, total=2)


def test_quality_scan_requires_a_connected_service():
    app = QApplication.instance() or QApplication([])
    window = ui.Window(demo=True, restore=False)
    window.section('live')
    window.search.setText('hbo')
    window.start_quality_scan()
    assert not window.scan_active
    window.close()


def test_quality_scan_refuses_with_no_visible_channels(environment, monkeypatch):
    store, windows = environment
    window = ui.Window(restore=False, account_store=store)
    windows.append(window)
    window.connect_account(Account("https://example.invalid", "u", "p"))
    wait_until(lambda: window.client is not None and not window.jobs)
    window.section('live')
    window.search.setText('does-not-exist')
    assert window.visible_rows == []
    window.start_quality_scan()
    assert not window.scan_active
