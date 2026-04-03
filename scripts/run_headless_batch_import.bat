@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
REM ============================================================
REM 单次 Headless 批量：-import 整目录 -recursive，对每个二进制跑 main_pipeline.py
REM 参考: support\analyzeHeadlessREADME.md 与 docs\Ghidra无头模式批量反编译与运行脚本.md
REM ============================================================

set GHIDRA_DIR=E:\work\symbol\auto\ghidra_12.0_PUBLIC_20251205\ghidra_12.0_PUBLIC
set PROJECT_PATH=C:\Projects\SymbolRecovery
set PROJECT_NAME=SymbolRecovery
set BIN_DIR=E:\work\symbol\auto\data_bin\test
set SCRIPT_DIR=%GHIDRA_DIR%\symbol_recovery_system\src
set ANALYSIS_TIMEOUT=600
set LOG_FILE=%GHIDRA_DIR%\symbol_recovery_system\logs\headless_batch_import.log

if not "%~1"=="" set BIN_DIR=%~1

echo ============================================================
echo Headless 批量导入：对目录内所有可执行文件跑 main_pipeline.py
echo ============================================================
echo 二进制目录: %BIN_DIR%
echo 项目: %PROJECT_PATH%\%PROJECT_NAME%
echo 脚本目录: %SCRIPT_DIR%
echo 日志: %LOG_FILE%
echo ============================================================

if not exist "%BIN_DIR%" (
    echo 错误: 目录不存在 "%BIN_DIR%"
    pause
    exit /b 1
)
if not exist "%GHIDRA_DIR%\support\analyzeHeadless.bat" (
    echo 错误: 未找到 analyzeHeadless，请设置 GHIDRA_DIR
    pause
    exit /b 1
)
if not exist "%SCRIPT_DIR%\main_pipeline.py" (
    echo 错误: 未找到 main_pipeline.py 于 %SCRIPT_DIR%
    pause
    exit /b 1
)

mkdir "%GHIDRA_DIR%\symbol_recovery_system\logs" 2>nul
cd /d "%GHIDRA_DIR%"

echo 开始执行（可能较久）...
call support\analyzeHeadless.bat "%PROJECT_PATH%" "%PROJECT_NAME%" ^
  -import "%BIN_DIR%" ^
  -recursive ^
  -postScript main_pipeline.py ^
  -scriptPath "%SCRIPT_DIR%" ^
  -analysisTimeoutPerFile %ANALYSIS_TIMEOUT% ^
  -log "%LOG_FILE%"

echo.
echo 完成。输出在 %GHIDRA_DIR%\data\features 与 %GHIDRA_DIR%\data\symbols
pause
