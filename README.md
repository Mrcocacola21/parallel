# Паралельна та розподілена обробка даних

Чотири лабораторні роботи з Python за методичними матеріалами у корені проєкту. ЛР №1 — **варіант 3**: 500 000 чисел, діапазон 1–30 000, K=200, seed=42. ЛР №2–4 використовують увесь наданий `online_retail_II.csv`.

| Робота | Дослідження | Звіт | Виконаний notebook |
|---|---|---|---|
| №1 | CPU-обчислення, ProcessPoolExecutor, 1/2/4/8 процесів | [report.md](lab01/report.md) | [lab01.ipynb](lab01/lab01.ipynb) |
| №2 | Online Retail II, Pool.starmap, коректне об'єднання агрегатів | [report.md](lab02/report.md) | [lab02.ipynb](lab02/lab02.ipynb) |
| №3 | Чотири частини, threading, ThreadPoolExecutor, asyncio, I/O та GIL | [report.md](lab03/report.md) | [lab03.ipynb](lab03/lab03.ipynb) |
| №4 | Справжні Spark DataFrame/RDD, lazy evaluation, partitions, pandas | [report.md](lab04/report.md) | [lab04.ipynb](lab04/lab04.ipynb) |

## Структура

```text
online_retail_II.csv       незмінний вихідний набір
Лаб*.pdf                  методичні матеріали
common/                   завантаження, очищення, заміри, графіки
lab01/ ... lab04/
  algorithms.py           імпортовані функції та worker
  main.py                 незалежна CLI-точка входу
  narrative.md            методика та хід роботи українською
  report.md               повний звіт із фактичними таблицями
  labXX.ipynb             виконаний notebook із результатами
  results/                CSV, JSON, PNG та SVG повних запусків
    quick/                явно відокремлені smoke-результати
tests/                    математичні, паралельні та Spark-перевірки
tools/                    генерація звітів, виконання notebook, аудит
requirements.txt          зафіксовані обчислювальні залежності
AUDIT.md                  фінальний стан і фактично виконані перевірки
REQUIREMENTS.md           відповідність кожному завданню PDF
```

## Встановлення у Windows PowerShell

Потрібні Python 3.11+ (перевірено 3.12.6), Java **17 або 21** для Spark 4.0, кілька GB вільної пам'яті та місця для залежностей. PySpark займає приблизно 435 MB завантаження і більше після розпакування. Для перших трьох робіт Java не потрібна. Дані вже наявні; повторно завантажувати їх не потрібно.

Усі команди нижче виконуйте **з кореня проєкту**. Активація середовища та зміна ExecutionPolicy не потрібні:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PYTHONIOENCODING = 'utf-8'
```

Для цього виконання `.venv` створено з `--system-site-packages`, щоб повторно використати наявні NumPy/pandas/Jupyter. PySpark 4.0.3 встановлено локально в `.venv`. Для нового комп'ютера наведений звичайний venv забезпечує ізоляцію; встановлення `requirements.txt` додає всі потрібні залежності.

## Java та PySpark

`lab04.spark_environment` знаходить сумісний JAVA_HOME, Java у PATH або JDK у типових каталогах Windows. Встановлена Java 8 з PATH не використовується для Spark 4.0. Виявлену Java 17/21 програма підключає тільки у власному процесі; системні налаштування не змінюються. Якщо автоматичний пошук не знайшов ваш JDK:

```powershell
# Підставте свій фактичний каталог JDK, який містить bin\java.exe.
.\.venv\Scripts\python.exe -m lab04.main --java-home 'D:\tools\jdk-17'
```

Версія PySpark зафіксована на **4.0.3**: 4.0.1 з Python 3.12 на Windows має відому помилку Python-worker [SPARK-53759](https://issues.apache.org/jira/browse/SPARK-53759). Потрібні Java 17/21 ([Apache Spark](https://spark.apache.org/docs/4.0.0/)). Не замінюйте локальний запуск на глобальний Python зі старим PySpark. Змінні PYSPARK_PYTHON та PYSPARK_DRIVER_PYTHON автоматично вказують на поточний Python.

Spark працює у `local[4]`, з вимкненим UI та AQE, `spark.sql.shuffle.partitions=8`. Можна змінити кількість локальних слотів: `--cores 2`. Це один комп'ютер, не багатовузловий кластер. Попередження про winutils.exe для перевірених читання/агрегацій не заважає роботі; сторонні executable не потрібні для реалізованих сценаріїв.

## Повні експерименти

Кожна команда самостійна. За замовчуванням виконуються **три повтори**, зберігаються всі часи та медіана. Запускайте роботи послідовно, щоб вони не конкурували за CPU:

```powershell
.\.venv\Scripts\python.exe -m lab01.main
.\.venv\Scripts\python.exe -m lab02.main
.\.venv\Scripts\python.exe -m lab03.main
.\.venv\Scripts\python.exe -m lab04.main
```

У №1 обчислюються всі 500 000 елементів для кожної конфігурації, без кешування функції. У №2–4 очищується весь CSV. №3 використовує рівно чотири частини; окремий Python CPU-контроль бере 40 000 значень Quantity. I/O-очікування становить 0,25 с на кожну частину, змінюється через `--io-delay`.

Опції: `--repeats 5`, `--data 'D:\дані\online_retail_II.csv'`, `--output 'D:\результати\lab02'`. Якщо змінено дані або output, автоматичний генератор стандартних звітів потребує результатів у звичайних `labXX/results/`. Вхідний CSV не змінюється.

## Швидка перевірка

```powershell
.\.venv\Scripts\python.exe -m lab01.main --quick --repeats 1
.\.venv\Scripts\python.exe -m lab02.main --quick --repeats 1
.\.venv\Scripts\python.exe -m lab03.main --quick --repeats 1
.\.venv\Scripts\python.exe -m lab04.main --quick --repeats 1
```

Швидкий режим явно скорочує №1 до 2 000 елементів, а №2–4 — до перших 20 000 вихідних рядків. K у №1 залишається 200. Результати записуються в `results/quick/` і **не використовуються у фінальних звітах**. Spark навіть у швидкому режимі потребує часу на JVM, job та shuffle.

## Перевірки

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q common lab01 lab02 lab03 lab04 tools tests
.\.venv\Scripts\python.exe -m tools.audit
```

