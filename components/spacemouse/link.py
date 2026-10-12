"""SpaceMouse USB over direct authenticated WebRTC, with encrypted relay fallback."""
import json
import os
import struct
import time

# Use Autobahn's bundled pure-Python WebSocket validator; no runtime C build.
# Transit encryption still uses libsodium/PyNaCl.
os.environ["AUTOBAHN_USE_NVX"] = "0"

from twisted.internet import defer, endpoints, protocol, task, threads
from wormhole import create, transit
from wormhole.cli import public_relay
from wormhole.errors import WrongPasswordError, ReflectionAttack

from protocol import ImportGate, ReplyGate, MAX_RECORD, VID, PID, validate_offer
from latency import LatencySamples
from identity import SESSION_APPID, AuthenticationError, connection_code, signed_identity, verify_identity

APPID = SESSION_APPID
DEFAULT_TRANSIT = "tcp:relay.mw.leastauthority.com:4001"


class BoundedConnection(transit.Connection):
    """Bound untrusted ciphertext framing before the library buffers a record."""
    def dataReceivedRECORDS(self):
        while len(self.buf) >= 4:
            length = struct.unpack("!I", self.buf[:4])[0]
            if length < 40 or length > MAX_RECORD + 40:
                raise transit.BadHandshake("Invalid SpaceMouse record length")
            if len(self.buf) < 4 + length:
                return
            encrypted, self.buf = self.buf[4:4 + length], self.buf[4 + length:]
            self.recordReceived(self._decrypt_record(encrypted))


# Pinned magic-wormhole 0.24.0: outbound factories provide the encrypted pipe.
transit.OutboundConnectionFactory.protocol = BoundedConnection


class LocalUSB(protocol.Protocol):
    def __init__(self, session):
        self.session = session

    def connectionMade(self):
        self.transport.setTcpNoDelay(True)
        self.session.local_ready(self)

    def dataReceived(self, data):
        try:
            self.session.from_local(data)
        except Exception as exc:
            self.session.fail(exc)

    def connectionLost(self, reason):
        self.session.finish("USB connection closed")


class OneUSBFactory(protocol.Factory):
    def __init__(self, session):
        self.session = session
        self.used = False

    def buildProtocol(self, addr):
        if self.used or self.session.stopping:
            return None
        self.used = True
        return LocalUSB(self.session)


