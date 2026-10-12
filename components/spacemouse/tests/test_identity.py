import json
import secrets
import unittest
from identity import (AuthenticationError, make_invitation, parse_invitation, new_identity,
                      signed_identity, verify_identity, verification_code, test_pair_configs)


class IdentityTests(unittest.TestCase):
    def test_invitation_expiry_and_limits(self):
        a = new_identity()
        invite, text = make_invitation(a["public_key"], now=1000)
        self.assertEqual(parse_invitation(text, now=1001), invite)
        for invalid, now in ((text,1300), (text,900), (text+'!',1001), ('x'*2049,1001)):
            with self.assertRaises(AuthenticationError):
                parse_invitation(invalid, now)

    def test_pin_rejects_another_identity_even_with_shared_secret(self):
        server, client = test_pair_configs()
        outsider = {"role": "server", **new_identity()}
        verifier = secrets.token_bytes(32)
        proof = signed_identity(outsider, verifier, "session")
        with self.assertRaises(AuthenticationError):
            verify_identity(proof, verifier, "session", "server", client["peer_key"])

    def test_valid_pin_and_replay_rejection(self):
        server, client = test_pair_configs()
        verifier = secrets.token_bytes(32)
        proof = signed_identity(server, verifier, "session")
        self.assertEqual(verify_identity(proof,verifier,"session","server",client["peer_key"]),server["public_key"])
        for challenge,purpose,role in ((secrets.token_bytes(32),"session","server"),
                                      (verifier,"pairing","server"),(verifier,"session","client")):
            with self.assertRaises(AuthenticationError):
                verify_identity(proof, challenge, purpose, role, client["peer_key"])

    def test_signature_modification_and_confirmation_binding(self):
        a, b = test_pair_configs()
        v = secrets.token_bytes(32)
        proof = signed_identity(a,v,"pairing")
        proof["signature"] = '00'*64
        with self.assertRaises(AuthenticationError):
            verify_identity(proof,v,"pairing","server",a["public_key"])
        original = verification_code(v,a["public_key"],b["public_key"])
        self.assertNotEqual(original,verification_code(v,a["public_key"],new_identity()["public_key"]))
        self.assertNotEqual(original,verification_code(secrets.token_bytes(32),a["public_key"],b["public_key"]))
