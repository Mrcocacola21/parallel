"""Узгоджений стиль графіків українською мовою."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

COLORS = ["#246A73", "#B85C38", "#6D597A", "#507C45"]
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titleweight": "bold",
        "axes.grid": True,
        "grid.alpha": 0.18,
        "figure.dpi": 120,
        "savefig.dpi": 220,
    }
)


def save_figure(figure: plt.Figure, output: Path, name: str) -> None:
    output.mkdir(parents=True, exist_ok=True)
    figure.savefig(output / f"{name}.png", bbox_inches="tight")
    figure.savefig(output / f"{name}.svg", bbox_inches="tight")
    plt.close(figure)


def scaling_plots(summary: pd.DataFrame, output: Path, title: str) -> None:
    parallel = summary.loc[summary.method != "sequential"]
    baseline = summary.loc[summary.method == "sequential", "seconds"].iloc[0]
    for field, ylabel, name in [
        ("seconds", "Час виконання, с", "time"),
        ("speedup", "Прискорення, разів", "speedup"),
        ("efficiency_pct", "Ефективність, %", "efficiency"),
    ]:
        figure, axis = plt.subplots(figsize=(8.5, 4.8), layout="constrained")
        axis.plot(
            parallel.workers,
            parallel[field],
            "o-",
            color=COLORS[0],
            label="Вимірювання",
        )
        if field == "seconds":
            axis.axhline(
                baseline, color=COLORS[1], linestyle="--", label="Послідовний алгоритм"
            )
        elif field == "speedup":
            axis.plot(
                parallel.workers,
                parallel.workers,
                "--",
                color=COLORS[1],
                label="Ідеальне S = p",
            )
        else:
            axis.axhline(100, color=COLORS[1], linestyle="--", label="Ідеальні 100 %")
        axis.set(xlabel="Кількість процесів", ylabel=ylabel, title=title)
        axis.set_xticks(parallel.workers)
        axis.legend()
        save_figure(figure, output, name)


def comparison_plot(
    summary: pd.DataFrame, output: Path, workload: str, title: str
) -> None:
    data = summary.loc[summary.workload == workload]
    labels = [f"{row.method}\np={row.workers}" for row in data.itertuples()]
    figure, axes = plt.subplots(1, 2, figsize=(13, 5.2), layout="constrained")
    for axis, field, ylabel in zip(
        axes, ["seconds", "speedup"], ["Час виконання, с", "Прискорення, разів"]
    ):
        bars = axis.bar(range(len(data)), data[field], color=COLORS[0], width=0.65)
        axis.set_xticks(range(len(data)), labels, rotation=28, ha="right", fontsize=9)
        axis.set_ylabel(ylabel)
        axis.set_ylim(0, max(data[field]) * 1.23)
        axis.bar_label(bars, fmt="%.3f", fontsize=9, padding=3)
    figure.suptitle(title, weight="bold")
    save_figure(figure, output, workload)
