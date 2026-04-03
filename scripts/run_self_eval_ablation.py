#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自对比 + 消融 + 多阈值：一键得到多样、可比的实验数据（不同 F1/Recall、消融对比）。
- 用 self_eval 数据（脱符号特征 + ground_truth + 符号库）
- 推理一次（低阈值 0.5）后按多种 confidence 阈值评估 → 不同 P/R/F1
- 跑多种消融（完整、去 RAG、去语义/CFG/统计、两两去、仅代码等）并评估
输出：results/self_eval/ablation_and_thresholds.json、ablation_and_thresholds.md
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 自对比默认路径
DEFAULT_FEATURES = ROOT / "data" / "self_eval" / "test_features.json"
DEFAULT_GT = ROOT / "data" / "self_eval" / "ground_truth.json"
DEFAULT_LIB = ROOT / "data" / "symbols" / "symbol_library_self.json"
DEFAULT_OUT = ROOT / "results" / "self_eval"


def run_cmd(cmd: list, cwd: str = None) -> bool:
    ret = subprocess.run(cmd, cwd=cwd or str(ROOT))
    return ret.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="自对比消融与多阈值实验，输出汇总表")
    parser.add_argument("--features", "-f", default=str(DEFAULT_FEATURES), help="测试特征 JSON")
    parser.add_argument("--ground-truth", "-g", default=str(DEFAULT_GT), help="Ground truth JSON")
    parser.add_argument("--library", "-l", default=str(DEFAULT_LIB), help="符号库 JSON")
    parser.add_argument("--out-dir", "-o", default=str(DEFAULT_OUT), help="结果目录")
    parser.add_argument("--build-library", action="store_true", help="先建库（-s symbols_from_ground_truth -f test_features）")
    parser.add_argument("--inference-threshold", type=float, default=0.5, help="推理时相似度阈值（低一点以保留更多预测供阈值分析）")
    parser.add_argument("--confidence-thresholds", nargs="+", type=float,
                        default=[0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9],
                        metavar="T", help="评估时置信度阈值列表，用于得到不同 P/R/F1")
    parser.add_argument("--skip-full", action="store_true",
                        help="跳过完整推理与多阈值评估，仅用已有 predictions_ablation_full + eval_confidence_t*.json 做消融并写汇总")
    parser.add_argument("--complete", action="store_true",
                        help="补齐实验：仅CFG、仅统计、RAG(无LLM)、RAG(LLM)、CodeBERT；需配合 --complete-build 先建对应库")
    parser.add_argument("--complete-build", action="store_true",
                        help="建库时同时生成 cfg_only / statistical_only / codebert 库（供 --complete 使用）")
    args = parser.parse_args()

    features_path = Path(args.features)
    gt_path = Path(args.ground_truth)
    lib_path = Path(args.library)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not features_path.exists():
        print(f"特征文件不存在: {features_path}")
        return 1
    if not gt_path.exists():
        print(f"Ground truth 不存在: {gt_path}")
        return 1

    # 可选：先建库（需先有 symbols_from_ground_truth.json，见 prepare_self_eval）
    if args.build_library:
        symbols_gt = gt_path.parent / "symbols_from_ground_truth.json"
        if not symbols_gt.exists():
            print("建库需要 data/self_eval/symbols_from_ground_truth.json，请先运行 prepare_self_eval.py 或 run_self_eval_rebuild_and_eval.bat 第一步")
            return 1
        print("========== 建库 ==========")
        if not run_cmd([
            sys.executable, str(ROOT / "scripts" / "build_symbol_library.py"),
            "-s", str(symbols_gt), "-f", str(features_path), "-o", str(lib_path),
        ]):
            print("建库失败")
            return 1
        if not lib_path.exists():
            print("符号库未生成")
            return 1

    # 可选：建仅CFG / 仅统计 / CodeBERT 库（供 --complete 用）
    symbols_gt = gt_path.parent / "symbols_from_ground_truth.json"
    lib_cfg = lib_path.parent / "symbol_library_self_cfg.json"
    lib_statistical = lib_path.parent / "symbol_library_self_statistical.json"
    lib_codebert = lib_path.parent / "symbol_library_self_codebert.json"
    if args.complete_build and symbols_gt.exists():
        print("\n========== 建库（仅CFG）==========")
        run_cmd([sys.executable, str(ROOT / "scripts" / "build_symbol_library.py"),
                 "-s", str(symbols_gt), "-f", str(features_path), "-o", str(lib_cfg), "--cfg-only"])
        print("\n========== 建库（仅统计）==========")
        run_cmd([sys.executable, str(ROOT / "scripts" / "build_symbol_library.py"),
                 "-s", str(symbols_gt), "-f", str(features_path), "-o", str(lib_statistical), "--statistical-only"])
        print("\n========== 建库（CodeBERT 全特征）==========")
        run_cmd([sys.executable, str(ROOT / "scripts" / "build_symbol_library.py"),
                 "-s", str(symbols_gt), "-f", str(features_path), "-o", str(lib_codebert),
                 "--config-override", "config/config_codebert.yaml"])

    results = {"ablation": [], "confidence_thresholds": [], "config": {}}
    results["config"] = {
        "features": str(features_path),
        "ground_truth": str(gt_path),
        "library": str(lib_path),
        "inference_threshold": args.inference_threshold,
        "skip_full": args.skip_full,
    }

    pred_full = out_dir / "predictions_ablation_full.json"

    if not args.skip_full:
        # ---------- 1) 多置信度阈值（同一份预测，不同 P/R/F1）----------
        print("\n========== 推理（完整模型，阈值 %.2f）==========" % args.inference_threshold)
        cmd_infer = [
            sys.executable, str(ROOT / "scripts" / "inference.py"), str(features_path),
            "-o", str(pred_full), "-l", str(lib_path), "-t", str(args.inference_threshold),
        ]
        if not run_cmd(cmd_infer):
            print("推理失败")
            return 1

        print("\n========== 多置信度阈值评估 ==========")
        for t in args.confidence_thresholds:
            eval_file = out_dir / f"eval_confidence_t{t}.json"
            if run_cmd([
                sys.executable, str(ROOT / "scripts" / "evaluate.py"), str(pred_full),
                "-g", str(gt_path), "-o", str(eval_file), "--no-print-samples",
                "--confidence-threshold", str(t),
            ]):
                try:
                    ev = json.loads(eval_file.read_text(encoding="utf-8"))
                    m = ev.get("metrics", {})
                    results["confidence_thresholds"].append({
                        "confidence_threshold": t,
                        "accuracy": m.get("accuracy"),
                        "precision": m.get("precision"),
                        "recall": m.get("recall"),
                        "f1": m.get("f1"),
                        "correct": m.get("correct"),
                        "total": m.get("total"),
                        "predicted_count": m.get("predicted_count"),
                    })
                except Exception as e:
                    results["confidence_thresholds"].append({"confidence_threshold": t, "error": str(e)})
    else:
        # 从已有文件加载多阈值结果
        print("\n========== 使用已有完整推理与多阈值评估结果 ==========")
        for t in args.confidence_thresholds:
            eval_file = out_dir / f"eval_confidence_t{t}.json"
            if eval_file.exists():
                try:
                    ev = json.loads(eval_file.read_text(encoding="utf-8"))
                    m = ev.get("metrics", {})
                    results["confidence_thresholds"].append({
                        "confidence_threshold": t,
                        "accuracy": m.get("accuracy"),
                        "precision": m.get("precision"),
                        "recall": m.get("recall"),
                        "f1": m.get("f1"),
                        "correct": m.get("correct"),
                        "total": m.get("total"),
                        "predicted_count": m.get("predicted_count"),
                    })
                except Exception as e:
                    results["confidence_thresholds"].append({"confidence_threshold": t, "error": str(e)})
        if not results["confidence_thresholds"]:
            print("未找到 eval_confidence_t*.json，多阈值表为空")

    # ---------- 2) 消融实验 ----------
    # (name, extra_args, library_override or None=default lib_path, skip_if_no_lib)
    ablation_configs = [
        ("ablation_full", [], None, False),
        ("ablation_no_library", ["--no-library"], None, False),
        ("ablation_wo_semantic", ["--no-semantic"], None, False),
        ("ablation_wo_cfg", ["--no-cfg"], None, False),
        ("ablation_wo_statistical", ["--no-statistical"], None, False),
        ("ablation_wo_semantic_cfg", ["--no-semantic", "--no-cfg"], None, False),
        ("ablation_wo_semantic_statistical", ["--no-semantic", "--no-statistical"], None, False),
        ("ablation_wo_cfg_statistical", ["--no-cfg", "--no-statistical"], None, False),
        ("ablation_code_only", ["--no-semantic", "--no-cfg", "--no-statistical"], None, False),
        ("ablation_multi_attention", ["--use-attention"], None, False),
    ]
    if args.complete:
        ablation_configs += [
            ("single_cfg", ["--cfg-only"], lib_cfg, True),
            ("single_statistical", ["--statistical-only"], lib_statistical, True),
            ("rag_no_llm", ["--rag", "--rag-no-llm"], None, False),
            ("rag_llm", ["--rag"], None, False),
            ("codebert", ["--config", str(ROOT / "config" / "config_codebert.yaml"),
             "--no-semantic", "--no-cfg", "--no-statistical"], lib_codebert, True),
        ]

    for item in ablation_configs:
        name = item[0]
        extra = item[1]
        lib_override = item[2] if len(item) > 2 else None
        skip_if_no_lib = item[3] if len(item) > 3 else False
        pred_file = out_dir / f"predictions_{name}.json"
        eval_file = out_dir / f"eval_{name}.json"
        if args.skip_full and name == "ablation_full" and eval_file.exists():
            try:
                ev = json.loads(eval_file.read_text(encoding="utf-8"))
                m = ev.get("metrics", {})
                results["ablation"].append({
                    "method": name,
                    "accuracy": m.get("accuracy"),
                    "precision": m.get("precision"),
                    "recall": m.get("recall"),
                    "f1": m.get("f1"),
                    "correct": m.get("correct"),
                    "total": m.get("total"),
                    "predicted_count": m.get("predicted_count"),
                })
            except Exception as e:
                results["ablation"].append({"method": name, "error": str(e)})
            continue
        use_lib = "no_library" not in name
        lib_to_use = (lib_override if lib_override is not None else lib_path) if use_lib else None
        if use_lib and lib_to_use and skip_if_no_lib and not Path(lib_to_use).exists():
            results["ablation"].append({"method": name, "error": f"库不存在: {lib_to_use}"})
            continue
        if use_lib and not lib_to_use:
            lib_to_use = lib_path
        cmd_infer = [
            sys.executable, str(ROOT / "scripts" / "inference.py"), str(features_path),
            "-o", str(pred_file), "-t", str(args.inference_threshold),
        ]
        if lib_to_use and Path(lib_to_use).exists():
            cmd_infer += ["-l", str(lib_to_use)]
        cmd_infer += extra
        print(f"\n[{name}] 推理...")
        if not run_cmd(cmd_infer):
            results["ablation"].append({"method": name, "error": "inference_failed"})
            continue
        if not run_cmd([
            sys.executable, str(ROOT / "scripts" / "evaluate.py"), str(pred_file),
            "-g", str(gt_path), "-o", str(eval_file), "--no-print-samples",
        ]):
            results["ablation"].append({"method": name, "error": "evaluate_failed"})
            continue
        try:
            ev = json.loads(eval_file.read_text(encoding="utf-8"))
            m = ev.get("metrics", {})
            results["ablation"].append({
                "method": name,
                "accuracy": m.get("accuracy"),
                "precision": m.get("precision"),
                "recall": m.get("recall"),
                "f1": m.get("f1"),
                "correct": m.get("correct"),
                "total": m.get("total"),
                "predicted_count": m.get("predicted_count"),
            })
        except Exception as e:
            results["ablation"].append({"method": name, "error": str(e)})

    # ---------- 写入 JSON ----------
    out_json = out_dir / "ablation_and_thresholds.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n已写入: {out_json}")

    # ---------- 写入 Markdown 表 ----------
    out_md = out_dir / "ablation_and_thresholds.md"
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("# 自对比：多阈值与消融实验结果\n\n")
        f.write("## 1. 多置信度阈值（同一推理结果，不同 P/R/F1）\n\n")
        f.write("| Confidence ≥ | Accuracy | Precision | Recall | F1 | Correct | Total | 有预测数 |\n")
        f.write("|--------------|----------|-----------|--------|-----|---------|-------|----------|\n")
        for r in results["confidence_thresholds"]:
            if "error" in r:
                f.write(f"| {r['confidence_threshold']} | - | - | - | - | - | - | - |\n")
                continue
            acc = f"{r['accuracy']:.4f}" if r.get("accuracy") is not None else "-"
            pr = f"{r['precision']:.4f}" if r.get("precision") is not None else "-"
            rc = f"{r['recall']:.4f}" if r.get("recall") is not None else "-"
            f1 = f"{r['f1']:.4f}" if r.get("f1") is not None else "-"
            c = r.get("correct", "-")
            t = r.get("total", "-")
            pc = r.get("predicted_count", "-")
            f.write(f"| {r['confidence_threshold']} | {acc} | {pr} | {rc} | {f1} | {c} | {t} | {pc} |\n")

        f.write("\n## 2. 消融实验\n\n")
        f.write("| 配置 | Accuracy | Precision | Recall | F1 | Correct/Total | 有预测数 |\n")
        f.write("|------|----------|-----------|--------|-----|---------------|----------|\n")
        for r in results["ablation"]:
            if "error" in r:
                f.write(f"| {r['method']} | - | - | - | - | - | {r.get('error', '')} |\n")
                continue
            acc = f"{r['accuracy']:.4f}" if r.get("accuracy") is not None else "-"
            pr = f"{r['precision']:.4f}" if r.get("precision") is not None else "-"
            rc = f"{r['recall']:.4f}" if r.get("recall") is not None else "-"
            f1 = f"{r['f1']:.4f}" if r.get("f1") is not None else "-"
            ct = f"{r.get('correct', '-')}/{r.get('total', '-')}"
            pc = r.get("predicted_count", "-")
            f.write(f"| {r['method']} | {acc} | {pr} | {rc} | {f1} | {ct} | {pc} |\n")

    print(f"已写入: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
