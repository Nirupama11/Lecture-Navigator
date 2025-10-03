from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Tuple
import threading
import time

_lock = threading.Lock()
_counters: Dict[str, int] = defaultdict(int)
_histograms: Dict[str, List[float]] = defaultdict(list)


def inc_counter(name: str, value: int = 1) -> None:
    with _lock:
        _counters[name] += value


def observe_histogram(name: str, value_ms: float) -> None:
    with _lock:
        _histograms[name].append(float(value_ms))


def snapshot() -> Dict[str, object]:
    with _lock:
        return {
            "counters": dict(_counters),
            "histograms": {k: _summary(v) for k, v in _histograms.items()},
        }


def _summary(values: List[float]) -> Dict[str, float]:
    if not values:
        return {"count": 0, "p50": 0.0, "p95": 0.0, "max": 0.0}
    vs = sorted(values)
    n = len(vs)
    def pct(p):
        idx = min(n - 1, max(0, int(p * n) - 1))
        return vs[idx]
    return {
        "count": float(n),
        "p50": pct(0.50),
        "p95": pct(0.95),
        "max": vs[-1],
    }



