"""An attacker with the rendezvous secret but the wrong identity is rejected."""
import secrets
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from twisted.internet import defer, task
from link import Session
from identity import test_pair_configs, new_identity


async def main(reactor):
    name = str(secrets.randbelow(900000000) + 100000000)
    events = []
    emit = lambda kind, value: events.append((kind, value))
    server, client = test_pair_configs()
    client.update(new_identity())  # The attacker has the shared secret, not the pinned private key.
    b = Session(reactor, server, emit, None,
                {"BusId": "1-4"}, simulate=True)
    p = Session(reactor, client, emit, None, simulate=True)
    b.start()
    p.start()
    try:
        await b.running.addTimeout(15, reactor)
        p.stop()
        await defer.DeferredList([b.running, p.running], consumeErrors=True).addTimeout(10, reactor)
        errors = [v for k,v in events if k == "security_error"]
        assert errors, events
        assert not any(k == "listen" for k,v in events), events
        assert b.pipe is None and p.pipe is None
        print("PASS: stolen rendezvous secret cannot impersonate the pinned peer; no USB listener or transit")
    finally:
        b.stop()
        p.stop()


if __name__ == "__main__":
    task.react(lambda reactor: defer.ensureDeferred(main(reactor)))
