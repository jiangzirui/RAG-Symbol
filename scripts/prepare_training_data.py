#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练数据准备脚本
从有符号文件中提取特征和标签，构建训练数据集
"""

import sys
import json
import argparse
from pathlib import Path
from collections import defaultdict

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def load_symbols_file(symbols_file):
    """加载符号文件"""
    with open(symbols_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_features_file(features_file):
    """加载特征文件"""
    with open(features_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def merge_symbols_and_features(symbols_data, features_data):
    """
    合并符号和特征数据
    
    Args:
        symbols_data: 符号数据（包含函数名）
        features_data: 特征数据（包含函数特征）
        
    Returns:
        list: 合并后的训练数据
    """
    # 构建地址到函数名的映射
    address_to_name = {}
    for func in symbols_data.get("functions", []):
        address = func.get("address", "")
        name = func.get("name", "")
        # 清理地址格式（移除可能的0x前缀等）
        address_clean = address.replace("0x", "").upper()
        address_to_name[address_clean] = name
        address_to_name[address] = name  # 也保留原始格式
    
    training_data = []
    
    # 遍历特征数据中的函数
    for func_features in features_data.get("functions", []):
        func_info = func_features.get("basic_info", {})
        address = func_info.get("address", "")
        
        # 查找对应的函数名
        func_name = None
        # 尝试多种地址格式匹配
        address_variants = [
            address,
            address.replace("0x", "").upper(),
            address.replace("0x", "").lower(),
        ]
        
        for addr_var in address_variants:
            if addr_var in address_to_name:
                func_name = address_to_name[addr_var]
                break
        
        # 如果找到了函数名，且不是自动生成的名称
        if func_name and not is_auto_generated_name(func_name):
            # 构建训练样本（保留 Ghidra 特征文件中的全部字段，便于与主流程一致）
            sample = {
                "address": address,
                "decompiled_code": func_features.get("decompiled_code", ""),
                "opcodes": func_features.get("opcodes", []),
                "cfg_features": func_features.get("cfg_features", {}) or func_features.get("cfg", {}),
                "constants": func_features.get("constants", []),
                "xrefs": func_features.get("xrefs", []),
                "vector": func_features.get("vector", []),
                "label": func_name,
                # 以下为 Ghidra 完整特征，与 feature_extractor 输出一致，便于多特征融合
                "semantic_features": func_features.get("semantic_features", {}),
                "cfg_structure": func_features.get("cfg_structure", {}),
                "extended_statistics": func_features.get("extended_statistics", {}),
            }
            training_data.append(sample)
    
    return training_data


def is_auto_generated_name(name):
    """检查是否是自动生成的函数名"""
    auto_prefixes = [
        "FUN_", "sub_", "LAB_", "entry", "thunk_",
        "undefined", "UNK_", "DAT_"
    ]
    return any(name.startswith(prefix) for prefix in auto_prefixes)


def prepare_training_data(symbols_files, features_files, output_file):
    """
    准备训练数据
    
    Args:
        symbols_files: 符号文件列表
        features_files: 特征文件列表
        output_file: 输出文件路径
    """
    print("=" * 60)
    print("准备训练数据")
    print("=" * 60)
    
    all_training_data = []
    stats = defaultdict(int)
    
    # 处理每个文件对
    for symbols_file, features_file in zip(symbols_files, features_files):
        print(f"\n处理文件对:")
        print(f"  符号文件: {symbols_file}")
        print(f"  特征文件: {features_file}")
        
        # 加载数据
        symbols_data = load_symbols_file(symbols_file)
        features_data = load_features_file(features_file)
        
        # 合并数据
        training_samples = merge_symbols_and_features(symbols_data, features_data)
        
        print(f"  提取样本数: {len(training_samples)}")
        stats["total_samples"] += len(training_samples)
        stats["processed_files"] += 1
        
        all_training_data.extend(training_samples)
    
    # 统计标签分布
    label_counts = defaultdict(int)
    for sample in all_training_data:
        label = sample.get("label", "unknown")
        label_counts[label] += 1
    
    print(f"\n统计信息:")
    print(f"  总样本数: {stats['total_samples']}")
    print(f"  处理文件数: {stats['processed_files']}")
    print(f"  唯一标签数: {len(label_counts)}")
    print(f"  最常见的10个标签:")
    for label, count in sorted(label_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"    {label}: {count}")
    
    # 保存训练数据
    output_data = {
        "total_samples": len(all_training_data),
        "unique_labels": len(label_counts),
        "label_distribution": dict(label_counts),
        "functions": all_training_data
    }
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n训练数据已保存到: {output_file}")
    print(f"  总样本数: {len(all_training_data)}")
    
    return output_data


def find_matching_files(data_dir):
    """
    自动查找匹配的符号和特征文件
    
    Args:
        data_dir: 数据目录
        
    Returns:
        list: (symbols_file, features_file) 元组列表
    """
    data_path = Path(data_dir)
    
    # 如果相对路径不存在，尝试从脚本目录查找
    if not data_path.exists():
        script_dir = Path(__file__).parent.parent
        # 尝试在脚本目录下查找
        alt_path = script_dir / data_dir
        if alt_path.exists():
            data_path = alt_path
        # 尝试在项目根目录查找
        elif (script_dir.parent / data_dir).exists():
            data_path = script_dir.parent / data_dir
    
    # 转换为绝对路径
    data_path = data_path.resolve()
    
    symbols_dir = data_path / "symbols"
    features_dir = data_path / "features"
    
    if not symbols_dir.exists() or not features_dir.exists():
        print(f"调试信息:")
        print(f"  查找路径: {data_path}")
        print(f"  symbols 目录存在: {symbols_dir.exists()}")
        print(f"  features 目录存在: {features_dir.exists()}")
        return []
    
    # 获取所有符号文件
    symbols_files = list(symbols_dir.glob("*_symbols.json"))
    
    matches = []
    for sym_file in symbols_files:
        # 支持两种命名格式：
        # 1. 程序名_架构分类_symbols.json (新格式，包含架构信息)
        # 2. 程序名_symbols.json (旧格式)
        stem = sym_file.stem
        base_name = stem.replace("_symbols", "")
        
        # 查找对应的特征文件
        # 先尝试新格式：程序名_架构分类_features.json
        feat_file = features_dir / f"{base_name}_features.json"
        if feat_file.exists():
            matches.append((str(sym_file), str(feat_file)))
            continue
        
        # 如果新格式不存在，尝试从 base_name 中提取程序名
        # base_name 可能是 "程序名_架构分类" 或 "程序名"
        # 尝试查找所有可能的特征文件（包含程序名前缀的）
        program_prefix = base_name.split('_')[0]  # 获取程序名前缀
        possible_feat_files = list(features_dir.glob(f"{program_prefix}*_features.json"))
        if possible_feat_files:
            # 使用第一个匹配的
            matches.append((str(sym_file), str(possible_feat_files[0])))
    
    return matches


def main():
    parser = argparse.ArgumentParser(description="准备训练数据")
    parser.add_argument("-s", "--symbols", nargs="+", help="符号文件路径列表")
    parser.add_argument("-f", "--features", nargs="+", help="特征文件路径列表")
    parser.add_argument("-d", "--data-dir", help="数据目录（自动查找匹配文件）")
    parser.add_argument("-o", "--output", default="data/training/training_data.json", 
                       help="输出文件路径")
    
    args = parser.parse_args()
    
    # 确定输入文件
    if args.data_dir:
        # 自动查找匹配文件
        matches = find_matching_files(args.data_dir)
        if not matches:
            print(f"错误: 在 {args.data_dir} 中未找到匹配的符号和特征文件")
            return
        
        symbols_files = [m[0] for m in matches]
        features_files = [m[1] for m in matches]
        print(f"自动找到 {len(matches)} 对匹配文件")
    elif args.symbols and args.features:
        symbols_files = args.symbols
        features_files = args.features
        
        if len(symbols_files) != len(features_files):
            print("错误: 符号文件和特征文件数量必须相同")
            return
    else:
        parser.print_help()
        print("\n错误: 必须提供 --symbols 和 --features，或使用 --data-dir 自动查找")
        return
    
    # 准备训练数据
    prepare_training_data(symbols_files, features_files, args.output)


if __name__ == "__main__":
    main()

