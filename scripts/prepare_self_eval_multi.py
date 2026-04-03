#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多二进制自对比评估数据准备。
从多对「有符号符号文件 + 脱符号特征文件」生成合并的 ground_truth、test_features 与 symbols_from_ground_truth，
便于在多个二进制上统一建库、推理与评估，支撑论文级实验。

用法:
  # 方式一：清单文件（推荐）
  python scripts/prepare_self_eval_multi.py --manifest data/self_eval_multi/manifest.json -o data/self_eval_multi

  # 方式二：多组参数（顺序一一对应）
  python scripts/prepare_self_eval_multi.py \\
    --symboled-symbols data/symbols/prog1_symbols.json data/symbols/prog2_symbols.json \\
    --stripped-features data/features/prog1_stripped_features.json data/features/prog2_stripped_features.json \\
    --ids prog1 prog2 \\
    -o data/self_eval_multi

manifest.json 格式（每项一个二进制）:
  [
    {"binary_id": "vxworks_arm32_1", "symboled_symbols": "data/symbols/vx1_symbols.json", "stripped_features": "data/features/vx1_stripped_features.json"},
    {"binary_id": "vxworks_arm32_2", "symboled_symbols": "data/symbols/vx2_symbols.json", "stripped_features": "data/features/vx2_stripped_features.json"}
  ]

输出:
  - ground_truth.json: 键为 "binary_id|normalized_address"，值为符号名
  - test_features.json: 合并后的脱符号特征，每条 basic_info.address = "binary_id|原地址"
  - symbols_from_ground_truth.json: 供 build_symbol_library 使用（address 为 composite）
  - manifest_used.json: 实际使用的清单（便于复现）
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


