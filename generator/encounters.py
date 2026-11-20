"""Encounters and downstream clinical events (inpatient, beds, procedures, labs, pharmacy)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, schema
from .profiles import (
    ReferenceData,
    choose_weighted,
    days_to_date,
    days_to_datetime,
    make_ids,
    sample_by_group,
    sample_event_days,
)

MAX_DAY = (config.END_DATE - config.START_DATE).days - 2
DISPOSITIONS = np.array(["Discharge", "Admit", "Transfer", "LWBS"], dtype=object)


def _apply(func, arr):
    return func(arr)


def generate_encounters(seed: int, refs: ReferenceData, patients: pd.DataFrame,
                        appointments: pd.DataFrame,
                        n: int = 82_000) -> dict[str, pd.DataFrame]:
    """Generate all clinical/event tables and return them keyed by table name."""
    rng = np.random.default_rng(seed + 400)
    patient_ids = patients["patient_id"].to_numpy()
    out: dict[str, pd.DataFrame] = {}

    # ------------------------------------------------------------------
    # Encounters: 60% linked to a completed appointment, 40% walk-in / ED
    # ------------------------------------------------------------------
    linked_n = int(n * 0.60)
    unlinked_n = n - linked_n
    completed = np.flatnonzero(appointments["status"].to_numpy() == "Completed")
    linked_rows = rng.choice(completed, size=linked_n, replace=False)
    apt = appointments.iloc[linked_rows]

    # Convert calendar dates to offsets from START_DATE.
    start64 = np.datetime64(config.START_DATE, "D")
    day_linked = (pd.to_datetime(apt["appointment_date"]).to_numpy().astype("datetime64[D]") - start64).astype(np.int64)

    day_unlinked = np.minimum(sample_event_days(rng, unlinked_n), MAX_DAY)
    hosp_unlinked = choose_weighted(rng, refs.hospital_ids, refs.hospital_weights, unlinked_n)

    day = np.concatenate([day_linked, day_unlinked])
    hospital = np.concatenate([
        apt["hospital_id"].to_numpy(), hosp_unlinked
    ])
    department = np.concatenate([
        apt["department_id"].to_numpy(),
        sample_by_group(rng, hosp_unlinked, refs.dept_ids_by_hospital,
                        refs.dept_probs_by_hospital),
    ])
    patient_id = np.concatenate([
        apt["patient_id"].to_numpy(),
        rng.choice(patient_ids, size=unlinked_n),
    ])
    appointment_id = np.concatenate([
        apt["appointment_id"].to_numpy(), np.full(unlinked_n, None, dtype=object)
    ])

    encounter_type = np.empty(n, dtype=object)
    encounter_type[:linked_n] = rng.choice(
        ["Outpatient", "Emergency", "Inpatient"], size=linked_n, p=[0.88, 0.10, 0.02]
    )
    for hid in refs.hospital_ids:
        m = np.zeros(n, dtype=bool)
        m[linked_n:] = hosp_unlinked == hid
        p_ed = float(refs.emergency_share[hid])
        encounter_type[m] = rng.choice(
            ["Emergency", "Outpatient", "Inpatient"],
            size=int(np.count_nonzero(m)),
            p=[p_ed, 0.90 - p_ed, 0.10],
        )

    is_ed = encounter_type == "Emergency"
    arrive_min = np.where(
        is_ed, rng.integers(0, 1440, size=n), rng.integers(480, 1020, size=n)
    )
    triage_delta = np.where(is_ed, rng.integers(2, 16, size=n), rng.integers(1, 9, size=n))
    wait_mean = np.array([refs.wait_mean[h] for h in hospital], dtype=float)
    wait_scale = np.where(is_ed, wait_mean * 1.25, wait_mean * 0.8) / 2.0
    wait_delta = np.round(rng.gamma(2.0, wait_scale, size=n), 0).astype(np.int64)
    wait_delta = np.clip(wait_delta, 2, 240)
    treated_mean = np.where(is_ed, 95.0, 45.0)
    treat_delta = np.round(rng.gamma(2.5, treated_mean / 2.5, size=n), 0).astype(np.int64)
    treat_delta = np.clip(treat_delta, 10, 420)

    arrival_dt = days_to_datetime(day, arrive_min)
    triage_dt = arrival_dt + pd.to_timedelta(triage_delta, unit="m")
    provider_dt = triage_dt + pd.to_timedelta(wait_delta, unit="m")
    disposition_dt = provider_dt + pd.to_timedelta(treat_delta, unit="m")

    triage_category = np.empty(n, dtype=object)
    triage_category[is_ed] = rng.choice(
        ["Critical", "Urgent", "Standard", "Non-urgent"],
        size=int(is_ed.sum()), p=[0.07, 0.24, 0.50, 0.19],
    )
    triage_category[~is_ed] = rng.choice(
        ["Critical", "Urgent", "Standard", "Non-urgent"],
        size=int((~is_ed).sum()), p=[0.01, 0.10, 0.58, 0.31],
    )

    disposition = np.empty(n, dtype=object)
    for hid in refs.hospital_ids:
        m = hospital == hid
        admit = 0.27 + (0.06 if hid in ("H03", "H08") else 0.0) + (0.03 if hid == "H09" else 0.0)
        admit = min(admit, 0.40)
        transfer, lwbs = 0.035, 0.02
        p = [1.0 - admit - transfer - lwbs, admit, transfer, lwbs]
        disposition[m] = rng.choice(DISPOSITIONS, size=int(m.sum()), p=p)
    # Emergency encounters are more likely to be admitted or leave without being seen.
    ed_mask = is_ed & (disposition == "Discharge")
    convert_n = int(ed_mask.sum() * 0.20)
    if convert_n:
        convert_idx = rng.choice(np.flatnonzero(ed_mask), size=convert_n, replace=False)
        disposition[convert_idx] = "Admit"

    arrival_mode = np.empty(n, dtype=object)
    arrival_mode[is_ed] = rng.choice(
        ["Walk-in", "Ambulance", "Referral"], size=int(is_ed.sum()), p=[0.55, 0.33, 0.12]
    )
    arrival_mode[~is_ed] = rng.choice(
        ["Walk-in", "Ambulance", "Referral"], size=int((~is_ed).sum()), p=[0.55, 0.08, 0.37]
    )

    encounters = pd.DataFrame({
        "encounter_id": make_ids("ENC", n, width=7),
        "patient_id": patient_id,
        "appointment_id": appointment_id,
        "hospital_id": hospital,
        "department_id": department,
        "encounter_type": encounter_type,
        "arrival_datetime": arrival_dt,
        "triage_category": triage_category,
        "triage_datetime": triage_dt,
        "provider_datetime": provider_dt,
        "disposition_datetime": disposition_dt,
        "waiting_minutes": (triage_delta + wait_delta).astype(np.float64),
        "treatment_minutes": treat_delta.astype(np.float64),
        "disposition": disposition,
        "arrival_mode": arrival_mode,
        "critical_flag": triage_category == "Critical",
    })
    out["encounters"] = encounters[schema.columns("encounters")]
    enc = out["encounters"]

    # ------------------------------------------------------------------
    # Admissions
    # ------------------------------------------------------------------
    admit_idx = np.flatnonzero(disposition == "Admit")
    na = len(admit_idx)
    a_enc_id = enc["encounter_id"].to_numpy()[admit_idx]
    a_patient = patient_id[admit_idx]
    a_hosp = hospital[admit_idx]
    a_dept = department[admit_idx]
    a_arrival = arrival_dt[admit_idx]
    a_disposition = disposition_dt[admit_idx]

    admit_dt = a_disposition + pd.to_timedelta(rng.integers(5, 240, size=na), unit="m")
    los = np.round(rng.gamma(2.0, 2.2, size=na) + 0.6, 2)
    los = np.clip(los, 0.5, 35.0)
    discharged = rng.random(na) < 0.90
    discharge_dt = admit_dt + pd.to_timedelta(np.round(los * 1440).astype(np.int64), unit="m")
    discharge_dt = discharge_dt.where(discharged, pd.NaT)
    los_final = np.where(discharged, los, np.nan)

    bed_ids = sample_by_group(rng, a_hosp, refs.beds_by_hospital)
    wards = np.array([refs.bed_ward[b] for b in bed_ids], dtype=object)
    boarding = np.round((admit_dt - a_arrival).total_seconds() / 3600.0, 2)

    adm_type = np.empty(na, dtype=object)
    for hid in refs.hospital_ids:
        m = a_hosp == hid
        elective = 0.55 if hid in ("H03", "H05", "H08", "H06") else 0.38
        adm_type[m] = rng.choice(["Elective", "Emergency", "Transfer"],
                                 size=int(m.sum()), p=[elective, 0.90 - elective, 0.10])

    admissions = pd.DataFrame({
        "admission_id": make_ids("ADM", na, width=6),
        "encounter_id": a_enc_id,
        "patient_id": a_patient,
        "hospital_id": a_hosp,
        "department_id": a_dept,
        "ward": wards,
        "bed_id": bed_ids,
        "admission_datetime": admit_dt,
        "discharge_datetime": discharge_dt,
        "admission_type": adm_type,
        "discharge_status": rng.choice(
            ["Recovered", "Referred", "Deceased", "Against advice"],
            size=na, p=[0.82, 0.10, 0.03, 0.05],
        ),
        "los_days": los_final.astype(np.float64),
        "readmission_flag": rng.random(na) < 0.08,
        "boarding_hours": boarding,
    })
    out["admissions"] = admissions[schema.columns("admissions")]

    # ------------------------------------------------------------------
    # Ward transfers
    # ------------------------------------------------------------------
    nt = min(3_600, na)
    sel = rng.choice(na, size=nt, replace=False)
    lo = admit_dt[sel] + pd.to_timedelta(30, unit="m")
    fallback = admit_dt[sel] + pd.to_timedelta(72 * 60, unit="m")
    hi = discharge_dt[sel].where(pd.notna(discharge_dt[sel]), fallback)
    span = ((hi - lo).total_seconds() / 60.0).astype(np.int64)
    span = np.maximum(span, 60)
    transfer_dt = lo + pd.to_timedelta((rng.random(nt) * span).astype(np.int64), unit="m")

    to_ward = np.empty(nt, dtype=object)
    wards_by_hospital = {
        hid: np.array(sorted({refs.bed_ward[b] for b in refs.beds_by_hospital[hid]}), dtype=object)
        for hid in refs.hospital_ids
    }
    for hid in refs.hospital_ids:
        m = a_hosp[sel] == hid
        pool = wards_by_hospital[hid]
        for k in np.flatnonzero(m):
            choices_ = pool[pool != wards[sel[k]]]
            to_ward[k] = choices_[rng.integers(len(choices_))]

    transfers = pd.DataFrame({
        "transfer_id": make_ids("TRF", nt, width=6),
        "admission_id": admissions["admission_id"].to_numpy()[sel],
        "patient_id": a_patient[sel],
        "hospital_id": a_hosp[sel],
        "from_ward": wards[sel],
        "to_ward": to_ward,
        "transfer_datetime": transfer_dt,
        "reason": rng.choice(["Clinical", "Capacity", "Specialist"], size=nt, p=[0.55, 0.30, 0.15]),
    })
    out["transfers"] = transfers[schema.columns("transfers")]

    # ------------------------------------------------------------------
    # Bed snapshots
    # ------------------------------------------------------------------
    ns = 102_000
    all_beds = refs.tables["dim_bed"]
    bed_pos = rng.integers(0, len(all_beds), size=ns)
    snap_beds = all_beds["bed_id"].to_numpy()[bed_pos]
    snap_hosp = all_beds["hospital_id"].to_numpy()[bed_pos]
    snap_day = np.minimum(sample_event_days(rng, ns), MAX_DAY)
    snap_min = rng.choice([7 * 60, 13 * 60, 19 * 60], size=ns) + rng.integers(0, 60, size=ns)
    snap_dt = days_to_datetime(snap_day, snap_min)

    status = np.empty(ns, dtype=object)
    blocked_prob = 0.035
    for hid in refs.hospital_ids:
        m = snap_hosp == hid
        p_occ = refs.occupancy[hid]
        status[m] = rng.choice(
            ["Occupied", "Available", "Blocked"], size=int(m.sum()),
            p=[p_occ, 1 - p_occ - blocked_prob, blocked_prob],
        )
    bed_snapshots = pd.DataFrame({
        "snapshot_id": make_ids("SNP", ns, width=7),
        "snapshot_datetime": snap_dt,
        "hospital_id": snap_hosp,
        "ward": all_beds["ward"].to_numpy()[bed_pos],
        "bed_id": snap_beds,
        "bed_type": all_beds["bed_type"].to_numpy()[bed_pos],
        "status": status,
        "occupied_flag": status == "Occupied",
        "blocked_flag": status == "Blocked",
    })
    out["bed_snapshots"] = bed_snapshots[schema.columns("bed_snapshots")]

    # ------------------------------------------------------------------
    # Procedures
    # ------------------------------------------------------------------
    np_ = 31_000
    proc_enc = rng.choice(n, size=np_, replace=False)
    p_hosp = hospital[proc_enc]
    p_dept = department[proc_enc]
    p_patient = patient_id[proc_enc]
    p_arrival = arrival_dt[proc_enc]
    sched_start = p_arrival + pd.to_timedelta(rng.integers(60, 5760, size=np_), unit="m")
    proc_status = rng.choice(["Completed", "Delayed", "Cancelled"], size=np_, p=[0.87, 0.08, 0.05])
    delay = np.where(
        proc_status == "Delayed", rng.integers(10, 91, size=np_),
        np.where(rng.random(np_) < 0.22, rng.integers(1, 31, size=np_), 0),
    ).astype(np.int64)
    duration = np.clip(np.round(rng.gamma(3.0, 28.0, size=np_)), 15, 300).astype(np.int64)
    actual_start = sched_start + pd.to_timedelta(delay, unit="m")
    actual_end = actual_start + pd.to_timedelta(duration, unit="m")
    is_cancelled = proc_status == "Cancelled"
    actual_start = actual_start.where(~is_cancelled, pd.NaT)
    actual_end = actual_end.where(~is_cancelled, pd.NaT)
    duration_final = np.where(is_cancelled, np.nan, duration)

    proc_code = sample_by_group(
        rng, p_dept,
        {d: refs.procedures_catalog.loc[
            refs.procedures_catalog["specialty_id"] == refs.dept_specialty[d], "procedure_code"
        ].to_numpy() if np.any(refs.procedures_catalog["specialty_id"] == refs.dept_specialty[d])
         else refs.procedures_catalog["procedure_code"].to_numpy()
         for d in np.unique(p_dept)},
    )
    revenue_base = rng.uniform(240, 2600, size=np_)
    procedures = pd.DataFrame({
        "procedure_id": make_ids("PRC", np_, width=7),
        "patient_id": p_patient,
        "encounter_id": enc["encounter_id"].to_numpy()[proc_enc],
        "hospital_id": p_hosp,
        "department_id": p_dept,
        "or_room": np.array([f"OR-{h}-{r}" for h, r in zip(
            p_hosp, rng.integers(1, 9, size=np_))], dtype=object),
        "surgeon_id": sample_by_group(rng, p_hosp, refs.doctors_by_hospital),
        "procedure_code": proc_code,
        "scheduled_start": sched_start,
        "actual_start": actual_start,
        "actual_end": actual_end,
        "duration_minutes": duration_final.astype(np.float64),
        "delay_minutes": np.where(is_cancelled, np.nan, delay).astype(np.float64),
        "status": proc_status,
        "cancellation_reason": np.where(is_cancelled, rng.choice(
            ["Patient request", "Surgeon unavailable", "Emergency case", "Equipment issue"], size=np_), None),
        "elective_emergency": np.where(
            (encounter_type[proc_enc] == "Emergency") | (rng.random(np_) < 0.08), "Emergency", "Elective"
        ),
        "revenue": np.round(revenue_base, 2),
    })
    out["procedures"] = procedures[schema.columns("procedures")]

    # ------------------------------------------------------------------
    # Laboratory orders and results
    # ------------------------------------------------------------------
    no = 106_000
    lab_enc = rng.integers(0, n, size=no)
    test_codes = refs.lab_tests["test_code"].to_numpy()
    sla_map = dict(zip(refs.lab_tests["test_code"], refs.lab_tests["sla_minutes"]))
    ordered = arrival_dt[lab_enc] + pd.to_timedelta(rng.integers(0, 181, size=no), unit="m")
    collection = ordered + pd.to_timedelta(rng.integers(2, 31, size=no), unit="m")
    lab_status = rng.choice(["Completed", "Pending", "Cancelled"], size=no, p=[0.86, 0.11, 0.03])
    lab_orders = pd.DataFrame({
        "lab_order_id": make_ids("LBO", no, width=7),
        "patient_id": patient_id[lab_enc],
        "encounter_id": enc["encounter_id"].to_numpy()[lab_enc],
        "hospital_id": hospital[lab_enc],
        "ordering_department": department[lab_enc],
        "test_code": rng.choice(test_codes, size=no),
        "priority": rng.choice(["Routine", "Urgent", "STAT"], size=no, p=[0.70, 0.22, 0.08]),
        "ordered_at": ordered,
        "collection_at": collection,
        "status": lab_status,
    })
    out["lab_orders"] = lab_orders[schema.columns("lab_orders")]

    completed_idx = np.flatnonzero(lab_status == "Completed")
    counts = 1 + rng.binomial(1, 0.72, size=len(completed_idx))
    order_idx = np.repeat(completed_idx, counts)
    nr = len(order_idx)
    sample_codes = lab_orders["test_code"].to_numpy()[order_idx]
    sla = np.array([sla_map[c] for c in sample_codes], dtype=float)
    sla_ok = rng.random(nr) < 0.85
    tat = np.where(
        sla_ok, sla * rng.uniform(0.25, 0.95, size=nr), sla * rng.uniform(1.05, 2.20, size=nr)
    )
    # Second result on the same order arrives later.
    first = np.concatenate([[True], order_idx[1:] != order_idx[:-1]])
    tat = tat + np.where(first, 0, rng.integers(20, 91, size=nr))
    tat = np.round(tat, 1)
    result_dt = lab_orders["collection_at"].to_numpy()[order_idx] + pd.to_timedelta(
        np.round(tat).astype(np.int64), unit="m"
    )
    result_status = np.where(rng.random(nr) < 0.99, "Final", "Pending")
    result_dt = result_dt.where(result_status == "Final", pd.NaT)
    lab_results = pd.DataFrame({
        "result_id": make_ids("LBR", nr, width=7),
        "lab_order_id": lab_orders["lab_order_id"].to_numpy()[order_idx],
        "patient_id": lab_orders["patient_id"].to_numpy()[order_idx],
        "test_code": sample_codes,
        "result_at": result_dt,
        "result_value": np.round(rng.normal(100, 30, size=nr), 1).clip(1, 350),
        "result_flag": rng.choice(["Normal", "High", "Low"], size=nr, p=[0.78, 0.14, 0.08]),
        "is_critical": rng.random(nr) < 0.03,
        "tat_minutes": np.where(result_status == "Final", tat, np.nan),
        "status": result_status,
    })
    out["lab_results"] = lab_results[schema.columns("lab_results")]

    # ------------------------------------------------------------------
    # Prescriptions and dispensing
    # ------------------------------------------------------------------
    nrx = 53_000
    rx_enc = rng.integers(0, n, size=nrx)
    meds = refs.medications
    med_pos = rng.integers(0, len(meds), size=nrx)
    med_codes = meds["medication_code"].to_numpy()[med_pos]
    unit_cost = meds["unit_cost"].to_numpy()[med_pos]
    qty = rng.integers(10, 91, size=nrx)
    rx_day = np.minimum(day[rx_enc] + rng.integers(0, 3, size=nrx), MAX_DAY)
    rx_status = rng.choice(["Dispensed", "Pending", "Cancelled"], size=nrx, p=[0.88, 0.08, 0.04])
    prescriptions = pd.DataFrame({
        "prescription_id": make_ids("RX", nrx, width=7),
        "patient_id": patient_id[rx_enc],
        "encounter_id": enc["encounter_id"].to_numpy()[rx_enc],
        "hospital_id": hospital[rx_enc],
        "medication_code": med_codes,
        "quantity": qty,
        "prescribed_date": days_to_date(rx_day),
        "status": rx_status,
        "amount": np.round(unit_cost * qty * rng.uniform(1.10, 1.60, size=nrx), 2),
    })
    out["prescriptions"] = prescriptions[schema.columns("prescriptions")]

    disp_status = np.empty(nrx, dtype=object)
    disp_status[rx_status == "Dispensed"] = rng.choice(
        ["Completed", "Partial"], size=int((rx_status == "Dispensed").sum()), p=[0.94, 0.06]
    )
    disp_status[rx_status != "Dispensed"] = "Pending"
    qty_disp = np.where(
        disp_status == "Completed", qty,
        np.where(disp_status == "Partial", np.round(qty * rng.uniform(0.4, 0.8, size=nrx)).astype(int), 0),
    )
    disp_day = np.where(
        disp_status == "Pending", -9999,
        np.minimum(rx_day + rng.integers(0, 4, size=nrx), MAX_DAY),
    )
    dispense_dt = days_to_date(disp_day).where(disp_day >= 0, pd.NaT)
    dispensing = pd.DataFrame({
        "dispensing_id": make_ids("DSP", nrx, width=7),
        "prescription_id": prescriptions["prescription_id"].to_numpy(),
        "hospital_id": hospital[rx_enc],
        "pharmacy_id": np.array([f"PH-{h}" for h in hospital[rx_enc]], dtype=object),
        "dispensed_date": dispense_dt,
        "quantity_dispensed": qty_disp,
        "status": disp_status,
    })
    out["dispensing"] = dispensing[schema.columns("dispensing")]

    return out


def slice_mask(values: np.ndarray, label) -> np.ndarray:
    """Boolean mask (used for the unlinked-encounter segment)."""
    return values == label
