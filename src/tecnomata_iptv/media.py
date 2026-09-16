"""Display only decoded-stream information, never infer quality from names."""
from math import isfinite
from .diagnostics import text_value


def describe_video(info):
    width, height = info.get('width'), info.get('height')
    if not width or not height:
        return 'Resolución no disponible' if info else 'Sin reproducción'
    quality = 'UHD' if height >= 2160 else 'Full HD' if height >= 1080 else 'HD' if height >= 720 else 'SD'
    parts = [f'{quality} · {width} × {height}']
    if info.get('fps') and isfinite(info['fps']) and info['fps'] > 0:
        parts.append(f"{info['fps']:g} fps")
    if info.get('codec'):
        parts.append(info['codec'].upper())
    return '  ·  '.join(parts)


def track_label(track):
    languages = {'spa': 'Español', 'es': 'Español', 'eng': 'English', 'en': 'English',
                 'por': 'Português', 'pt': 'Português', 'fra': 'Français', 'fr': 'Français',
                 'jpn': '日本語', 'ja': '日本語', 'deu': 'Deutsch', 'de': 'Deutsch', 'ita': 'Italiano'}
    lang = text_value(track.get('lang'))
    parts = [languages.get(lang, lang) if lang else 'Idioma no indicado']
    for key in ('title', 'codec'):
        value = text_value(track.get(key))
        if value and value not in parts:
            parts.append(value)
    return ' · '.join(parts) + f" (#{track['id']})"
