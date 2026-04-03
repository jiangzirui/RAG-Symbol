#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消融：左轴准确率（柱状）+ 右轴相对全模型的性能下降（折线，不含首条 Full）。

输出:
  docs/figures/ablation_dual_axis.{pdf,png}      英文
  docs/figures/ablation_dual_axis_zh.{pdf,png}  中文
"""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


def setup_font_chinese():
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


def setup_font_english():
    mpl.rcParams["font.family"] = "sans-serif"
    mpl.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Helvetica"]


def plot_one(out_dir: Path, lang: str) -> None:
    if lang == "zh":
        setup_font_chinese()
        configs = [
            "VulPatchGuard（全特征）",
            "去除 Statistical",
            "去除 CFG",
            "去除 Statistical+CFG",
            "去除 Semantic",
            "去除 Semantic+Statistical",
            "去除 CFG+Semantic",
            "CLAP（基线）",
            "CodeBERT（基线）",
        ]
        ylabel_acc = "准确率 (%)"
        ylabel_drop = "性能下降 (%)"
        line_label = "相对下降 (%)"
        title = "消融实验：各组件重要性分析"
        stem = out_dir / "ablation_dual_axis_zh"
    else:
        setup_font_english()
        configs = [
            "VulPatchGuard (Full)",
            "w/o Statistical",
            "w/o CFG",
            "w/o Statistical+CFG",
            "w/o Semantic",
            "w/o Semantic+Statistical",
            "w/o CFG+Semantic",
            "CLAP (baseline)",
            "CodeBERT (baseline)",
        ]
        ylabel_acc = "Accuracy (%)"
        ylabel_drop = "Performance Drop (%)"
        line_label = "Relative Drop %"
        title = "Ablation Study: Component Importance Analysis"
        stem = out_dir / "ablation_dual_axis"

    accuracy = [95.09, 78.47, 70.36, 56.97, 17.12, 14.87, 13.84, 9.73, 8.32]
    colors = [
        "#2E7D32",
        "#1976D2",
        "#1976D2",
        "#90CAF9",
        "#D32F2F",
        "#EF9A9A",
        "#EF9A9A",
        "#757575",
        "#757575",
    ]
    full_acc = 95.09

    fig, ax1 = plt.subplots(figsize=(12, 6))
    x = np.arange(len(configs))
    width = 0.6

    bars = ax1.bar(
        x, accuracy, width, color=colors, edgecolor="black", linewidth=0.5
    )
    ax1.set_ylabel(ylabel_acc, fontsize=12, color="black")
    ax1.tick_params(axis="y", labelcolor="black")
    ax1.set_ylim(0, 100)

    relative_drop = [(full_acc - acc) / full_acc * 100.0 for acc in accuracy]
    ax2 = ax1.twinx()
    ax2.plot(
        x[1:],
        relative_drop[1:],
        "ro-",
        linewidth=2,
        markersize=8,
        label=line_label,
    )
    ax2.set_ylabel(ylabel_drop, fontsize=12, color="red")
    ax2.tick_params(axis="y", labelcolor="red")
    dmax = max(relative_drop[1:]) if len(relative_drop) > 1 else 100.0
    ax2.set_ylim(0, min(100.0, dmax * 1.08 + 5))

    for bar, acc in zip(bars, accuracy):
        height = bar.get_height()
        ax1.text(
            bar.get_x() + bar.get_width() / 2.0,
            height + 1.0,
            f"{acc:.1f}",
            ha="center",
            va="bottom",
            fontsize=9,
            rotation=45,
        )

    ax1.set_xticks(x)
    ax1.set_xticklabels(configs, rotation=45, ha="right", fontsize=9)
    ax1.set_title(title, fontsize=13, fontweight="bold")
    ax1.grid(axis="y", linestyle="--", alpha=0.3)

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax2.legend(h1 + h2, l1 + l2, loc="upper right", fontsize=9)

    plt.tight_layout()
    fig.savefig(stem.with_suffix(".pdf"), dpi=300, bbox_inches="tight", pad_inches=0.15)
    fig.savefig(stem.with_suffix(".png"), dpi=300, bbox_inches="tight", pad_inches=0.15)
    plt.close()
    print(f"Saved: {stem}.pdf / .png")


def main():
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "docs" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    for lang in ("en", "zh"):
        plot_one(out_dir, lang)
    print("Done.")


if __name__ == "__main__":
    main()
