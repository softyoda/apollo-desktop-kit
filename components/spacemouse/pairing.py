"""Explicit short-lived pairing. No USB access before both humans approve."""
import json
import time
from twisted.internet import defer
from wormhole import create
from wormhole.cli.public_relay import MAILBOX_RELAY
from identity import (PAIR_APPID, AuthenticationError, signed_identity, verify_identity,
                      verification_code, short_id)


class Pairing:
    def __init__(self, reactor, config, invitation, emit):
        self.reactor, self.config, self.invitation, self.emit = reactor, config, invitation, emit
        self.w = None
        self.approval = None
        self.waiting = None
        self.stopped = False
        self.deadline = time.monotonic() + max(0, min(300, invitation["expires"] - time.time()))

    async def wait(self, pending):
        if self.stopped:
            pending.cancel()
            raise defer.CancelledError()
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            pending.cancel()
            raise AuthenticationError("Invitation expired. Generate a new one.")
        self.waiting = pending
        try:
            return await pending.addTimeout(remaining, self.reactor)
        finally:
            self.waiting = None

    def approve(self, allowed):
        if self.approval is not None and not self.approval.called:
            self.approval.callback(bool(allowed))

    def stop(self):
        self.stopped = True
        if self.waiting is not None and not self.waiting.called:
            self.waiting.cancel()

    async def run(self):
        try:
            self.w = create(PAIR_APPID, MAILBOX_RELAY, self.reactor)
            self.w.set_code(self.invitation["code"])
            verifier = await self.wait(self.w.get_verifier())
            self.w.send_message(json.dumps(signed_identity(self.config, verifier, "pairing")).encode())
            raw = await self.wait(self.w.get_message())
            if len(raw) > 1024:
                raise AuthenticationError("Invalid pairing identity")
            role = self.config["role"]
            other_role = "client" if role == "server" else "server"
            pinned = self.invitation["server_key"] if role == "client" else None
            public = verify_identity(json.loads(raw), verifier, "pairing", other_role, pinned)
            server_key = self.config["public_key"] if role == "server" else public
            client_key = public if role == "server" else self.config["public_key"]
            self.approval = defer.Deferred()
            self.emit("pair_confirm", {"code": verification_code(verifier, server_key, client_key),
                                       "peer": short_id(public)})
            approved = await self.wait(self.approval)
            self.w.send_message(json.dumps({"approved": approved}).encode())
            if not approved:
                raise AuthenticationError("Pairing cancelled. The invitation is no longer used by this app.")
            reply = await self.wait(self.w.get_message())
            if len(reply) > 128 or json.loads(reply).get("approved") is not True:
                raise AuthenticationError("The other device did not approve pairing.")
            result = {"peer_key": public,
                      "connection_secret": self.w.derive_key(PAIR_APPID + "/pinned-connection", 32).hex()}
            self.emit("paired", result)
        except defer.CancelledError:
            self.emit("status", "Pairing cancelled")
        except Exception as exc:
            self.emit("security_error", str(exc))
        finally:
            if self.w:
                try:
                    await self.w.close().addTimeout(5, self.reactor)
                except Exception:
                    pass
            self.emit("pair_finished", None)
