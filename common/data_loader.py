"""Читання вихідного CSV без зміни файлу та аудит його структури."""

from pathlib import Path
from typing import Any

import pandas as pd

ALIASES = {"Invoice": "InvoiceNo", "Price": "UnitPrice", "Customer ID": "CustomerID"}
REQUIRED = [
    "InvoiceNo",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
    "Country",
]


def load_retail(
    path: Path, limit: int | None = None
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Не знайдено CSV: {path}")
    encoding = "utf-8-sig"
    try:
        frame = pd.read_csv(
            path,
            encoding=encoding,
            nrows=limit,
            dtype={"Invoice": str, "InvoiceNo": str, "StockCode": str},
        )
    except UnicodeDecodeError:
        encoding = "cp1252"
        frame = pd.read_csv(
            path,
            encoding=encoding,
            nrows=limit,
            dtype={"Invoice": str, "InvoiceNo": str, "StockCode": str},
        )
    profile = {
        "rows": len(frame),
        "columns": len(frame.columns),
        "source_columns": frame.columns.tolist(),
        "source_dtypes": frame.dtypes.astype(str).to_dict(),
        "missing": {key: int(value) for key, value in frame.isna().sum().items()},
        "duplicates": int(frame.duplicated().sum()),
        "encoding": encoding,
        "separator": ",",
        "limited": limit is not None,
    }
    frame = frame.rename(columns=ALIASES)
    if frame.columns.duplicated().any():
        raise ValueError("Неоднозначні назви стовпців після нормалізації.")
    missing = set(REQUIRED) - set(frame.columns)
    if missing:
        raise ValueError(f"Відсутні обов'язкові стовпці: {sorted(missing)}")
    return frame, profile
