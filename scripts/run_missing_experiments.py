#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
只跑「未跑完」的补齐实验：rag_llm、codebert。
若某实验的 predictions_*.json 已存在则跳过（可删掉该文件后重跑）。
用法：在 symbol_recovery_system 目录下
  python scripts/run_missing_experiments.py
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEATURES = ROOT / "data" / "self_eval" / "test_features.json"
GT = ROOT / "data" / "self_eval" / "ground_truth.json"
LIB = ROOT / "data" / "symbols" / "symbol_library_self.json"
LIB_CODEBERT = ROOT / "data" / "symbols" / "symbol_library_self_codebert.json"
OUT_DIR = ROOT / "results" / "self_eval"


def run(cmd: list) -> bool:
    return subprocess.run(cmd, cwd=str(ROOT)).returncode == 0


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    experiments = []

    # 1) RAG + LLM
    pred_rag_llm = OUT_DIR / "predictions_rag_llm.json"
    if not pred_rag_llm.exists():
        experiments.append(("rag_llm", [
            sys.executable, str(ROOT / "scripts" / "inference.py"), str(FEATURES),
            "-o", str(pred_rag_llm), "-l", str(LIB), "--rag", "-t", "0.5",
        ]))
    else:
        print("[跳过] rag_llm 已有预测文件:", pred_rag_llm)

    # 2) CodeBERT（仅代码 + CodeBERT 库）
    pred_codebert = OUT_DIR / "predictions_codebert.json"
    if not pred_codebert.exists() and LIB_CODEBERT.exists():
        experiments.append(("codebert", [
            sys.executable, str(ROOT / "scripts" / "inference.py"), str(FEATURES),
            "-o", str(pred_codebert), "-l", str(LIB_CODEBERT),
            "--config", "config/config_codebert.yaml",
            "--no-semantic", "--no-cfg", "--no-statistical", "-t", "0.5",
        ]))
    elif not LIB_CODEBERT.exists():
        print("[跳过] codebert 需要库:", LIB_CODEBERT, "（请先运行 --complete-build 建库）")
    else:
        print("[跳过] codebert 已有预测文件:", pred_codebert)

    for name, cmd in experiments:
        print("\n========== 运行:", name, "==========")
        if not run(cmd):
            print(f"[失败] {name}")
            continue
        eval_file = OUT_DIR / f"eval_{name}.json"
        if run([
            sys.executable, str(ROOT / "scripts" / "evaluate.py"),
            str(OUT_DIR / f"predictions_{name}.json"), "-g", str(GT), "-o", str(eval_file), "--no-print-samples",
        ]):
            print(f"[完成] {name} ->", eval_file)
        else:
            print(f"[评估失败] {name}")

    print("\n如需把结果并入 ablation 表，请查看 results/self_eval/eval_rag_llm.json 与 eval_codebert.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
