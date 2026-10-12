import unittest
from latency import LatencySamples


class LatencyTests(unittest.TestCase):
    def test_only_one_outstanding_probe(self):
        probe = LatencySamples()
        self.assertIsNone(probe.received(1))
        self.assertTrue(probe.sent(1))
        self.assertFalse(probe.sent(1.01))
        self.assertEqual(probe.received(1.07)["latest_ms"], 70)
        self.assertIsNone(probe.received(1.08))

    def test_rolling_statistics(self):
        probe = LatencySamples(capacity=3)
        for index, value in enumerate((200, 60, 70, 80)):
            probe.sent(index)
            result = probe.received(index + value / 1000)
        self.assertEqual(result, {"samples": 3, "total_samples": 4, "latest_ms": 80,
                                 "min_ms": 60, "median_ms": 70, "p95_ms": 80, "max_ms": 80})
