import pandas as pd

from common.data_loader import load_retail
from common.preprocessing import prepare_retail
from common.utilities import record, summarize


def fixture_frame():
    return pd.DataFrame(
        {
            "InvoiceNo": ["1", "1", "C2", "3", "4", "5", "6", "7"],
            "StockCode": ["A"] * 8,
            "Description": ["Товар"] * 6 + [None, "Товар"],
            "Quantity": [2, 2, -1, 0, 1, 3, 1, 1],
            "InvoiceDate": ["2010-01-01 12:00:00"] * 7 + ["bad"],
            "UnitPrice": [5, 5, 5, 5, -1, 2, 1, 1],
            "CustomerID": [123.0] * 5 + [None, 123.0, 123.0],
            "Country": ["UK"] * 8,
        }
    )


def test_cleaning_conservation_and_anonymous_sales():
    source = fixture_frame()
    clean, audit = prepare_retail(source)
    assert len(source) == 8
    assert len(clean) == 2
    assert clean.Revenue.tolist() == [10, 6]
    assert clean.CustomerID.iloc[0] == "123"
    assert clean.CustomerID.isna().sum() == 1
    assert sum(audit["excluded"].values()) + audit["after"] == audit["before"]


def test_aliases_and_original_unchanged(tmp_path):
    source = fixture_frame().rename(
        columns={
            "InvoiceNo": "Invoice",
            "UnitPrice": "Price",
            "CustomerID": "Customer ID",
        }
    )
    path = tmp_path / "дані з пробілом.csv"
    source.to_csv(path, index=False)
    before = path.read_bytes()
    loaded, profile = load_retail(path)
    assert profile["rows"] == 8
    assert "UnitPrice" in loaded
    assert path.read_bytes() == before


def test_median_and_metrics():
    rows = [record("x", "sequential", 1, i, t) for i, t in enumerate([4, 8, 6])]
    rows += [record("x", "pool", 2, i, t) for i, t in enumerate([1, 3, 2])]
    summary = summarize(rows)
    parallel = summary[summary.method == "pool"].iloc[0]
    assert parallel.seconds == 2
    assert parallel.speedup == 3
    assert parallel.efficiency_pct == 150
