@echo off
chcp 65001 >nul
cd /d "%~dp0.."

echo ========== 第一步：用脱符号特征重新建库 ==========
python scripts/build_symbol_library.py -s data/self_eval/symbols_from_ground_truth.json -f data/self_eval/test_features.json -o data/symbols/symbol_library_self.json
if errorlevel 1 ( echo 建库失败 & pause & exit /b 1 )

echo.
echo ========== 第二步：推理 ==========
python scripts/inference.py data/self_eval/test_features.json -o results/self_eval/predictions.json -l data/symbols/symbol_library_self.json -t 0.5
if errorlevel 1 ( echo 推理失败 & pause & exit /b 1 )

echo.
echo ========== 第三步：评估 ==========
python scripts/evaluate.py results/self_eval/predictions.json -g data/self_eval/ground_truth.json -o results/self_eval/eval.json
echo.
echo 结果见: results\self_eval\eval.json
pause
