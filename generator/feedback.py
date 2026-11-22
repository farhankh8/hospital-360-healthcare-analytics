"""Patient feedback and quality/safety incidents."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, schema
from .profiles import (
    COMPLAINT_TEXTS,
    ReferenceData,
    days_to_date,
    make_ids,
    sample_event_days,
)

BASE_RATING_PROBS = np.array([0.06, 0.09, 0.18, 0.32, 0.35])
RATING_BOOST = {
    "H01": 0.05, "H02": -0.02, "H03": 0.06, "H04": 0.04, "H05": 0.01,
    "H06": 0.03, "H07": -0.08, "H08": 0.05, "H09": -0.06, "H10": 0.00,
}
MAX_DAY = (config.END_DATE - config.START_DATE).days - 2


def generate_feedback(seed: int, refs: ReferenceData, encounters: pd.DataFrame,
                      n: int = 15_600, n_incidents: int = 4_200) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed + 900)
    pick = rng.integers(0, len(encounters), size=n)
    enc = encounters.iloc[pick]
    enc_day = (pd.to_datetime(enc["arrival_datetime"]).to_numpy().astype("datetime64[D]") -
               np.datetime64(config.START_DATE, "D")).astype(np.int64)

    hospital = enc["hospital_id"].to_numpy()
    rating = np.empty(n, dtype=np.int64)
    for hid in refs.hospital_ids:
        m = hospital == hid
        p = BASE_RATING_PROBS.copy()
        p[4] += RATING_BOOST[hid]
        p[0] = max(0.01, p[0] - RATING_BOOST[hid])
        p = p / p.sum()
        rating[m] = rng.choice([1, 2, 3, 4, 5], size=int(m.sum()), p=p)

    category = rng.choice(
        ["Care", "Facilities", "Staff", "Waiting", "Billing", "Other"],
        size=n, p=[0.32, 0.16, 0.22, 0.14, 0.10, 0.06],
    )
    sentiment = np.where(
        rating >= 4, "Synthetic: Positive",
        np.where(rating == 3, "Synthetic: Neutral", "Synthetic: Negative"),
    )
    complaint = (rating <= 2) | ((rating == 3) & (category == "Waiting") & (rng.random(n) < 0.35))
    complaint_text = np.full(n, None, dtype=object)
    if complaint.any():
        complaint_text[complaint] = rng.choice(
            COMPLAINT_TEXTS, size=int(complaint.sum())
        )
    resolution_status = np.full(n, "N/A", dtype=object)
    if complaint.any():
        resolution_status[complaint] = rng.choice(
            ["Resolved", "Open", "In progress"],
            size=int(complaint.sum()), p=[0.62, 0.18, 0.20],
        )
    resolution_days = np.where(
        complaint & (resolution_status != "Open"),
        np.round(rng.exponential(5.5, size=n) + 1, 1), np.nan,
    )
    feedback_type = rng.choice(["Survey", "Complaint", "Suggestion"], size=n, p=[0.76, 0.15, 0.09])
    nps = np.empty(n, dtype=np.int64)
    for r, low, high in [(1, 0, 2), (2, 3, 5), (3, 6, 7), (4, 8, 9), (5, 9, 10)]:
        m = rating == r
        nps[m] = rng.integers(low, high + 1, size=int(m.sum()))

    feedback = pd.DataFrame({
        "feedback_id": make_ids("FBK", n, width=7),
        "patient_id": enc["patient_id"].to_numpy(),
        "hospital_id": hospital,
        "department_id": enc["department_id"].to_numpy(),
        "visit_date": days_to_date(np.minimum(enc_day, MAX_DAY)),
        "rating": rating,
        "category": category,
        "sentiment_label": sentiment,
        "complaint_flag": complaint,
        "complaint_text": complaint_text,
        "resolution_status": resolution_status,
        "resolution_days": resolution_days.astype(np.float64),
        "feedback_type": feedback_type,
        "nps_score": nps,
    })

    # -- incidents ----------------------------------------------------------
    inc_hosp = rng.choice(refs.hospital_ids, size=n_incidents)
    inc_dept = np.empty(n_incidents, dtype=object)
    for hid in refs.hospital_ids:
        m = inc_hosp == hid
        inc_dept[m] = rng.choice(refs.dept_ids_by_hospital[hid], size=int(m.sum()))
    inc_day = np.minimum(sample_event_days(rng, n_incidents), MAX_DAY)
    inc_cat = rng.choice(["Fall", "Medication", "Infection", "Safety", "Other"],
                         size=n_incidents, p=[0.22, 0.24, 0.20, 0.21, 0.13])
    severity = rng.choice(["Low", "Medium", "High", "Critical"],
                          size=n_incidents, p=[0.32, 0.38, 0.23, 0.07])
    status = rng.choice(["Open", "Investigating", "Resolved", "Closed"],
                        size=n_incidents, p=[0.10, 0.18, 0.32, 0.40])
    complete = (status == "Resolved") | (status == "Closed")
    investigation_days = np.round(rng.gamma(2.0, 3.0, size=n_incidents) + 1, 1)
    investigation_days = np.where(complete, investigation_days, np.nan)
    inc_offset = np.nan_to_num(np.round(investigation_days), nan=0.0).astype(np.int64)
    resolution_day = np.where(
        complete, np.minimum(inc_day + inc_offset, MAX_DAY), -1
    )
    incidents = pd.DataFrame({
        "incident_id": make_ids("INC", n_incidents, width=7),
        "hospital_id": inc_hosp,
        "department_id": inc_dept,
        "incident_date": days_to_date(inc_day),
        "category": inc_cat,
        "severity": severity,
        "status": status,
        "investigation_complete_flag": complete,
        "investigation_days": investigation_days.astype(np.float64),
        "resolution_date": days_to_date(resolution_day).where(resolution_day >= 0, pd.NaT),
    })

    return {
        "feedback": feedback[schema.columns("feedback")],
        "incidents": incidents[schema.columns("incidents")],
    }
