#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试单次 LLM 调用耗时，用于验证「每函数一次调用」的耗时是否合理。
正常应在毫秒～数秒级；若达数十秒需检查模型（如是否开启深度思考）、网络或 API 限流。

用法（在 symbol_recovery_system 目录下）:
  python scripts/benchmark_llm_single_call.py
  python scripts/benchmark_llm_single_call.py --runs 5
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 与 RAG 使用的格式一致的短 prompt，便于反映真实单次调用耗时
MINIMAL_PROMPT = """你是一个二进制代码分析专家。请根据以下反编译代码与候选函数列表，完成符号恢复。

反编译代码：
```c
void copy_data(char *dst, const char *src, int n) { while (n--) *dst++ = *src++; }
```

**相似度阈值：0.70**（最高候选相似度：0.850）

候选函数列表（名称与相似度）：
1. **memcpy** (相似度: 0.850)
   描述: 内存拷贝
2. **strcpy** (相似度: 0.620)

请严格按以下 JSON 格式输出（仅输出 JSON）：
{"function_name": "memcpy", "source": "candidate", "confidence": 0.9, "reason": "语义一致"}
"""


def main():
    parser = argparse.ArgumentParser(description="测试单次 LLM 调用耗时")
    parser.add_argument("--runs", type=int, default=3, help="调用次数，取平均（默认 3）")
    args = parser.parse_args()

    try:
        from src.llm_client import get_default_llm_client
    except ImportError as e:
        print(f"无法导入 LLM 客户端: {e}")
        return 1

    print("加载 LLM 客户端...")
    client = get_default_llm_client()
    print(f"  模型: {client.model_name}")
    print(f"  单次 prompt 长度: {len(MINIMAL_PROMPT)} 字符")
    print()

    times_sec = []
    for i in range(args.runs):
        t0 = time.perf_counter()
        try:
            result = client.predict_function_name(MINIMAL_PROMPT)
            elapsed = time.perf_counter() - t0
            times_sec.append(elapsed)
            name = result.get("function_name", "?")
            print(f"  第 {i+1}/{args.runs} 次: {elapsed:.3f} s  -> function_name={name}")
        except Exception as e:
            print(f"  第 {i+1}/{args.runs} 次: 失败 - {e}")
    print()

    if not times_sec:
        print("无有效调用，请检查 API 配置与网络。")
        return 1

    avg = sum(times_sec) / len(times_sec)
    print("单次 LLM 调用耗时（秒）:")
    print(f"  最小: {min(times_sec):.3f} s")
    print(f"  平均: {avg:.3f} s")
    print(f"  最大: {max(times_sec):.3f} s")
    print()
    if avg > 10:
        print("说明: 平均超过 10 秒/次偏慢，常见原因：模型开启深度思考、网络延迟或 API 限流。")
        print("      RAG (LLM) 为「每个函数调用一次」LLM，故单函数均时 ≈ 单次调用耗时。")
    else:
        print("说明: 单次调用在合理范围；若表 5b 中 RAG (LLM) 单函数均时远大于此，请检查推理时是否有多余调用或计时口径。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
