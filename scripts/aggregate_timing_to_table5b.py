#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 results/self_eval 下各 *_timing.json 汇总成表 5b（各阶段耗时）。
用法:
  python scripts/aggregate_timing_to_table5b.py [--dir results/self_eval] [--md] [--update-doc]
  --md: 只打印 Markdown 表
  --update-doc: 用汇总结果替换 docs/实验部分-论文版.md 中的表 5b（谨慎使用，建议先 --md 查看）
"""

import json
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIR = ROOT / "results" / "self_eval"
DOC_PATH = ROOT / "docs" / "实验部分-论文版.md"

# 文件名片段 -> 表 5b 组别显示名
NAME_MAP = {
    "ablation_full": "Full",
    "rag_no_llm": "RAG (no LLM)",
    "rag_llm": "RAG (LLM)",
    "code_only": "code_only",
    "ablation_code_only": "code_only",
    "single_cfg": "single_cfg",
    "single_statistical": "single_statistical",
    "codebert": "CodeBERT (code only)",
}


def find_timing_files(results_dir: Path):
    """找出所有 *_timing.json（不含 timing_summary.json）。"""
    out = []
    for f in results_dir.glob("*_timing.json"):
        if f.name == "timing_summary.json":
            continue
        # 例如 predictions_ablation_full_timing.json -> ablation_full
        stem = f.stem.replace("_timing", "").replace("predictions_", "")
        out.append((stem, f))
    return out


def load_timing(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("timing", data)


def build_table(rows: list, total_functions: int = 7791) -> str:
    """生成表 5b 的 Markdown。最后一列为单函数均时(秒)，便于对比。"""
    header = "| 组别 | 加载符号库 | 特征编码 | 检索 | 匹配 | RAG大模型分析 | 单函数均时(秒) |"
    sep = "|------|------------|----------|------|------|----------------|----------------|"
    lines = [header, sep]
    n = max(1, int(total_functions))
    for name, t in rows:
        load_s = t.get("load_library_seconds", 0) or 0
        enc_s = t.get("feature_encoding_seconds", 0) or 0
        ret_s = t.get("retrieval_seconds", 0) or 0
        mat_s = t.get("matching_seconds", 0) or 0
        llm_s = t.get("llm_seconds", 0) or 0
        total_s = t.get("total_seconds", 0) or 0
        avg_s = total_s / n
        lines.append(
            f"| {name} | {load_s:.2f} | {enc_s:.2f} | {ret_s:.2f} | {mat_s:.2f} | {llm_s:.2f} | {avg_s:.3f} |"
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="汇总 *_timing.json 为表 5b")
    parser.add_argument("--dir", default=str(DEFAULT_DIR), help="结果目录")
    parser.add_argument("--total-functions", type=int, default=7791, metavar="N", help="函数总数，用于计算单函数均时（默认 7791）")
    parser.add_argument("--md", action="store_true", help="只打印 Markdown 表")
    parser.add_argument("--update-doc", action="store_true", help="用汇总表替换文档中的表 5b")
    args = parser.parse_args()
    results_dir = Path(args.dir)
    if not results_dir.exists():
        print(f"目录不存在: {results_dir}")
        return 1

    pairs = find_timing_files(results_dir)
    if not pairs:
        print("未找到 *_timing.json，请先运行 inference 生成各配置的预测与计时文件。")
        return 0

    rows = []
    for stem, path in sorted(pairs, key=lambda x: x[0]):
        display_name = NAME_MAP.get(stem, stem)
        try:
            timing = load_timing(path)
            rows.append((display_name, timing))
        except Exception as e:
            print(f"跳过 {path.name}: {e}")

    if not rows:
        print("没有可用的 timing 数据。")
        return 0

    table_md = build_table(rows, total_functions=args.total_functions)
    if args.md:
        print(table_md)
        return 0

    if args.update_doc:
        if not DOC_PATH.exists():
            print(f"文档不存在: {DOC_PATH}")
            return 1
        text = DOC_PATH.read_text(encoding="utf-8")
        # 替换「表 5b 各组实验各阶段耗时」到下一个「注：」之前的表格体
        start_marker = "表 5b 各组实验各阶段耗时（秒）\n\n"
        end_marker = "\n\n注："
        if start_marker not in text or end_marker not in text:
            print("未在文档中找到表 5b 的起止标记，请手动替换。")
            print("当前汇总表：\n")
            print(table_md)
            return 1
        idx0 = text.index(start_marker) + len(start_marker)
        idx1 = text.index(end_marker, idx0)
        new_text = text[:idx0] + table_md + text[idx1:]
        DOC_PATH.write_text(new_text, encoding="utf-8")
        print(f"已更新 {DOC_PATH} 中的表 5b。")
        return 0

    print("各阶段耗时汇总（表 5b）：\n")
    print(table_md)
    print("\n使用 --md 仅输出上表；使用 --update-doc 将上表写回 docs/实验部分-论文版.md。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
