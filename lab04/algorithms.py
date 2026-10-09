"""Справжні Spark DataFrame, RDD та еквівалентні операції pandas."""

from __future__ import annotations

import math
import operator
from pathlib import Path
from typing import Any

import pandas as pd
from pyspark.sql import Column, DataFrame, SparkSession, functions as F

from common.data_loader import ALIASES, REQUIRED


def load_spark(spark: SparkSession, path: Path, limit: int | None = None) -> DataFrame:
    frame = (
        spark.read.option("header", True)
        .option("encoding", "UTF-8")
        .option("multiLine", True)
        .option("quote", '"')
        .option("escape", '"')
        .option("mode", "FAILFAST")
        .csv(str(path.resolve()))
    )
    for old, new in ALIASES.items():
        if old in frame.columns:
            if new in frame.columns:
                raise ValueError(f"Неоднозначний стовпець {new}")
            frame = frame.withColumnRenamed(old, new)
    if set(REQUIRED) - set(frame.columns):
        raise ValueError("CSV не містить усіх потрібних стовпців.")
    return frame.limit(limit) if limit else frame


def finite(column: str) -> Column:
    value = F.col(column)
    return value.isNotNull() & ~F.isnan(value) & (F.abs(value) != F.lit(float("inf")))


def prepare_spark(source: DataFrame) -> tuple[DataFrame, dict[str, Any]]:
    before = source.count()
    frame = source.dropDuplicates()
    remaining = frame.count()
    excluded = {"exact_duplicates": before - remaining}
    for name in ("InvoiceNo", "StockCode", "Description", "Country"):
        frame = frame.withColumn(
            name, F.when(F.length(F.trim(F.col(name))) > 0, F.trim(F.col(name)))
        )
    frame = frame.withColumn(
        "InvoiceDate", F.try_to_timestamp("InvoiceDate", F.lit("yyyy-MM-dd HH:mm:ss"))
    )
    for name in ("Quantity", "UnitPrice", "CustomerID"):
        frame = frame.withColumn(name, F.col(name).try_cast("double"))
    customer = F.col("CustomerID")
    frame = frame.withColumn(
        "CustomerID",
        F.when(
            finite("CustomerID") & (customer > 0) & (customer == F.floor(customer)),
            customer.try_cast("bigint").cast("string"),
        ),
    )
    required = [name for name in REQUIRED if name != "CustomerID"]
    missing = F.lit(False)
    for name in required:
        missing = missing | F.col(name).isNull()
    # Ті самі взаємовиключні причини та порядок, що у pandas.
    rules = [
        (
            "cancelled",
            F.coalesce(F.upper(F.col("InvoiceNo")).startswith("C"), F.lit(False)),
        ),
        ("missing_required", missing),
        ("invalid_quantity", ~finite("Quantity") | (F.col("Quantity") <= 0)),
        ("invalid_price", ~finite("UnitPrice") | (F.col("UnitPrice") <= 0)),
    ]
    for reason, bad in rules:
        frame = frame.filter(~bad)
        count = frame.count()
        excluded[reason], remaining = remaining - count, count
    frame = frame.withColumn("Revenue", F.col("Quantity") * F.col("UnitPrice"))
    frame = frame.filter(finite("Revenue"))
    after = frame.count()
    excluded["invalid_revenue"] = remaining - after
    return frame, {
        "before": before,
        "after": after,
        "removed": before - after,
        "excluded": excluded,
    }


def group_sales(frame: DataFrame, key: str = "Country") -> DataFrame:
    return frame.groupBy(key).agg(
        F.count("*").alias("count"),
        F.sum("Revenue").alias("total"),
        F.avg("Revenue").alias("mean"),
    )


def collect_groups(frame: DataFrame, key: str = "Country") -> pd.DataFrame:
    rows = group_sales(frame, key).collect()
    result = pd.DataFrame(
        [row.asDict() for row in rows], columns=[key, "count", "total", "mean"]
    )
    return result.sort_values(key).reset_index(drop=True)


def pandas_groups(frame: pd.DataFrame, key: str = "Country") -> pd.DataFrame:
    return (
        frame.groupby(key, sort=True)
        .Revenue.agg(count="size", total="sum", mean="mean")
        .reset_index()
    )


def assert_groups(reference: pd.DataFrame, actual: pd.DataFrame) -> None:
    pd.testing.assert_frame_equal(
        reference, actual, check_dtype=False, check_exact=False, rtol=1e-9, atol=1e-8
    )


def rdd_demo(frame: DataFrame, threshold: float) -> dict[str, float | int]:
    # Увесь очищений набір: map формує Revenue, filter використовує той самий поріг.
    mapped = frame.select("Quantity", "UnitPrice").rdd.map(
        lambda row: float(row[0]) * float(row[1])
    )
    filtered = mapped.filter(lambda revenue: revenue > threshold)
    count = filtered.count()
    total = filtered.reduce(operator.add) if count else 0.0
    expected = (
        frame.filter(F.col("Revenue") > threshold)
        .agg(F.count("*").alias("count"), F.sum("Revenue").alias("total"))
        .first()
    )
    assert count == expected["count"]
    assert math.isclose(total, expected["total"] or 0.0, rel_tol=1e-9, abs_tol=1e-7)
    return {"count": count, "total": total, "threshold": threshold}
