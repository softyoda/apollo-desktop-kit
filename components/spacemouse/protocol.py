"""SpaceMouse-only USB/IP request validation. No network or Windows dependencies."""
import re
import struct

VID = 0x256F
PID = 0xC635
IMPORT = 0x8003
VERSION = 0x0111
MAX_RECORD = 32769


def valid_busid(value):
    return isinstance(value, str) and re.fullmatch(r"[1-9][0-9]{0,3}-[1-9][0-9]{0,3}", value) is not None


class ImportGate:
    """Release bytes only after the exact selected USB/IP import was validated."""
    def __init__(self, busid):
        if not valid_busid(busid):
            raise ValueError("Invalid USB bus ID")
        self.busid = busid
        self.buffer = bytearray()
        self.open = False

    def feed(self, data):
        if self.open:
            return data
        self.buffer.extend(data)
        if len(self.buffer) < 40:
            return b""
        version, command, status = struct.unpack("!HHI", self.buffer[:8])
        expected = self.busid.encode("ascii").ljust(32, b"\0")
        if (version, command, status) != (VERSION, IMPORT, 0) or self.buffer[8:40] != expected:
            self.buffer.clear()
            raise ValueError("Only an import of the selected SpaceMouse is permitted")
        self.open = True
        result = bytes(self.buffer)
        self.buffer.clear()
        return result


class ReplyGate:
    """Do not expose a device to the receiving driver unless its VID/PID match."""
    def __init__(self):
        self.buffer = bytearray()
        self.open = False

    def feed(self, data):
        if self.open:
            return data
        self.buffer.extend(data)
        if len(self.buffer) < 8:
            return b""
        version, command, status = struct.unpack("!HHI", self.buffer[:8])
        if (version, command, status) != (VERSION, 3, 0):
            raise ValueError("USB exporter rejected the SpaceMouse import")
        # usbip_usb_device: path[256], busid[32], busnum/devnum/speed (12), VID/PID.
        if len(self.buffer) < 320:
            return b""
        if struct.unpack("!HH", self.buffer[308:312]) != (VID, PID):
            raise ValueError("Remote USB device is not a SpaceMouse Compact")
        self.open = True
        result = bytes(self.buffer)
        self.buffer.clear()
        return result


def validate_offer(value, expected_role):
    if not isinstance(value, dict) or value.get("version") != 1 or value.get("role") != expected_role:
        raise ValueError("The peer is not the opposite SpaceMouse Link role")
    if expected_role == "server":
        if value.get("vid") != VID or value.get("pid") != PID or not valid_busid(value.get("busid")):
            raise ValueError("The peer is not offering a SpaceMouse Compact")
    return value
