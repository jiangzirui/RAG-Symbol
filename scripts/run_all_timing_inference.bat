@echo off
chcp 65001 >nul
set ROOT=%~dp0..
cd /d "%ROOT%"
set FEAT=data/self_eval/test_features.json
set OUT_DIR=results/self_eval
set LIB=data/symbols/symbol_library_self.json
set LIB_CFG=data/symbols/symbol_library_self_cfg.json

echo ========== 1/5 Full ==========
python scripts/inference.py "%FEAT%" -o "%OUT_DIR%/predictions_ablation_full.json" -l "%LIB%" -t 0.5
if errorlevel 1 exit /b 1

echo ========== 2/5 RAG (no LLM) ==========
python scripts/inference.py "%FEAT%" -o "%OUT_DIR%/predictions_rag_no_llm.json" -l "%LIB%" -t 0.5 --rag --rag-no-llm
if errorlevel 1 exit /b 1

echo ========== 3/5 RAG (LLM) ==========
python scripts/inference.py "%FEAT%" -o "%OUT_DIR%/predictions_rag_llm.json" -l "%LIB%" -t 0.5 --rag
if errorlevel 1 exit /b 1

echo ========== 4/5 code_only ==========
python scripts/inference.py "%FEAT%" -o "%OUT_DIR%/predictions_ablation_code_only.json" -l "%LIB%" -t 0.5 --no-semantic --no-cfg --no-statistical
if errorlevel 1 exit /b 1

echo ========== 5/5 single_cfg ==========
python scripts/inference.py "%FEAT%" -o "%OUT_DIR%/predictions_single_cfg.json" -l "%LIB_CFG%" -t 0.5 --cfg-only
if errorlevel 1 exit /b 1

echo ========== 汇总表 5b ==========
python scripts/aggregate_timing_to_table5b.py --dir "%OUT_DIR%"
echo.
echo 使用 --update-doc 写回文档: python scripts/aggregate_timing_to_table5b.py --dir %OUT_DIR% --update-doc
