#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 training_data.json（或任意含 address + label/symbol 的 JSON）生成 evaluate.py 所需的 ground_truth.json。
用法: python scripts/prepare_ground_truth.py data/training/training_data.json -o data/test/ground_truth.json
"""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="从训练/测试数据中提取 address -> symbol，生成 ground_truth.json")
    parser.add_argument("input", help="输入 JSON（含 functions 或 samples 列表，每项有 address 与 label/symbol）")
    parser.add_argument("-o", "--output", required=True, help="输出 ground_truth.json 路径")
    args = parser.parse_args()

    path = Path(args.input)
    if not path.exists():
        raise SystemExit(f"文件不存在: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("functions") or data.get("samples") or []
    if not items and isinstance(data, list):
        items = data

    gt = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        addr = item.get("address")
        symbol = item.get("label") or item.get("symbol") or item.get("name")
        if addr is None or symbol is None:
            continue
        key = str(addr).strip().replace("0x", "").upper()
        gt[key] = str(symbol).strip()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(gt, f, indent=2, ensure_ascii=False)

    print(f"已写入 {len(gt)} 条 ground truth: {out_path}")


if __name__ == "__main__":
    main()
