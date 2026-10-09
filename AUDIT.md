# Фінальний аудит лабораторних робіт №1–4

Усі повні експерименти виконано на наданих даних; нижче — стан, підтверджений `python -m tools.audit`. Машинозчитуваний результат: [verification.json](verification.json). Повний перелік пунктів методичок: [REQUIREMENTS.md](REQUIREMENTS.md).

| Лабораторна | Вимоги PDF | Реалізація | Перевірка | Звіт і notebook |
|---|---|---|---|---|
| №1 | 9 завдань + 19 контрольних питань | Виконано | 15 замірів, усі перевірені | [Звіт](lab01/report.md), [виконаний notebook](lab01/lab01.ipynb) |
| №2 | 15 завдань | Виконано | 15 замірів, усі перевірені | [Звіт](lab02/report.md), [виконаний notebook](lab02/lab02.ipynb) |
| №3 | 10 завдань | Виконано | 48 замірів, усі перевірені | [Звіт](lab03/report.md), [виконаний notebook](lab03/lab03.ipynb) |
| №4 | 10 завдань | Виконано | 30 замірів, усі перевірені | [Звіт](lab04/report.md), [виконаний notebook](lab04/lab04.ipynb) |

## Виконані експерименти

ЛР №1: повний варіант 3 (500 000, K=200, seed=42), baseline і ProcessPoolExecutor з p=1/2/4/8, по три повтори. ЛР №2: увесь CSV, baseline і Pool.starmap з p=1/2/4/8, по три повтори. ЛР №3: увесь очищений CSV, чотири частини, шість способів для аналізу та I/O, чотири способи для окремого Python CPU-контролю, по три повтори. ЛР №4: увесь CSV; справжні Spark DataFrame і RDD, усі три групування, по три повтори pandas/Spark і восьми конфігурацій partitions (два сценарії × 1/2/4/8).

Усі чотири скорочені CLI-запуски також виконано; їх результати лежать у `results/quick/` і не підміняють повні. Після налаштування Spark роботи №1–3 повторно виконано послідовно з `.venv`, щоб усунути перетин із первинною конфігурацією середовища.

## Фактично виконані команди

Команди наведено з кореня проєкту. Перші перевірки №1–3 виконувались глобальним Python; остаточні повні заміри та загальні перевірки — Python з `.venv`.

```powershell
python -m venv --system-site-packages .venv
.\.venv\Scripts\python.exe -m pip install pyspark==4.0.3
.\.venv\Scripts\python.exe -m lab01.main
.\.venv\Scripts\python.exe -m lab02.main
.\.venv\Scripts\python.exe -m lab03.main
.\.venv\Scripts\python.exe -m lab04.main
# Smoke-команди №1–3 спочатку виконано через глобальний python; №4 — через .venv.
python -m lab01.main --quick --repeats 1
python -m lab02.main --quick --repeats 1
python -m lab03.main --quick --repeats 1
.\.venv\Scripts\python.exe -m lab04.main --quick --repeats 1
.\.venv\Scripts\python.exe -m pytest -q --junitxml=.work/verification/pytest.xml
.\.venv\Scripts\python.exe -m compileall -q common lab01 lab02 lab03 lab04 tools tests
.\.venv\Scripts\python.exe -m tools.build_documents all
.\.venv\Scripts\python.exe -m tools.execute_notebooks lab01 lab02 lab03 lab04
python -m ruff check common lab01 lab02 lab03 lab04 tools tests
python -m ruff format --check common lab01 lab02 lab03 lab04 tools tests
.\.venv\Scripts\python.exe -m tools.audit
```

## Перевірки

Pytest: **24 пройдено**, помилок 0, невдалих 0, пропущених 0. JUnit-результат збережено локально у `.work/verification/pytest.xml`.

Перевірено формулу, довжину й порядок масивів, Windows spawn, 1/2/4/8 процесів, нерівні й порожні частини, зважені середні, union множин, передачу винятків, справжні Spark DataFrame/RDD, усі групування і партиції. Аудит додатково перераховує медіани/Speedup/Efficiency з raw CSV, перевіряє виконані notebook без error cells, всі посилання звітів, цілісність PNG/SVG та узгодженість робіт №2–4.

## Незмінність даних

Файл `online_retail_II.csv`, 94,850,204 bytes. SHA-256:

`32569a66f3842a82b0d8c4d63b263c5d98a76bde5d1f65c6c01bf457e541d3a9`

Відбиток збігається з метаданими всіх трьох робіт із CSV. Вихідних рядків 1 067 371, очищених 1 007 913; причини виключення збігаються між pandas та Spark.

## Створені файли та результати

Створено `common/`, модулі/CLI/narrative/report/notebook у кожній `labXX/`, `tests/`, `tools/`, README, REQUIREMENTS, AUDIT, requirements, pyproject, .gitignore та verification.json. Кожна `results/` містить timings_raw.csv, timings.csv, metadata.json і графіки PNG/SVG. Додатково №1 має повний values.npy; №2 — профіль, очищення, агрегати і Top-10; №3 — статистики чотирьох частин; №4 — всі групи, RDD, job IDs, query plan та partitions CSV. Виконані notebook містять таблиці, код і вбудовані зображення.

## Межі висновків

Перевірено Windows 11, Python 3.12.6, 16 логічних CPU, Spark 4.0.3 та локальні чотири слоти. Виконання на багатовузловому кластері та інших ОС не досліджувалося. Три повтори — описова оцінка, час залежить від кешів і фонового навантаження. I/O — контрольована модель sleep, asyncio.to_thread — гібрид із потоками. Очищення досліджує додатні продажі, не нетто-потік із поверненнями. Точні дублікати вилучено за явним припущенням. Попередження winutils.exe лишається, але не завадило жодному реалізованому Spark-завданню. Незавершених перевірок в межах заданих чотирьох лабораторних не залишилося.
