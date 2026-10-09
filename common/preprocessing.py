"""Єдина політика: унікальні коректні рядки додатних продажів."""

from typing import Any

import numpy as np
import pandas as pd


def prepare_retail(source: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    frame = source.copy()
    audit: dict[str, Any] = {"before": len(frame), "excluded": {}}
    audit["diagnostics"] = {
        "cancelled": int(
            frame.InvoiceNo.astype(str).str.upper().str.startswith("C").sum()
        ),
        "nonpositive_quantity": int(
            (pd.to_numeric(frame.Quantity, errors="coerce") <= 0).sum()
        ),
        "nonpositive_price": int(
            (pd.to_numeric(frame.UnitPrice, errors="coerce") <= 0).sum()
        ),
        "missing_customers": int(frame.CustomerID.isna().sum()),
        "numeric_description": frame[["Quantity", "UnitPrice"]].describe().to_dict(),
    }
    duplicate = frame.duplicated()
    audit["excluded"]["exact_duplicates"] = int(duplicate.sum())
    frame = frame.loc[~duplicate].copy()
    for name in ("InvoiceNo", "StockCode", "Description", "Country"):
        frame[name] = frame[name].astype("string").str.strip().replace("", pd.NA)
    frame["InvoiceDate"] = pd.to_datetime(
        frame.InvoiceDate, errors="coerce", format="%Y-%m-%d %H:%M:%S"
    )
    for name in ("Quantity", "UnitPrice"):
        frame[name] = pd.to_numeric(frame[name], errors="coerce")
    customers = pd.to_numeric(frame.CustomerID, errors="coerce")
    customers = customers.where(
        np.isfinite(customers) & (customers > 0) & (customers % 1 == 0)
    )
    frame["CustomerID"] = customers.astype("Int64").astype("string")
    rules = [
        (
            "cancelled",
            lambda df: df.InvoiceNo.str.upper().str.startswith("C").fillna(False),
        ),
        (
            "missing_required",
            lambda df: (
                df[
                    [
                        "InvoiceNo",
                        "StockCode",
                        "Description",
                        "Country",
                        "InvoiceDate",
                        "Quantity",
                        "UnitPrice",
                    ]
                ]
                .isna()
                .any(axis=1)
            ),
        ),
        ("invalid_quantity", lambda df: ~np.isfinite(df.Quantity) | (df.Quantity <= 0)),
        ("invalid_price", lambda df: ~np.isfinite(df.UnitPrice) | (df.UnitPrice <= 0)),
    ]
    for reason, predicate in rules:
        mask = predicate(frame)
        audit["excluded"][reason] = int(mask.sum())
        frame = frame.loc[~mask].copy()
    frame["Revenue"] = frame.Quantity * frame.UnitPrice
    invalid = ~np.isfinite(frame.Revenue)
    audit["excluded"]["invalid_revenue"] = int(invalid.sum())
    frame = frame.loc[~invalid].reset_index(drop=True)
    audit.update(
        after=len(frame),
        removed=len(source) - len(frame),
        retained_missing_customers=int(frame.CustomerID.isna().sum()),
        date_min=frame.InvoiceDate.min().isoformat() if len(frame) else None,
        date_max=frame.InvoiceDate.max().isoformat() if len(frame) else None,
    )
    assert sum(audit["excluded"].values()) + audit["after"] == audit["before"]
    return frame, audit
