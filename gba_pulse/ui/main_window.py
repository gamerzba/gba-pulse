from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

from PySide6.QtCore import Qt, QPoint, QSettings, QUrl, QSize
from PySide6.QtGui import QPixmap, QIcon, QDesktopServices
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QToolButton,
    QScrollArea, QSizePolicy, QApplication, QDialog, QMessageBox, QGraphicsDropShadowEffect,
)
from PySide6.QtWebEngineCore import QWebEngineProfile

from gba_pulse.config import APP_NAME, COLORS, FORUM_URL, RSS_URL
from gba_pulse.services.forum_session import ForumSession
from gba_pulse.ui.login_dialog import LoginDialog
from gba_pulse.ui.logo_loader import LogoLoader
from gba_pulse.ui.settings_dialog import SettingsDialog
from gba_pulse.ui.theme import GLOBAL_STYLE


def _safe_web_url(value: str) -> bool:
    parsed = urlparse(value or "")
    return parsed.scheme in {"https", "http"} and bool(parsed.netloc)


def _format_number(value) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "—"
    if isinstance(value, float) and not value.is_integer():
        return f"{value:,.1f}".replace(",", ".")
    return f"{int(value):,}".replace(",", ".")


def _short_status(value: str) -> str:
    text = str(value or "")
    if "mapirati" in text.lower() or "struktura" in text.lower():
        return "Format odgovora nije mapiran"
    if "403" in text or "401" in text or "prijav" in text.lower() or "sesija" in text.lower():
        return "Provjeri prijavu"
    if "ažurirano" in text.lower() or "primljen" in text.lower():
        return "Ažurirano"
    if not text:
        return "Čeka podatke"
    return text[:42]


class DragBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_offset: QPoint | None = None
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_offset = None
        super().mouseReleaseEvent(event)


class MetricCard(QFrame):
    def __init__(self, title: str, accent: str, parent=None):
        super().__init__(parent)
        self.setObjectName("raisedCard")
        # Keep these glanceable counters compact; the RSS panel gets the freed space.
        self.setFixedHeight(84)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 7, 12, 6)
        layout.setSpacing(2)

        top = QHBoxLayout()
        top.setSpacing(6)
        self.dot = QLabel("●")
        self.dot.setStyleSheet(f"color:{accent};font-size:8px;")
        self.heading = QLabel(title.upper())
        self.heading.setStyleSheet("color:#9AA5B8;font-size:9px;font-weight:800;letter-spacing:1px;")
        top.addWidget(self.dot)
        top.addWidget(self.heading)
        top.addStretch(1)
        layout.addLayout(top)

        self.value = QLabel("—")
        self.value.setStyleSheet("color:#F0F3F8;font-size:22px;font-weight:750;letter-spacing:-0.4px;")
        self.value.setMinimumHeight(25)
        layout.addWidget(self.value)
        self.status = QLabel("Čeka podatke")
        self.status.setStyleSheet("color:#6F7A8D;font-size:8px;")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        layout.addStretch(1)

    def set_metric(self, value, status: str, detail: str | None = None) -> None:
        self.value.setText(_format_number(value))
        self.status.setText(detail if detail else _short_status(status))
        self.status.setToolTip(status)
        color = "#7B8598" if value is None else "#F0F3F8"
        self.value.setStyleSheet(f"color:{color};font-size:22px;font-weight:750;letter-spacing:-0.4px;")


class FeedItemRow(QFrame):
    def __init__(self, title: str, summary: str, published: str, link: str, on_open, parent=None):
        super().__init__(parent)
        self._link = link
        self._on_open = on_open
        self.setCursor(Qt.CursorShape.PointingHandCursor if link else Qt.CursorShape.ArrowCursor)
        self.setStyleSheet("QFrame{background:transparent;border:1px solid transparent;border-radius:10px;} QFrame:hover{background:#0F1522;border-color:#202838;}")
        row = QHBoxLayout(self)
        row.setContentsMargins(9, 7, 7, 7)
        row.setSpacing(9)

        marker = QLabel("↗" if link else "•")
        marker.setFixedWidth(15)
        marker.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        marker.setStyleSheet("color:#FB9524;font-size:12px;font-weight:800;background:transparent;border:none;")
        marker.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        row.addWidget(marker)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(3)
        title_label = QLabel(title or "(Bez naslova)")
        title_label.setWordWrap(True)
        title_label.setTextFormat(Qt.TextFormat.PlainText)
        title_label.setMaximumHeight(34)
        title_label.setStyleSheet("color:#E5EAF3;font-size:10pt;font-weight:650;background:transparent;border:none;")
        title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        text_col.addWidget(title_label)
        sub = summary if summary else published
        if sub:
            sub_label = QLabel(sub[:100])
            sub_label.setTextFormat(Qt.TextFormat.PlainText)
            sub_label.setWordWrap(False)
            sub_label.setStyleSheet("color:#748095;font-size:8.5pt;background:transparent;border:none;")
            sub_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            text_col.addWidget(sub_label)
        row.addLayout(text_col, 1)

        if link:
            arrow = QLabel("↗")
            arrow.setStyleSheet("color:#657188;font-size:11px;background:transparent;border:none;")
            arrow.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            row.addWidget(arrow, 0, Qt.AlignmentFlag.AlignTop)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._link and _safe_web_url(self._link):
            self._on_open(self._link)
        super().mouseReleaseEvent(event)


