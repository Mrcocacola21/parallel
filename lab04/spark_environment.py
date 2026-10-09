"""Локальна конфігурація Spark; системні змінні не змінюються."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from pyspark.sql import SparkSession


def java_version(home: Path) -> int | None:
    executable = home / "bin" / ("java.exe" if os.name == "nt" else "java")
    if not executable.is_file():
        return None
    result = subprocess.run(
        [str(executable), "-version"],
        capture_output=True,
        text=True,
        timeout=15,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    match = re.search(r'version "(\d+)', result.stderr + result.stdout)
    return int(match.group(1)) if match else None


def configure_java(explicit: Path | None = None) -> Path:
    if explicit is not None:
        if java_version(explicit) not in (17, 21):
            raise RuntimeError("Для Spark 4.0 потрібна Java 17 або 21.")
        os.environ["JAVA_HOME"] = str(explicit.resolve())
        return explicit.resolve()
    candidates = []
    if os.environ.get("JAVA_HOME"):
        candidates.append(Path(os.environ["JAVA_HOME"]))
    executable = shutil.which("java")
    if executable:
        candidates.append(Path(executable).resolve().parents[1])
    if os.name == "nt":
        for root in [
            Path(os.environ.get("ProgramFiles", "C:/Program Files"))
            / "Eclipse Adoptium",
            Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Java",
            Path.home() / ".jdks",
        ]:
            if root.exists():
                candidates.extend(sorted(root.iterdir()))
    for candidate in candidates:
        if java_version(candidate) in (17, 21):
            os.environ["JAVA_HOME"] = str(candidate)
            return candidate
    raise RuntimeError(
        "Java 17/21 не знайдено. Встановіть JDK та задайте --java-home або JAVA_HOME."
    )


def create_spark(cores: int = 4, java_home: Path | None = None) -> SparkSession:
    if cores < 1:
        raise ValueError("Кількість ядер має бути додатною.")
    configure_java(java_home)
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    os.environ.setdefault("SPARK_LOCAL_IP", "127.0.0.1")
    spark = (
        SparkSession.builder.appName("OnlineRetailII-Lab04")
        .master(f"local[{cores}]")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.ui.enabled", "false")
        .config("spark.ui.showConsoleProgress", "false")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.sql.adaptive.enabled", "false")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.python.worker.faulthandler.enabled", "true")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    return spark
