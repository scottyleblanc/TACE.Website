"""Bond staleness (review finding R8) — business days, not calendar days."""

from datetime import date

import pytest

import indicators


@pytest.mark.parametrize("last,today,stale", [
    ("2026-11-06", date(2026, 11, 9),  False),  # Fri data, Mon morning
    ("2026-11-06", date(2026, 11, 10), False),  # Fri data, Tue (Mon missed)
    ("2026-12-24", date(2026, 12, 29), False),  # Christmas/Boxing closure — was a false stale
    ("2026-12-31", date(2027, 1, 4),   False),  # New Year
    ("2026-11-02", date(2026, 11, 9),  True),   # four business days missed
    ("2026-01-07", date(2026, 2, 10),  True),   # benchmark transition gap
    ("2026-11-11", date(2026, 11, 11), False),  # same day
])
def test_is_stale_counts_missed_business_days(last, today, stale):
    assert indicators._is_stale(last, business_days=indicators.BOND_STALE_BUSINESS_DAYS, today=today) is stale
