"""Запуск: python -m lab01.main (повний варіант №3)."""

import logging
import multiprocessing as mp
import os
import random

import numpy as np
import pandas as pd

from common.plotting import scaling_plots
from common.utilities import (
    environment,
    parser_for,
    record,
    save_json,
    setup_logging,
    timed,
    write_timings,
)
from lab01.algorithms import (
    assert_equivalent,
    parallel_processing,
    process_value,
    sequential_processing,
    split_data,
)


def main() -> None:
    args = parser_for("lab01").parse_args()
    setup_logging()
    output = args.output / "quick" if args.quick else args.output
    output.mkdir(parents=True, exist_ok=True)
    n, k, seed = (2_000 if args.quick else 500_000), 200, 42
    generator = random.Random(seed)
    data, generation_time = timed(
        lambda: [generator.randint(1, 30_000) for _ in range(n)]
    )
    test_data = [10, 20, 30, 40, 50]
    sample = sequential_processing(test_data, k)
    pd.DataFrame({"x": test_data, "f(x)": sample}).to_csv(
        output / "function_check.csv", index=False
    )
    assert_equivalent(sample, [process_value(x, k) for x in test_data])
    save_json(
        output / "split_demo.json",
        {"parts": 5, "sizes": [len(x) for x in split_data(data, 5)]},
    )
    records, reference = [], None
    workers_list = [1, 2, 4, 8]
    for repeat in range(1, args.repeats + 1):
        logging.info(
            "Послідовний розрахунок %s/%s; n=%s, K=%s", repeat, args.repeats, n, k
        )
        result, seconds = timed(sequential_processing, data, k)
        if reference is None:
            reference = result
            np.save(output / "values.npy", np.asarray(reference))
        assert_equivalent(reference, result)
        records.append(record("cpu", "sequential", 1, repeat, seconds))
        for workers in workers_list:
            logging.info("ProcessPoolExecutor: p=%s, повтор=%s", workers, repeat)
            result, seconds = timed(parallel_processing, data, k, workers)
            assert_equivalent(reference, result)
            records.append(record("cpu", "process_pool", workers, repeat, seconds))
            write_timings(output, records)
    summary = write_timings(output, records)
    save_json(
        output / "metadata.json",
        {
            "environment": environment(),
            "variant": 3,
            "n": n,
            "k": k,
            "seed": seed,
            "range": [1, 30_000],
            "quick": args.quick,
            "generation_seconds": generation_time,
            "workers": workers_list,
            "oversubscribed": [p for p in workers_list if p > (os.cpu_count() or 1)],
            "timing_scope": "Розбиття + spawn + передавання + обчислення + збирання + закриття пулу",
        },
    )
    scaling_plots(summary, output, "ЛР №1 · Обчислення математичної функції")
    logging.info("Усі результати перевірено. Збережено: %s", output)


if __name__ == "__main__":
    mp.freeze_support()
    main()
