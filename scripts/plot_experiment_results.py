#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据 results/self_eval/ablation_and_thresholds.json 绘制实验 Accuracy 柱状图，
用于论文实验部分（图 1）。
输出：results/self_eval/fig_experiment_accuracy.png（及可选 PDF）。
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "results" / "self_eval" / "ablation_and_thresholds.json"
OUT_DIR = ROOT / "results" / "self_eval"


def main():
    if not DATA_PATH.exists():
        print(f"未找到: {DATA_PATH}")
        return 1

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 配置 -> 显示名（短，用于横轴）
    name_map = {
        "ablation_full": "Full",
        "ablation_no_library": "No library",
        "ablation_wo_semantic": "w/o semantic",
        "ablation_wo_cfg": "w/o CFG",
        "ablation_wo_statistical": "w/o statistical",
        "ablation_wo_semantic_cfg": "w/o sem+CFG",
        "ablation_wo_semantic_statistical": "w/o sem+stat",
        "ablation_wo_cfg_statistical": "w/o CFG+stat",
        "ablation_code_only": "CLAP only",
        "ablation_multi_attention": "Multi+attn",
        "single_cfg": "Single-CFG",
        "single_statistical": "Single-stat",
        "rag_no_llm": "RAG(no LLM)",
        "rag_llm": "RAG(LLM)",
        "codebert": "CodeBERT",
    }

    methods = []
    accs = []
    for r in data.get("ablation", []):
        method = r.get("method", "")
        acc = r.get("accuracy")
        if acc is None:
            continue
        methods.append(name_map.get(method, method))
        accs.append(acc * 100.0)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("需要 matplotlib。pip install matplotlib 后重试。")
        return 1

    fig, ax = plt.subplots(figsize=(10, 5))
    x = range(len(methods))
    bars = ax.bar(x, accs, color="#2e86ab", edgecolor="#1a5276", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(methods, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("Accuracy (%)", fontsize=11)
    ax.set_ylim(0, 105)
    ax.set_title("Symbol recovery accuracy (self-eval, 7781 functions)")
    ax.grid(axis="y", alpha=0.3)
    # 高亮 Full 与 RAG(LLM)
    for i, (m, a) in enumerate(zip(methods, accs)):
        if m in ("Full", "RAG(LLM)"):
            bars[i].set_facecolor("#e94f37")
            bars[i].set_edgecolor("#c73e30")
    fig.tight_layout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    png_path = OUT_DIR / "fig_experiment_accuracy.png"
    fig.savefig(png_path, dpi=150, bbox_inches="tight")
    print(f"已保存: {png_path}")
    try:
        pdf_path = OUT_DIR / "fig_experiment_accuracy.pdf"
        fig.savefig(pdf_path, bbox_inches="tight")
        print(f"已保存: {pdf_path}")
    except Exception:
        pass
    plt.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