class Session:
    def __init__(self, reactor, config, emit, usb, device=None, simulate=False):
        self.reactor, self.config, self.emit, self.usb = reactor, config, emit, usb
        self.role = config["role"]
        self.device = device
        self.simulate = simulate
        self.wormhole = self.pipe = self.local = self.listener = self.heartbeat = None
        self.bound = False
        self.attached = None
        self.attach_task = None
        self.stopping = False
        self.completed = defer.Deferred()
        self.local_connected = defer.Deferred()
        self.running = None
        self.waiting = None
        self.last_rx = time.monotonic()
        self.tx = self.rx = 0
        self.gate = None
        self.latency = LatencySamples()
        self.mode = "connecting"
        self.direct_attempt = None

    def start(self):
        self.running = defer.ensureDeferred(self.run())
        self.running.addErrback(lambda f: self.emit("error", str(f.value)))
        return self.running

    def stop(self):
        self.stopping = True
        self.finish("Disconnected")
        if self.waiting and not self.waiting.called:
            self.waiting.cancel()

    async def wait(self, pending, timeout):
        if self.stopping:
            pending.cancel()
            raise defer.CancelledError()
        self.waiting = pending
        try:
            return await pending.addTimeout(timeout, self.reactor)
        finally:
            self.waiting = None

    def finish(self, message):
        if not self.completed.called:
            self.completed.callback(message)

    def fail(self, exc):
        self.emit("error", str(exc))
        self.finish("Connection stopped")
        if self.waiting is not None and not self.waiting.called:
            self.waiting.cancel()

    async def run(self):
        try:
            if self.role == "server":
                if not self.device:
                    raise ValueError("Select your SpaceMouse Compact first")
                self.busid = self.device["BusId"]
                self.gate = ImportGate(self.busid)
            if self.stopping:
                return
            self.emit("status", "Waiting for the paired computer...")
            self.wormhole = create(APPID, self.config.get("mailbox", public_relay.MAILBOX_RELAY), self.reactor)
            self.wormhole.set_code(connection_code(self.config["connection_secret"]))
            # PAKE authenticates the secret before any USB data or device metadata.
            verifier = await self.wait(self.wormhole.get_verifier(), 180)
            self.wormhole.send_message(json.dumps(signed_identity(self.config, verifier, "session")).encode())
            proof = await self.wait(self.wormhole.get_message(), 30)
            if len(proof) > 1024:
                raise AuthenticationError("Invalid peer identity")
            verify_identity(json.loads(proof), verifier, "session",
                            "client" if self.role == "server" else "server", self.config["peer_key"])
            if self.role == "server" and not self.simulate:
                await threads.deferToThread(self.usb.validate_shared_device, self.busid)
            offer = {"version": 1, "role": self.role}
            if self.config.get("direct", True):
                offer["transports"] = ["webrtc-v1", "relay-v1"]
            if self.role == "server":
                offer.update(busid=self.busid, vid=VID, pid=PID)
            self.wormhole.send_message(json.dumps(offer).encode("ascii"))
            raw = await self.wait(self.wormhole.get_message(), 30)
            if len(raw) > 1024:
                raise ValueError("Invalid peer offer")
            peer = validate_offer(json.loads(raw), "client" if self.role == "server" else "server")
            if self.role == "client":
                self.busid = peer["busid"]
                self.gate = ReplyGate()
            if self.config.get("direct", True) and "webrtc-v1" in peer.get("transports", []):
                from direct import negotiate
                self.emit("status", "Peer authenticated. Trying direct UDP connection (ICE/STUN)...")
                self.pipe = await negotiate(self)
            if self.pipe:
                self.mode = "DIRECT - WebRTC UDP"
            else:
                self.emit("status", "Direct unavailable or older peer. Using encrypted relay fallback.")
                cls = transit.TransitSender if self.role == "server" else transit.TransitReceiver
                connector = cls(self.config.get("transit", DEFAULT_TRANSIT),
                                no_listen=True, reactor=self.reactor)
                await connector.get_connection_hints()
                connector.set_transit_key(self.wormhole.derive_key(APPID + "/usb-transit", 32))
                self.pipe = await self.wait(connector.connect(), 75)
                self.mode = "RELAY - Least Authority"
            self.emit("mode", self.mode)
            self.pipe.transport.setTcpNoDelay(True)
            await self.wait(self.wormhole.close(), 8)
            self.wormhole = None
            if self.role == "server":
                if not self.simulate:
                    connected = await threads.deferToThread(self.usb.devices)
                    if not any(d["BusId"] == self.busid for d in connected):
                        raise RuntimeError("SpaceMouse was unplugged before attachment")
                await self.wait(endpoints.TCP4ClientEndpoint(self.reactor, "127.0.0.1",
                        self.config.get("test_usb_port", 3240), timeout=10).connect(OneUSBFactory(self)), 12)
            else:
                self.listener = self.reactor.listenTCP(0, OneUSBFactory(self), interface="127.0.0.1")
                port = self.listener.getHost().port
                if self.simulate:
                    self.emit("listen", port)
                else:
                    self.attach_task = defer.ensureDeferred(self.attach(port))
                    self.attach_task.addErrback(lambda f: self.fail(f.value))
            await self.wait(self.local_connected, 60)
            self.pipe.connectConsumer(self)
            self.heartbeat = task.LoopingCall(self.ping)
            self.heartbeat.start(1 if self.role == "client" else 10, now=False)
            self.emit("status", "USB tunnel connected; waiting for device recognition...")
            result = await self.completed
            self.emit("status", result)
        except defer.CancelledError:
            self.emit("status", "Disconnected")
        except (AuthenticationError, WrongPasswordError, ReflectionAttack) as exc:
            self.emit("security_error", str(exc))
        except Exception as exc:
            self.emit("error", str(exc))
        finally:
            try:
                await self.cleanup()
            finally:
                self.emit("finished", None)

    async def attach(self, port):
        attached = await threads.deferToThread(self.usb.attach_device, self.busid, port)
        if self.stopping:
            await threads.deferToThread(self.usb.detach_device, attached)
        else:
            self.attached = attached
            self.emit("status", "SpaceMouse attached in client. Test it in 3Dconnexion Trainer.")

    def local_ready(self, local):
        self.local = local
        # Twisted transports propagate backpressure in both directions.
        self.pipe.registerProducer(local.transport, True)
        local.transport.registerProducer(self.pipe, True)
        if not self.local_connected.called:
            self.local_connected.callback(None)
        if self.listener:
            self.listener.stopListening()
            self.listener = None

    def from_local(self, data):
        if self.stopping:
            return
        # On server, local bytes are replies from usbipd. On client, requests
        # are sent to server, where the import gate enforces the selected bus.
        for offset in range(0, len(data), MAX_RECORD - 1):
            block = data[offset:offset + MAX_RECORD - 1]
            self.pipe.send_record(b"D" + block)
            self.tx += len(block)

    def registerProducer(self, producer, streaming):
        pass  # Explicit transport registrations in local_ready handle flow control.

    def unregisterProducer(self):
        pass

    def write(self, record):
        try:
            if not record or len(record) > MAX_RECORD:
                raise ValueError("Invalid record")
            self.last_rx = time.monotonic()
            if record == b"P":
                self.pipe.send_record(b"Q")
            elif record == b"Q":
                result = self.latency.received(time.perf_counter())
                if result is not None:
                    result["mode"] = self.mode
                    self.emit("latency", result)
            elif record[:1] == b"D":
                data = self.gate.feed(record[1:])
                if data:
                    self.local.transport.write(data)
                    self.rx += len(data)
            else:
                raise ValueError("Unknown record type")
        except Exception as exc:
            self.fail(exc)

    def ping(self):
        if time.monotonic() - self.last_rx > 45:
            self.fail(RuntimeError("Peer stopped responding. Reconnect both apps."))
            return
        if self.latency.sent(time.perf_counter()):
            self.pipe.send_record(b"P")
        self.emit("traffic", (self.tx, self.rx))

    async def cleanup(self):
        self.stopping = True
        if self.heartbeat and self.heartbeat.running:
            self.heartbeat.stop()
        if self.listener:
            await defer.maybeDeferred(self.listener.stopListening)
            self.listener = None
        if self.local:
            self.local.transport.unregisterProducer()
            self.local.transport.abortConnection()
        if self.pipe:
            self.pipe.unregisterProducer()
            self.pipe.close()
        if self.direct_attempt:
            self.direct_attempt.close()
        if self.wormhole:
            try:
                await self.wormhole.close().addTimeout(5, self.reactor)
            except Exception:
                pass
        if self.attach_task and not self.attach_task.called:
            # Let a native attach already in progress finish and release its own
            # port before permitting another session. Never detach someone else's port.
            try:
                await self.attach_task
            except Exception:
                pass
        if self.attached:
            try:
                await threads.deferToThread(self.usb.detach_device, self.attached)
            except Exception as exc:
                self.emit("error", "USB detach: " + str(exc))
            self.attached = None
        if self.bound:
            try:
                await threads.deferToThread(self.usb.unbind_device, self.busid)
            except Exception as exc:
                self.emit("error", "USB release: " + str(exc))
            self.bound = False
