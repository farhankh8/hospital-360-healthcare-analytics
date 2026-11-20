"""Global configuration for HOSPITAL 360 synthetic data generation.

Single source of truth for paths, seeds, date range and record targets.
All other modules import from here so the dataset is reproducible.
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
BRONZE_DIR = DATA_DIR / "bronze"
SILVER_DIR = DATA_DIR / "silver"
GOLD_DIR = DATA_DIR / "gold"
QUARANTINE_DIR = DATA_DIR / "quarantine"
MANIFEST_DIR = DATA_DIR / "manifests"
DUCKDB_PATH = DATA_DIR / "hospital360.duckdb"
ANALYTICS_DIR = ROOT / "analytics"

for _d in (DATA_DIR, BRONZE_DIR, SILVER_DIR, GOLD_DIR, QUARANTINE_DIR, MANIFEST_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
SEED = int(os.getenv("H360_SEED", "42"))
GENERATOR_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Reporting window: 24 months
# ---------------------------------------------------------------------------
START_DATE = date(2025, 1, 1)
END_DATE = date(2026, 12, 31)

# ---------------------------------------------------------------------------
# Record targets (development targets, not guaranteed facts)
# The manifest reports the ACTUAL achieved counts.
# ---------------------------------------------------------------------------
TARGETS = {
    "hospitals": 10,
    "patients": 15_000,
    "departments": 100,
    "doctors": 500,
    "staff": 2_500,
    "appointments": 100_000,
    "encounters": 80_000,
    "admissions": 20_000,
    "bed_snapshots": 100_000,
    "lab_orders": 100_000,
    "lab_results": 150_000,
    "prescriptions": 50_000,
    "dispensing": 50_000,
    "invoice_lines": 100_000,
    "claims": 50_000,
    "shifts": 50_000,
    "inventory_movements": 50_000,
    "feedback": 15_000,
}

# ---------------------------------------------------------------------------
# Controlled data-quality issues injected into selected bronze records.
# These are intentional and documented in the manifest.
# ---------------------------------------------------------------------------
DQ_INJECTION = {
    "duplicate_patients": 40,
    "missing_payer": 150,
    "invalid_dates": 40,
    "unknown_department": 60,
    "invalid_status": 50,
    "incorrect_hospital_id": 40,
    "negative_amounts": 30,
    "orphaned_references": 40,
}

# ---------------------------------------------------------------------------
# Hospital network (matches the blueprint exactly)
# ---------------------------------------------------------------------------
HOSPITALS = [
    ("H01", "Central Medical Center", "Downtown", "Multispecialty", 700),
    ("H02", "North General Hospital", "Northside", "General medicine", 450),
    ("H03", "Cardiac & Specialty Institute", "Westgate", "Cardiology", 300),
    ("H04", "Children's Hospital", "Riverside", "Pediatrics", 250),
    ("H05", "Orthopedic & Trauma Center", "Eastfield", "Orthopedics", 350),
    ("H06", "Women's Health Center", "Midtown", "Women's health", 250),
    ("H07", "East Community Hospital", "Eastside", "Community care", 200),
    ("H08", "Oncology Institute", "Southbank", "Oncology", 250),
    ("H09", "Emergency & Critical Care Hospital", "Harbor", "Emergency", 300),
    ("H10", "South Medical Campus", "Southfield", "Multispecialty", 400),
]
TOTAL_BEDS = sum(h[4] for h in HOSPITALS)  # 3,450
