from datetime import datetime, timedelta, timezone

from cleanup_service import PaymentEvent, SweepRequest, decide_cleanup


def test_only_stale_high_risk_pending_events_are_quarantined():
    now = datetime.now(timezone.utc)
    request = SweepRequest(before=now - timedelta(days=30))
    stale_risky = PaymentEvent("evt-1", "acct-1", now - timedelta(days=31), 85, "pending")
    fresh_risky = PaymentEvent("evt-2", "acct-1", now - timedelta(days=2), 85, "pending")
    stale_low_risk = PaymentEvent("evt-3", "acct-1", now - timedelta(days=31), 20, "pending")
    assert decide_cleanup(stale_risky, request).action == "quarantine"
    assert decide_cleanup(fresh_risky, request) is None
    assert decide_cleanup(stale_low_risk, request) is None
