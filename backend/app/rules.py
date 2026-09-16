"""Pure, deterministic threshold/hysteresis/persistence rule engine.

No I/O here on purpose: this module is unit-tested directly (tests/worker/test_rules.py)
and imported by the diagnosis worker. It intentionally never computes a confidence
probability — only a threshold-based state transition with an explicit trail of
the evidence (readings) that caused it.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricThreshold:
    trigger: float
    clear: float
    unit: str


@dataclass
class EvalResult:
    consecutive_breach: int
    consecutive_healthy: int
    state: str  # "healthy" | "active"
    transitioned_to_active: bool
    transitioned_to_healthy: bool


def evaluate(
    value: float,
    threshold: MetricThreshold,
    consecutive_breach: int,
    consecutive_healthy: int,
    state: str,
    persistence_breaches_to_trigger: int,
    persistence_healthy_to_clear: int,
) -> EvalResult:
    """Advance one machine/fault-type state machine by exactly one (in-order) reading.

    Hysteresis: values strictly between `clear` and `trigger` are a dead zone that
    freezes both counters, so noise oscillating near a single threshold cannot flap
    the incident open/closed.
    """
    if value >= threshold.trigger:
        consecutive_breach += 1
        consecutive_healthy = 0
    elif value <= threshold.clear:
        consecutive_healthy += 1
        consecutive_breach = 0
    # else: inside the hysteresis band — counters intentionally unchanged.

    transitioned_to_active = False
    transitioned_to_healthy = False

    if state == "healthy" and consecutive_breach >= persistence_breaches_to_trigger:
        state = "active"
        transitioned_to_active = True
    elif state == "active" and consecutive_healthy >= persistence_healthy_to_clear:
        state = "healthy"
        transitioned_to_healthy = True

    return EvalResult(
        consecutive_breach=consecutive_breach,
        consecutive_healthy=consecutive_healthy,
        state=state,
        transitioned_to_active=transitioned_to_active,
        transitioned_to_healthy=transitioned_to_healthy,
    )
