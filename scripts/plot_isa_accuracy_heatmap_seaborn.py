#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跨架构 × 优化等级准确率热力图（seaborn），与用户提供的代码一致。"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

def main():
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "docs" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    data = np.array(
        [
            [95.09, 93.40, 92.35],  # ARM
            [93.52, 95.40, 94.18],  # RISC-V
            [92.05, 93.94, 93.02],  # X86
            [87.53, 89.35, 88.33],  # MIPS
        ]
    )

    df = pd.DataFrame(
        data,
        index=["ARM", "RISC-V", "X86", "MIPS"],
        columns=["O1", "O2", "O3"],
    )

    fig, ax = plt.subplots(figsize=(6, 4))
    sns.heatmap(
        df,
        annot=True,
        fmt=".1f",
        cmap="YlOrRd",
        cbar_kws={"label": "Accuracy (%)"},
        linewidths=0.5,
        linecolor="gray",
        ax=ax,
    )

    ax.set_title("Symbol Recovery Accuracy Heatmap", fontsize=12, fontweight="bold")
    plt.tight_layout()

    out_pdf = out_dir / "isa_accuracy_heatmap_seaborn.pdf"
    out_png = out_dir / "isa_accuracy_heatmap_seaborn.png"
    plt.savefig(out_pdf, dpi=300)
    plt.savefig(out_png, dpi=300)
    plt.close()
    print(f"已保存: {out_pdf}")
    print(f"已保存: {out_png}")


if __name__ == "__main__":
    main()
