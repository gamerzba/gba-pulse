from __future__ import annotations

from PySide6.QtCore import QByteArray, QObject, QUrl, Signal
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtSvg import QSvgRenderer

from gba_pulse.config import LOGO_URL


class LogoLoader(QObject):
    pixmap_ready = Signal(QPixmap)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = QNetworkAccessManager(self)
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        request = QNetworkRequest(QUrl(LOGO_URL))
        request.setTransferTimeout(8000)
        reply = self.manager.get(request)
        reply.finished.connect(lambda: self._finish(reply))

    def _finish(self, reply) -> None:
        try:
            if reply.error():
                return
            data = bytes(reply.readAll())
            if not data or len(data) > 300_000:
                return
            renderer = QSvgRenderer(QByteArray(data))
            if not renderer.isValid():
                return
            pixmap = QPixmap(96, 96)
            pixmap.fill(0)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            renderer.render(painter)
            painter.end()
            self.pixmap_ready.emit(pixmap)
        finally:
            reply.deleteLater()
