import struct
import unittest

from protocol import ImportGate, ReplyGate, validate_offer, valid_busid


def request(busid="1-4", command=0x8003):
    return struct.pack("!HHI", 0x111, command, 0) + busid.encode().ljust(32, b"\0")


def reply(vid=0x256f, pid=0xc635):
    data = bytearray(320)
    struct.pack_into("!HHI", data, 0, 0x111, 3, 0)
    struct.pack_into("!HH", data, 308, vid, pid)
    return bytes(data)


class GateTests(unittest.TestCase):
    def test_fragmentation_and_stream_preservation(self):
        gate = ImportGate("1-4")
        wire = request() + b"USB transfer data"
        result = b"".join(gate.feed(bytes([b])) for b in wire)
        self.assertEqual(result, wire)
        self.assertEqual(gate.feed(b"later"), b"later")

    def test_wrong_device_rejected(self):
        with self.assertRaises(ValueError):
            ImportGate("1-4").feed(request("1-5"))

    def test_device_list_and_other_operations_rejected(self):
        for cmd in (0x8005, 0x8001, 3, 0):
            with self.assertRaises(ValueError):
                ImportGate("1-4").feed(request(command=cmd))

    def test_nonzero_padding_rejected(self):
        data = bytearray(request())
        data[-1] = 1
        with self.assertRaises(ValueError):
            ImportGate("1-4").feed(data)

    def test_noncompact_reply_rejected(self):
        for vid, pid in ((0x046d, 0xc635), (0x256f, 0xc652)):
            with self.assertRaises(ValueError):
                ReplyGate().feed(reply(vid, pid))

    def test_reply_fragmentation(self):
        gate = ReplyGate()
        data = reply() + b"HID data"
        self.assertEqual(b"".join(gate.feed(data[i:i+3]) for i in range(0, len(data), 3)), data)

    def test_offer_role_and_hardware(self):
        offer = {"version": 1, "role": "server", "vid": 0x256f, "pid": 0xc635, "busid": "1-4"}
        self.assertEqual(validate_offer(offer, "server"), offer)
        with self.assertRaises(ValueError):
            validate_offer(offer, "client")
        with self.assertRaises(ValueError):
            validate_offer({**offer, "busid": "1-4; powershell"}, "server")
        self.assertFalse(valid_busid("1-4\n"))

    def test_failed_import_not_forwarded(self):
        with self.assertRaises(ValueError):
            ReplyGate().feed(struct.pack("!HHI", 0x111, 3, 1))


if __name__ == "__main__":
    unittest.main()
