#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 SymLM 的 dataset_sample 或 Zenodo 解压后的同类目录，转换为本项目的测试集格式。
SymLM 的 self/input.label = 每行一个函数名（可能为空格分隔的 token），input.static = 每行一条函数的伪汇编文本。
用法:
  python scripts/prepare_test_set_symlm.py --symlm-dir "E:/work/symbol/auto/ghidra_12.0_PUBLIC_20251205/ghidra_12.0_PUBLIC/SymLM-main/dataset_generation/dataset_sample" -o data/test_symlm --split test
"""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="从 SymLM dataset_sample 制备测试集")
    parser.add_argument("--symlm-dir", required=True, help="SymLM dataset_sample 目录（含 train/valid/test 子目录）")
    parser.add_argument("-o", "--out-dir", default="data/test_symlm", help="输出目录")
    parser.add_argument("--split", default="test", choices=["train", "valid", "test"], help="使用哪个 split")
    parser.add_argument("--max-functions", type=int, default=None, help="最多取多少条（默认全部，可设 500 快速试跑）")
    args = parser.parse_args()

    base = Path(args.symlm_dir)
    if not base.exists():
        raise SystemExit(f"目录不存在: {base}")

    split_dir = base / args.split
    label_file = split_dir / "self" / "input.label"
    static_file = split_dir / "self" / "input.static"

    for f in (label_file, static_file):
        if not f.exists():
            raise SystemExit(f"缺少文件: {f}")

    labels = []
    with open(label_file, "r", encoding="utf-8", errors="replace") as fp:
        for line in fp:
            labels.append(line.strip())
    statics = []
    with open(static_file, "r", encoding="utf-8", errors="replace") as fp:
        for line in fp:
            statics.append(line.strip())

    if len(labels) != len(statics):
        raise SystemExit(f"行数不一致: input.label={len(labels)}, input.static={len(statics)}")

    n = len(labels)
    if args.max_functions and n > args.max_functions:
        n = args.max_functions

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    functions = []
    ground_truth = {}

    for i in range(n):
        label = labels[i]
        static = statics[i]
        if not static:
            continue
        addr = f"symlm_{args.split}_{i:06d}"
        # SymLM 的 label 常为空格分隔的 token，可保留或改为下划线；此处保留原样便于与 SymLM 评估一致
        symbol = label if label else f"unknown_{i}"

        basic_info = {"name": f"FUN_{addr}", "address": addr, "size": 0}
        func = {
            "basic_info": basic_info,
            "decompiled_code": static,
            "opcodes": [],
            "constants": [],
            "xrefs": {},
            "semantic_features": {},
            "cfg_structure": {},
            "extended_statistics": {},
        }
        functions.append(func)
        ground_truth[addr] = symbol

    test_features = {
        "program_name": f"symlm_{args.split}_subset",
        "total_functions": len(functions),
        "functions": functions,
    }

    test_path = out_dir / "test_features.json"
    gt_path = out_dir / "ground_truth.json"

    with open(test_path, "w", encoding="utf-8") as f:
        json.dump(test_features, f, indent=2, ensure_ascii=False)

    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2, ensure_ascii=False)

    print(f"已写入: {test_path} ({len(functions)} 条)")
    print(f"已写入: {gt_path}")
    print("说明: SymLM 的 label 为空格分隔 token，评估时如需与 C 符号一致可先做规范化（如空格→下划线）。")
    print("下一步示例:")
    print(f"  python scripts/run_experiments.py -f {test_path} -g {gt_path} -l <符号库路径> -o results/exp_symlm")


if __name__ == "__main__":
    main()
