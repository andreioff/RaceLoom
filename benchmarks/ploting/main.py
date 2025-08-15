# mypy: ignore-errors
import sys
from typing import Tuple

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

from cli import CLIError, ScenarioType, getCLIArgs
from util import safe_lookup_func, save_figure, timeFormatter


def printAndExit(msg: str) -> None:
    print(msg)
    sys.exit()


def get_diameter_dict():
    df = pd.read_csv("./plotdata/diameters.csv")
    diameters: dict[str, int] = {}
    for row in df.itertuples(index=True, name="Row"):
        diameters[row.name] = row.diameter
    return diameters


def extract_switch_non_det_branches(branches: str) -> int:
    splitB = branches.split(";")
    for s in splitB:
        if s.lower().find("sw") == -1:
            continue
        return int(s.split(":")[1])
    return -1


def get_csv_df(filePath):
    df = pd.read_csv(filePath)
    # extract network name
    df["networkName"] = df["sdnModelFile"].astype(str).str.split("_").str[2]

    diDict = get_diameter_dict()

    df["diameter"] = df["networkName"].apply(safe_lookup_func(diDict))
    df["swBranches"] = df["modelBranchCounts"].apply(extract_switch_non_det_branches)

    df["pythonTime"] = (
        df["traceAnalyzerExecTime"]
        - df["katchExecTime"]
        + df["tracesGenTime"]
        - df["maudeExecTime"]
    )

    df = df.sort_values(by="diameter", ascending=True).reset_index()
    return df


def plot_xy(
    x_values,
    y_values,
    figsize: Tuple[float, float] = (8, 6),
    title: str = "plot",
    x_label: str = "X-axis",
    y_label: str = "Y-axis",
    xLabelCount: int = 0,
    yLabelCount: int = 0,
) -> Figure:
    if len(x_values) != len(y_values):
        raise ValueError("Both input lists must have the same length.")

    fig, ax = plt.subplots(figsize=figsize)

    if xLabelCount > 0:
        ax.xaxis.set_major_locator(MaxNLocator(nbins=xLabelCount))
    if yLabelCount > 0:
        ax.yaxis.set_major_locator(MaxNLocator(nbins=yLabelCount))

    ax.plot(x_values, y_values, marker="o", linestyle="-", color="b")

    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.grid(True)
    fig.tight_layout()
    return fig


def bar_plot_exec_time(
    df,
    xTickLabels: pd.DataFrame,
    xTickIndicies: pd.DataFrame | None = None,
    xLabel="X axis",
    title="Title",
    figsize: Tuple[float, float] = (16, 7),
    barWidth: float = 0.8,
) -> Figure:
    if xTickIndicies is None:
        xTickIndicies = df.index

    x_positions = df.index

    fig, ax = plt.subplots(figsize=figsize)
    ax.yaxis.set_major_formatter(timeFormatter)

    ax.bar(
        x_positions, df["katchExecTime"], color="skyblue", label="KATch", width=barWidth
    )
    ax.bar(
        x_positions,
        df["maudeExecTime"],
        bottom=df["katchExecTime"],
        color="orange",
        label="Maude",
        width=barWidth,
    )
    ax.bar(
        x_positions,
        df["pythonTime"],
        bottom=df["maudeExecTime"] + df["katchExecTime"],
        color="red",
        label="Python",
        width=barWidth,
    )

    ax.set_xticks(xTickIndicies)
    ax.set_xticklabels(xTickLabels, rotation=45)

    # Labels and legend
    ax.set_xlabel(xLabel)
    ax.set_ylabel("Execution Time (mm:ss)")
    ax.set_title(title)
    ax.legend()

    fig.tight_layout()
    return fig


def shaded_line_plot_exec_time(
    df,
    xTickLabels: pd.DataFrame,
    xTickIndicies: pd.DataFrame | None = None,
    xLabel="X axis",
    title="Title",
) -> Figure:
    plt.rcParams.update({"font.size": 7})  # Apply smaller font size globally

    if xTickIndicies is None:
        xTickIndicies = df.index
    # Create index for X-axis (e.g., task number)
    x = df.index
    # Plot
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.yaxis.set_major_formatter(timeFormatter)

    fromSum, toSum = 0, df["katchExecTime"]
    ax.fill_between(x, fromSum, toSum, color="skyblue", label="KATch")

    fromSum, toSum = toSum, (toSum + df["maudeExecTime"])
    ax.fill_between(x, fromSum, toSum, color="orange", label="Maude")

    fromSum, toSum = toSum, (toSum + df["pythonTime"])
    ax.fill_between(x, fromSum, toSum, color="red", label="Python")

    # Optionally draw total time line
    ax.plot(x, toSum, color="black", linewidth=0.5, label="Total Time")

    ax.set_xticks(xTickIndicies)
    ax.set_xticklabels(xTickLabels, rotation=45)

    # Labels and legend
    ax.set_xlabel(xLabel)
    ax.set_ylabel("Execution Time (mm:ss)")
    ax.set_title(title)
    ax.legend()

    fig.tight_layout()
    plt.rcdefaults()  # reset font back
    return fig


