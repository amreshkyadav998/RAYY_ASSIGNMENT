"""Payment webhook handling. No HTTP here."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from app.models import PaymentWebhook
from app.repositories import orders as orders_repo

log = logging.getLogger(__name__)

HANDLED_EVENT = "payment.succeeded"


class PaymentOrderNotFound(Exception):
    pass


@dataclass(frozen=True)
class PaymentResult:
    # applied | duplicate | ignored | amount_mismatch | already_paid_other_payment
    outcome: str


async def handle_payment_succeeded(event: PaymentWebhook, now: datetime | None = None) -> PaymentResult:
    """Mark the order paid exactly once.

    The state change is a single conditional update (pending + amount equals
    the order total), so duplicate or concurrent deliveries, and a discount
    landing mid-flight, cannot double-apply. Anything that does not apply
    cleanly is classified from the order's current state and noted on it.
    """
    if event.event != HANDLED_EVENT:
        return PaymentResult("ignored")
    now = now or datetime.now(timezone.utc)
    payment = {"payment_id": event.payment_id, "amount_paise": event.amount_paise, "received_at": now}

    if await orders_repo.mark_paid_if_matching(event.order_id, event.amount_paise, payment, now):
        return PaymentResult("applied")

    order = await orders_repo.get(event.order_id)
    if order is None:
        raise PaymentOrderNotFound(event.order_id)

    anomaly = dict(payment)
    if order["status"] == "paid":
        if (order.get("payment") or {}).get("payment_id") == event.payment_id:
            return PaymentResult("duplicate")
        anomaly["reason"] = "order already paid by a different payment"
        outcome = "already_paid_other_payment"
    else:
        anomaly["reason"] = f"charged {event.amount_paise} but order total is {order['total_paise']}"
        outcome = "amount_mismatch"
    if event.payment_id not in {a.get("payment_id") for a in order.get("payment_anomalies", [])}:
        await orders_repo.record_payment_anomaly(event.order_id, anomaly)
    log.warning("payment %s for %s not applied: %s", event.payment_id, event.order_id, anomaly["reason"])
    return PaymentResult(outcome)
