"""Authenticated WebRTC data channel adapted to the existing Twisted USB bridge.

Only SDP exchanged inside the PAKE-authenticated wormhole is accepted. DTLS
checks the fingerprint from that authenticated SDP. No TURN, UPnP or NAT-PMP
is configured here: successful ICE means a direct host/srflx/peer-reflexive path.
"""
import asyncio
from collections import deque
import concurrent.futures
import threading
import re

from twisted.internet import defer
from twisted.python.failure import Failure

from protocol import MAX_RECORD

_loop = None
_loop_lock = threading.Lock()
LIMIT = 4 * 1024 * 1024
HIGH = 256 * 1024
LOW = 64 * 1024
LABEL = "spacemouse-usb-v1"


def validate_sdp(sdp):
    if not isinstance(sdp, str) or len(sdp.encode("utf-8")) > 60000:
        raise ValueError("Invalid direct description")
    lines = sdp.splitlines()
    media = [line for line in lines if line.startswith("m=")]
    if len(media) != 1 or not media[0].startswith("m=application "):
        raise ValueError("Only a data channel is permitted")
    if not any(re.fullmatch(r"a=fingerprint:sha-256 (?:[0-9A-Fa-f]{2}:){31}[0-9A-Fa-f]{2}", line) for line in lines):
        raise ValueError("DTLS SHA-256 fingerprint is required")
    candidates = [line for line in lines if line.startswith("a=candidate:")]
    if len(candidates) > 64 or any(" typ relay" in line for line in candidates):
        raise ValueError("Unexpected ICE candidates")
    return sdp


def event_loop():
    global _loop
    with _loop_lock:
        if _loop is None:
            _loop = asyncio.new_event_loop()
            def run():
                asyncio.set_event_loop(_loop)
                _loop.run_forever()
            threading.Thread(target=run, name="SpaceMouse-ICE", daemon=True).start()
    return _loop


class DirectPipe:
    def __init__(self, reactor, on_failure, stun=True):
        self.reactor = reactor
        self.on_failure = on_failure
        self.loop = event_loop()
        self.stun = stun
        self.pc = self.channel = None
        self.opened = None
        self.closed = False
        self.active = False
        self.consumer = self.producer = None
        self.pending = deque()
        self.pending_bytes = 0
        self.inbound_paused = False
        self.producer_paused = False
        self.outbound_bytes = 0
        self.lock = threading.Lock()
        self.transport = self

    def dispatch(self, coroutine):
        future = asyncio.run_coroutine_threadsafe(coroutine, self.loop)
        result = defer.Deferred(lambda _: future.cancel())
        def deliver():
            if result.called:
                return
            try:
                value = future.result()
            except concurrent.futures.CancelledError:
                result.errback(Failure(defer.CancelledError()))
            except Exception as exc:
                result.errback(Failure(exc))
            else:
                result.callback(value)
        future.add_done_callback(lambda _: self.reactor.callFromThread(deliver))
        return result

    async def setup(self):
        from aiortc import RTCPeerConnection, RTCConfiguration, RTCIceServer
        self.pc = RTCPeerConnection(RTCConfiguration(iceServers=[
            RTCIceServer(urls="stun:stun.l.google.com:19302")
        ] if self.stun else []))
        self.opened = asyncio.Event()

        @self.pc.on("datachannel")
        def incoming(channel):
            if self.channel is not None or channel.label != LABEL or not channel.ordered or channel.maxRetransmits is not None or channel.maxPacketLifeTime is not None:
                self.fail("Unexpected WebRTC channel")
                channel.close()
                return
            self.bind_channel(channel)

        @self.pc.on("connectionstatechange")
        def state_changed():
            if self.active and not self.closed and self.pc.connectionState in ("failed", "closed"):
                self.fail("Direct connection lost; reconnect both apps")

    def bind_channel(self, channel):
        self.channel = channel
        channel.bufferedAmountLowThreshold = LOW
        @channel.on("open")
        def opened():
            self.opened.set()
        @channel.on("message")
        def message(data):
            if not isinstance(data, bytes) or not 1 <= len(data) <= MAX_RECORD:
                self.fail("Invalid direct USB record")
                return
            with self.lock:
                self.pending_bytes += len(data)
                excessive = self.pending_bytes > LIMIT
            if excessive:
                self.fail("Direct receive buffer limit exceeded")
                return
            self.reactor.callFromThread(self.receive, data)
        @channel.on("bufferedamountlow")
        def drained():
            self.reactor.callFromThread(self.pressure, channel.bufferedAmount)
        @channel.on("close")
        def closed():
            if self.active and not self.closed:
                self.fail("Direct channel closed; reconnect both apps")
        if channel.readyState == "open":
            self.opened.set()

    async def make_offer(self):
        await self.setup()
        self.bind_channel(self.pc.createDataChannel(LABEL, ordered=True))
        await asyncio.wait_for(self.pc.setLocalDescription(await self.pc.createOffer()), 12)
        return self.pc.localDescription.sdp

    async def make_answer(self, sdp):
        from aiortc import RTCSessionDescription
        await self.setup()
        await self.pc.setRemoteDescription(RTCSessionDescription(sdp=validate_sdp(sdp), type="offer"))
        await asyncio.wait_for(self.pc.setLocalDescription(await self.pc.createAnswer()), 12)
        return self.pc.localDescription.sdp

    async def accept_answer(self, sdp):
        from aiortc import RTCSessionDescription
        await self.pc.setRemoteDescription(RTCSessionDescription(sdp=validate_sdp(sdp), type="answer"))

    async def ready(self):
        await asyncio.wait_for(self.opened.wait(), 15)
        if self.channel.readyState != "open":
            raise RuntimeError("Direct channel did not open")
        return True

    def activate(self):
        self.active = True

    def fail(self, text):
        if not self.closed:
            self.reactor.callFromThread(self.on_failure, RuntimeError(text))
        self.close()

    def send_record(self, data):
        if self.closed:
            return
        if not isinstance(data, bytes) or not 1 <= len(data) <= MAX_RECORD:
            raise ValueError("Invalid direct record")
        self.outbound_bytes += len(data)
        if self.outbound_bytes > LIMIT:
            self.fail("Direct send buffer limit exceeded")
            return
        self.pressure(self.outbound_bytes)
        def send():
            if not self.closed:
                try:
                    self.channel.send(data)
                    buffered = self.channel.bufferedAmount
                    if buffered > LIMIT:
                        self.fail("WebRTC send buffer limit exceeded")
                except Exception:
                    self.fail("Direct USB send failed")
                    buffered = 0
            else:
                buffered = 0
            self.reactor.callFromThread(self.sent, len(data), buffered)
        self.loop.call_soon_threadsafe(send)

    def sent(self, length, buffered):
        self.outbound_bytes -= length
        self.pressure(buffered + self.outbound_bytes)

    def pressure(self, buffered):
        if self.producer is None:
            return
        if buffered >= HIGH and not self.producer_paused:
            self.producer_paused = True
            self.producer.pauseProducing()
        elif buffered <= LOW and self.producer_paused:
            self.producer_paused = False
            self.producer.resumeProducing()

    def receive(self, data):
        if self.closed:
            with self.lock:
                self.pending_bytes -= len(data)
            return
        self.pending.append(data)
        self.flush()

    def flush(self):
        while self.consumer and not self.inbound_paused and self.pending:
            data = self.pending.popleft()
            with self.lock:
                self.pending_bytes -= len(data)
            self.consumer.write(data)

    def connectConsumer(self, consumer):
        self.consumer = consumer
        self.flush()

    def registerProducer(self, producer, streaming):
        self.producer = producer

    def unregisterProducer(self):
        self.producer = None

    def pauseProducing(self):
        self.inbound_paused = True

    def resumeProducing(self):
        self.inbound_paused = False
        self.flush()

    def stopProducing(self):
        self.close()

    def setTcpNoDelay(self, enabled):
        pass  # The data channel uses SCTP/DTLS/UDP, not TCP.

    def close(self):
        if self.closed:
            return
        self.closed = True
        async def close_peer():
            if self.pc:
                await self.pc.close()
        asyncio.run_coroutine_threadsafe(close_peer(), self.loop)


