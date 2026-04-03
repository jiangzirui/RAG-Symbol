#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消融实验准确率热力图：横向单行（1×N），避免纵向过长；配色为 Blues。

用法:
  python scripts/plot_ablation_accuracy_heatmap.py
输出:
  docs/figures/ablation_accuracy_heatmap_zh.{pdf,png}
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

from ablation_figure_data import ABLATION_ROWS


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
            "font.size": 9,
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

    labels = [r[0] for r in ABLATION_ROWS]
    n = len(labels)
    # 横向：1 行 × N 列，版面扁宽，观感优于细长竖条
    acc = np.array([r[1] for r in ABLATION_ROWS], dtype=float).reshape(1, n)

    # 宽 > 高；高度仅容纳一行热力格 + 下方标签与 colorbar
    fig_w = max(11.0, 0.95 * n)
    fig, ax = plt.subplots(figsize=(fig_w, 3.2))

    im = ax.imshow(acc, aspect="auto", cmap="Blues", vmin=0, vmax=100)

    ax.set_yticks([0])
    ax.set_yticklabels(["准确率 (%)"])
    ax.set_xticks(np.arange(n))
    ax.set_xticklabels(labels, fontsize=7.5, rotation=38, ha="right")

    for j in range(n):
        v = acc[0, j]
        c, tot = ABLATION_ROWS[j][2], ABLATION_ROWS[j][3]
        text_color = "white" if v > 52 else "0.12"
        ax.text(
            j,
            0,
            f"{v:.2f}%\n({c}/{tot})",
            ha="center",
            va="center",
            fontsize=6.8,
            color=text_color,
        )

    ax.set_title("消融实验准确率（热力图）  N=7781", pad=10)
    ax.set_xlim(-0.5, n - 0.5)
    ax.set_ylim(0.5, -0.5)

    cbar = fig.colorbar(
        im,
        ax=ax,
        orientation="horizontal",
        pad=0.28,
        fraction=0.09,
        aspect=28,
    )
    cbar.set_label("准确率 (%)")

    fig.tight_layout()
    stem = out_dir / "ablation_accuracy_heatmap_zh"
    for ext in ("pdf", "png"):
        fig.savefig(f"{stem}.{ext}", format=ext)
        print(f"已保存: {stem}.{ext}")
    plt.close(fig)
    print("完成。")


if __name__ == "__main__":
    main()
