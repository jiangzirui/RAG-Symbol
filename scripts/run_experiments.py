#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实验运行脚本：按多种方法/配置跑推理并评估，汇总结果表格，便于论文实验部分使用。
用法示例：
  python scripts/run_experiments.py --features data/test/test_features.json \\
      --ground-truth data/test/ground_truth.json --symbol-library data/symbols/symbol_library_arm32.json \\
      --out-dir results/exp1
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# 项目根目录
ROOT = Path(__file__).resolve().parent.parent


def run_cmd(cmd: list, cwd: str = None) -> bool:
    ret = subprocess.run(cmd, cwd=cwd or str(ROOT))
    return ret.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="运行多种符号恢复方法并评估，输出汇总表")
    parser.add_argument("--features", "-f", required=True, help="测试集特征文件路径")
    parser.add_argument("--ground-truth", "-g", required=True, help="Ground truth JSON（地址->符号）")
    parser.add_argument("--symbol-library", "-l", default=None, help="符号库路径（不指定则用默认查找逻辑）")
    parser.add_argument("--out-dir", "-o", default="results/experiments", help="各方法推理与评估结果输出目录")
    parser.add_argument("--threshold", "-t", type=float, default=0.7, help="相似度阈值")
    parser.add_argument("--methods", nargs="+", default=["multi", "rag"],
                        help="要跑的方法: clap, multi, rag（可多选）")
    parser.add_argument("--ablation", action="store_true",
                        help="额外跑消融实验: full, w/o_semantic, w/o_cfg, w/o_statistical, 两两去除, no_library, code_only, multi_attention")
    parser.add_argument("--confidence-thresholds", nargs="+", type=float, default=None, metavar="T",
                        help="对首份预测做多阈值评估，得到不同 P/R/F1（例: --confidence-thresholds 0.5 0.6 0.7 0.8 0.9）")
    args = parser.parse_args()

    features_path = Path(args.features)
    gt_path = Path(args.ground_truth)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not features_path.exists():
        print(f"特征文件不存在: {features_path}")
        return 1
    if not gt_path.exists():
        print(f"Ground truth 不存在: {gt_path}")
        return 1

    lib_opt = ["-l", str(args.symbol_library)] if args.symbol_library else []
    results_table = []

    # 构建要跑的方法列表（含可选消融）
    run_list = list(args.methods)
    if args.ablation:
        run_list += [
            "ablation_full",
            "ablation_wo_semantic",
            "ablation_wo_cfg",
            "ablation_wo_statistical",
            "ablation_wo_semantic_cfg",
            "ablation_wo_semantic_statistical",
            "ablation_wo_cfg_statistical",
            "ablation_no_library",
            "ablation_code_only",
            "ablation_multi_attention",
        ]

    for method in run_list:
        name = method.lower()
        pred_file = out_dir / f"predictions_{name}.json"
        eval_file = out_dir / f"eval_{name}.json"

        # 1) 推理（no_library 时不传 -l）
        use_lib = (name != "ablation_no_library") and args.symbol_library
        cmd_infer = [
            sys.executable, str(ROOT / "scripts" / "inference.py"), str(features_path),
            "-o", str(pred_file), "-t", str(args.threshold)
        ] + (["-l", str(args.symbol_library)] if use_lib else [])

        if name == "rag":
            cmd_infer += ["--rag", "--rag-top-k", "10"]
        elif name == "ablation_wo_semantic":
            cmd_infer += ["--no-semantic"]
        elif name == "ablation_wo_cfg":
            cmd_infer += ["--no-cfg"]
        elif name == "ablation_wo_statistical":
            cmd_infer += ["--no-statistical"]
        elif name == "ablation_wo_semantic_cfg":
            cmd_infer += ["--no-semantic", "--no-cfg"]
        elif name == "ablation_wo_semantic_statistical":
            cmd_infer += ["--no-semantic", "--no-statistical"]
        elif name == "ablation_wo_cfg_statistical":
            cmd_infer += ["--no-cfg", "--no-statistical"]
        elif name == "ablation_no_library":
            cmd_infer += ["--no-library"]
        elif name == "ablation_code_only":
            cmd_infer += ["--no-semantic", "--no-cfg", "--no-statistical"]
        elif name == "ablation_multi_attention":
            cmd_infer += ["--use-attention"]
        # ablation_full: 不加任何消融参数（默认多特征加权）

        print(f"[{name}] 运行推理: {' '.join(cmd_infer)}")
        if not run_cmd(cmd_infer):
            print(f"[{name}] 推理失败，跳过")
            results_table.append({"method": name, "accuracy": None, "f1": None, "error": "inference_failed"})
            continue

        # 2) 评估
        cmd_eval = [
            sys.executable, str(ROOT / "scripts" / "evaluate.py"), str(pred_file),
            "-g", str(gt_path), "-o", str(eval_file), "--no-print-samples"
        ]
        print(f"[{name}] 运行评估: {' '.join(cmd_eval)}")
        if not run_cmd(cmd_eval):
            print(f"[{name}] 评估失败，跳过")
            results_table.append({"method": name, "accuracy": None, "f1": None, "error": "evaluate_failed"})
            continue

        try:
            ev = json.loads(eval_file.read_text(encoding="utf-8"))
            m = ev.get("metrics", {})
            results_table.append({
                "method": name,
                "accuracy": m.get("accuracy"),
                "precision": m.get("precision"),
                "recall": m.get("recall"),
                "f1": m.get("f1"),
                "correct": m.get("correct"),
                "total": m.get("total"),
            })
        except Exception as e:
            results_table.append({"method": name, "accuracy": None, "f1": None, "error": str(e)})

    # 2.5) 可选：对首份预测做多置信度阈值评估，得到不同 P/R/F1
    if args.confidence_thresholds and run_list:
        first_name = run_list[0].lower()
        first_pred = out_dir / f"predictions_{first_name}.json"
        if first_pred.exists():
            for t in args.confidence_thresholds:
                eval_t_file = out_dir / f"eval_confidence_t{t}.json"
                cmd_eval = [
                    sys.executable, str(ROOT / "scripts" / "evaluate.py"), str(first_pred),
                    "-g", str(gt_path), "-o", str(eval_t_file), "--no-print-samples",
                    "--confidence-threshold", str(t),
                ]
                if run_cmd(cmd_eval):
                    try:
                        ev = json.loads(eval_t_file.read_text(encoding="utf-8"))
                        m = ev.get("metrics", {})
                        results_table.append({
                            "method": f"confidence_threshold_{t}",
                            "accuracy": m.get("accuracy"),
                            "precision": m.get("precision"),
                            "recall": m.get("recall"),
                            "f1": m.get("f1"),
                            "correct": m.get("correct"),
                            "total": m.get("total"),
                        })
                    except Exception:
                        pass

    # 3) 汇总表
    summary_path = out_dir / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({"methods": results_table, "config": {"threshold": args.threshold}}, f, indent=2, ensure_ascii=False)

    # Markdown 表
    md_path = out_dir / "summary.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("| Method | Accuracy | Precision | Recall | F1 | Correct/Total |\n")
        f.write("|--------|----------|-----------|--------|-----|---------------|\n")
        for r in results_table:
            acc = f"{r['accuracy']:.4f}" if r.get("accuracy") is not None else "-"
            pr = f"{r['precision']:.4f}" if r.get("precision") is not None else "-"
            rc = f"{r['recall']:.4f}" if r.get("recall") is not None else "-"
            f1 = f"{r['f1']:.4f}" if r.get("f1") is not None else "-"
            ct = f"{r.get('correct', '-')}/{r.get('total', '-')}" if r.get("total") is not None else "-"
            f.write(f"| {r['method']} | {acc} | {pr} | {rc} | {f1} | {ct} |\n")

    print(f"\n汇总已写入: {summary_path}, {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
