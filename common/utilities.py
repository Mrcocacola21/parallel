"""Вимірювання часу, метадані та збереження артефактів."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import logging
import os
import platform
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, TypeVar

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
T = TypeVar("T")


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("Значення має бути додатним.")
    return number


def parser_for(lab: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"Лабораторна робота {lab}")
    parser.add_argument("--data", type=Path, default=ROOT / "online_retail_II.csv")
    parser.add_argument("--output", type=Path, default=ROOT / lab / "results")
    parser.add_argument("--repeats", type=positive_int, default=3)
    parser.add_argument("--quick", action="store_true", help="Скорочений smoke-режим")
    return parser


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")


def timed(function: Callable[..., T], *args: Any, **kwargs: Any) -> tuple[T, float]:
    start = perf_counter()
    result = function(*args, **kwargs)
    return result, perf_counter() - start


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )


def fingerprint(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {
        "filename": path.name,
        "bytes": path.stat().st_size,
        "sha256": digest.hexdigest(),
    }


def environment() -> dict[str, Any]:
    versions = {}
    for name in ("numpy", "pandas", "matplotlib", "pyspark", "nbformat", "pytest"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return {
        "python": platform.python_version(),
        "os": platform.platform(),
        "logical_cpus": os.cpu_count(),
        "libraries": versions,
    }


def split_frame(frame: pd.DataFrame, parts: int) -> list[pd.DataFrame]:
    if parts < 1:
        raise ValueError("Кількість частин має бути додатною.")
    size, extra = divmod(len(frame), parts)
    chunks, start = [], 0
    for index in range(parts):
        stop = start + size + (index < extra)
        chunks.append(frame.iloc[start:stop])
        start = stop
    return chunks


def summarize(records: list[dict[str, Any]]) -> pd.DataFrame:
    raw = pd.DataFrame(records)
    keys = ["workload", "method", "workers", "effective_workers"]
    result = raw.groupby(keys, sort=False, as_index=False).agg(
        seconds=("seconds", "median"),
        min_seconds=("seconds", "min"),
        max_seconds=("seconds", "max"),
        verified=("verified", "all"),
        repeats=("seconds", "size"),
    )
    bases = result.loc[result.method == "sequential"].set_index("workload").seconds
    result["speedup"] = result.workload.map(bases) / result.seconds
    result["efficiency_pct"] = result.speedup / result.workers * 100
    return result


def write_timings(output: Path, records: list[dict[str, Any]]) -> pd.DataFrame:
    output.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_csv(output / "timings_raw.csv", index=False)
    summary = summarize(records)
    summary.to_csv(output / "timings.csv", index=False)
    return summary


def record(
    workload: str,
    method: str,
    workers: int,
    repeat: int,
    seconds: float,
    effective: int | None = None,
) -> dict[str, Any]:
    return {
        "workload": workload,
        "method": method,
        "workers": workers,
        "effective_workers": effective or workers,
        "repeat": repeat,
        "seconds": seconds,
        "verified": True,
    }