def diameter_vs_non_det_branches_plot(df) -> Figure:
    return plot_xy(
        df["diameter"],
        df["swBranches"],
        (8, 6),
        "Diameter VS Non-Det Branches of Data Plane Expression",
        "diameter",
        "Non-Det Branches of Data Plane Expression",
    )


def scenario1_1sw_1ct(df):
    uniqueConsecutive = df[df["diameter"] != df["diameter"].shift()]
    uniqueConsecutive = uniqueConsecutive[
        # fmt: off
        uniqueConsecutive["diameter"].isin([
            2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
            # 17,
            18, 24, 32, 59,
        ])
        # fmt: on
    ]
    swBranches = df["swBranches"][uniqueConsecutive.index]
    xAxisLabels = list(zip(uniqueConsecutive["diameter"], swBranches))
    return shaded_line_plot_exec_time(
        df,
        # uniqueConsecutive["diameter"],
        xAxisLabels,
        xTickIndicies=uniqueConsecutive.index,
        xLabel="(Diameter, Non-Det Branches of Data Plane)",
        title="Execution Time Per Diameter/Non-Det Branches of Data Plane",
    )


def scenario1_katch_calls_per_diameter(df):
    return plot_xy(
        df["diameter"],
        df["katchCacheMisses"],
        figsize=(5, 3),
        title="No. of KATch Calls Per Diameter",
        x_label="Diameter",
        y_label="No. of KATch Calls",
        xLabelCount=14,
        yLabelCount=10,
    )


def scenario2_1sw_2ct_until_diameter_8(df):
    xAxisLabels = list(zip(df["diameter"], df["swBranches"]))
    return bar_plot_exec_time(
        df,
        xAxisLabels,
        xLabel="(Diameter, Non-Det Branches of Data Plane)",
        title="Execution Time Per\nDiameter/Non-Det Branches of Data Plane",
        figsize=(4.5, 5),
        barWidth=0.6,
    )


def scenario2_1sw_2ct_diameter_9_and_10(df):
    xAxisLabels = list(zip(df["diameter"], df["swBranches"]))
    return bar_plot_exec_time(
        df,
        xAxisLabels,
        xLabel="(Diameter, Non-Det Branches of Data Plane)",
        title="Execution Time Per\nDiameter/Non-Det Branches of Data Plane",
        figsize=(4.5, 5),
        barWidth=0.4,
    )


def branches_scenario1_1sw_1ct(df):
    uniqueConsecutive = df[df["diameter"] != df["diameter"].shift()]
    uniqueConsecutive = uniqueConsecutive[
        # fmt: off
        uniqueConsecutive["diameter"].isin([
            2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 17, 18, 24, 32, 59,
        ])
        # fmt: on
    ]
    return shaded_line_plot_exec_time(
        df,
        uniqueConsecutive["swBranches"],
        xTickIndicies=uniqueConsecutive.index,
        xLabel="Non-Det Branches of The Data Plane",
        title="Execution Time Per Non-Det Branches Count",
    )


def branches_scenario2_1sw_2ct_until_diameter_8(df):
    dfNew = df.iloc[:-2]
    return bar_plot_exec_time(
        dfNew,
        dfNew["swBranches"],
        xLabel="Non-Det Branches of The Data Plane",
        title="Execution Time Per Non-Det Branches Count",
        figsize=(6, 7),
        barWidth=0.6,
    )


def branches_scenario2_1sw_2ct_diameter_9_and_10(df):
    dfNew = df.copy().iloc[-2:]
    return bar_plot_exec_time(
        dfNew,
        dfNew["swBranches"],
        xLabel="Non-Det Branches of The Data Plane",
        title="Execution Time Per Non-Det Branches Count",
        figsize=(5, 7),
        barWidth=0.4,
    )


def main() -> None:
    try:
        args = getCLIArgs()

        df = get_csv_df(args.statsFile)

        figures = []
        if args.scenarioType == ScenarioType.S1:
            figures = [
                (scenario1_1sw_1ct(df), "execution_time"),
                (scenario1_katch_calls_per_diameter(df), "katch_calls"),
            ]
        elif args.scenarioType == ScenarioType.S2:
            df1 = df.copy().iloc[:-2]
            df2 = df.copy().iloc[-2:]
            figures = [
                (
                    scenario2_1sw_2ct_until_diameter_8(df1),
                    "scenario2_1sw_2ct_until_diameter_8",
                ),
                (
                    scenario2_1sw_2ct_diameter_9_and_10(df2),
                    "scenario2_1sw_2ct_diameter_9_and_10",
                ),
            ]
        elif args.scenarioType == ScenarioType.S2_SUBSET:
            figures = [
                (
                    scenario2_1sw_2ct_until_diameter_8(df),
                    "scenario2_1sw_2ct_until_diameter_8",
                )
            ]
        for fig, title in figures:
            save_figure(fig, title, args.outputDir)

    except CLIError as e:
        printAndExit(e.__str__())


if __name__ == "__main__":
    main()
