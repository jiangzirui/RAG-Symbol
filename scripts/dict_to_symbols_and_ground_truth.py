#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 dict.txt（地址 -> 真实函数名）转为本系统所需的 symbols JSON 与 ground_truth.json。
用于：bin 目录下用 dict.txt 标注了地址与真实函数名，Ghidra 只导出 features 无符号时，
用本脚本从 dict.txt 生成符号文件及评估用 ground_truth。

dict.txt 格式（任一行一种，可混用）：
  - 每行：地址 函数名（空格或制表符分隔）
  - 地址可为 0x8048000 或 8048000，会统一规范化
  - # 开头或空行忽略

用法:
  # 指定 dict、features 目录，自动配对（仅一个 *_features.json 时）
  python scripts/dict_to_symbols_and_ground_truth.py --dict "E:\work\symbol\auto\data_bin\test\dict.txt" --features-dir "E:\...\ghidra_12.0_PUBLIC\data\features" -o data/dat_bin_test

  # 指定具体 features 文件
  python scripts/dict_to_symbols_and_ground_truth.py --dict "E:\...\test\dict.txt" --features-file "E:\...\data\features\program_x86_64_features.json" -o data/dat_bin_test
"""

import argparse
import json
import re
import sys
from pathlib import Path


def normalize_address(addr: str) -> str:
    if not addr:
        return ""
    s = str(addr).strip().replace("0x", "").replace("0X", "").upper()
    return s


def parse_dict_txt(path: str) -> dict:
    """解析 dict.txt，返回 address_key -> name。"""
    path = Path(path)
    if not path.exists():
        return {}
    addr_to_name = {}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = re.split(r"[\s\t,]+", line, maxsplit=1)
            if len(parts) < 2:
                continue
            addr, name = parts[0], parts[1].strip()
            if not name:
                continue
            key = normalize_address(addr)
            addr_to_name[key] = name
    return addr_to_name


def main():
    parser = argparse.ArgumentParser(
        description="从 dict.txt 生成 symbols JSON 与 ground_truth，供建库与评估"
    )
    parser.add_argument("--dict", required=True, help="dict.txt 路径（地址 函数名 每行）")
    parser.add_argument("--features-dir", default=None, help="features 目录（用于配对 *_features.json）")
    parser.add_argument("--features-file", default=None, help="指定单个 features 文件（与 --features-dir 二选一）")
    parser.add_argument("-o", "--output-dir", default="data/dat_bin_test", help="输出目录（symbols 会按 stem 写入，ground_truth.json 写在此目录）")
    parser.add_argument("--symbols-dir", default=None, help="symbols 写入目录（默认与 features 同目录，便于 merge 配对）")
    args = parser.parse_args()

    addr_to_name = parse_dict_txt(args.dict)
    if not addr_to_name:
        print("dict.txt 未解析到任何 地址->函数名，请检查格式（每行：地址 函数名）")
        return 1

    features_file = None
    if args.features_file:
        features_file = Path(args.features_file)
        if not features_file.exists():
            print(f"features 文件不存在: {features_file}")
            return 1
    elif args.features_dir:
        features_dir = Path(args.features_dir)
        if not features_dir.exists():
            print(f"features 目录不存在: {features_dir}")
            return 1
        candidates = list(features_dir.glob("*_features.json"))
        if len(candidates) == 0:
            print(f"未在 {features_dir} 找到 *_features.json")
            return 1
        if len(candidates) > 1:
            print(f"存在多个 *_features.json，请用 --features-file 指定: {[str(c) for c in candidates]}")
            return 1
        features_file = candidates[0]
    else:
        print("请指定 --features-dir 或 --features-file")
        return 1

    stem = features_file.stem.replace("_features", "")
    with open(features_file, "r", encoding="utf-8") as f:
        features_data = json.load(f)

    functions = features_data.get("functions", [])
    symbols_functions = []
    ground_truth = {}
    for func in functions:
        basic = func.get("basic_info", {})
        addr = basic.get("address", "")
        key = normalize_address(addr)
        if key not in addr_to_name:
            continue
        name = addr_to_name[key]
        symbols_functions.append({"address": addr, "name": name})
        ground_truth[key] = name

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    symbols_dir = Path(args.symbols_dir) if args.symbols_dir else out_dir
    symbols_dir.mkdir(parents=True, exist_ok=True)

    symbols_json = {"functions": symbols_functions}
    symbols_path = symbols_dir / f"{stem}_symbols.json"
    with open(symbols_path, "w", encoding="utf-8") as f:
        json.dump(symbols_json, f, indent=2, ensure_ascii=False)
    print(f"已写 symbols: {symbols_path}（{len(symbols_functions)} 条）")

    gt_path = out_dir / "ground_truth.json"
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2, ensure_ascii=False)
    print(f"已写 ground_truth: {gt_path}（{len(ground_truth)} 条）")

    test_features_path = out_dir / "test_features.json"
    if not test_features_path.exists():
        import shutil
        shutil.copy(features_file, test_features_path)
        print(f"已复制 features 到: {test_features_path}（供 inference 用）")
    lib_name = out_dir.name.replace("-", "_") + "_lib"
    lib_path = Path("data/symbols") / f"symbol_library_{lib_name}.json"
    print()
    print("下一步:")
    print(f"  1) 建库: python scripts/build_symbol_library.py -s {symbols_path} -f {features_file} -o {lib_path}")
    print(f"  2) 推理: python scripts/inference.py {out_dir / 'test_features.json'} -o results/{out_dir.name}/predictions.json -l {lib_path} -t 0.5")
    print(f"  3) 评估: python scripts/evaluate.py results/{out_dir.name}/predictions.json -g {gt_path} -o results/{out_dir.name}/eval.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
