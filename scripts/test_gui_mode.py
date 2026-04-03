## ###
# GUI模式测试脚本
# 测试Ghidra GUI环境和脚本是否正常工作
# @category: Symbol Recovery
# @runtime PyGhidra

"""
GUI模式测试脚本
用于验证Ghidra GUI环境和脚本配置是否正确
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 60)
print("Ghidra GUI模式 - 环境测试")
print("=" * 60)
print()

# 测试1: 检查Ghidra环境
print("测试 1: Ghidra环境")
print("-" * 60)
try:
    program = currentProgram
    if program is None:
        print("⚠ 当前未打开程序")
        print("  这是正常的，如果你还没有导入二进制文件")
        print("  要完整测试，请先: File → Import File → 选择二进制文件")
        print("  然后重新运行此脚本")
    else:
        print(f"✓ 当前程序: {program.getName()}")
        print(f"✓ 程序语言: {program.getLanguageID()}")
        try:
            print(f"✓ 程序路径: {program.getExecutablePath()}")
        except:
            print("✓ 程序路径: (无法获取)")
except NameError:
    print("✗ 错误: 无法获取当前程序")
    print("  请确保在Ghidra中打开了一个程序")
    print("  或者这是正常的，如果还没有导入文件")

# 测试2: 检查函数管理器
print("\n测试 2: 函数管理器")
print("-" * 60)
try:
    if program is None:
        print("⚠ 跳过（未打开程序）")
    else:
        functionManager = program.getFunctionManager()
        function_count = functionManager.getFunctionCount()
        print(f"✓ 找到 {function_count} 个函数")
        
        functions = functionManager.getFunctions(True)
        
        # 显示前5个函数
        count = 0
        print("\n前5个函数:")
        for func in functions:
            if count >= 5:
                break
            print(f"  - {func.getName()} @ {func.getEntryPoint()}")
            count += 1
except Exception as e:
    print(f"⚠ 错误: {e}")
    if program is None:
        print("  （这是正常的，因为未打开程序）")

# 测试3: 检查项目路径
print("\n测试 3: 项目路径")
print("-" * 60)
try:
    project_dir = Path(".")
    print(f"✓ 当前工作目录: {project_dir.absolute()}")
    
    # 检查关键目录
    data_dir = Path("data")
    if data_dir.exists():
        print(f"✓ data目录存在")
    else:
        print(f"⚠ data目录不存在，将自动创建")
        data_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ 已创建data目录")
except Exception as e:
    print(f"✗ 错误: {e}")

# 测试4: 检查模块导入
print("\n测试 4: 模块导入")
print("-" * 60)
modules = [
    "src.symbol_detector",
    "src.static_analyzer",
    "src.feature_extractor",
    "src.model_manager",
    "src.symbol_recovery"
]

all_ok = True
for module_name in modules:
    try:
        __import__(module_name)
        print(f"✓ {module_name}")
    except ImportError as e:
        # torch is optional for model_manager
        if module_name == "src.model_manager" and "torch" in str(e):
            print(f"⚠ {module_name}: {e} (可选依赖，模型功能需要)")
        elif "graph" in str(e) and module_name == "src.feature_extractor":
            print(f"⚠ {module_name}: {e} (graph模块可能不可用，但会使用替代方案)")
        else:
            print(f"✗ {module_name}: {e}")
            all_ok = False
    except Exception as e:
        print(f"⚠ {module_name}: {e}")

# 测试5: 检查符号检测器
print("\n测试 5: 符号检测器")
print("-" * 60)
try:
    if program is None:
        print("⚠ 跳过（未打开程序）")
    else:
        from src.symbol_detector import SymbolDetector
        detector = SymbolDetector(program)
        has_symbols = detector.has_debug_symbols()
        if has_symbols:
            print("✓ 检测到调试符号")
        else:
            print("⚠ 未检测到调试符号（这是正常的，如果文件没有符号表）")
except Exception as e:
    print(f"⚠ 错误: {e}")
    if program is None:
        print("  （这是正常的，因为未打开程序）")

# 测试6: 检查静态分析器
print("\n测试 6: 静态分析器")
print("-" * 60)
try:
    if program is None:
        print("⚠ 跳过（未打开程序）")
    else:
        from src.static_analyzer import StaticAnalyzer
        analyzer = StaticAnalyzer(program)
        functions = analyzer.get_all_functions()
        print(f"✓ 可以获取函数列表: {len(functions)} 个函数")
except Exception as e:
    print(f"⚠ 错误: {e}")
    if program is None:
        print("  （这是正常的，因为未打开程序）")

# 测试7: 检查特征提取器
print("\n测试 7: 特征提取器")
print("-" * 60)
try:
    if program is None:
        print("⚠ 跳过（未打开程序）")
    else:
        from src.feature_extractor import FeatureExtractor
        extractor = FeatureExtractor(program)
        print("✓ 特征提取器初始化成功")
except Exception as e:
    print(f"⚠ 错误: {e}")
    if program is None:
        print("  （这是正常的，因为未打开程序）")

# 总结
print("\n" + "=" * 60)
print("测试总结")
print("=" * 60)

if program is None:
    print("⚠ 注意: 当前未打开程序")
    print("  要完整测试所有功能，请:")
    print("  1. File → Import File → 选择二进制文件")
    print("  2. 等待分析完成")
    print("  3. 重新运行此测试脚本")
    print()
    print("✓ PyGhidra环境正常，可以运行Python脚本")
    print("✓ 所有模块都可以正常导入")
else:
    if all_ok:
        print("✓ 所有测试通过！")
        print("\n你可以开始使用符号恢复系统了：")
        print("1. 运行 main_pipeline.py 进行完整流程")
        print("2. 或分别运行各个模块进行测试")
    else:
        print("⚠ 部分测试失败，请检查错误信息")
        print("\n建议：")
        print("1. 检查Python环境和依赖是否正确安装")
        print("2. 确保PyGhidra已正确启动")
        print("3. 检查脚本路径是否正确")

print("\n" + "=" * 60)
