"""Pure pricing rules. Integer paise only; no I/O, no floats.

Rounding decisions (documented in NOTES.md):

* The discount is ``subtotal * percent_bps / 10000`` rounded **down** to a whole
  paisa (never over-discount), then capped at the code's ``cap_paise``.
* The partner's share of the discount is rounded **down**; RAYY's share is the
  remainder, so the two shares always add up to the discount exactly.
"""

from dataclasses import dataclass

from app.models import DiscountCode

BPS = 10_000


@dataclass(frozen=True)
class DiscountBreakdown:
    amount_paise: int
    partner_share_paise: int
    rayy_share_paise: int


def compute_discount(subtotal_paise: int, code: DiscountCode) -> DiscountBreakdown:
    raw = subtotal_paise * code.percent_off_bps // BPS
    amount = min(raw, code.cap_paise, subtotal_paise)
    partner = amount * code.partner_share_bps // BPS
    return DiscountBreakdown(amount, partner, amount - partner)
