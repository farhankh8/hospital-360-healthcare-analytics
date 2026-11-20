"""Scheduling system: appointments with seasonal, weekday and hospital-profile effects."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import schema
from .profiles import (
    CANCELLATION_REASONS,
    ReferenceData,
    choose_weighted,
    days_to_date,
    days_to_datetime,
    make_ids,
    sample_by_group,
    sample_event_days,
)

STATUSES = np.array(["Completed", "Cancelled", "No-show", "Scheduled"], dtype=object)
APPOINTMENT_TYPES = ["New", "Follow-up", "Routine", "Urgent"]
BOOKING_CHANNELS = ["Online", "Phone", "Portal", "Walk-in"]


def generate_appointments(seed: int, refs: ReferenceData, patients: pd.DataFrame,
                          n: int = 104_000) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 300)
    patient_ids = patients["patient_id"].to_numpy()

    hospital = choose_weighted(rng, refs.hospital_ids, refs.hospital_weights, n)
    department = sample_by_group(rng, hospital, refs.dept_ids_by_hospital,
                                 refs.dept_probs_by_hospital)
    doctor = sample_by_group(rng, department, refs.doctors_by_dept)

    day = sample_event_days(rng, n)
    lead = np.minimum(rng.geometric(0.09, size=n) - 1, 90).astype(np.int64)
    booking_day = day - lead

    status = np.empty(n, dtype=object)
    for hid in refs.hospital_ids:
        mask = hospital == hid
        ns = refs.no_show[hid]
        cancelled, scheduled = 0.10, 0.05
        probs = [1.0 - ns - cancelled - scheduled, cancelled, ns, scheduled]
        status[mask] = rng.choice(STATUSES, size=int(mask.sum()), p=probs)

    completed = status == "Completed"
    cancelled = status == "Cancelled"

    # Check-in times only exist for completed appointments.
    checkin_minute = rng.integers(450, 990, size=n)
    checkin_dt = days_to_datetime(day, checkin_minute)
    wait_mean = np.array([refs.wait_mean[h] for h in hospital], dtype=float)
    waiting = np.round(rng.gamma(2.2, wait_mean / 2.2, size=n), 1)
    checkin_dt = checkin_dt.where(completed, pd.NaT)
    waiting = np.where(completed, waiting, np.nan)

    cancellation_reason = np.full(n, None, dtype=object)
    if cancelled.any():
        cancellation_reason[cancelled] = rng.choice(
            CANCELLATION_REASONS, size=int(cancelled.sum())
        )

    df = pd.DataFrame({
        "appointment_id": make_ids("APT", n, width=7),
        "patient_id": rng.choice(patient_ids, size=n),
        "hospital_id": hospital,
        "department_id": department,
        "doctor_id": doctor,
        "booking_date": days_to_date(booking_day),
        "appointment_date": days_to_date(day),
        "appointment_type": rng.choice(APPOINTMENT_TYPES, size=n, p=[0.24, 0.34, 0.34, 0.08]),
        "status": status,
        "checkin_datetime": checkin_dt,
        "waiting_minutes": waiting.astype(np.float64),
        "cancellation_reason": cancellation_reason,
        "booking_channel": rng.choice(BOOKING_CHANNELS, size=n, p=[0.40, 0.29, 0.21, 0.10]),
        "lead_days": lead,
        "rescheduled_flag": rng.random(n) < 0.12,
    })
    return df[schema.columns("appointments")]
