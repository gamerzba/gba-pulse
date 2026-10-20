from __future__ import annotations

import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox,
    QComboBox, QLineEdit, QFrame, QMessageBox, QApplication, QScrollArea,
    QWidget,
)
from PySide6.QtWebEngineCore import QWebEngineProfile

from gba_pulse.config import ALLOWED_REFRESH_SECONDS
from gba_pulse.services.autostart import is_autostart_enabled, set_autostart
from gba_pulse.ui.theme import GLOBAL_STYLE


class DiagnosticsDialog(QDialog):
    def __init__(self, details: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API dijagnostika")
        self.resize(640, 500)
        self.setStyleSheet(GLOBAL_STYLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        header = QLabel("API RESPONSE INSPECTOR")
        header.setStyleSheet("font-size:12px;font-weight:800;letter-spacing:1px;color:#FB9524;")
        layout.addWidget(header)
        intro = QLabel("Prikazuju se samo statusni kodovi, content-type i nazivi polja/tipovi podataka. Stvarne vrijednosti odgovora nisu prikazane niti zapisane.")
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#8E98AA;")
        layout.addWidget(intro)

        self.lines: list[str] = []
        if isinstance(details, dict) and details.get("diagnostic_note"):
            self.lines.append("Zadnja greška obrade\n" + str(details.get("diagnostic_note")) + "\n")
        statuses = details.get("endpoint_statuses", {}) if isinstance(details, dict) else {}
        for key, title in (("messages", "Poruke"), ("points", "Bodovi"), ("rss", "RSS"), ("home", "Početna stranica")):
            val = details.get(key, {}) if isinstance(details, dict) else {}
            if key in {"messages", "points"} and isinstance(val, dict):
                content_type = val.get("content_type", "") or "nije dostupan"
                schema = val.get("schema", "Nema podataka")
                status = val.get("status", statuses.get(key, "Nema odgovora"))
            else:
                content_type = "—"
                schema = details.get(f"{key}_status", statuses.get(key, "Nema odgovora")) if isinstance(details, dict) else "Nema odgovora"
                status = statuses.get(key, "Nema odgovora")
            self.lines.append(f"{title}\nStatus: {status}\nContent-Type: {content_type}\nStruktura: {schema}\n")
        from PySide6.QtWidgets import QPlainTextEdit
        output = QPlainTextEdit()
        output.setReadOnly(True)
        output.setPlainText("\n".join(self.lines))
        output.setStyleSheet("QPlainTextEdit{background:#0B101B;border:1px solid #202838;border-radius:10px;padding:10px;color:#C6CDDA;font-family:Consolas,monospace;font-size:10pt;}")
        layout.addWidget(output, 1)
        buttons = QHBoxLayout()
        copy = QPushButton("Kopiraj strukturu")
        copy.clicked.connect(lambda: QApplication.clipboard().setText("\n".join(self.lines)))
        buttons.addWidget(copy)
        buttons.addStretch(1)
        close = QPushButton("Zatvori")
        close.setObjectName("primaryButton")
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        layout.addLayout(buttons)


class SettingsDialog(QDialog):
    def __init__(self, settings, profile: QWebEngineProfile, diagnostics: dict, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.profile = profile
        self.diagnostics = diagnostics or {}
        self.setWindowTitle("G.ba Pulse — postavke")
        self.setFixedWidth(500)
        self.setStyleSheet(GLOBAL_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        title = QLabel("POSTAVKE")
        title.setStyleSheet("font-size:12px;font-weight:800;letter-spacing:1.7px;color:#FB9524;")
        root.addWidget(title)
        description = QLabel("Diskretno prilagodi widget. Sesija ostaje lokalno u odvojenom profilu aplikacije.")
        description.setWordWrap(True)
        description.setStyleSheet("color:#8E98AA;")
        root.addWidget(description)

        self.refresh_combo = QComboBox()
        for seconds in ALLOWED_REFRESH_SECONDS:
            self.refresh_combo.addItem(f"Svakih {seconds} sekundi", seconds)
        current = int(self.settings.value("refresh_seconds", 60))
        index = self.refresh_combo.findData(current)
        self.refresh_combo.setCurrentIndex(index if index >= 0 else self.refresh_combo.findData(60))
        root.addWidget(self._field("Interval osvježavanja", self.refresh_combo))

        self.autostart = QCheckBox("Pokreni G.ba Pulse pri prijavi u Windows")
        self.autostart.setChecked(is_autostart_enabled())
        if os.name != "nt":
            self.autostart.setEnabled(False)
            self.autostart.setToolTip("Dostupno samo na Windowsu.")
        root.addWidget(self.autostart)

        mapping_title = QLabel("MAPIRANJE API ODGOVORA")
        mapping_title.setStyleSheet("font-size:11px;font-weight:800;letter-spacing:1.2px;color:#A9B4C8;margin-top:5px;")
        root.addWidget(mapping_title)
        mapping_help = QLabel("Prema potvrđenim odgovorima Gamerz.ba, bodovi se čitaju iz `balance`, a nepročitane poruke iz `unread`. Oba endpointa mogu vratiti i `notifications`. Putanje se mogu prilagoditi ako se API promijeni.")
        mapping_help.setWordWrap(True)
        mapping_help.setStyleSheet("color:#8E98AA;font-size:9pt;")
        root.addWidget(mapping_help)

        self.points_path = QLineEdit(str(self.settings.value("api/points_json_path", "balance") or "balance"))
        self.points_path.setPlaceholderText("balance")
        root.addWidget(self._field("Bodovi · JSON putanja", self.points_path))
        self.messages_path = QLineEdit(str(self.settings.value("api/messages_json_path", "unread") or "unread"))
        self.messages_path.setPlaceholderText("unread")
        root.addWidget(self._field("Poruke · JSON putanja", self.messages_path))

        diag_button = QPushButton("Otvori API dijagnostiku")
        diag_button.clicked.connect(self._show_diagnostics)
        root.addWidget(diag_button)

        privacy = QLabel("Ne kopiramo kolačiće iz Chromea/Edgea i ne zapisujemo API payload u logove. Za prijavu koristi ugrađeni prozor Gamerz.ba.")
        privacy.setWordWrap(True)
        privacy.setStyleSheet("color:#8E98AA;font-size:9pt;")
        root.addWidget(privacy)

        buttons = QHBoxLayout()
        clear_session = QPushButton("Odjavi / očisti sesiju")
        clear_session.clicked.connect(self._clear_session)
        buttons.addWidget(clear_session)
        buttons.addStretch(1)
        cancel = QPushButton("Odustani")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        save = QPushButton("Spremi")
        save.setObjectName("primaryButton")
        save.clicked.connect(self._save)
        buttons.addWidget(save)
        root.addLayout(buttons)

    def _field(self, caption: str, editor) -> QWidget:
        wrap = QWidget(self)
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        label = QLabel(caption)
        label.setStyleSheet("color:#B4BED0;font-weight:600;font-size:9pt;")
        layout.addWidget(label)
        layout.addWidget(editor)
        return wrap

    def _show_diagnostics(self) -> None:
        DiagnosticsDialog(self.diagnostics, self).exec()

    def _clear_session(self) -> None:
        answer = QMessageBox.question(
            self, "Očistiti lokalnu sesiju?",
            "Ovo briše kolačiće u G.ba Pulse profilu i odjavit će te u widgetu. Ne dira kolačiće tvog glavnog browsera.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.profile.cookieStore().deleteAllCookies()
            self.profile.clearHttpCache()
            QMessageBox.information(self, "Sesija očišćena", "Lokalni kolačići su obrisani. Sljedeće osvježavanje može tražiti novu prijavu.")

    def _save(self) -> None:
        interval = int(self.refresh_combo.currentData())
        self.settings.setValue("refresh_seconds", interval)
        self.settings.setValue("api/points_json_path", self.points_path.text().strip() or "balance")
        self.settings.setValue("api/messages_json_path", self.messages_path.text().strip() or "unread")
        ok, message = set_autostart(self.autostart.isChecked())
        if self.autostart.isChecked() and not ok:
            QMessageBox.warning(self, "Startup postavka", message)
        self.settings.sync()
        self.accept()
