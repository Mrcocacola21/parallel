"""Незалежні CPU-обчислення; функції доступні для Windows spawn."""

import math
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor


def process_value(x: int, k: int) -> float:
    if k < 1 or x < 0:
        raise ValueError("Потрібні x >= 0 та k >= 1.")
    result = 0.0
    for i in range(1, k + 1):
        result += math.sqrt(x + i) * math.sin(x + i)
    return result


def sequential_processing(data: list[int], k: int) -> list[float]:
    return [process_value(x, k) for x in data]


def split_data(data: list[int], parts: int) -> list[list[int]]:
    if parts < 1:
        raise ValueError("Кількість частин має бути додатною.")
    size, extra = divmod(len(data), parts)
    result, start = [], 0
    for i in range(parts):
        stop = start + size + (i < extra)
        result.append(data[start:stop])
        start = stop
    return result


def process_chunk(arguments: tuple[list[int], int]) -> list[float]:
    return sequential_processing(*arguments)


def parallel_processing(data: list[int], k: int, workers: int) -> list[float]:
    if workers < 1:
        raise ValueError("Кількість процесів має бути додатною.")
    # Чотири задачі на процес зменшують дисбаланс; порядок map збережено.
    chunks = split_data(data, min(len(data) or 1, workers * 4))
    with ProcessPoolExecutor(
        max_workers=workers, mp_context=mp.get_context("spawn")
    ) as pool:
        results = pool.map(process_chunk, [(chunk, k) for chunk in chunks])
        return [value for chunk in results for value in chunk]


def assert_equivalent(reference: list[float], actual: list[float]) -> None:
    if len(reference) != len(actual) or not all(
        math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)
        for a, b in zip(reference, actual)
    ):
        raise AssertionError("Послідовний і паралельний результати відрізняються.")
