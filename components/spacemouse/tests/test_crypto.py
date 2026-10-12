import os
import struct
import unittest

from nacl.exceptions import CryptoError
from nacl.secret import SecretBox
from wormhole.transit import BadHandshake, BadNonce
from link import BoundedConnection


class CryptoTests(unittest.TestCase):
    def connection(self):
        conn = BoundedConnection(None, None, None, "test")
        conn.receive_box = SecretBox(os.urandom(32))
        conn.next_receive_nonce = 0
        conn.received = []
        conn.recordReceived = conn.received.append
        return conn

    def test_oversize_rejected_before_buffering(self):
        conn = self.connection()
        conn.buf = struct.pack("!I", 2**32 - 1)
        with self.assertRaises(BadHandshake):
            conn.dataReceivedRECORDS()

    def test_truncated_header_waits(self):
        conn = self.connection()
        conn.buf = b"\0\0"
        conn.dataReceivedRECORDS()
        self.assertEqual(conn.received, [])

    def test_encrypted_record_and_replay(self):
        conn = self.connection()
        encrypted = conn.receive_box.encrypt(b"Dtest", bytes(24))
        wire = struct.pack("!I", len(encrypted)) + encrypted
        conn.buf = wire
        conn.dataReceivedRECORDS()
        self.assertEqual(conn.received, [b"Dtest"])
        conn.buf = wire
        with self.assertRaises(BadNonce):
            conn.dataReceivedRECORDS()

    def test_tampered_ciphertext_rejected(self):
        conn = self.connection()
        encrypted = bytearray(conn.receive_box.encrypt(b"Dtest", bytes(24)))
        encrypted[-1] ^= 1
        conn.buf = struct.pack("!I", len(encrypted)) + encrypted
        with self.assertRaises(CryptoError):
            conn.dataReceivedRECORDS()

    def test_wrong_key_rejected(self):
        conn = self.connection()
        encrypted = SecretBox(os.urandom(32)).encrypt(b"Dtest", bytes(24))
        conn.buf = struct.pack("!I", len(encrypted)) + encrypted
        with self.assertRaises(CryptoError):
            conn.dataReceivedRECORDS()
