# Security model and validation

This document describes what is protected and what the tests demonstrate. It is **not a proof of absolute security, a formal verification or an independent audit**. The custom app is a public beta.

## Intended trust boundary

Protect the SpaceMouse USB stream from network observers, untrusted rendezvous/relay operators and unauthorized remote computers. Each Windows-user role profile trusts exactly one peer identity. Restrict forwarding to the selected USB SpaceMouse Compact (VID 256F, PID C635), not a general network tunnel or arbitrary USB sharing.

Trusted: both Windows installations/accounts, their administrators, the installed USB drivers, Python/crypto/WebRTC dependencies, the installer delivery chain, and the user checking the pairing codes. A compromised trusted endpoint can act as that endpoint. This is key-based identity pinning, not hardware attestation: an administrator who extracts/clones both the protected identity and pairing state can clone a device.

## First pairing

Each profile creates its own Ed25519 identity at first launch, never during the build. Server creates a random 256-bit invitation secret expiring after five minutes. The invitation includes Server's public key. Client explicitly copies that invitation; neither GitHub nor an installer distributes a shared operational secret.

Magic Wormhole SPAKE2 authenticates the invitation and derives a fresh encrypted session. Both identities sign the session verifier, a domain separator, the protocol purpose and their role. Client checks the Server key against the invitation. Both screens show a 64-bit comparison code derived from the verifier and both public keys. **Both users must approve** before either stores the peer key and a newly derived connection secret.

An attacker who observes the network cannot recover the invitation or replace an identity without breaking the underlying cryptography. If the invitation itself is stolen before use, an attacker may race the legitimate client; explicit comparison/confirmation on both screens is therefore essential. Pairing is not unattended. Rejected/expired invitations are discarded by the application, and the pairing listener closes after the attempt.

## Subsequent connections

The peers first authenticate the saved high-entropy connection secret using SPAKE2, then prove possession of the **pinned Ed25519 private key** over that session's verifier. Reusing the secret alone is insufficient. Role and purpose binding prevent using a pairing proof as a connection proof or reflecting a client proof as a server proof. A signature from a previous session is rejected because the verifier changes.

Peer identity verification happens before opening the USB tunnel. WebRTC certificate fingerprints and candidates are exchanged within that authenticated encrypted signaling session. WebRTC uses reliable ordered SCTP over DTLS/UDP, and verifies the fingerprint. Only one application data channel is accepted, with bounded records and queues; audio/video channels are rejected. No TURN service is configured, so DIRECT does not hide a TURN relay. ICE/STUN may fail on restrictive NATs; the UI explicitly labels the authenticated encrypted TCP relay fallback.

The relay path uses Magic Wormhole/PyNaCl authenticated records with sequence/nonce checks. Frame lengths are bounded before buffering. Device import requests and returned VID/PID are checked. Neither path accepts an arbitrary destination host/port supplied by a peer. Relays can deny service and observe IPs, sizes and timing. Availability, endpoint compromise and all traffic analysis are outside the confidentiality guarantee.

## Windows privilege boundary

The app and tray run as a normal user. Native driver installation is an explicit optional elevated installer task; Server device preparation is a separate narrow UAC action. Native downloads are pinned by SHA-256 and checked by Authenticode. The installer does not enable test signing, disable Windows security, add a VPN or configure the ISP router.

The Server's native usbipd service listens on TCP 3240. A Windows Firewall block rejects non-loopback sources; its default LAN allow rule is disabled. The app checks that protection before exposing USB through the tunnel. Company policy that disables local firewall rules must be resolved by IT rather than bypassed. **Local processes can still access the native loopback USB service**; this app does not claim isolation from other untrusted local software or administrators.

Identity/pairing files use DPAPI with **CurrentUser** scope. They live in the user's private profile directory, not in the installed binary. Other accounts cannot decrypt the blob merely by obtaining a copy. Software already running as the same user can request DPAPI decryption, so malware in that account remains outside the threat boundary. Forgetting a peer removes the saved peer key and connection secret and disables automatic connection.

## Evidence

- Protocol tests reject wrong device IDs, wrong USB operations and invalid framing.
- Crypto tests reject altered ciphertext, wrong keys and replayed nonces.
- Identity tests reject expired invitations, wrong pinned identities, changed signatures, role/purpose confusion and previous-session proofs.
- Live synthetic pairing test verifies equal comparison codes and mutual pinning; rejecting one side saves no credentials.
- Live adversarial session test gives an attacker the connection secret but a different private key: the authorized Server rejects it before any USB listener or transit connection exists.
- Synthetic transport tests exercise direct mode and relay fallback with generated bytes, not user files or hardware data.
- A reject-only native-client test verifies unprivileged client access without importing a real device.

These are executable tests under `tests/`. Passing tests supports these specific properties; it does not establish absence of all vulnerabilities. No third-party penetration test or formal proof has been performed. WAN behavior, company firewall policy, driver installation and tray/startup behavior still require validation on the deployment machines.

## Services and dependencies

- Rendezvous: `relay.magic-wormhole.io:4000` (the application payload is PAKE-encrypted even though the WebSocket is not TLS).
- STUN: `stun.l.google.com:19302` over UDP, only address discovery.
- Fallback relay: `relay.mw.leastauthority.com:4001`; no plaintext USB data.
- USB server: [usbipd-win 5.3.0](https://github.com/dorssel/usbipd-win/releases/tag/v5.3.0).
- Virtual USB client: [usbip-win2 0.9.8.1](https://github.com/vadimgrn/usbip-win2/releases/tag/v.0.9.8.1).
- [Magic Wormhole protocol](https://magic-wormhole.readthedocs.io/en/latest/client-protocol.html), [aiortc API](https://aiortc.readthedocs.io/en/latest/api.html).

Do not post invitations, private keys, DPAPI files or workstation data in an issue. Report a suspected vulnerability privately to the repository owner when GitHub private vulnerability reporting is available; otherwise request a private contact channel without disclosing exploit credentials.
