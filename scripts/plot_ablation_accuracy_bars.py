#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消融与基线对比：准确率横向柱状图。
- 配色参考顶会/期刊常见风格：主方法一条深色，其余统一浅灰（非彩虹色）。
- X 轴固定为 0–100%（准确率不可能超过 100%）；数值标注放在图右外侧，不拉长横轴。

用法:
  python scripts/plot_ablation_accuracy_bars.py
输出:
  docs/figures/ablation_accuracy_bars_zh.{pdf,png}

数据见 scripts/ablation_figure_data.py 中 ABLATION_ROWS。
"""

import sys
from pathlib import Path

# 保证可 import 同目录下 ablation_figure_data
sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.transforms import blended_transform_factory

from ablation_figure_data import ABLATION_ROWS, BAR_COLOR_MAIN, BAR_COLOR_OTHER


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

    rows = ABLATION_ROWS
    labels = [r[0] for r in rows]
    acc = np.array([r[1] for r in rows], dtype=float)
    n = len(labels)
    y = np.arange(n)

    colors = [BAR_COLOR_MAIN] + [BAR_COLOR_OTHER] * (n - 1)

    fig, ax = plt.subplots(figsize=(7.4, 5.2))
    bars = ax.barh(y, acc, height=0.62, color=colors, edgecolor="0.35", linewidth=0.5)

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlabel("准确率 (%)")
    ax.set_title("消融实验与基线对比（自对比数据集，N=7781）")
    ax.set_xlim(0, 100)
    ax.grid(True, axis="x", linestyle=":", alpha=0.65)
    ax.set_axisbelow(True)

    # 标注放在坐标轴右外侧（axes x>1），不占用 0–100 的刻度区间
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
    stem = out_dir / "ablation_accuracy_bars_zh"
    for ext in ("pdf", "png"):
        fig.savefig(f"{stem}.{ext}", format=ext)
        print(f"已保存: {stem}.{ext}")
    plt.close(fig)
    print("完成。")


if __name__ == "__main__":
    main()
