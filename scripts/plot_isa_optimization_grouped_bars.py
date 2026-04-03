#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨架构 × 编译优化等级：分组柱状图（O1/O2/O3），标星/最低标注与 90% 基线。
输出:
  docs/figures/isa_optimization_grouped_bars.{pdf,png}        英文
  docs/figures/isa_optimization_grouped_bars_zh.{pdf,png}    中文
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


def plot_grouped_bars(out_dir: Path, lang: str) -> None:
    archs = ["ARM", "RISC-V", "X86", "MIPS"]
    o1_acc = [95.09, 93.52, 92.05, 87.53]
    o2_acc = [93.40, 95.40, 93.94, 89.35]
    o3_acc = [92.35, 94.18, 93.02, 88.33]

    x = np.arange(len(archs))
    width = 0.25

    if lang == "zh":
        setup_font_chinese()
        ylabel = "准确率 (%)"
        xlabel = "指令集架构"
        title = "编译优化对符号恢复准确率的影响"
        legend_title = "优化等级"
        baseline_txt = "90% 参考线"
        stem = out_dir / "isa_optimization_grouped_bars_zh"
    else:
        setup_font_english()
        ylabel = "Accuracy (%)"
        xlabel = "Architecture"
        title = "Impact of Compiler Optimization on Symbol Recovery Accuracy"
        legend_title = "Opt. Level"
        baseline_txt = "90% baseline"
        stem = out_dir / "isa_optimization_grouped_bars"

    fig, ax = plt.subplots(figsize=(8, 5))

    colors = ["#1f78b4", "#ff7f00", "#33a02c"]
    bars1 = ax.bar(x - width, o1_acc, width, label="O1", color=colors[0], edgecolor="black", linewidth=0.5)
    bars2 = ax.bar(x, o2_acc, width, label="O2", color=colors[1], edgecolor="black", linewidth=0.5)
    bars3 = ax.bar(x + width, o3_acc, width, label="O3", color=colors[2], edgecolor="black", linewidth=0.5)

    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + 0.3,
                f"{height:.1f}",
                ha="center",
                va="bottom",
                fontsize=8,
                rotation=0,
            )

    # 全局最高 RISC-V·O2：五角星放在「柱顶数值」之上（数据坐标 +1.2%），避免与柱顶标注重叠
    ax.text(
        x[1],
        o2_acc[1] + 0.5,
        "★",
        ha="center",
        va="bottom",
        fontsize=14,
        color="red",
    )

    ax.annotate(
        "▼",
        xy=(x[3], o1_acc[3]),
        xytext=(0, -18),
        textcoords="offset points",
        ha="center",
        fontsize=12,
        color="navy",
    )

    ax.set_ylabel(ylabel, fontsize=11, fontweight="bold")
    ax.set_xlabel(xlabel, fontsize=11, fontweight="bold")
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(archs)
    ax.set_ylim(85, 97)
    ax.legend(title=legend_title, frameon=True, loc="upper right")
    ax.grid(axis="y", linestyle="--", alpha=0.3)

    ax.axhline(y=90, color="gray", linestyle=":", linewidth=1, alpha=0.5)
    ax.text(3.6, 90.2, baseline_txt, fontsize=8, color="gray")

    plt.tight_layout()
    for ext in ("pdf", "png"):
        plt.savefig(stem.with_suffix(f".{ext}"), dpi=300, bbox_inches="tight")
    plt.close()
    print(f"已保存: {stem}.pdf / .png")


def main():
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "docs" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    for lang in ("en", "zh"):
        plot_grouped_bars(out_dir, lang)
    print("完成。")


if __name__ == "__main__":
    main()
