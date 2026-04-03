#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 SymLM 的 dataset_sample 的 train（及可选 valid）转成本系统的「特征 + 符号」格式，用于建符号库。
这样库和测试集同源、同表示（都是 Trex 风格 input.static），符号名也来自 SymLM label，推理时才能匹配到。

用法:
  python scripts/prepare_symlm_library.py --symlm-dir "path/to/SymLM-main/dataset_generation/dataset_sample" -o data/symlm_library
  python scripts/build_symbol_library.py -s data/symlm_library/library_symbols.json -f data/symlm_library/library_features.json -o data/symbols/symbol_library_symlm.json
  python scripts/inference.py data/test_symlm_500/test_features.json -o results/exp_symlm_500/predictions.json -l data/symbols/symbol_library_symlm.json -t 0.5
"""

import argparse
import json
from pathlib import Path


def read_split(base: Path, split: str):
    """读取一个 split 的 input.label 和 input.static，返回 (labels, statics)。"""
    split_dir = base / split
    label_file = split_dir / "self" / "input.label"
    static_file = split_dir / "self" / "input.static"
    for f in (label_file, static_file):
        if not f.exists():
            raise FileNotFoundError(f"缺少: {f}")
    labels = []
    with open(label_file, "r", encoding="utf-8", errors="replace") as fp:
        for line in fp:
            labels.append(line.strip())
    statics = []
    with open(static_file, "r", encoding="utf-8", errors="replace") as fp:
        for line in fp:
            statics.append(line.strip())
    if len(labels) != len(statics):
        raise ValueError(f"{split}: input.label={len(labels)}, input.static={len(statics)} 行数不一致")
    return labels, statics


def main():
    parser = argparse.ArgumentParser(description="从 SymLM train/valid 制备建库用特征与符号")
    parser.add_argument("--symlm-dir", required=True, help="SymLM dataset_sample 目录（含 train/valid/test）")
    parser.add_argument("-o", "--out-dir", default="data/symlm_library", help="输出目录")
    parser.add_argument("--splits", nargs="+", default=["train", "valid"], help="用哪些 split 建库（默认 train valid）")
    parser.add_argument("--max-functions", type=int, default=None, help="每个 split 最多取多少条（默认全部）")
    args = parser.parse_args()

    base = Path(args.symlm_dir)
    if not base.exists():
        raise SystemExit(f"目录不存在: {base}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_functions = []
    all_symbols = []  # [{"address": addr, "name": name}, ...]

    for split in args.splits:
        labels, statics = read_split(base, split)
        n = len(labels)
        if args.max_functions and n > args.max_functions:
            n = args.max_functions
        for i in range(n):
            label = labels[i]
            static = statics[i]
            if not static:
                continue
            addr = f"symlm_{split}_{i:06d}"
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
            all_functions.append(func)
            all_symbols.append({"address": addr, "name": symbol})

    features_path = out_dir / "library_features.json"
    symbols_path = out_dir / "library_symbols.json"

    features_data = {
        "program_name": "symlm_library",
        "total_functions": len(all_functions),
        "functions": all_functions,
    }
    with open(features_path, "w", encoding="utf-8") as f:
        json.dump(features_data, f, indent=2, ensure_ascii=False)

    symbols_data = {"functions": all_symbols}
    with open(symbols_path, "w", encoding="utf-8") as f:
        json.dump(symbols_data, f, indent=2, ensure_ascii=False)

    print(f"已写入: {features_path} ({len(all_functions)} 条)")
    print(f"已写入: {symbols_path}")
    print()
    print("下一步：用该特征+符号建库，再用此库对 SymLM 测试集推理")
    print(f"  1) 建库: python scripts/build_symbol_library.py -s {symbols_path} -f {features_path} -o data/symbols/symbol_library_symlm.json")
    print(f"  2) 推理: python scripts/inference.py data/test_symlm_500/test_features.json -o results/exp_symlm_500/predictions.json -l data/symbols/symbol_library_symlm.json -t 0.5")
    print(f"  3) 评估: python scripts/evaluate.py results/exp_symlm_500/predictions.json -g data/test_symlm_500/ground_truth.json -o results/exp_symlm_500/eval.json")


if __name__ == "__main__":
    main()
