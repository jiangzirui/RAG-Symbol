@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."

set SYMLM_DIR=%~1
if "%SYMLM_DIR%"=="" set SYMLM_DIR=E:\work\symbol\auto\ghidra_12.0_PUBLIC_20251205\ghidra_12.0_PUBLIC\SymLM-main\dataset_generation\dataset_sample

set MAX_FUNC=%~2
if "%MAX_FUNC%"=="" set MAX_FUNC=500

set INFERENCE_LIMIT=%~3
if "%INFERENCE_LIMIT%"=="" set INFERENCE_LIMIT=

set OUT_TEST=data\test_symlm_%MAX_FUNC%
set OUT_EXP=results\exp_symlm_%MAX_FUNC%
if exist data\symbols\symbol_library_symlm.json (
  set LIB=data\symbols\symbol_library_symlm.json
  echo 使用 SymLM 符号库: %LIB%
) else (
  set LIB=data\symbols\symbol_library_arm32.json
  echo 未找到 symbol_library_symlm.json，使用 %LIB% ^(跨架构匹配率可能为 0^)
)

echo [1/4] 生成 SymLM 测试集 ^(%MAX_FUNC% 条^) ...
python scripts/prepare_test_set_symlm.py --symlm-dir "%SYMLM_DIR%" -o %OUT_TEST% --split test --max-functions %MAX_FUNC%
if errorlevel 1 exit /b 1

echo [2/4] 推理 ^(若第3参数有值则仅推理前 N 条，快速出结果^) ...
if "%INFERENCE_LIMIT%"=="" (
  python scripts/inference.py %OUT_TEST%\test_features.json -o %OUT_EXP%\predictions_multi.json -l %LIB% -t 0.5
) else (
  python scripts/inference.py %OUT_TEST%\test_features.json -o %OUT_EXP%\predictions_multi.json -l %LIB% -t 0.5 --limit %INFERENCE_LIMIT%
)
if errorlevel 1 exit /b 1

echo [3/4] 评估 ...
python scripts/evaluate.py %OUT_EXP%\predictions_multi.json -g %OUT_TEST%\ground_truth.json -o %OUT_EXP%\eval_multi.json --no-print-samples
if errorlevel 1 exit /b 1

echo [4/4] 完成. 结果见 %OUT_EXP%\eval_multi.json
type %OUT_EXP%\eval_multi.json | findstr /C:"accuracy" /C:"f1"
exit /b 0
