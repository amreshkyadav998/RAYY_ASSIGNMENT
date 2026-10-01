"""Order business rules. No HTTP here; routes call into this module."""

from datetime import datetime, timezone

from app.models import AppliedDiscount, Order
from app.repositories import discount_codes as discount_codes_repo
from app.repositories import orders as orders_repo
from app.services import pricing


class OrderNotFound(Exception):
    pass


async def get_order(order_id: str) -> Order:
    doc = await orders_repo.get(order_id)
    if doc is None:
        raise OrderNotFound(order_id)
    return Order(**doc)


async def list_orders(limit: int = 50) -> list[Order]:
    return [Order(**doc) for doc in await orders_repo.list_recent(limit)]


class DiscountCodeInvalid(Exception):
    """Unknown or expired code."""


class OrderNotDiscountable(Exception):
    """Order already paid, or already carries a different discount code."""


async def apply_discount(order_id: str, code_str: str, now: datetime | None = None) -> Order:
    """Apply a partner code to a pending order.

    Policy: one code per order. Re-sending the same code is idempotent; a
    different code is rejected (OrderNotDiscountable) rather than replacing or
    stacking.
    """
    now = now or datetime.now(timezone.utc)
    order = await get_order(order_id)
    code = discount_codes_repo.get_by_code(code_str.strip().upper())
    if code is None:
        raise DiscountCodeInvalid("unknown discount code")
    if order.discount is not None:
        if order.discount.code == code.code:
            return order
        raise OrderNotDiscountable("order already has a discount code")
    if order.status != "pending":
        raise OrderNotDiscountable("order is not pending")
    if code.expires_at <= now:
        raise DiscountCodeInvalid("discount code expired")

    breakdown = pricing.compute_discount(order.subtotal_paise, code)
    snapshot = AppliedDiscount(
        code=code.code,
        amount_paise=breakdown.amount_paise,
        percent_off_bps=code.percent_off_bps,
        cap_paise=code.cap_paise,
        partner_share_bps=code.partner_share_bps,
        rayy_share_bps=code.rayy_share_bps,
        partner_share_paise=breakdown.partner_share_paise,
        rayy_share_paise=breakdown.rayy_share_paise,
        applied_at=now,
    )
    won = await orders_repo.apply_discount_if_open(
        order_id, snapshot.model_dump(), order.subtotal_paise - breakdown.amount_paise, order.subtotal_paise
    )
    # Re-read: either we won, or someone else changed the order first and the
    # same rules decide what the caller sees.
    current = await get_order(order_id)
    if won:
        return current
    if current.discount is not None and current.discount.code == code.code:
        return current
    raise OrderNotDiscountable("order already has a discount code or is no longer pending")