def load_manifest(manifest_path: Path, root: Path) -> list:
    with open(manifest_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    out = []
    for item in raw:
        bid = item.get("binary_id") or item.get("id") or ""
        sym = item.get("symboled_symbols") or item.get("symbols")
        feat = item.get("stripped_features") or item.get("features")
        if not sym or not feat:
            continue
        sym_p = root / sym if not Path(sym).is_absolute() else Path(sym)
        feat_p = root / feat if not Path(feat).is_absolute() else Path(feat)
        if not sym_p.exists() or not feat_p.exists():
            continue
        if not bid:
            bid = sym_p.stem.replace("_symbols", "").replace("_symbol", "")
        out.append({"binary_id": bid, "symboled_symbols": sym_p, "stripped_features": feat_p})
    return out


def main():
    parser = argparse.ArgumentParser(description="多二进制自对比：合并 ground_truth、test_features、symbols_from_ground_truth")
    parser.add_argument("--manifest", "-m", help="清单 JSON：每项含 binary_id, symboled_symbols, stripped_features")
    parser.add_argument("--symboled-symbols", nargs="+", help="有符号符号文件列表（与 --stripped-features 一一对应）")
    parser.add_argument("--stripped-features", nargs="+", help="脱符号特征文件列表")
    parser.add_argument("--ids", nargs="+", help="每个二进制的 ID（与上面列表一一对应，缺省用文件名 stem）")
    parser.add_argument("-o", "--out-dir", default="data/self_eval_multi", help="输出目录")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = root / out_dir

    entries = []
    if args.manifest:
        manifest_path = Path(args.manifest)
        if not manifest_path.is_absolute():
            manifest_path = root / manifest_path
        if not manifest_path.exists():
            raise SystemExit(f"清单文件不存在: {manifest_path}")
        entries = load_manifest(manifest_path, root)
    elif args.symboled_symbols and args.stripped_features:
        if len(args.symboled_symbols) != len(args.stripped_features):
            raise SystemExit("--symboled-symbols 与 --stripped-features 数量必须相同")
        ids = args.ids or []
        for i, (sym, feat) in enumerate(zip(args.symboled_symbols, args.stripped_features)):
            sym_p = Path(sym) if Path(sym).is_absolute() else root / sym
            feat_p = Path(feat) if Path(feat).is_absolute() else root / feat
            if not sym_p.exists() or not feat_p.exists():
                raise SystemExit(f"文件不存在: {sym_p} 或 {feat_p}")
            bid = ids[i] if i < len(ids) else sym_p.stem.replace("_symbols", "").replace("_symbol", "")
            entries.append({"binary_id": bid, "symboled_symbols": sym_p, "stripped_features": feat_p})
    else:
        parser.print_help()
        raise SystemExit("请提供 --manifest 或同时提供 --symboled-symbols 与 --stripped-features")

    if not entries:
        raise SystemExit("没有有效的二进制条目")

    out_dir.mkdir(parents=True, exist_ok=True)
    ground_truth = {}
    all_functions = []
    symbols_functions = []
    meta = {"binaries": [], "total_functions": 0, "total_ground_truth": 0}

    for ent in entries:
        bid = ent["binary_id"]
        sym_path = ent["symboled_symbols"]
        feat_path = ent["stripped_features"]

        with open(sym_path, "r", encoding="utf-8") as f:
            symbols_data = json.load(f)
        addr_to_name = {}
        for func in symbols_data.get("functions", []):
            addr = func.get("address", "")
            name = (func.get("name") or "").strip()
            if not addr or not name or is_auto_generated_name(name):
                continue
            addr_to_name[normalize_address(addr)] = name

        with open(feat_path, "r", encoding="utf-8") as f:
            features_data = json.load(f)

        count_gt = 0
        for func in features_data.get("functions", []):
            basic = func.get("basic_info", {})
            addr = basic.get("address", "")
            addr_norm = normalize_address(addr)
            if addr_norm not in addr_to_name:
                continue
            name = addr_to_name[addr_norm]
            composite_addr = f"{bid}|{addr}" if addr else f"{bid}|0"
            composite_norm = f"{bid}|{addr_norm}"
            ground_truth[composite_norm] = name
            count_gt += 1
            # 复制函数并改写 address 为 composite，便于推理/评估时键一致
            func_copy = json.loads(json.dumps(func))
            if "basic_info" not in func_copy:
                func_copy["basic_info"] = {}
            func_copy["basic_info"]["address"] = composite_addr
            func_copy["basic_info"]["binary_id"] = bid
            all_functions.append(func_copy)
            symbols_functions.append({"address": composite_addr, "name": name})

        meta["binaries"].append({
            "binary_id": bid,
            "symboled_symbols": str(sym_path),
            "stripped_features": str(feat_path),
            "ground_truth_count": count_gt,
        })
        meta["total_functions"] += len(features_data.get("functions", []))
        meta["total_ground_truth"] += count_gt

    # 合并特征：保留第一个文件的全局字段（如 architecture），其余用第一个的
    with open(entries[0]["stripped_features"], "r", encoding="utf-8") as f:
        first_feat = json.load(f)
    merged_features = {
        "functions": all_functions,
        "metadata": {
            "source": "prepare_self_eval_multi",
            "num_binaries": len(entries),
            "binary_ids": [e["binary_id"] for e in entries],
        },
    }
    if "architecture" in first_feat:
        merged_features["architecture"] = first_feat["architecture"]

    gt_path = out_dir / "ground_truth.json"
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2, ensure_ascii=False)

    test_features_path = out_dir / "test_features.json"
    with open(test_features_path, "w", encoding="utf-8") as f:
        json.dump(merged_features, f, indent=2, ensure_ascii=False)

    symbols_gt_path = out_dir / "symbols_from_ground_truth.json"
    with open(symbols_gt_path, "w", encoding="utf-8") as f:
        json.dump({"functions": symbols_functions}, f, indent=2, ensure_ascii=False)

    manifest_used_path = out_dir / "manifest_used.json"
    with open(manifest_used_path, "w", encoding="utf-8") as f:
        json.dump([{"binary_id": e["binary_id"], "symboled_symbols": str(e["symboled_symbols"]), "stripped_features": str(e["stripped_features"])} for e in entries], f, indent=2, ensure_ascii=False)

    print(f"已写入: {gt_path} ({len(ground_truth)} 条 ground truth，{len(entries)} 个二进制)")
    print(f"已写入: {test_features_path} ({len(all_functions)} 个函数)")
    print(f"已写入: {symbols_gt_path} ({len(symbols_functions)} 条供建库)")
    print(f"已写入: {manifest_used_path}")
    print()
    print("下一步:")
    print("  1) 建库（脱符号特征 + 上述 symbols）：")
    print(f"     python scripts/build_symbol_library.py -s {symbols_gt_path} -f {test_features_path} -o data/symbols/symbol_library_self_multi.json")
    print("  2) 推理:")
    print(f"     python scripts/inference.py {test_features_path} -o results/self_eval_multi/predictions.json -l data/symbols/symbol_library_self_multi.json -t 0.5")
    print("  3) 评估:")
    print(f"     python scripts/evaluate.py results/self_eval_multi/predictions.json -g {gt_path} -o results/self_eval_multi/eval.json")


if __name__ == "__main__":
    main()
