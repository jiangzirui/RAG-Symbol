@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
REM ============================================================
REM 将 SymLM data_bin 下所有二进制用本系统 Ghidra 流程跑一遍
REM 仅做特征+符号提取（-skip-inference -skip-apply），不做推理
REM ============================================================

set DATA_BIN=E:\work\symbol\auto\ghidra_12.0_PUBLIC_20251205\ghidra_12.0_PUBLIC\SymLM-main\data_bin
set GHIDRA_DIR=E:\work\symbol\auto\ghidra_12.0_PUBLIC_20251205\ghidra_12.0_PUBLIC
set SCRIPT_DIR=%~dp0
REM 脚本在 symbol_recovery_system\scripts，上一级为 symbol_recovery_system
set SYS_ROOT=%~dp0..
REM headless 在 symbol_recovery_system 下；运行时应从 Ghidra 根目录调用
set LIST_FILE=%SYS_ROOT%\data\symlm_processed_list.txt

if not "%~1"=="" set DATA_BIN=%~1

echo ============================================================
echo SymLM 二进制批量跑 Ghidra 特征/符号提取
echo ============================================================
echo 二进制目录: %DATA_BIN%
echo 输出列表: %LIST_FILE%
echo 仅提取（跳过推理与应用）: -skip-inference -skip-apply
echo ============================================================

if not exist "%DATA_BIN%" (
    echo 错误: 目录不存在 "%DATA_BIN%"
    pause
    exit /b 1
)

if not exist "%GHIDRA_DIR%\support\analyzeHeadless.bat" (
    echo 错误: 未找到 Ghidra analyzeHeadless，请设置 GHIDRA_DIR
    pause
    exit /b 1
)

if not exist "%SYS_ROOT%\headless_完整流程_调试版.bat" (
    echo 错误: 未找到 headless_完整流程_调试版.bat
    echo 期望路径: %SYS_ROOT%\headless_完整流程_调试版.bat
    pause
    exit /b 1
)

mkdir "%SYS_ROOT%\data" 2>nul
echo # SymLM binaries processed at %date% %time% > "%LIST_FILE%"

REM 从 Ghidra 根目录运行 headless，以便脚本路径 symbol_recovery_system\src\main_pipeline.py 正确
cd /d "%GHIDRA_DIR%"
set HEADLESS_BAT=%GHIDRA_DIR%\symbol_recovery_system\headless_完整流程_调试版.bat
if not exist "%HEADLESS_BAT%" set HEADLESS_BAT=%SYS_ROOT%\headless_完整流程_调试版.bat

set N=0
for /r "%DATA_BIN%" %%f in (*.exe *.dll *.so *.bin *.elf *.out) do (
    set /a N+=1
    echo.
    echo [!N!] 处理: %%f
    call "%HEADLESS_BAT%" "%%f" -skip-inference -skip-apply
    echo %%f >> "%LIST_FILE%"
)

echo.
echo ============================================================
echo 批量处理结束，共处理 !N! 个文件
echo 已写入列表: %LIST_FILE%
echo.
echo 下一步: 合并输出并建库（在 symbol_recovery_system 目录下）
echo   cd symbol_recovery_system
echo   python scripts/merge_symlm_ghidra_outputs.py
echo 若 features/symbols 在 Ghidra 根下 data:
echo   python scripts/merge_symlm_ghidra_outputs.py --features-dir "..\data\features" --symbols-dir "..\data\symbols"
echo ============================================================
pause
