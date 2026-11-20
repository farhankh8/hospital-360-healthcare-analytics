"""Staff shifts and attendance records."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import schema
from .profiles import ReferenceData, days_to_date, make_ids, sample_event_days


def generate_workforce(seed: int, refs: ReferenceData, n: int = 52_000) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed + 700)
    staff = refs.tables["dim_staff"]
    staff_pos = rng.integers(0, len(staff), size=n)
    staff_ids = staff["staff_id"].to_numpy()[staff_pos]
    hospital = staff["hospital_id"].to_numpy()[staff_pos]
    department = staff["department_id"].to_numpy()[staff_pos]

    shift_day = sample_event_days(rng, n)
    shift_type = rng.choice(["Morning", "Evening", "Night"], size=n, p=[0.50, 0.32, 0.18])
    scheduled = rng.choice([8.0, 10.0, 12.0], size=n, p=[0.62, 0.20, 0.18])
    noise = rng.normal(0, 0.7, size=n)
    overtime = np.round(np.maximum(0.0, rng.exponential(0.6, size=n) + (shift_type == "Night") * 0.3), 2)
    actual = np.maximum(0.0, np.round(scheduled + noise + overtime, 2))

    shifts = pd.DataFrame({
        "shift_id": make_ids("SFT", n, width=7),
        "staff_id": staff_ids,
        "hospital_id": hospital,
        "department_id": department,
        "shift_date": days_to_date(shift_day),
        "shift_type": shift_type,
        "scheduled_hours": scheduled,
        "actual_hours": actual,
        "overtime_hours": np.round(np.maximum(0.0, actual - scheduled), 2),
    })

    att_status = rng.choice(
        ["Present", "Late", "Absent", "Leave"], size=n, p=[0.88, 0.05, 0.05, 0.02]
    )
    hours_worked = np.where(
        att_status == "Present", actual,
        np.where(att_status == "Late", np.maximum(0.0, actual - 0.8), 0.0),
    )
    attendance = pd.DataFrame({
        "attendance_id": make_ids("ATT", n, width=7),
        "shift_id": shifts["shift_id"].to_numpy(),
        "staff_id": staff_ids,
        "attendance_date": days_to_date(shift_day),
        "status": att_status,
        "hours_worked": np.round(hours_worked, 2),
    })

    return {
        "shifts": shifts[schema.columns("shifts")],
        "attendance": attendance[schema.columns("attendance")],
    }
