#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P2：读取实验汇总 summary.json，生成 Accuracy / F1 对比柱状图与消融图，保存到 figures/。
用法:
  python scripts/plot_results.py results/experiments/summary.json -o figures
  python scripts/plot_results.py results/exp1/summary.json
"""

import argparse
import json
from pathlib import Path

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


def main():
    parser = argparse.ArgumentParser(description="根据 summary.json 绘制方法对比与消融图")
    parser.add_argument("summary", help="summary.json 路径")
    parser.add_argument("-o", "--out-dir", default="figures", help="图片输出目录（默认 figures）")
    parser.add_argument("--dpi", type=int, default=150, help="图片 DPI")
    args = parser.parse_args()

    if not HAS_MPL:
        raise SystemExit("需要安装 matplotlib: pip install matplotlib")

    path = Path(args.summary)
    if not path.exists():
        raise SystemExit(f"文件不存在: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    methods = data.get("methods") or []
    if not methods:
        raise SystemExit("summary 中无 methods 列表")

    # 过滤掉无效行
    valid = [m for m in methods if m.get("accuracy") is not None and m.get("error") is None]
    if not valid:
        raise SystemExit("没有有效的指标数据可绘图")

    names = [m["method"] for m in valid]
    accs = [m["accuracy"] for m in valid]
    f1s = [m["f1"] for m in valid]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 柱状图：Accuracy
    fig, ax = plt.subplots(figsize=(max(6, len(names) * 0.5), 4))
    x = range(len(names))
    bars = ax.bar(x, accs, color="steelblue", edgecolor="navy", alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=45, ha="right")
    ax.set_ylabel("Accuracy")
    ax.set_ylim(0, 1.05)
    ax.set_title("Symbol Recovery Accuracy by Method")
    for b, v in zip(bars, accs):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.02, f"{v:.3f}", ha="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_dir / "accuracy_comparison.png", dpi=args.dpi, bbox_inches="tight")
    plt.close()
    print(f"已保存: {out_dir / 'accuracy_comparison.png'}")

    # 柱状图：F1
    fig, ax = plt.subplots(figsize=(max(6, len(names) * 0.5), 4))
    bars = ax.bar(x, f1s, color="coral", edgecolor="darkred", alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=45, ha="right")
    ax.set_ylabel("F1")
    ax.set_ylim(0, 1.05)
    ax.set_title("Symbol Recovery F1 by Method")
    for b, v in zip(bars, f1s):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.02, f"{v:.3f}", ha="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_dir / "f1_comparison.png", dpi=args.dpi, bbox_inches="tight")
    plt.close()
    print(f"已保存: {out_dir / 'f1_comparison.png'}")

    # 若有消融项，单独画一张消融 Accuracy 图（仅包含 ablation_ 开头的方法）
    ablation = [m for m in valid if m["method"].startswith("ablation_")]
    if ablation:
        anames = [m["method"].replace("ablation_", "") for m in ablation]
        aaccs = [m["accuracy"] for m in ablation]
        fig, ax = plt.subplots(figsize=(max(5, len(anames) * 0.5), 4))
        x = range(len(anames))
        ax.bar(x, aaccs, color="seagreen", edgecolor="darkgreen", alpha=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(anames, rotation=45, ha="right")
        ax.set_ylabel("Accuracy")
        ax.set_ylim(0, 1.05)
        ax.set_title("Ablation: Accuracy")
        fig.tight_layout()
        fig.savefig(out_dir / "ablation_accuracy.png", dpi=args.dpi, bbox_inches="tight")
        plt.close()
        print(f"已保存: {out_dir / 'ablation_accuracy.png'}")


if __name__ == "__main__":
    main()
