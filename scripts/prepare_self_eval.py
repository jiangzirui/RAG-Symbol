#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
有符号→脱符号自对比评估：从「有符号符号文件」和「脱符号特征文件」生成 ground_truth 和测试用特征。
保证地址一致时，用脱符号特征做推理，再与有符号时的真实名对比算准确率。

用法:
  python scripts/prepare_self_eval.py --symboled-symbols data/symbols/xxx_symbols.json --stripped-features data/features/xxx_stripped_features.json -o data/self_eval
"""

import argparse
import json
import shutil
from pathlib import Path


def normalize_address(addr: str) -> str:
    if not addr:
        return ""
    return str(addr).strip().replace("0x", "").upper()


def is_auto_generated_name(name: str) -> bool:
    auto_prefixes = ("FUN_", "sub_", "LAB_", "entry", "thunk_", "undefined", "UNK_", "DAT_")
    return any(name.startswith(p) for p in auto_prefixes)


def main():
    parser = argparse.ArgumentParser(description="准备自对比评估：ground_truth + 脱符号 test_features")
    parser.add_argument("--symboled-symbols", required=True, help="有符号二进制导出的符号文件（含 functions[].address, name）")
    parser.add_argument("--stripped-features", required=True, help="脱符号二进制导出的特征文件")
    parser.add_argument("-o", "--out-dir", default="data/self_eval", help="输出目录")
    args = parser.parse_args()

    symbols_path = Path(args.symboled_symbols)
    features_path = Path(args.stripped_features)
    out_dir = Path(args.out_dir)
    if not symbols_path.exists():
        raise SystemExit(f"符号文件不存在: {symbols_path}")
    if not features_path.exists():
        raise SystemExit(f"特征文件不存在: {features_path}")

    # 有符号：地址 → 真实函数名（仅保留非自动生成名）
    with open(symbols_path, "r", encoding="utf-8") as f:
        symbols_data = json.load(f)
    addr_to_name = {}
    for func in symbols_data.get("functions", []):
        addr = func.get("address", "")
        name = (func.get("name") or "").strip()
        if not addr or not name or is_auto_generated_name(name):
            continue
        addr_to_name[normalize_address(addr)] = name

    # 脱符号特征：按地址与有符号对齐，得到 ground_truth
    with open(features_path, "r", encoding="utf-8") as f:
        features_data = json.load(f)
    ground_truth = {}
    for func in features_data.get("functions", []):
        addr = func.get("basic_info", {}).get("address", "")
        addr_norm = normalize_address(addr)
        if addr_norm in addr_to_name:
            ground_truth[addr_norm] = addr_to_name[addr_norm]

    out_dir.mkdir(parents=True, exist_ok=True)
    gt_path = out_dir / "ground_truth.json"
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2, ensure_ascii=False)

    test_features_path = out_dir / "test_features.json"
    shutil.copy2(features_path, test_features_path)

    print(f"已写入: {gt_path} ({len(ground_truth)} 条 ground truth)")
    print(f"已复制脱符号特征: {test_features_path}")
    print()
    print("下一步:")
    print("  1) 用「有符号符号 + 脱符号特征」建符号库（自对比必须用脱符号特征建库，准确率才高）:")
    print(f"     python scripts/build_symbol_library.py -s <有符号符号.json> -f {test_features_path} -o data/symbols/symbol_library_self.json")
    print("  2) 推理:")
    print(f"     python scripts/inference.py {test_features_path} -o results/self_eval/predictions.json -l data/symbols/symbol_library_self.json -t 0.5")
    print("  3) 评估:")
    print(f"     python scripts/evaluate.py results/self_eval/predictions.json -g {gt_path} -o results/self_eval/eval.json")


if __name__ == "__main__":
    main()
