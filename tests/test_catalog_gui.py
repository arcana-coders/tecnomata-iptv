import time
from collections import Counter
import httpx
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from tecnomata_iptv import app as ui
from tecnomata_iptv.accounts import AccountStore
from tecnomata_iptv.xtream import Account, XtreamClient


class MemoryBackend:
    def __init__(self):
        self.payload = None

    def get_password(self, *args):
        return self.payload

    def set_password(self, service, identity, payload):
        self.payload = payload

    def delete_password(self, *args):
        self.payload = None


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication(["tecnomata-iptv-test"])


def wait_until(predicate):
    deadline = time.monotonic() + 8
    while not predicate():
        assert time.monotonic() < deadline, "Qt worker did not finish"
        QTest.qWait(10)


@pytest.fixture
def environment(qapp, monkeypatch):
    calls = Counter()
    def handler(request):
        action = request.url.params.get("action", "authenticate")
        calls[action] += 1
        time.sleep(.025)
        if action == "authenticate":
            return httpx.Response(200, json={"user_info": {"auth": 1, "status": "Active"}})
        if action.endswith("_categories"):
            return httpx.Response(200, json=[{"category_id": "1", "category_name": "Prueba"}])
        if action == "get_series_info":
            return httpx.Response(200, json={"episodes": {"1": [{"id": "9", "title": "Piloto", "episode_num": 1}]}})
        return httpx.Response(200, json=[{"name": "Prueba", "category_id": "1", "stream_id": 2, "series_id": 3}])
    monkeypatch.setattr(ui, "XtreamClient", lambda account: XtreamClient(account, httpx.MockTransport(handler)))
    store = AccountStore(MemoryBackend())
    windows = []
    yield calls, store, windows
    for window in windows:
        wait_until(lambda: not window.jobs)
        window.close()
        window.deleteLater()


def test_prefetch_browsing_refresh_and_episode_cache(environment):
    calls, store, windows = environment
    window = ui.Window(restore=False, account_store=store)
    windows.append(window)
    window.connect_account(Account("https://example.invalid", "u", "p"), update_store=True)
    wait_until(lambda: window.cache is not None and "live" in window.cache.sections and window.pending_section == "vod")
    assert window.navigation.isEnabled() and window.items.isEnabled()
    wait_until(lambda: not window.jobs)
    assert len(window.cache.sections) == 3
    assert sum(calls.values()) == 7
    for _ in range(3):
        for kind in ("vod", "series", "live"):
            window.section(kind)
            assert window.items.count() == 1
            window.category.setCurrentIndex(1)
            assert window.items.count() == 1
    assert sum(calls.values()) == 7
    for _ in range(2):
        window.section("series")
        window.activate(window.items.item(0))
        wait_until(lambda: not window.jobs)
        assert window.in_episodes
        assert not window.category.isEnabled()
    assert calls["get_series_info"] == 1
    window.refresh_catalogs()
    wait_until(lambda: not window.jobs)
    assert calls["get_live_streams"] == calls["get_vod_streams"] == calls["get_series"] == 2


def test_saved_account_restores_on_launch_and_forget_clears_session(environment):
    calls, store, windows = environment
    account = Account("https://example.invalid", "remembered-user", "remembered-password")
    store.save(account)
    window = ui.Window(account_store=store)
    windows.append(window)
    wait_until(lambda: window.client is not None and not window.jobs)
    assert window.client.account == account
    assert calls["authenticate"] == 1
    assert len(window.cache.sections) == 3
    dialog = ui.Login(window, window.saved_account)
    assert dialog.user.text() == account.username
    assert dialog.password.text() == account.password
    dialog.deleteLater()
    window.forget_account()
    wait_until(lambda: not window.jobs)
    assert store.load() is None
    assert window.client is None and window.cache is None


def test_session_only_login_removes_previous_saved_account(environment):
    calls, store, windows = environment
    account = Account("https://example.invalid", "u", "p")
    store.save(account)
    window = ui.Window(restore=False, account_store=store)
    windows.append(window)
    window.connect_account(account, remember=False, update_store=True)
    wait_until(lambda: window.client is not None and not window.jobs)
    assert store.load() is None
    assert window.saved_account is None
