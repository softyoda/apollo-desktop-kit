"""Pinned Ed25519 identities, PAKE invitations and session-bound signatures."""
import base64
import hashlib
import json
import re
import secrets
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, NoEncryption

PAIR_APPID = "org.apollo-desktop-kit/spacemouse/pair/v2"
SESSION_APPID = "org.apollo-desktop-kit/spacemouse/session/v2"


class AuthenticationError(ValueError):
    pass


def new_identity():
    key = Ed25519PrivateKey.generate()
    return {"private_key": key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()).hex(),
            "public_key": key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()}


def fingerprint(public_key):
    return hashlib.sha256(bytes.fromhex(public_key)).hexdigest().upper()


def short_id(public_key):
    text = fingerprint(public_key)[:24]
    return "-".join(text[i:i+4] for i in range(0, len(text), 4))


def make_invitation(public_key, now=None):
    now = int(time.time() if now is None else now)
    invitation = {"v": 2, "server_key": public_key, "expires": now + 300,
                  "code": str(secrets.randbelow(900000000) + 100000000) + "-" + secrets.token_hex(32)}
    text = "SML2." + base64.urlsafe_b64encode(json.dumps(invitation, separators=(",", ":")).encode()).decode()
    return invitation, text


def parse_invitation(text, now=None):
    now = int(time.time() if now is None else now)
    try:
        if not isinstance(text, str) or len(text) > 2048 or not text.startswith("SML2."):
            raise ValueError()
        value = json.loads(base64.b64decode(text[5:].strip(), altchars=b"-_", validate=True))
        if value.get("v") != 2 or not re.fullmatch(r"[a-f0-9]{64}", value.get("server_key", "")):
            raise ValueError()
        if not re.fullmatch(r"[0-9]{9}-[a-f0-9]{64}", value.get("code", "")):
            raise ValueError()
        if type(value.get("expires")) is not int or not now < value["expires"] <= now + 330:
            raise ValueError()
        return value
    except (ValueError, TypeError, AttributeError, KeyError) as exc:
        raise AuthenticationError("Invalid or expired invitation. Generate a new invitation on the server.") from exc


def signed_identity(config, verifier, purpose):
    role, public = config["role"], config["public_key"]
    payload = b"SpaceMouseLink-v2\0" + purpose.encode() + b"\0" + verifier + b"\0" + role.encode() + bytes.fromhex(public)
    signature = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(config["private_key"])).sign(payload)
    return {"role": role, "public_key": public, "signature": signature.hex()}


def verify_identity(proof, verifier, purpose, expected_role, pinned_key=None):
    try:
        public = proof["public_key"]
        if proof["role"] != expected_role or not re.fullmatch(r"[a-f0-9]{64}", public):
            raise ValueError()
        if pinned_key is not None and not secrets.compare_digest(public, pinned_key):
            raise ValueError()
        signature = bytes.fromhex(proof["signature"])
        payload = b"SpaceMouseLink-v2\0" + purpose.encode() + b"\0" + verifier + b"\0" + expected_role.encode() + bytes.fromhex(public)
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public)).verify(signature, payload)
        return public
    except (KeyError, TypeError, AttributeError, ValueError, InvalidSignature) as exc:
        raise AuthenticationError("Peer identity verification failed. Connection refused; pair again only with your own device.") from exc


def verification_code(verifier, server_key, client_key):
    value = hashlib.sha256(b"SML2/user-confirmation\0" + verifier + bytes.fromhex(server_key) + bytes.fromhex(client_key)).hexdigest()[:16].upper()
    return " ".join(value[i:i+4] for i in range(0, 16, 4))


def connection_code(secret):
    if not re.fullmatch(r"[a-f0-9]{64}", secret):
        raise AuthenticationError("Invalid stored pairing. Forget this peer and pair again.")
    name = int(hashlib.sha256(bytes.fromhex(secret)).hexdigest()[:8], 16) % 900000000 + 100000000
    return str(name) + "-" + secret


def test_pair_configs():
    """Fresh non-persistent identities for diagnostics; never an installed default."""
    a, b = new_identity(), new_identity()
    secret = secrets.token_hex(32)
    return ({**a, "role": "server", "peer_key": b["public_key"], "connection_secret": secret},
            {**b, "role": "client", "peer_key": a["public_key"], "connection_secret": secret})
