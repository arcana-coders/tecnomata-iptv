"""Acceso Xtream. No registrar requests: contienen credenciales en la URL."""
from dataclasses import dataclass, field
from urllib.parse import quote, urlsplit, urlunsplit
import re

import httpx

from .i18n import t


class ServiceError(Exception):
    """Mensaje saneado que puede mostrarse en pantalla."""


@dataclass(frozen=True)
class Account:
    server: str
    username: str = field(repr=False)
    password: str = field(repr=False)

    def __post_init__(self):
        parts = urlsplit(self.server.strip())
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise ServiceError(t('error_url_incomplete'))
        if parts.username or parts.password or parts.query or parts.fragment:
            raise ServiceError(t('error_url_extra_fields'))
        path = parts.path.rstrip("/")
        if path.endswith("/player_api.php"):
            path = path[:-len("/player_api.php")]
        if not self.username.strip() or not self.password:
            raise ServiceError(t('error_missing_credentials'))
        object.__setattr__(self, "server", urlunsplit((parts.scheme, parts.netloc, path, "", "")))


class XtreamClient:
    def __init__(self, account: Account, transport=None):
        self.account = account
        self.http = httpx.Client(timeout=20, transport=transport, follow_redirects=False,
                                 headers={"User-Agent": "Tecnomata-IPTV/0.1"})

    def close(self):
        self.http.close()

    def request(self, action=None, **extra):
        params = {"username": self.account.username, "password": self.account.password, **extra}
        if action:
            params["action"] = action
        try:
            response = self.http.get(self.account.server + "/player_api.php", params=params)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError):
            raise ServiceError(t('error_service_bad_response')) from None

    def authenticate(self):
        data = self.request()
        info = data.get("user_info", {}) if isinstance(data, dict) else {}
        if not isinstance(info, dict) or str(info.get("auth")) != "1":
            raise ServiceError(t('error_access_rejected'))
        if info.get("status", "Active").lower() != "active":
            raise ServiceError(t('error_account_inactive'))
        return info

    def categories(self, kind):
        return self._list(f"get_{kind}_categories")

    def catalog(self, kind, category=None):
        action = "get_series" if kind == "series" else f"get_{kind}_streams"
        return self._list(action, **({"category_id": category} if category else {}))

    def _list(self, action, **params):
        data = self.request(action, **params)
        if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
            raise ServiceError(t('error_catalog_incompatible'))
        return data

    def episodes(self, series_id):
        data = self.request("get_series_info", series_id=series_id)
        seasons = data.get("episodes", {}) if isinstance(data, dict) else {}
        if not isinstance(seasons, dict):
            raise ServiceError(t('error_seasons_incompatible'))
        result = []
        for season, episodes in sorted(seasons.items(), key=lambda pair: str(pair[0]).zfill(5)):
            if not isinstance(episodes, list):
                continue
            for episode in episodes:
                if isinstance(episode, dict) and episode.get("id"):
                    result.append({**episode, "stream_id": episode["id"],
                                   "name": t('episode_label', season=season, number=episode.get('episode_num', '?'),
                                            title=episode.get('title') or t('episode_untitled'))})
        return result

    def stream_url(self, kind, stream_id, extension=None):
        if kind not in ("live", "vod", "series") or not str(stream_id).isdigit():
            raise ServiceError(t('error_invalid_content_id'))
        extension = extension or ("ts" if kind == "live" else "mp4")
        if not re.fullmatch(r"[a-zA-Z0-9]{1,8}", extension):
            raise ServiceError(t('error_incompatible_format'))
        route = "movie" if kind == "vod" else kind
        user = quote(self.account.username, safe="")
        password = quote(self.account.password, safe="")
        return f"{self.account.server}/{route}/{user}/{password}/{stream_id}.{extension}"
