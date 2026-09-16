import httpx
import pytest
from tecnomata_iptv.xtream import Account, XtreamClient, ServiceError


def client(handler):
    return XtreamClient(Account("https://example.invalid/", "user name", "secret/password"),
                        httpx.MockTransport(handler))


def test_account_normalizes_api_endpoint_and_hides_secrets():
    account = Account("https://example.invalid/base/player_api.php", "private-user", "private-password")
    assert account.server == "https://example.invalid/base"
    assert "private" not in repr(account)


@pytest.mark.parametrize("server", ["example.invalid", "ftp://example.invalid", "https://user:secret@example.invalid", "https://example.invalid?password=secret"])
def test_invalid_server(server):
    with pytest.raises(ServiceError):
        Account(server, "u", "p")


def test_login_and_catalog_requests():
    seen = []
    def handler(request):
        seen.append(request)
        action = request.url.params.get("action")
        if not action:
            return httpx.Response(200, json={"user_info": {"auth": 1, "status": "Active"}})
        return httpx.Response(200, json=[{"name": "Contenido", "stream_id": 42}])
    api = client(handler)
    assert api.authenticate()["auth"] == 1
    for kind, action in [("live", "get_live_streams"), ("vod", "get_vod_streams"), ("series", "get_series")]:
        assert api.catalog(kind, "7")[0]["stream_id"] == 42
        assert seen[-1].url.params["action"] == action
        assert seen[-1].url.params["category_id"] == "7"
        assert seen[-1].url.params["password"] == "secret/password"
    api.close()


@pytest.mark.parametrize("data", [{"user_info": {"auth": 0}}, {"user_info": {"auth": "1", "status": "Expired"}}, [], {"user_info": None}])
def test_auth_rejected(data):
    api = client(lambda request: httpx.Response(200, json=data))
    with pytest.raises(ServiceError):
        api.authenticate()
    api.close()


def test_http_error_is_sanitized():
    api = client(lambda request: httpx.Response(403))
    with pytest.raises(ServiceError) as error:
        api.authenticate()
    assert "secret" not in str(error.value)
    assert "example.invalid" not in str(error.value)
    api.close()


def test_stream_routes_and_escaping():
    api = client(lambda request: httpx.Response(200))
    assert api.stream_url("live", 42) == "https://example.invalid/live/user%20name/secret%2Fpassword/42.ts"
    assert api.stream_url("vod", 42, "mkv").endswith("/movie/user%20name/secret%2Fpassword/42.mkv")
    assert api.stream_url("series", 42).endswith("/series/user%20name/secret%2Fpassword/42.mp4")
    with pytest.raises(ServiceError):
        api.stream_url("vod", "../../private", "mkv")
    with pytest.raises(ServiceError):
        api.stream_url("vod", 42, "mkv?password=secret")
    api.close()


def test_episodes_preserve_container_and_sort_seasons():
    api = client(lambda request: httpx.Response(200, json={"episodes": {
        "10": [{"id": "102", "title": "Final", "container_extension": "mkv", "episode_num": 1}],
        "2": [{"id": "21", "title": "Inicio", "episode_num": 1}]}}))
    episodes = api.episodes(3)
    assert episodes[0]["stream_id"] == "21"
    assert episodes[1]["container_extension"] == "mkv"
    api.close()


def test_malformed_catalog():
    api = client(lambda request: httpx.Response(200, json={"error": "bad"}))
    with pytest.raises(ServiceError):
        api.catalog("live")
    api.close()
