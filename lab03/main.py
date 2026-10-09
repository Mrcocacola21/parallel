"""Запуск усіх 10 завдань: python -m lab03.main."""

import asyncio
import logging
from functools import partial

from common.data_loader import load_retail
from common.plotting import comparison_plot
from common.preprocessing import prepare_retail
from common.utilities import (
    environment,
    fingerprint,
    parser_for,
    record,
    save_json,
    setup_logging,
    split_frame,
    timed,
    write_timings,
)
from lab01.algorithms import assert_equivalent as assert_values
from lab03.algorithms import (
    analyze_chunk,
    analyze_with_wait,
    assert_equivalent,
    async_processing,
    merge_analysis,
    pool_processing,
    python_cpu,
    sequential,
    threading_processing,
)


def main() -> None:
    parser = parser_for("lab03")
    parser.add_argument(
        "--io-delay",
        type=float,
        default=0.25,
        help="Однакове очікування I/O для кожної з чотирьох задач, с",
    )
    args = parser.parse_args()
    if args.io_delay < 0:
        parser.error("--io-delay має бути невід'ємним")
    setup_logging()
    output = args.output / "quick" if args.quick else args.output
    output.mkdir(parents=True, exist_ok=True)
    (source, profile), load_seconds = timed(
        load_retail, args.data, 20_000 if args.quick else None
    )
    (frame, cleaning), prepare_seconds = timed(prepare_retail, source)
    if frame.empty:
        raise ValueError("Після очищення не залишилося продажів.")
    chunks = split_frame(frame, 4)
    reference = analyze_chunk(frame)
    save_json(output / "profile.json", profile)
    save_json(output / "cleaning.json", cleaning)
    save_json(output / "statistics.json", reference.summary())
    save_json(
        output / "chunks.json", [analyze_chunk(part).summary() for part in chunks]
    )
    frame.head(12).to_csv(output / "prepared_sample.csv", index=False)
    records = []
    for workload in ["analysis", "io"]:
        function = (
            analyze_chunk
            if workload == "analysis"
            else partial(analyze_with_wait, delay=args.io_delay)
        )
        methods = [
            ("sequential", 1, lambda: sequential(chunks, function)),
            ("threading", 4, lambda: threading_processing(chunks, function)),
            ("thread_pool", 2, lambda: pool_processing(chunks, 2, function)),
            ("thread_pool", 4, lambda: pool_processing(chunks, 4, function)),
            ("thread_pool", 8, lambda: pool_processing(chunks, 8, function)),
            (
                "asyncio_to_thread",
                4,
                lambda: asyncio.run(
                    async_processing(
                        chunks, analyze_chunk, args.io_delay if workload == "io" else 0
                    )
                ),
            ),
        ]
        for repeat in range(1, args.repeats + 1):
            for name, workers, operation in methods:
                logging.info("%s: %s, p=%s, повтор=%s", workload, name, workers, repeat)
                result, seconds = timed(lambda: merge_analysis(operation()))
                assert_equivalent(reference, result)
                records.append(
                    record(workload, name, workers, repeat, seconds, min(workers, 4))
                )
    # Окремий чистий Python CPU-цикл відрізняє GIL від pandas/C-операцій.
    cpu_chunks = [
        part.Quantity.head(200 if args.quick else 10_000).astype(int).tolist()
        for part in chunks
    ]
    cpu_reference = [python_cpu(chunk) for chunk in cpu_chunks]
    cpu_methods = [
        ("sequential", 1, lambda: sequential(cpu_chunks, python_cpu)),
        ("threading", 4, lambda: threading_processing(cpu_chunks, python_cpu)),
        ("thread_pool", 4, lambda: pool_processing(cpu_chunks, 4, python_cpu)),
        (
            "asyncio_to_thread",
            4,
            lambda: asyncio.run(async_processing(cpu_chunks, python_cpu)),
        ),
    ]
    for repeat in range(1, args.repeats + 1):
        for name, workers, operation in cpu_methods:
            result, seconds = timed(operation)
            for expected, actual in zip(cpu_reference, result):
                assert_values(expected, actual)
            records.append(record("python_cpu", name, workers, repeat, seconds))
    summary = write_timings(output, records)
    save_json(
        output / "metadata.json",
        {
            "environment": environment(),
            "quick": args.quick,
            "dataset": fingerprint(args.data),
            "load_seconds": load_seconds,
            "prepare_seconds": prepare_seconds,
            "parts": 4,
            "chunk_sizes": list(map(len, chunks)),
            "io_delay_seconds": args.io_delay,
            "python_cpu_elements": sum(map(len, cpu_chunks)),
            "async_model": "create_task + gather + to_thread; I/O очікує через asyncio.sleep",
            "efficiency_denominator": "Налаштовані workers; для asyncio p=4 задачі, одночасно не більше 4",
            "timing_scope": "Обчислення + створення/закриття потоків або event loop + об'єднання; без CSV/очищення/розбиття",
        },
    )
    for workload, title in [
        ("analysis", "ЛР №3 · Аналіз чотирьох частин Online Retail II"),
        ("io", "ЛР №3 · Аналіз з контрольованим очікуванням I/O"),
        ("python_cpu", "ЛР №3 · CPU-цикл Python та вплив GIL"),
    ]:
        comparison_plot(summary, output, workload, title)
    logging.info("Усі реалізації та чотири частини перевірено.")


if __name__ == "__main__":
    main()
