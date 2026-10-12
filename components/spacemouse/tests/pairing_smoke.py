"""Live rendezvous tests using throwaway keys and simulated user approvals."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os
os.environ['AUTOBAHN_USE_NVX'] = '0'
from twisted.internet import task, defer
from identity import new_identity, make_invitation
from pairing import Pairing


async def scenario(reactor, approve):
    a, b = {'role':'server', **new_identity()}, {'role':'client', **new_identity()}
    invitation, _ = make_invitation(a['public_key'])
    results, codes, peers = {}, {}, {}
    def emitter(role):
        def emit(kind, value):
            if kind == 'pair_confirm':
                codes[role] = value['code']
                if len(codes) == 2:
                    assert codes['server'] == codes['client']
                    peers['server'].approve(approve)
                    peers['client'].approve(True)
            if kind == 'paired':
                results[role] = value
        return emit
    peers['server'] = Pairing(reactor,a,invitation,emitter('server'))
    peers['client'] = Pairing(reactor,b,invitation,emitter('client'))
    runs = [defer.ensureDeferred(p.run()) for p in peers.values()]
    try:
        await defer.DeferredList(runs, fireOnOneErrback=True).addTimeout(20,reactor)
        if approve:
            assert results['server']['peer_key'] == b['public_key']
            assert results['client']['peer_key'] == a['public_key']
            assert results['server']['connection_secret'] == results['client']['connection_secret']
        else:
            assert not results, 'Rejected pairing must never persist credentials'
    finally:
        for p in peers.values():
            p.stop()


async def main(reactor):
    await scenario(reactor,True)
    await scenario(reactor,False)
    print('PASS: mutual confirmation pins both keys; rejection saves no pairing')


if __name__ == '__main__':
    task.react(lambda r: defer.ensureDeferred(main(r)))
