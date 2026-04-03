#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评估脚本：根据推理结果与 ground truth 计算 Accuracy、Precision、Recall、F1 等指标。
支持多级评估：exact（一字不差）、normalized（规范后比对）、synonym（允许同义/多参考答案）。
用于论文实验部分的定量评估。
"""

import argparse
import json
import re
from pathlib import Path
from collections import defaultdict


# 常见符号名规范化：多种写法视为同一（可选，用于 normalized 档）
SYMBOL_NORMALIZE_ABBREV = {
    "mem_copy": "memcpy", "mem_cpy": "memcpy",
    "string_length": "strlen", "str_len": "strlen", "get_length": "strlen",
    "memory_set": "memset", "mem_set": "memset",
    "string_compare": "strcmp", "str_cmp": "strcmp",
}


def normalize_address(addr: str) -> str:
    """统一地址格式便于匹配（去 0x、转大写）。"""
    if not addr:
        return ""
    s = str(addr).strip().replace("0x", "").upper()
    return s


def normalize_symbol(s: str, metric: str) -> str:
    """
    符号名规范化，用于 normalized / synonym 档比对。
    - exact: 仅 strip
    - normalized: 小写、空格/多下划线规整、可选缩写统一
    """
    if not s:
        return ""
    s = s.strip()
    if metric == "exact":
        return s
    s = s.lower().replace(" ", "_")
    s = re.sub(r"_+", "_", s).strip("_")
    return SYMBOL_NORMALIZE_ABBREV.get(s, s)


def load_predictions(path: str, confidence_threshold: float = None) -> dict:
    """
    加载推理结果 JSON，返回 address -> { predicted_name, original_name, confidence }。
    若指定 confidence_threshold，则 confidence < 该阈值的预测视为“未预测”（predicted_name 置空），
    用于同一份推理结果在不同阈值下得到不同的 P/R/F1。
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    by_addr = {}
    for rec in data.get("recovered_symbols", []):
        addr = rec.get("address") or rec.get("basic_info", {}).get("address")
        if addr is None:
            continue
        key = normalize_address(addr)
        pred_name = (rec.get("predicted_name") or "").strip()
        conf = float(rec.get("confidence", 0.0))
        if confidence_threshold is not None and conf < confidence_threshold:
            pred_name = ""
        by_addr[key] = {
            "predicted_name": pred_name,
            "original_name": rec.get("original_name") or "",
            "confidence": conf,
        }
    return by_addr


