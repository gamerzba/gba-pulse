from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView

from gba_pulse.config import FORUM_URL
from gba_pulse.ui.theme import GLOBAL_STYLE


class LoginDialog(QDialog):
    """Sign in on the real forum origin using a dedicated persistent profile."""
    def __init__(self, profile: QWebEngineProfile, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Prijava na Gamerz.ba")
        self.setModal(True)
        self.resize(980, 720)
        self.setStyleSheet(GLOBAL_STYLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        intro = QLabel("PRIJAVA NA GBA\nPrijavi se na Gamerz.ba u ovom prozoru. G.ba Pulse koristi zasebnu lokalnu sesiju; ne čita kolačiće iz tvog glavnog browsera.")
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#A0AABC; padding: 2px 3px 8px 3px;")
        layout.addWidget(intro)

        self.view = QWebEngineView(self)
        self.page = QWebEnginePage(profile, self.view)
        self.view.setPage(self.page)
        self.view.setUrl(QUrl(FORUM_URL))
        layout.addWidget(self.view, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.done_button = QPushButton("Gotovo — provjeri sesiju")
        self.done_button.setObjectName("primaryButton")
        self.done_button.clicked.connect(self.accept)
        buttons.addWidget(self.done_button)
        cancel = QPushButton("Zatvori")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    def closeEvent(self, event) -> None:
        # Keep the profile (and its persistent cookies) alive for the app.
        super().closeEvent(event)
