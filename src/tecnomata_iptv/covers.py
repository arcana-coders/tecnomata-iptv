"""Asynchronous cover/poster downloader with local disk cache and thread safety."""
import os
from hashlib import sha256
from pathlib import Path
import httpx

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, QSize, Qt, QRectF
from PySide6.QtGui import QPixmap, QColor, QPainter, QFont, QPen, QPainterPath

from .themes import THEMES

MAX_MEMORY_CACHE = 400


class DownloadSignals(QObject):
    finished = Signal(str, str)  # (url, cache_path_or_empty)


class DownloadJob(QRunnable):
    """Downloads an image in a worker thread and saves it directly to disk.
    NEVER touches QPixmap/QImage in the background thread (Qt GUI thread requirement)."""
    def __init__(self, url, cache_path):
        super().__init__()
        self.url = url
        self.cache_path = cache_path
        self.signals = DownloadSignals()

    def run(self):
        try:
            with httpx.Client(timeout=8.0, follow_redirects=True,
                              headers={"User-Agent": "TecnomataIPTV/1.0 (Linux)"}) as client:
                resp = client.get(self.url)
                if resp.status_code == 200 and resp.content and len(resp.content) > 100:
                    self.cache_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                    temp = self.cache_path.with_suffix(".tmp")
                    temp.write_bytes(resp.content)
                    temp.replace(self.cache_path)
                    self.signals.finished.emit(self.url, str(self.cache_path))
                    return
        except Exception:
            pass
        self.signals.finished.emit(self.url, "")


class CoverCache(QObject):
    cover_loaded = Signal(str)

    def __init__(self, cache_dir=None, parent=None):
        super().__init__(parent)
        if cache_dir is None:
            cache_dir = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "tecnomata-iptv/covers"
        self.cache_dir = Path(cache_dir)
        self.memory_cache = {}      # url -> QPixmap
        self.failed_urls = set()     # set of urls that 404'd or errored to avoid infinite retries
        self.pending = set()         # currently downloading urls
        self.callbacks = {}          # url -> list of callbacks
        self.placeholders = {}       # (title, theme, w, h) -> QPixmap

        # Dedicated thread pool with max 4 concurrent downloads to prevent flooding
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(4)

    def get(self, url, callback=None):
        if not url:
            return None
        if url in self.memory_cache:
            return self.memory_cache[url]
        if url in self.failed_urls:
            return None

        key = sha256(url.encode()).hexdigest()
        path = self.cache_dir / f"{key}.jpg"
        if path.is_file():
            pix = QPixmap(str(path))
            if not pix.isNull():
                self._put_memory(url, pix)
                return pix
            else:
                # Corrupt cache file, remove it
                try:
                    path.unlink()
                except OSError:
                    pass

        if callback:
            self.callbacks.setdefault(url, []).append(callback)

        if url not in self.pending:
            self.pending.add(url)
            job = DownloadJob(url, path)
            job.signals.finished.connect(self._on_download_finished)
            self.pool.start(job)

        return None

    def _on_download_finished(self, url, path_str):
        self.pending.discard(url)
        cbs = self.callbacks.pop(url, [])

        if path_str and Path(path_str).is_file():
            pix = QPixmap(path_str)
            if not pix.isNull():
                self._put_memory(url, pix)
                for cb in cbs:
                    try:
                        cb(url, pix)
                    except Exception:
                        pass
                self.cover_loaded.emit(url)
                return

        # Download failed or file is invalid
        self.failed_urls.add(url)
        for cb in cbs:
            try:
                cb(url, None)
            except Exception:
                pass

    def _put_memory(self, url, pix):
        if len(self.memory_cache) >= MAX_MEMORY_CACHE:
            # Drop the oldest 50 items
            for k in list(self.memory_cache.keys())[:50]:
                self.memory_cache.pop(k, None)
        self.memory_cache[url] = pix

    def placeholder(self, title, theme_key="springfield", size=QSize(150, 225)):
        cache_key = (title, theme_key, size.width(), size.height())
        if cache_key in self.placeholders:
            return self.placeholders[cache_key]

        pix = QPixmap(size)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        theme = THEMES.get(theme_key, THEMES["springfield"])
        accent = QColor(theme[2])
        panel = QColor(theme[4])

        path = QPainterPath()
        path.addRoundedRect(QRectF(1, 1, size.width() - 2, size.height() - 2), 8, 8)
        painter.fillPath(path, panel)
        painter.setPen(QPen(accent.darker(120), 1.5))
        painter.drawPath(path)

        painter.setPen(accent)
        icon_rect = QRectF(0, 30, size.width(), 40)
        font = QFont()
        font.setPixelSize(28)
        painter.setFont(font)
        painter.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, "🎬")

        font.setPixelSize(12)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#f0f0f0"))
        text_rect = QRectF(10, 80, size.width() - 20, size.height() - 95)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
                         title[:45] + ("…" if len(title) > 45 else ""))

        painter.end()
        if len(self.placeholders) >= 200:
            self.placeholders.clear()
        self.placeholders[cache_key] = pix
        return pix
