"""HOSPITAL 360 synthetic data generation entry point.

Run with ``python -m generator.generate`` from the hospital360 directory.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

import pandas as pd

from . import config, schema
from .appointments import generate_appointments
from .claims import generate_claims
from .encounters import generate_encounters
from .feedback import generate_feedback
from .finance import generate_finance
from .inventory import generate_inventory
from .patients import generate_patients
from .profiles import build_reference, hospital_summary
from .quality import inject_dq
from .workforce import generate_workforce

MANIFEST_PATH = config.MANIFEST_DIR / "generator_manifest.json"

# (child table, child column, parent table, parent column, DQ issue to exclude)
FK_CHECKS = [
    ("appointments", "patient_id", "patients", "patient_id", None),
    ("appointments", "hospital_id", "dim_hospital", "hospital_id", None),
    ("appointments", "department_id", "dim_department", "department_id", "unknown_department"),
    ("appointments", "doctor_id", "dim_doctor", "doctor_id", None),
    ("encounters", "patient_id", "patients", "patient_id", None),
    ("encounters", "hospital_id", "dim_hospital", "hospital_id", None),
    ("encounters", "department_id", "dim_department", "department_id", None),
    ("admissions", "encounter_id", "encounters", "encounter_id", None),
    ("admissions", "patient_id", "patients", "patient_id", None),
    ("admissions", "bed_id", "dim_bed", "bed_id", None),
    ("transfers", "admission_id", "admissions", "admission_id", None),
    ("bed_snapshots", "bed_id", "dim_bed", "bed_id", None),
    ("procedures", "encounter_id", "encounters", "encounter_id", None),
    ("procedures", "surgeon_id", "dim_doctor", "doctor_id", None),
    ("procedures", "procedure_code", "dim_procedure", "procedure_code", None),
    ("lab_orders", "encounter_id", "encounters", "encounter_id", None),
    ("lab_orders", "hospital_id", "dim_hospital", "hospital_id", "incorrect_hospital_id"),
    ("lab_orders", "test_code", "dim_lab_test", "test_code", None),
    ("lab_results", "lab_order_id", "lab_orders", "lab_order_id", None),
    ("lab_results", "test_code", "dim_lab_test", "test_code", None),
    ("prescriptions", "encounter_id", "encounters", "encounter_id", None),
    ("prescriptions", "patient_id", "patients", "patient_id", "orphaned_references"),
    ("prescriptions", "medication_code", "dim_medication", "medication_code", None),
    ("dispensing", "prescription_id", "prescriptions", "prescription_id", None),
    ("invoices", "encounter_id", "encounters", "encounter_id", None),
    ("invoices", "patient_id", "patients", "patient_id", None),
    ("invoices", "payer_id", "dim_payer", "payer_id", None),
    ("invoice_lines", "invoice_id", "invoices", "invoice_id", None),
    ("invoice_lines", "service_code", "dim_service", "service_code", None),
    ("payments", "invoice_id", "invoices", "invoice_id", None),
    ("claims", "invoice_id", "invoices", "invoice_id", None),
    ("claims", "payer_id", "dim_payer", "payer_id", "missing_payer"),
    ("claim_lines", "claim_id", "claims", "claim_id", None),
    ("claim_lines", "service_code", "dim_service", "service_code", None),
    ("claim_events", "claim_id", "claims", "claim_id", None),
    ("shifts", "staff_id", "dim_staff", "staff_id", None),
    ("shifts", "hospital_id", "dim_hospital", "hospital_id", None),
    ("shifts", "department_id", "dim_department", "department_id", None),
    ("attendance", "shift_id", "shifts", "shift_id", None),
    ("attendance", "staff_id", "dim_staff", "staff_id", None),
    ("inventory_movements", "item_id", "dim_inventory_item", "item_id", None),
    ("inventory_movements", "supplier_id", "dim_supplier", "supplier_id", None),
    ("inventory_movements", "hospital_id", "dim_hospital", "hospital_id", None),
    ("purchase_orders", "supplier_id", "dim_supplier", "supplier_id", None),
    ("feedback", "patient_id", "patients", "patient_id", None),
    ("incidents", "hospital_id", "dim_hospital", "hospital_id", None),
    ("incidents", "department_id", "dim_department", "department_id", None),
]


def build_dim_patient(patients: pd.DataFrame) -> pd.DataFrame:
    """Build the conformed patient dimension from the clean patient registry."""
    dim = patients.drop_duplicates(subset=["patient_id"], keep="first").copy()
    return dim[schema.columns("dim_patient")]


def write_bronze(tables: dict[str, pd.DataFrame]) -> None:
    """Write one CSV per contract table, with exact column names and order."""
    for table in schema.TABLES:
        df = tables[table]
        expected = schema.columns(table)
        missing = [c for c in expected if c not in df.columns]
        if missing:
            raise ValueError(f"Table {table} is missing columns: {missing}")
        df = df[expected].copy()
        for column, dtype, _ in schema.TABLES[table]:
            if dtype == "date" and pd.api.types.is_datetime64_any_dtype(df[column]):
                df[column] = df[column].dt.date
        folder = config.BRONZE_DIR / table
        folder.mkdir(parents=True, exist_ok=True)
        df.to_csv(folder / f"{table}.csv", index=False, encoding="utf-8", lineterminator="\n")


def _exclusion_mask(tables, table, id_column, dq_by_table, issue):
    if issue is None:
        return None
    ids = set()
    for entry in dq_by_table.get((table, issue), []):
        ids.update(entry["row_identifiers"])
    if not ids:
        return None
    return tables[table][id_column].astype(str).isin(ids).to_numpy()


def validate(tables: dict[str, pd.DataFrame], dq_log: list[dict]) -> dict:
    """Check schema, targets, referential integrity and date ordering."""
    problems: list[str] = []

    for table, cols in schema.TABLES.items():
        if list(tables[table].columns) != [c for c, _, _ in cols]:
            problems.append(f"{table}: column contract mismatch")

    dq_by_table: dict[tuple[str, str], list[dict]] = {}
    for entry in dq_log:
        dq_by_table.setdefault((entry["table"], entry["issue_type"]), []).append(entry)

    dq_id_columns = {
        ("appointments", "unknown_department"): "appointment_id",
        ("appointments", "invalid_status"): "appointment_id",
        ("encounters", "invalid_dates"): "encounter_id",
        ("lab_orders", "incorrect_hospital_id"): "lab_order_id",
        ("claims", "missing_payer"): "claim_id",
        ("prescriptions", "orphaned_references"): "prescription_id",
    }
    for table, col, parent, parent_col, issue in FK_CHECKS:
        mask = _exclusion_mask(tables, table, dq_id_columns.get((table, issue), _id_col(tables, table)),
                               dq_by_table, issue)
        values = tables[table][col]
        if mask is not None:
            values = values[~mask]
        valid = set(tables[parent][parent_col].dropna().astype(str))
        bad = (~values.isna()) & (~values.astype(str).isin(valid))
        count = int(bad.sum())
        if count:
            problems.append(f"{table}.{col}: {count} orphaned references -> {parent}.{parent_col}")

    # Date-ordering checks (skip intentionally corrupted encounter rows).
    apt = tables["appointments"]
    bad = (pd.to_datetime(apt["booking_date"]) > pd.to_datetime(apt["appointment_date"])).sum()
    if bad:
        problems.append(f"appointments: {bad} booking dates after appointment dates")

    enc = tables["encounters"].copy()
    bad_dates = _exclusion_mask(tables, "encounters", "encounter_id", dq_by_table, "invalid_dates")
    parsed = {c: pd.to_datetime(enc[c], errors="coerce") for c in
              ["arrival_datetime", "triage_datetime", "provider_datetime", "disposition_datetime"]}
    valid = parsed["arrival_datetime"].notna()
    if bad_dates is not None:
        valid &= ~bad_dates
    for earlier, later in [("arrival_datetime", "triage_datetime"),
                           ("triage_datetime", "provider_datetime"),
                           ("provider_datetime", "disposition_datetime")]:
        n = int((parsed[earlier][valid] > parsed[later][valid]).sum())
        if n:
            problems.append(f"encounters: {n} rows with {earlier} after {later}")

    adm = tables["admissions"]
    a = pd.to_datetime(adm["admission_datetime"])
    d = pd.to_datetime(adm["discharge_datetime"])
    bad = int((a > d).sum())
    if bad:
        problems.append(f"admissions: {bad} discharge dates before admission")

    lo = tables["lab_orders"]
    bad = int((pd.to_datetime(lo["ordered_at"]) > pd.to_datetime(lo["collection_at"])).sum())
    if bad:
        problems.append(f"lab_orders: {bad} collection times before order times")

    proc = tables["procedures"]
    ss = pd.to_datetime(proc["scheduled_start"])
    ast = pd.to_datetime(proc["actual_start"])
    aend = pd.to_datetime(proc["actual_end"])
    both = ast.notna() & aend.notna()
    n = int(((ss[both] > ast[both]) | (ast[both] > aend[both])).sum())
    if n:
        problems.append(f"procedures: {n} rows with invalid start/end ordering")

    # Domain checks that account for the injected invalid values.
    ap = tables["appointments"]
    invalid_status_ids = set()
    for entry in dq_by_table.get(("appointments", "invalid_status"), []):
        invalid_status_ids.update(entry["row_identifiers"])
    allowed_status = {"Completed", "Cancelled", "No-show", "Scheduled"}
    bad = ap.loc[~ap["appointment_id"].astype(str).isin(invalid_status_ids), "status"]
    n = int((~bad.isin(allowed_status)).sum())
    if n:
        problems.append(f"appointments: {n} unexpected status values")

    pay = tables["payments"]
    injected_pay_ids = set()
    for entry in dq_by_table.get(("payments", "negative_amounts"), []):
        injected_pay_ids.update(entry["row_identifiers"])
    regular = pay.loc[~pay["payment_id"].astype(str).isin(injected_pay_ids)]
    n = int(((regular["payment_type"] == "Payment") & (regular["amount"] < 0)).sum())
    if n:
        problems.append(f"payments: {n} negative regular payments")

    # Reporting-window freshness. Historical demographic attributes are excluded.
    historical_columns = {"birth_date", "registration_date"}
    window_end = pd.Timestamp(config.END_DATE) + pd.Timedelta(days=1)
    for table, cols in schema.DATE_COLUMNS.items():
        frame = tables.get(table)
        if frame is None:
            continue
        for col in cols:
            if col in historical_columns:
                continue
            parsed = pd.to_datetime(frame[col], errors="coerce")
            latest = parsed.max()
            if pd.notna(latest) and latest > window_end:
                problems.append(f"{table}.{col}: date {latest.date()} exceeds reporting window end")

    target_table = {
        "hospitals": "dim_hospital", "departments": "dim_department",
        "doctors": "dim_doctor", "staff": "dim_staff",
    }
    shortfalls = {
        target_name: {"target": target, "actual": len(tables[target_table.get(target_name, target_name)])}
        for target_name, target in config.TARGETS.items()
        if len(tables[target_table.get(target_name, target_name)]) < target
    }
    return {"passed": not problems and not shortfalls,
            "problems": problems, "shortfalls": shortfalls}


def _id_col(tables, table):
    df = tables[table]
    for candidate in ("appointment_id", "encounter_id", "admission_id", "bed_id", "lab_order_id",
                      "prescription_id", "invoice_id", "claim_id", "shift_id", "patient_id",
                      "staff_id", "hospital_id", "department_id"):
        if candidate in df.columns:
            return candidate
    return df.columns[0]


def generate_all(seed: int = config.SEED) -> dict:
    """Generate all bronze tables, write CSVs + manifest and return actual counts."""
    started = datetime.now(timezone.utc)
    refs = build_reference(seed)
    patients = generate_patients(seed)
    dim_patient = build_dim_patient(patients)
    appointments = generate_appointments(seed, refs, patients)
    clinical = generate_encounters(seed, refs, patients, appointments)
    encounters = clinical["encounters"]
    finance = generate_finance(seed, refs, encounters, n_invoices=66_000)
    claims = generate_claims(seed, refs, finance["invoices"], encounters)
    workforce = generate_workforce(seed, refs)
    inventory = generate_inventory(seed, refs)
    feedback = generate_feedback(seed, refs, encounters)

    tables: dict[str, pd.DataFrame] = dict(refs.tables)
    tables.update({
        "dim_patient": dim_patient,
        "patients": patients, "appointments": appointments,
        **clinical, **finance, **claims, **workforce, **inventory, **feedback,
    })

    dq_log = inject_dq(tables, seed)
    validation = validate(tables, dq_log)
    write_bronze(tables)

    counts = {table: len(tables[table]) for table in schema.TABLES}
    manifest = {
        "run_id": f"GEN_{started:%Y%m%d_%H%M%S}_{seed}",
        "generator_version": config.GENERATOR_VERSION,
        "seed": seed,
        "generated_at": started.isoformat().replace("+00:00", "Z"),
        "status": "success" if validation["passed"] else "success_with_dq_or_shortfalls",
        "window": {"start_date": str(config.START_DATE), "end_date": str(config.END_DATE)},
        "targets": config.TARGETS,
        "actual_counts": counts,
        "total_records": int(sum(counts.values())),
        "dq_injections": dq_log,
        "dq_injections_applied": {
            entry["issue_type"]: entry["count"] for entry in dq_log
        },
        "validation": validation,
        "hospital_profiles": hospital_summary(refs),
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return counts


def _print_summary(counts: dict, manifest: dict | None = None) -> None:
    header = f"{'Table':<24} {'Rows':>10} {'Target':>10}  Status"
    print(header)
    print("-" * len(header))
    target_table = {
        "hospitals": "dim_hospital", "departments": "dim_department",
        "doctors": "dim_doctor", "staff": "dim_staff",
    }
    for table, count in counts.items():
        target_name = next((k for k, v in target_table.items() if v == table), table)
        target = config.TARGETS.get(target_name)
        marker = "" if target is None else ("OK" if count >= target else "SHORT")
        print(f"{table:<24} {count:>10,} {(str(target) if target else '-'):>10}  {marker}")
    print("-" * len(header))
    print(f"{'TOTAL':<24} {sum(counts.values()):>10,}")
    if manifest:
        print(f"Manifest: {MANIFEST_PATH}")
        print(f"DQ injections applied: {manifest['dq_injections_applied']}")
        if manifest["validation"]["problems"]:
            for p in manifest["validation"]["problems"]:
                print(f"VALIDATION: {p}")
        if manifest["validation"]["shortfalls"]:
            print(f"SHORTFALLS: {manifest['validation']['shortfalls']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate HOSPITAL 360 synthetic bronze data")
    parser.add_argument("--seed", type=int, default=config.SEED, help="Reproducibility seed")
    args = parser.parse_args()
    counts = generate_all(seed=args.seed)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    _print_summary(counts, manifest)


if __name__ == "__main__":
    main()
