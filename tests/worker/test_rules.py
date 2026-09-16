"""Pure unit tests for the threshold/hysteresis/persistence rule engine.

No database or broker needed — run with:
  PYTHONPATH=backend pytest tests/worker/test_rules.py -v
"""
from app.rules import MetricThreshold, evaluate

TEMP = MetricThreshold(trigger=85.0, clear=75.0, unit="C")


def _run(values, breaches_to_trigger=3, healthy_to_clear=5):
    breach = healthy = 0
    state = "healthy"
    history = []
    for v in values:
        r = evaluate(v, TEMP, breach, healthy, state, breaches_to_trigger, healthy_to_clear)
        breach, healthy, state = r.consecutive_breach, r.consecutive_healthy, r.state
        history.append(r)
    return history


def test_healthy_readings_never_trigger():
    history = _run([50.0] * 20)
    assert all(h.state == "healthy" for h in history)
    assert all(not h.transitioned_to_active for h in history)


def test_sustained_breach_triggers_after_persistence_window():
    history = _run([90.0, 90.0, 90.0])
    assert history[0].transitioned_to_active is False
    assert history[1].transitioned_to_active is False
    assert history[2].transitioned_to_active is True
    assert history[2].state == "active"


def test_noise_in_hysteresis_band_does_not_flap():
    # Values strictly between clear (75) and trigger (85) must not build toward
    # either a breach or a clear, so oscillation near a single threshold cannot
    # flap an incident open and closed.
    history = _run([80.0] * 30)
    assert all(h.state == "healthy" for h in history)
    assert all(h.consecutive_breach == 0 and h.consecutive_healthy == 0 for h in history)


def test_hysteresis_dip_freezes_rather_than_resets_the_breach_counter():
    # 80C is inside the hysteresis band (between clear=75 and trigger=85): it
    # freezes the breach counter at 2 rather than resetting it to 0, so the
    # very next genuine breach (the 4th reading overall) reaches 3 and triggers
    # -- one reading earlier than a "reset on any non-breach" design would.
    history = _run([90.0, 90.0, 80.0, 90.0, 90.0, 90.0])
    assert [h.transitioned_to_active for h in history] == [False, False, False, True, False, False]
    assert history[-1].state == "active"


def test_recovery_requires_full_healthy_window():
    breach = 3
    healthy = 0
    state = "active"
    for i, v in enumerate([70.0] * 4):
        r = evaluate(v, TEMP, breach, healthy, state, 3, 5)
        breach, healthy, state = r.consecutive_breach, r.consecutive_healthy, r.state
        assert r.transitioned_to_healthy is False, f"cleared too early at step {i}"
    r = evaluate(70.0, TEMP, breach, healthy, state, 3, 5)
    assert r.transitioned_to_healthy is True
    assert r.state == "healthy"


def test_out_of_order_style_replay_is_deterministic():
    # The rule engine itself is order-dependent by design (it only ever sees
    # readings the caller chooses to feed it in order); out-of-order protection
    # lives in the worker, which simply skips stale readings before calling
    # evaluate(). Here we confirm evaluate() is a pure function of its inputs.
    r1 = evaluate(90.0, TEMP, 2, 0, "healthy", 3, 5)
    r2 = evaluate(90.0, TEMP, 2, 0, "healthy", 3, 5)
    assert r1 == r2
