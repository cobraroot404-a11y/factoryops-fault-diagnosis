# ADR 0002: Hysteresis + persistence windows for fault detection

## Status
Accepted

## Context
Real (and simulated) sensor readings are noisy near a threshold. A single
reading crossing a threshold and immediately opening/closing an incident
would flap constantly as noise oscillates around that value.

## Decision
Each numeric fault type (overheating, overload, vibration) has two
thresholds, not one: a `trigger` and a lower `clear`. Values strictly between
them are a dead zone that freezes both the breach and healthy counters. An
incident opens only after `persistence_breaches_to_trigger` **consecutive**
in-order breaching readings, and resolves only after
`persistence_healthy_to_clear` **consecutive** in-order healthy readings.
Both thresholds and both window sizes are configuration
(`backend/app/config.py`), not hardcoded.

FactoryOps never reports a confidence probability for a diagnosis — every
transition is explainable purely from the configured thresholds and the
sequence of readings that caused it (see `evidence` on each incident). This
is a rule engine, not a trained model.

## Consequences
- Noise inside the hysteresis band can never open or close an incident by
  itself (tested in `tests/worker/test_rules.py::test_hysteresis_band_noise_does_not_flap`).
- Recovery is intentionally slower than detection (5 healthy readings vs. 3
  breaching readings by default) — a real machine trending back to normal
  should stay there for a while before FactoryOps calls it resolved.
- Out-of-order readings (timestamp older than the last one already folded
  into a machine/fault-type's state) are stored but do not move the state
  machine, so a stale redelivered "healthy" reading cannot retroactively
  close an incident that later breaching readings already opened.
