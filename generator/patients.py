"""Deterministic synthetic patient registry."""
from __future__ import annotations

import numpy as np
import pandas as pd
from faker import Faker

from . import config, schema
from .profiles import CITIES, REGIONS, make_faker, make_ids


def generate_patients(seed: int, n: int = 15_200) -> pd.DataFrame:
    """Generate the patient dimension with stable PAT000001-style identifiers."""
    rng = np.random.default_rng(seed + 200)
    fake: Faker = make_faker(seed + 201)

    patient_id = make_ids("PAT", n, width=6)
    first_names = np.array([fake.first_name() for _ in range(n)], dtype=object)
    last_names = np.array([fake.last_name() for _ in range(n)], dtype=object)

    # Age mixture: pediatric share is visible in H04, seniors in general medicine.
    band = rng.choice(4, size=n, p=[0.12, 0.07, 0.51, 0.30])
    age = np.empty(n, dtype=np.int64)
    lo = np.array([0, 18, 30, 65])
    hi = np.array([17, 29, 64, 95])
    for b in range(4):
        mask = band == b
        age[mask] = rng.integers(lo[b], hi[b] + 1, size=int(mask.sum()))
    end = pd.Timestamp(config.END_DATE)
    birth = end + pd.to_timedelta(
        -(np.round(age * 365.25).astype(np.int64) + rng.integers(0, 365, size=n)), unit="D"
    )
    registration = pd.Timestamp(config.START_DATE) + pd.to_timedelta(
        rng.integers(-1095, 1, size=n), unit="D"
    )

    gender = rng.choice(["Male", "Female", "Other"], size=n, p=[0.49, 0.49, 0.02])
    blood = rng.choice(
        ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
        size=n, p=[0.27, 0.03, 0.09, 0.01, 0.03, 0.01, 0.51, 0.05],
    )

    df = pd.DataFrame({
        "patient_id": patient_id,
        "first_name": first_names,
        "last_name": last_names,
        "birth_date": birth,
        "gender": gender,
        "city": rng.choice(CITIES, size=n),
        "state": rng.choice(REGIONS, size=n),
        "registration_date": registration,
        "blood_type": blood,
        "patient_type": rng.choice(["New", "Returning"], size=n, p=[0.32, 0.68]),
    })
    age_years = (pd.Timestamp(config.END_DATE) - pd.to_datetime(df["birth_date"])).dt.days / 365.25
    df["age_group"] = pd.cut(
        age_years,
        bins=[-float("inf"), 17, 34, 49, 64, float("inf")],
        labels=["0-17", "18-34", "35-49", "50-64", "65+"],
    ).astype("string")
    return df[schema.columns("patients")]
