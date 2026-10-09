"""Інтеграційні тести справжнього Spark, включно з Python-worker RDD."""

import pandas as pd
import pytest
from pyspark.sql import functions as F

from common.preprocessing import prepare_retail
from lab04.algorithms import (
    assert_groups,
    collect_groups,
    load_spark,
    pandas_groups,
    prepare_spark,
    rdd_demo,
)
from lab04.spark_environment import create_spark
from tests.test_data import fixture_frame


@pytest.fixture(scope="module")
def spark():
    session = create_spark(2)
    yield session
    session.stop()


def test_spark_cleaning_groups_partitions_and_rdd(spark, tmp_path):
    source = fixture_frame()
    path = tmp_path / "роздрібні дані.csv"
    source.to_csv(path, index=False)
    raw = load_spark(spark, path)
    actual, audit = prepare_spark(raw)
    expected, reference_audit = prepare_retail(source)
    assert audit["excluded"] == reference_audit["excluded"]
    assert actual.count() == len(expected)
    assert actual.filter(F.col("CustomerID").isNull()).count() == 1
    for partitions in [1, 2, 4, 8]:
        distributed = actual.repartition(partitions)
        assert distributed.rdd.getNumPartitions() == partitions
        assert_groups(pandas_groups(expected), collect_groups(distributed))
    stats = rdd_demo(actual, 7)
    assert stats["count"] == 1
    assert stats["total"] == 10


def test_group_results_for_all_keys(spark):
    # createDataFrame також перевіряє Python-worker після виправлення SPARK-53759.
    frame = spark.createDataFrame(
        [("UK", "A", "1", 2.0), ("UK", "A", "2", 4.0), ("DE", "B", "1", 8.0)],
        ["Country", "StockCode", "CustomerID", "Revenue"],
    )
    pdf = pd.DataFrame(
        [("UK", "A", "1", 2.0), ("UK", "A", "2", 4.0), ("DE", "B", "1", 8.0)],
        columns=frame.columns,
    )
    for key in ["Country", "StockCode", "CustomerID"]:
        assert_groups(pandas_groups(pdf, key), collect_groups(frame, key))
