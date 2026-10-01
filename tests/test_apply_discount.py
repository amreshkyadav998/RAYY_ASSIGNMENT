import asyncio

from app.repositories import orders as orders_repo


async def apply(client, order_id, code):
    return await client.post(f"/orders/{order_id}/apply-discount", json={"code": code})


async def test_apply_percentage_discount_and_snapshot(client):
    r = await apply(client, "ord_a_1001", "PARTNER15")
    assert r.status_code == 200
    body = r.json()
    assert body["subtotal_paise"] == 19999
    assert body["total_paise"] == 19999 - 2999
    d = body["discount"]
    assert d["code"] == "PARTNER15"
    assert d["amount_paise"] == 2999
    assert (d["partner_share_paise"], d["rayy_share_paise"]) == (2099, 900)
    assert (d["partner_share_bps"], d["rayy_share_bps"]) == (7000, 3000)
    # persisted, not just returned
    got = (await client.get("/orders/ord_a_1001")).json()
    assert got["total_paise"] == 19999 - 2999


async def test_cap_is_applied(client):
    r = await apply(client, "ord_a_1002", "MEGA50")
    assert r.status_code == 200
    assert r.json()["discount"]["amount_paise"] == 6000
    assert r.json()["total_paise"] == 19999 - 6000
    assert r.json()["discount"]["partner_share_paise"] == 3600
    assert r.json()["discount"]["rayy_share_paise"] == 2400


async def test_expired_code_rejected_and_order_untouched(client):
    r = await apply(client, "ord_a_1002", "LASTWEEK20")
    assert r.status_code == 422
    order = (await client.get("/orders/ord_a_1002")).json()
    assert order["discount"] is None and order["total_paise"] == 19999


async def test_unknown_code_and_unknown_order(client):
    assert (await apply(client, "ord_a_1001", "NOPE")).status_code == 422
    assert (await apply(client, "ord_missing", "PARTNER15")).status_code == 404


async def test_code_is_case_insensitive(client):
    assert (await apply(client, "ord_a_1001", " partner15 ")).status_code == 200


async def test_empty_code_is_validation_error(client):
    assert (await apply(client, "ord_a_1001", "")).status_code == 422


async def test_same_code_twice_is_idempotent(client):
    first = (await apply(client, "ord_a_1001", "PARTNER15")).json()
    second = await apply(client, "ord_a_1001", "PARTNER15")
    assert second.status_code == 200
    assert second.json()["total_paise"] == first["total_paise"]


async def test_second_different_code_is_rejected_sequentially(client):
    # fixture apply_5
    assert (await apply(client, "ord_a_1004", "PARTNER15")).status_code == 200
    r = await apply(client, "ord_a_1004", "WELCOME10")
    assert r.status_code == 409
    order = (await client.get("/orders/ord_a_1004")).json()
    assert order["discount"]["code"] == "PARTNER15"
    assert order["total_paise"] == 19999 - 2999


async def test_two_codes_at_the_same_time_only_one_wins(client):
    # fixture apply_4
    results = await asyncio.gather(
        apply(client, "ord_a_1005", "PARTNER15"), apply(client, "ord_a_1005", "WELCOME10")
    )
    assert sorted(r.status_code for r in results) == [200, 409]
    winner = next(r for r in results if r.status_code == 200).json()["discount"]["code"]
    order = (await client.get("/orders/ord_a_1005")).json()
    assert order["discount"]["code"] == winner
    # total reflects exactly one discount, never both
    assert order["total_paise"] == order["subtotal_paise"] - order["discount"]["amount_paise"]


async def test_repository_guard_blocks_second_discount_even_if_service_raced(db):
    # The service's pre-checks are advisory; the conditional update is the rule.
    assert await orders_repo.apply_discount_if_open("ord_a_1001", {"code": "A"}, 100, 19999)
    assert not await orders_repo.apply_discount_if_open("ord_a_1001", {"code": "B"}, 50, 19999)


async def test_cannot_discount_a_paid_order(client, db):
    await db["orders"].update_one({"_id": "ord_a_1001"}, {"$set": {"status": "paid"}})
    r = await apply(client, "ord_a_1001", "PARTNER15")
    assert r.status_code == 409
