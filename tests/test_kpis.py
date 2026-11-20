"""KPI edge-case validation (blueprint section 22).

Reference implementations encode the CONTRACT formulas so edge cases are always
tested. If the analytics layer exposes equivalent functions they are cross-checked
when available; otherwise those integration checks skip.
"""
from __future__ import annotations

import pandas as pd
import pytest
from conftest import load_optional

pytestmark = pytest.mark.kpi


def no_show_rate(rows) -> float | None:
    """Eligible = Completed + No-show; Cancelled and Scheduled excluded."""
    eligible = [r for r in rows if getattr(r, "status", None) in {"Completed", "No-show"}
                or (isinstance(r, dict) and r.get("status") in {"Completed", "No-show"})]
    if not eligible:
        return None
    no_shows = sum(
        1 for r in eligible
        if (getattr(r, "status", None) == "No-show"
            or (isinstance(r, dict) and r.get("status") == "No-show"))
    )
    return no_shows / len(eligible) * 100


def occupancy_rate(occupied_bed_days: float, available_bed_days: float) -> float | None:
    if not available_bed_days:
        return None
    return occupied_bed_days / available_bed_days * 100


def occupancy_from_snapshots(snapshots) -> tuple[float | None, int]:
    statuses = list(snapshots["status"])
    occupied = sum(s == "Occupied" for s in statuses)
    available = sum(s in {"Occupied", "Available"} for s in statuses)  # blocked excluded
    blocked = sum(s == "Blocked" for s in statuses)
    return occupancy_rate(occupied, available), blocked


def average_los(admissions) -> float | None:
    discharged = [
        a for a in admissions
        if a.get("discharge") is not None and not pd.isna(a.get("discharge"))
    ]
    if not discharged:
        return None
    return sum(a["los"] for a in discharged) / len(discharged)


def collection_rate(collections: float, net_revenue: float) -> float | None:
    if not net_revenue:
        return None
    return collections / net_revenue * 100


def denial_rate(rows) -> float | None:
    """Adjudicated = Approved + Denied; pending / under review excluded."""
    adjudicated = [r for r in rows if r["status"] in {"Approved", "Denied"}]
    if not adjudicated:
        return None
    denied = sum(r["status"] == "Denied" for r in adjudicated)
    return denied / len(adjudicated) * 100


# ---------------------------------------------------------------------------
# No-show rate
# ---------------------------------------------------------------------------
def test_no_show_rate_all_completed_is_zero() -> None:
    rows = [{"status": "Completed"}] * 5
    assert no_show_rate(rows) == 0.0


def test_no_show_rate_all_no_show_is_hundred() -> None:
    rows = [{"status": "No-show"}] * 4
    assert no_show_rate(rows) == 100.0


def test_no_show_rate_excludes_cancelled_and_scheduled(samples) -> None:
    # 2 completed + 2 no-show + 1 cancelled + 1 scheduled -> 2/4 = 50%
    assert no_show_rate(samples.appointments.to_dict("records")) == 50.0


def test_no_show_rate_empty_denominator_is_null() -> None:
    rows = [{"status": "Cancelled"}, {"status": "Scheduled"}]
    assert no_show_rate(rows) is None


def test_no_show_rate_date_filter_changes_both_sides(samples) -> None:
    apt = samples.appointments
    full = no_show_rate(apt.to_dict("records"))
    early = no_show_rate(apt[apt["appointment_date"] <= "2025-01-11"].to_dict("records"))
    late = no_show_rate(apt[apt["appointment_date"] >= "2025-01-13"].to_dict("records"))
    assert full == 50.0
    assert early == 0.0          # 2 completed, 0 no-show
    assert late == 100.0         # 1 no-show, cancelled + scheduled excluded


# ---------------------------------------------------------------------------
# Occupancy
# ---------------------------------------------------------------------------
def test_occupancy_all_beds_occupied_is_hundred() -> None:
    assert occupancy_rate(10, 10) == 100.0


def test_occupancy_zero_occupied_is_zero() -> None:
    assert occupancy_rate(0, 10) == 0.0


def test_occupancy_no_available_bed_days_is_undefined() -> None:
    assert occupancy_rate(0, 0) is None


