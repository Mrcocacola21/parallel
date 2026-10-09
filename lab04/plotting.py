"""Графіки Spark з можливістю перебудови без повторення замірів."""

from pathlib import Path

import pandas as pd

from common.plotting import COLORS, plt, save_figure


def save_plots(
    summary: pd.DataFrame, partitions: pd.DataFrame, output: Path, cores: int
) -> None:
    figure, axis = plt.subplots(figsize=(9, 5.6), layout="constrained")
    labels = {
        "cached_partitions": "Кешовані партиції; без repartition",
        "with_repartition": "З repartition і shuffle",
    }
    for (scope, data), color in zip(partitions.groupby("scope"), COLORS):
        axis.plot(data.partitions, data.seconds, "o-", color=color, label=labels[scope])
    axis.set(
        xlabel="Кількість вхідних партицій",
        ylabel="Медіанний час, с",
        title="ЛР №4 · Партиції та накладні витрати Spark",
    )
    axis.set_xticks([1, 2, 4, 8])
    axis.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), frameon=False)
    save_figure(figure, output, "partitions")
    figure, axis = plt.subplots(figsize=(8, 4.8), layout="constrained")
    bars = axis.bar(
        ["Pandas", f"Spark local[{cores}]"], summary.seconds, color=COLORS[:2]
    )
    axis.bar_label(bars, fmt="%.4f с", padding=5)
    axis.set(ylabel="Медіанний час, с", title="ЛР №4 · Однакове групування за країнами")
    axis.set_ylim(0, summary.seconds.max() * 1.22)
    save_figure(figure, output, "engines")
