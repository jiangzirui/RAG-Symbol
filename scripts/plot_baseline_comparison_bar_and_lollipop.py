#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主方法 vs 基线：竖向柱状图 + 棒棒糖图（用户提供的两种版式）。

用法:
  python scripts/plot_baseline_comparison_bar_and_lollipop.py
输出:
  docs/figures/baseline_comparison_chart.{pdf,png}      英文
  docs/figures/baseline_comparison_chart_zh.{pdf,png}   中文
  docs/figures/baseline_comparison_lollipop.{pdf,png}   英文
  docs/figures/baseline_comparison_lollipop_zh.{pdf,png}中文
"""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch


def setup_font_chinese() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": [
                "Microsoft YaHei",
                "Microsoft YaHei UI",
                "SimHei",
                "Noto Sans CJK SC",
                "DejaVu Sans",
            ],
            "axes.unicode_minus": False,
        }
    )


def setup_font_english() -> None:
    mpl.rcParams["font.family"] = "sans-serif"
    mpl.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Helvetica"]


def plot_bar_chart(out_dir: Path, lang: str) -> None:
    if lang == "zh":
        setup_font_chinese()
        methods = ["VulPatchGuard\n（本文）", "VulPatchGuard\n（无 LLM）", "Finger", "Bindiff"]
        ylabel = "准确率 (%)"
        title = "与现有方法的性能对比"
        legend_elements = [
            Patch(facecolor="#2E7D32", edgecolor="black", label="本文方法（Full）"),
            Patch(facecolor="#81C784", edgecolor="black", label="消融（去除 LLM）"),
            Patch(facecolor="#757575", edgecolor="black", label="基线方法"),
        ]
        stem = out_dir / "baseline_comparison_chart_zh"
        ann1 = "+107.3%\n相对 Finger"
        ann2 = "+372.1%\n相对 Bindiff"
    else:
        setup_font_english()
        methods = ["VulPatchGuard\n(Ours)", "VulPatchGuard\n(no LLM)", "Finger", "Bindiff"]
        ylabel = "Accuracy (%)"
        title = "Performance Comparison with State-of-the-Art Methods"
        legend_elements = [
            Patch(facecolor="#2E7D32", edgecolor="black", label="Our Full Method"),
            Patch(facecolor="#81C784", edgecolor="black", label="Ablation (w/o LLM)"),
            Patch(facecolor="#757575", edgecolor="black", label="Baseline Methods"),
        ]
        stem = out_dir / "baseline_comparison_chart"
        ann1 = "+107.3%\nvs. Finger"
        ann2 = "+372.1%\nvs. Bindiff"

    accuracy = [95.09, 67.41, 45.87, 20.14]
    correct = [7399, 5245, 3569, 1567]
    total = [7781, 7781, 7781, 7781]

    colors = ["#2E7D32", "#81C784", "#757575", "#9E9E9E"]
    edge_colors = ["black", "black", "black", "black"]

    fig, ax = plt.subplots(figsize=(8, 6))

    bars = ax.bar(
        methods,
        accuracy,
        color=colors,
        edgecolor=edge_colors,
        linewidth=1.2,
        width=0.6,
        alpha=0.9,
    )

    for i, (bar, acc, cor, tot) in enumerate(zip(bars, accuracy, correct, total)):
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height + 2,
            f"{acc:.1f}%",
            ha="center",
            va="bottom",
            fontsize=11,
            fontweight="bold",
        )
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height / 2,
            f"{cor}/{tot}",
            ha="center",
            va="center",
            fontsize=9,
            color="white",
            fontweight="bold",
        )

    ax.annotate(
        "",
        xy=(0, 95.09),
        xytext=(2, 45.87),
        arrowprops=dict(arrowstyle="->", color="red", lw=2),
    )
    ax.text(
        0.5,
        70,
        ann1,
        fontsize=10,
        color="red",
        fontweight="bold",
        ha="center",
    )
    ax.text(
        0.5,
        30,
        ann2,
        fontsize=10,
        color="red",
        fontweight="bold",
        ha="center",
    )

    ax.set_ylabel(ylabel, fontsize=12, fontweight="bold")
    ax.set_title(
        title,
        fontsize=13,
        fontweight="bold",
        pad=20,
    )
    ax.set_ylim(0, 105)
    ax.grid(axis="y", linestyle="--", alpha=0.3)

    ax.legend(handles=legend_elements, loc="upper right", frameon=True)

    plt.tight_layout()
    fig.savefig(stem.with_suffix(".pdf"), dpi=300, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".png"), dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved: {stem}.pdf / .png")


def plot_lollipop(out_dir: Path, lang: str) -> None:
    if lang == "zh":
        setup_font_chinese()
        methods = ["VulPatchGuard\n（本文）", "VulPatchGuard\n（无 LLM）", "Finger", "Bindiff"]
        xlabel = "准确率 (%)"
        title = "与基线方法对比（棒棒糖图）"
        stem = out_dir / "baseline_comparison_lollipop_zh"
        best_text = "最优"
    else:
        setup_font_english()
        methods = ["VulPatchGuard\n(Ours)", "VulPatchGuard\n(no LLM)", "Finger", "Bindiff"]
        xlabel = "Accuracy (%)"
        title = "Comparison with Baseline Methods"
        stem = out_dir / "baseline_comparison_lollipop"
        best_text = "Best"

    accuracy = [95.09, 67.41, 45.87, 20.14]
    y = np.arange(len(methods))

    fig, ax = plt.subplots(figsize=(8, 5))

    markersize = 12
    ax.plot(
        accuracy,
        y,
        "o",
        markersize=markersize,
        color="#2E7D32",
        markeredgecolor="black",
        markeredgewidth=1.5,
    )
    ax.hlines(y=y, xmin=0, xmax=accuracy, color="gray", linewidth=2, alpha=0.5)

    ax.set_yticks(y)
    ax.set_yticklabels(methods)

    for i, (acc, _method) in enumerate(zip(accuracy, methods)):
        ax.text(acc + 2, i, f"{acc:.1f}%", va="center", fontsize=10, fontweight="bold")
        if i == 0:
            ax.text(
                acc - 5,
                i,
                best_text,
                va="center",
                ha="right",
                fontsize=9,
                color="white",
                fontweight="bold",
            )

    ax.set_xlabel(xlabel, fontsize=12, fontweight="bold")
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xlim(0, 100)
    ax.grid(axis="x", linestyle="--", alpha=0.3)

    plt.tight_layout()
    fig.savefig(stem.with_suffix(".pdf"), dpi=300, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".png"), dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved: {stem}.pdf / .png")


def main():
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "docs" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    for lang in ("en", "zh"):
        plot_bar_chart(out_dir, lang)
        plot_lollipop(out_dir, lang)
    print("Done.")


if __name__ == "__main__":
    main()