class DesktopLogo(QWidget):
    def __init__(self, on_restore, settings: QSettings, icon_path: str, parent=None):
        super().__init__(parent)
        self._on_restore = on_restore
        self.settings = settings
        self._drag_offset: QPoint | None = None
        self._press_pos: QPoint | None = None
        self.setObjectName("DesktopLogo")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(68, 68)
        self.setToolTip("G.ba Pulse — klikni za otvaranje")
        shell = QFrame(self)
        shell.setGeometry(1, 1, 66, 66)
        shell.setStyleSheet("QFrame{background:#0B101B;border:1px solid #30394A;border-radius:21px;}")
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(9, 9, 9, 9)
        shell.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.logo = QLabel("G.")
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo.setStyleSheet("color:#FB9524;font-size:26px;font-weight:900;background:transparent;border:none;")
        self.logo.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.logo)
        self.setWindowIcon(QIcon(icon_path))
        self._set_saved_position()

    def set_logo_pixmap(self, pixmap: QPixmap) -> None:
        self.logo.setPixmap(pixmap.scaled(43, 43, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def _set_saved_position(self) -> None:
        point = self.settings.value("window/logo_pos")
        if point is not None and hasattr(point, "x"):
            self.move(point)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.globalPosition().toPoint()
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            moved = self._press_pos is not None and (event.globalPosition().toPoint() - self._press_pos).manhattanLength() > 5
            self.settings.setValue("window/logo_pos", self.pos())
            self._drag_offset = None
            self._press_pos = None
            if not moved:
                self.hide()
                self._on_restore()
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class PulseWindow(QWidget):
    def __init__(self, settings: QSettings, profile: QWebEngineProfile, session: ForumSession, logo_loader: LogoLoader, icon_path: str):
        super().__init__()
        self.settings = settings
        self.profile = profile
        self.session = session
        self.logo_loader = logo_loader
        self.icon_path = icon_path
        self._exiting = False
        self._has_data = False
        self._previous_connection = "warning"

        self.setObjectName("PulseWindow")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(392, 690)
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(icon_path))
        self.setStyleSheet(GLOBAL_STYLE + "QWidget#PulseWindow{background:transparent;} QFrame#mainShell{background:#060911;border:1px solid #202838;border-radius:21px;}")

        self.shell = QFrame(self)
        self.shell.setObjectName("mainShell")
        root = QVBoxLayout(self)
        root.setContentsMargins(1, 1, 1, 1)
        root.addWidget(self.shell)

        self.layout_root = QVBoxLayout(self.shell)
        self.layout_root.setContentsMargins(17, 14, 17, 13)
        self.layout_root.setSpacing(10)

        self._build_header()
        self._build_intro()
        self._build_metrics()
        self._build_online()
        self._build_feed()
        self._build_quick_links()
        self._build_footer()

        self.logo_window = DesktopLogo(self.restore_panel, settings, icon_path)
        self.logo_loader.pixmap_ready.connect(self._set_logo)
        self.logo_loader.load()
        self.session.data_updated.connect(self.apply_data)
        self.session.state_changed.connect(self.apply_state)

        saved_pos = self.settings.value("window/main_pos")
        if saved_pos is not None and hasattr(saved_pos, "x"):
            self.move(saved_pos)
        else:
            screen = QApplication.primaryScreen()
            if screen:
                avail = screen.availableGeometry()
                x = max(avail.left() + 10, min(avail.right() - self.width() - 10, avail.right() - self.width() - 25))
                y = max(avail.top() + 10, min(avail.bottom() - self.height() - 10, avail.top() + 80))
                self.move(x, y)

    def _build_header(self) -> None:
        bar = DragBar(self.shell)
        bar.setFixedHeight(43)
        row = QHBoxLayout(bar)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(9)
        self.logo_label = QLabel("G.")
        self.logo_label.setFixedSize(39, 39)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.setStyleSheet("background:#101725;border:1px solid #232D3E;border-radius:12px;color:#FB9524;font-size:18pt;font-weight:900;")
        self.logo_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        row.addWidget(self.logo_label)

        title_col = QVBoxLayout()
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(1)
        title = QLabel("G.ba Pulse")
        title.setStyleSheet("color:#F0F3F9;font-size:14pt;font-weight:800;letter-spacing:-.3px;")
        title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        kicker = QLabel("GAMERZ.BA  /  COMMUNITY")
        kicker.setStyleSheet("color:#FB9524;font-size:7.5pt;font-weight:800;letter-spacing:1.1px;")
        kicker.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        title_col.addWidget(title)
        title_col.addWidget(kicker)
        row.addLayout(title_col, 1)

        self.refresh_btn = self._icon_button("↻", "Osvježi sada", self.session.refresh)
        self.hide_btn = self._icon_button("◉", "Sakrij panel — ostavi logo", self.hide_to_logo)
        self.settings_btn = self._icon_button("⚙", "Postavke", self.open_settings)
        close_btn = self._icon_button("×", "Zatvori aplikaciju", self.close_app)
        row.addWidget(self.refresh_btn)
        row.addWidget(self.hide_btn)
        row.addWidget(self.settings_btn)
        row.addWidget(close_btn)
        self.layout_root.addWidget(bar)

    def _icon_button(self, text: str, tooltip: str, slot) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("quietButton")
        button.setFixedSize(28, 30)
        button.setToolTip(tooltip)
        button.setStyleSheet(button.styleSheet() + "QPushButton{font-size:15px;font-weight:600;}")
        button.clicked.connect(slot)
        return button

    def _build_intro(self) -> None:
        row = QHBoxLayout()
        row.setContentsMargins(2, 0, 2, 0)
        col = QVBoxLayout()
        col.setSpacing(3)
        eyebrow = QLabel("TVOJ FORUM, NA JEDAN POGLED")
        eyebrow.setStyleSheet("color:#8994A8;font-size:8px;font-weight:800;letter-spacing:1.4px;")
        self.heading = QLabel("Ima li šta novo?")
        self.heading.setStyleSheet("color:#F0F3F9;font-size:18pt;font-weight:750;letter-spacing:-.6px;")
        col.addWidget(eyebrow)
        col.addWidget(self.heading)
        row.addLayout(col, 1)

        self.connection_pill = QLabel("●  POVEZIVANJE")
        self.connection_pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.connection_pill.setStyleSheet("background:#171D2A;color:#A3AFC2;border:1px solid #273044;border-radius:9px;padding:7px 8px;font-size:7.5pt;font-weight:800;letter-spacing:.4px;")
        self.connection_pill.setMaximumWidth(112)
        row.addWidget(self.connection_pill, 0, Qt.AlignmentFlag.AlignVCenter)
        self.layout_root.addLayout(row)

    def _build_metrics(self) -> None:
        row = QHBoxLayout()
        row.setSpacing(9)
        self.points_card = MetricCard("Bodovi", COLORS["accent"])
        self.messages_card = MetricCard("Poruke", COLORS["accent_2"])
        row.addWidget(self.points_card, 1)
        row.addWidget(self.messages_card, 1)
        self.layout_root.addLayout(row)

    def _build_online(self) -> None:
        card = QFrame()
        card.setObjectName("surfaceCard")
        row = QHBoxLayout(card)
        row.setContentsMargins(12, 9, 12, 9)
        row.setSpacing(9)
        self.online_dot = QLabel("●")
        self.online_dot.setStyleSheet("color:#8CBF2B;font-size:10px;")
        row.addWidget(self.online_dot)
        col = QVBoxLayout()
        col.setSpacing(1)
        title = QLabel("GBA UŽIVO")
        title.setStyleSheet("color:#9AA5B8;font-size:8px;font-weight:800;letter-spacing:1.1px;")
        self.online_value = QLabel("— članova online")
        self.online_value.setStyleSheet("color:#E9EDF5;font-size:10pt;font-weight:650;")
        col.addWidget(title)
        col.addWidget(self.online_value)
        row.addLayout(col, 1)
        self.online_status = QLabel("Čeka podatke")
        self.online_status.setStyleSheet("color:#6F7A8D;font-size:8pt;")
        row.addWidget(self.online_status)
        self.layout_root.addWidget(card)

    def _build_feed(self) -> None:
        header = QHBoxLayout()
        label_col = QVBoxLayout()
        label_col.setSpacing(2)
        title = QLabel("ZADNJE SA FORUMA")
        title.setStyleSheet("color:#F0F3F9;font-size:10pt;font-weight:800;letter-spacing:.6px;")
        subtitle = QLabel("Teme i razgovori koji se upravo vrte")
        subtitle.setStyleSheet("color:#7A869A;font-size:8.5pt;")
        label_col.addWidget(title)
        label_col.addWidget(subtitle)
        header.addLayout(label_col, 1)
        self.rss_button = QPushButton("RSS ↗")
        self.rss_button.setObjectName("quietButton")
        self.rss_button.setFixedHeight(28)
        self.rss_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(RSS_URL)))
        header.addWidget(self.rss_button, 0, Qt.AlignmentFlag.AlignVCenter)
        self.layout_root.addLayout(header)

        self.feed_scroll = QScrollArea()
        self.feed_scroll.setWidgetResizable(True)
        self.feed_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Let the feed absorb the extra room freed by the compact counter cards.
        self.feed_scroll.setMinimumHeight(205)
        self.feed_content = QWidget()
        self.feed_content.setStyleSheet("background:transparent;")
        self.feed_layout = QVBoxLayout(self.feed_content)
        self.feed_layout.setContentsMargins(0, 0, 0, 0)
        self.feed_layout.setSpacing(3)
        self.feed_placeholder = QLabel("RSS se još učitava…")
        self.feed_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.feed_placeholder.setWordWrap(True)
        self.feed_placeholder.setStyleSheet("background:#0B101B;border:1px dashed #273044;border-radius:12px;color:#8E98AA;padding:22px;font-size:9pt;")
        self.feed_layout.addWidget(self.feed_placeholder)
        self.feed_layout.addStretch(1)
        self.feed_scroll.setWidget(self.feed_content)
        self.layout_root.addWidget(self.feed_scroll, 1)

    def _build_quick_links(self) -> None:
        row = QHBoxLayout()
        row.setSpacing(7)
        forum = QPushButton("↗  FORUM")
        forum.setObjectName("primaryButton")
        forum.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(FORUM_URL)))
        rss = QPushButton("◔  RSS")
        rss.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(RSS_URL)))
        login = QPushButton("◎  PRIJAVA")
        login.clicked.connect(self.open_login)
        row.addWidget(forum, 1)
        row.addWidget(rss)
        row.addWidget(login)
        self.layout_root.addLayout(row)

    def _build_footer(self) -> None:
        row = QHBoxLayout()
        row.setContentsMargins(2, 0, 2, 0)
        self.footer_status = QLabel("●  ČEKAM VEZU")
        self.footer_status.setStyleSheet("color:#727E92;font-size:7.5pt;font-weight:750;letter-spacing:.5px;")
        self.checked_label = QLabel("—")
        self.checked_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.checked_label.setStyleSheet("color:#626D80;font-size:8pt;")
        row.addWidget(self.footer_status, 1)
        row.addWidget(self.checked_label)
        self.layout_root.addLayout(row)

    def _set_logo(self, pixmap: QPixmap) -> None:
        self.logo_label.setPixmap(pixmap.scaled(34, 34, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.logo_label.setText("")
        self.logo_window.set_logo_pixmap(pixmap)

    def _open_url(self, url: str) -> None:
        if _safe_web_url(url):
            QDesktopServices.openUrl(QUrl(url))

    def open_login(self) -> None:
        dialog = LoginDialog(self.profile, self)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            self.session.refresh()

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self.profile, self.session.last_diagnostics(), self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            interval = int(self.settings.value("refresh_seconds", 60))
            self.session.set_refresh_interval(interval)
            self.session.refresh()

    def hide_to_logo(self) -> None:
        self.settings.setValue("window/main_pos", self.pos())
        if not self.logo_window.isVisible():
            self.logo_window.move(self.pos() + QPoint(self.width() - 84, 18))
        self.hide()
        self.logo_window.show()
        self.logo_window.raise_()

    def restore_panel(self) -> None:
        point = self.settings.value("window/main_pos")
        if point is not None and hasattr(point, "x"):
            self.move(point)
        self.show()
        self.raise_()
        self.activateWindow()
        self.session.refresh()

    def apply_state(self, text: str) -> None:
        safe_text = str(text or "")
        upper = safe_text.upper()
        self.footer_status.setText("●  " + upper[:40])
        self.footer_status.setToolTip(safe_text)

        # Keep the header status informative before the first completed poll.
        # Once a data batch is applied, apply_data owns the connection badge so
        # this transient state cannot overwrite a confirmed online/offline result.
        if not self._has_data:
            lower = safe_text.lower()
            if any(word in lower for word in ("greška", "isteklo", "nije moguće", "nije moguce", "offline")):
                self.connection_pill.setText("●  GREŠKA VEZE")
                self.connection_pill.setStyleSheet("background:#2B1A1A;color:#E59B91;border:1px solid #51302F;border-radius:9px;padding:7px 8px;font-size:7.5pt;font-weight:800;letter-spacing:.4px;")
            elif any(word in lower for word in ("osvjež", "provjer", "podatke")):
                self.connection_pill.setText("●  OSVJEŽAVAM")
                self.connection_pill.setStyleSheet("background:#171D2A;color:#A3AFC2;border:1px solid #273044;border-radius:9px;padding:7px 8px;font-size:7.5pt;font-weight:800;letter-spacing:.4px;")

    def apply_data(self, data: dict) -> None:
        self._has_data = True
        points = data.get("points", {})
        messages = data.get("messages", {})
        self.points_card.set_metric(points.get("value"), points.get("status", "Čeka podatke"))
        notifications = data.get("notifications", {}) or {}
        notification_count = notifications.get("value")
        message_detail = (
            f"{_format_number(notification_count)} obavijesti"
            if messages.get("value") is not None and notification_count is not None
            else None
        )
        self.messages_card.set_metric(
            messages.get("value"), messages.get("status", "Čeka podatke"), message_detail
        )

        online = data.get("online_count")
        self.online_value.setText(f"{_format_number(online)} članova online" if online is not None else "Broj članova nije dostupan")
        self.online_status.setText(_short_status(data.get("online_status", "")))
        self.online_status.setToolTip(data.get("online_status", ""))

        items = data.get("rss_items", []) or []
        while self.feed_layout.count():
            item = self.feed_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                child_layout = item.layout()
                while child_layout.count():
                    child = child_layout.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
        if items:
            for item in items[:5]:
                row = FeedItemRow(item.title, item.summary, item.published, item.link, self._open_url, self.feed_content)
                self.feed_layout.addWidget(row)
        else:
            placeholder = QLabel("RSS trenutno nema dostupnih stavki. Provjeri vezu ili osvježi ponovo.")
            placeholder.setWordWrap(True)
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("background:#0B101B;border:1px dashed #273044;border-radius:12px;color:#8E98AA;padding:22px;font-size:9pt;")
            self.feed_layout.addWidget(placeholder)
        self.feed_layout.addStretch(1)

        checked = data.get("checked_at", "—")
        self.checked_label.setText(f"PROVJERENO {checked}")
        state = data.get("connection_state", "warning")
        if state == "ok":
            self.connection_pill.setText("●  POVEZANO")
            self.connection_pill.setStyleSheet("background:#14271B;color:#A9D56B;border:1px solid #28472C;border-radius:9px;padding:7px 8px;font-size:7.5pt;font-weight:800;letter-spacing:.4px;")
            self.footer_status.setText("●  PODACI OSVJEŽENI")
            self.footer_status.setStyleSheet("color:#8CBF2B;font-size:7.5pt;font-weight:750;letter-spacing:.5px;")
        elif state == "warning":
            self.connection_pill.setText("●  DJELOMIČNO")
            self.connection_pill.setStyleSheet("background:#2F2418;color:#FB9524;border:1px solid #5D3A1A;border-radius:9px;padding:7px 8px;font-size:7.5pt;font-weight:800;letter-spacing:.4px;")
            self.footer_status.setText("●  DJELOMIČNA VEZA")
            self.footer_status.setStyleSheet("color:#FB9524;font-size:7.5pt;font-weight:750;letter-spacing:.5px;")
        else:
            self.connection_pill.setText("●  OFFLINE")
            self.connection_pill.setStyleSheet("background:#2B1A1A;color:#E59B91;border:1px solid #51302F;border-radius:9px;padding:7px 8px;font-size:7.5pt;font-weight:800;letter-spacing:.4px;")
            self.footer_status.setText("●  VEZA NIJE DOSTUPNA")
            self.footer_status.setStyleSheet("color:#E06B69;font-size:7.5pt;font-weight:750;letter-spacing:.5px;")
        self._previous_connection = state

    def close_app(self) -> None:
        self.close()

    def closeEvent(self, event) -> None:
        self._exiting = True
        self.settings.setValue("window/main_pos", self.pos())
        self.logo_window.hide()
        self.session.stop()
        self.settings.sync()
        event.accept()
        QApplication.quit()
