#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消融：相对全特征的准确率与降幅（水平柱状图 + 全特征参考线）。

与论文常用版一致：横轴 0–100；柱右准确率、柱内白字降幅。
柱较宽时降幅靠柱右内侧；柱很窄时降幅改在柱几何中心并略缩小字号，避免与 y 轴重叠。
参考线处标注 Full。

输出:
  docs/figures/ablation_horizontal_degradation.{pdf,png}      英文
  docs/figures/ablation_horizontal_degradation_zh.{pdf,png}  中文
"""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt


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


# 柱宽小于此值时，不用「柱右内侧」排版，改为柱中心 + 略小字号
DROP_INNER_MIN_WIDTH = 28.0


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
        xlabel = "准确率 (%)"
        title = (
            "消融实验：各特征贡献\n"
            "（相对 VulPatchGuard 全特征的准确率变化）"
        )
        full_lbl = "全模型（Full）"
        stem = out_dir / "ablation_horizontal_degradation_zh"
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
        xlabel = "Accuracy (%)"
        title = (
            "Ablation Study: Contribution of Different Features\n"
            "(VulPatchGuard Performance Degradation)"
        )
        full_lbl = "Full Model"
        stem = out_dir / "ablation_horizontal_degradation"

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
    gaps = [full_acc - a for a in accuracy]

    fig, ax = plt.subplots(figsize=(10, 6))

    bars = ax.barh(
        configs,
        accuracy,
        color=colors,
        edgecolor="black",
        linewidth=0.5,
        height=0.6,
    )

    for i, (bar, acc, gap) in enumerate(zip(bars, accuracy, gaps)):
        w = bar.get_width()
        yc = bar.get_y() + bar.get_height() / 2.0
        ax.text(
            w + 1,
            yc,
            f"{acc:.1f}%",
            ha="left",
            va="center",
            fontsize=10,
            fontweight="bold",
        )
        if i > 0:
            if w >= DROP_INNER_MIN_WIDTH:
                ax.text(
                    w - 5,
                    yc,
                    f"↓{gap:.1f}",
                    ha="right",
                    va="center",
                    fontsize=9,
                    color="white",
                    fontweight="bold",
                )
            else:
                # 窄柱：居中在柱内 + 略小字号，避免 ha=right 时文字越过 x=0
                fs = 7 if w < 12 else 8
                ax.text(
                    w / 2,
                    yc,
                    f"↓{gap:.1f}",
                    ha="center",
                    va="center",
                    fontsize=fs,
                    color="white",
                    fontweight="bold",
                )

    ax.axvline(
        x=full_acc,
        color="red",
        linestyle="--",
        alpha=0.5,
        linewidth=1.5,
    )
    ax.text(
        full_acc,
        8.5,
        full_lbl,
        ha="center",
        fontsize=9,
        color="red",
    )

    ax.set_xlabel(xlabel, fontsize=12, fontweight="bold")
    ax.set_title(title, fontsize=13, fontweight="bold", pad=20)
    ax.set_xlim(0, 100)
    ax.grid(axis="x", linestyle="--", alpha=0.3)

    ax.invert_yaxis()

    plt.tight_layout()
    fig.subplots_adjust(left=0.28)
    plt.savefig(stem.with_suffix(".pdf"), dpi=300, bbox_inches="tight", pad_inches=0.12)
    plt.savefig(stem.with_suffix(".png"), dpi=300, bbox_inches="tight", pad_inches=0.12)
    plt.close()
    print(f"已保存: {stem}.pdf / .png")


def main():
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "docs" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    for lang in ("en", "zh"):
        plot_one(out_dir, lang)
    print("完成。")


if __name__ == "__main__":
    main()
