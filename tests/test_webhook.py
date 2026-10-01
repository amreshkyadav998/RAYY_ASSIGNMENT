import asyncio
import json

from app.gateway import SIGNATURE_HEADER, StubGateway

gateway = StubGateway(webhook_secret="whsec_test")


def signed(body: dict | bytes):
    raw = body if isinstance(body, bytes) else json.dumps(body, separators=(",", ":")).encode()
    return {SIGNATURE_HEADER: gateway.sign(raw), "Content-Type": "application/json"}, raw


def event(payment_id="pay_1", order_id="ord_a_1003", amount=89900, kind="payment.succeeded"):
    return {"event": kind, "payment_id": payment_id, "order_id": order_id, "amount_paise": amount}


async def post(client, body):
    headers, raw = signed(body)
    return await client.post("/webhooks/payment", content=raw, headers=headers)


async def order(client, order_id):
    return (await client.get(f"/orders/{order_id}")).json()


async def test_payment_marks_order_paid_and_records_payment(client):
    r = await post(client, event("pay_a_7001"))
    assert r.status_code == 200 and r.json() == {"status": "applied"}
    o = await order(client, "ord_a_1003")
    assert o["status"] == "paid"
    assert o["payment"]["payment_id"] == "pay_a_7001"
    assert o["payment"]["amount_paise"] == 89900
    assert o["paid_at"] is not None


async def test_duplicate_delivery_is_applied_once(client, db):
    # fixture webhook_1: delivered twice, using the gateway's own deliveries()
    payment = {"payment_id": "pay_a_7001", "order_id": "ord_a_1003", "amount_paise": 89900}
    for headers, body in gateway.deliveries(payment):
        r = await client.post("/webhooks/payment", content=body, headers=headers)
        assert r.status_code == 200
    o = await order(client, "ord_a_1003")
    first_paid_at = o["paid_at"]
    assert o["status"] == "paid"
    raw = await db["orders"].find_one({"_id": "ord_a_1003"})
    assert "payment_anomalies" not in raw
    # a later redelivery must not move paid_at
    await post(client, event("pay_a_7001"))
    assert (await order(client, "ord_a_1003"))["paid_at"] == first_paid_at


async def test_concurrent_duplicate_deliveries(client, db):
    results = await asyncio.gather(*[post(client, event("pay_a_7001")) for _ in range(5)])
    assert all(r.status_code == 200 for r in results)
    assert sorted(r.json()["status"] for r in results).count("applied") == 1
    assert "payment_anomalies" not in await db["orders"].find_one({"_id": "ord_a_1003"})


async def test_bad_or_missing_signature_rejected(client):
    raw = json.dumps(event()).encode()
    r = await client.post("/webhooks/payment", content=raw)
    assert r.status_code == 401
    r = await client.post("/webhooks/payment", content=raw, headers={SIGNATURE_HEADER: "deadbeef"})
    assert r.status_code == 401
    wrong = StubGateway(webhook_secret="other").sign(raw)
    r = await client.post("/webhooks/payment", content=raw, headers={SIGNATURE_HEADER: wrong})
    assert r.status_code == 401
    assert (await order(client, "ord_a_1003"))["status"] == "pending"


async def test_signature_covers_the_exact_body(client):
    headers, raw = signed(event(amount=89900))
    tampered = raw.replace(b"89900", b"1")
    r = await client.post("/webhooks/payment", content=tampered, headers=headers)
    assert r.status_code == 401


async def test_malformed_body_with_valid_signature(client):
    bad_bodies = [
        b"not json",
        json.dumps({"event": "payment.succeeded"}).encode(),
        json.dumps(event(amount=1.5)).encode(),
        json.dumps(event(amount="89900")).encode(),
        json.dumps(event(amount=-5)).encode(),
    ]
    for bad in bad_bodies:
        headers, raw = signed(bad)
        r = await client.post("/webhooks/payment", content=raw, headers=headers)
        assert r.status_code == 400, bad


async def test_unknown_order_is_404(client):
    assert (await post(client, event(order_id="ord_nope"))).status_code == 404


async def test_other_events_are_acknowledged_and_ignored(client):
    r = await post(client, event(kind="payment.failed"))
    assert r.status_code == 200 and r.json() == {"status": "ignored"}
    assert (await order(client, "ord_a_1003"))["status"] == "pending"


async def test_charge_of_undiscounted_amount_does_not_mark_paid(client, db):
    # fixture webhook_2: discount applied first, gateway charged the full price
    await client.post("/orders/ord_a_1001/apply-discount", json={"code": "PARTNER15"})
    r = await post(client, event("pay_a_7002", "ord_a_1001", 19999))
    assert r.status_code == 422
    o = await order(client, "ord_a_1001")
    assert o["status"] == "pending" and o["payment"] is None
    raw = await db["orders"].find_one({"_id": "ord_a_1001"})
    assert raw["payment_anomalies"][0]["payment_id"] == "pay_a_7002"
    # gateway retry does not pile up duplicate anomalies
    await post(client, event("pay_a_7002", "ord_a_1001", 19999))
    assert len((await db["orders"].find_one({"_id": "ord_a_1001"}))["payment_anomalies"]) == 1


async def test_discounted_amount_is_accepted(client):
    await client.post("/orders/ord_a_1001/apply-discount", json={"code": "PARTNER15"})
    r = await post(client, event("pay_ok", "ord_a_1001", 19999 - 2999))
    assert r.status_code == 200
    assert (await order(client, "ord_a_1001"))["status"] == "paid"


async def test_different_payment_on_paid_order_is_flagged_not_overwritten(client, db):
    await post(client, event("pay_first"))
    r = await post(client, event("pay_second"))
    assert r.status_code == 200 and r.json() == {"status": "already_paid_other_payment"}
    assert (await order(client, "ord_a_1003"))["payment"]["payment_id"] == "pay_first"
    raw = await db["orders"].find_one({"_id": "ord_a_1003"})
    assert raw["payment_anomalies"][0]["payment_id"] == "pay_second"


async def test_discount_cannot_be_applied_after_payment(client):
    await post(client, event("pay_1", "ord_a_1001", 19999))
    r = await client.post("/orders/ord_a_1001/apply-discount", json={"code": "PARTNER15"})
    assert r.status_code == 409
    assert (await order(client, "ord_a_1001"))["total_paise"] == 19999
