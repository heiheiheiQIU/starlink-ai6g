"""Integrate deterministic wire time inside the currently visible real window."""

from backend.contracts import Window
from .energy import finite_number


def transmission_time(windows: list[Window], start_s: float, mode: str,
                      wire_bytes: int, duration_s: float) -> float | None:
    start = finite_number(start_s, "start_s")
    duration = finite_number(duration_s, "duration_s", positive=True)
    if mode not in {"robust", "fast"}:
        raise ValueError("Transmission mode must be robust or fast")
    if isinstance(wire_bytes, bool) or not isinstance(wire_bytes, int) or wire_bytes <= 0:
        raise ValueError("wire_bytes must be a positive integer")
    end = finite_number(start + duration, "step end")
    for item in windows:
        window = Window.model_validate(item)
        if not window.start_s <= start < window.end_s:
            continue
        limit = min(end, window.end_s)
        points = window.rate_profile
        remaining = wire_bytes * 8
        for i, point in enumerate(points):
            left = max(start, point.time_s)
            right = min(limit, points[i + 1].time_s if i + 1 < len(points) else window.end_s)
            rate = getattr(point, f"{mode}_bps")
            if right <= left or rate == 0:
                continue
            needed = remaining / rate
            if needed <= right - left:
                finish = left + needed
                # The manual requires data transmission to finish before close.
                if finish >= window.end_s:
                    return None
                elapsed = finish - start
                if elapsed <= 0:
                    raise ValueError("Transmission time underflow")
                return elapsed
            remaining -= rate * (right - left)
        return None
    return None
