"""SpaceMouse Link: normal-user desktop/tray app. Elevation is a separate USB step."""
import argparse
import ctypes
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

os.environ["AUTOBAHN_USE_NVX"] = "0"
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from identity import make_invitation, parse_invitation, short_id
from icon_art import icon
import settings
import windows_usb

VERSION = "0.2.0-beta.1"


def resources():
    return Path(getattr(sys, "_MEIPASS", Path(__file__).parent))


class Window:
    def __init__(self, root, config, start_hidden=False, preview=False):
        from twisted.internet import reactor
        self.root, self.config, self.reactor = root, config, reactor
        self.role = config["role"]
        self.events = queue.Queue()
        self.session = self.pairing = None
        self.busy = self.pair_busy = self.quitting = False
        self.manual_pause = False
        self.retry_delay = 3
        self.retry_timer = None
        self.devices = []
        self.invitation_text = ""
        self.tray = None
        self.preview = preview
        self.last_report = None
        self.autostart = settings.startup_enabled(self.role) if not preview else False
        title = "Server" if self.role == "server" else "Client"
        root.title("SpaceMouse Link · " + title)
        root.geometry("740x660")
        root.minsize(680, 610)
        root.configure(bg="#f4f7fb")
        try:
            root.iconbitmap(str(resources() / "assets/spacemouse.ico"))
        except tk.TclError:
            pass
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#f4f7fb")
        style.configure("TLabel", background="#f4f7fb", foreground="#172b42", font=("Segoe UI", 10))
        style.configure("Muted.TLabel", foreground="#526780")
        style.configure("Title.TLabel", font=("Segoe UI", 23, "bold"))
        style.configure("Section.TLabel", font=("Segoe UI", 12, "bold"))
        style.configure("TButton", font=("Segoe UI", 10), padding=(14, 8))
        style.configure("Primary.TButton", background="#1764ae", foreground="white")
        style.map("Primary.TButton", background=[("active", "#114f8e"), ("disabled", "#9cb4ca")])
        style.configure("TCheckbutton", background="#f4f7fb", font=("Segoe UI", 10))
        style.configure("TNotebook", background="#f4f7fb", borderwidth=0)
        style.configure("TNotebook.Tab", font=("Segoe UI", 10), padding=(16, 9))
        body = ttk.Frame(root, padding=24)
        body.pack(fill="both", expand=True)
        header = ttk.Frame(body)
        header.pack(fill="x")
        from PIL import ImageTk
        self.logo = ImageTk.PhotoImage(icon(size=58))
        ttk.Label(header, image=self.logo).pack(side="left", padx=(0, 14))
        titles = ttk.Frame(header)
        titles.pack(side="left")
        ttk.Label(titles, text="SpaceMouse Link", style="Title.TLabel").pack(anchor="w")
        tagline = "SERVER  ·  Share a connected SpaceMouse" if self.role == "server" else "CLIENT  ·  Use your SpaceMouse on this computer"
        ttk.Label(titles, text=tagline, style="Muted.TLabel").pack(anchor="w")
        self.status = tk.StringVar(value="Pair your two computers to get started." if not config.get("peer_key") else "Ready to connect to your trusted peer.")
        ttk.Label(body, textvariable=self.status, wraplength=660).pack(anchor="w", pady=(20, 12))
        self.tabs = ttk.Notebook(body)
        self.tabs.pack(fill="both", expand=True)
        self.connection_tab = ttk.Frame(self.tabs, padding=18)
        self.pair_tab = ttk.Frame(self.tabs, padding=18)
        self.settings_tab = ttk.Frame(self.tabs, padding=18)
        for pane, text in ((self.connection_tab,"Connection"),(self.pair_tab,"Pairing"),(self.settings_tab,"Preferences")):
            self.tabs.add(pane, text=text)
        self.build_connection()
        self.build_pairing()
        self.build_settings()
        footer = ttk.Frame(body)
        footer.pack(fill="x", pady=(12, 0))
        ttk.Label(footer, text="Encrypted · Direct connection preferred · " + VERSION, style="Muted.TLabel").pack(side="left")
        ttk.Button(footer, text="Quit", command=self.quit).pack(side="right")
        root.protocol("WM_DELETE_WINDOW", self.close_window)
        if not preview:
            threading.Thread(target=reactor.run, kwargs={"installSignalHandlers": False}, daemon=True).start()
            self.create_tray()
            if self.role == "server":
                self.refresh()
            self.root.after(1000, self.maybe_auto_connect)
        root.after(100, self.drain)
        if start_hidden and self.tray:
            root.withdraw()
        if not config.get("peer_key"):
            self.tabs.select(self.pair_tab)

    def build_connection(self):
        pane = self.connection_tab
        self.peer_label = tk.StringVar()
        self.update_peer()
        ttk.Label(pane, textvariable=self.peer_label, style="Section.TLabel", wraplength=615).pack(anchor="w", pady=(0,12))
        if self.role == "server":
            self.selector = ttk.Combobox(pane, state="readonly")
            self.selector.pack(fill="x")
            row = ttk.Frame(pane)
            row.pack(fill="x", pady=(6,12))
            ttk.Button(row, text="Refresh", command=self.refresh).pack(side="left")
            ttk.Button(row, text="Prepare USB device…", command=self.prepare).pack(side="left", padx=8)
            ttk.Label(pane, text="USB preparation requests administrator permission once.\nSharing starts only after your trusted peer is authenticated.", style="Muted.TLabel").pack(anchor="w")
        else:
            ttk.Label(pane, text="Install 3DxWare on this computer, then use the SpaceMouse\nin your usual CAD applications.", style="Muted.TLabel").pack(anchor="w", pady=(0,14))
        row = ttk.Frame(pane)
        row.pack(fill="x", pady=14)
        self.connect_button = ttk.Button(row, text="Connect", style="Primary.TButton", command=self.connect)
        self.connect_button.pack(side="left")
        self.disconnect_button = ttk.Button(row, text="Disconnect", command=self.disconnect, state="disabled")
        self.disconnect_button.pack(side="left", padx=8)
        self.mode_text = tk.StringVar(value="Transport: disconnected")
        self.latency_text = tk.StringVar(value="Latency: —")
        ttk.Label(pane, textvariable=self.mode_text).pack(anchor="w")
        ttk.Label(pane, textvariable=self.latency_text, style="Muted.TLabel").pack(anchor="w", pady=(4,10))
        self.log = tk.Text(pane, height=5, bg="white", fg="#526780", relief="flat", font=("Segoe UI",9), wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True)

    def build_pairing(self):
        pane = self.pair_tab
        ttk.Label(pane, text="Trust one computer", style="Section.TLabel").pack(anchor="w")
        ttk.Label(pane, text="Copy an invitation once, then compare the verification code on both screens.\nFuture connections accept only the saved identity.", style="Muted.TLabel", wraplength=615).pack(anchor="w", pady=(6,14))
        ttk.Label(pane, text="This device ID (public)").pack(anchor="w")
        self.id_value = tk.StringVar(value=short_id(self.config["public_key"]))
        ttk.Entry(pane, textvariable=self.id_value, state="readonly").pack(fill="x", pady=(4,14))
        self.invitation_value = tk.StringVar()
        ttk.Label(pane, text="Invitation (private, expires after 5 minutes)").pack(anchor="w")
        ttk.Entry(pane, textvariable=self.invitation_value, show="•").pack(fill="x", pady=(4,10))
        row = ttk.Frame(pane)
        row.pack(fill="x")
        if self.role == "server":
            ttk.Button(row, text="Create invitation", style="Primary.TButton", command=self.create_invitation).pack(side="left")
            ttk.Button(row, text="Copy invitation", command=self.copy_invitation).pack(side="left", padx=8)
        else:
            ttk.Button(row, text="Paste invitation", command=self.paste_invitation).pack(side="left")
            ttk.Button(row, text="Pair with server", style="Primary.TButton", command=self.join_invitation).pack(side="left", padx=8)
        ttk.Button(pane, text="Cancel pairing", command=self.cancel_pairing).pack(anchor="w", pady=10)
        ttk.Label(pane, text="Never publish an invitation. An ID alone grants no access.\nIf the verification codes differ, reject pairing on both computers.", style="Muted.TLabel", wraplength=615).pack(anchor="w", pady=8)
        ttk.Button(pane, text="Forget trusted peer…", command=self.forget_peer).pack(anchor="w", pady=10)

    def build_settings(self):
        pane = self.settings_tab
        self.startup_var = tk.BooleanVar(value=self.autostart)
        self.auto_var = tk.BooleanVar(value=self.config.get("auto_connect", False))
        self.tray_var = tk.BooleanVar(value=self.config.get("close_to_tray", True))
        ttk.Checkbutton(pane, text="Launch at Windows sign-in", variable=self.startup_var, command=self.change_startup).pack(anchor="w", pady=10)
        ttk.Checkbutton(pane, text="Automatically connect to the last trusted peer", variable=self.auto_var, command=self.change_auto).pack(anchor="w", pady=10)
        ttk.Checkbutton(pane, text="Keep running in the notification area when I close the window", variable=self.tray_var, command=self.change_close).pack(anchor="w", pady=10)
        ttk.Label(pane, text="Startup is optional and applies only to this Windows user.\nQuit always disconnects and closes the application.\nDisconnect pauses automatic reconnection until you connect again.", style="Muted.TLabel", wraplength=615).pack(anchor="w", pady=18)

    def emit(self, kind, value):
        self.events.put((kind, value))

    def update_peer(self):
        key = self.config.get("peer_key")
        self.peer_label.set("Trusted peer · " + short_id(key) if key else "No trusted peer yet")

    def create_tray(self):
        try:
            import pystray
            item = pystray.MenuItem
            self.tray = pystray.Icon("SpaceMouseLink-" + self.role, icon(), "SpaceMouse Link · " + self.role,
                pystray.Menu(item("Open", lambda: self.emit("action", "show"), default=True),
                    item("Connect", lambda: self.emit("action", "connect")),
                    item("Disconnect", lambda: self.emit("action", "disconnect")),
                    pystray.Menu.SEPARATOR,
                    item("Launch at startup", lambda: self.emit("action", "toggle_startup"), checked=lambda _: self.autostart),
                    item("Auto-connect to trusted peer", lambda: self.emit("action", "toggle_auto"), checked=lambda _: bool(self.config.get("auto_connect"))),
                    pystray.Menu.SEPARATOR, item("Quit", lambda: self.emit("action", "quit"))))
            def run():
                try:
                    self.tray.run()
                except Exception:
                    self.emit("tray_failed", None)
            threading.Thread(target=run, daemon=True).start()
        except Exception:
            self.tray = None
            self.emit("error", "Notification icon unavailable; closing the window will quit.")

    def show(self):
        self.root.deiconify()
        self.root.lift()

    def save(self):
        if not self.preview:
            settings.save(self.config)

    def change_startup(self):
        try:
            if not self.preview:
                settings.set_startup(self.role, self.startup_var.get())
            self.autostart = self.startup_var.get()
            if self.tray:
                self.tray.update_menu()
        except Exception as exc:
            self.startup_var.set(self.autostart)
            messagebox.showerror("Startup", str(exc), parent=self.root)

    def toggle_startup(self):
        self.startup_var.set(not self.autostart)
        self.change_startup()

    def change_auto(self):
        self.config["auto_connect"] = self.auto_var.get()
        self.save()
        self.manual_pause = False
        if self.tray:
            self.tray.update_menu()
        self.maybe_auto_connect()

    def toggle_auto(self):
        self.auto_var.set(not self.config.get("auto_connect", False))
        self.change_auto()

    def change_close(self):
        self.config["close_to_tray"] = self.tray_var.get()
        self.save()

    def refresh(self):
        if self.busy or self.preview:
            return
        def work():
            try:
                self.emit("devices", windows_usb.devices())
            except Exception as exc:
                self.emit("error", str(exc))
        threading.Thread(target=work, daemon=True).start()

    def selected(self):
        index = self.selector.current()
        return self.devices[index] if 0 <= index < len(self.devices) else None

    def prepare(self):
        if self.busy:
            return
        device = self.selected()
        if not device:
            messagebox.showinfo("USB device", "Plug in a SpaceMouse Compact and click Refresh.", parent=self.root)
            return
        self.config["device_id"] = device["InstanceId"]
        self.save()
        self.status.set("Preparing the USB device. Check the Windows administrator prompt…")
        def work():
            try:
                windows_usb.prepare_device(device["BusId"], Path(sys.executable).parent)
                self.emit("status", "USB device prepared. Pair the two computers, then connect.")
                self.emit("action", "refresh")
            except Exception as exc:
                self.emit("error", str(exc))
        threading.Thread(target=work, daemon=True).start()

    def connect(self, automatic=False):
        if self.busy or self.pair_busy or self.preview:
            return
        if not self.config.get("peer_key"):
            self.tabs.select(self.pair_tab)
            return
        device = self.selected() if self.role == "server" else None
        if automatic and self.role == "server" and device and device["InstanceId"] != self.config.get("device_id"):
            self.status.set("Waiting for the saved USB device. Select Connect to use a different device.")
            self.schedule_retry()
            return
        if self.role == "server" and (not device or not device.get("PersistedGuid")):
            if not automatic:
                messagebox.showinfo("USB device", "Select a SpaceMouse and use Prepare USB device first.", parent=self.root)
            self.schedule_retry()
            return
        if device:
            self.config["device_id"] = device["InstanceId"]
            self.save()
        self.manual_pause = False
        self.busy = True
        self.connect_button.configure(state="disabled")
        self.disconnect_button.configure(state="normal")
        self.mode_text.set("Transport: negotiating")
        self.latency_text.set("Latency: measuring after connection…")
        if self.tray:
            self.tray.icon = icon("#fbbf24")
        def start():
            if self.quitting or self.manual_pause:
                self.emit("finished", None)
                return
            from link import Session
            self.session = Session(self.reactor, dict(self.config), self.emit, windows_usb, device)
            self.session.start()
        self.reactor.callFromThread(start)

    def maybe_auto_connect(self):
        self.retry_timer = None
        if not self.quitting and not self.manual_pause and self.config.get("auto_connect") and self.config.get("peer_key"):
            self.connect(automatic=True)

    def schedule_retry(self):
        if self.retry_timer is None and not self.quitting and not self.manual_pause and self.config.get("auto_connect"):
            self.retry_timer = self.root.after(self.retry_delay * 1000, self.maybe_auto_connect)
            self.retry_delay = min(60, self.retry_delay * 2)
            if self.role == "server":
                self.refresh()

    def disconnect(self):
        self.manual_pause = True
        if self.retry_timer is not None:
            self.root.after_cancel(self.retry_timer)
            self.retry_timer = None
        if self.session:
            self.reactor.callFromThread(self.session.stop)

    def can_pair(self):
        if self.busy or self.pair_busy:
            return False
        if self.config.get("peer_key"):
            messagebox.showinfo("Already paired", "Forget the current trusted peer before pairing a different computer.", parent=self.root)
            return False
        return True

    def create_invitation(self):
        if not self.can_pair():
            return
        invitation, text = make_invitation(self.config["public_key"])
        self.invitation_text = text
        self.invitation_value.set(text)
        self.begin_pairing(invitation)

    def copy_invitation(self):
        if self.invitation_text:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.invitation_text)
            self.status.set("Invitation copied. Paste it in the client app within 5 minutes.")

    def paste_invitation(self):
        try:
            self.invitation_value.set(self.root.clipboard_get().strip())
        except tk.TclError:
            messagebox.showinfo("Pairing", "Copy the server invitation first.", parent=self.root)

    def join_invitation(self):
        if not self.can_pair():
            return
        try:
            invitation = parse_invitation(self.invitation_value.get().strip())
            self.begin_pairing(invitation)
        except Exception as exc:
            messagebox.showerror("Invitation", str(exc), parent=self.root)

    def begin_pairing(self, invitation):
        self.pair_busy = True
        self.status.set("Pairing: waiting for the other computer…")
        def start():
            if self.quitting:
                self.emit("pair_finished", None)
                return
            from pairing import Pairing
            self.pairing = Pairing(self.reactor, dict(self.config), invitation, self.emit)
            from twisted.internet import defer
            defer.ensureDeferred(self.pairing.run()).addErrback(lambda f: self.emit("error", "Pairing failed."))
        self.reactor.callFromThread(start)

    def cancel_pairing(self):
        if self.pairing:
            self.reactor.callFromThread(self.pairing.stop)

    def forget_peer(self):
        if self.busy or self.pair_busy:
            messagebox.showinfo("Pairing", "Disconnect and cancel any pairing attempt first.", parent=self.root)
            return
        if messagebox.askyesno("Forget trusted peer", "Revoke this pairing? A new invitation and confirmation will be required.", parent=self.root):
            self.config.pop("peer_key", None)
            self.config.pop("connection_secret", None)
            self.config["auto_connect"] = False
            self.auto_var.set(False)
            self.manual_pause = True
            self.save()
            self.update_peer()
            self.status.set("Peer forgotten. Previous pairing credentials are no longer accepted.")

    def drain(self):
        while not self.events.empty():
            kind, value = self.events.get()
            if kind == "action":
                getattr(self, value)()
            elif kind == "devices":
                self.devices = value
                self.selector.configure(values=["SpaceMouse Compact · USB " + d["BusId"] + (" · ready" if d.get("PersistedGuid") else " · needs preparation") for d in value])
                if value:
                    index = next((i for i,d in enumerate(value) if d["InstanceId"] == self.config.get("device_id")), 0)
                    self.selector.current(index)
                else:
                    self.selector.set("No SpaceMouse Compact detected")
            elif kind == "pair_confirm":
                self.show()
                allowed = messagebox.askyesno("Verify both computers", "Compare this code on BOTH screens:\n\n" + value["code"] + "\n\nPeer ID: " + value["peer"] + "\n\nApprove only if both codes match and you initiated this pairing.", parent=self.root)
                self.reactor.callFromThread(self.pairing.approve, allowed)
            elif kind == "paired":
                self.config.update(value)
                self.save()
                self.update_peer()
                self.status.set("Pairing saved. Only this peer's identity will be accepted.")
                self.tabs.select(self.connection_tab)
            elif kind == "pair_finished":
                self.pair_busy = False
                try:
                    if self.invitation_text and self.root.clipboard_get() == self.invitation_text:
                        self.root.clipboard_clear()
                except tk.TclError:
                    pass
                self.invitation_text = ""
                self.invitation_value.set("")
                if self.quitting:
                    self.finish_quit()
                    return
            elif kind == "mode":
                self.mode_text.set("Transport: " + value)
                self.retry_delay = 3
                if self.tray:
                    self.tray.icon = icon("#34d399")
                self.emit("status", "Connected: " + value)
            elif kind == "latency":
                self.latency_text.set("RTT {latest_ms:.1f} ms  ·  median {median_ms:.1f} ms  ·  p95 {p95_ms:.1f} ms".format(**value))
                self.last_report = {**value, "updated_utc": datetime.now(timezone.utc).isoformat(), "connected": True}
                if not self.preview:
                    (settings.directory(self.role) / "latency.json").write_text(json.dumps(self.last_report, indent=2))
            elif kind == "finished":
                self.busy = False
                self.mode_text.set("Transport: disconnected")
                self.connect_button.configure(state="normal")
                self.disconnect_button.configure(state="disabled")
                if self.tray:
                    self.tray.icon = icon()
                if self.last_report and not self.preview:
                    self.last_report["connected"] = False
                    (settings.directory(self.role) / "latency.json").write_text(json.dumps(self.last_report, indent=2))
                if self.quitting:
                    self.finish_quit()
                    return
                self.schedule_retry()
            elif kind == "tray_failed":
                self.tray = None
                self.show()
                self.emit("error", "Notification icon unavailable; window kept open.")
            elif kind in ("status", "error", "security_error"):
                if kind == "security_error":
                    self.manual_pause = True
                text = ("Error: " if kind != "status" else "") + str(value)
                self.status.set(text)
                self.log.configure(state="normal")
                self.log.insert("end", text + "\n")
                if int(self.log.index("end-1c").split('.')[0]) > 120:
                    self.log.delete("1.0", "20.0")
                self.log.see("end")
                self.log.configure(state="disabled")
        if not self.quitting or self.busy or self.pair_busy:
            self.root.after(100, self.drain)

    def close_window(self):
        if self.tray and self.config.get("close_to_tray", True):
            self.root.withdraw()
        else:
            self.quit()

    def quit(self):
        self.quitting = True
        self.disconnect()
        self.cancel_pairing()
        if not self.busy and not self.pair_busy:
            self.finish_quit()
        else:
            self.status.set("Disconnecting and releasing the device…")

    def finish_quit(self):
        if self.tray:
            self.tray.stop()
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=["server", "client"], default="client")
    parser.add_argument("--tray", action="store_true")
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--transport-check", action="store_true")
    parser.add_argument("--report")
    args = parser.parse_args()
    if args.transport_check:
        from twisted.internet import task, defer
        from tests.relay_smoke import main as test
        task.react(lambda reactor: defer.ensureDeferred(test(reactor, args.report)))
        return
    if args.self_check:
        import pystray
        from aiortc import RTCPeerConnection
        from link import Session
        if args.report:
            Path(args.report).write_text(json.dumps({"ok": True, "version": VERSION}))
        return
    root = tk.Tk()
    root.withdraw()
    try:
        kernel = ctypes.windll.kernel32
        kernel.CreateMutexW.restype = ctypes.c_void_p
        mutex = kernel.CreateMutexW(None, False, "Local\\SpaceMouseLink-v2-" + args.role)
        if kernel.GetLastError() == 183:
            raise RuntimeError("SpaceMouse Link is already running. Open it from the notification area.")
        config = settings.load(args.role)
        window = Window(root, config, args.tray)
        if not args.tray or window.tray is None:
            root.deiconify()
        root.mainloop()
        kernel.CloseHandle(ctypes.c_void_p(mutex))
    except Exception as exc:
        messagebox.showerror("SpaceMouse Link", str(exc), parent=root)
        root.destroy()


if __name__ == "__main__":
    main()
