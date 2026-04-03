#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0：从 training_data.json 制备标准测试集，产出与主流程特征文件格式一致的 test_features.json 与 ground_truth.json。
用法:
  python scripts/prepare_test_set.py data/training/training_data.json -o data/test
可选 --max-functions 限制条数（便于快速实验），--seed 固定随机划分。
"""

import argparse
import json
import random
from pathlib import Path


def normalize_addr(addr: str) -> str:
    return str(addr).strip().replace("0x", "").upper()


def main():
    parser = argparse.ArgumentParser(description="从 training_data 制备测试集：test_features.json + ground_truth.json")
    parser.add_argument("input", help="training_data.json 路径")
    parser.add_argument("-o", "--out-dir", default="data/test", help="输出目录（默认 data/test）")
    parser.add_argument("--max-functions", type=int, default=None, help="最多保留函数数（默认全部）")
    parser.add_argument("--seed", type=int, default=42, help="随机种子（用于采样时）")
    args = parser.parse_args()

    path = Path(args.input)
    if not path.exists():
        raise SystemExit(f"文件不存在: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    functions = data.get("functions") or data.get("samples") or []
    if isinstance(data, list):
        functions = data

    # 过滤：必须有 address 和 label
    items = []
    for f in functions:
        if not isinstance(f, dict) or not f.get("address") or not f.get("label"):
            continue
        items.append(f)

    if args.max_functions and len(items) > args.max_functions:
        random.seed(args.seed)
        items = random.sample(items, args.max_functions)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 转为与主流程特征文件一致的格式（模拟脱符号：basic_info.name = FUN_<address>）
    program_name = "test_set_from_training"
    test_functions = []
    ground_truth = {}

    for f in items:
        addr = f.get("address", "")
        label = (f.get("label") or f.get("symbol") or f.get("name") or "").strip()
        addr_norm = normalize_addr(addr)

        basic_info = {
            "name": f"FUN_{addr_norm}",
            "address": addr,
            "size": 0,
        }
        # 主流程格式字段
        func = {
            "basic_info": basic_info,
            "decompiled_code": f.get("decompiled_code") or "",
            "opcodes": f.get("opcodes") or [],
            "constants": f.get("constants") or [],
            "xrefs": f.get("xrefs") or {},
            "semantic_features": f.get("semantic_features") if isinstance(f.get("semantic_features"), dict) else {},
            "cfg_structure": f.get("cfg_structure") or f.get("cfg_features") or {},
            "extended_statistics": f.get("extended_statistics") or {},
        }
        test_functions.append(func)
        ground_truth[addr_norm] = label

    test_features = {
        "program_name": program_name,
        "total_functions": len(test_functions),
        "functions": test_functions,
    }

    test_features_path = out_dir / "test_features.json"
    gt_path = out_dir / "ground_truth.json"

    with open(test_features_path, "w", encoding="utf-8") as fp:
        json.dump(test_features, fp, indent=2, ensure_ascii=False)

    with open(gt_path, "w", encoding="utf-8") as fp:
        json.dump(ground_truth, fp, indent=2, ensure_ascii=False)

    print(f"已写入测试集: {test_features_path} ({len(test_functions)} 条)")
    print(f"已写入 ground truth: {gt_path} ({len(ground_truth)} 条)")


if __name__ == "__main__":
    main()
