"""Catálogos de una cuenta, conservados en RAM hasta actualizar o cambiar cuenta."""
from dataclasses import dataclass


KINDS = ("live", "vod", "series")


@dataclass
class Section:
    categories: list
    rows: list

    def filtered(self, category=None):
        if category is None:
            return self.rows
        return [row for row in self.rows if str(row.get("category_id")) == str(category)]


class CatalogCache:
    def __init__(self, client):
        self.client = client
        self.sections = {}
        self.episode_lists = {}

    def section(self, kind):
        if kind not in KINDS:
            raise ValueError("Sección inválida")
        if kind not in self.sections:
            # Publish only when both requests succeed, so failures can be retried.
            categories = self.client.categories(kind)
            rows = self.client.catalog(kind)
            self.sections[kind] = Section(categories, rows)
        return self.sections[kind]

    def episodes(self, series_id):
        key = str(series_id)
        if key not in self.episode_lists:
            self.episode_lists[key] = self.client.episodes(series_id)
        return self.episode_lists[key]
