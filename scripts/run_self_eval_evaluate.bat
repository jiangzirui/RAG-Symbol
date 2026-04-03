@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo 正在评估 self_eval 预测结果...
python scripts/evaluate.py results/self_eval/predictions.json -g data/self_eval/ground_truth.json -o results/self_eval/eval.json
echo.
echo 结果见: results\self_eval\eval.json
pause
