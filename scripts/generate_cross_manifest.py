#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扫描「跨架构/跨优化」构建目录，为所有已具备 symbols.json 与 features.json 的子目录
生成 prepare_self_eval_multi 所需的 manifest.json。

目录约定：在 build_cross_binaries.py 输出下，每个可执行单位占一目录，内有：
  symbols.json   （Ghidra 从有符号二进制导出）
  features.json  （Ghidra 从 .stripped 导出）

用法:
  python scripts/generate_cross_manifest.py -d data/cross_build
  python scripts/generate_cross_manifest.py -d data/cross_build -o data/cross_build/manifest.json
"""

import argparse
import json
import sys
from pathlib import Path


def find_units(root: Path):
    """递归查找同时包含 symbols.json 与 features.json 的目录（作为一条 manifest 单位）。"""
    root = Path(root).resolve()
    units = []
    for d in root.rglob("*"):
        if not d.is_dir():
            continue
        symbols = d / "symbols.json"
        features = d / "features.json"
        if symbols.exists() and features.exists():
            units.append(d)
    return sorted(units)


def main():
    parser = argparse.ArgumentParser(
        description="根据跨架构/跨优化目录生成 prepare_self_eval_multi 的 manifest.json"
    )
    parser.add_argument("-d", "--dir", default="data/cross_build", help="构建根目录")
    parser.add_argument("-o", "--output", default=None, help="输出 manifest 路径（默认 <dir>/manifest.json）")
    args = parser.parse_args()

    root = Path(args.dir).resolve()
    if not root.exists():
        print(f"目录不存在: {root}")
        return 1

    units = find_units(root)
    if not units:
        print(f"在 {root} 下未找到同时包含 symbols.json 与 features.json 的子目录。")
        print("请先用 Ghidra 对 build_cross_binaries.py 生成的各可执行目录导出符号与特征。")
        return 1

    # 相对路径便于移植；若需绝对路径可改为 str(u.resolve())
    manifest = []
    for u in units:
        try:
            binary_id = "_".join(u.relative_to(root).parts)
        except ValueError:
            binary_id = f"unit_{len(manifest)}"
        symbols_path = u / "symbols.json"
        features_path = u / "features.json"
        try:
            cwd = Path.cwd()
            sym_str = str(symbols_path.relative_to(cwd))
            feat_str = str(features_path.relative_to(cwd))
        except ValueError:
            sym_str = str(symbols_path)
            feat_str = str(features_path)
        manifest.append({
            "binary_id": binary_id,
            "symboled_symbols": sym_str,
            "stripped_features": feat_str,
        })

    out_path = Path(args.output) if args.output else (root / "manifest.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"已生成 manifest：{out_path}，共 {len(manifest)} 条。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
