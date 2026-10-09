"""Потоки, справжні coroutine та коректне об'єднання множин."""

from __future__ import annotations

import asyncio
import math
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

import pandas as pd

from lab01.algorithms import sequential_processing

T = TypeVar("T")


@dataclass
class Analysis:
    count: int
    products: set[str]
    customers: set[str]
    revenue: float
    price_sum: float
    price_count: int
    max_quantity: float | None

    def summary(self) -> dict:
        return {
            "count": self.count,
            "unique_products": len(self.products),
            "unique_customers": len(self.customers),
            "revenue": self.revenue,
            "mean_price": self.price_sum / self.price_count
            if self.price_count
            else None,
            "max_quantity": self.max_quantity,
        }


def analyze_chunk(frame: pd.DataFrame) -> Analysis:
    return Analysis(
        len(frame),
        set(frame.StockCode.dropna()),
        set(frame.CustomerID.dropna()),
        float(frame.Revenue.sum()),
        float(frame.UnitPrice.sum()),
        int(frame.UnitPrice.count()),
        float(frame.Quantity.max()) if len(frame) else None,
    )


def merge_analysis(results: list[Analysis]) -> Analysis:
    nonempty = [result for result in results if result.count]
    return Analysis(
        sum(r.count for r in results),
        set().union(*(r.products for r in results)),
        set().union(*(r.customers for r in results)),
        math.fsum(r.revenue for r in results),
        math.fsum(r.price_sum for r in results),
        sum(r.price_count for r in results),
        max(r.max_quantity for r in nonempty) if nonempty else None,
    )


def assert_equivalent(reference: Analysis, actual: Analysis) -> None:
    assert reference.count == actual.count
    assert reference.products == actual.products
    assert reference.customers == actual.customers
    assert reference.price_count == actual.price_count
    for name in ("revenue", "price_sum", "max_quantity"):
        left, right = getattr(reference, name), getattr(actual, name)
        assert (
            (left is right)
            if left is None or right is None
            else math.isclose(left, right, rel_tol=1e-9, abs_tol=1e-8)
        ), name


def sequential(
    chunks: list[Any], function: Callable[[Any], T] = analyze_chunk
) -> list[T]:
    return [function(chunk) for chunk in chunks]


def threading_processing(
    chunks: list[Any], function: Callable[[Any], T] = analyze_chunk
) -> list[T]:
    futures: list[Future] = [Future() for _ in chunks]

    def worker(index: int, chunk: Any) -> None:
        try:
            futures[index].set_result(function(chunk))
        except BaseException as error:
            futures[index].set_exception(error)

    threads = [
        threading.Thread(target=worker, args=(i, chunk), name=f"part-{i}")
        for i, chunk in enumerate(chunks)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    # Future.result повертає виняток у головний потік замість тихої втрати.
    return [future.result() for future in futures]


def pool_processing(
    chunks: list[Any], workers: int, function: Callable[[Any], T] = analyze_chunk
) -> list[T]:
    if workers < 1:
        raise ValueError("Кількість потоків має бути додатною.")
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(function, chunks))


async def async_processing(
    chunks: list[Any],
    function: Callable[[Any], T] = analyze_chunk,
    io_delay: float = 0.0,
) -> list[T]:
    if io_delay < 0:
        raise ValueError("Час очікування не може бути від'ємним.")

    async def task(chunk: Any) -> T:
        if io_delay:
            await asyncio.sleep(io_delay)
        # CPU-функція не блокує event loop; обчислення виконує thread executor.
        return await asyncio.to_thread(function, chunk)

    tasks = [asyncio.create_task(task(chunk)) for chunk in chunks]
    return await asyncio.gather(*tasks)


def analyze_with_wait(frame: pd.DataFrame, delay: float) -> Analysis:
    if delay < 0:
        raise ValueError("Час очікування не може бути від'ємним.")
    time.sleep(delay)
    return analyze_chunk(frame)


def python_cpu(chunk: list[int]) -> list[float]:
    return sequential_processing(chunk, 200)
