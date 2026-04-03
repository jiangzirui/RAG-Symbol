#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
符号推理脚本
在外部 Python 环境中运行，使用训练好的模型或符号库进行符号推理
"""

import sys
import json
import argparse
import time
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.model_manager import ModelManager
import numpy as np


def load_features(features_file):
    """加载特征数据"""
    with open(features_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_symbol_library(library_file):
    """加载符号库"""
    with open(library_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def _embedding_to_np(embedding, dim_target=None):
    """统一转为 numpy 一维，可选对齐到 dim_target。"""
    if embedding is None:
        return None
    if hasattr(embedding, 'cpu'):
        out = embedding.cpu().numpy().flatten().astype(np.float64)
    else:
        out = np.array(embedding).flatten().astype(np.float64)
    if dim_target is not None and len(out) != dim_target:
        if len(out) > dim_target:
            out = out[:dim_target]
        else:
            out = np.pad(out, (0, dim_target - len(out)), mode="constant", constant_values=0)
    return out


def _build_library_matrix(symbol_library):
    """把符号库转成 (N, dim) 矩阵和名字列表，行已归一化（余弦用）。返回 (lib_matrix_norm, lib_names, dim) 或 (None, [], 0)。"""
    symbols = symbol_library.get("symbols", {})
    if not symbols:
        return None, [], 0
    names = []
    rows = []
    dim = len(next(iter(symbols.values()))["embedding"])
    for name, data in symbols.items():
        emb = np.array(data.get("embedding", []), dtype=np.float64)
        if len(emb) != dim:
            continue
        names.append(name)
        rows.append(emb)
    if not rows:
        return None, [], dim
    mat = np.vstack(rows)
    norms = np.linalg.norm(mat, axis=1, keepdims=True) + 1e-8
    mat_norm = (mat / norms).astype(np.float64)
    return mat_norm, names, dim


def match_with_symbol_library(embedding, symbol_library, threshold=0.7, lib_matrix_norm=None, lib_names=None):
    """
    使用符号库进行相似度匹配。若提供 lib_matrix_norm/lib_names 则用向量化计算（快很多）。
    """
    if embedding is None:
        return None, 0.0
    symbols = symbol_library.get("symbols", {})
    if not symbols:
        return None, 0.0
    dim_lib = len(next(iter(symbols.values()))["embedding"])
    embedding_np = _embedding_to_np(embedding, dim_lib)
    if embedding_np is None:
        return None, 0.0

    # 向量化路径：一次矩阵乘法（始终返回最佳匹配名与分数，由调用方按 threshold 过滤）
    if lib_matrix_norm is not None and lib_names is not None and len(lib_names) > 0:
        norm = np.linalg.norm(embedding_np) + 1e-8
        q = (embedding_np / norm).reshape(1, -1).astype(np.float64)
        if q.shape[1] == lib_matrix_norm.shape[1]:
            scores = np.dot(q, lib_matrix_norm.T).flatten()
            best_idx = int(np.argmax(scores))
            best_score = float(scores[best_idx])
            best_match = lib_names[best_idx]
            return best_match, best_score
    # 回退：逐符号循环（始终返回最佳匹配名与分数）
    best_match = None
    best_score = 0.0
    for symbol_name, symbol_data in symbols.items():
        symbol_embedding = np.array(symbol_data["embedding"])
        if len(embedding_np) != len(symbol_embedding):
            continue
        similarity = cosine_similarity(embedding_np, symbol_embedding)
        if similarity > best_score:
            best_score = similarity
            best_match = symbol_name
    return (best_match, float(best_score)) if best_match is not None else (None, float(best_score))


def cosine_similarity(vec1, vec2):
    """计算余弦相似度"""
    vec1_norm = vec1 / (np.linalg.norm(vec1) + 1e-8)
    vec2_norm = vec2 / (np.linalg.norm(vec2) + 1e-8)
    return np.dot(vec1_norm, vec2_norm)


def inference(features_file, output_file=None, model_path=None, symbol_library_file=None,
              use_library=True, similarity_threshold=0.7, use_rag=False, rag_top_k=10, rag_use_llm=True,
              generate_if_no_match=False,
              use_code=True, use_semantic=True, use_cfg=True, use_statistical=True, use_attention=False,
              start_from=1, limit=None, config_path=None):
    """
    执行推理
    
    Args:
        features_file: 特征文件路径
        output_file: 输出文件路径
        model_path: 训练好的模型路径（可选）
        symbol_library_file: 符号库文件路径（可选）
        use_library: 是否使用符号库匹配
        similarity_threshold: 相似度阈值
        use_code: 多特征融合时是否使用代码特征（仅CFG/仅统计时为 False）
        use_semantic: 多特征融合时是否使用语义特征（消融用）
        use_cfg: 多特征融合时是否使用 CFG 特征（消融用）
        use_statistical: 多特征融合时是否使用统计特征（消融用）
        use_attention: 多特征融合时是否使用注意力（否则加权融合）
        config_path: 配置文件路径（可选，用于 CodeBERT 等切换模型）
    """
    print("=" * 60)
    print("符号推理")
    print("=" * 60)
    
    # 加载特征
    print(f"\n加载特征数据: {features_file}")
    features_data = load_features(features_file)
    print(f"  程序: {features_data['program_name']}")
    print(f"  函数数: {features_data['total_functions']}")
    
    # 加载模型
    print("\n加载模型...")
    cfg_path = config_path or "config/config.yaml"
    if model_path:
        # 使用指定的模型路径更新配置
        import yaml
        with open(cfg_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        config["model"]["model_path"] = model_path
        # 临时保存配置
        temp_config = Path("config/temp_config.yaml")
        with open(temp_config, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)
        cfg_path = str(temp_config)
    
    manager = ModelManager(cfg_path)
    model, tokenizer = manager.load_base_model()
    
    # 检查是否使用CLAP
    use_clap = manager.use_clap
    if use_clap:
        print("  使用CLAP模型进行符号匹配")
    else:
        print("  使用CodeBERT模型进行符号匹配")
    
    # 检查是否支持多特征融合
    use_multi_feature = False
    fusion = None
    try:
        from src.multi_feature_fusion import MultiFeatureFusion
        fusion = MultiFeatureFusion(cfg_path)
        fusion.initialize()
        use_multi_feature = True
        print("  支持多特征融合（结构+语义+统计）")
    except Exception as e:
        print(f"  多特征融合不可用: {e}")
        print("  将使用单一特征匹配")
    
    # 检测目标文件的架构信息
    target_arch_info = features_data.get("architecture")
    if target_arch_info:
        print(f"\n检测到目标文件架构:")
        print(f"  架构: {target_arch_info.get('arch_name', 'unknown')}")
        print(f"  操作系统: {target_arch_info.get('os', 'unknown')}")
        print(f"  LanguageID: {target_arch_info.get('language_id', 'unknown')}")
    
    # 加载符号库（如果提供）
    symbol_library = None
    if use_library and symbol_library_file:
        print(f"\n加载指定符号库: {symbol_library_file}")
        symbol_library = load_symbol_library(symbol_library_file)
        print(f"  符号数: {symbol_library.get('total_symbols', 0)}")
    elif use_library:
        # 尝试根据架构自动查找符号库
        library_found = False
        if target_arch_info:
            arch_name = target_arch_info.get('arch_name', 'unknown')
            os_name = target_arch_info.get('os', 'unknown')
            
            # 尝试多个可能的符号库路径
            possible_libraries = []
            if os_name != 'unknown':
                possible_libraries.append(f"data/symbols/symbol_library_{arch_name}_{os_name}.json")
            possible_libraries.append(f"data/symbols/symbol_library_{arch_name}.json")
            possible_libraries.append("data/symbols/symbol_library.json")
            
            for lib_path in possible_libraries:
                lib_file = Path(lib_path)
                if lib_file.exists():
                    print(f"\n根据架构自动选择符号库: {lib_path}")
                    symbol_library = load_symbol_library(str(lib_file))
                    print(f"  符号数: {symbol_library.get('total_symbols', 0)}")
                    library_found = True
                    break
        
        # 如果自动查找失败，尝试默认符号库
        if not library_found:
            default_library = Path("data/symbols/symbol_library.json")
            if default_library.exists():
                print(f"\n使用默认符号库: {default_library}")
                symbol_library = load_symbol_library(str(default_library))
                print(f"  符号数: {symbol_library.get('total_symbols', 0)}")
                library_found = True
        
        if not library_found:
            print("\n未找到匹配的符号库，将使用基础模型推理")
            print("  提示: 可以手动指定符号库: -l <符号库路径>")
            use_library = False
    
    # 初始化RAG预测器（使用RAG 或 仅需「无匹配时生成」时）
    rag_predictor = None
    if use_rag and use_library and symbol_library:
        try:
            from src.rag_symbol_predictor import RAGSymbolPredictor
            print("\n初始化RAG预测器...")
            library_file = symbol_library_file or "data/symbols/symbol_library.json"
            rag_predictor = RAGSymbolPredictor(library_file)
            print("  [OK] RAG预测器已初始化（将使用DeepSeek API）")
        except Exception as e:
            print(f"  [警告] RAG预测器初始化失败: {e}")
            print("  将使用传统向量匹配方法")
            use_rag = False
    elif generate_if_no_match and use_library and symbol_library:
        try:
            from src.rag_symbol_predictor import RAGSymbolPredictor
            print("\n初始化RAG预测器（仅用于无匹配时生成函数名）...")
            library_file = symbol_library_file or "data/symbols/symbol_library.json"
            rag_predictor = RAGSymbolPredictor(library_file)
            print("  [OK] RAG预测器已初始化")
        except Exception as e:
            print(f"  [警告] RAG预测器初始化失败，无法使用「无匹配时生成」: {e}")
            generate_if_no_match = False
    
    # 预建符号库矩阵（向量化匹配，避免 7724 次循环卡顿）
    t_load_lib_start = time.perf_counter()
    lib_matrix_norm = None
    lib_names = []
    if use_library and symbol_library:
        lib_matrix_norm, lib_names, _ = _build_library_matrix(symbol_library)
        if lib_matrix_norm is not None:
            print(f"  已预计算符号库矩阵: {len(lib_names)} 个符号，向量化匹配", flush=True)
    t_load_lib_end = time.perf_counter()
    time_load_library_seconds = t_load_lib_end - t_load_lib_start

    # 推理（各阶段计时）
    print("\n开始推理...")
    time_encoding_seconds = 0.0
    time_retrieval_seconds = 0.0
    time_matching_seconds = 0.0
    time_llm_seconds = 0.0
    inference_method = "rag" if use_rag else ("symbol_library" if use_library else "base_model")
    results = {
        "program_name": features_data["program_name"],
        "inference_method": inference_method,
        "recovered_symbols": []
    }

    start_from = max(1, int(start_from))
    limit = int(limit) if limit is not None else None

    matched_count = 0
    total_funcs = len(features_data["functions"])
    t_inference_start = time.perf_counter()
    for i, func_features in enumerate(features_data["functions"], 1):
        if limit is not None and (i - start_from + 1) > limit:
            # 只跑前 limit 个函数（用于抽样测 RAG LLM 等耗时），剩余补空
            for k in range(i, total_funcs + 1):
                f = features_data["functions"][k - 1]
                results["recovered_symbols"].append({
                    "original_name": f.get("basic_info", {}).get("name", "unknown"),
                    "address": f.get("basic_info", {}).get("address", ""),
                    "predicted_name": "",
                    "confidence": 0.0,
                })
            break
        if i < start_from:
            results["recovered_symbols"].append({
                "original_name": func_features.get("basic_info", {}).get("name", "unknown"),
                "address": func_features.get("basic_info", {}).get("address", ""),
                "predicted_name": "",
                "confidence": 0.0,
            })
            continue
        processed_so_far = i - start_from + 1
        if i % 50 == 0 or i == total_funcs:
            wall_elapsed = time.perf_counter() - t_inference_start
            avg_per_func = wall_elapsed / processed_so_far if processed_so_far else 0
            remaining = total_funcs - i
            est_remaining_sec = remaining * avg_per_func if processed_so_far else 0
            est_remaining_h = est_remaining_sec / 3600
            llm_part = f"，LLM 累计 {time_llm_seconds:.0f}s（均 {time_llm_seconds/processed_so_far:.1f}s/函数）" if (processed_so_far and time_llm_seconds > 0) else ""
            print(f"  已处理 {i}/{total_funcs} 个函数 | 总耗时 {wall_elapsed/60:.1f} min，均 {avg_per_func:.1f}s/函数{llm_part}，预计剩余约 {est_remaining_h:.1f} h", flush=True)
            # 每 50 个函数写一次当前运行时间，中途停掉也能保留已跑完的耗时数据
            try:
                _resolved = Path(output_file) if output_file else (Path(features_file).parent.parent / "results" / f"{features_data['program_name']}_inference.json")
                _resolved = Path(_resolved)
                _dir = _resolved.parent
                _stem = _resolved.stem
                _timing_partial = _dir / f"{_stem}_timing_partial.json"
                _t = {
                    "processed_count": i,
                    "total_functions": total_funcs,
                    "wall_elapsed_seconds": round(wall_elapsed, 2),
                    "load_library_seconds": round(time_load_library_seconds, 2),
                    "feature_encoding_seconds": round(time_encoding_seconds, 2),
                    "retrieval_seconds": round(time_retrieval_seconds, 2),
                    "matching_seconds": round(time_matching_seconds, 2),
                    "llm_seconds": round(time_llm_seconds, 2),
                    "total_seconds": round(time_load_library_seconds + time_encoding_seconds + time_retrieval_seconds + time_matching_seconds + time_llm_seconds, 2),
                }
                _dir.mkdir(parents=True, exist_ok=True)
                with open(_timing_partial, "w", encoding="utf-8") as _f:
                    json.dump(_t, _f, indent=2, ensure_ascii=False)
            except Exception:
                pass

        predicted_name = None
        confidence = 0.0

        # 如果使用RAG，优先使用RAG预测（单次调用内：候选中选择 或 相似度低于阈值时由模型生成）
        if use_rag and rag_predictor:
            try:
                rag_timing = {}
                t0_rag = time.perf_counter()
                predicted_name, confidence, reason = rag_predictor.predict(
                    func_features,
                    top_k=rag_top_k,
                    use_llm=rag_use_llm,
                    similarity_threshold=similarity_threshold,
                    generate_when_below_threshold=generate_if_no_match,
                    generate_when_no_candidates=generate_if_no_match,
                    timing_out=rag_timing,
                )
                elapsed_rag = time.perf_counter() - t0_rag
                llm_sec = rag_timing.get("llm_seconds", 0.0)
                time_llm_seconds += llm_sec
                time_retrieval_seconds += elapsed_rag - llm_sec
                if predicted_name and predicted_name != "UNKNOWN":
                    results["recovered_symbols"].append({
                        "original_name": func_features["basic_info"].get("name", "unknown"),
                        "address": func_features["basic_info"].get("address", "unknown"),
                        "predicted_name": predicted_name,
                        "confidence": confidence,
                        "method": "rag",
                        "reason": reason,
                    })
                    matched_count += 1
                    continue
            except Exception as e:
                if i % 100 == 0:
                    print(f"  RAG预测失败，回退到传统方法: {e}")
        
        # 尝试使用多特征融合（如果可用且符号库也支持）
        use_fusion_for_this_func = False
        library_uses_multi_feature = symbol_library.get("multi_feature", False) if symbol_library else False
        
        # 多特征融合匹配：完整多特征库 或 仅CFG/仅统计（需对应库）
        use_single_feature_lib = use_code is False and (use_cfg or use_statistical)
        if use_multi_feature and fusion and (library_uses_multi_feature or use_single_feature_lib):
            # 检查是否有可编码特征（代码/反编译/opcodes 或 结构/语义/统计）
            has_code = bool((func_features.get("decompiled_code") or "").strip()) or bool(func_features.get("opcodes"))
            has_semantic = "semantic_features" in func_features and func_features["semantic_features"]
            has_cfg_structure = "cfg_structure" in func_features and func_features["cfg_structure"]
            has_extended_stats = "extended_statistics" in func_features and func_features["extended_statistics"]
            
            if (has_code or has_semantic or has_cfg_structure or has_extended_stats) and use_library and symbol_library:
                try:
                    # 使用多特征融合编码（支持消融：仅代码/仅CFG/仅统计等）
                    t0_enc = time.perf_counter()
                    encoded_features = fusion.encode_features(
                        func_features,
                        use_code=use_code,
                        use_semantic=use_semantic,
                        use_cfg=use_cfg,
                        use_statistical=use_statistical,
                    )
                    fused_embedding = fusion.fuse_features(encoded_features, use_attention=use_attention)
                    emb_flat = fused_embedding.flatten() if hasattr(fused_embedding, 'flatten') else np.array(fused_embedding).flatten()
                    emb_flat = emb_flat.astype(np.float64)
                    time_encoding_seconds += time.perf_counter() - t0_enc
                    # 向量化匹配（避免 7724 次循环）
                    t0_ret = time.perf_counter()
                    if lib_matrix_norm is not None and len(lib_names) > 0 and emb_flat.shape[0] == lib_matrix_norm.shape[1]:
                        norm = np.linalg.norm(emb_flat) + 1e-8
                        q = (emb_flat / norm).reshape(1, -1)
                        scores = np.dot(q, lib_matrix_norm.T).flatten()
                        best_idx = int(np.argmax(scores))
                        best_score = float(scores[best_idx])
                        best_match = lib_names[best_idx]  # 始终保留最佳匹配名，供评估时按 confidence 阈值过滤
                    else:
                        best_match = None
                        best_score = 0.0
                        for symbol_name, symbol_data in symbol_library.get("symbols", {}).items():
                            symbol_embedding = np.array(symbol_data.get("embedding", []))
                            if len(symbol_embedding) == len(emb_flat):
                                sim = cosine_similarity(emb_flat, symbol_embedding)
                                if sim > best_score:
                                    best_score = sim
                                    best_match = symbol_name
                    time_retrieval_seconds += time.perf_counter() - t0_ret
                    t0_mat = time.perf_counter()
                    if best_match is not None:
                        predicted_name = best_match
                        confidence = float(best_score)
                        if best_score >= similarity_threshold:
                            matched_count += 1
                        use_fusion_for_this_func = True
                    time_matching_seconds += time.perf_counter() - t0_mat
                except Exception as e:
                    if i % 100 == 0:  # 每100个函数打印一次错误
                        print(f"  多特征融合匹配失败，回退到单一特征: {e}")
        
        # 如果多特征融合未使用，使用原有方法
        if not use_fusion_for_this_func:
            decompiled_code = (func_features.get("decompiled_code") or "").strip()
            lib_has_code = any("code" in d for d in (symbol_library.get("symbols", {}) or {}).values()) if symbol_library else False
            # CLAP 模式：仅当有反编译代码且符号库含 code 字符串时使用
            if use_clap and decompiled_code and use_library and symbol_library and lib_has_code:
                clap_symbol_library = {}
                for symbol_name, symbol_data in symbol_library.get("symbols", {}).items():
                    if "code" in symbol_data:
                        clap_symbol_library[symbol_name] = symbol_data["code"]
                if clap_symbol_library:
                    t0_clap = time.perf_counter()
                    matches = manager.predict_function_name(
                        function_code=decompiled_code,
                        symbol_library=clap_symbol_library,
                        top_k=1,
                        threshold=similarity_threshold
                    )
                    time_retrieval_seconds += time.perf_counter() - t0_clap
                    if matches:
                        if isinstance(matches, list):
                            predicted_name, confidence = matches[0]
                        else:
                            predicted_name = matches
                            confidence = 0.8
                        if predicted_name:
                            matched_count += 1
            # 嵌入匹配：无反编译代码或符号库仅有 embedding 时用（encode_features 会使用 opcodes）
            if not predicted_name:
                t0_emb = time.perf_counter()
                embedding = manager.encode_features(func_features)
                time_encoding_seconds += time.perf_counter() - t0_emb
                if embedding is not None:
                    if use_library and symbol_library:
                        t0_m = time.perf_counter()
                        predicted_name, confidence = match_with_symbol_library(
                            embedding, symbol_library, similarity_threshold,
                            lib_matrix_norm=lib_matrix_norm, lib_names=lib_names
                        )
                        time_retrieval_seconds += time.perf_counter() - t0_m
                        if predicted_name and confidence >= similarity_threshold:
                            matched_count += 1
                    else:
                        predicted_name = manager.predict_function_name(embedding)
                        confidence = 0.5

        # 无任何匹配时：若开启「无匹配时生成」且已有 RAG 预测器，则用 LLM 生成名称
        if (not predicted_name or predicted_name == "UNKNOWN") and generate_if_no_match and rag_predictor:
            try:
                decompiled_code = (func_features.get("decompiled_code") or "").strip()
                context = (func_features.get("semantic_features") or {}).get("context", {})
                gen_timing = {}
                gen_name, gen_conf, gen_reason = rag_predictor.generate_function_name(
                    decompiled_code, context=context, timing_out=gen_timing
                )
                time_llm_seconds += gen_timing.get("llm_seconds", 0.0)
                if gen_name and gen_name != "UNKNOWN":
                    predicted_name, confidence = gen_name, gen_conf
            except Exception as e:
                if i % 100 == 0:
                    print(f"  无匹配时生成失败: {e}")

        # 统一写入预测结果（每个函数一条记录，便于与 ground_truth 按地址对齐评估）
        results["recovered_symbols"].append({
            "original_name": func_features["basic_info"].get("name", "unknown"),
            "address": func_features["basic_info"].get("address", "unknown"),
            "predicted_name": predicted_name or "",
            "confidence": float(confidence),
        })
    
    # 各阶段耗时汇总（若用了 --limit 则按全量外推，便于表 5b 与其他组一致）
    if limit is not None and limit > 0:
        scale = total_funcs / limit
        time_encoding_seconds *= scale
        time_retrieval_seconds *= scale
        time_matching_seconds *= scale
        time_llm_seconds *= scale
    total_seconds = time_load_library_seconds + time_encoding_seconds + time_retrieval_seconds + time_matching_seconds + time_llm_seconds
    timing = {
        "load_library_seconds": round(time_load_library_seconds, 4),
        "feature_encoding_seconds": round(time_encoding_seconds, 4),
        "retrieval_seconds": round(time_retrieval_seconds, 4),
        "matching_seconds": round(time_matching_seconds, 4),
        "llm_seconds": round(time_llm_seconds, 4),
        "total_seconds": round(total_seconds, 4),
    }
    results["timing"] = timing

    # 保存结果
    if output_file is None:
        output_file = Path(features_file).parent.parent / "results" / f"{features_data['program_name']}_inference.json"
    
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # 单独写出各阶段耗时（便于汇总脚本读取）
    timing_path = output_file.with_name(output_file.stem + "_timing.json")
    with open(timing_path, 'w', encoding='utf-8') as f:
        json.dump({"output_file": str(output_file), "timing": timing}, f, indent=2, ensure_ascii=False)
    
    print(f"\n推理结果已保存到: {output_file}")
    print(f"  恢复符号数: {len(results['recovered_symbols'])}")
    if use_library:
        print(f"  符号库匹配数: {matched_count}")
    print(f"  各阶段耗时(秒): 加载符号库={timing['load_library_seconds']:.2f}, 特征编码={timing['feature_encoding_seconds']:.2f}, 检索={timing['retrieval_seconds']:.2f}, 匹配={timing['matching_seconds']:.2f}, RAG大模型分析={timing['llm_seconds']:.2f}, 合计={timing['total_seconds']:.2f}")
    print(f"  已写入: {timing_path}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="符号推理脚本")
    parser.add_argument("features_file", help="特征文件路径")
    parser.add_argument("-o", "--output", help="输出文件路径")
    parser.add_argument("-m", "--model", help="训练好的模型路径")
    parser.add_argument("-l", "--library", help="符号库文件路径")
    parser.add_argument("--no-library", action="store_true", help="不使用符号库匹配")
    parser.add_argument("-t", "--threshold", type=float, default=0.7, help="相似度阈值（默认0.7）")
    parser.add_argument("--rag", action="store_true", help="使用RAG方法（需要符号库有文本描述）")
    parser.add_argument("--rag-no-llm", action="store_true", help="RAG 仅检索+相似度取最佳，不调用 LLM（与「向量匹配」区别：RAG 先 top-k 再选）")
    parser.add_argument("--generate-if-no-match", action="store_true", help="当无库匹配或置信度不足时，用 LLM 根据反编译代码生成函数名（需同时开启 --rag）")
    parser.add_argument("--rag-top-k", type=int, default=10, help="RAG检索的候选数量（默认10）")
    # 消融实验
    parser.add_argument("--no-semantic", action="store_true", help="多特征融合时关闭语义特征")
    parser.add_argument("--no-cfg", action="store_true", help="多特征融合时关闭CFG特征")
    parser.add_argument("--no-statistical", action="store_true", help="多特征融合时关闭统计特征")
    parser.add_argument("--cfg-only", action="store_true", help="仅用 CFG 特征匹配（需用 --cfg-only 建的库，-l 指定）")
    parser.add_argument("--statistical-only", action="store_true", help="仅用统计特征匹配（需用 --statistical-only 建的库，-l 指定）")
    parser.add_argument("--use-attention", action="store_true", help="多特征融合时使用注意力（默认加权融合）")
    parser.add_argument("--config", default=None, help="配置文件路径（如 config/config_codebert.yaml 用于 CodeBERT）")
    parser.add_argument("--start-from", type=int, default=1, help="从第 N 个函数开始推理（跳过前 N-1 个，用于卡住后续跑）")
    parser.add_argument("--limit", type=int, default=None, metavar="N", help="仅处理前 N 个函数（用于抽样测 RAG LLM 等耗时，timing 会外推到全量）")
    
    args = parser.parse_args()
    
    use_code = not (args.cfg_only or args.statistical_only)
    use_cfg = True if args.cfg_only else (False if args.statistical_only else (not args.no_cfg))
    use_semantic = False if (args.cfg_only or args.statistical_only) else (not args.no_semantic)
    use_statistical = True if args.statistical_only else (False if args.cfg_only else (not args.no_statistical))
    
    inference(
        args.features_file,
        args.output,
        model_path=args.model,
        symbol_library_file=args.library,
        use_library=not args.no_library,
        similarity_threshold=args.threshold,
        use_rag=args.rag,
        rag_top_k=args.rag_top_k,
        rag_use_llm=not args.rag_no_llm,
        generate_if_no_match=args.generate_if_no_match,
        use_code=use_code,
        use_semantic=use_semantic,
        use_cfg=use_cfg,
        use_statistical=use_statistical,
        use_attention=args.use_attention,
        start_from=args.start_from,
        limit=args.limit,
        config_path=args.config,
    )


if __name__ == "__main__":
    main()

