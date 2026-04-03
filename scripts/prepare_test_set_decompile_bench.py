#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 Hugging Face 上的 Decompile-Bench 数据集下载并转换为本项目的测试集格式。
产出：data/test_decompile_bench/test_features.json、ground_truth.json。
依赖：pip install datasets
用法:
  python scripts/prepare_test_set_decompile_bench.py -o data/test_decompile_bench --max-functions 5000
"""

import argparse
import json
from pathlib import Path

try:
    from datasets import load_dataset
    HAS_DATASETS = True
except ImportError:
    HAS_DATASETS = False


def main():
    parser = argparse.ArgumentParser(description="从 Decompile-Bench (HF) 制备测试集")
    parser.add_argument("-o", "--out-dir", default="data/test_decompile_bench", help="输出目录")
    parser.add_argument("--max-functions", type=int, default=10000, help="最多取多少条（默认 10000）")
    parser.add_argument("--split", default="train", help="HF split: train 或 test（若有）")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    args = parser.parse_args()

    if not HAS_DATASETS:
        raise SystemExit("请先安装: pip install datasets")

    print("正在从 Hugging Face 加载 Decompile-Bench ...")
    try:
        ds = load_dataset("LLM4Binary/decompile-bench", split=args.split, trust_remote_code=True)
    except Exception as e:
        raise SystemExit(f"加载失败（请检查网络或 HF 权限）: {e}")

    n_total = len(ds)
    if args.max_functions < n_total:
        import random
        indices = list(range(n_total))
        random.seed(args.seed)
        indices = random.sample(indices, args.max_functions)
        ds = ds.select(indices)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    functions = []
    ground_truth = {}

    for i, row in enumerate(ds):
        name = (row.get("name") or "").strip()
        asm = (row.get("asm") or "").strip()
        code = (row.get("code") or "").strip()
        if not name:
            continue
        # 用索引做唯一地址，与 ground truth 对齐
        addr = f"idx_{i:06d}"
        # 优先用 asm 作为“反编译代码”的替代（很多模型直接吃 asm）
        decompiled = asm if asm else code
        if not decompiled:
            continue

        basic_info = {"name": f"FUN_{addr}", "address": addr, "size": 0}
        func = {
            "basic_info": basic_info,
            "decompiled_code": decompiled,
            "opcodes": [],
            "constants": [],
            "xrefs": {},
            "semantic_features": {},
            "cfg_structure": {},
            "extended_statistics": {},
        }
        functions.append(func)
        ground_truth[addr] = name

    test_features = {
        "program_name": "decompile_bench_subset",
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
    print("下一步: 用该目录作为测试集跑 inference + evaluate，例如:")
    print(f"  python scripts/run_experiments.py -f {test_path} -g {gt_path} -l <符号库路径> -o results/exp_decompile_bench")


if __name__ == "__main__":
    main()
