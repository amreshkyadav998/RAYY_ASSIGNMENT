# NOTES

## Choices
- **Client:** React (`client/web/`). `formatPaise` uses BigInt, so every step is exact integer maths. Negative input is formatted with a leading `-` instead of throwing. Non-integers, NaN, Infinity and unsafe integers throw.
- **Transactions:** not used. Every state change is one conditional `update_one`, so `make test` (mongomock) is enough. I did not run against a real replica set (see "Would not yet trust").
- **Rounding:**
  - The discount is `subtotal * bps // 10000`, rounded down to a paisa, then capped by `cap_paise` (and never above the subtotal).
  - The partner share is `discount * partner_bps // 10000`, rounded down. RAYY's share is the remainder, so the two always sum to the discount exactly.
  - Example: 19999 at 15% is 2999.85, so the discount is 2999 (partner 2099, RAYY 900).
- **Second code on an order:** one code per order, no stacking and no replacing.
  - The same code again is idempotent (200, unchanged).
  - A different code gets 409.
  - The guard is a conditional update (`status=pending AND discount=null`), so two simultaneous codes cannot both win (fixture `apply_4`).
  - Unknown or expired code: 422. Paid order: 409. Unknown order: 404.
- **Webhook** (`POST /webhooks/payment`):
  - The HMAC is verified over the raw bytes with a constant-time compare, before parsing (401 on failure).
  - Marking paid is one conditional update: `pending AND total_paise == amount_paise`. Duplicate or concurrent deliveries are therefore applied once; repeats return 200 `duplicate`.
  - Fixture `webhook_2`: the gateway charged 19999 on an order whose discounted total is 17000. I do not mark it paid. I return 422 and push a note into `payment_anomalies` on the order (once per payment id). Money was taken, so this needs a human or a refund.
  - A different payment id on an already paid order returns 200 and is noted in `payment_anomalies`, without overwriting the first payment.
  - Other event types return 200 `ignored`. A body that fails validation returns 400. An unknown order returns 404, so the gateway keeps retrying.
- A discount cannot be applied after payment. The conditional updates make the discount-vs-payment race safe in either order.

## Settlement (5 lines)
- Per order I store a snapshot in `orders.discount`: `code, amount_paise, percent_off_bps, cap_paise, partner_share_bps, rayy_share_bps, partner_share_paise, rayy_share_paise, applied_at`. The order also stores `partner_id`, `paid_at` and `payment`.
- The shares are computed once, at apply time, so a changed split next month cannot touch orders already discounted.
- The settlement query (`orders_repo.settlement_by_partner`) matches `status=paid AND paid_at in [month_start, month_end) AND discount != null`, then groups by `partner_id` and sums `discount.partner_share_paise` (and RAYY's). It never reads the discount-code table.
- It runs off the index `(status, paid_at, partner_id)`. Month boundaries should be IST midnights, and `paid_at` is the time the webhook was applied.
- Test: `tests/test_settlement.py` mutates the live code's split after payment and checks that the result is unchanged.

## What the AI got wrong that I caught
- It wrote the `formatPaise` test row `123456789000 -> "₹12,34,56,789.00"`. That is 1,234,567,890.00 rupees, so the correct grouping is `₹1,23,45,67,890.00`. The implementation was right and the expectation was wrong. I caught it by running the suite and checking the arithmetic instead of editing the code to match.
- Related: my first concurrency test for "two codes at once" still passed after I deleted the `discount: None` guard. mongomock runs the calls serially, and the service's read-then-check caught it. I added `test_repository_guard_blocks_second_discount_even_if_service_raced` and confirmed it fails when the guard is removed. The `webhook_2` amount guard was checked the same way.

## Would not yet trust in production
- The concurrency tests run on mongomock, which serializes operations. I have not run against the docker replica set (`make test-mongo`), so the atomicity claims rest on Mongo's single-document update semantics, not on a test of real contention.
- The webhook has no timestamp or replay window; the documented payload has none. An old captured, validly signed event is replayable, though the idempotency above limits the damage.
- `payment_anomalies` is only a note on the order. Nothing alerts anyone, and there is no refund flow for the mismatch or double-payment cases.
- Discount codes are read from a JSON file cached for the process (`lru_cache`), so expiry is computed relative to process start. That is the starter's design; production should store codes in a database with absolute expiry.
- There is no auth on `apply-discount`. Failed webhook signatures are not rate-limited or logged.
- A settlement endpoint and month-boundary (IST) handling are not exposed; only the repository query exists.

## Time
Rough breakdown: reading the starter and deciding the design about 25 min, backend about 60 min, tests and mutation checks about 30 min, client about 25 min, notes and prompts about 10 min.
