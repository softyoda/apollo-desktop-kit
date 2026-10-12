import unittest
from direct import validate_sdp, decode_signal


class DirectValidation(unittest.TestCase):
    def description(self):
        return 'v=0\r\nm=application 9 UDP/DTLS/SCTP webrtc-datachannel\r\na=fingerprint:sha-256 ' + ':'.join(['AB']*32) + '\r\n'

    def test_only_data_channel_with_authenticated_fingerprint(self):
        good = self.description()
        self.assertEqual(validate_sdp(good), good)
        for bad in (good.replace('application', 'audio'), good.replace('sha-256', 'sha-1'),
                    good + 'm=video 9 UDP/TLS/RTP/SAVPF 96\r\n', good + 'a=candidate:1 1 udp 1 1.2.3.4 123 typ relay\r\n'):
            with self.assertRaises(ValueError):
                validate_sdp(bad)

    def test_signal_phase_and_size(self):
        self.assertEqual(decode_signal(b'{"kind":"direct-result","ok":true}', 'direct-result')['ok'], True)
        for data in (b'{"kind":"wrong"}', b'[]', b' ' * 65537):
            with self.assertRaises(ValueError):
                decode_signal(data, 'direct-result')
