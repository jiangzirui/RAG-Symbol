#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用推理结果到Ghidra的辅助脚本
这个脚本需要在Ghidra中运行（通过Script Manager）
"""

## ###
# 应用推理结果
# 将外部推理的结果应用到Ghidra项目
# @category: Symbol Recovery
# @runtime PyGhidra

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.symbol_recovery import SymbolRecovery


def main():
    """主函数"""
    recovery = SymbolRecovery()
    
    # 查找最新的推理结果
    results_dir = Path("data/results")
    if not results_dir.exists():
        print("结果目录不存在，请先运行推理脚本")
        return
    
    # 查找推理结果文件
    inference_files = list(results_dir.glob("*_inference.json"))
    
    if not inference_files:
        print("未找到推理结果文件")
        print("请先运行: python scripts/inference.py <features_file>")
        return
    
    # 使用最新的文件
    latest_file = max(inference_files, key=lambda p: p.stat().st_mtime)
    
    print(f"找到推理结果: {latest_file}")
    
    # 预览模式
    print("\n预览模式 - 查看将应用的符号:")
    stats = recovery.apply_results(str(latest_file), min_confidence=0.7, dry_run=True)
    
    # 询问是否应用
    apply = askYesNo("应用符号", f"是否将 {stats['applied']} 个恢复的符号应用到当前程序？")
    
    if apply:
        print("\n应用符号...")
        recovery.apply_results(str(latest_file), min_confidence=0.7, dry_run=False)
        print("\n完成！")
    else:
        print("\n已取消")


if __name__ == "__main__":
    main()

