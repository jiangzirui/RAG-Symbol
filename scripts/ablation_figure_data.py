# -*- coding: utf-8 -*-
"""消融实验表格数据（与 results/self_eval/ablation_and_thresholds 一致，供作图脚本共用）。"""

# (显示名, 准确率%, 正确数, 总数)
ABLATION_ROWS = [
    ("VulPatchGuard（全特征）", 95.09, 7399, 7781),
    ("w/o statistical（去除统计）", 78.47, 6106, 7781),
    ("w/o CFG（去除 CFG）", 70.36, 5475, 7781),
    ("w/o semantic（去除语义）", 17.12, 1332, 7781),
    ("w/o statistical+CFG", 56.97, 4433, 7781),
    ("w/o semantic+statistical", 14.87, 1157, 7781),
    ("w/o CFG+semantic", 13.84, 1077, 7781),
    ("CLAP（code only）", 9.73, 757, 7781),
    ("CodeBERT（code only）", 8.32, 647, 7781),
]

# 学术论文风格柱状图：主方法一条深色，其余统一浅灰（见 plot_ablation_accuracy_bars.py）
BAR_COLOR_MAIN = "#2E4057"  # 深蓝灰，接近 IEEE/Nature 常用单色强调
BAR_COLOR_OTHER = "#DADEE3"  # 浅灰条
# 主方法变体（如 no LLM）：介于主条与基线之间的灰蓝
BAR_COLOR_OURS_VARIANT = "#6B7B8C"

# 表 5.6 主方法与基线对比（与 results/self_eval 中 RAG / rag_no_llm 等一致）
BASELINE_COMPARISON_ROWS = [
    ("VulPatchGuard", 95.09, 7399, 7781),
    ("VulPatchGuard (no LLM)", 67.41, 5245, 7781),
    ("Finger", 45.87, 3569, 7781),
    ("Bindiff", 20.14, 1567, 7781),
]
