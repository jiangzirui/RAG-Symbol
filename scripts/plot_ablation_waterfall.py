#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
反向消融：从基线到全特征的累计贡献（瀑布图）。
数据与 ablation 实验一致：CodeBERT → +Semantic → +CFG → +Statistical → Full。

输出:
  docs/figures/ablation_waterfall.{pdf,png}
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def main():
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "docs" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    steps = [
        "CodeBERT\n(Baseline)",
        "+Semantic",
        "+CFG",
        "+Statistical",
        "Full Model\n(VulPatchGuard)",
    ]
    # 各阶段累计准确率（与实验表一致）
    cumulative = np.array([8.32, 17.12, 70.36, 78.47, 95.09], dtype=float)
    # 每段高度 = 相对上一阶段的增量；首段为基线绝对值
    heights = np.diff(np.concatenate([[0.0], cumulative]))

    x = np.arange(len(steps))
    bottom = np.concatenate([[0.0], cumulative[:-1]])

    colors = ["#757575", "#D32F2F", "#1976D2", "#1976D2", "#2E7D32"]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(
        x,
        heights,
        bottom=bottom,
        color=colors,
        edgecolor="black",
        linewidth=0.5,
    )

    for i, bar in enumerate(bars):
        h = bar.get_height()
        cum_i = cumulative[i]
        # 累计值标在柱顶略上方
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            cum_i + 1.0,
            f"{cum_i:.1f}%",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )
        # 增量标在柱内（首柱为基线，不标 +）
        if i > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                bottom[i] + h / 2.0,
                f"+{h:.2f}",
                ha="center",
                va="center",
                fontsize=9,
                color="white",
            )

    ax.set_xticks(x)
    ax.set_xticklabels(steps, fontsize=10)
    ax.set_ylabel("Accuracy (%)", fontsize=12, fontweight="bold")
    ax.set_title(
        "Cumulative Feature Contribution Analysis\n(Building from Baseline to Full Model)",
        fontsize=13,
        fontweight="bold",
    )
    ax.set_ylim(0, 100)
    ax.grid(axis="y", linestyle="--", alpha=0.3)

    plt.tight_layout()
    stem = out_dir / "ablation_waterfall"
    plt.savefig(stem.with_suffix(".pdf"), dpi=300, bbox_inches="tight")
    plt.savefig(stem.with_suffix(".png"), dpi=300, bbox_inches="tight")
    plt.close()
    print(f"已保存: {stem}.pdf")
    print(f"已保存: {stem}.png")


if __name__ == "__main__":
    main()
