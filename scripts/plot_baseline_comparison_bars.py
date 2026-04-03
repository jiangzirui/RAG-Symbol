#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
表 5.6 主方法与基线对比：横向柱状图（学术风格，横轴 0–100%）。
用法:
  python scripts/plot_baseline_comparison_bars.py
输出:
  docs/figures/baseline_comparison_bars_zh.{pdf,png}
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.transforms import blended_transform_factory

from ablation_figure_data import (
    BASELINE_COMPARISON_ROWS,
    BAR_COLOR_MAIN,
    BAR_COLOR_OTHER,
    BAR_COLOR_OURS_VARIANT,
)


def setup_font_chinese():
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": [
                "Microsoft YaHei",
                "Microsoft YaHei UI",
                "SimHei",
                "Noto Sans CJK SC",
                "Source Han Sans SC",
                "DejaVu Sans",
            ],
            "font.size": 9,
            "axes.labelsize": 11,
            "axes.titlesize": 12,
            "axes.unicode_minus": False,
            "figure.dpi": 150,
            "savefig.dpi": 600,
            "savefig.bbox": "tight",
        }
    )


def main():
    setup_font_chinese()
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "docs" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = BASELINE_COMPARISON_ROWS
    labels = [r[0] for r in rows]
    acc = np.array([r[1] for r in rows], dtype=float)
    n = len(labels)
    y = np.arange(n)

    # 主方法 / 本文变体 / 外部基线
    colors = [
        BAR_COLOR_MAIN,
        BAR_COLOR_OURS_VARIANT,
        BAR_COLOR_OTHER,
        BAR_COLOR_OTHER,
    ]

    fig, ax = plt.subplots(figsize=(6.8, 3.4))
    bars = ax.barh(y, acc, height=0.58, color=colors, edgecolor="0.35", linewidth=0.5)

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("准确率 (%)")
    ax.set_title("主方法与基线对比（自对比数据集，N=7781）")
    ax.set_xlim(0, 100)
    ax.grid(True, axis="x", linestyle=":", alpha=0.65)
    ax.set_axisbelow(True)

    trans = blended_transform_factory(ax.transAxes, ax.transData)
    for bar, v, row in zip(bars, acc, rows):
        c, tot = row[2], row[3]
        txt = f"{v:.2f}%  ({c}/{tot})"
        yc = bar.get_y() + bar.get_height() / 2
        ax.text(
            1.01,
            yc,
            txt,
            transform=trans,
            ha="left",
            va="center",
            fontsize=7.0,
            color="0.15",
            clip_on=False,
        )

    fig.tight_layout()
    fig.subplots_adjust(right=0.72)
    stem = out_dir / "baseline_comparison_bars_zh"
    for ext in ("pdf", "png"):
        fig.savefig(f"{stem}.{ext}", format=ext)
        print(f"已保存: {stem}.{ext}")
    plt.close(fig)
    print("完成。")


if __name__ == "__main__":
    main()
