"""Звіт і виконуваний notebook з фактично збережених результатів."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import nbformat as nbf
import pandas as pd

from common.utilities import ROOT


def markdown_table(frame: pd.DataFrame) -> str:
    return frame.to_markdown(index=False, floatfmt=".4f")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def lab01_tasks() -> list[tuple[str, str, str]]:
    return [
        (
            "1. Генерація даних",
            "Варіант №3 і відтворюваність генератора.",
            "display(meta)\nrng = random.Random(42)\ndisplay([rng.randint(1, 30_000) for _ in range(10)])",
        ),
        (
            "2. Послідовний алгоритм",
            "Формула реалізована в імпортованому модулі; малий контрольний набір.",
            "print(inspect.getsource(a.process_value))\ndisplay(pd.read_csv(result_dir / 'function_check.csv'))",
        ),
        (
            "3. Час послідовної обробки",
            "Повні вимірювання без вартості запису результатів.",
            "display(raw[raw.method == 'sequential'])",
        ),
        (
            "4. Розподіл даних",
            "Демонстрація п'яти частин та коректного нерівного розбиття.",
            "display(read_json('split_demo.json'))\ndisplay(a.split_data(list(range(13)), 5))",
        ),
        (
            "5. ProcessPoolExecutor",
            "Пул запускають з CLI, що безпечно для Windows. Тут відображається фактична реалізація.",
            "print(inspect.getsource(a.parallel_processing))",
        ),
        (
            "6. Кількість процесів",
            "Окремі вимірювання p=1,2,4,8, включно з усіма накладними витратами.",
            "display(raw[raw.method == 'process_pool'])",
        ),
        (
            "7. Speedup та Efficiency",
            "Медіанні значення; baseline є окремим послідовним алгоритмом.",
            "display(timings)\nassert np.allclose(timings.efficiency_pct, timings.speedup / timings.workers * 100)",
        ),
        (
            "8. Правильність",
            "У CLI перевірено кожен елемент кожного запуску; notebook додатково перевіряє перші десять.",
            "values = np.load(result_dir / 'values.npy')\nassert len(values) == meta['n']\nrng = random.Random(meta['seed'])\nsample = [rng.randint(1, 30_000) for _ in range(10)]\na.assert_equivalent(values[:10].tolist(), a.sequential_processing(sample, meta['k']))\ndisplay({'elements': len(values), 'all_runs_verified': bool(raw.verified.all())})",
        ),
        (
            "9. Графіки",
            "Час, прискорення та ефективність з однакових вимірювань.",
            "for name in ['time', 'speedup', 'efficiency']:\n    display(Image(filename=str(result_dir / f'{name}.png')))",
        ),
    ]


def build(
    lab: str,
    tasks: list[tuple[str, str, str]],
    imports: str,
    results_text: str,
    analysis: str,
    figures: list[str],
) -> None:
    folder = ROOT / lab
    narrative = (folder / "narrative.md").read_text(encoding="utf-8")
    meta = read_json(folder / "results/metadata.json")
    timings = pd.read_csv(folder / "results/timings.csv")
    best = timings.loc[timings.seconds.idxmin()]
    if lab in ("lab01", "lab02"):
        conclusion = (
            f"Найменший час має {best.method}, p={int(best.workers)}: {best.seconds:.4f} с. "
            "Правильність усіх повних запусків підтверджено; доцільність паралельності "
            "визначається співвідношенням обчислень і накладних витрат."
        )
    elif lab == "lab03":
        io = timings[timings.workload == "io"].sort_values("seconds").iloc[0]
        conclusion = (
            f"Для I/O найшвидший спосіб {io.method}, p={int(io.workers)}: S={io.speedup:.3f}. "
            "Перекриття очікувань допомагає, а CPU-обчислення потребують урахування GIL "
            "та максимуму чотирьох незалежних задач. Усі способи дали еквівалентний аналіз."
        )
    else:
        spark = timings[timings.method == "spark"].iloc[0]
        conclusion = (
            f"Для прогрітого локального Spark S={spark.speedup:.4f} відносно pandas. "
            "Усі DataFrame/RDD та групування перевірені. Зміна партицій впливає на "
            "планування та shuffle; її слід оцінювати при явних межах вимірювання."
        )
    table = timings.rename(
        columns={
            "workload": "Навантаження",
            "method": "Спосіб",
            "workers": "p",
            "effective_workers": "Корисне p",
            "seconds": "Медіана, с",
            "min_seconds": "Мінімум, с",
            "max_seconds": "Максимум, с",
            "verified": "Перевірено",
            "repeats": "Повторів",
            "speedup": "Speedup",
            "efficiency_pct": "Efficiency, %",
        }
    )
    report = (
        f"# Лабораторна робота №{int(lab[-2:])}\n\n"
        + narrative
        + "\n\n## Результати експериментів\n\n"
        + results_text
        + "\n\n"
        + markdown_table(table)
        + "\n\n"
        + "\n\n".join(f"![{name}](results/{name}.png)" for name in figures)
        + "\n\n## Аналіз результатів\n\n"
        + analysis
        + "\n\n## Висновки\n\n"
        + conclusion
        + "\n\n## Відтворення та середовище\n\n"
        + f"Повний запуск: `python -m {lab}.main`. Скорочений: `python -m {lab}.main --quick --repeats 1`. "
        + "Скорочені результати відокремлено в `results/quick/`. "
        + "Окремі вимірювання: [timings_raw.csv](results/timings_raw.csv); "
        + "підсумок: [timings.csv](results/timings.csv); "
        + "метадані: [metadata.json](results/metadata.json).\n\n"
        + "```json\n"
        + json.dumps(meta["environment"], ensure_ascii=False, indent=2)
        + "\n```\n"
    )
    (folder / "report.md").write_text(report, encoding="utf-8")
    setup = (
        "from pathlib import Path\nimport sys\nimport json\nimport inspect\nimport random\n"
        "import numpy as np\nimport pandas as pd\n"
        "from IPython.display import display, Image, Markdown\n"
        "root = Path.cwd().resolve()\n"
        "if not (root / 'common').exists():\n    root = root.parent\n"
        "if not (root / 'common').exists():\n    raise RuntimeError('Відкрийте notebook у корені проєкту або каталозі лабораторної.')\n"
        "sys.path.insert(0, str(root))\n" + imports + "\n"
        f"result_dir = root / '{lab}' / 'results'\n"
        "def read_json(name):\n    return json.loads((result_dir / name).read_text(encoding='utf-8'))\n"
        "meta = read_json('metadata.json')\n"
        "timings = pd.read_csv(result_dir / 'timings.csv')\n"
        "raw = pd.read_csv(result_dir / 'timings_raw.csv')\n"
        "pd.set_option('display.max_columns', 16)\n"
        "assert not meta.get('quick', False), 'Для захисту потрібен повний запуск.'"
    )
    cells = [
        nbf.v4.new_markdown_cell(
            f"# Лабораторна робота №{int(lab[-2:])}\n\n"
            + narrative.split("## Хід роботи")[0]
            + "\n\n## Використані технології та підготовка середовища\n\n"
            "Python, pandas, NumPy, Matplotlib та засоби паралельності з модуля роботи. "
            "Встановлення: `python -m pip install -r requirements.txt`. "
            f"Повні обчислення: `python -m {lab}.main`. "
            "Notebook відтворює аналіз збереженого повного експерименту; "
            "worker-функції розміщені в імпортованих `.py`, а запуск пулів відбувається через CLI."
        ),
        nbf.v4.new_code_cell(setup),
    ]
    for title, explanation, code in tasks:
        cells.extend(
            [
                nbf.v4.new_markdown_cell(f"## {title}\n\n{explanation}"),
                nbf.v4.new_code_cell(code),
            ]
        )
    cells.extend(
        [
            nbf.v4.new_markdown_cell(
                "## Аналіз результатів\n\n" + results_text + "\n\n" + analysis
            ),
            nbf.v4.new_code_cell("display(timings)"),
            nbf.v4.new_markdown_cell("## Висновки\n\n" + conclusion),
        ]
    )
    if "## Контрольні питання" in narrative:
        cells.append(
            nbf.v4.new_markdown_cell(
                "## Контрольні питання" + narrative.split("## Контрольні питання")[1]
            )
        )
    notebook = nbf.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": meta["environment"]["python"],
            },
        },
    )
    nbf.write(notebook, folder / f"{lab}.ipynb")


def build_lab01() -> None:
    frame = pd.read_csv(ROOT / "lab01/results/timings.csv")
    parallel = frame[frame.method == "process_pool"]
    best = parallel.loc[parallel.seconds.idxmin()]
    baseline = frame[frame.method == "sequential"].iloc[0]
    one = parallel[parallel.workers == 1].iloc[0]
    analysis = (
        f"Послідовний прохід має медіану {baseline.seconds:.4f} с. "
        f"Пул з одним процесом — {one.seconds:.4f} с (S={one.speedup:.3f}), "
        "що демонструє вартість організації пулу. "
        f"Найшвидший досліджений пул: p={int(best.workers)}, {best.seconds:.4f} с, "
        f"S={best.speedup:.3f}, E={best.efficiency_pct:.2f}%. "
        "Навіть за наявності 16 логічних CPU ідеальне прискорення не гарантоване: "
        "ядра ділять ресурси, а кожен запуск передає великий масив через IPC. "
        "Розкид мінімум–максимум відображає нестабільність середовища; три повтори не є "
        "повноцінним статистичним дослідженням. Оптимум стосується цього комп'ютера, "
        "реалізації та поточного навантаження. "
        + (
            "Для цього обсягу найкращий пул прискорив обчислення."
            if best.speedup > 1
            else "У цьому середовищі навіть найкращий пул повільніший за послідовний алгоритм."
        )
    )
    build(
        "lab01",
        lab01_tasks(),
        "from lab01 import algorithms as a",
        "Повний варіант №3; три повтори всіх п'яти конфігурацій. Кожен результат перевірений.",
        analysis,
        ["time", "speedup", "efficiency"],
    )


def build_lab02() -> None:
    folder = ROOT / "lab02/results"
    profile, cleaning, filtered = [
        read_json(folder / name)
        for name in ["profile.json", "cleaning.json", "filter.json"]
    ]
    timings = pd.read_csv(folder / "timings.csv")
    parallel = timings[timings.method == "multiprocessing"]
    best = parallel.loc[parallel.seconds.idxmin()]
    efficient = parallel.loc[parallel.efficiency_pct.idxmax()]
    baseline = timings[timings.method == "sequential"].iloc[0]
    results = (
        f"Вихідний набір: {profile['rows']:,} рядків і {profile['columns']} стовпців. "
        f"Точних дублікатів: {profile['duplicates']:,}. "
        f"Після очищення: {cleaning['after']:,}; виключено {cleaning['removed']:,}.\n\n"
        + markdown_table(
            pd.DataFrame(
                list(cleaning["excluded"].items()), columns=["Причина", "Виключено"]
            )
        )
        + f"\n\nЗбережено {cleaning['retained_missing_customers']:,} продажів без відомого клієнта. "
        f"Глобальне середнє Revenue: {filtered['threshold']:.6f} GBP; вище нього "
        f"{filtered['count']:,} рядків ({filtered['percentage']:.3f}%), "
        f"сума {filtered['revenue']:,.2f} GBP.\n\n### Top-10 країн\n\n"
        + markdown_table(pd.read_csv(folder / "top10.csv"))
    )
    analysis = (
        f"Послідовне векторизоване групування: {baseline.seconds:.4f} с. "
        f"Найшвидший пул: p={int(best.workers)}, {best.seconds:.4f} с, "
        f"S={best.speedup:.4f}, E={best.efficiency_pct:.2f}%. "
        f"Найбільша ефективність серед пулів при p={int(efficient.workers)}. "
        + (
            "Жоден досліджений пул не перевершив послідовний алгоритм. "
            if best.speedup < 1
            else "Найкращий пул перевершив послідовний алгоритм. "
        )
        + "Саме групування pandas реалізоване ефективними низькорівневими операціями. "
        "Запуск процесів і серіалізація понад мільйона вихідних рядків можуть коштувати "
        "більше, ніж корисні обчислення. Це пояснює відмінність від CPU-циклу в ЛР №1. "
        "Збільшення p збільшує витрати пам'яті та організації пулу. Для цього аналізу "
        "доцільний спосіб з найменшим виміряним часом; оптимум пулу не означає, що "
        "слід обов'язково обрати multiprocessing. Послідовний і паралельний алгоритми "
        "дають однакові числові результати в установленій похибці, усі групи та Top-10 збігаються."
    )
    tasks = [
        (
            "1. Завантаження",
            "Вихідні дані та відбиток файлу.",
            "display(meta['dataset'])\ndisplay(read_json('profile.json'))",
        ),
        (
            "2. Первинний аналіз",
            "Розмір, типи, пропуски та дублікати.",
            "p = read_json('profile.json')\ndisplay(pd.DataFrame({'Тип': p['source_dtypes'], 'Пропуски': p['missing']}))\ndisplay({'rows': p['rows'], 'columns': p['columns'], 'duplicates': p['duplicates']})",
        ),
        (
            "3. Підготовка",
            "Взаємовиключні причини очищення; анонімні продажі збережено.",
            "cleaning = read_json('cleaning.json')\ndisplay(cleaning)\nassert sum(cleaning['excluded'].values()) + cleaning['after'] == cleaning['before']",
        ),
        (
            "4. Revenue",
            "Перші підготовлені рядки та контроль добутку.",
            "sample = pd.read_csv(result_dir / 'prepared_sample.csv')\ndisplay(sample)\nassert np.allclose(sample.Revenue, sample.Quantity * sample.UnitPrice)",
        ),
        (
            "5. Фільтрація",
            "Використано глобальний поріг середнього Revenue.",
            "display(read_json('filter.json'))",
        ),
        (
            "6. Групування",
            "Повна таблиця країн.",
            "countries = pd.read_csv(result_dir / 'countries.csv')\ndisplay(countries)",
        ),
        (
            "7. Top-10",
            "Сортування за виручкою.",
            "display(pd.read_csv(result_dir / 'top10.csv'))\ndisplay(Image(filename=str(result_dir / 'top10.png')))",
        ),
        (
            "8. Функція та послідовний алгоритм",
            "Глобальні статистики та реалізація.",
            "print(inspect.getsource(a.process_chunk))\ndisplay(read_json('statistics.json'))\ndisplay(raw[raw.method == 'sequential'])",
        ),
        (
            "9. Розподіл DataFrame",
            "Нерівні частини не порушують загальне середнє.",
            "from common.utilities import split_frame\nparts = split_frame(sample, 4)\ndisplay([len(part) for part in parts])\nassert sum(map(len, parts)) == len(sample)",
        ),
        (
            "10. Pool та starmap",
            "Запуск із CLI гарантує імпортовані worker-функції.",
            "print(inspect.getsource(a.parallel_processing))",
        ),
        (
            "11. Об'єднання",
            "Коректність зважування на нерівних частинах.",
            "print(inspect.getsource(a.merge_results))\nmerged = a.merge_results([a.process_chunk(part) for part in parts])\na.assert_equivalent(a.process_chunk(sample), merged)\ndisplay(merged.scalar_dict())",
        ),
        (
            "12. Перевірка",
            "Кожен повний запуск перевірив також країни та Top-10.",
            "assert raw.verified.all()\ndisplay(raw[['method', 'workers', 'repeat', 'verified']])",
        ),
        (
            "13. Вимірювання",
            "Окремі повтори та медіани для 1,2,4,8 процесів.",
            "display(raw)\ndisplay(timings)",
        ),
        (
            "14. Графіки",
            "Час, прискорення та ефективність.",
            "for name in ['time', 'speedup', 'efficiency']:\n    display(Image(filename=str(result_dir / f'{name}.png')))",
        ),
        (
            "15. Оптимальна кількість процесів",
            "Найшвидший пул та baseline порівнюються окремо.",
            "display(timings.sort_values('seconds'))\ndisplay(meta['environment'])",
        ),
    ]
    build(
        "lab02",
        tasks,
        "from lab02 import algorithms as a",
        results,
        analysis,
        ["time", "speedup", "efficiency", "top10"],
    )


def build_lab03() -> None:
    folder = ROOT / "lab03/results"
    timings = pd.read_csv(folder / "timings.csv")
    stats, meta = (
        read_json(folder / "statistics.json"),
        read_json(folder / "metadata.json"),
    )
    chunks = read_json(folder / "chunks.json")
    results = (
        "Статистика всього очищеного набору (унікальні клієнти — тільки відомі ID):\n\n"
        + markdown_table(pd.DataFrame([stats]))
        + "\n\nЧотири незалежні частини:\n\n"
        + markdown_table(pd.DataFrame(chunks))
        + f"\n\nОчікування на задачу: {meta['io_delay_seconds']} с; "
        f"чистий Python CPU-контроль: {meta['python_cpu_elements']:,} значень, K=200."
    )
    notes = []
    for workload, label in [
        ("analysis", "Аналіз pandas"),
        ("io", "Аналіз із I/O"),
        ("python_cpu", "Python CPU-цикл"),
    ]:
        part = timings[timings.workload == workload]
        best = part.loc[part.seconds.idxmin()]
        base = part[part.method == "sequential"].iloc[0]
        notes.append(
            f"{label}: baseline {base.seconds:.4f} с; найшвидший спосіб "
            f"{best.method}, p={int(best.workers)}, {best.seconds:.4f} с, S={best.speedup:.3f}."
        )
    analysis = (
        "\n\n".join(notes)
        + "\n\n"
        + "Для I/O перекриття очікувань дає виграш, обмежений чотирма незалежними задачами "
        "та часом самого аналізу. Вісім workers не створюють восьми задач. "
        "Python CPU-контроль показує обмеження GIL: потоки не гарантують багатоядерного "
        "прискорення Python-циклу. Pandas містить C-операції, роботу з рядками та побудову "
        "множин, тому його масштабування є змішаним і залежить від реалізації. "
        "Малі відмінності часу не слід трактувати як універсальну перевагу: вони залежать "
        "від кешів, планувальника й фонового навантаження. Asyncio у цій роботі керує "
        "очікуваннями та віддає CPU-функції потокам; джерелом CPU-паралелізму є "
        "низькорівневі операції, які звільняють GIL, а не сама наявність async def. "
        "Усі повні реалізації дали ті самі множини ID, кількості, виручку, середню ціну та максимум."
    )
    tasks = [
        (
            "1. Завантаження та підготовка",
            "Спільна політика очищення і нормалізації.",
            "display(read_json('profile.json'))\ndisplay(read_json('cleaning.json'))\nsample = pd.read_csv(result_dir / 'prepared_sample.csv', dtype={'StockCode': str, 'CustomerID': 'string'})\ndisplay(sample)",
        ),
        (
            "2. Функція обробки частини",
            "Шість аналітичних показників та дані для правильного об'єднання.",
            "print(inspect.getsource(a.analyze_chunk))\ndisplay(read_json('statistics.json'))",
        ),
        (
            "3. Чотири незалежні частини",
            "Унікальні значення між частинами можуть перетинатися.",
            "display(meta['chunk_sizes'])\ndisplay(pd.DataFrame(read_json('chunks.json')))",
        ),
        (
            "4. Послідовна обробка",
            "Однакові чотири частини; три повтори.",
            "display(raw[(raw.workload == 'analysis') & (raw.method == 'sequential')])",
        ),
        (
            "5. threading.Thread",
            "По потоку на частину; помилки повертаються через Future.result().",
            "print(inspect.getsource(a.threading_processing))\ndisplay(timings[timings.method == 'threading'])",
        ),
        (
            "6. ThreadPoolExecutor",
            "2,4,8 workers при максимумі чотирьох активних задач.",
            "print(inspect.getsource(a.pool_processing))\ndisplay(timings[(timings.workload == 'analysis') & (timings.method == 'thread_pool')])",
        ),
        (
            "7. Asyncio",
            "create_task та gather керують справжнім очікуванням to_thread та sleep.",
            "print(inspect.getsource(a.async_processing))\nfrom common.utilities import split_frame\nparts = split_frame(sample, 4)\npartial_results = await a.async_processing(parts)\na.assert_equivalent(a.analyze_chunk(sample), a.merge_analysis(partial_results))\ndisplay(a.merge_analysis(partial_results).summary())",
        ),
        (
            "8. I/O-залежні задачі",
            "Однакові затримки; результати аналізу не замінюються очікуванням.",
            "display({'delay_seconds': meta['io_delay_seconds'], 'tasks': meta['parts']})\ndisplay(timings[timings.workload == 'io'])\ndisplay(Image(filename=str(result_dir / 'io.png')))",
        ),
        (
            "9. Speedup та Efficiency",
            "Розрахунки для трьох незалежних навантажень.",
            "display(timings)\nassert np.allclose(timings.efficiency_pct, timings.speedup / timings.workers * 100)\nassert raw.verified.all()",
        ),
        (
            "10. Порівняльний аналіз",
            "GIL, межа конкурентності та зважування середніх.",
            "print(inspect.getsource(a.merge_analysis))\nfor name in ['analysis', 'python_cpu']:\n    display(Image(filename=str(result_dir / f'{name}.png')))",
        ),
    ]
    build(
        "lab03",
        tasks,
        "from lab03 import algorithms as a",
        results,
        analysis,
        ["analysis", "io", "python_cpu"],
    )


def build_lab04() -> None:
    folder = ROOT / "lab04/results"
    timings = pd.read_csv(folder / "timings.csv")
    partitions = pd.read_csv(folder / "partitions.csv")
    meta = read_json(folder / "metadata.json")
    profile, cleaning = (
        read_json(folder / "profile.json"),
        read_json(folder / "cleaning.json"),
    )
    pandas_row = timings[timings.method == "sequential"].iloc[0]
    spark_row = timings[timings.method == "spark"].iloc[0]
    results = (
        f"Spark {meta['spark']['version']}, {meta['spark']['master']}; "
        f"{profile['rows']:,} вихідних і {meta['rows']:,} очищених рядків. "
        f"Початкових партицій: {profile['initial_partitions']}; "
        f"після очищення: {meta['prepared_partitions']}. "
        "Кількості виключених рядків Spark та pandas збіглися для кожної причини.\n\n"
        + markdown_table(
            pd.DataFrame(
                list(cleaning["spark"]["excluded"].items()),
                columns=["Причина", "Виключено"],
            )
        )
        + "\n\nОкремі етапи (не входять у прогріті заміри):\n\n"
        + markdown_table(
            pd.DataFrame(
                [(k, v) for k, v in meta.items() if k.endswith("_seconds")],
                columns=["Етап", "Час, с"],
            )
        )
        + "\n\n### Партиції: два різні інтервали вимірювання\n\n"
        + markdown_table(partitions)
    )
    partition_notes = []
    for scope, data in partitions.groupby("scope"):
        best = data.loc[data.seconds.idxmin()]
        partition_notes.append(
            f"{scope}: найменша медіана при {int(best.partitions)} партиціях, {best.seconds:.4f} с."
        )
    analysis = (
        f"Еквівалентне групування: pandas {pandas_row.seconds:.4f} с; "
        f"Spark {spark_row.seconds:.4f} с; S={spark_row.speedup:.4f}. "
        + (
            "Локальний Spark повільніший за pandas у цьому вимірюванні. "
            if spark_row.speedup < 1
            else "Локальний Spark швидший за pandas у цьому вимірюванні. "
        )
        + "Набір приблизно 95 MB вміщується в пам'ять, а групування має лише кілька десятків країн. "
        "Планування Spark job, shuffle та передавання підсумку через JVM/Python можуть "
        "переважати над обчисленнями. Це не заперечує переваг Spark для даних іншого "
        "масштабу або кластера.\n\n"
        + "\n\n".join(partition_notes)
        + "\n\n"
        + "Різниця між сценаріями показує вплив перерозподілу та матеріалізації. "
        "Вимірювання з repartition починається з кешованого очищеного набору; варіант "
        "cached_partitions додатково кешує новий розподіл. Це різні межі та стани кешу, "
        "тому їх різницю не слід видавати за точну ізольовану вартість shuffle. "
        "Після певного p додаткові партиції створюють більше дрібних задач при незмінних "
        "чотирьох слотах. Вихідна кількість партицій залежить від способу читання: "
        "multiLine обробляє цей CSV як один файл. Далі dropDuplicates і groupBy "
        "використовують shuffle. Висновок стосується локального виконання, трьох повторів "
        "та зафіксованих налаштувань; оптимум може змінитися на іншій машині. "
        "Справжні Spark DataFrame і Python RDD дали еквівалентні результати; "
        "перевірені всі країни, товари та відомі клієнти."
    )
    tasks = [
        (
            "1. SparkSession",
            "Фактичні параметри сесії та локальні ресурси.",
            "display(read_json('spark_session.json'))\nprint(inspect.getsource(create_spark))",
        ),
        (
            "2. Завантаження та дослідження",
            "Spark самостійно читає CSV; схема до й після явних приведень.",
            "display(read_json('profile.json'))\ndisplay(meta['prepared_schema'])\nprint(inspect.getsource(a.load_spark))",
        ),
        (
            "3. Попередня обробка",
            "Кількості виключень повинні збігатися з незалежною pandas-реалізацією.",
            "cleaning = read_json('cleaning.json')\ndisplay(cleaning)\nassert cleaning['spark']['excluded'] == cleaning['pandas']['excluded']\nprint(inspect.getsource(a.prepare_spark))",
        ),
        (
            "4. Фільтрація та вибірка",
            "Revenue вище глобального середнього; справжні результати Spark.",
            "display(read_json('filter.json'))\ndisplay(pd.read_csv(result_dir / 'filtered_sample.csv'))",
        ),
        (
            "5. GroupBy та агрегати",
            "Усі країни, товари та відомі клієнти порівняно з pandas.",
            "print(inspect.getsource(a.group_sales))\nfor name in ['countries', 'products', 'customers']:\n    table = pd.read_csv(result_dir / f'{name}.csv')\n    display(Markdown(f'**{name}: {len(table)} груп**'))\n    display(table.sort_values('total', ascending=False).head(10))",
        ),
        (
            "6. Механізм partitions",
            "Вхідні партиції досліджуються при фіксованих local cores та shuffle partitions.",
            "display({'source_partitions': read_json('profile.json')['initial_partitions'], 'prepared_partitions': meta['prepared_partitions'], 'tested': meta['partition_values'], 'cores': meta['spark']['local_cores']})",
        ),
        (
            "7. RDD map, filter, reduce",
            "Оброблено увесь очищений DataFrame, числовий результат перевірено.",
            "print(inspect.getsource(a.rdd_demo))\ndisplay(read_json('rdd.json'))\nassert read_json('rdd.json')['verified']",
        ),
        (
            "8. Transformation, Action та lazy evaluation",
            "Фактичні Spark job до/після побудови плану та collect.",
            "lazy = read_json('lazy_evaluation.json')\ndisplay(lazy)\nassert lazy['jobs_before'] == lazy['jobs_after_transformation']\nassert len(lazy['jobs_after_collect']) > len(lazy['jobs_after_transformation'])\nprint((result_dir / 'query_plan.txt').read_text(encoding='utf-8'))",
        ),
        (
            "9. Pandas проти PySpark",
            "Однакові очищені дані та count/sum/mean за Country; прогріті рушії.",
            "display(raw)\ndisplay(timings)\ndisplay(Image(filename=str(result_dir / 'engines.png')))",
        ),
        (
            "10. Експеримент з partitions",
            "Три повтори з repartition у таймері та без нього.",
            "partition_raw = pd.read_csv(result_dir / 'partitions_raw.csv')\ndisplay(partition_raw)\ndisplay(pd.read_csv(result_dir / 'partitions.csv'))\nassert partition_raw.verified.all()\ndisplay(Image(filename=str(result_dir / 'partitions.png')))",
        ),
    ]
    build(
        "lab04",
        tasks,
        "from lab04 import algorithms as a\nfrom lab04.spark_environment import create_spark",
        results,
        analysis,
        ["engines", "partitions"],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("lab", choices=["lab01", "lab02", "lab03", "lab04", "all"])
    args = parser.parse_args()
    for name in (
        ["lab01", "lab02", "lab03", "lab04"] if args.lab == "all" else [args.lab]
    ):
        globals()[f"build_{name}"]()


if __name__ == "__main__":
    main()
