#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
绘制两张折线图：
1) 消融实验结果折线图
2) RAG 对比实验结果折线图

数据源：results/self_eval/ablation_and_thresholds.json
输出：
- results/self_eval/fig_ablation_line.png / .pdf
- results/self_eval/fig_rag_comparison_line.png / .pdf
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "results" / "self_eval" / "ablation_and_thresholds.json"
OUT_DIR = ROOT / "results" / "self_eval"


def _load_data() -> dict:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"未找到结果文件: {DATA_PATH}")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _to_method_map(data: dict) -> dict:
    return {item.get("method"): item for item in data.get("ablation", [])}


def _format_point_label(acc: float, correct: int, total: int) -> str:
    return f"{acc * 100:.2f}%\n{correct}/{total}"


def _plot_ablation_line(method_map: dict, lang: str = "zh"):
    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS", "DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False
    import matplotlib.pyplot as plt

    if lang == "en":
        order = [
            ("ablation_full", "Full"),
            ("ablation_wo_semantic", "w/o semantic"),
            ("ablation_wo_cfg", "w/o CFG"),
            ("ablation_wo_statistical", "w/o statistical"),
            ("ablation_wo_semantic_cfg", "w/o sem+CFG"),
            ("ablation_wo_semantic_statistical", "w/o sem+stat"),
            ("ablation_wo_cfg_statistical", "w/o CFG+stat"),
            ("ablation_multi_attention", "Multi+attn"),
        ]
    else:
        order = [
            ("ablation_full", "完整模型"),
            ("ablation_wo_semantic", "去语义"),
            ("ablation_wo_cfg", "去CFG"),
            ("ablation_wo_statistical", "去统计"),
            ("ablation_wo_semantic_cfg", "去语义+CFG"),
            ("ablation_wo_semantic_statistical", "去语义+统计"),
            ("ablation_wo_cfg_statistical", "去CFG+统计"),
            ("ablation_multi_attention", "多特征+注意力"),
        ]

    labels = []
    accs = []
    corrects = []
    totals = []
    for key, label in order:
        row = method_map.get(key)
        if not row or row.get("accuracy") is None:
            continue
        labels.append(label)
        accs.append(row["accuracy"] * 100.0)
        corrects.append(row.get("correct", 0))
        totals.append(row.get("total", 0))

    fig, ax = plt.subplots(figsize=(12, 5.5))
    x = list(range(len(labels)))
    ax.plot(
        x,
        accs,
        marker="o",
        markersize=7,
        linewidth=2.2,
        color="#2E86AB",
        markerfacecolor="white",
        markeredgewidth=1.8,
        markeredgecolor="#2E86AB",
    )

    # 高亮关键点
    for idx, label in enumerate(labels):
        if label in (("Full", "w/o statistical") if lang == "en" else ("完整模型", "去统计")):
            ax.scatter(x[idx], accs[idx], s=90, color="#E74C3C", zorder=3)

    for idx, val in enumerate(accs):
        ax.annotate(
            _format_point_label(val / 100.0, corrects[idx], totals[idx]),
            (x[idx], val),
            textcoords="offset points",
            xytext=(0, 10),
            ha="center",
            fontsize=8.5,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#cfcfcf", alpha=0.95),
        )

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=22, ha="right", fontsize=9.5)
    if lang == "en":
        ax.set_ylabel("Accuracy (%)", fontsize=11)
        ax.set_xlabel("Ablation configuration", fontsize=11)
        ax.set_title("Ablation line chart (self-eval, 7781 functions)", fontsize=12.5, pad=10)
    else:
        ax.set_ylabel("准确率（%）", fontsize=11)
        ax.set_xlabel("消融配置", fontsize=11)
        ax.set_title("消融实验折线图（self-eval，7781个函数）", fontsize=12.5, pad=10)
    ax.set_ylim(0, 102)
    ax.grid(axis="y", linestyle="--", linewidth=0.7, alpha=0.35)

    fig.tight_layout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = "en" if lang == "en" else "zh"
    png_path = OUT_DIR / f"fig_ablation_line_{suffix}.png"
    pdf_path = OUT_DIR / f"fig_ablation_line_{suffix}.pdf"
    # 兼容历史默认文件名（保留中文版本为默认）
    if lang != "en":
        fig.savefig(OUT_DIR / "fig_ablation_line.png", dpi=220, bbox_inches="tight")
        fig.savefig(OUT_DIR / "fig_ablation_line.pdf", bbox_inches="tight")
    fig.savefig(png_path, dpi=220, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)
    return png_path, pdf_path


