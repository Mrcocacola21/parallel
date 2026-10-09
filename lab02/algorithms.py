"""Агрегація табличних даних з коректним зважуванням середніх."""

from __future__ import annotations

import math
import multiprocessing as mp
from dataclasses import dataclass

import pandas as pd

from common.utilities import split_frame


@dataclass
class ChunkStats:
    count: int
    total: float
    mean: float | None
    minimum: float | None
    maximum: float | None
    groups: pd.DataFrame

    def scalar_dict(self) -> dict:
        return {
            "count": self.count,
            "total": self.total,
            "mean": self.mean,
            "minimum": self.minimum,
            "maximum": self.maximum,
        }


def process_chunk(
    frame: pd.DataFrame, value_column: str = "Revenue", group_column: str = "Country"
) -> ChunkStats:
    values = frame[value_column]
    if values.isna().any() or frame[group_column].isna().any():
        raise ValueError("Агрегація потребує очищених значень та груп.")
    count, total = len(frame), float(values.sum())
    groups = (
        frame.groupby(group_column, sort=True)[value_column]
        .agg(count="size", total="sum", mean="mean")
        .reset_index()
    )
    return ChunkStats(
        count,
        total,
        total / count if count else None,
        float(values.min()) if count else None,
        float(values.max()) if count else None,
        groups,
    )


def merge_results(
    results: list[ChunkStats], group_column: str = "Country"
) -> ChunkStats:
    if not results:
        raise ValueError("Потрібен щонайменше один частковий результат.")
    count = sum(result.count for result in results)
    total = math.fsum(result.total for result in results)
    nonempty = [result for result in results if result.count]
    groups = pd.concat([result.groups for result in results], ignore_index=True)
    groups = groups.groupby(group_column, as_index=False, sort=True).agg(
        count=("count", "sum"), total=("total", "sum")
    )
    groups["mean"] = groups.total / groups["count"]
    return ChunkStats(
        count,
        total,
        total / count if count else None,
        min(r.minimum for r in nonempty) if nonempty else None,
        max(r.maximum for r in nonempty) if nonempty else None,
        groups,
    )


def top_countries(stats: ChunkStats, group_column: str = "Country") -> pd.DataFrame:
    return (
        stats.groups.sort_values(["total", group_column], ascending=[False, True])
        .head(10)
        .reset_index(drop=True)
    )


def parallel_processing(frame: pd.DataFrame, workers: int) -> ChunkStats:
    if workers < 1:
        raise ValueError("Кількість процесів має бути додатною.")
    # Передається весь очищений DataFrame, без приховування вартості pickle.
    chunks = split_frame(frame, workers)
    with mp.get_context("spawn").Pool(processes=workers) as pool:
        results = pool.starmap(
            process_chunk, [(chunk, "Revenue", "Country") for chunk in chunks]
        )
    return merge_results(results)


def assert_equivalent(reference: ChunkStats, actual: ChunkStats) -> None:
    assert reference.count == actual.count, "Різна кількість записів"
    for name in ("total", "mean", "minimum", "maximum"):
        left, right = getattr(reference, name), getattr(actual, name)
        if left is None or right is None:
            assert left is right
        else:
            assert math.isclose(left, right, rel_tol=1e-9, abs_tol=1e-8), name
    pd.testing.assert_frame_equal(
        reference.groups,
        actual.groups,
        check_dtype=False,
        check_exact=False,
        rtol=1e-9,
        atol=1e-8,
    )
    pd.testing.assert_frame_equal(
        top_countries(reference),
        top_countries(actual),
        check_dtype=False,
        check_exact=False,
        rtol=1e-9,
        atol=1e-8,
    )
