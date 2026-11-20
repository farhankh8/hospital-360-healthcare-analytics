"""Controlled data-quality injection.

Issues are applied to a small, documented set of bronze rows AFTER clean
generation. Every injection records the table, the row identifiers and the issue
type so the ETL layer can quarantine exactly those records without silently
dropping anything.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def inject_dq(tables: dict[str, pd.DataFrame], seed: int) -> list[dict]:
    """Apply the configured DQ issues and return a detailed audit log."""
    rng = np.random.default_rng(seed + 1000)
    log: list[dict] = []

    def record(issue: str, table: str, id_column: str, ids, description: str) -> None:
        log.append({
            "issue_type": issue,
            "table": table,
            "id_column": id_column,
            "row_identifiers": [str(x) for x in ids],
            "count": len(ids),
            "description": description,
        })

    # 1. Duplicate patient rows (same primary key, copied attributes).
    patients = tables["patients"]
    dup_pos = rng.choice(len(patients), size=config.DQ_INJECTION["duplicate_patients"], replace=False)
    dup_rows = patients.iloc[dup_pos].copy()
    tables["patients"] = pd.concat([patients, dup_rows], ignore_index=True)
    record("duplicate_patients", "patients", "patient_id",
           dup_rows["patient_id"], "Exact duplicate patient rows appended to bronze")

    # 2. Missing payer on claims.
    claims = tables["claims"]
    p = rng.choice(len(claims), size=config.DQ_INJECTION["missing_payer"], replace=False)
    ids = claims["claim_id"].to_numpy()[p]
    claims.loc[p, "payer_id"] = None
    record("missing_payer", "claims", "claim_id", ids, "payer_id set to null")

    # 3. Invalid date strings on encounters.
    encounters = tables["encounters"]
    p = rng.choice(len(encounters), size=config.DQ_INJECTION["invalid_dates"], replace=False)
    ids = encounters["encounter_id"].to_numpy()[p]
    encounters["arrival_datetime"] = encounters["arrival_datetime"].astype(object)
    encounters.loc[p, "arrival_datetime"] = "INVALID_DATE"
    record("invalid_dates", "encounters", "encounter_id", ids,
           "arrival_datetime replaced with an unparseable string")

    # 4. Unknown department on appointments.
    appointments = tables["appointments"]
    p = rng.choice(len(appointments), size=config.DQ_INJECTION["unknown_department"], replace=False)
    ids = appointments["appointment_id"].to_numpy()[p]
    appointments.loc[p, "department_id"] = "D9999"
    record("unknown_department", "appointments", "appointment_id", ids,
           "department_id points to a non-existent department")

    # 5. Invalid status on a disjoint set of appointments.
    free = np.setdiff1d(np.arange(len(appointments)), p, assume_unique=False)
    p = rng.choice(free, size=config.DQ_INJECTION["invalid_status"], replace=False)
    ids = appointments["appointment_id"].to_numpy()[p]
    appointments.loc[p, "status"] = "UNKNOWN_STATUS"
    record("invalid_status", "appointments", "appointment_id", ids,
           "status value outside the allowed domain")

    # 6. Incorrect hospital code on lab orders.
    lab_orders = tables["lab_orders"]
    p = rng.choice(len(lab_orders), size=config.DQ_INJECTION["incorrect_hospital_id"], replace=False)
    ids = lab_orders["lab_order_id"].to_numpy()[p]
    lab_orders.loc[p, "hospital_id"] = "H99"
    record("incorrect_hospital_id", "lab_orders", "lab_order_id", ids,
           "hospital_id points to a non-existent hospital")

    # 7. Negative monetary amounts on otherwise valid payments.
    payments = tables["payments"]
    positive = np.flatnonzero(payments["amount"].to_numpy() > 0)
    p = rng.choice(positive, size=config.DQ_INJECTION["negative_amounts"], replace=False)
    ids = payments["payment_id"].to_numpy()[p]
    payments.loc[p, "amount"] = -np.abs(payments.loc[p, "amount"])
    record("negative_amounts", "payments", "payment_id", ids,
           "amount sign flipped to negative on a regular payment")

    # 8. Orphaned patient references on prescriptions.
    prescriptions = tables["prescriptions"]
    p = rng.choice(len(prescriptions), size=config.DQ_INJECTION["orphaned_references"], replace=False)
    ids = prescriptions["prescription_id"].to_numpy()[p]
    prescriptions.loc[p, "patient_id"] = "PAT999999"
    record("orphaned_references", "prescriptions", "prescription_id", ids,
           "patient_id points to a non-existent patient")

    return log