def _plot_rag_line(method_map: dict, lang: str = "zh"):
    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS", "DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False
    import matplotlib.pyplot as plt

    if lang == "en":
        order = [
            ("ablation_no_library", "No library"),
            ("rag_no_llm", "RAG (no LLM)"),
            ("rag_llm", "RAG (LLM)"),
            ("ablation_full", "Full"),
        ]
    else:
        order = [
            ("ablation_no_library", "无符号库"),
            ("rag_no_llm", "RAG（无LLM）"),
            ("rag_llm", "RAG（LLM）"),
            ("ablation_full", "完整模型"),
        ]

    labels = []
    accs = []
    corrects = []
    totals = []
    for key, label in order:
        row = method_map.get(key)
        if not row or row.get("accuracy") is None:
            continue
        labels.append(label)
        accs.append(row["accuracy"] * 100.0)
        corrects.append(row.get("correct", 0))
        totals.append(row.get("total", 0))

    fig, ax = plt.subplots(figsize=(10, 5.2))
    x = list(range(len(labels)))
    ax.plot(
        x,
        accs,
        marker="o",
        markersize=8,
        linewidth=2.4,
        color="#27AE60",
        markerfacecolor="white",
        markeredgewidth=2,
        markeredgecolor="#1E8449",
    )

    for idx, val in enumerate(accs):
        ax.annotate(
            _format_point_label(val / 100.0, corrects[idx], totals[idx]),
            (x[idx], val),
            textcoords="offset points",
            xytext=(0, 10),
            ha="center",
            fontsize=9,
            bbox=dict(boxstyle="round,pad=0.22", fc="white", ec="#cfcfcf", alpha=0.95),
        )

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    if lang == "en":
        ax.set_ylabel("Accuracy (%)", fontsize=11)
        ax.set_xlabel("RAG comparison setting", fontsize=11)
        ax.set_title("RAG comparison line chart (self-eval, 7781 functions)", fontsize=12.5, pad=10)
    else:
        ax.set_ylabel("准确率（%）", fontsize=11)
        ax.set_xlabel("RAG对比配置", fontsize=11)
        ax.set_title("RAG对比实验折线图（self-eval，7781个函数）", fontsize=12.5, pad=10)
    ax.set_ylim(0, 102)
    ax.grid(axis="y", linestyle="--", linewidth=0.7, alpha=0.35)

    fig.tight_layout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = "en" if lang == "en" else "zh"
    png_path = OUT_DIR / f"fig_rag_comparison_line_{suffix}.png"
    pdf_path = OUT_DIR / f"fig_rag_comparison_line_{suffix}.pdf"
    if lang != "en":
        fig.savefig(OUT_DIR / "fig_rag_comparison_line.png", dpi=220, bbox_inches="tight")
        fig.savefig(OUT_DIR / "fig_rag_comparison_line.pdf", bbox_inches="tight")
    fig.savefig(png_path, dpi=220, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)
    return png_path, pdf_path


def main():
    try:
        data = _load_data()
    except Exception as exc:
        print(str(exc))
        return 1

    try:
        method_map = _to_method_map(data)
        outputs = []
        for lang in ("zh", "en"):
            outputs.extend(_plot_ablation_line(method_map, lang=lang))
            outputs.extend(_plot_rag_line(method_map, lang=lang))
    except ImportError:
        print("需要 matplotlib。请先安装：pip install matplotlib")
        return 1
    except Exception as exc:
        print(f"绘图失败: {exc}")
        return 1

    for out in outputs:
        print(f"已生成: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

