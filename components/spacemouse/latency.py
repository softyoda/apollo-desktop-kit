"""RTT of one outstanding application-level ping, without clock synchronisation."""
from collections import deque
import math
import statistics


class LatencySamples:
    def __init__(self, capacity=300):
        self.values = deque(maxlen=capacity)
        self.pending = None
        self.total = 0

    def sent(self, now):
        if self.pending is not None:
            return False
        self.pending = now
        return True

    def received(self, now):
        if self.pending is None:
            return None
        elapsed = (now - self.pending) * 1000
        self.pending = None
        if elapsed < 0:
            return None
        self.values.append(elapsed)
        self.total += 1
        ordered = sorted(self.values)
        return {"samples": len(ordered), "total_samples": self.total,
                "latest_ms": round(elapsed, 1), "min_ms": round(ordered[0], 1),
                "median_ms": round(statistics.median(ordered), 1),
                "p95_ms": round(ordered[math.ceil(len(ordered) * .95) - 1], 1),
                "max_ms": round(ordered[-1], 1)}
