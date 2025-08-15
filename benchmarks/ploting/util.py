# mypy: ignore-errors
import os
from typing import Callable

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter


def seconds_to_mmss(x, pos):
    minutes = int(x) // 60
    seconds = int(x) % 60
    return f"{minutes}:{seconds:02d}"


timeFormatter = FuncFormatter(seconds_to_mmss)


def save_figure(fig: Figure, title: str, outputDir: str) -> None:
    fig.savefig(f"{outputDir}/{title}.png", dpi=300)
    plt.close(fig)


def safe_lookup_func(d: dict[str, int]) -> Callable[[str], int]:
    def safe_lookup(key: str):
        if key not in d:
            raise KeyError(f"Key '{key}' not found in diameters dictionary!")
        return d[key]

    return safe_lookup


def compare_exec_time(
    df1, df2, labelPref1: str, labelPref2: str, limitXLabels: bool = False
) -> None:
    # Create index for X-axis (e.g., task number)
    x = df1.index

    # Plot
    fig, ax = plt.subplots(figsize=(15, 6))
    ax.yaxis.set_major_formatter(timeFormatter)
    total1 = df1["katchExecTime"] + df1["maudeExecTime"] + df1["pythonTime"]
    total2 = df2["katchExecTime"] + df2["maudeExecTime"] + df2["pythonTime"]

    # Optionally draw total time line
    ax.plot(x, total1, color="blue", label=(labelPref1 + " Total Exec Time"))
    ax.plot(x, total2, color="red", label=(labelPref2 + " Total Exec Time"))

    ax.set_xticks(x)
    ax.set_xticklabels(df1["diameter"])
    if limitXLabels:
        # Select rows where the current value is different from the previous one
        uniqueConsecutive = df1[df1["diameter"] != df1["diameter"].shift()]
        uniqueConsecutive = uniqueConsecutive[
            # fmt: off
            uniqueConsecutive["diameter"].isin([
                2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 17, 18, 24, 32, 59,
            ])
            # fmt: on
        ]
        ax.set_xticks(x[uniqueConsecutive.index])
        ax.set_xticklabels(uniqueConsecutive["diameter"], rotation=45)

    # Labels and legend
    ax.set_xlabel("Diameter")
    ax.set_ylabel("Computation Time (mm:ss)")
    ax.set_title("Computation Time Per Diameter")
    ax.legend()

    plt.tight_layout()
    plt.show()
