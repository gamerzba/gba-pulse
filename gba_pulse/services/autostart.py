"""Opt-in Windows logon startup registration."""
from __future__ import annotations
import os
import sys
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "GbaPulse"


def command_for_startup() -> str:
    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable).resolve()}"'
    entry = Path(sys.argv[0]).resolve()
    return f'"{Path(sys.executable).resolve()}" "{entry}"'


def is_autostart_enabled() -> bool:
    if os.name != "nt":
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, VALUE_NAME)
            return bool(value)
    except OSError:
        return False


def set_autostart(enabled: bool) -> tuple[bool, str]:
    if os.name != "nt":
        return False, "Automatsko pokretanje dostupno je samo na Windowsu."
    import winreg
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            if enabled:
                winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, command_for_startup())
            else:
                try:
                    winreg.DeleteValue(key, VALUE_NAME)
                except FileNotFoundError:
                    pass
        return True, "Postavka automatskog pokretanja je spremljena."
    except OSError as exc:
        return False, f"Windows nije dozvolio promjenu startup postavke: {exc}"
