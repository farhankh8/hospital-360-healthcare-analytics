"""Hospital profiles, reference catalogs and shared generator helpers.

All catalogs are entirely synthetic. The hospital profiles deliberately differ so
that cross-hospital comparisons in the analytics layer are meaningful (e.g. H03 is
cardiology-heavy, H04 pediatric, H05 orthopedic, H08 oncology, H09 emergency-heavy,
H01 the highest-volume facility).

Every helper in this module is deterministic for a given seed.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from faker import Faker

from . import config, schema

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

BASE = pd.Timestamp(config.START_DATE)
N_DAYS = (config.END_DATE - config.START_DATE).days + 1
DAY_INDEX = np.arange(N_DAYS, dtype=np.int64)


def make_faker(seed: int) -> Faker:
    """Return a Faker instance with a reproducible, instance-local seed."""
    Faker.seed(seed)
    fake = Faker()
    fake.seed_instance(seed)
    return fake


def make_ids(prefix: str, n: int, width: int = 7, start: int = 1) -> np.ndarray:
    """Vectorised ID construction: PAT000001, PAT000002, ..."""
    return np.fromiter(
        (f"{prefix}{i:0{width}d}" for i in range(start, start + n)),
        dtype=object,
        count=n,
    )


def days_to_date(day_offsets: np.ndarray) -> pd.DatetimeIndex:
    """Integer day offsets from START_DATE -> midnight timestamps."""
    return BASE + pd.to_timedelta(np.asarray(day_offsets, dtype=np.int64), unit="D")


def days_to_datetime(day_offsets: np.ndarray, minutes: np.ndarray) -> pd.DatetimeIndex:
    """Integer day offsets + minute-of-day -> timestamps."""
    return (
        BASE
        + pd.to_timedelta(np.asarray(day_offsets, dtype=np.int64), unit="D")
        + pd.to_timedelta(np.asarray(minutes, dtype=np.int64), unit="m")
    )


WINDOW_END = pd.Timestamp(config.END_DATE) + pd.Timedelta(hours=23, minutes=59, seconds=59)


def clip_to_window(values) -> np.ndarray:
    """Clamp event timestamps to the declared reporting window, preserving NaT."""
    arr = np.asarray(values, dtype="datetime64[ns]")
    lower = np.datetime64(config.START_DATE, "ns")
    upper = WINDOW_END.to_datetime64()
    return np.where(np.isnat(arr), arr, np.clip(arr, lower, upper))


# Seasonal (winter higher) and weekday patterns used wherever events are dated.
_SEASONAL = np.array([
    {1: 1.22, 2: 1.18, 3: 1.05, 4: 0.97, 5: 0.95, 6: 0.90,
     7: 0.88, 8: 0.92, 9: 1.00, 10: 1.06, 11: 1.12, 12: 1.25}[m]
    for m in range(1, 13)
])
_WEEKDAY = np.array([1.12, 1.14, 1.12, 1.10, 1.08, 0.86, 0.72])  # Mon .. Sun
_MONTHS = np.asarray(days_to_date(DAY_INDEX).month)
_DOW = np.asarray(days_to_date(DAY_INDEX).dayofweek)
_DAY_P = _SEASONAL[_MONTHS - 1] * _WEEKDAY[_DOW]
_DAY_P = _DAY_P / _DAY_P.sum()


def sample_event_days(rng: np.random.Generator, n: int) -> np.ndarray:
    """Sample day offsets with winter/weekday weighting."""
    return rng.choice(DAY_INDEX, size=n, p=_DAY_P)


def choose_weighted(rng: np.random.Generator, values, probabilities, size: int) -> np.ndarray:
    """Vectorised weighted sampling with replacement."""
    p = np.asarray(probabilities, dtype=float)
    p = p / p.sum()
    return rng.choice(np.asarray(values, dtype=object), size=size, p=p)


def choose_without_replacement(
    rng: np.random.Generator, values, weights, k: int
) -> np.ndarray:
    """Weighted sampling without replacement (Gumbel top-k, O(n log n))."""
    vals = np.asarray(values, dtype=object)
    w = np.asarray(weights, dtype=float)
    w = np.clip(w, 1e-9, None)
    scores = np.log(w) + rng.gumbel(size=len(w))
    k = min(k, len(vals))
    idx = np.argpartition(scores, -k)[-k:]
    return vals[np.sort(idx)]


def sample_by_group(
    rng: np.random.Generator,
    groups: np.ndarray,
    choices: dict,
    probabilities: dict | None = None,
) -> np.ndarray:
    """Sample a value conditional on a group label (10 groups max here).

    `groups` is an array of group labels; `choices[label]` is the array of eligible
    values. This loops over groups, never over rows.
    """
    out = np.empty(len(groups), dtype=object)
    for group in np.unique(groups):
        mask = groups == group
        pool = np.asarray(choices[group], dtype=object)
        probs = None
        if probabilities is not None and group in probabilities:
            probs = np.asarray(probabilities[group], dtype=float)
            probs = probs / probs.sum()
        out[mask] = rng.choice(pool, size=int(mask.sum()), replace=True, p=probs)
    return out


# ---------------------------------------------------------------------------
# Static catalogs
# ---------------------------------------------------------------------------

SPECIALTIES = [
    ("S01", "Cardiology"), ("S02", "Pediatrics"), ("S03", "Orthopedics"),
    ("S04", "Oncology"), ("S05", "Emergency Medicine"), ("S06", "General Medicine"),
    ("S07", "Surgery"), ("S08", "Neurology"), ("S09", "Obstetrics & Gynecology"),
    ("S10", "Dermatology"), ("S11", "Psychiatry"), ("S12", "Radiology"),
    ("S13", "Anesthesiology"), ("S14", "Endocrinology"), ("S15", "Pulmonology"),
    ("S16", "Gastroenterology"), ("S17", "Nephrology"), ("S18", "Geriatrics"),
]

PAYERS = [
    ("P01", "Private Health Plan Alpha", "Insurance"),
    ("P02", "Private Health Plan Beta", "Insurance"),
    ("P03", "Private Health Plan Gamma", "Insurance"),
    ("P04", "Private Health Plan Delta", "Insurance"),
    ("P05", "Government Health Scheme", "Government"),
    ("P06", "Self-pay", "Self-pay"),
]
PAYER_PROBS = np.array([0.17, 0.13, 0.10, 0.07, 0.33, 0.20])

DIAGNOSES = [
    ("D0010", "Essential hypertension", "Cardiovascular"),
    ("D0011", "Atrial fibrillation", "Cardiovascular"),
    ("D0012", "Acute myocardial infarction", "Cardiovascular"),
    ("D0013", "Heart failure", "Cardiovascular"),
    ("D0014", "Coronary artery disease", "Cardiovascular"),
    ("D0020", "Community-acquired pneumonia", "Respiratory"),
    ("D0021", "Asthma exacerbation", "Respiratory"),
    ("D0022", "COPD", "Respiratory"),
    ("D0023", "Pulmonary embolism", "Respiratory"),
    ("D0030", "Type 2 diabetes mellitus", "Endocrine"),
    ("D0031", "Hypothyroidism", "Endocrine"),
    ("D0032", "Obesity", "Endocrine"),
    ("D0040", "Acute appendicitis", "Gastrointestinal"),
    ("D0041", "Gastroenteritis", "Gastrointestinal"),
    ("D0042", "Peptic ulcer disease", "Gastrointestinal"),
    ("D0043", "Colorectal cancer", "Oncology"),
    ("D0044", "Breast cancer", "Oncology"),
    ("D0045", "Lung cancer", "Oncology"),
    ("D0046", "Lymphoma", "Oncology"),
    ("D0050", "Fever of unknown origin", "General medicine"),
    ("D0051", "Sepsis", "General medicine"),
    ("D0052", "Anemia", "General medicine"),
    ("D0060", "Fracture of femur", "Orthopedic"),
    ("D0061", "Fracture of wrist", "Orthopedic"),
    ("D0062", "Osteoarthritis", "Orthopedic"),
    ("D0063", "Rotator cuff injury", "Orthopedic"),
    ("D0070", "Normal pregnancy", "Maternity"),
    ("D0071", "Pre-eclampsia", "Maternity"),
    ("D0072", "Postpartum care", "Maternity"),
    ("D0080", "Acute bronchiolitis", "Pediatric"),
    ("D0081", "Febrile seizure", "Pediatric"),
    ("D0082", "Childhood asthma", "Pediatric"),
    ("D0083", "Congenital anomaly", "Pediatric"),
    ("D0090", "Ischemic stroke", "Neurology"),
    ("D0091", "Epilepsy", "Neurology"),
    ("D0092", "Migraine", "Neurology"),
    ("D0100", "Renal failure", "Nephrology"),
    ("D0101", "Urinary tract infection", "Nephrology"),
    ("D0110", "Major depressive disorder", "Psychiatry"),
    ("D0111", "Anxiety disorder", "Psychiatry"),
    ("D0120", "Cellulitis", "Dermatology"),
    ("D0121", "Eczema", "Dermatology"),
    ("D0130", "Multiple trauma", "Emergency"),
    ("D0131", "Head injury", "Emergency"),
    ("D0140", "Post-operative care", "Surgery"),
]

PROCEDURES = [
    ("CPT0010", "Coronary angiography", "S01", "Diagnostic"),
    ("CPT0011", "Percutaneous coronary intervention", "S01", "Therapeutic"),
    ("CPT0012", "Pacemaker insertion", "S01", "Surgical"),
    ("CPT0013", "Echocardiography", "S01", "Diagnostic"),
    ("CPT0020", "Appendectomy", "S07", "Surgical"),
    ("CPT0021", "Cholecystectomy", "S07", "Surgical"),
    ("CPT0022", "Hernia repair", "S07", "Surgical"),
    ("CPT0023", "Laparoscopy", "S07", "Surgical"),
    ("CPT0030", "Fracture fixation", "S03", "Surgical"),
    ("CPT0031", "Knee arthroscopy", "S03", "Surgical"),
    ("CPT0032", "Hip replacement", "S03", "Surgical"),
    ("CPT0033", "Shoulder reconstruction", "S03", "Surgical"),
    ("CPT0040", "Tumor resection", "S04", "Surgical"),
    ("CPT0041", "Chemotherapy session", "S04", "Therapeutic"),
    ("CPT0042", "Radiotherapy session", "S04", "Therapeutic"),
    ("CPT0043", "Bone marrow biopsy", "S04", "Diagnostic"),
    ("CPT0050", "Caesarean section", "S09", "Surgical"),
    ("CPT0051", "Hysterectomy", "S09", "Surgical"),
    ("CPT0052", "Fetal ultrasound", "S09", "Diagnostic"),
    ("CPT0060", "Endoscopy", "S16", "Diagnostic"),
    ("CPT0061", "Colonoscopy", "S16", "Diagnostic"),
    ("CPT0062", "Liver biopsy", "S16", "Diagnostic"),
    ("CPT0070", "Craniotomy", "S08", "Surgical"),
    ("CPT0071", "EEG monitoring", "S08", "Diagnostic"),
    ("CPT0080", "Bronchoscopy", "S15", "Diagnostic"),
    ("CPT0081", "Lung biopsy", "S15", "Diagnostic"),
    ("CPT0090", "Dialysis session", "S17", "Therapeutic"),
    ("CPT0091", "Kidney biopsy", "S17", "Diagnostic"),
    ("CPT0100", "Emergency trauma laparotomy", "S05", "Surgical"),
    ("CPT0101", "Wound debridement", "S05", "Surgical"),
    ("CPT0110", "Pediatric appendectomy", "S02", "Surgical"),
    ("CPT0111", "Congenital heart repair", "S02", "Surgical"),
    ("CPT0120", "Cataract surgery", "S10", "Surgical"),
    ("CPT0121", "Skin biopsy", "S10", "Diagnostic"),
    ("CPT0130", "Coronary bypass surgery", "S01", "Surgical"),
    ("CPT0131", "Valve replacement", "S01", "Surgical"),
    ("CPT0140", "PET-CT scan", "S12", "Diagnostic"),
    ("CPT0141", "MRI scan", "S12", "Diagnostic"),
    ("CPT0150", "General anesthesia", "S13", "Support"),
    ("CPT0151", "Regional anesthesia", "S13", "Support"),
    ("CPT0160", "Thyroidectomy", "S14", "Surgical"),
    ("CPT0161", "Adrenalectomy", "S14", "Surgical"),
    ("CPT0170", "Psychological assessment", "S11", "Diagnostic"),
    ("CPT0180", "Geriatric assessment", "S18", "Diagnostic"),
]

MEDICATIONS = [
    ("MED0001", "Amoxicillin", "Antibiotic", 4.20),
    ("MED0002", "Azithromycin", "Antibiotic", 7.80),
    ("MED0003", "Ceftriaxone", "Antibiotic", 12.50),
    ("MED0004", "Vancomycin", "Antibiotic", 21.00),
    ("MED0005", "Metformin", "Antidiabetic", 2.10),
    ("MED0006", "Insulin glargine", "Antidiabetic", 28.00),
    ("MED0007", "Gliclazide", "Antidiabetic", 3.40),
    ("MED0008", "Atorvastatin", "Cardiovascular", 6.70),
    ("MED0009", "Rosuvastatin", "Cardiovascular", 9.30),
    ("MED0010", "Amlodipine", "Cardiovascular", 2.90),
    ("MED0011", "Bisoprolol", "Cardiovascular", 3.60),
    ("MED0012", "Ramipril", "Cardiovascular", 4.10),
    ("MED0013", "Clopidogrel", "Cardiovascular", 8.20),
    ("MED0014", "Apixaban", "Cardiovascular", 42.00),
    ("MED0015", "Furosemide", "Cardiovascular", 2.30),
    ("MED0016", "Digoxin", "Cardiovascular", 3.10),
    ("MED0017", "Paracetamol", "Analgesic", 1.10),
    ("MED0018", "Ibuprofen", "Analgesic", 1.90),
    ("MED0019", "Morphine", "Analgesic", 15.50),
    ("MED0020", "Tramadol", "Analgesic", 5.60),
    ("MED0021", "Omeprazole", "Gastrointestinal", 4.80),
    ("MED0022", "Pantoprazole", "Gastrointestinal", 5.40),
    ("MED0023", "Ondansetron", "Gastrointestinal", 7.20),
    ("MED0024", "Loperamide", "Gastrointestinal", 2.60),
    ("MED0025", "Salbutamol", "Respiratory", 3.30),
    ("MED0026", "Budesonide", "Respiratory", 11.40),
    ("MED0027", "Montelukast", "Respiratory", 8.90),
    ("MED0028", "Tiotropium", "Respiratory", 36.00),
    ("MED0029", "Prednisolone", "Anti-inflammatory", 2.80),
    ("MED0030", "Methotrexate", "Anti-inflammatory", 12.80),
    ("MED0031", "Doxycycline", "Antibiotic", 3.90),
    ("MED0032", "Piperacillin-tazobactam", "Antibiotic", 26.00),
    ("MED0033", "Fluconazole", "Antifungal", 9.60),
    ("MED0034", "Acyclovir", "Antiviral", 11.20),
    ("MED0035", "Oseltamivir", "Antiviral", 18.40),
    ("MED0036", "Levothyroxine", "Endocrine", 2.40),
    ("MED0037", "Carbimazole", "Endocrine", 5.90),
    ("MED0038", "Hydrocortisone", "Endocrine", 4.70),
    ("MED0039", "Sertraline", "Psychiatric", 6.30),
    ("MED0040", "Fluoxetine", "Psychiatric", 5.10),
    ("MED0041", "Olanzapine", "Psychiatric", 14.60),
    ("MED0042", "Lorazepam", "Psychiatric", 4.40),
    ("MED0043", "Carboplatin", "Oncology", 185.00),
    ("MED0044", "Paclitaxel", "Oncology", 142.00),
    ("MED0045", "Trastuzumab", "Oncology", 420.00),
    ("MED0046", "Rituximab", "Oncology", 390.00),
    ("MED0047", "Filgrastim", "Oncology", 96.00),
    ("MED0048", "Meszna", "Oncology", 22.00),
    ("MED0049", "Sodium chloride 0.9%", "Infusion", 1.40),
    ("MED0050", "Glucose 5%", "Infusion", 1.60),
    ("MED0051", "Ringer lactate", "Infusion", 1.80),
    ("MED0052", "Albumin 20%", "Infusion", 62.00),
]

LAB_TESTS = [
    ("LAB0001", "Complete blood count", "Hematology", 60),
    ("LAB0002", "Hemoglobin", "Hematology", 45),
    ("LAB0003", "Platelet count", "Hematology", 45),
    ("LAB0004", "Erythrocyte sedimentation rate", "Hematology", 90),
    ("LAB0005", "Coagulation profile", "Hematology", 120),
    ("LAB0006", "Blood glucose (fasting)", "Chemistry", 45),
    ("LAB0007", "HbA1c", "Chemistry", 180),
    ("LAB0008", "Serum creatinine", "Chemistry", 60),
    ("LAB0009", "Blood urea nitrogen", "Chemistry", 60),
    ("LAB0010", "Electrolyte panel", "Chemistry", 60),
    ("LAB0011", "Serum sodium", "Chemistry", 45),
    ("LAB0012", "Serum potassium", "Chemistry", 45),
    ("LAB0013", "Total cholesterol", "Chemistry", 90),
    ("LAB0014", "Liver function tests", "Chemistry", 120),
    ("LAB0015", "Serum amylase", "Chemistry", 90),
    ("LAB0016", "Troponin I", "Cardiac markers", 45),
    ("LAB0017", "Creatine kinase-MB", "Cardiac markers", 60),
    ("LAB0018", "BNP", "Cardiac markers", 120),
    ("LAB0019", "C-reactive protein", "Immunology", 90),
    ("LAB0020", "Erythrocyte sedimentation (high sensitivity)", "Immunology", 120),
    ("LAB0021", "Thyroid stimulating hormone", "Endocrinology", 180),
    ("LAB0022", "Free T4", "Endocrinology", 180),
    ("LAB0023", "Cortisol", "Endocrinology", 240),
    ("LAB0024", "Urinalysis", "Urinalysis", 45),
    ("LAB0025", "Urine culture", "Microbiology", 720),
    ("LAB0026", "Blood culture", "Microbiology", 900),
    ("LAB0027", "Sputum culture", "Microbiology", 900),
    ("LAB0028", "Wound swab culture", "Microbiology", 720),
    ("LAB0029", "COVID-19 PCR", "Molecular", 240),
    ("LAB0030", "Influenza PCR", "Molecular", 240),
    ("LAB0031", "Hepatitis B surface antigen", "Immunology", 180),
    ("LAB0032", "HIV antibody screening", "Immunology", 180),
    ("LAB0033", "Tumor marker CA-125", "Oncology", 480),
    ("LAB0034", "Prostate specific antigen", "Oncology", 480),
    ("LAB0035", "Carcinoembryonic antigen", "Oncology", 480),
    ("LAB0036", "Arterial blood gas", "Critical care", 30),
    ("LAB0037", "Lactate", "Critical care", 30),
    ("LAB0038", "Lipase", "Chemistry", 90),
]

SERVICES = [
    ("SVC0001", "General consultation", "Consultation", 75.0),
    ("SVC0002", "Specialist consultation", "Consultation", 145.0),
    ("SVC0003", "Follow-up consultation", "Consultation", 65.0),
    ("SVC0004", "Emergency consultation", "Consultation", 190.0),
    ("SVC0005", "Telemedicine consultation", "Consultation", 55.0),
    ("SVC0006", "Pre-admission assessment", "Consultation", 110.0),
    ("SVC0007", "Minor surgical procedure", "Procedures", 320.0),
    ("SVC0008", "Major surgical procedure", "Procedures", 1850.0),
    ("SVC0009", "Orthopedic procedure", "Procedures", 950.0),
    ("SVC0010", "Cardiac catheterization", "Procedures", 2200.0),
    ("SVC0011", "Chemotherapy administration", "Procedures", 1250.0),
    ("SVC0012", "Dialysis session", "Procedures", 480.0),
    ("SVC0013", "Endoscopy", "Procedures", 640.0),
    ("SVC0014", "Caesarean section", "Procedures", 1650.0),
    ("SVC0015", "Wound debridement", "Procedures", 280.0),
    ("SVC0016", "X-ray", "Diagnostics", 120.0),
    ("SVC0017", "CT scan", "Diagnostics", 460.0),
    ("SVC0018", "MRI scan", "Diagnostics", 780.0),
    ("SVC0019", "Ultrasound", "Diagnostics", 210.0),
    ("SVC0020", "ECG", "Diagnostics", 95.0),
    ("SVC0021", "Echocardiography", "Diagnostics", 340.0),
    ("SVC0022", "Pulmonary function test", "Diagnostics", 180.0),
    ("SVC0023", "Laboratory panel - basic", "Diagnostics", 85.0),
    ("SVC0024", "Laboratory panel - extended", "Diagnostics", 240.0),
    ("SVC0025", "Histopathology", "Diagnostics", 390.0),
    ("SVC0026", "Pharmacy - generic medication", "Pharmacy", 45.0),
    ("SVC0027", "Pharmacy - specialty medication", "Pharmacy", 260.0),
    ("SVC0028", "Pharmacy - oncology medication", "Pharmacy", 980.0),
    ("SVC0029", "Pharmacy - IV infusion", "Pharmacy", 135.0),
    ("SVC0030", "Pharmacy - discharge medication", "Pharmacy", 70.0),
    ("SVC0031", "Inpatient bed day - general", "Inpatient services", 420.0),
    ("SVC0032", "Inpatient bed day - ICU", "Inpatient services", 1450.0),
    ("SVC0033", "Inpatient bed day - pediatric", "Inpatient services", 480.0),
    ("SVC0034", "Inpatient bed day - maternity", "Inpatient services", 510.0),
    ("SVC0035", "Nursing care - per shift", "Inpatient services", 190.0),
    ("SVC0036", "Theatre and anesthesia - per hour", "Inpatient services", 620.0),
    ("SVC0037", "Rehabilitation session", "Inpatient services", 130.0),
    ("SVC0038", "Ambulance transport", "Inpatient services", 240.0),
]

SUPPLIERS = [
    ("SUP0001", "Medline Nord Supplies", 7, 0.94),
    ("SUP0002", "CardioDevices Limited", 14, 0.89),
    ("SUP0003", "Global Pharma Distributors", 10, 0.92),
    ("SUP0004", "Surgical Innovations Co", 21, 0.87),
    ("SUP0005", "LabReagents Nordic", 12, 0.95),
    ("SUP0006", "Sterile Products Union", 9, 0.91),
    ("SUP0007", "OrthoImplant Systems", 25, 0.84),
    ("SUP0008", "Oncology Supply Partners", 18, 0.90),
    ("SUP0009", "Pediatric Care Goods", 11, 0.93),
    ("SUP0010", "Hospital Consumables Group", 6, 0.96),
    ("SUP0011", "Diagnostic Equipment Co", 16, 0.88),
    ("SUP0012", "BioMedical Supplies", 13, 0.92),
    ("SUP0013", "PharmaCore Wholesale", 8, 0.94),
    ("SUP0014", "Protective Gear Industries", 5, 0.97),
    ("SUP0015", "Critical Care Equipment", 20, 0.86),
    ("SUP0016", "Wound Care Specialists", 10, 0.93),
    ("SUP0017", "Imaging Solutions Ltd", 28, 0.83),
    ("SUP0018", "Maternity Supply House", 14, 0.90),
    ("SUP0019", "Rehabilitation Equipment Co", 19, 0.89),
    ("SUP0020", "General Medical Merchants", 7, 0.95),
]

INVENTORY_ITEM_NAMES = [
    ("Surgical gloves", "Surgical"), ("Surgical gowns", "Surgical"),
    ("Surgical masks", "Surgical"), ("Scalpel blades", "Surgical"),
    ("Suture packs", "Surgical"), ("Forceps sterile", "Surgical"),
    ("Surgical drapes", "Surgical"), ("Sterile gauze", "Surgical"),
    ("Cannula 18G", "Clinical"), ("Cannula 22G", "Clinical"),
    ("Syringe 5ml", "Clinical"), ("Syringe 10ml", "Clinical"),
    ("Infusion set", "Clinical"), ("Blood collection tube", "Clinical"),
    ("Temperature probe", "Clinical"), ("Blood pressure cuff", "Clinical"),
    ("Pulse oximeter sensor", "Clinical"), ("Oxygen mask", "Clinical"),
    ("Nasogastric tube", "Clinical"), ("Urinary catheter", "Clinical"),
    ("Wound dressing", "Clinical"), ("Adhesive tape", "Clinical"),
    ("Disposable apron", "Clinical"), ("Sharps container", "Clinical"),
    ("Paracetamol 500mg tablets", "Pharmacy"), ("Amoxicillin 500mg capsules", "Pharmacy"),
    ("Ibuprofen 400mg tablets", "Pharmacy"), ("Insulin vial", "Pharmacy"),
    ("Normal saline 1000ml", "Pharmacy"), ("Ringer lactate 1000ml", "Pharmacy"),
    ("Atorvastatin 20mg tablets", "Pharmacy"), ("Metformin 500mg tablets", "Pharmacy"),
    ("Omeprazole 20mg capsules", "Pharmacy"), ("Salbutamol inhaler", "Pharmacy"),
    ("Furosemide 40mg tablets", "Pharmacy"), ("Tramadol 50mg capsules", "Pharmacy"),
    ("Ceftriaxone 1g vial", "Pharmacy"), ("Vancomycin 500mg vial", "Pharmacy"),
    ("Ondansetron 4mg tablets", "Pharmacy"), ("Prednisolone 5mg tablets", "Pharmacy"),
    ("Levothyroxine 50mcg tablets", "Pharmacy"), ("Amlodipine 5mg tablets", "Pharmacy"),
    ("Clopidogrel 75mg tablets", "Pharmacy"), ("Apixaban 5mg tablets", "Pharmacy"),
    ("Lorazepam 1mg tablets", "Pharmacy"), ("Sertraline 50mg tablets", "Pharmacy"),
    ("Fluconazole 150mg tablets", "Pharmacy"), ("Acyclovir 200mg tablets", "Pharmacy"),
    ("Interpretation kit - CBC", "Consumables"), ("Interpretation kit - chemistry", "Consumables"),
    ("Reagent strip - glucose", "Consumables"), ("Reagent strip - protein", "Consumables"),
    ("Culture plate", "Consumables"), ("PCR reaction mix", "Consumables"),
    ("Specimen container", "Consumables"), ("Laboratory pipette tips", "Consumables"),
    ("Centrifuge tube", "Consumables"), ("Slide glass", "Consumables"),
    ("CT contrast media", "Consumables"), ("MRI contrast media", "Consumables"),
    ("Ultrasound gel", "Consumables"), ("X-ray film", "Consumables"),
    ("ECG electrodes", "Consumables"), ("Electrode gel", "Consumables"),
    ("Surgical sponge", "Consumables"), ("Bone cement", "Consumables"),
    ("Orthopedic screw", "Consumables"), ("Orthopedic plate", "Consumables"),
    ("Prosthetic knee component", "Consumables"), ("Prosthetic hip component", "Consumables"),
    ("Chemotherapy infusion bag", "Consumables"), ("Radiotherapy mask", "Consumables"),
    ("Pediatric feeding tube", "Consumables"), ("Pediatric nebulizer mask", "Consumables"),
    ("Maternity delivery pack", "Consumables"), ("Newborn blanket", "Consumables"),
    ("ICU ventilator circuit", "Consumables"), ("ICU central line kit", "Consumables"),
    ("Critical care filter", "Consumables"), ("Defibrillator pads", "Consumables"),
    ("Wheelchair cushion", "Consumables"), ("Crutch pair", "Consumables"),
    ("Walker frame", "Consumables"), ("Compression stockings", "Consumables"),
    ("Blood bag", "Consumables"), ("Platelet concentrate bag", "Consumables"),
    ("Sterile water 1000ml", "Consumables"), ("Alcohol swabs", "Consumables"),
    ("Hand sanitizer", "Consumables"), ("Disinfectant concentrate", "Consumables"),
    ("Bed linen pack", "Consumables"), ("Patient gown", "Consumables"),
    ("Face shield", "Consumables"), ("N95 respirator", "Consumables"),
    ("Shoe covers", "Consumables"), ("Cap disposable", "Consumables"),
    ("Waste bag clinical", "Consumables"), ("Sharps needle", "Consumables"),
    ("Insulin syringe", "Consumables"), ("Blood glucose strip", "Consumables"),
    ("Urine test strip", "Consumables"), ("Thermometer disposable", "Consumables"),
    ("Nebulizer set", "Consumables"), ("Suction catheter", "Consumables"),
    ("Feeding syringe", "Consumables"), ("Tracheostomy tube", "Consumables"),
    ("Suture needle", "Consumables"), ("Skin stapler", "Consumables"),
    ("Bone wax", "Consumables"), ("Hemostatic dressing", "Consumables"),
    ("Dental kit", "Consumables"), ("Eye irrigation solution", "Consumables"),
    ("Ear drops", "Consumables"), ("Oral care kit", "Consumables"),
    ("Pressure relief mattress", "Consumables"), ("Patient identification band", "Consumables"),
    ("Label printer roll", "Consumables"), ("Barcode scanner battery", "Consumables"),
    ("Computer keyboard", "Consumables"), ("Printer toner cartridge", "Consumables"),
    ("Backup battery pack", "Consumables"), ("Network cable", "Consumables"),
]

CANCELLATION_REASONS = [
    "Patient request", "Scheduling conflict", "Provider unavailable",
    "Facility closure", "Weather", "Insurance issue", "Duplicate booking",
]
DENIAL_REASONS = [
    "Missing documentation", "Procedure not covered", "Authorization absent",
    "Duplicate claim", "Coding error", "Timely filing limit exceeded",
    "Benefit exhausted", "Provider not in network",
]
COMPLAINT_TEXTS = [
    "Long wait time before being seen by the clinical team.",
    "Difficulty reaching the department by phone.",
    "Billing statement was not explained clearly.",
    "Room was not cleaned to the expected standard.",
    "Appointment was rescheduled without adequate notice.",
    "Staff communication about the treatment plan was unclear.",
    "Delay in receiving laboratory results.",
    "Noise on the ward affected rest during the stay.",
]


# ---------------------------------------------------------------------------
# Hospital profiles
# ---------------------------------------------------------------------------

def _boost(**kwargs) -> dict:
    return {str(k): w for k, w in kwargs.items()}


HOSPITAL_PROFILES = {
    "H01": {"volume": 1.70, "departments": 16, "doctors": 98, "staff": 470,
                "occupancy": 0.86, "emergency": 0.14, "no_show": 0.085, "wait": 24,
                "specialty_boost": _boost(S01=1.6, S06=1.5, S07=1.5, S12=1.4)},
    "H02": {"volume": 1.05, "departments": 12, "doctors": 68, "staff": 300,
                "occupancy": 0.78, "emergency": 0.18, "no_show": 0.105, "wait": 30,
                "specialty_boost": _boost(S06=3.0, S15=1.5)},
    "H03": {"volume": 0.95, "departments": 12, "doctors": 72, "staff": 280,
                "occupancy": 0.83, "emergency": 0.10, "no_show": 0.065, "wait": 19,
                "specialty_boost": _boost(S01=9.0, S13=1.8, S17=1.5)},
    "H04": {"volume": 0.80, "departments": 11, "doctors": 62, "staff": 260,
                "occupancy": 0.74, "emergency": 0.16, "no_show": 0.095, "wait": 26,
                "specialty_boost": _boost(S02=9.0, S13=1.6, S01=1.4)},
    "H05": {"volume": 0.90, "departments": 11, "doctors": 66, "staff": 275,
                "occupancy": 0.80, "emergency": 0.22, "no_show": 0.10, "wait": 28,
                "specialty_boost": _boost(S03=9.0, S07=2.2, S05=1.4)},
    "H06": {"volume": 0.75, "departments": 11, "doctors": 58, "staff": 240,
                "occupancy": 0.72, "emergency": 0.09, "no_show": 0.08, "wait": 22,
                "specialty_boost": _boost(S09=7.0, S04=1.5, S14=1.4)},
    "H07": {"volume": 0.65, "departments": 10, "doctors": 50, "staff": 215,
                "occupancy": 0.68, "emergency": 0.20, "no_show": 0.13, "wait": 36,
                "specialty_boost": _boost(S06=3.2, S18=2.5, S05=1.5)},
    "H08": {"volume": 0.80, "departments": 11, "doctors": 64, "staff": 265,
                "occupancy": 0.81, "emergency": 0.08, "no_show": 0.07, "wait": 21,
                "specialty_boost": _boost(S04=9.5, S12=2.0, S07=1.4)},
    "H09": {"volume": 1.00, "departments": 12, "doctors": 70, "staff": 320,
                "occupancy": 0.84, "emergency": 0.68, "no_show": 0.12, "wait": 42,
                "specialty_boost": _boost(S05=10.0, S13=2.0, S15=1.6, S08=1.4)},
    "H10": {"volume": 1.15, "departments": 14, "doctors": 82, "staff": 355,
                "occupancy": 0.79, "emergency": 0.17, "no_show": 0.10, "wait": 29,
                "specialty_boost": _boost(S06=1.8, S07=1.7, S16=1.5, S03=1.4)},
}

WARD_LAYOUT = {
    "default": (["General Medicine", "ICU", "Surgery", "Observation"],
                [0.55, 0.12, 0.18, 0.15]),
    "H03": (["Cardiology", "ICU", "General Medicine", "Observation"],
            [0.48, 0.14, 0.23, 0.15]),
    "H04": (["Pediatrics", "ICU", "General Medicine", "Observation"],
            [0.60, 0.08, 0.17, 0.15]),
    "H05": (["Orthopedics", "ICU", "Surgery", "Observation"],
            [0.50, 0.10, 0.25, 0.15]),
    "H06": (["Maternity", "ICU", "General Medicine", "Observation"],
            [0.52, 0.08, 0.25, 0.15]),
    "H08": (["Oncology", "ICU", "General Medicine", "Observation"],
            [0.50, 0.14, 0.21, 0.15]),
    "H09": (["Emergency", "ICU", "Observation", "General Medicine"],
            [0.38, 0.16, 0.28, 0.18]),
}

BED_TYPE_BY_WARD = {
    "ICU": "ICU", "Pediatrics": "Pediatric", "Maternity": "Maternity",
    "Observation": "Observation",
}

STAFF_ROLES = [
    ("Nurse", 0.34, 32.0), ("Nurse Assistant", 0.10, 19.0),
    ("Technician", 0.11, 24.0), ("Lab Technician", 0.08, 27.0),
    ("Pharmacist", 0.05, 46.0), ("Radiographer", 0.05, 41.0),
    ("Physiotherapist", 0.04, 38.0), ("Dietitian", 0.03, 36.0),
    ("Social Worker", 0.03, 33.0), ("Administrator", 0.10, 29.0),
    ("Receptionist", 0.04, 18.0), ("Ward Attendant", 0.03, 16.0),
]

CITIES = [
    "Northfield", "Westgate", "Riverside", "Eastfield", "Midtown", "Eastside",
    "Southbank", "Harbor", "Southfield", "Lakeview", "Hillcrest", "Fairview",
    "Greenfield", "Springvale", "Brookdale", "Maplewood", "Oakdale", "Cedar Grove",
    "Pinecrest", "Willowbrook", "Stonebridge", "Silverdale", "Harborview", "Highland",
]
REGIONS = ["North Region", "South Region", "East Region", "West Region", "Central Region"]


@dataclass
class ReferenceData:
    tables: dict[str, pd.DataFrame] = field(default_factory=dict)
    hospital_ids: np.ndarray = None
    hospital_weights: np.ndarray = None
    specialty_ids: np.ndarray = None
    dept_ids: np.ndarray = None
    dept_ids_by_hospital: dict = field(default_factory=dict)
    dept_probs_by_hospital: dict = field(default_factory=dict)
    dept_hospital: dict = field(default_factory=dict)
    dept_specialty: dict = field(default_factory=dict)
    doctors_by_hospital: dict = field(default_factory=dict)
    doctors_by_dept: dict = field(default_factory=dict)
    staff_by_hospital: dict = field(default_factory=dict)
    beds_by_hospital: dict = field(default_factory=dict)
    bed_ward: dict = field(default_factory=dict)
    bed_type: dict = field(default_factory=dict)
    payers_all: np.ndarray = None
    payers_insurance: np.ndarray = None
    payer_probs: np.ndarray = None
    services: pd.DataFrame = None
    service_probs: np.ndarray = None
    lab_tests: pd.DataFrame = None
    medications: pd.DataFrame = None
    inventory_items: pd.DataFrame = None
    suppliers: pd.DataFrame = None
    procedures_catalog: pd.DataFrame = None
    diagnosis_catalog: pd.DataFrame = None
    occupancy: dict = field(default_factory=dict)
    no_show: dict = field(default_factory=dict)
    emergency_share: dict = field(default_factory=dict)
    wait_mean: dict = field(default_factory=dict)


def build_reference(seed: int) -> ReferenceData:
    """Create every dimension table and the lookup structures used by fact generators."""
    rng = np.random.default_rng(seed + 101)
    fake = make_faker(seed + 102)
    refs = ReferenceData()

    hospitals = config.HOSPITALS
    hospital_ids = np.array([h[0] for h in hospitals], dtype=object)
    refs.hospital_ids = hospital_ids
    vol = np.array([HOSPITAL_PROFILES[h[0]]["volume"] for h in hospitals], dtype=float)
    refs.hospital_weights = vol / vol.sum()
    for h in hospitals:
        p = HOSPITAL_PROFILES[h[0]]
        refs.occupancy[h[0]] = p["occupancy"]
        refs.no_show[h[0]] = p["no_show"]
        refs.emergency_share[h[0]] = p["emergency"]
        refs.wait_mean[h[0]] = p["wait"]

    # -- dim_hospital -------------------------------------------------------
    lat_lon = {
        "H01": (40.7130, -74.0060), "H02": (40.7820, -73.9650),
        "H03": (40.6900, -74.0450), "H04": (40.7600, -73.9800),
        "H05": (40.7350, -73.8850), "H06": (40.7450, -73.9850),
        "H07": (40.7250, -73.8600), "H08": (40.6800, -74.0100),
        "H09": (40.7050, -74.0350), "H10": (40.6950, -73.8800),
    }
    refs.tables["dim_hospital"] = pd.DataFrame({
        "hospital_id": hospital_ids,
        "hospital_name": [h[1] for h in hospitals],
        "city": [h[2] for h in hospitals],
        "profile": [h[3] for h in hospitals],
        "hospital_type": [
            "Teaching" if h[0] in ("H01", "H03", "H08") else "General" for h in hospitals
        ],
        "beds": np.array([h[4] for h in hospitals], dtype=np.int64),
        "status": "Active",
        "latitude": [lat_lon[h[0]][0] for h in hospitals],
        "longitude": [lat_lon[h[0]][1] for h in hospitals],
    })

    # -- dim_location -------------------------------------------------------
    location_rows = []
    for hid, hospital_name, city, _, _ in hospitals:
        lat, lon = lat_lon[hid]
        location_rows.append((
            f"LOC-{hid}", hid, f"{hospital_name} Main Campus", "Hospital campus",
            f"{100 + len(location_rows)} Synthetic Way", city, "Synthetic Region", lat, lon,
        ))
    location_df = pd.DataFrame(location_rows, columns=[
        "location_id", "hospital_id", "location_name", "location_type",
        "address_line", "city", "state", "latitude", "longitude",
    ])
    refs.tables["dim_location"] = location_df[schema.columns("dim_location")]

    # -- dim_specialty ------------------------------------------------------
    refs.specialty_ids = np.array([s[0] for s in SPECIALTIES], dtype=object)
    refs.tables["dim_specialty"] = pd.DataFrame(SPECIALTIES, columns=["specialty_id", "specialty_name"])
    specialty_names = dict(SPECIALTIES)

    # -- dim_department -----------------------------------------------------
    dept_rows = []
    for hid in hospital_ids:
        p = HOSPITAL_PROFILES[hid]
        weights = np.array([
            p["specialty_boost"].get(sid, 1.0) for sid in refs.specialty_ids
        ], dtype=float)
        chosen = choose_without_replacement(rng, refs.specialty_ids, weights, p["departments"])
        for sid in chosen:
            dept_rows.append((
                f"D{len(dept_rows) + 1:03d}", hid,
                f"{specialty_names[sid]} Department", sid,
            ))
    dept_df = pd.DataFrame(dept_rows, columns=["department_id", "hospital_id", "department_name", "specialty_id"])
    refs.tables["dim_department"] = dept_df
    refs.dept_ids = dept_df["department_id"].to_numpy()
    refs.dept_hospital = dict(zip(dept_df["department_id"], dept_df["hospital_id"]))
    refs.dept_specialty = dict(zip(dept_df["department_id"], dept_df["specialty_id"]))
    for hid in hospital_ids:
        sub = dept_df[dept_df["hospital_id"] == hid]
        refs.dept_ids_by_hospital[hid] = sub["department_id"].to_numpy()
        p = HOSPITAL_PROFILES[hid]
        w = np.array([
            p["specialty_boost"].get(sid, 1.0) for sid in sub["specialty_id"]
        ], dtype=float)
        refs.dept_probs_by_hospital[hid] = w / w.sum()

    # -- dim_doctor ---------------------------------------------------------
    doctor_rows = []
    for hid in hospital_ids:
        p = HOSPITAL_PROFILES[hid]
        depts = refs.dept_ids_by_hospital[hid]
        # Guarantee at least one clinician per department, then distribute the rest.
        assigned = list(depts)
        remaining = p["doctors"] - len(depts)
        if remaining > 0:
            assigned.extend(rng.choice(depts, size=remaining, replace=True,
                                       p=refs.dept_probs_by_hospital[hid]))
        for dept in assigned:
            sid = refs.dept_specialty[dept]
            doctor_rows.append((
                f"DOC{len(doctor_rows) + 1:04d}", hid, dept,
                f"{fake.first_name()} {fake.last_name()}", sid,
                str(rng.choice(["Consultant", "Specialist", "Resident"], p=[0.25, 0.45, 0.30])),
            ))
    doctor_df = pd.DataFrame(doctor_rows, columns=[
        "doctor_id", "hospital_id", "department_id", "doctor_name", "specialty_id", "role"
    ])
    refs.tables["dim_doctor"] = doctor_df
    for hid in hospital_ids:
        sub = doctor_df[doctor_df["hospital_id"] == hid]
        refs.doctors_by_hospital[hid] = sub["doctor_id"].to_numpy()
    for dept, sub in doctor_df.groupby("department_id", sort=False):
        refs.doctors_by_dept[dept] = sub["doctor_id"].to_numpy()

    # -- dim_staff ----------------------------------------------------------
    staff_rows = []
    role_names = [r[0] for r in STAFF_ROLES]
    role_probs = np.array([r[1] for r in STAFF_ROLES], dtype=float)
    role_rates = np.array([r[2] for r in STAFF_ROLES], dtype=float)
    for hid in hospital_ids:
        p = HOSPITAL_PROFILES[hid]
        depts = refs.dept_ids_by_hospital[hid]
        assigned = rng.choice(depts, size=p["staff"], replace=True,
                              p=refs.dept_probs_by_hospital[hid])
        for dept in assigned:
            ri = rng.choice(len(role_names), p=role_probs)
            employment = str(rng.choice(["Full-time", "Part-time", "Contract"], p=[0.70, 0.20, 0.10]))
            status = "Active" if rng.random() < 0.95 else "On leave"
            rate = role_rates[ri] * (0.85 + 0.30 * rng.random()) * (1.08 if employment == "Contract" else 1.0)
            staff_rows.append((
                f"STF{len(staff_rows) + 1:05d}", hid, dept,
                f"{fake.first_name()} {fake.last_name()}", role_names[ri],
                employment, status, round(float(rate), 2),
            ))
    staff_df = pd.DataFrame(staff_rows, columns=[
        "staff_id", "hospital_id", "department_id", "staff_name", "role",
        "employment_type", "status", "hourly_rate"
    ])
    refs.tables["dim_staff"] = staff_df
    for hid in hospital_ids:
        refs.staff_by_hospital[hid] = staff_df.loc[
            staff_df["hospital_id"] == hid, "staff_id"
        ].to_numpy()

    # -- dim_payer ----------------------------------------------------------
    refs.tables["dim_payer"] = pd.DataFrame(PAYERS, columns=["payer_id", "payer_name", "payer_type"])
    refs.payers_all = np.array([p[0] for p in PAYERS], dtype=object)
    refs.payers_insurance = np.array([p[0] for p in PAYERS if p[2] != "Self-pay"], dtype=object)
    refs.payer_probs = PAYER_PROBS

    # -- small catalog dimensions ------------------------------------------
    refs.tables["dim_diagnosis"] = pd.DataFrame(
        DIAGNOSES, columns=["diagnosis_code", "diagnosis_name", "category"]
    )
    refs.diagnosis_catalog = refs.tables["dim_diagnosis"]

    refs.tables["dim_procedure"] = pd.DataFrame(
        PROCEDURES, columns=["procedure_code", "procedure_name", "specialty_id", "category"]
    )
    refs.procedures_catalog = refs.tables["dim_procedure"]

    refs.tables["dim_medication"] = pd.DataFrame(MEDICATIONS, columns=[
        "medication_code", "medication_name", "category", "unit_cost"
    ])
    refs.medications = refs.tables["dim_medication"]

    refs.tables["dim_lab_test"] = pd.DataFrame(LAB_TESTS, columns=[
        "test_code", "test_name", "category", "sla_minutes"
    ])
    refs.lab_tests = refs.tables["dim_lab_test"]

    refs.tables["dim_service"] = pd.DataFrame(SERVICES, columns=[
        "service_code", "service_name", "category", "unit_price"
    ])
    refs.services = refs.tables["dim_service"]
    cat_probs = {"Consultation": 0.28, "Procedures": 0.20, "Diagnostics": 0.24,
                 "Pharmacy": 0.15, "Inpatient services": 0.13}
    service_weights = np.array([cat_probs[c] for c in refs.services["category"]], dtype=float)
    refs.service_probs = service_weights / service_weights.sum()

    refs.tables["dim_supplier"] = pd.DataFrame(SUPPLIERS, columns=[
        "supplier_id", "supplier_name", "lead_days", "reliability_score"
    ])
    refs.suppliers = refs.tables["dim_supplier"]

    # 120 inventory items (>= 100 required).
    item_rows = []
    for i, (name, category) in enumerate(INVENTORY_ITEM_NAMES):
        supplier = SUPPLIERS[i % len(SUPPLIERS)][0]
        unit_cost = round(float(rng.uniform(3, 180) * (2.5 if category == "Surgical" else 1.0)), 2)
        item_rows.append((
            f"ITEM{i + 1:05d}", name, category, unit_cost,
            int(rng.integers(20, 200)), supplier,
        ))
    item_df = pd.DataFrame(item_rows, columns=[
        "item_id", "item_name", "category", "unit_cost", "reorder_level", "supplier_id"
    ])
    refs.tables["dim_inventory_item"] = item_df
    refs.inventory_items = item_df

    # -- dim_bed: exactly one row per licensed bed -------------------------
    bed_rows = []
    for hid, _, _, _, bed_count in hospitals:
        wards, ward_weights = WARD_LAYOUT.get(hid, WARD_LAYOUT["default"])
        assigned = rng.choice(len(wards), size=bed_count, p=np.array(ward_weights) / sum(ward_weights))
        for j, wi in enumerate(assigned):
            ward = wards[wi]
            bed_rows.append((
                f"BED-{hid}-{j + 1:04d}", hid, ward,
                BED_TYPE_BY_WARD.get(ward, "General"),
            ))
    bed_df = pd.DataFrame(bed_rows, columns=["bed_id", "hospital_id", "ward", "bed_type"])
    refs.tables["dim_bed"] = bed_df
    for hid in hospital_ids:
        sub = bed_df[bed_df["hospital_id"] == hid]
        refs.beds_by_hospital[hid] = sub["bed_id"].to_numpy()
    refs.bed_ward = dict(zip(bed_df["bed_id"], bed_df["ward"]))
    refs.bed_type = dict(zip(bed_df["bed_id"], bed_df["bed_type"]))

    # -- dim_date / dim_time ------------------------------------------------
    dates = days_to_date(DAY_INDEX)
    month_names = ["January", "February", "March", "April", "May", "June", "July",
                   "August", "September", "October", "November", "December"]
    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    refs.tables["dim_date"] = pd.DataFrame({
        "date_key": dates.year * 10000 + dates.month * 100 + dates.day,
        "full_date": dates,
        "year": dates.year,
        "quarter": dates.quarter,
        "month": dates.month,
        "month_name": np.array([month_names[m - 1] for m in dates.month], dtype=object),
        "day": dates.day,
        "weekday": dates.dayofweek,
        "weekday_name": np.array([weekday_names[d] for d in dates.dayofweek], dtype=object),
        "is_weekend": dates.dayofweek >= 5,
    })
    minutes = np.arange(1440, dtype=np.int64)
    hours = minutes // 60
    mins = minutes % 60
    buckets = np.where(hours < 12, "Morning", np.where(hours < 17, "Afternoon",
                       np.where(hours < 21, "Evening", "Night")))
    refs.tables["dim_time"] = pd.DataFrame({
        "time_key": hours * 100 + mins,
        "hour": hours,
        "minute": mins,
        "hour_bucket": buckets,
    })

    return refs


def hospital_summary(refs: ReferenceData) -> list[dict]:
    """Compact per-hospital summary stored in the generation manifest."""
    out = []
    for hid in refs.hospital_ids:
        p = HOSPITAL_PROFILES[hid]
        out.append({
            "hospital_id": hid,
            "hospital_name": HOSPITAL_PROFILE_NAMES[hid],
            "profile": config.HOSPITALS[list(refs.hospital_ids).index(hid)][3],
            "licensed_beds": int(config.HOSPITALS[list(refs.hospital_ids).index(hid)][4]),
            "volume_weight": float(p["volume"]),
            "target_occupancy": float(p["occupancy"]),
            "emergency_share": float(p["emergency"]),
            "no_show_rate": float(p["no_show"]),
            "departments": len(refs.dept_ids_by_hospital[hid]),
            "doctors": len(refs.doctors_by_hospital[hid]),
            "staff": len(refs.staff_by_hospital[hid]),
            "beds": len(refs.beds_by_hospital[hid]),
        })
    return out


HOSPITAL_PROFILE_NAMES = {h[0]: h[1] for h in config.HOSPITALS}
