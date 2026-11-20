"""Inventory movements and purchase orders."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, schema
from .profiles import ReferenceData, days_to_date, make_ids, sample_event_days

MOVEMENT_TYPES = ["Receipt", "Issue", "Transfer", "Adjustment", "Return", "Waste", "Expiry"]
MOVEMENT_PROBS = [0.25, 0.30, 0.10, 0.08, 0.07, 0.10, 0.10]
MAX_DAY = (config.END_DATE - config.START_DATE).days - 2


def generate_inventory(seed: int, refs: ReferenceData,
                       n_movements: int = 52_000, n_orders: int = 5_200) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed + 800)
    hospitals = rng.choice(refs.hospital_ids, size=n_movements)
    items = refs.inventory_items
    supplier_of_item = dict(zip(items["item_id"], items["supplier_id"]))
    cost_of_item = dict(zip(items["item_id"], items["unit_cost"]))
    item_pos = rng.integers(0, len(items), size=n_movements)
    item_ids = items["item_id"].to_numpy()[item_pos]
    supplier_ids = np.array([supplier_of_item[i] for i in item_ids], dtype=object)
    unit_cost = np.array([cost_of_item[i] for i in item_ids], dtype=float)

    movement_date_day = sample_event_days(rng, n_movements)
    movement_type = rng.choice(MOVEMENT_TYPES, size=n_movements, p=MOVEMENT_PROBS)
    positive = (movement_type == "Receipt") | (movement_type == "Return")
    quantity = np.where(
        positive, rng.integers(1, 120, size=n_movements),
        -rng.integers(1, 60, size=n_movements),
    )
    expiry_day = np.minimum(
        movement_date_day + rng.integers(30, 540, size=n_movements), MAX_DAY
    )
    expiry = days_to_date(expiry_day).where(movement_type == "Receipt", pd.NaT)

    movements = pd.DataFrame({
        "movement_id": make_ids("INVM", n_movements, width=7),
        "hospital_id": hospitals,
        "item_id": item_ids,
        "supplier_id": supplier_ids,
        "movement_date": days_to_date(movement_date_day),
        "movement_type": movement_type,
        "quantity": quantity.astype(np.int64),
        "unit_cost": np.round(unit_cost, 2),
        "expiry_date": expiry,
    })

    # -- purchase orders ----------------------------------------------------
    sup = refs.suppliers
    lead = dict(zip(sup["supplier_id"], sup["lead_days"]))
    reliability = dict(zip(sup["supplier_id"], sup["reliability_score"]))
    po_hospital = rng.choice(refs.hospital_ids, size=n_orders)
    po_supplier_pos = rng.integers(0, len(sup), size=n_orders)
    po_supplier = sup["supplier_id"].to_numpy()[po_supplier_pos]
    lead_days = np.array([lead[s] for s in po_supplier], dtype=np.int64)
    rel = np.array([reliability[s] for s in po_supplier], dtype=float)
    order_day = sample_event_days(rng, n_orders)
    expected_day = np.minimum(order_day + lead_days, MAX_DAY)

    on_time = rng.random(n_orders) < rel
    late = (~on_time) & (rng.random(n_orders) < 0.60)
    cancelled = rng.random(n_orders) < 0.04
    pending = (~on_time) & (~late) & (~cancelled) & (rng.random(n_orders) < 0.30)

    received_day = np.where(
        on_time, order_day + np.maximum(1, np.round(lead_days * rng.uniform(0.7, 1.0, size=n_orders)).astype(int)),
        np.where(late, expected_day + rng.integers(1, 16, size=n_orders), -1),
    )
    received_day = np.where(cancelled | pending, -1, received_day)
    received_day = np.where(received_day >= 0, np.minimum(received_day, MAX_DAY), received_day)
    status = np.where(cancelled, "Cancelled",
                      np.where(pending, "Pending",
                               np.where(late, "Delayed", "Received")))
    po_items = rng.integers(0, len(items), size=n_orders)
    po_qty = rng.integers(20, 400, size=n_orders)
    po_value = np.round(po_qty * items["unit_cost"].to_numpy()[po_items] * rng.uniform(0.85, 1.15, size=n_orders), 2)

    orders = pd.DataFrame({
        "po_id": make_ids("PO", n_orders, width=7),
        "hospital_id": po_hospital,
        "supplier_id": po_supplier,
        "order_date": days_to_date(order_day),
        "expected_date": days_to_date(expected_day),
        "received_date": days_to_date(received_day).where(received_day >= 0, pd.NaT),
        "status": status,
        "total_amount": po_value,
    })

    return {
        "inventory_movements": movements[schema.columns("inventory_movements")],
        "purchase_orders": orders[schema.columns("purchase_orders")],
    }
