"""Запуск усіх 15 завдань: python -m lab02.main."""

import logging
import multiprocessing as mp
import os

from common.data_loader import load_retail
from common.plotting import COLORS, plt, save_figure, scaling_plots
from common.preprocessing import prepare_retail
from common.utilities import (
    environment,
    fingerprint,
    parser_for,
    record,
    save_json,
    setup_logging,
    timed,
    write_timings,
)
from lab02.algorithms import (
    assert_equivalent,
    parallel_processing,
    process_chunk,
    top_countries,
)


def main() -> None:
    args = parser_for("lab02").parse_args()
    setup_logging()
    output = args.output / "quick" if args.quick else args.output
    output.mkdir(parents=True, exist_ok=True)
    (source, profile), load_seconds = timed(
        load_retail, args.data, 20_000 if args.quick else None
    )
    (frame, audit), prepare_seconds = timed(prepare_retail, source)
    if frame.empty:
        raise ValueError("Після очищення не залишилося продажів.")
    save_json(output / "profile.json", profile)
    save_json(output / "cleaning.json", audit)
    frame.head(10).to_csv(output / "prepared_sample.csv", index=False)
    threshold = float(frame.Revenue.mean())
    filtered = frame.loc[frame.Revenue > threshold]
    save_json(
        output / "filter.json",
        {
            "threshold": threshold,
            "count": len(filtered),
            "percentage": len(filtered) / len(frame) * 100,
            "revenue": float(filtered.Revenue.sum()),
            "base_count": len(frame),
        },
    )
    records, reference = [], None
    for repeat in range(1, args.repeats + 1):
        result, seconds = timed(process_chunk, frame)
        if reference is None:
            reference = result
            save_json(output / "statistics.json", reference.scalar_dict())
            reference.groups.to_csv(output / "countries.csv", index=False)
            top_countries(reference).to_csv(output / "top10.csv", index=False)
        assert_equivalent(reference, result)
        records.append(record("retail", "sequential", 1, repeat, seconds))
        for workers in [1, 2, 4, 8]:
            logging.info("multiprocessing.Pool: p=%s, повтор=%s", workers, repeat)
            result, seconds = timed(parallel_processing, frame, workers)
            assert_equivalent(reference, result)
            records.append(
                record("retail", "multiprocessing", workers, repeat, seconds)
            )
            write_timings(output, records)
    summary = write_timings(output, records)
    best = summary.loc[summary.method != "sequential"].sort_values("seconds").iloc[0]
    save_json(
        output / "metadata.json",
        {
            "environment": environment(),
            "quick": args.quick,
            "dataset": fingerprint(args.data),
            "load_seconds": load_seconds,
            "prepare_seconds": prepare_seconds,
            "rows": len(frame),
            "best_pool_workers": int(best.workers),
            "cpu_count": os.cpu_count(),
            "timing_scope": "Розбиття повного DataFrame + spawn + pickle + starmap + об'єднання + закриття пулу",
        },
    )
    scaling_plots(summary, output, "ЛР №2 · Агрегація продажів за країнами")
    top = top_countries(reference).iloc[::-1]
    figure, axis = plt.subplots(figsize=(9, 5), layout="constrained")
    axis.barh(top.Country, top.total / 1_000_000, color=COLORS[0])
    axis.set(xlabel="Виручка, млн GBP", title="10 країн з найбільшою виручкою")
    save_figure(figure, output, "top10")
    logging.info(
        "Перевірено всі агрегати, групи та Top-10; очищених рядків: %s", len(frame)
    )


if __name__ == "__main__":
    mp.freeze_support()
    main()