Spark-тести запускають реальну Java-сесію й Python-worker, тому потребують сумісних Java та PySpark. Вони не підмінені mock. Окрема перевірка без Java: `python -m pytest tests/test_data.py tests/test_lab01.py tests/test_lab02.py tests/test_lab03.py -q`.

## Звіти та notebook

Після повторних повних запусків оновіть звіти й виконайте notebook:

```powershell
.\.venv\Scripts\python.exe -m tools.build_documents all
.\.venv\Scripts\python.exe -m tools.execute_notebooks lab01 lab02 lab03 lab04
.\.venv\Scripts\python.exe -m tools.audit
```

Генератор створює звіти з `narrative.md` та фактичних CSV/JSON. Notebook демонструє кожне завдання PDF, імпортовані реалізації, фактичні результати, графіки та висновки. Основні повні обчислення запускаються CLI: це забезпечує Windows spawn і не залежить від інтерактивної серіалізації notebook. Збережені outputs можна переглядати без повторення багатохвилинних експериментів. Для власних обчислень у Jupyter оберіть kernel вашого `.venv`; `tools.execute_notebooks` сам використовує Python, яким його запущено.

## Дані та методика

Початкові поля: `Invoice, StockCode, Description, Quantity, InvoiceDate, Price, Customer ID, Country`. У пам'яті перейменовано Invoice→InvoiceNo, Price→UnitPrice, Customer ID→CustomerID. Профілі містять вихідні типи та пропуски.

Джерело опису: Daqing Chen, **Online Retail II**, UCI Machine Learning Repository, DOI [10.24432/C5CG6D](https://doi.org/10.24432/C5CG6D), CC BY 4.0. Ціна одиниці вказана у фунтах стерлінгів, тому Revenue та графіки використовують GBP ([опис полів UCI](https://archive.ics.uci.edu/dataset/502/online%2Bretail%2Bii)). Аналізується наданий локальний CSV; дані не завантажувалися повторно.

Досліджуються **додатні продажі після видалення точних дублікатів**, а не фінансовий нетто-дохід з поверненнями. Скасування, Quantity≤0, UnitPrice≤0, обов'язкові пропуски й некоректні значення виключаються послідовно. У `cleaning.json` є взаємовиключні причини та баланс до/після. Відсутній CustomerID не вилучає відомий продаж; унікальні клієнти й групування клієнтів ігнорують невідомі ID. Видалення точних дублікатів є явним припущенням про повторний запис і може впливати на суму продажів.

Speedup = T_seq/T_method; Efficiency = Speedup/p×100%. Послідовний алгоритм відрізняється від пулу з одним процесом. Для №1–2 включено створення пулу та передавання даних. Для №3 порівнюються одні й ті самі підготовлені чотири частини; p=8 дає максимум чотири одночасні задачі. Asyncio використовує to_thread для синхронного аналізу та справжній asyncio.sleep для I/O. Для №4 порівнюються прогріті агрегації; startup, читання, очищення та кешування виміряні окремо. Два сценарії partitions мають явно різні межі часу.

Часи залежать від обладнання, кешу, планувальника та фонового навантаження. Три повтори дають описову оцінку, не статистичну гарантію переваги. Не всі способи повинні прискорювати аналіз: висновки будуються з фактичних вимірювань. Детальні результати й стан перевірки — у [AUDIT.md](AUDIT.md).
