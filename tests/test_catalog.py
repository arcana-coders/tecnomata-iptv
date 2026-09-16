import pytest
from tecnomata_iptv.catalog import CatalogCache, KINDS


class Client:
    def __init__(self, prefix=""):
        self.calls = []
        self.prefix = prefix
        self.fail = False

    def categories(self, kind):
        self.calls.append(("categories", kind))
        return [{"category_id": "1", "category_name": "Prueba"}]

    def catalog(self, kind):
        self.calls.append(("catalog", kind))
        if self.fail:
            raise RuntimeError("Network unavailable")
        return [{"name": self.prefix + kind, "category_id": 1},
                {"name": "Otro", "category_id": "2"}]

    def episodes(self, series_id):
        self.calls.append(("episodes", str(series_id)))
        return [{"stream_id": 9, "name": "Piloto"}]


def test_sections_and_categories_reuse_prefetched_data():
    client = Client()
    cache = CatalogCache(client)
    for kind in KINDS:
        cache.section(kind)
    for _ in range(4):
        for kind in KINDS:
            assert cache.section(kind).filtered("1")[0]["name"] == kind
            assert len(cache.section(kind).filtered()) == 2
    assert len(client.calls) == 6


def test_failed_section_is_not_published_and_can_retry():
    client = Client()
    cache = CatalogCache(client)
    client.fail = True
    with pytest.raises(RuntimeError):
        cache.section("vod")
    assert "vod" not in cache.sections
    client.fail = False
    assert cache.section("vod").rows


def test_episode_cache_normalizes_ids():
    client = Client()
    cache = CatalogCache(client)
    assert cache.episodes(3) == cache.episodes("3")
    assert client.calls == [("episodes", "3")]


def test_cache_is_scoped_to_account_and_refresh():
    first = CatalogCache(Client("first-"))
    second = CatalogCache(Client("second-"))
    assert first.section("vod").rows[0]["name"] == "first-vod"
    assert second.section("vod").rows[0]["name"] == "second-vod"
