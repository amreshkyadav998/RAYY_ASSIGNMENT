"""All database access for the ``orders`` collection."""

from app.db import ORDERS, get_db


def _to_order_dict(doc: dict) -> dict:
    doc = dict(doc)
    doc["order_id"] = doc.pop("_id")
    return doc


async def get(order_id: str) -> dict | None:
    doc = await get_db()[ORDERS].find_one({"_id": order_id})
    return _to_order_dict(doc) if doc else None


async def list_recent(limit: int = 50) -> list[dict]:
    cursor = get_db()[ORDERS].find({}).sort("created_at", -1).limit(limit)
    return [_to_order_dict(doc) async for doc in cursor]


async def apply_discount_if_open(order_id: str, discount: dict, total_paise: int, expected_subtotal: int) -> bool:
    """Attach a discount only if the order is still pending and has none.

    One conditional update, so two concurrent requests cannot both win and a
    payment landing in between cannot be discounted afterwards.
    """
    result = await get_db()[ORDERS].update_one(
        {"_id": order_id, "status": "pending", "discount": None, "subtotal_paise": expected_subtotal},
        {"$set": {"discount": discount, "total_paise": total_paise}},
    )
    return result.modified_count == 1


async def mark_paid_if_matching(order_id: str, amount_paise: int, payment: dict, paid_at) -> bool:
    """Mark paid only if the order is pending and the charged amount equals its total."""
    result = await get_db()[ORDERS].update_one(
        {"_id": order_id, "status": "pending", "total_paise": amount_paise},
        {"$set": {"status": "paid", "paid_at": paid_at, "payment": payment}},
    )
    return result.modified_count == 1


async def record_payment_anomaly(order_id: str, anomaly: dict) -> None:
    """Keep a note of a payment we could not apply, for manual follow-up."""
    await get_db()[ORDERS].update_one({"_id": order_id}, {"$push": {"payment_anomalies": anomaly}})


async def ensure_indexes() -> None:
    # Settlement reads paid orders by month and groups by partner.
    await get_db()[ORDERS].create_index([("status", 1), ("paid_at", 1), ("partner_id", 1)])


async def settlement_by_partner(start, end) -> list[dict]:
    """Per-partner discount liability for orders paid in [start, end).

    Reads only the per-order snapshot (``discount.*_share_paise``), never the
    current discount-code table, so a changed split affects future orders only.
    """
    pipeline = [
        {"$match": {"status": "paid", "paid_at": {"$gte": start, "$lt": end}, "discount": {"$ne": None}}},
        {
            "$group": {
                "_id": "$partner_id",
                "partner_share_paise": {"$sum": "$discount.partner_share_paise"},
                "rayy_share_paise": {"$sum": "$discount.rayy_share_paise"},
                "orders": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    return [
        {
            "partner_id": row["_id"],
            "partner_share_paise": row["partner_share_paise"],
            "rayy_share_paise": row["rayy_share_paise"],
            "orders": row["orders"],
        }
        async for row in get_db()[ORDERS].aggregate(pipeline)
    ]