def load_ground_truth(path: str) -> dict:
    """
    加载 ground truth 文件。返回 dict[address_key] = list[acceptable_names]。
    支持格式：
    1) { "address1": "symbol1", ... } -> 单参考答案
    2) { "address1": ["s1", "s2"], ... } -> 多参考答案（同义/语义等价）
    3) { "address1": {"primary": "s1", "synonyms": ["s2"]}, ... }
    4) { "ground_truth": [ {"address": "...", "symbol": "..."}, ... ] }
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    by_addr = {}
    if "ground_truth" in data:
        for item in data["ground_truth"]:
            addr = item.get("address")
            sym = item.get("symbol") or item.get("name") or item.get("label")
            if addr is not None and sym is not None:
                key = normalize_address(addr)
                by_addr[key] = [str(sym).strip()]
    else:
        for addr, sym in data.items():
            key = normalize_address(addr)
            if isinstance(sym, str):
                by_addr[key] = [sym.strip()]
            elif isinstance(sym, list):
                by_addr[key] = [str(x).strip() for x in sym if x]
            elif isinstance(sym, dict):
                primary = (sym.get("primary") or sym.get("symbol") or "").strip()
                syns = [str(x).strip() for x in sym.get("synonyms", []) if x]
                by_addr[key] = ([primary] if primary else []) + syns
    return by_addr


def load_synonym_file(path: str) -> dict:
    """加载同义词扩展：address_key -> list[extra_acceptable_names]。"""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    out = {}
    for addr, names in data.items():
        key = normalize_address(addr)
        if isinstance(names, str):
            out.setdefault(key, []).append(names.strip())
        else:
            out.setdefault(key, []).extend([str(x).strip() for x in names if x])
    return out


def compute_metrics(
    pred_by_addr: dict,
    gt_by_addr: dict,
    metric: str = "exact",
    ignore_case: bool = False,
    synonym_by_addr: dict = None,
) -> dict:
    """
    根据预测与 ground truth 计算指标。
    gt_by_addr: address_key -> list[acceptable_names]
    metric: exact | normalized | synonym
    """
    synonym_by_addr = synonym_by_addr or {}

    def refs_for_addr(addr):
        refs = list(gt_by_addr.get(addr, []))
        refs.extend(synonym_by_addr.get(addr, []))
        return refs

    def is_match(pred_name: str, acceptable_refs: list) -> bool:
        if not pred_name or not acceptable_refs:
            return False
        pred_n = pred_name.strip()
        if metric == "exact":
            if ignore_case:
                return any(pred_n.lower() == r.strip().lower() for r in acceptable_refs)
            return any(pred_n == r.strip() for r in acceptable_refs)
        pred_norm = normalize_symbol(pred_n, "normalized")
        for r in acceptable_refs:
            if pred_norm == normalize_symbol(r.strip(), "normalized"):
                return True
        return False

    correct = 0
    total = 0
    true_positives = 0
    predicted_positives = 0
    actual_positives = 0
    per_sample = []

    for addr, acceptable_list in gt_by_addr.items():
        if not acceptable_list:
            continue
        total += 1
        actual_positives += 1
        pred = pred_by_addr.get(addr, {})
        pred_name = (pred.get("predicted_name") or "").strip()
        predicted_positives += 1 if pred_name else 0
        refs = refs_for_addr(addr)
        is_correct = is_match(pred_name, refs)
        if is_correct:
            correct += 1
            true_positives += 1
        per_sample.append({
            "address": addr,
            "ground_truth": acceptable_list[0],
            "acceptable_refs": refs,
            "predicted": pred_name,
            "correct": is_correct,
        })

    accuracy = (correct / total) if total else 0.0
    # 在「每个样本都算一个要预测的符号」设定下：Precision = 预测对的 / 预测数, Recall = 预测对的 / 总数
    precision = (true_positives / predicted_positives) if predicted_positives else 0.0
    recall = (correct / total) if total else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "correct": correct,
        "total": total,
        "predicted_count": predicted_positives,
        "ignore_case": ignore_case,
        "metric": metric,
        "per_sample": per_sample,
    }


def main():
    parser = argparse.ArgumentParser(description="评估符号恢复结果：Accuracy / Precision / Recall / F1")
    parser.add_argument("predictions", help="推理结果 JSON 路径（*_inference.json）")
    parser.add_argument(
        "--ground-truth",
        "-g",
        help="Ground truth JSON：地址 -> 符号，或 ground_truth 列表",
    )
    parser.add_argument(
        "--use-original-as-gt",
        action="store_true",
        help="用推理结果中的 original_name 作为真实符号（适用于对带符号二进制做推理时的自检）",
    )
    parser.add_argument("--ignore-case", action="store_true", help="比较符号时忽略大小写")
    parser.add_argument(
        "--metric",
        choices=["exact", "normalized", "synonym"],
        default="exact",
        help="评估档：exact=一字不差，normalized=规范后比对，synonym=允许同义/多参考答案",
    )
    parser.add_argument(
        "--synonym-file",
        metavar="JSON",
        help="同义词扩展 JSON：address -> [可接受名称列表]，用于 synonym 档",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=None,
        metavar="T",
        help="仅将 confidence >= T 的预测计为有效预测，低于 T 视为未预测，从而得到不同 P/R/F1（例: 0.6, 0.8）",
    )
    parser.add_argument("-o", "--output", help="将指标与 per_sample 写入此 JSON 文件")
    parser.add_argument("--no-print-samples", action="store_true", help="输出 JSON 中不包含 per_sample（文件更小）")
    args = parser.parse_args()

    pred_path = Path(args.predictions)
    if not pred_path.exists():
        raise SystemExit(f"预测文件不存在: {pred_path}")

    pred_by_addr = load_predictions(str(pred_path), confidence_threshold=args.confidence_threshold)

    if args.use_original_as_gt:
        gt_by_addr = {}
        for addr, rec in pred_by_addr.items():
            name = (rec.get("original_name") or "").strip()
            if addr and name:
                gt_by_addr[addr] = name
    elif args.ground_truth:
        gt_path = Path(args.ground_truth)
        if not gt_path.exists():
            raise SystemExit(f"Ground truth 文件不存在: {gt_path}")
        gt_by_addr = load_ground_truth(str(gt_path))
    else:
        raise SystemExit("请指定 --ground-truth 或 --use-original-as-gt")

    if not gt_by_addr:
        raise SystemExit("Ground truth 为空，请检查文件格式或 --use-original-as-gt 的数据")

    synonym_by_addr = {}
    if args.synonym_file:
        sp = Path(args.synonym_file)
        if sp.exists():
            synonym_by_addr = load_synonym_file(str(sp))

    metrics = compute_metrics(
        pred_by_addr,
        gt_by_addr,
        metric=args.metric,
        ignore_case=args.ignore_case,
        synonym_by_addr=synonym_by_addr,
    )

    out = {
        "predictions_file": str(pred_path),
        "ground_truth_file": args.ground_truth or "(use-original-as-gt)",
        "confidence_threshold": args.confidence_threshold,
        "metrics": {
            "accuracy": metrics["accuracy"],
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "f1": metrics["f1"],
            "correct": metrics["correct"],
            "total": metrics["total"],
            "predicted_count": metrics["predicted_count"],
        "ignore_case": metrics["ignore_case"],
        "metric": metrics.get("metric", "exact"),
    },
    }
    if not args.no_print_samples:
        out["per_sample"] = metrics["per_sample"]

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"已写入: {args.output}")

    print("\n===== 评估结果 =====")
    print(f"  Metric:    {metrics.get('metric', 'exact')}")
    print(f"  Accuracy:  {metrics['accuracy']:.4f}  ({metrics['correct']}/{metrics['total']})")
    print(f"  Precision: {metrics['precision']:.4f}")
    print(f"  Recall:    {metrics['recall']:.4f}")
    print(f"  F1:        {metrics['f1']:.4f}")
    print(f"  有预测数:  {metrics['predicted_count']}/{metrics['total']}")
    if metrics["predicted_count"] == metrics["total"] and metrics["total"] > 0:
        print("  （对全部样本都做了预测时，Precision=Recall=Accuracy，F1 与之相同；若提高推理阈值使部分不预测，P/R 会分化）")
    print("====================\n")

    return out


if __name__ == "__main__":
    main()