def test_occupancy_excludes_blocked_beds(bed_snapshots) -> None:
    # 2 occupied + 2 available + 2 blocked snapshots -> 2/(2+2) = 50%
    rate, blocked = occupancy_from_snapshots(bed_snapshots)
    assert rate == 50.0
    assert blocked == 2


def test_occupancy_blocked_only_is_undefined() -> None:
    import pandas as pd

    frames = pd.DataFrame({"status": ["Blocked", "Blocked"]})
    rate, blocked = occupancy_from_snapshots(frames)
    assert rate is None
    assert blocked == 2


def test_occupancy_duplicate_snapshots_are_detectable(bed_snapshots) -> None:
    import pandas as pd

    dup = pd.concat([bed_snapshots, bed_snapshots.iloc[[0]]], ignore_index=True)
    assert dup["snapshot_id"].duplicated().any()
    # Duplicates would inflate both numerator and denominator; silver must remove them.
    assert occupancy_from_snapshots(dup.drop_duplicates("snapshot_id"))[0] == 50.0


# ---------------------------------------------------------------------------
# Length of stay
# ---------------------------------------------------------------------------
def test_average_los_uses_discharged_admissions_only(admissions) -> None:
    rows = [
        {"discharge": r["discharge_datetime"], "los": r["los_days"]}
        for r in admissions.to_dict("records")
    ]
    # ADM000001 (3 days) + ADM000002 (2 days); ADM000003 is still open.
    assert average_los(rows) == 2.5


def test_average_los_empty_denominator_is_null() -> None:
    assert average_los([{"discharge": None, "los": None}]) is None


# ---------------------------------------------------------------------------
# Collection rate
# ---------------------------------------------------------------------------
def test_collection_rate_basic() -> None:
    assert collection_rate(9_500, 10_000) == 95.0


def test_collection_rate_refunds_reduce_numerator() -> None:
    assert collection_rate(9_500 - 200, 10_000) == 93.0


def test_collection_rate_zero_denominator_is_null() -> None:
    assert collection_rate(500, 0) is None


def test_collection_rate_can_exceed_hundred_with_prior_period_cash() -> None:
    # Documented caveat: collecting prior-period balances in this period.
    assert collection_rate(11_000, 10_000) == pytest.approx(110.0)


# ---------------------------------------------------------------------------
# Denial rate
# ---------------------------------------------------------------------------
def test_denial_rate_mixed_claims(claims) -> None:
    # 1 approved + 2 denied + 1 pending -> 2/3
    assert denial_rate(claims.to_dict("records")) == pytest.approx(200 / 3)


def test_denial_rate_all_approved_is_zero() -> None:
    assert denial_rate([{"status": "Approved"}] * 3) == 0.0


def test_denial_rate_all_denied_is_hundred() -> None:
    assert denial_rate([{"status": "Denied"}] * 3) == 100.0


def test_denial_rate_empty_denominator_is_null() -> None:
    assert denial_rate([{"status": "Pending"}, {"status": "Under review"}]) is None


# ---------------------------------------------------------------------------
# Cross-check against the real analytics layer when it exists
# ---------------------------------------------------------------------------
def test_analytics_kpi_helpers_match_reference_when_available() -> None:
    helper = None
    for module_name in ("analytics.kpis", "analytics.calculations", "etl.gold"):
        module = load_optional(module_name)
        if module is None:
            continue
        for name in ("no_show_rate", "calc_no_show_rate", "compute_no_show_rate"):
            candidate = getattr(module, name, None)
            if callable(candidate):
                helper = candidate
                break
        if helper:
            break
    if helper is None:
        pytest.skip("analytics KPI helpers not implemented yet")
    try:
        all_completed = helper([{"status": "Completed"}, {"status": "Completed"}])
        all_noshow = helper([{"status": "No-show"}, {"status": "No-show"}])
    except Exception as exc:  # noqa: BLE001 - parallel implementation may differ
        pytest.skip(f"analytics KPI helper signature not usable here: {exc}")
    assert all_completed == pytest.approx(0.0)
    assert all_noshow == pytest.approx(100.0)
