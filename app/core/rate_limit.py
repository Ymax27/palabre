from collections import defaultdict
from time import monotonic

_hits: dict[str, list[float]] = defaultdict(list)


def allow(key: str, limit: int, window_seconds: int) -> bool:
    now = monotonic()
    recent = [stamp for stamp in _hits[key] if now - stamp < window_seconds]
    if len(recent) >= limit:
        _hits[key] = recent
        return False
    recent.append(now)
    _hits[key] = recent
    return True
