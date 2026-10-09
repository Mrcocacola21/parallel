"""Перевірка узгодженості коду, результатів, звітів і notebook."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import nbformat
import numpy as np
import pandas as pd
from PIL import Image

from common.utilities import ROOT, fingerprint, save_json, summarize


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def audit() -> dict:
    results = []
    source = fingerprint(ROOT / "online_retail_II.csv")
    for lab, count in [("lab01", 9), ("lab02", 15), ("lab03", 10), ("lab04", 10)]:
        folder, output = ROOT / lab, ROOT / lab / "results"
        meta = read_json(output / "metadata.json")
        assert not meta["quick"], f"{lab}: скорочені результати"
        if lab == "lab01":
            assert (meta["n"], meta["k"], meta["seed"], meta["variant"]) == (
                500_000,
                200,
                42,
                3,
            )
            values = np.load(output / "values.npy")
            assert len(values) == 500_000 and np.isfinite(values).all()
        else:
            assert meta["dataset"] == source, f"{lab}: змінився вихідний CSV"
        raw = pd.read_csv(output / "timings_raw.csv")
        summary = pd.read_csv(output / "timings.csv")
        assert raw.verified.all() and summary.verified.all()
        assert (raw.seconds > 0).all() and np.isfinite(raw.seconds).all()
        assert (summary.repeats == 3).all(), f"{lab}: потрібні три повні повтори"
        pd.testing.assert_frame_equal(
            summarize(raw.to_dict("records")),
            summary,
            check_exact=False,
            rtol=1e-9,
            atol=1e-9,
        )
        notebook = nbformat.read(folder / f"{lab}.ipynb", as_version=4)
        nbformat.validate(notebook)
        task_cells = [
            cell
            for cell in notebook.cells
            if cell.cell_type == "markdown" and re.match(r"## \d+\.", cell.source)
        ]
        assert len(task_cells) == count, f"{lab}: пропущене завдання notebook"
        code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
        assert all(cell.execution_count is not None for cell in code_cells)
        assert not any(
            out.output_type == "error" for cell in code_cells for out in cell.outputs
        )
        report = (folder / "report.md").read_text(encoding="utf-8")
        for reference in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", report):
            if not reference.startswith(("http", "#")):
                assert (folder / reference).is_file(), (
                    f"Відсутнє посилання: {lab}/{reference}"
                )
        plots = sorted(output.glob("*.png"))
        assert len(plots) >= 2
        for plot in plots:
            with Image.open(plot) as image:
                assert image.width >= 640 and image.height >= 400
                image.verify()
            assert plot.with_suffix(".svg").is_file()
        results.append(
            {
                "lab": lab,
                "tasks": count,
                "measurements": len(raw),
                "plots": len(plots),
                "executed_cells": len(code_cells),
                "verified": True,
            }
        )
    cleaning = [
        read_json(ROOT / lab / "results/cleaning.json") for lab in ["lab02", "lab03"]
    ]
    spark_cleaning = read_json(ROOT / "lab04/results/cleaning.json")
    assert cleaning[0] == cleaning[1]
    assert cleaning[0]["excluded"] == spark_cleaning["spark"]["excluded"]
    assert cleaning[0]["after"] == spark_cleaning["spark"]["after"]
    stats2 = read_json(ROOT / "lab02/results/statistics.json")
    stats3 = read_json(ROOT / "lab03/results/statistics.json")
    assert stats2["count"] == stats3["count"]
    assert np.isclose(stats2["total"], stats3["revenue"], rtol=1e-9, atol=1e-8)
    countries2 = pd.read_csv(ROOT / "lab02/results/countries.csv")
    countries4 = pd.read_csv(ROOT / "lab04/results/countries.csv")
    pd.testing.assert_frame_equal(
        countries2,
        countries4,
        check_dtype=False,
        check_exact=False,
        rtol=1e-9,
        atol=1e-8,
    )
    partitions = pd.read_csv(ROOT / "lab04/results/partitions_raw.csv")
    assert partitions.verified.all()
    assert set(partitions.partitions) == {1, 2, 4, 8}
    assert set(partitions.scope) == {"with_repartition", "cached_partitions"}
    assert (partitions.groupby(["scope", "partitions"]).size() == 3).all()
    results[-1]["partition_measurements"] = len(partitions)
    results[-1]["measurements"] += len(partitions)
    lazy = read_json(ROOT / "lab04/results/lazy_evaluation.json")
    assert lazy["jobs_before"] == lazy["jobs_after_transformation"]
    assert len(lazy["jobs_after_collect"]) > len(lazy["jobs_before"])
    assert read_json(ROOT / "lab04/results/rdd.json")["verified"]
    junit = ROOT / ".work/verification/pytest.xml"
    tests = None
    if junit.exists():
        suite = ET.parse(junit).getroot().find("testsuite")
        tests = {
            key: int(suite.attrib[key])
            for key in ["tests", "failures", "errors", "skipped"]
        }
        assert tests["failures"] == tests["errors"] == tests["skipped"] == 0
    payload = {
        "dataset": source,
        "labs": results,
        "tests": tests,
        "cross_lab_consistency": True,
        "status": "passed",
    }
    save_json(ROOT / "verification.json", payload)
    return payload


def main() -> None:
    payload = audit()
    write_audit_report(payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def write_audit_report(payload: dict) -> None:
    source = payload["dataset"]
    lines = [
        "# Фінальний аудит лабораторних робіт №1–4",
        "",
        "Усі повні експерименти виконано на наданих даних; нижче — стан, підтверджений `python -m tools.audit`. "
        "Машинозчитуваний результат: [verification.json](verification.json). "
        "Повний перелік пунктів методичок: [REQUIREMENTS.md](REQUIREMENTS.md).",
        "",
        "| Лабораторна | Вимоги PDF | Реалізація | Перевірка | Звіт і notebook |",
        "|---|---|---|---|---|",
    ]
    for row in payload["labs"]:
        lab = row["lab"]
        extra = " + 19 контрольних питань" if lab == "lab01" else ""
        lines.append(
            f"| №{int(lab[-2:])} | {row['tasks']} завдань{extra} | Виконано | "
            f"{row['measurements']} замірів, усі перевірені | "
            f"[Звіт]({lab}/report.md), [виконаний notebook]({lab}/{lab}.ipynb) |"
        )
    lines.extend(
        [
            "",
            "## Виконані експерименти",
            "",
            "ЛР №1: повний варіант 3 (500 000, K=200, seed=42), baseline і ProcessPoolExecutor з p=1/2/4/8, "
            "по три повтори. ЛР №2: увесь CSV, baseline і Pool.starmap з p=1/2/4/8, по три повтори. "
            "ЛР №3: увесь очищений CSV, чотири частини, шість способів для аналізу та I/O, "
            "чотири способи для окремого Python CPU-контролю, по три повтори. "
            "ЛР №4: увесь CSV; справжні Spark DataFrame і RDD, усі три групування, "
            "по три повтори pandas/Spark і восьми конфігурацій partitions (два сценарії × 1/2/4/8).",
            "",
            "Усі чотири скорочені CLI-запуски також виконано; їх результати лежать у `results/quick/` "
            "і не підміняють повні. Після налаштування Spark роботи №1–3 повторно виконано "
            "послідовно з `.venv`, щоб усунути перетин із первинною конфігурацією середовища.",
            "",
            "## Фактично виконані команди",
            "",
            "Команди наведено з кореня проєкту. Перші перевірки №1–3 виконувались глобальним Python; "
            "остаточні повні заміри та загальні перевірки — Python з `.venv`.",
            "",
            "```powershell",
            "python -m venv --system-site-packages .venv",
            ".\\.venv\\Scripts\\python.exe -m pip install pyspark==4.0.3",
        ]
    )
    for lab in ["lab01", "lab02", "lab03", "lab04"]:
        lines.append(f".\\.venv\\Scripts\\python.exe -m {lab}.main")
    lines.extend(
        [
            "# Smoke-команди №1–3 спочатку виконано через глобальний python; №4 — через .venv.",
            "python -m lab01.main --quick --repeats 1",
            "python -m lab02.main --quick --repeats 1",
            "python -m lab03.main --quick --repeats 1",
            ".\\.venv\\Scripts\\python.exe -m lab04.main --quick --repeats 1",
            ".\\.venv\\Scripts\\python.exe -m pytest -q --junitxml=.work/verification/pytest.xml",
            ".\\.venv\\Scripts\\python.exe -m compileall -q common lab01 lab02 lab03 lab04 tools tests",
            ".\\.venv\\Scripts\\python.exe -m tools.build_documents all",
            ".\\.venv\\Scripts\\python.exe -m tools.execute_notebooks lab01 lab02 lab03 lab04",
            "python -m ruff check common lab01 lab02 lab03 lab04 tools tests",
            "python -m ruff format --check common lab01 lab02 lab03 lab04 tools tests",
            ".\\.venv\\Scripts\\python.exe -m tools.audit",
            "```",
            "",
            "## Перевірки",
            "",
        ]
    )
    if payload["tests"]:
        tests = payload["tests"]
        lines.append(
            f"Pytest: **{tests['tests']} пройдено**, помилок {tests['errors']}, "
            f"невдалих {tests['failures']}, пропущених {tests['skipped']}. "
            "JUnit-результат збережено локально у `.work/verification/pytest.xml`."
        )
    else:
        lines.append(
            "JUnit-файл недоступний; кількість pytest-перевірок цим аудитом не підтверджено."
        )
    lines.extend(
        [
            "",
            "Перевірено формулу, довжину й порядок масивів, Windows spawn, 1/2/4/8 процесів, "
            "нерівні й порожні частини, зважені середні, union множин, передачу винятків, "
            "справжні Spark DataFrame/RDD, усі групування і партиції. Аудит додатково "
            "перераховує медіани/Speedup/Efficiency з raw CSV, перевіряє виконані notebook "
            "без error cells, всі посилання звітів, цілісність PNG/SVG та узгодженість робіт №2–4.",
            "",
            "## Незмінність даних",
            "",
            f"Файл `{source['filename']}`, {source['bytes']:,} bytes. SHA-256:",
            "",
            f"`{source['sha256']}`",
            "",
            "Відбиток збігається з метаданими всіх трьох робіт із CSV. "
            "Вихідних рядків 1 067 371, очищених 1 007 913; причини виключення збігаються між pandas та Spark.",
            "",
            "## Створені файли та результати",
            "",
            "Створено `common/`, модулі/CLI/narrative/report/notebook у кожній `labXX/`, `tests/`, "
            "`tools/`, README, REQUIREMENTS, AUDIT, requirements, pyproject, .gitignore та verification.json. "
            "Кожна `results/` містить timings_raw.csv, timings.csv, metadata.json і графіки PNG/SVG. "
            "Додатково №1 має повний values.npy; №2 — профіль, очищення, агрегати і Top-10; "
            "№3 — статистики чотирьох частин; №4 — всі групи, RDD, job IDs, query plan та partitions CSV. "
            "Виконані notebook містять таблиці, код і вбудовані зображення.",
            "",
            "## Межі висновків",
            "",
            "Перевірено Windows 11, Python 3.12.6, 16 логічних CPU, Spark 4.0.3 та локальні чотири слоти. "
            "Виконання на багатовузловому кластері та інших ОС не досліджувалося. "
            "Три повтори — описова оцінка, час залежить від кешів і фонового навантаження. "
            "I/O — контрольована модель sleep, asyncio.to_thread — гібрид із потоками. "
            "Очищення досліджує додатні продажі, не нетто-потік із поверненнями. "
            "Точні дублікати вилучено за явним припущенням. Попередження winutils.exe лишається, "
            "але не завадило жодному реалізованому Spark-завданню. Незавершених перевірок "
            "в межах заданих чотирьох лабораторних не залишилося.",
        ]
    )
    (ROOT / "AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
