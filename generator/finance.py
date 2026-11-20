"""Billing: invoices, invoice lines and payments with reconciled amounts."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, schema
from .profiles import (
    ReferenceData,
    choose_weighted,
    days_to_date,
    make_ids,
)

MAX_DAY = (config.END_DATE - config.START_DATE).days - 2


def generate_finance(seed: int, refs: ReferenceData,
                     encounters: pd.DataFrame, n_invoices: int = 62_000) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed + 500)
    enc_idx = rng.choice(len(encounters), size=n_invoices, replace=False)
    enc = encounters.iloc[enc_idx]
    enc_arrival = pd.to_datetime(enc["arrival_datetime"])
    enc_day = (enc_arrival.to_numpy().astype("datetime64[D]") -
               np.datetime64(config.START_DATE, "D")).astype(np.int64)

    payer = choose_weighted(rng, refs.payers_all, refs.payer_probs, n_invoices)
    is_self = payer == "P06"
    is_gov = payer == "P05"
    inv_day = np.minimum(enc_day + rng.integers(0, 4, size=n_invoices), MAX_DAY)
    invoice_date = days_to_date(inv_day)

    # -- invoice lines ------------------------------------------------------
    line_counts = rng.choice([1, 2, 3], size=n_invoices, p=[0.20, 0.50, 0.30])
    n_lines = int(line_counts.sum())
    line_inv_idx = np.repeat(np.arange(n_invoices), line_counts)
    services = refs.services
    service_pos = rng.choice(len(services), size=n_lines, p=refs.service_probs)
    service_codes = services["service_code"].to_numpy()[service_pos]
    categories = services["category"].to_numpy()[service_pos]
    descriptions = services["service_name"].to_numpy()[service_pos]
    unit_prices = services["unit_price"].to_numpy()[service_pos]
    qty = rng.integers(1, 4, size=n_lines)
    line_amount = np.round(qty * unit_prices * rng.uniform(0.90, 1.10, size=n_lines), 2)

    invoice_lines = pd.DataFrame({
        "line_id": make_ids("IL", n_lines, width=8),
        "invoice_id": make_ids("INV", n_invoices, width=7)[line_inv_idx],
        "service_code": service_codes,
        "service_category": categories,
        "description": descriptions,
        "quantity": qty,
        "unit_price": np.round(unit_prices, 2),
        "line_amount": line_amount,
    })

    gross = np.bincount(line_inv_idx, weights=line_amount, minlength=n_invoices)
    gross = np.round(gross, 2)
    discount = np.round(gross * rng.uniform(0.0, 0.15, size=n_invoices), 2)
    net = np.round(gross - discount, 2)

    ratio_mean = np.where(is_self, 0.45, np.where(is_gov, 0.62, 0.74))
    ratio = rng.beta(3.0, 3.0 * (1.0 - ratio_mean) / np.maximum(ratio_mean, 0.01), size=n_invoices)
    ratio = np.clip(ratio, 0.0, 1.0)
    paid = np.round(net * ratio, 2)
    paid = np.minimum(paid, net)
    balance = np.round(net - paid, 2)

    age_days = MAX_DAY - inv_day
    invoice_status = np.where(
        balance <= 0.01, "Paid",
        np.where(paid <= 0.01, np.where(age_days > 45, "Overdue", "Pending"), "Partial"),
    )
    payment_status = np.where(balance <= 0.01, "Settled",
                              np.where(paid <= 0.01, "Unpaid", "Partial"))

    invoice_ids = make_ids("INV", n_invoices, width=7)
    invoices = pd.DataFrame({
        "invoice_id": invoice_ids,
        "encounter_id": enc["encounter_id"].to_numpy(),
        "patient_id": enc["patient_id"].to_numpy(),
        "hospital_id": enc["hospital_id"].to_numpy(),
        "payer_id": payer,
        "invoice_date": invoice_date,
        "gross_amount": gross,
        "discount_amount": discount,
        "net_amount": net,
        "paid_amount": paid,
        "balance_amount": balance,
        "invoice_status": invoice_status,
        "payment_status": payment_status,
    })

    # -- payments (positive collections, split payments and a few refunds) --
    pay_idx = np.flatnonzero(paid > 0.01)
    amounts = paid[pay_idx]
    inv_for_pay = pay_idx
    # ~18% of invoices generate a second instalment.
    split_mask = rng.random(len(pay_idx)) < 0.18
    second_idx = pay_idx[split_mask]
    first_amount = np.where(split_mask, amounts * 0.6, amounts)
    all_inv = np.concatenate([inv_for_pay, second_idx])
    all_amount = np.concatenate([np.round(first_amount, 2), np.round(amounts[split_mask] * 0.4, 2)])

    pay_day = np.minimum(
        inv_day[all_inv] + rng.integers(0, 46, size=len(all_inv)), MAX_DAY
    )
    n_refunds = 900
    refund_inv = rng.integers(0, n_invoices, size=n_refunds)
    all_inv = np.concatenate([all_inv, refund_inv])
    all_amount = np.concatenate([all_amount, -np.round(rng.uniform(15, 240, size=n_refunds), 2)])
    pay_day = np.concatenate([
        pay_day, np.minimum(inv_day[refund_inv] + rng.integers(1, 60, size=n_refunds), MAX_DAY)
    ])
    n_pay = len(all_inv)
    is_refund = all_amount < 0
    payments = pd.DataFrame({
        "payment_id": make_ids("PAY", n_pay, width=7),
        "invoice_id": invoice_ids[all_inv],
        "patient_id": invoices["patient_id"].to_numpy()[all_inv],
        "payment_date": days_to_date(pay_day),
        "amount": np.round(all_amount, 2),
        "method": rng.choice(["Cash", "Card", "Insurance", "Transfer"],
                             size=n_pay, p=[0.12, 0.38, 0.38, 0.12]),
        "payment_type": np.where(is_refund, "Refund", "Payment"),
        "status": rng.choice(["Cleared", "Pending", "Failed"],
                             size=n_pay, p=[0.86, 0.10, 0.04]),
    })

    return {
        "invoices": invoices[schema.columns("invoices")],
        "invoice_lines": invoice_lines[schema.columns("invoice_lines")],
        "payments": payments[schema.columns("payments")],
    }
