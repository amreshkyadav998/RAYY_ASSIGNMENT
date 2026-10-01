from datetime import datetime, timezone

import pytest

from app.models import DiscountCode
from app.services.pricing import compute_discount


def make_code(bps=1500, cap=50_000, partner=7000):
    return DiscountCode(
        code="X",
        percent_off_bps=bps,
        cap_paise=cap,
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
        partner_share_bps=partner,
        rayy_share_bps=10_000 - partner,
    )


def test_percentage_rounds_down():
    # 19999 * 15% = 2999.85 paise -> 2999
    assert compute_discount(19999, make_code()).amount_paise == 2999


def test_cap_applies():
    assert compute_discount(19999, make_code(bps=5000, cap=6000)).amount_paise == 6000


def test_never_exceeds_subtotal():
    assert compute_discount(100, make_code(bps=10_000, cap=10_000)).amount_paise == 100


@pytest.mark.parametrize("subtotal", [1, 7, 333, 19999, 49998, 89900])
@pytest.mark.parametrize("partner", [0, 3333, 7000, 10_000])
def test_shares_always_sum_to_discount(subtotal, partner):
    d = compute_discount(subtotal, make_code(partner=partner))
    assert d.partner_share_paise + d.rayy_share_paise == d.amount_paise
    assert d.partner_share_paise >= 0 and d.rayy_share_paise >= 0


def test_share_split_70_30():
    d = compute_discount(19999, make_code())
    assert (d.partner_share_paise, d.rayy_share_paise) == (2099, 900)
