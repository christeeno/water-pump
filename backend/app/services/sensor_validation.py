import collections
import statistics
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, Deque, Dict, Any


@dataclass
class ValidationResult:
    raw_value: Optional[float]
    filtered_value: Optional[float]
    is_valid: bool
    status: str  # "OK", "DEGRADED", "OFFLINE"
    last_valid: Optional[float]
    is_stale: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class UltrasonicValidator:
    def __init__(
        self,
        min_distance: float = 2.0,
        max_distance: float = 400.0,
        window_size: int = 5,
        timeout_s: float = 10.0,
        degraded_threshold: int = 3,
        offline_threshold: int = 5,
    ):
        self.min_distance = min_distance
        self.max_distance = max_distance
        self.window_size = window_size
        self.timeout_s = timeout_s
        self.degraded_threshold = degraded_threshold
        self.offline_threshold = offline_threshold

        self.valid_window: Deque[float] = collections.deque(maxlen=window_size)
        self.consecutive_invalid: int = 0
        self.last_valid_value: Optional[float] = None
        self.last_valid_time: Optional[datetime] = None

    def validate(
        self,
        raw_distance: Optional[float],
        timestamp: Optional[datetime] = None,
    ) -> ValidationResult:
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        elif timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        # Check staleness / timeout
        is_stale = False
        if self.last_valid_time is not None:
            time_diff = (timestamp - self.last_valid_time).total_seconds()
            if time_diff > self.timeout_s:
                is_stale = True

        # Validation rules
        is_valid = True
        if raw_distance is None:
            is_valid = False
        elif raw_distance <= 0:
            is_valid = False
        elif raw_distance < self.min_distance or raw_distance > self.max_distance:
            is_valid = False

        if is_valid:
            self.consecutive_invalid = 0
            self.valid_window.append(raw_distance)
            filtered_val = float(statistics.median(self.valid_window))
            self.last_valid_value = filtered_val
            self.last_valid_time = timestamp
            status = "OK"
            is_stale = False
            return ValidationResult(
                raw_value=raw_distance,
                filtered_value=round(filtered_val, 2),
                is_valid=True,
                status=status,
                last_valid=round(self.last_valid_value, 2) if self.last_valid_value is not None else None,
                is_stale=False,
            )
        else:
            self.consecutive_invalid += 1
            if self.consecutive_invalid >= self.offline_threshold or is_stale:
                status = "OFFLINE"
            elif self.consecutive_invalid >= self.degraded_threshold:
                status = "DEGRADED"
            else:
                status = "DEGRADED" if self.consecutive_invalid > 0 else "OK"

            return ValidationResult(
                raw_value=raw_distance,
                filtered_value=round(self.last_valid_value, 2) if self.last_valid_value is not None else None,
                is_valid=False,
                status=status,
                last_valid=round(self.last_valid_value, 2) if self.last_valid_value is not None else None,
                is_stale=is_stale,
            )

    def reset(self):
        self.valid_window.clear()
        self.consecutive_invalid = 0
        self.last_valid_value = None
        self.last_valid_time = None


def calculate_tank_level(
    filtered_distance: float,
    empty_distance: float,
    full_distance: float,
) -> float:
    """
    Calculate tank percentage level from filtered distance.
    Only call after validation passes.
    level = (empty - current) / (empty - full) * 100
    Clamped to 0 - 100.
    Raises ValueError if empty == full.
    """
    if empty_distance == full_distance:
        raise ValueError("empty_distance cannot equal full_distance")

    level = (empty_distance - filtered_distance) / (empty_distance - full_distance) * 100.0
    return max(0.0, min(100.0, round(level, 2)))
