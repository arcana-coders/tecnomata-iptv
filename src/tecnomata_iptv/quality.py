"""Sondeo real de resolución de un stream, sin ventana ni GUI.

No infiere calidad del nombre del canal: abre brevemente el stream con un
motor libmpv independiente del reproductor visible, lee el video-params real
y lo clasifica. Un canal caído o lento se reporta como desconocido, nunca
como una calidad inventada.
"""
import threading

TIERS = ("sd", "hd", "fullhd")


def classify(height):
    if not height or height <= 0:
        return None
    if height >= 1080:
        return "fullhd"
    if height >= 720:
        return "hd"
    return "sd"


def probe_stream(url, timeout=7, engine_factory=None):
    """Devuelve (width, height, tier). Todo None si no se pudo determinar a tiempo."""
    if engine_factory is None:
        import mpv
        engine_factory = lambda: mpv.MPV(
            vo="null", ao="null", config=False, idle=True, hwdec="no", terminal=False,
            ytdl=False, user_agent="VLC/3.0.21 LibVLC/3.0.21", network_timeout=min(timeout, 20),
            loglevel="error", input_default_bindings=False, input_vo_keyboard=False,
            osd_level=0, osc=False)
    result = {"width": None, "height": None}
    ready = threading.Event()

    engine = engine_factory()
    try:
        @engine.property_observer("video-params")
        def _observe(_name, value):
            if isinstance(value, dict) and value.get("h"):
                result["width"], result["height"] = value.get("w"), value.get("h")
                ready.set()
        try:
            engine.command("loadfile", url, "replace")
        except Exception:
            return None, None, None
        ready.wait(timeout)
    finally:
        try:
            engine.terminate()
        except Exception:
            pass
    return result["width"], result["height"], classify(result["height"])
