"""Aísla el idioma de la app real: las pruebas siempre corren en español,
sin importar la preferencia guardada en QSettings de esta máquina."""
import pytest
from tecnomata_iptv import i18n


@pytest.fixture(autouse=True)
def spanish_ui_language():
    i18n.force_language_override('es')
    yield
    i18n.force_language_override(None)