def decode_signal(raw, kind):
    import json
    if len(raw) > 65536:
        raise ValueError("Oversized direct negotiation")
    message = json.loads(raw)
    if not isinstance(message, dict) or message.get("kind") != kind:
        raise ValueError("Unexpected direct negotiation message")
    return message


async def negotiate(session):
    """Both peers agree on direct success before exposing any USB endpoint."""
    import json
    pipe = DirectPipe(session.reactor, session.fail, stun=session.config.get("stun", True))
    session.direct_attempt = pipe
    w = session.wormhole
    local_ok = False
    try:
        if session.role == "server":
            try:
                sdp = await session.wait(pipe.dispatch(pipe.make_offer()), 15)
            except Exception:
                if session.stopping:
                    raise defer.CancelledError()
                sdp = None
            w.send_message(json.dumps({"kind": "direct-offer", "sdp": sdp}).encode())
            answer = decode_signal(await session.wait(w.get_message(), 25), "direct-answer")
            if sdp and isinstance(answer.get("sdp"), str):
                await session.wait(pipe.dispatch(pipe.accept_answer(answer["sdp"])), 5)
                try:
                    local_ok = await session.wait(pipe.dispatch(pipe.ready()), 18)
                except Exception:
                    if session.stopping:
                        raise defer.CancelledError()
        else:
            offer = decode_signal(await session.wait(w.get_message(), 25), "direct-offer")
            answer_sdp = None
            if isinstance(offer.get("sdp"), str):
                try:
                    answer_sdp = await session.wait(pipe.dispatch(pipe.make_answer(offer["sdp"])), 15)
                except Exception:
                    if session.stopping:
                        raise defer.CancelledError()
            w.send_message(json.dumps({"kind": "direct-answer", "sdp": answer_sdp}).encode())
            if answer_sdp:
                try:
                    local_ok = await session.wait(pipe.dispatch(pipe.ready()), 18)
                except Exception:
                    if session.stopping:
                        raise defer.CancelledError()
        w.send_message(json.dumps({"kind": "direct-result", "ok": bool(local_ok)}).encode())
        peer = decode_signal(await session.wait(w.get_message(), 22), "direct-result")
        if local_ok and peer.get("ok") is True:
            pipe.activate()
            return pipe
        pipe.close()
        return None
    except BaseException:
        pipe.close()
        raise
