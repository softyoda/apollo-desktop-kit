"""Narrow Windows USB operations. Never invoke a shell with user/device text."""
import ctypes
import json
import os
from pathlib import Path
import re
import subprocess

from protocol import valid_busid

CREATE_NO_WINDOW = 0x08000000


def run(argv, timeout=30):
    result = subprocess.run([str(x) for x in argv], capture_output=True, text=True,
                            errors="replace", timeout=timeout, creationflags=CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or "Command failed").strip()[:1200])
    return result.stdout.strip()


def executable(role):
    root = Path(os.environ.get("ProgramW6432", os.environ.get("ProgramFiles", "C:/Program Files")))
    path = root / ("usbipd-win/usbipd.exe" if role == "server" else "USBip/usbip.exe")
    if not path.is_file():
        raise RuntimeError("USB driver/tool is not installed. Run this computer's installer first.")
    return path


def check_firewall():
    # Setup creates explicit non-loopback block rules; refuse sharing if removed.
    script = """
$ErrorActionPreference='Stop'
$profiles = @(Get-NetFirewallProfile -PolicyStore ActiveStore)
if (@($profiles | Where-Object { -not $_.Enabled }).Count) { throw 'Windows Firewall must be enabled.' }
if (@($profiles | Where-Object { $_.AllowLocalFirewallRules -eq 'False' }).Count) { throw 'Company policy disables local firewall rules. IT must provide equivalent USB protection.' }
$rule = Get-NetFirewallRule -PolicyStore ActiveStore -Name 'SpaceMouseLink-USB-LocalOnly' -ErrorAction Stop
if ($rule.Enabled -ne 'True' -or $rule.Direction -ne 'Inbound' -or $rule.Action -ne 'Block') { throw 'USB firewall protection is not active.' }
$port = $rule | Get-NetFirewallPortFilter
if ($port.Protocol -ne 'TCP' -or $port.LocalPort -ne '3240') { throw 'USB firewall protection was changed.' }
$addresses = @($rule | Get-NetFirewallAddressFilter | Select-Object -ExpandProperty RemoteAddress)
foreach ($required in @('0.0.0.0-126.255.255.255','128.0.0.0-255.255.255.255','::2-ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff')) {
 if ($addresses -notcontains $required) { throw 'USB firewall address protection was changed.' }
}
"""
    run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script])


def devices():
    state = json.loads(run([executable("server"), "state"]))
    return [d for d in state.get("Devices", [])
            if "VID_256F&PID_C635" in d.get("InstanceId", "").upper()
            and valid_busid(d.get("BusId"))]


def validate_shared_device(busid):
    if not valid_busid(busid):
        raise ValueError("Invalid bus ID")
    check_firewall()
    matches = [d for d in devices() if d["BusId"] == busid]
    if len(matches) != 1:
        raise RuntimeError("The selected SpaceMouse is no longer connected")
    d = matches[0]
    if d.get("ClientIPAddress"):
        raise RuntimeError("SpaceMouse is already in use by a USB/IP client")
    if not d.get("PersistedGuid"):
        raise RuntimeError("Select Prepare USB device first. Windows will request administrator approval once.")


def unbind_device(busid):
    if not valid_busid(busid):
        raise ValueError("Invalid bus ID")
    # Never unbind an arbitrary newly inserted device occupying the old port.
    if any(d["BusId"] == busid for d in devices()):
        run([executable("server"), "unbind", "--busid", busid])


def attach_device(busid, port):
    if not valid_busid(busid) or not 1 <= port <= 65535:
        raise ValueError("Invalid USB attachment")
    result = run([executable("client"), "--tcp-port", str(port), "attach", "--once", "--terse",
                  "--remote", "127.0.0.1", "--bus-id", busid], timeout=50)
    if not re.fullmatch(r"[0-9]{1,3}", result) or not 1 <= int(result) <= 255:
        raise RuntimeError("USB driver did not report an attached port: " + result[:250])
    return int(result)


def detach_device(port):
    if not isinstance(port, int) or not 1 <= port <= 255:
        raise ValueError("Invalid USB port")
    run([executable("client"), "detach", "--port", str(port)])


class Blob(ctypes.Structure):
    _fields_ = [("length", ctypes.c_ulong), ("data", ctypes.POINTER(ctypes.c_ubyte))]


def unprotect(data):
    buf = ctypes.create_string_buffer(data)
    src = Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte)))
    dst = Blob()
    if not ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(src), None, None, None, None,
                                                 1, ctypes.byref(dst)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(dst.data, dst.length)
    finally:
        ctypes.windll.kernel32.LocalFree(dst.data)


def protect(data):
    buf = ctypes.create_string_buffer(data)
    src = Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte)))
    dst = Blob()
    # Current-user scope: deliberately omit CRYPTPROTECT_LOCAL_MACHINE.
    if not ctypes.windll.crypt32.CryptProtectData(ctypes.byref(src), "SpaceMouse Link", None, None,
                                               None, 1, ctypes.byref(dst)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(dst.data, dst.length)
    finally:
        ctypes.windll.kernel32.LocalFree(dst.data)


def prepare_device(busid, resource_dir):
    if not valid_busid(busid):
        raise ValueError("Invalid bus ID")
    script = Path(resource_dir) / "Prepare-Device.ps1"
    # This script resides in the administrator-writable installation directory.
    command = subprocess.list2cmdline([str(script), "-BusId", busid])
    shell = str(Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe")
    class ExecuteInfo(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_ulong), ("fMask", ctypes.c_ulong), ("hwnd", ctypes.c_void_p),
                    ("lpVerb", ctypes.c_wchar_p), ("lpFile", ctypes.c_wchar_p), ("lpParameters", ctypes.c_wchar_p),
                    ("lpDirectory", ctypes.c_wchar_p), ("nShow", ctypes.c_int), ("hInstApp", ctypes.c_void_p),
                    ("lpIDList", ctypes.c_void_p), ("lpClass", ctypes.c_wchar_p), ("hkeyClass", ctypes.c_void_p),
                    ("dwHotKey", ctypes.c_ulong), ("hIcon", ctypes.c_void_p), ("hProcess", ctypes.c_void_p)]
    info = ExecuteInfo()
    info.cbSize = ctypes.sizeof(info)
    info.fMask = 0x40
    info.lpVerb, info.lpFile = "runas", shell
    info.lpParameters = "-NoProfile -ExecutionPolicy Bypass -File " + command
    info.nShow = 0
    if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(info)):
        raise RuntimeError("USB preparation was cancelled or could not start.")
    handle = ctypes.c_void_p(info.hProcess)
    try:
        if ctypes.windll.kernel32.WaitForSingleObject(handle, 120000) != 0:
            raise RuntimeError("USB preparation is still running. Finish its Windows prompt, then Refresh.")
        code = ctypes.c_ulong()
        ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        if code.value:
            raise RuntimeError("USB preparation failed. Check the device and Windows Firewall, then retry.")
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)
