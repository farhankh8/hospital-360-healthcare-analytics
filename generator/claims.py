"""Insurance claims, claim lines and the status-event trail."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, schema
from .profiles import DENIAL_REASONS, ReferenceData, days_to_date, make_ids

MAX_DAY = (config.END_DATE - config.START_DATE).days - 2
CLAIM_STATUSES = np.array(
    ["Approved", "Denied", "Pending", "Under review", "Appealed"], dtype=object
)


def _events(claim_ids, claim_day, processing, status, paid, rng):
    """Build (claim_index, day_offset, event_type, resulting_status) tuples."""
    n = len(claim_ids)
    parts: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = []
    idx_all = np.arange(n)

    def add(idx, offsets, event_type, resulting):
        parts.append((
            idx, np.asarray(offsets, dtype=np.int64),
            np.full(len(idx), event_type, dtype=object),
            np.full(len(idx), resulting, dtype=object),
        ))

    # Every claim is submitted and then reviewed.
    add(idx_all, np.zeros(n, dtype=np.int64), "Submitted", "Submitted")
    review_offset = rng.integers(1, 6, size=n)
    add(idx_all, review_offset, "Under review", "Under review")

    approved = status == "Approved"
    denied = status == "Denied"
    pending = status == "Pending"
    under_review = status == "Under review"
    appealed = status == "Appealed"

    if approved.any():
        idx = np.flatnonzero(approved)
        off = np.maximum(processing[idx] + 2, review_offset[idx] + 2)
        add(idx, off, "Approved", "Approved")
        pay_idx = idx[paid[idx] > 0]
        add(pay_idx, off[paid[idx] > 0] + rng.integers(2, 8, size=len(pay_idx)), "Paid", "Paid")

    if denied.any():
        idx = np.flatnonzero(denied)
        off = np.maximum(processing[idx], review_offset[idx] + 1)
        add(idx, off, "Denied", "Denied")

    if appealed.any():
        idx = np.flatnonzero(appealed)
        first_denial = np.maximum(np.maximum(processing[idx] // 2, review_offset[idx] + 1), 4)
        add(idx, first_denial, "Denied", "Denied")
        appeal_off = np.maximum(processing[idx], first_denial + 2)
        add(idx, appeal_off, "Appealed", "Appealed")
        won = rng.random(len(idx)) < 0.55
        won_idx = idx[won]
        add(won_idx, appeal_off[won] + rng.integers(5, 16, size=len(won_idx)),
            "Approved", "Approved")

    # Pending / Under review claims simply stop after the review event.
    assert pending.any() or under_review.any()

    ci = np.concatenate([p[0] for p in parts])
    off = np.concatenate([p[1] for p in parts])
    etype = np.concatenate([p[2] for p in parts])
    resulting = np.concatenate([p[3] for p in parts])
    order = np.lexsort((off, ci))
    ci, off, etype, resulting = ci[order], off[order], etype[order], resulting[order]
    event_day = np.minimum(claim_day[ci] + off, MAX_DAY)
    return ci, event_day, etype, resulting


def generate_claims(seed: int, refs: ReferenceData, invoices: pd.DataFrame,
                    encounters: pd.DataFrame) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed + 600)
    eligible = np.flatnonzero(invoices["payer_id"].to_numpy() != "P06")
    n = min(52_000, len(eligible))
    pick = rng.choice(eligible, size=n, replace=False)
    inv = invoices.iloc[pick]

    enc_types = encounters.set_index("encounter_id")["encounter_type"]
    claim_type = enc_types.reindex(inv["encounter_id"]).fillna("Outpatient").to_numpy()
    claim_type = np.where(claim_type == "Inpatient", "Inpatient",
                          np.where(claim_type == "Emergency", "Emergency", "Outpatient"))

    inv_day = (pd.to_datetime(inv["invoice_date"]).to_numpy().astype("datetime64[D]") -
               np.datetime64(config.START_DATE, "D")).astype(np.int64)
    claim_day = np.minimum(inv_day + rng.integers(0, 8, size=n), MAX_DAY)
    claim_amount = np.round(inv["net_amount"].to_numpy() * rng.uniform(0.92, 1.0, size=n), 2)

    status = rng.choice(CLAIM_STATUSES, size=n, p=[0.55, 0.12, 0.14, 0.10, 0.09])
    approved = status == "Approved"
    denied = status == "Denied"
    appealed = status == "Appealed"
    decided = approved | denied | appealed
    approved_amount = np.zeros(n, dtype=float)
    approved_amount[approved] = np.round(claim_amount[approved] * rng.uniform(0.85, 1.0, size=int(approved.sum())), 2)
    approved_amount[appealed] = np.round(claim_amount[appealed] * rng.uniform(0.70, 0.95, size=int(appealed.sum())), 2)
    approved_amount = np.minimum(approved_amount, claim_amount)

    paid = np.zeros(n, dtype=float)
    pa = approved & (approved_amount > 0)
    paid[pa] = np.round(approved_amount[pa] * rng.uniform(0.90, 1.0, size=int(pa.sum())), 2)
    pp = appealed & (approved_amount > 0)
    paid[pp] = np.round(approved_amount[pp] * rng.uniform(0.80, 0.95, size=int(pp.sum())), 2)
    paid = np.minimum(paid, approved_amount)

    processing = np.zeros(n, dtype=float)
    processing[decided] = np.round(rng.uniform(5, 46, size=int(decided.sum())), 1)
    denial_reason = np.full(n, None, dtype=object)
    if denied.any():
        denial_reason[denied] = rng.choice(DENIAL_REASONS, size=int(denied.sum()))

    claim_ids = make_ids("CLM", n, width=7)
    claims = pd.DataFrame({
        "claim_id": claim_ids,
        "invoice_id": inv["invoice_id"].to_numpy(),
        "patient_id": inv["patient_id"].to_numpy(),
        "hospital_id": inv["hospital_id"].to_numpy(),
        "payer_id": inv["payer_id"].to_numpy(),
        "claim_date": days_to_date(claim_day),
        "claim_amount": claim_amount,
        "approved_amount": approved_amount,
        "paid_amount": paid,
        "status": status,
        "denial_reason": denial_reason,
        "processing_days": processing,
        "claim_type": claim_type,
    })

    # -- claim lines --------------------------------------------------------
    line_counts = rng.choice([1, 2, 3], size=n, p=[0.10, 0.80, 0.10])
    n_lines = int(line_counts.sum())
    line_claim = np.repeat(np.arange(n), line_counts)
    service_codes = rng.choice(refs.services["service_code"].to_numpy(), size=n_lines)
    shares = rng.uniform(0.5, 1.5, size=n_lines)
    totals = np.bincount(line_claim, weights=shares, minlength=n)
    line_amount = np.round(claim_amount[line_claim] * shares / totals[line_claim], 2)
    line_status = np.where(
        denied[line_claim], "Denied",
        np.where(appealed[line_claim], "Pending",
                 np.where(approved[line_claim], "Approved", "Pending")),
    )
    claim_lines = pd.DataFrame({
        "claim_line_id": make_ids("CXL", n_lines, width=7),
        "claim_id": claim_ids[line_claim],
        "service_code": service_codes,
        "line_amount": line_amount,
        "status": line_status,
    })

    # -- event trail --------------------------------------------------------
    ci, event_day, etype, resulting = _events(
        claim_ids, claim_day, processing, status, paid, rng
    )
    claim_events = pd.DataFrame({
        "event_id": make_ids("CVE", len(ci), width=7),
        "claim_id": claim_ids[ci],
        "event_date": days_to_date(event_day),
        "event_type": etype,
        "status": resulting,
    })

    return {
        "claims": claims[schema.columns("claims")],
        "claim_lines": claim_lines[schema.columns("claim_lines")],
        "claim_events": claim_events[schema.columns("claim_events")],
    }
