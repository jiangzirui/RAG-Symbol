#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强符号库：为符号库添加文本描述字段
使用大模型自动生成函数描述
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm_client import get_default_llm_client


def enhance_symbol_library(symbol_library_path: str, output_path: str = None, 
                          batch_size: int = 10, skip_existing: bool = True):
    """
    增强符号库，添加文本描述字段
    
    Args:
        symbol_library_path: 符号库文件路径
        output_path: 输出文件路径（如果为None，覆盖原文件）
        batch_size: 批量处理大小
        skip_existing: 是否跳过已有描述的符号
    """
    print("=" * 60)
    print("增强符号库 - 添加文本描述")
    print("=" * 60)
    
    # 加载符号库
    print(f"\n加载符号库: {symbol_library_path}")
    with open(symbol_library_path, 'r', encoding='utf-8') as f:
        symbol_library = json.load(f)
    
    symbols = symbol_library.get("symbols", {})
    total_symbols = len(symbols)
    print(f"  总符号数: {total_symbols}")
    
    # 初始化LLM客户端
    print("\n初始化LLM客户端...")
    try:
        llm_client = get_default_llm_client()
        print("  [OK] LLM客户端已初始化")
    except Exception as e:
        print(f"  [错误] LLM客户端初始化失败: {e}")
        return
    
    # 统计
    enhanced_count = 0
    skipped_count = 0
    failed_count = 0
    
    # 处理每个符号
    print(f"\n开始处理符号（批量大小: {batch_size}）...")
    for i, (symbol_name, symbol_data) in enumerate(symbols.items(), 1):
        if i % 10 == 0:
            print(f"  已处理 {i}/{total_symbols} 个符号...")
        
        # 检查是否已有描述
        if skip_existing and symbol_data.get("description"):
            skipped_count += 1
            continue
        
        # 获取函数代码
        function_code = symbol_data.get("code", "")
        if not function_code:
            # 如果没有代码，尝试从其他字段构建
            # 可以添加更多逻辑
            failed_count += 1
            continue
        
        try:
            # 使用LLM生成描述
            description_data = llm_client.generate_function_description(
                function_code=function_code,
                function_name=symbol_name
            )
            
            # 添加到符号数据
            symbol_data["description"] = description_data.get("description", "")
            symbol_data["description_details"] = {
                "parameters": description_data.get("parameters", ""),
                "return_value": description_data.get("return_value", ""),
                "usage": description_data.get("usage", ""),
                "related_functions": description_data.get("related_functions", "")
            }
            
            enhanced_count += 1
            
        except Exception as e:
            print(f"  处理符号 {symbol_name} 时出错: {e}")
            failed_count += 1
            continue
    
    # 保存增强后的符号库
    if output_path is None:
        output_path = symbol_library_path
    
    print(f"\n保存增强后的符号库: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(symbol_library, f, indent=2, ensure_ascii=False)
    
    # 输出统计
    print("\n" + "=" * 60)
    print("处理完成")
    print("=" * 60)
    print(f"  总符号数: {total_symbols}")
    print(f"  增强数量: {enhanced_count}")
    print(f"  跳过数量: {skipped_count}")
    print(f"  失败数量: {failed_count}")
    print(f"  输出文件: {output_path}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="增强符号库，添加文本描述")
    parser.add_argument("symbol_library", help="符号库文件路径")
    parser.add_argument("-o", "--output", help="输出文件路径（默认覆盖原文件）")
    parser.add_argument("-b", "--batch-size", type=int, default=10, help="批量处理大小")
    parser.add_argument("--no-skip", action="store_true", help="不跳过已有描述的符号")
    
    args = parser.parse_args()
    
    enhance_symbol_library(
        symbol_library_path=args.symbol_library,
        output_path=args.output,
        batch_size=args.batch_size,
        skip_existing=not args.no_skip
    )


if __name__ == "__main__":
    main()
