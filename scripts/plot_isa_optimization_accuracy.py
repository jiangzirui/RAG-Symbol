#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨架构 × 编译优化等级下的符号恢复准确率 / 耗时作图。
- 学术风格：灰阶线条 + 线型/标记区分（IEEE/ACM 黑白印刷友好），避免高饱和多色。
用法: python scripts/plot_isa_optimization_accuracy.py
输出:
  英文: docs/figures/isa_optimization_accuracy.{pdf,png}, isa_optimization_time.{pdf,png}
  中文: docs/figures/isa_optimization_accuracy_zh.{pdf,png}, isa_optimization_time_zh.{pdf,png}
"""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

# 灰阶四档 + 线型/标记冗余（顶刊论文插图常见做法）
COLORS = {
    "ARM": "#1a1a1a",
    "RISC-V": "#4a4a4a",
    "x86": "#7a7a7a",
    "MIPS": "#a8a8a8",
}
LINESTYLES = {"ARM": "-", "RISC-V": "--", "x86": "-.", "MIPS": ":"}
MARKERS = {"ARM": "o", "RISC-V": "s", "x86": "^", "MIPS": "D"}

# 数据来自实验表：准确率(%), 正确/总数, 平均耗时(s)
DATA = {
    "ARM": {
        "N": 7781,
        "O1": (95.09, 7399, 7781, 2.68),
        "O2": (93.40, 7268, 7781, 2.76),
        "O3": (92.35, 7186, 7781, 2.84),
    },
    "RISC-V": {
        "N": 9600,
        "O1": (93.52, 8978, 9600, 3.26),
        "O2": (95.40, 9158, 9600, 3.29),
        "O3": (94.18, 9041, 9600, 3.12),
    },
    "x86": {
        "N": 8420,
        "O1": (92.05, 7751, 8420, 2.79),
        "O2": (93.94, 7910, 8420, 2.82),
        "O3": (93.02, 7832, 8420, 2.85),
    },
    "MIPS": {
        "N": 6930,
        "O1": (87.53, 6066, 6930, 2.49),
        "O2": (89.35, 6192, 6930, 2.52),
        "O3": (88.33, 6121, 6930, 2.56),
    },
}

OPTS = ["O1", "O2", "O3"]
X = np.arange(len(OPTS))


def legend_label(isa: str, n: int, lang: str) -> str:
    """图例：英文用半角括号；中文用全角括号，避免与正文混排违和。"""
    if lang == "zh":
        return f"{isa}（N={n}）"
    return f"{isa} (N={n})"


def set_legend_below_axes(fig, ax, ncol: int = 2) -> None:
    """
    将图例放在坐标轴下方居中、两列排布，不遮挡折线。
    略增高画布高度以容纳图例。
    """
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.14),
        ncol=ncol,
        framealpha=1.0,
        fontsize=9,
        columnspacing=1.2,
        handlelength=2.5,
        edgecolor="0.6",
        fancybox=False,
    )
    # 为底部图例留出空间（tight_layout 后再微调）
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.24)


def setup_base_style():
    mpl.rcParams.update(
        {
            "font.size": 10,
            "axes.labelsize": 11,
            "axes.titlesize": 12,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "axes.linewidth": 1.0,
            "lines.linewidth": 1.8,
            "lines.markersize": 7,
            "figure.dpi": 150,
            "savefig.dpi": 600,
            "savefig.bbox": "tight",
        }
    )


def setup_font_english():
    setup_base_style()
    mpl.rcParams["font.family"] = "sans-serif"
    mpl.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Helvetica"]
    mpl.rcParams["axes.unicode_minus"] = True


def setup_font_chinese():
    """Windows 常见微软雅黑 / 黑体；Linux 可装 Noto Sans CJK SC。"""
    setup_base_style()
    mpl.rcParams["font.family"] = "sans-serif"
    mpl.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "Microsoft YaHei UI",
        "SimHei",
        "PingFang SC",
        "Noto Sans CJK SC",
        "Source Han Sans SC",
        "DejaVu Sans",
    ]
    mpl.rcParams["axes.unicode_minus"] = False  # 负号用 Unicode，避免方框


def plot_accuracy(out_dir: Path, lang: str):
    """lang: 'en' | 'zh'"""
    if lang == "zh":
        setup_font_chinese()
        xlabel = "编译优化等级"
        ylabel = "准确率 (%)"
        title = "不同指令集架构与编译优化等级下的符号恢复准确率"
        suffix = "_zh"
    else:
        setup_font_english()
        xlabel = "Optimization level"
        ylabel = "Accuracy (%)"
        title = "Symbol recovery accuracy by ISA and optimization level"
        suffix = ""

    # 略增高以容纳底部图例
    fig, ax = plt.subplots(figsize=(5.2, 4.0))

    for isa, block in DATA.items():
        ys = [block[o][0] for o in OPTS]
        ax.plot(
            X,
            ys,
            color=COLORS[isa],
            linestyle=LINESTYLES[isa],
            marker=MARKERS[isa],
            label=legend_label(isa, block["N"], lang),
            clip_on=False,
        )

    ax.set_xticks(X)
    ax.set_xticklabels(OPTS)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_ylim(84, 97)
    ax.grid(True, linestyle=":", alpha=0.6)
    set_legend_below_axes(fig, ax, ncol=2)

    stem = f"isa_optimization_accuracy{suffix}"
    for ext in ("pdf", "png"):
        p = out_dir / f"{stem}.{ext}"
        fig.savefig(p, format=ext)
        print(f"已保存: {p}")
    plt.close(fig)


def plot_time(out_dir: Path, lang: str):
    if lang == "zh":
        setup_font_chinese()
        xlabel = "编译优化等级"
        ylabel = "函数平均耗时 (s)"
        title = "不同架构与优化等级下的单函数平均推理耗时"
        suffix = "_zh"
    else:
        setup_font_english()
        xlabel = "Optimization level"
        ylabel = "Avg. time per function (s)"
        title = "Average inference time per function by ISA and optimization level"
        suffix = ""

    fig, ax = plt.subplots(figsize=(5.2, 4.0))

    for isa, block in DATA.items():
        ts = [block[o][3] for o in OPTS]
        ax.plot(
            X,
            ts,
            color=COLORS[isa],
            linestyle=LINESTYLES[isa],
            marker=MARKERS[isa],
            label=legend_label(isa, block["N"], lang),
            clip_on=False,
        )

    ax.set_xticks(X)
    ax.set_xticklabels(OPTS)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_ylim(2.2, 3.5)
    ax.grid(True, linestyle=":", alpha=0.6)
    set_legend_below_axes(fig, ax, ncol=2)

    stem = f"isa_optimization_time{suffix}"
    for ext in ("pdf", "png"):
        p = out_dir / f"{stem}.{ext}"
        fig.savefig(p, format=ext)
        print(f"已保存: {p}")
    plt.close(fig)


def main():
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "docs" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    for lang in ("en", "zh"):
        plot_accuracy(out_dir, lang)
        plot_time(out_dir, lang)
    print("完成（英文 + 英文无后缀，中文为 *_zh）。")


if __name__ == "__main__":
    main()
