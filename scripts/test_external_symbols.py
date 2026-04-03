## ###
# 测试外部符号提取
# @category: Symbol Recovery
# @runtime PyGhidra

"""
测试外部符号提取功能
用于调试getLibraryName问题
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 60)
print("测试外部符号提取")
print("=" * 60)
print()

try:
    program = currentProgram
    if program is None:
        print("⚠ 未打开程序")
        sys.exit(1)
    
    print(f"程序: {program.getName()}")
    print()
    
    symbol_table = program.getSymbolTable()
    external_symbols = symbol_table.getExternalSymbols()
    
    print(f"找到 {sum(1 for _ in external_symbols)} 个外部符号")
    print()
    
    # 重置迭代器
    external_symbols = symbol_table.getExternalSymbols()
    
    count = 0
    for ext_symbol in external_symbols:
        if count >= 5:
            break
        
        print(f"符号 {count + 1}:")
        print(f"  名称: {ext_symbol.getName()}")
        print(f"  类型: {ext_symbol.getSymbolType()}")
        print(f"  是否外部: {ext_symbol.isExternal()}")
        
        # 测试获取库名
        library_name = None
        try:
            parent_namespace = ext_symbol.getParentNamespace()
            if parent_namespace:
                from ghidra.program.model.listing import Library
                if isinstance(parent_namespace, Library):
                    library_name = parent_namespace.getName()
                    print(f"  库名 (Library): {library_name}")
                else:
                    ns_name = parent_namespace.getName()
                    if ns_name and ns_name != "Global":
                        library_name = ns_name
                        print(f"  库名 (命名空间): {library_name}")
                    else:
                        print(f"  命名空间: {ns_name}")
        except Exception as e:
            print(f"  获取库名失败: {e}")
        
        print()
        count += 1
    
    print("=" * 60)
    print("测试完成")
    print("=" * 60)
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
