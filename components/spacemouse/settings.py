"""Per-user encrypted identity/pairing and explicit HKCU logon preference."""
import json
import os
from pathlib import Path
import subprocess
import sys

from identity import new_identity
from windows_usb import protect, unprotect


def directory(role):
    if role not in ("server", "client"):
        raise ValueError("Invalid role")
    return Path(os.environ["LOCALAPPDATA"]) / "SpaceMouseLink" / role


def load(role):
    folder = directory(role)
    file = folder / "identity.dpapi"
    if file.exists():
        config = json.loads(unprotect(file.read_bytes()))
        if config.get("role") != role:
            raise ValueError("Stored identity role mismatch")
        return config
    config = {"role": role, **new_identity(), "auto_connect": False, "close_to_tray": True}
    save(config)
    return config


def save(config):
    folder = directory(config["role"])
    folder.mkdir(parents=True, exist_ok=True)
    temporary = folder / "identity.dpapi.tmp"
    temporary.write_bytes(protect(json.dumps(config).encode()))
    temporary.replace(folder / "identity.dpapi")


def startup_enabled(role):
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
            winreg.QueryValueEx(key, "SpaceMouseLink-" + role)
            return True
    except FileNotFoundError:
        return False


def set_startup(role, enabled):
    import winreg
    if role not in ("server", "client"):
        raise ValueError("Invalid role")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
        name = "SpaceMouseLink-" + role
        if enabled:
            if not getattr(sys, "frozen", False):
                raise RuntimeError("Install the packaged app before enabling launch at startup.")
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ,
                             subprocess.list2cmdline([sys.executable, "--role", role, "--tray"]))
        else:
            try:
                winreg.DeleteValue(key, name)
            except FileNotFoundError:
                pass
