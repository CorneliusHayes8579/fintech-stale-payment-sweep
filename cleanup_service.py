"""Periodic stale-payment sweep with an audit record for every decision."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List

from infrai_client import InfraiClient


@dataclass(frozen=True)
class PaymentEvent:
    event_id: str
    account_id: str
    occurred_at: datetime
    risk_score: int
    status: str


@dataclass(frozen=True)
class SweepRequest:
    before: datetime
    minimum_risk_score: int = 70


@dataclass(frozen=True)
class AuditNotification:
    event_id: str
    action: str
    reason: str


def decide_cleanup(event: PaymentEvent, request: SweepRequest) -> AuditNotification | None:
    stale = event.occurred_at < request.before
    risky = event.risk_score >= request.minimum_risk_score
    if stale and risky and event.status == "pending":
        return AuditNotification(event.event_id, "quarantine", "stale pending payment with elevated risk")
    return None


def run_sweep(events: List[PaymentEvent], request: SweepRequest, client: InfraiClient) -> List[AuditNotification]:
    notices = [notice for event in events if (notice := decide_cleanup(event, request))]
    for notice in notices:
        client.queue.publish({"event_id": notice.event_id, "action": notice.action, "reason": notice.reason})
    return notices


def schedule_sweep(client: InfraiClient, task_url: str) -> str:
    result = client.cron.create(cron_expr="0 * * * *", task=task_url)
    return str(result["job_id"])


if __name__ == "__main__":
    client = InfraiClient()
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    print("scheduled job:", schedule_sweep(client, "https://example.com/payments/sweep"))
    print("cutoff:", cutoff.isoformat())
