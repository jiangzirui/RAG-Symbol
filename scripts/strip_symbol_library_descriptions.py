#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从符号库中移除 LLM 生成的描述字段，得到「无 LLM 描述」版符号库。
用于实验：对比「有 LLM 描述」与「无 LLM 描述」时的准确率（RAG 等会受影响，Full 向量匹配不受影响）。

用法:
  python scripts/strip_symbol_library_descriptions.py data/symbols/symbol_library_self.json -o data/symbols/symbol_library_self_no_desc.json
  # 然后用 -l data/symbols/symbol_library_self_no_desc.json 跑推理与评估
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def strip_descriptions(symbol_library_path: str, output_path: str) -> None:
    with open(symbol_library_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    symbols = data.get("symbols", {})
    removed = 0
    for name, ent in symbols.items():
        if ent.pop("description", None) is not None:
            removed += 1
        if ent.pop("description_details", None) is not None:
            removed += 1
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"已移除描述字段，共 {len(symbols)} 个符号（有描述并已删的约 {removed} 处）")
    print(f"输出: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="移除符号库中的 LLM 描述字段，用于「无 LLM 描述」准确率实验")
    parser.add_argument("symbol_library", help="符号库 JSON 路径")
    parser.add_argument("-o", "--output", required=True, help="输出路径（如 symbol_library_self_no_desc.json）")
    args = parser.parse_args()
    strip_descriptions(args.symbol_library, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
