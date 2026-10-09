# Відповідність методичним матеріалам

Прочитано всі сторінки чотирьох PDF, таблицю варіантів, формули та контрольні питання. Нижче наведено зіставлення кожного пронумерованого завдання. Кожен рядок також має окремий розділ у відповідному notebook та опис у звіті.

| PDF / пункт | Реалізація | Артефакт / перевірка |
|---|---|---|
| №1 / 1. Генерація | `lab01.main`: Random(42), N=500000, 1–30000, K=200 | `lab01/results/metadata.json`, контроль перших значень у notebook |
| №1 / 2. Послідовний алгоритм | `lab01.algorithms.process_value`, `sequential_processing` | `function_check.csv`, `tests/test_lab01.py` |
| №1 / 3. Час baseline | `timed(sequential_processing)` | `timings_raw.csv`, окрема method=sequential |
| №1 / 4. Розподіл | `split_data`; приклад 5 частин; експеримент 4p задач | `split_demo.json`, нерівні й порожні частини у тестах |
| №1 / 5. Паралельний алгоритм | ProcessPoolExecutor, spawn, map зі збереженням порядку | `parallel_processing`, перевірки 1/2/4/8 процесів |
| №1 / 6. Різна кількість процесів | p=1,2,4,8, 3 повтори | `timings_raw.csv` |
| №1 / 7. Продуктивність | Медіана, Speedup, Efficiency | `timings.csv`, `tests/test_data.py` |
| №1 / 8. Правильність | Перевірка довжини та isclose кожного елемента | `values.npy`, verified усіх вимірювань |
| №1 / 9. Графіки | Час, прискорення з S=p, ефективність | `time`, `speedup`, `efficiency` у PNG/SVG |
| №1 / 19 контрольних питань | Відповіді на кожне питання українською | `lab01/report.md`, остання секція notebook |
| №2 / 1. Завантаження | `common.data_loader.load_retail` | SHA-256, джерело не перезаписується |
| №2 / 2. Первинний аналіз | Рядки, стовпці, імена, типи, пропуски, дублікати | `lab02/results/profile.json` |
| №2 / 3. Підготовка | Description/CustomerID, дата, Quantity/UnitPrice, скасування | `cleaning.json`, баланс причин; `tests/test_data.py` |
| №2 / 4. Revenue | Quantity×UnitPrice після очищення | `prepared_sample.csv`, перевірка у notebook |
| №2 / 5. Фільтрація | Єдине глобальне середнє, count/percentage/sum | `filter.json` |
| №2 / 6. Групування | Country: count/sum/mean | `countries.csv` |
| №2 / 7. Top-N | Top-10 за виручкою, стабільне правило рівності | `top10.csv`, `top10.png` |
| №2 / 8. Функція та baseline | `process_chunk`: count/sum/mean/min/max/groups | `statistics.json`, method=sequential |
| №2 / 9. Розподіл DataFrame | `split_frame`, зокрема p=4 | Нерівні та порожні частини у тестах |
| №2 / 10. Pool | `multiprocessing` spawn Pool і starmap | `parallel_processing`; тести 1/2/4/8 |
| №2 / 11. Об'єднання | Суми, кількості, min/max, зважені mean, країни | `merge_results`; тест нерівних розмірів |
| №2 / 12. Правильність | Усі скалярні показники, країни та Top-10 | `assert_equivalent`, verified у всіх запусках |
| №2 / 13. Продуктивність | p=1,2,4,8, 3 повтори, CPU у метаданих | `timings_raw.csv`, `timings.csv` |
| №2 / 14. Графіки | Час, Speedup, Efficiency | PNG/SVG з фактичних CSV |
| №2 / 15. Оптимум | Мінімальний час пулу, ефективність, порівняння baseline | `metadata.json`, аналіз `report.md` |
| №3 / 1. Підготовка | Той самий CSV/очищення, datetime, Revenue | `lab03/results/profile.json`, `cleaning.json` |
| №3 / 2. Функція | `analyze_chunk`: 6 потрібних показників | `statistics.json`, `chunks.json` |
| №3 / 3. Частини | Рівно 4 незалежні частини | `metadata.json`: chunk_sizes |
| №3 / 4. Послідовний алгоритм | Аналіз 4 частин і злиття; perf_counter | workload=analysis, method=sequential |
| №3 / 5. threading | По Thread на частину, start/join, Future для винятків | `threading_processing`, перевірка передачі помилок |
| №3 / 6. ThreadPoolExecutor | Workers=2,4,8 | `timings.csv`, корисне p≤4 |
| №3 / 7. Asyncio | create_task, gather, to_thread | `async_processing`, реальне await, тести результатів/винятків |
| №3 / 8. I/O | time.sleep проти asyncio.sleep; однакова затримка + аналіз | workload=io, `io.png`, io_delay у metadata |
| №3 / 9. Показники | Окремий baseline кожного навантаження, явний p | `timings.csv`, додатковий workload=python_cpu |
| №3 / 10. Аналіз | GIL, I/O, межа 4 задач, union ID, зважені ціни | `analysis.png`, `python_cpu.png`, `report.md` |
| №4 / 1. SparkSession | Java 17/21, локальний Spark 4.0.3, параметри | `spark_session.json`, справжня Spark fixture у тестах |
| №4 / 2. Завантаження | Spark CSV reader, кількості, схеми, пропуски | `lab04/results/profile.json`, metadata.prepared_schema |
| №4 / 3. Очищення | Spark cast/timestamp/filter/dropDuplicates/Revenue | `cleaning.json`, кількості причин збігаються з pandas |
| №4 / 4. Фільтрація/select | Revenue>глобальне середнє, вибрані стовпці | `filter.json`, `filtered_sample.csv`; перевірка pandas |
| №4 / 5. GroupBy | Country/StockCode/CustomerID, count/sum/mean | `countries.csv`, `products.csv`, `customers.csv`; перевірені всі групи |
| №4 / 6. Частини | Початкові партиції, repartition 1/2/4/8 | profile/metadata, getNumPartitions; AQE вимкнено |
| №4 / 7. RDD | DataFrame.rdd.map.filter.reduce на всьому очищеному наборі | `rdd.json`, незалежна перевірка DataFrame |
| №4 / 8. Lazy evaluation | Transformation проти Action; реальні job ID | `query_plan.txt`, `lazy_evaluation.json` |
| №4 / 9. Pandas/Spark | Однакові правила, дані, Country count/sum/mean | `timings.csv`, `engines.png`, rtol=1e-9/atol=1e-8 |
| №4 / 10. Експеримент | 1/2/4/8 partitions, 3 повтори, з/без repartition у часі | `partitions_raw.csv`, `partitions.csv`, `partitions.png` |

Спільні вимоги: українські звіти й підписи; англійські ідентифікатори; pathlib; CLI; незалежні модулі; Windows spawn; явні помилки; реальні perf_counter; окремі етапи та метадані; PNG/SVG; виконані notebook; модульні й інтеграційні тести. Конкретний стан виконання і кількість пройдених перевірок наведено у [AUDIT.md](AUDIT.md).
