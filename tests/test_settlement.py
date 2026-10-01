from datetime import datetime, timedelta, timezone

from app.repositories import discount_codes
from app.repositories import orders as orders_repo
from tests.test_webhook import event, post


def _window():
    now = datetime.now(timezone.utc)
    return now - timedelta(days=1), now + timedelta(days=1)


async def test_settlement_uses_stored_snapshot_not_current_split(client):
    await client.post("/orders/ord_a_1001/apply-discount", json={"code": "PARTNER15"})
    await post(client, event("pay_s1", "ord_a_1001", 19999 - 2999))

    # The partner's split changes "next month": mutate the live code.
    code = discount_codes.get_by_code("PARTNER15")
    object.__setattr__(code, "partner_share_bps", 1000)
    object.__setattr__(code, "rayy_share_bps", 9000)
    try:
        rows = await orders_repo.settlement_by_partner(*_window())
    finally:
        object.__setattr__(code, "partner_share_bps", 7000)
        object.__setattr__(code, "rayy_share_bps", 3000)
    assert rows == [{"partner_id": "prt_a_01", "partner_share_paise": 2099, "rayy_share_paise": 900, "orders": 1}]


async def test_settlement_ignores_unpaid_and_out_of_window(client):
    await client.post("/orders/ord_a_1002/apply-discount", json={"code": "MEGA50"})  # never paid
    await client.post("/orders/ord_a_1001/apply-discount", json={"code": "PARTNER15"})
    await post(client, event("pay_s1", "ord_a_1001", 19999 - 2999))
    now = datetime.now(timezone.utc)
    assert await orders_repo.settlement_by_partner(now + timedelta(days=1), now + timedelta(days=2)) == []
    rows = await orders_repo.settlement_by_partner(*_window())
    assert rows[0]["orders"] == 1
