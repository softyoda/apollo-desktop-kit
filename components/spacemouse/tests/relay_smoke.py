"""Public-relay integration test. Transfers generated test bytes only, no files/USB."""
import json
import os
from pathlib import Path
import secrets
import struct
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from twisted.internet import defer, endpoints, protocol, task
from link import Session, DEFAULT_TRANSIT
from protocol import ImportGate
from identity import test_pair_configs


PAYLOAD = bytes(range(256)) * 512


class FakeUSB(protocol.Protocol):
    def __init__(self):
        self.gate = ImportGate("1-4")
        self.buffer = b""
        self.imported = False

    def connectionMade(self):
        self.transport.setTcpNoDelay(True)

    def dataReceived(self, data):
        if not self.imported:
            self.buffer += data
            if len(self.buffer) < 40:
                return
            data = self.gate.feed(self.buffer)
            self.imported = True
            response = bytearray(320)
            struct.pack_into("!HHI", response, 0, 0x111, 3, 0)
            struct.pack_into("!HH", response, 308, 0x256f, 0xc635)
            self.transport.write(bytes(response))
            data = data[40:]
        if data:
            self.transport.write(data)


class Importer(protocol.Protocol):
    def __init__(self, done):
        self.done = done
        self.buffer = bytearray()
        self.sent_payload = False
        self.started = 0
        self.bulk_ms = None
        self.pings = []

    def connectionMade(self):
        self.transport.setTcpNoDelay(True)
        self.transport.write(struct.pack("!HHI", 0x111, 0x8003, 0) + b"1-4".ljust(32, b"\0"))

    def dataReceived(self, data):
        self.buffer.extend(data)
        if not self.sent_payload and len(self.buffer) >= 320:
            del self.buffer[:320]
            self.sent_payload = True
            self.started = time.perf_counter()
            self.transport.write(PAYLOAD)
        if self.sent_payload and self.bulk_ms is None and len(self.buffer) >= len(PAYLOAD) and not self.done.called:
            if bytes(self.buffer) != PAYLOAD:
                self.done.errback(ValueError("Tunnel changed stream bytes"))
            else:
                self.bulk_ms = round((time.perf_counter() - self.started)*1000, 1)
                self.buffer.clear()
                self.started = time.perf_counter()
                self.transport.write(b"p")
        elif self.bulk_ms is not None and self.buffer and not self.done.called:
            assert self.buffer == b"p"
            self.buffer.clear()
            self.pings.append(round((time.perf_counter() - self.started)*1000, 1))
            if len(self.pings) == 5:
                self.done.callback((self.bulk_ms, self.pings))
            else:
                self.started = time.perf_counter()
                self.transport.write(b"p")


async def main(reactor, report_path=None):
    if os.environ.get("SPACEMOUSE_TEST_FAIL_DIRECT") == "1":
        from direct import DirectPipe
        async def unavailable(self):
            raise TimeoutError("Synthetic direct failure for fallback regression")
        DirectPipe.ready = unavailable
    usb_factory = protocol.Factory()
    usb_factory.protocol = FakeUSB
    fake = reactor.listenTCP(0, usb_factory, interface="127.0.0.1")
    code = str(secrets.randbelow(900000000) + 100000000) + "-" + secrets.token_hex(32)
    events = []
    modes = {}
    done = defer.Deferred()
    ports = []
    importer_d = []
    def emit(role):
        def handler(kind, value):
            if kind == "mode":
                modes[role] = value
            if kind == "listen":
                ports.append(value)
                factory = protocol.Factory()
                factory.buildProtocol = lambda addr: Importer(done)
                d = endpoints.TCP4ClientEndpoint(reactor, "127.0.0.1", value).connect(factory)
                importer_d.append(d)
                d.addErrback(lambda f: done.errback(f) if not done.called else None)
            elif kind in ("status", "error", "security_error"):
                events.append((role, kind, value))
                print(role, kind, value, flush=True)
                if kind in ("error", "security_error") and not done.called:
                    done.errback(RuntimeError(value))
        return handler
    server_config, client_config = test_pair_configs()
    base = {
            "direct": os.environ.get("SPACEMOUSE_FORCE_RELAY") != "1",
            "stun": os.environ.get("SPACEMOUSE_TEST_NO_STUN") != "1",
            "transit": os.environ.get("SPACEMOUSE_TEST_TRANSIT", DEFAULT_TRANSIT)}
    b_config = {**base, **server_config, "test_usb_port": fake.getHost().port}
    if os.environ.get("SPACEMOUSE_TEST_LEGACY") == "1":
        b_config["direct"] = False
    b = Session(reactor, b_config,
                emit("server"), None, {"BusId": "1-4"}, simulate=True)
    p = Session(reactor, {**base, **client_config}, emit("client"), None, simulate=True)
    start = time.monotonic()
    b.start()
    p.start()
    try:
        elapsed, pings = await done.addTimeout(110, reactor)
        expected = os.environ.get("SPACEMOUSE_EXPECT_MODE")
        if expected:
            assert len(modes) == 2 and all(v.startswith(expected) for v in modes.values()), modes
        report = {"ok": True, "bytes_each_direction": len(PAYLOAD), "payload_roundtrip_ms": elapsed,
                  "transports": modes,
                  "small_message_roundtrip_ms": pings,
                  "total_seconds": round(time.monotonic() - start, 2), "synthetic_only": True,
                  "loopback_listener": True, "endpoints_same_machine": True}
        Path(report_path or "relay-test-result.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(report), flush=True)
    finally:
        b.stop()
        p.stop()
        await defer.DeferredList([b.running, p.running], consumeErrors=True)
        await fake.stopListening()


if __name__ == "__main__":
    task.react(lambda reactor: defer.ensureDeferred(main(reactor)))
