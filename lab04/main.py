"""Усі 10 завдань PySpark, повні та прогріті вимірювання."""

import logging
import math
from pathlib import Path

import pandas as pd
from pyspark.sql import functions as F

from common.data_loader import load_retail
from common.preprocessing import prepare_retail
from common.utilities import (
    environment,
    fingerprint,
    parser_for,
    positive_int,
    record,
    save_json,
    setup_logging,
    timed,
    write_timings,
)
from lab04.algorithms import (
    assert_groups,
    collect_groups,
    group_sales,
    load_spark,
    pandas_groups,
    prepare_spark,
    rdd_demo,
)
from lab04.plotting import save_plots
from lab04.spark_environment import create_spark


def main() -> None:
    parser = parser_for("lab04")
    parser.add_argument("--cores", type=positive_int, default=4)
    parser.add_argument("--java-home", type=Path)
    args = parser.parse_args()
    setup_logging()
    output = args.output / "quick" if args.quick else args.output
    output.mkdir(parents=True, exist_ok=True)
    limit = 20_000 if args.quick else None
    spark, startup_seconds = timed(create_spark, args.cores, args.java_home)
    try:
        logging.info("Spark %s; master=%s", spark.version, spark.sparkContext.master)
        raw = load_spark(spark, args.data, limit).cache()
        _, spark_load_seconds = timed(raw.count)
        profile = {
            "rows": raw.count(),
            "columns": len(raw.columns),
            "raw_schema": raw.schema.jsonValue(),
            "initial_partitions": raw.rdd.getNumPartitions(),
            "missing": raw.select(
                *[F.sum(F.col(c).isNull().cast("int")).alias(c) for c in raw.columns]
            )
            .first()
            .asDict(),
        }
        save_json(output / "profile.json", profile)
        (clean, spark_cleaning), spark_prepare_seconds = timed(prepare_spark, raw)
        clean = clean.cache()
        clean_count, cache_seconds = timed(clean.count)
        if not clean_count:
            raise ValueError("Після очищення не залишилося продажів.")
        (pandas_source, pandas_profile), pandas_load_seconds = timed(
            load_retail, args.data, limit
        )
        (pandas_frame, pandas_cleaning), pandas_prepare_seconds = timed(
            prepare_retail, pandas_source
        )
        assert spark_cleaning["excluded"] == pandas_cleaning["excluded"]
        assert clean_count == len(pandas_frame)
        save_json(
            output / "cleaning.json",
            {"spark": spark_cleaning, "pandas": pandas_cleaning},
        )
        threshold = float(pandas_frame.Revenue.mean())
        selection = clean.filter(F.col("Revenue") > threshold).select(
            "InvoiceNo", "StockCode", "CustomerID", "Country", "Revenue"
        )
        selection.limit(10).toPandas().to_csv(
            output / "filtered_sample.csv", index=False
        )
        filter_stats = (
            selection.agg(F.count("*").alias("count"), F.sum("Revenue").alias("total"))
            .first()
            .asDict()
        )
        pandas_filtered = pandas_frame[pandas_frame.Revenue > threshold]
        assert filter_stats["count"] == len(pandas_filtered)
        assert math.isclose(
            filter_stats["total"],
            float(pandas_filtered.Revenue.sum()),
            rel_tol=1e-9,
            abs_tol=1e-8,
        )
        save_json(output / "filter.json", {**filter_stats, "threshold": threshold})
        references = {}
        for key, name in [
            ("Country", "countries"),
            ("StockCode", "products"),
            ("CustomerID", "customers"),
        ]:
            pframe = pandas_frame.dropna(subset=[key])
            sframe = clean.filter(F.col(key).isNotNull())
            expected = pandas_groups(pframe, key)
            actual = collect_groups(sframe, key)
            assert_groups(expected, actual)
            actual.to_csv(output / f"{name}.csv", index=False)
            references[key] = expected
        rdd_result, rdd_seconds = timed(rdd_demo, clean, threshold)
        save_json(
            output / "rdd.json",
            {**rdd_result, "seconds": rdd_seconds, "verified": True},
        )
        spark.sparkContext.setJobGroup("lazy_demo", "Transformation та Action")
        jobs_before = spark.sparkContext.statusTracker().getJobIdsForGroup("lazy_demo")
        lazy_plan = group_sales(clean.filter(F.col("Revenue") > threshold))
        jobs_after_transform = spark.sparkContext.statusTracker().getJobIdsForGroup(
            "lazy_demo"
        )
        assert jobs_before == jobs_after_transform
        (output / "query_plan.txt").write_text(
            lazy_plan._jdf.queryExecution().toString(), encoding="utf-8"
        )
        lazy_plan.collect()
        jobs_after_action = spark.sparkContext.statusTracker().getJobIdsForGroup(
            "lazy_demo"
        )
        assert len(jobs_after_action) > len(jobs_after_transform)
        save_json(
            output / "lazy_evaluation.json",
            {
                "jobs_before": jobs_before,
                "jobs_after_transformation": jobs_after_transform,
                "jobs_after_collect": jobs_after_action,
                "transformations": [
                    "filter",
                    "select",
                    "groupBy/agg",
                    "repartition",
                    "RDD.map",
                    "RDD.filter",
                ],
                "actions": ["count", "collect", "RDD.reduce"],
            },
        )
        spark.sparkContext.setLocalProperty("spark.jobGroup.id", None)
        # Прогрів усіх шляхів перед збором вимірювань, без результатного кешу groupBy.
        pandas_groups(pandas_frame)
        collect_groups(clean)
        records = []
        for repeat in range(1, args.repeats + 1):
            actual, seconds = timed(pandas_groups, pandas_frame)
            assert_groups(references["Country"], actual)
            records.append(record("engines", "sequential", 1, repeat, seconds))
            actual, seconds = timed(collect_groups, clean)
            assert_groups(references["Country"], actual)
            records.append(record("engines", "spark", args.cores, repeat, seconds))
        partition_records = []
        for partitions in [1, 2, 4, 8]:
            logging.info("Дослідження partitions=%s", partitions)
            # Включно з shuffle: побудова repartition + groupBy + collect.
            collect_groups(clean.repartition(partitions))
            for repeat in range(1, args.repeats + 1):
                actual, seconds = timed(
                    lambda: collect_groups(clean.repartition(partitions))
                )
                assert_groups(references["Country"], actual)
                partition_records.append(
                    {
                        "scope": "with_repartition",
                        "partitions": partitions,
                        "repeat": repeat,
                        "seconds": seconds,
                        "verified": True,
                    }
                )
            # Окремий прогрітий, матеріалізований розподіл; repartition поза таймером.
            distributed = clean.repartition(partitions).cache()
            _, repartition_seconds = timed(distributed.count)
            assert distributed.rdd.getNumPartitions() == partitions
            collect_groups(distributed)
            for repeat in range(1, args.repeats + 1):
                actual, seconds = timed(collect_groups, distributed)
                assert_groups(references["Country"], actual)
                partition_records.append(
                    {
                        "scope": "cached_partitions",
                        "partitions": partitions,
                        "repeat": repeat,
                        "seconds": seconds,
                        "materialization_seconds": repartition_seconds,
                        "verified": True,
                    }
                )
            distributed.unpersist(blocking=True)
        raw_partitions = pd.DataFrame(partition_records)
        raw_partitions.to_csv(output / "partitions_raw.csv", index=False)
        partition_summary = raw_partitions.groupby(
            ["scope", "partitions"], as_index=False
        ).agg(
            seconds=("seconds", "median"),
            min_seconds=("seconds", "min"),
            max_seconds=("seconds", "max"),
            repeats=("repeat", "size"),
            verified=("verified", "all"),
        )
        partition_summary.to_csv(output / "partitions.csv", index=False)
        summary = write_timings(output, records)
        parameters = {
            "version": spark.version,
            "master": spark.sparkContext.master,
            "default_parallelism": spark.sparkContext.defaultParallelism,
            "local_cores": args.cores,
            "configuration": dict(spark.sparkContext.getConf().getAll()),
        }
        # Не зберігаємо локальні абсолютні шляхи або службові секрети Spark.
        parameters["configuration"] = {
            k: v
            for k, v in parameters["configuration"].items()
            if k
            in [
                "spark.master",
                "spark.app.name",
                "spark.sql.shuffle.partitions",
                "spark.sql.adaptive.enabled",
                "spark.sql.session.timeZone",
                "spark.ui.enabled",
                "spark.driver.host",
                "spark.driver.bindAddress",
            ]
        }
        save_json(output / "spark_session.json", parameters)
        save_json(
            output / "metadata.json",
            {
                "environment": environment(),
                "quick": args.quick,
                "dataset": fingerprint(args.data),
                "rows": clean_count,
                "spark_startup_seconds": startup_seconds,
                "spark_load_seconds": spark_load_seconds,
                "spark_prepare_seconds": spark_prepare_seconds,
                "cache_materialization_seconds": cache_seconds,
                "pandas_load_seconds": pandas_load_seconds,
                "pandas_prepare_seconds": pandas_prepare_seconds,
                "spark": parameters,
                "prepared_schema": clean.schema.jsonValue(),
                "prepared_partitions": clean.rdd.getNumPartitions(),
                "partition_values": [1, 2, 4, 8],
                "timing_scope": "Прогрітий groupBy(Country): count/sum/mean + collect + мала таблиця pandas",
                "partition_scopes": {
                    "with_repartition": "repartition входить у час",
                    "cached_partitions": "repartition і cache.count поза часом",
                },
            },
        )
        save_plots(summary, partition_summary, output, args.cores)
        logging.info(
            "Усі Spark DataFrame, RDD і partitions перевірено на %s рядках.",
            clean_count,
        )
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
