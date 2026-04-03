#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
符号库构建脚本
从有符号文件中构建符号库，用于相似度匹配
"""

import sys
import json
import argparse
from pathlib import Path
import numpy as np

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.model_manager import ModelManager


def load_features_file(features_file):
    """加载特征文件"""
    with open(features_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_symbols_file(symbols_file):
    """加载符号文件"""
    with open(symbols_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_symbol_library(symbols_files, features_files, output_file, config_path="config/config.yaml",
                        cfg_only=False, statistical_only=False, config_path_override=None):
    """
    构建符号库
    
    Args:
        symbols_files: 符号文件列表
        features_files: 特征文件列表
        output_file: 输出文件路径
        config_path: 配置文件路径
        cfg_only: 仅使用 CFG 特征建库（用于单一特征消融）
        statistical_only: 仅使用统计特征建库（用于单一特征消融）
    """
    cfg = config_path_override or config_path
    print("=" * 60)
    print("构建符号库")
    print("=" * 60)
    
    # 加载模型管理器（用于编码函数）
    print("\n加载模型...")
    manager = ModelManager(cfg)
    model, tokenizer = manager.load_base_model()
    
    # 检查是否使用CLAP
    use_clap = manager.use_clap
    if use_clap:
        print("  使用CLAP模型（将存储代码用于匹配）")
    else:
        print("  使用CodeBERT模型（将存储嵌入向量）")
    if cfg_only:
        print("  [仅CFG] 建库仅使用 CFG 特征")
    if statistical_only:
        print("  [仅统计] 建库仅使用统计特征")
    
    # 初始化多特征融合器（如果可用）
    fusion = None
    try:
        from src.multi_feature_fusion import MultiFeatureFusion
        fusion = MultiFeatureFusion(cfg)
        fusion.initialize()
        print("  多特征融合器已初始化（结构+语义+统计）")
    except Exception as e:
        print(f"  多特征融合器不可用: {e}")
        print("  将使用单一特征编码")
    
    symbol_library = {}
    stats = {
        "total_functions": 0,
        "encoded_functions": 0,
        "failed": 0
    }
    
    # 收集架构信息（用于自动分类）
    architecture_info = None
    
    # 处理每个文件对
    for symbols_file, features_file in zip(symbols_files, features_files):
        print(f"\n处理:")
        print(f"  符号文件: {symbols_file}")
        print(f"  特征文件: {features_file}")
        
        # 加载数据
        symbols_data = load_symbols_file(symbols_file)
        features_data = load_features_file(features_file)
        
        # 提取架构信息（从第一个文件）
        if architecture_info is None and "architecture" in features_data:
            architecture_info = features_data["architecture"]
            print(f"\n检测到架构信息:")
            print(f"  架构: {architecture_info.get('arch_name', 'unknown')}")
            print(f"  操作系统: {architecture_info.get('os', 'unknown')}")
            print(f"  LanguageID: {architecture_info.get('language_id', 'unknown')}")
        
        # 构建地址到函数名的映射
        address_to_name = {}
        for func in symbols_data.get("functions", []):
            address = func.get("address", "")
            name = func.get("name", "")
            if name and not is_auto_generated_name(name):
                address_to_name[address] = name
                # 也添加清理后的地址格式
                address_clean = address.replace("0x", "").upper()
                address_to_name[address_clean] = name
        
        # 处理每个函数
        for func_features in features_data.get("functions", []):
            stats["total_functions"] += 1
            
            func_info = func_features.get("basic_info", {})
            address = func_info.get("address", "")
            
            # 查找函数名
            func_name = None
            address_variants = [
                address,
                address.replace("0x", "").upper(),
                address.replace("0x", "").lower(),
            ]
            
            for addr_var in address_variants:
                if addr_var in address_to_name:
                    func_name = address_to_name[addr_var]
                    break
            
            if not func_name or is_auto_generated_name(func_name):
                continue
            
            # 编码函数特征（支持多特征融合）
            try:
                # 尝试使用多特征融合（如果已初始化）
                use_multi_feature = False
                fused_embedding = None
                
                if fusion:
                    # 检查是否有新特征
                    has_semantic = "semantic_features" in func_features and func_features["semantic_features"]
                    has_cfg_structure = "cfg_structure" in func_features and func_features["cfg_structure"]
                    has_extended_stats = "extended_statistics" in func_features and func_features["extended_statistics"]
                    
                    if has_semantic or has_cfg_structure or has_extended_stats:
                        try:
                            # 使用多特征融合（支持仅CFG/仅统计）
                            use_code = not (cfg_only or statistical_only)
                            use_semantic = not (cfg_only or statistical_only)
                            use_cfg = True if cfg_only else (not statistical_only)
                            use_statistical = True if statistical_only else (not cfg_only)
                            encoded_features = fusion.encode_features(
                                func_features,
                                use_code=use_code,
                                use_semantic=use_semantic,
                                use_cfg=use_cfg,
                                use_statistical=use_statistical,
                            )
                            fused_embedding = fusion.fuse_features(encoded_features, use_attention=False)
                            use_multi_feature = True
                            if stats["encoded_functions"] % 100 == 0:  # 每100个函数打印一次
                                print(f"  [多特征融合] 已编码 {stats['encoded_functions']} 个函数...")
                        except Exception as e:
                            # 如果多特征融合失败，回退到单一特征
                            if stats["encoded_functions"] % 100 == 0:
                                print(f"  多特征融合失败，使用单一特征: {e}")
                
                if use_multi_feature and fused_embedding is not None:
                    # 使用融合后的特征
                    embedding_np = fused_embedding.flatten() if len(fused_embedding.shape) > 1 else fused_embedding
                    
                    if func_name in symbol_library:
                        existing_embedding = np.array(symbol_library[func_name]["embedding"])
                        new_embedding = (existing_embedding + embedding_np) / 2
                        symbol_library[func_name]["count"] += 1
                        symbol_library[func_name]["embedding"] = new_embedding.tolist()
                        # 保存多特征信息
                        if "multi_feature" not in symbol_library[func_name]:
                            symbol_library[func_name]["multi_feature"] = True
                    else:
                        symbol_library[func_name] = {
                            "embedding": embedding_np.tolist(),
                            "count": 1,
                            "examples": [address],
                            "multi_feature": True  # 标记使用了多特征融合
                        }
                    stats["encoded_functions"] += 1
                elif use_clap:
                    # CLAP模式：使用asm编码器编码代码，存储嵌入向量（代码-代码匹配）
                    decompiled_code = func_features.get("decompiled_code")
                    if decompiled_code:
                        try:
                            # 使用asm编码器编码代码
                            code_embedding = manager.encode_function(decompiled_code)
                            embedding_np = code_embedding.cpu().numpy().flatten() if hasattr(code_embedding, 'cpu') else np.array(code_embedding).flatten()
                            
                            if func_name in symbol_library:
                                existing_embedding = np.array(symbol_library[func_name]["embedding"])
                                new_embedding = (existing_embedding + embedding_np) / 2
                                symbol_library[func_name]["count"] += 1
                                symbol_library[func_name]["embedding"] = new_embedding.tolist()
                            else:
                                symbol_library[func_name] = {
                                    "embedding": embedding_np.tolist(),
                                    "count": 1,
                                    "examples": [address]
                                }
                            stats["encoded_functions"] += 1
                        except Exception as e:
                            print(f"  编码函数 {func_name} 时出错: {e}")
                            stats["failed"] += 1
                    else:
                        stats["failed"] += 1
                else:
                    # CodeBERT模式：存储嵌入向量
                    embedding = manager.encode_features(func_features)
                    
                    if embedding is not None:
                        # 转换为numpy数组并保存
                        embedding_np = embedding.cpu().numpy() if hasattr(embedding, 'cpu') else np.array(embedding)
                        
                        # 如果函数名已存在，合并嵌入（取平均）
                        if func_name in symbol_library:
                            existing_embedding = np.array(symbol_library[func_name]["embedding"])
                            new_embedding = (existing_embedding + embedding_np.flatten()) / 2
                            symbol_library[func_name]["count"] += 1
                            symbol_library[func_name]["embedding"] = new_embedding.tolist()
                        else:
                            symbol_library[func_name] = {
                                "embedding": embedding_np.flatten().tolist(),
                                "count": 1,
                                "examples": [address]  # 保存示例地址
                            }
                        
                        stats["encoded_functions"] += 1
                    else:
                        stats["failed"] += 1
            except Exception as e:
                print(f"  编码函数 {func_name} 时出错: {e}")
                import traceback
                traceback.print_exc()
                stats["failed"] += 1
    
    # 如果检测到架构信息，自动调整输出文件名
    if architecture_info:
        # 使用与 ArchitectureDetector.get_classification_key() 相同的逻辑
        arch_name = architecture_info.get('arch_name', 'unknown')
        os_name = architecture_info.get('os', 'unknown')
        
        if os_name != 'unknown':
            classification_key = f"{arch_name}_{os_name}"
        else:
            classification_key = arch_name
        
        # 如果输出文件是默认路径，根据架构分类
        output_path = Path(output_file)
        if output_path.name == "symbol_library.json":
            # 自动生成分类文件名
            new_filename = f"symbol_library_{classification_key}.json"
            output_file = str(output_path.parent / new_filename)
            print(f"\n根据架构信息，符号库将保存为: {new_filename}")
            print(f"  架构: {arch_name}")
            print(f"  操作系统: {os_name}")
            print(f"  分类键: {classification_key}")
    
    # 若任意符号使用多特征融合，则顶层标记，推理时会走多特征匹配
    any_multi = any(
        (s.get("multi_feature") for s in symbol_library.values())
    )
    output_data = {
        "total_symbols": len(symbol_library),
        "statistics": stats,
        "architecture": architecture_info if architecture_info else None,
        "symbols": symbol_library,
        "multi_feature": any_multi,
    }
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n符号库已保存到: {output_file}")
    print(f"  总符号数: {len(symbol_library)}")
    print(f"  编码函数数: {stats['encoded_functions']}")
    print(f"  失败数: {stats['failed']}")
    if architecture_info:
        print(f"  架构: {architecture_info.get('arch_name', 'unknown')}")
        print(f"  操作系统: {architecture_info.get('os', 'unknown')}")
    
    return output_data


def is_auto_generated_name(name):
    """检查是否是自动生成的函数名"""
    auto_prefixes = [
        "FUN_", "sub_", "LAB_", "entry", "thunk_",
        "undefined", "UNK_", "DAT_"
    ]
    return any(name.startswith(prefix) for prefix in auto_prefixes)


def find_matching_files(data_dir):
    """自动查找匹配的符号和特征文件"""
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
    
    symbols_files = list(symbols_dir.glob("*_symbols.json"))
    matches = []
    
    for sym_file in symbols_files:
        # 支持两种命名格式：
        # 1. 程序名_架构分类_symbols.json (新格式)
        # 2. 程序名_symbols.json (旧格式)
        stem = sym_file.stem
        
        # 尝试匹配新格式：程序名_架构分类_symbols
        if "_symbols" in stem:
            # 移除 _symbols 后缀
            base_name = stem.replace("_symbols", "")
            
            # 查找对应的特征文件
            # 先尝试新格式：程序名_架构分类_features.json
            feat_file = features_dir / f"{base_name}_features.json"
            if feat_file.exists():
                matches.append((str(sym_file), str(feat_file)))
                continue
            
            # 如果新格式不存在，尝试从 base_name 中提取程序名
            # base_name 可能是 "程序名_架构分类" 或 "程序名"
            # 尝试移除架构分类部分（假设架构分类在最后）
            # 但这样比较复杂，所以先尝试直接匹配
            
            # 如果都不存在，跳过
            if not feat_file.exists():
                # 尝试查找所有可能的特征文件（包含程序名前缀的）
                possible_feat_files = list(features_dir.glob(f"{base_name.split('_')[0]}*_features.json"))
                if possible_feat_files:
                    # 使用第一个匹配的
                    matches.append((str(sym_file), str(possible_feat_files[0])))
    
    return matches


def main():
    parser = argparse.ArgumentParser(description="构建符号库")
    parser.add_argument("-s", "--symbols", nargs="+", help="符号文件路径列表")
    parser.add_argument("-f", "--features", nargs="+", help="特征文件路径列表")
    parser.add_argument("-d", "--data-dir", help="数据目录（自动查找匹配文件）")
    parser.add_argument("-o", "--output", default="data/symbols/symbol_library.json",
                       help="输出文件路径")
    parser.add_argument("-c", "--config", default="config/config.yaml", help="配置文件路径")
    parser.add_argument("--cfg-only", action="store_true", help="仅用 CFG 特征建库（单一特征消融）")
    parser.add_argument("--statistical-only", action="store_true", help="仅用统计特征建库（单一特征消融）")
    parser.add_argument("--config-override", help="覆盖配置文件路径（如 CodeBERT 用 config/config_codebert.yaml）")
    
    args = parser.parse_args()
    
    # 确定输入文件
    if args.data_dir:
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
    
    # 构建符号库
    build_symbol_library(symbols_files, features_files, args.output, args.config,
                        cfg_only=args.cfg_only, statistical_only=args.statistical_only,
                        config_path_override=args.config_override)


if __name__ == "__main__":
    main()

