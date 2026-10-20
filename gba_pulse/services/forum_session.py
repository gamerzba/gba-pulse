"""Authenticated requests through a persistent, first-party WebEngine profile."""
from __future__ import annotations

import json

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile

from gba_pulse.config import DEFAULT_REFRESH_SECONDS, FORUM_URL, MESSAGES_URL, POINTS_URL, RSS_URL
from gba_pulse.services.fetch_result import decode_fetch_snapshot
from gba_pulse.services.fetch_script import build_fetch_script
from gba_pulse.services.response_processor import process_responses


class ForumSession(QObject):
    """Poll forum endpoints without blocking the UI thread.

    WebEngine's JS callback representation varies slightly by Qt version, so the
    result is normalized before it reaches the response processor. Every failed
    cycle produces a visible unavailable state instead of leaving initial
    placeholders on screen forever.
    """
    data_updated = Signal(dict)
    state_changed = Signal(str)

    ENDPOINTS = {
        "messages": MESSAGES_URL,
        "points": POINTS_URL,
        "rss": RSS_URL,
        "home": FORUM_URL,
    }

    def __init__(self, profile: QWebEngineProfile, settings, parent: QObject | None = None):
        super().__init__(parent)
        self.profile = profile
        self.settings = settings
        self.page = QWebEnginePage(profile, self)
        self.page.loadFinished.connect(self._on_loaded)
        self._loaded = False
        self._loading = True
        self._inflight = False
        self._stopped = False
        self._last_data: dict = {}
        self._consecutive_failures = 0
        self._active_batch_token: str | None = None
        self._received_responses: dict[str, dict] = {}

        self._page_load_timeout = QTimer(self)
        self._page_load_timeout.setSingleShot(True)
        self._page_load_timeout.timeout.connect(self._on_page_load_timeout)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(self._refresh_interval() * 1000)

        # Poll a tiny JS sentinel for compatibility across Qt versions. A separate
        # watchdog ensures it cannot stay in the loading state indefinitely.
        self._result_watch = QTimer(self)
        self._result_watch.setInterval(300)
        self._result_watch.timeout.connect(self._check_js_result)
        self._request_timeout = QTimer(self)
        self._request_timeout.setSingleShot(True)
        self._request_timeout.timeout.connect(self._on_request_timeout)

        self.state_changed.emit("Uspostavljam vezu s Gamerz.ba…")
        self._page_load_timeout.start(18000)
        self.page.setUrl(QUrl(FORUM_URL))

    def _refresh_interval(self) -> int:
        try:
            return max(30, min(300, int(self.settings.value("refresh_seconds", DEFAULT_REFRESH_SECONDS))))
        except (TypeError, ValueError):
            return DEFAULT_REFRESH_SECONDS

    def set_refresh_interval(self, seconds: int) -> None:
        seconds = seconds if seconds in (30, 60, 300) else DEFAULT_REFRESH_SECONDS
        self.timer.setInterval(seconds * 1000)
        if not self.timer.isActive():
            self.timer.start()

    def _on_loaded(self, ok: bool) -> None:
        if self._stopped:
            return
        self._page_load_timeout.stop()
        self._loading = False
        self._loaded = bool(ok)
        if ok:
            self.state_changed.emit("Povezano s Gamerz.ba; provjeravam podatke…")
            self.refresh()
        else:
            self.state_changed.emit("Stranicu nije moguće učitati. Provjeri internet i pokušaj ponovo.")
            self._publish_unavailable("network", "Stranicu Gamerz.ba nije moguće učitati.")
            QTimer.singleShot(3000, self.refresh)

    def _on_page_load_timeout(self) -> None:
        if self._stopped or self._loaded:
            return
        self._loading = False
        self._publish_unavailable("timeout", "Učitavanje početne stranice je isteklo.")
        self.state_changed.emit("Učitavanje Gamerz.ba je isteklo; pokušat ću ponovo.")
        QTimer.singleShot(3000, self.refresh)

    def refresh(self) -> None:
        if self._stopped:
            return
        if not self._loaded:
            self.state_changed.emit("Čekam vezu s Gamerz.ba…")
            if not self._loading:
                self._loading = True
                self._page_load_timeout.start(18000)
                self.page.setUrl(QUrl(FORUM_URL))
            return
        if self._inflight:
            return
        self._inflight = True
        self._active_batch_token = None
        self._received_responses = {}
        self.state_changed.emit("Osvježavam podatke…")
        self._request_timeout.start(20000)
        # The script returns the new batch token immediately after scheduling
        # requests. The UI then polls snapshots so completed endpoints update
        # independently instead of waiting for the slowest API.
        self.page.runJavaScript(build_fetch_script(), self._on_batch_started)

    def _on_batch_started(self, token) -> None:
        if self._stopped or not self._inflight:
            return
        if token is None:
            # The watchdog will turn this into a visible failure if Qt never
            # returns the script result.
            return
        self._active_batch_token = str(token)
        self._result_watch.start()

    def _check_js_result(self) -> None:
        if not self._inflight or self._stopped:
            self._result_watch.stop()
            return
        # Return a single JSON string regardless of Qt's native JS-to-QVariant
        # conversion, with a token to reject a stale callback from an old batch.
        script = "(function(){const r=window.__gbaPulseResponse;if(!r||Object.keys(r).length===0)return null;return JSON.stringify({token:window.__gbaPulseBatchId||null,responses:Object.values(r),complete:!!window.__gbaPulseDone});})()"
        self.page.runJavaScript(script, self._on_fetch_result)

    def _finish_cycle(self) -> None:
        self._inflight = False
        self._result_watch.stop()
        self._request_timeout.stop()

    def _on_fetch_result(self, raw_result) -> None:
        if self._stopped or not self._inflight or raw_result is None:
            return
        try:
            snapshot = decode_fetch_snapshot(raw_result)
            token = snapshot.get("token")
            if self._active_batch_token and token and token != self._active_batch_token:
                return  # Late callback from a timed-out/replaced request batch.
            responses_list = snapshot["responses"]
            changed = False
            for item in responses_list:
                key = item.get("key")
                if key not in self.ENDPOINTS:
                    continue
                if key not in self._received_responses:
                    self._received_responses[key] = item
                    changed = True
            complete = bool(snapshot.get("complete"))
            if not changed and not complete:
                return
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            self._finish_cycle()
            self._consecutive_failures += 1
            safe_reason = f"Qt rezultat: {type(raw_result).__name__}; greška parsera: {type(exc).__name__}."
            self._publish_unavailable("decode", safe_reason)
            self.state_changed.emit("Odgovor web-prozora nije moguće obraditi; pokušaj ponovo.")
            return

        # Publish each endpoint as soon as it completes. A stalled personalized
        # endpoint no longer hides already-received RSS or online-member data.
        if self._received_responses:
            paths = {
                "points": str(self.settings.value("api/points_json_path", "balance") or "balance").strip(),
                "messages": str(self.settings.value("api/messages_json_path", "unread") or "unread").strip(),
            }
            data = process_responses(self._received_responses, paths)
            self._last_data = data
            self.data_updated.emit(data)

        if complete or set(self.ENDPOINTS).issubset(self._received_responses):
            self._finish_cycle()
            self._consecutive_failures = 0 if self._last_data.get("connection_state") == "ok" else self._consecutive_failures + 1
            self.state_changed.emit("Podaci osvježeni" if self._last_data.get("connection_state") == "ok" else "Djelimična ili neuspješna veza")

    def _on_request_timeout(self) -> None:
        if self._stopped or not self._inflight:
            return
        self._finish_cycle()
        self._consecutive_failures += 1
        self._publish_unavailable("timeout", "Osvježavanje je isteklo. Provjeri vezu ili ponovi pokušaj.")
        self.state_changed.emit("Zahtjevu je isteklo vrijeme; pokušaj ponovo.")

    def _publish_unavailable(self, error: str, explanation: str) -> None:
        responses = {}
        for key, url in self.ENDPOINTS.items():
            responses[key] = {
                "key": key,
                "requestedUrl": url,
                "status": 0,
                "ok": False,
                "url": url,
                "redirected": False,
                "contentType": "",
                "body": "",
                "error": error if error in {"timeout", "network"} else "network",
            }
        data = process_responses(responses)
        data["connection_state"] = "error"
        data["diagnostic_note"] = explanation
        self._last_data = data
        self.data_updated.emit(data)

    def last_diagnostics(self) -> dict:
        return self._last_data

    def stop(self) -> None:
        self._stopped = True
        self.timer.stop()
        self._result_watch.stop()
        self._request_timeout.stop()
        self._page_load_timeout.stop()
        try:
            self.page.triggerAction(QWebEnginePage.WebAction.Stop)
        except Exception:
            pass
