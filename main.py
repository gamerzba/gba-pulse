from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QSettings, QStandardPaths
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtWebEngineCore import QWebEngineProfile

from gba_pulse.config import APP_ID, APP_NAME
from gba_pulse.paths import resource_path
from gba_pulse.services.forum_session import ForumSession
from gba_pulse.ui.logo_loader import LogoLoader
from gba_pulse.ui.main_window import PulseWindow
from gba_pulse.ui.theme import GLOBAL_STYLE


def main() -> int:
    QCoreApplication.setOrganizationName("Gamerz.ba")
    QCoreApplication.setApplicationName(APP_ID)
    QCoreApplication.setApplicationVersion("0.1.2")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Gamerz.ba")
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")
    app.setStyleSheet(GLOBAL_STYLE)

    icon_path = resource_path("assets/gba_pulse_mark.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    data_root = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))
    profile_root = data_root / "web-profile"
    cache_root = data_root / "web-cache"
    profile_root.mkdir(parents=True, exist_ok=True)
    cache_root.mkdir(parents=True, exist_ok=True)

    profile = QWebEngineProfile("GbaPulseProfile", app)
    profile.setPersistentStoragePath(str(profile_root))
    profile.setCachePath(str(cache_root))
    profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)

    settings = QSettings("Gamerz.ba", APP_ID)
    session = ForumSession(profile, settings, app)
    logo_loader = LogoLoader(app)
    window = PulseWindow(settings, profile, session, logo_loader, str(icon_path))
    window.show()
    return app.exec()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        # Keep top-level crashes understandable for a double-clicked Windows app.
        try:
            app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(None, "G.ba Pulse — greška", f"Aplikacija nije mogla pokrenuti sučelje.\n\n{exc}")
        except Exception:
            print(f"G.ba Pulse startup error: {exc}", file=sys.stderr)
        raise SystemExit(1)
