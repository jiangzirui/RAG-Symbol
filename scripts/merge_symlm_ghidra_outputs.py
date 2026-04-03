#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合并 SymLM 二进制经 Ghidra 提取后的 features/symbols，生成 training_data 与符号库。
用法:
  python scripts/merge_symlm_ghidra_outputs.py
  python scripts/merge_symlm_ghidra_outputs.py --features-dir "E:/ghidra/data/features" --symbols-dir "E:/ghidra/data/symbols"
  python scripts/merge_symlm_ghidra_outputs.py --processed-list data/symlm_processed_list.txt
"""

import argparse
import json
from pathlib import Path
import sys

# 项目根（symbol_recovery_system）
SCRIPT_DIR = Path(__file__).resolve().parent
SYS_ROOT = SCRIPT_DIR.parent
if str(SYS_ROOT) not in sys.path:
    sys.path.insert(0, str(SYS_ROOT))


def _norm(s: str) -> str:
    return (s or "").strip().replace("0x", "").upper()


def find_pairs(features_dir: Path, symbols_dir: Path, processed_list: Path = None):
    """
    在 features_dir 和 symbols_dir 中按「程序名_架构」配对 *_features.json 与 *_symbols.json。
    若提供 processed_list，则只考虑与列表中文件名（不含路径）匹配的程序名。
    """
    allowed_bases = set()
    if processed_list and processed_list.exists():
        with open(processed_list, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # 行是完整路径，取文件名不含扩展名作为程序名（如 foo.exe -> foo）
                stem = Path(line).stem
                if stem:
                    allowed_bases.add(stem)

    features_dir = Path(features_dir)
    symbols_dir = Path(symbols_dir)
    if not features_dir.exists():
        return [], f"特征目录不存在: {features_dir}"
    if not symbols_dir.exists():
        return [], f"符号目录不存在: {symbols_dir}"

    # 所有 *_features.json -> 提取 stem（程序名_架构），与 symbols 配对
    feat_by_base = {}
    for f in features_dir.glob("*_features.json"):
        stem = f.stem.replace("_features", "")
        if allowed_bases:
            name_only = stem.split("_")[0] if "_" in stem else stem
            if name_only not in allowed_bases and stem not in allowed_bases:
                continue
        feat_by_base[stem] = f

    pairs = []
    for stem, feat_path in feat_by_base.items():
        sym_path = symbols_dir / f"{stem}_symbols.json"
        if not sym_path.exists():
            sym_path = symbols_dir / f"{stem}.json"
        if sym_path.exists():
            pairs.append((str(sym_path), str(feat_path)))
        else:
            # 无符号文件也可用于特征（建库时仅用有符号的；training_data 需有 label，会跳过无符号）
            pass
    return pairs, None


def main():
    parser = argparse.ArgumentParser(description="合并 SymLM Ghidra 输出并生成 training_data + 符号库")
    parser.add_argument("--features-dir", default=None, help="特征目录（默认: ../../data/features）")
    parser.add_argument("--symbols-dir", default=None, help="符号目录（默认: ../../data/symbols）")
    parser.add_argument("--processed-list", default=None, help="run_symlm_binaries 生成的文件列表，用于过滤")
    parser.add_argument("-o", "--out-dir", default=None, help="输出目录（默认: data）")
    parser.add_argument("--no-library", action="store_true", help="不构建符号库，仅生成 training_data")
    args = parser.parse_args()

    # 默认目录：Ghidra 根下 data（headless 写出的位置）
    base_data = SYS_ROOT.parent / "data"  # ghidra_12.0_PUBLIC/data
    features_dir = Path(args.features_dir) if args.features_dir else (base_data / "features")
    symbols_dir = Path(args.symbols_dir) if args.symbols_dir else (base_data / "symbols")
    out_dir = Path(args.out_dir) if args.out_dir else (SYS_ROOT / "data")
    processed_list = Path(args.processed_list) if args.processed_list else (SYS_ROOT / "data" / "symlm_processed_list.txt")

    pairs, err = find_pairs(features_dir, symbols_dir, processed_list)
    if err:
        print(err)
        sys.exit(1)
    if not pairs:
        print("未找到任何 (symbols, features) 配对。请检查:")
        print(f"  特征目录: {features_dir}")
        print(f"  符号目录: {symbols_dir}")
        print(f"  列表文件（可选）: {processed_list}")
        sys.exit(1)

    print(f"找到 {len(pairs)} 对 (symbols, features)")
    symbols_files = [p[0] for p in pairs]
    features_files = [p[1] for p in pairs]

    out_dir.mkdir(parents=True, exist_ok=True)
    training_out = out_dir / "training" / "training_data_symlm.json"
    training_out.parent.mkdir(parents=True, exist_ok=True)

    # 1) prepare_training_data
    import importlib.util
    spec = importlib.util.spec_from_file_location("prepare_training_data", SCRIPT_DIR / "prepare_training_data.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    prepare_training_data = mod.prepare_training_data

    print("生成 training_data_symlm.json ...")
    prepare_training_data(symbols_files, features_files, str(training_out))
    print(f"  已写入: {training_out}")

    # 2) build_symbol_library（可选）
    if not args.no_library:
        lib_out = out_dir / "symbols" / "symbol_library_symlm.json"
        lib_out.parent.mkdir(parents=True, exist_ok=True)
        spec = importlib.util.spec_from_file_location("build_symbol_library", SCRIPT_DIR / "build_symbol_library.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        build_symbol_library = mod.build_symbol_library
        print("构建符号库 symbol_library_symlm.json ...")
        build_symbol_library(symbols_files, features_files, str(lib_out))
        print(f"  已写入: {lib_out}")

    print("完成。后续可:")
    print(f"  1) 从 training_data 制备测试集: python scripts/prepare_test_set.py {training_out} -o data/test_symlm_ours --max-functions 500")
    print(f"  2) 推理: python scripts/inference.py data/test_symlm_ours/test_features.json -o results/exp_symlm_ours/predictions_multi.json -l {out_dir}/symbols/symbol_library_symlm.json -t 0.5")
    print(f"  3) 评估: python scripts/evaluate.py results/exp_symlm_ours/predictions_multi.json -g data/test_symlm_ours/ground_truth.json -o results/exp_symlm_ours/eval_multi.json")


if __name__ == "__main__":
    main()
