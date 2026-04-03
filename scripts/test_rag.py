#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试RAG功能
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag_symbol_predictor import RAGSymbolPredictor
from src.llm_client import get_default_llm_client
import json


def test_llm_client():
    """测试LLM客户端"""
    print("=" * 60)
    print("测试LLM客户端")
    print("=" * 60)
    
    try:
        llm_client = get_default_llm_client()
        print("\n[OK] LLM客户端初始化成功")
        
        # 测试生成函数描述
        print("\n测试生成函数描述...")
        test_code = """
        void *memcpy(void *dest, const void *src, size_t n) {
            char *d = (char *)dest;
            const char *s = (const char *)src;
            for (size_t i = 0; i < n; i++) {
                d[i] = s[i];
            }
            return dest;
        }
        """
        
        description = llm_client.generate_function_description(test_code, "memcpy")
        print(f"  描述: {description.get('description', 'N/A')}")
        print(f"  参数: {description.get('parameters', 'N/A')}")
        print(f"  返回值: {description.get('return_value', 'N/A')}")
        print("\n[OK] LLM客户端测试成功")
        return True
        
    except Exception as e:
        print(f"\n[错误] LLM客户端测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rag_predictor():
    """测试RAG预测器"""
    print("\n" + "=" * 60)
    print("测试RAG预测器")
    print("=" * 60)
    
    symbol_library_path = "data/symbols/symbol_library_arm32.json"
    if not Path(symbol_library_path).exists():
        print(f"\n[错误] 符号库不存在: {symbol_library_path}")
        return False
    
    try:
        predictor = RAGSymbolPredictor(symbol_library_path)
        print("\n[OK] RAG预测器初始化成功")
        
        # 测试检索候选
        print("\n测试检索候选函数...")
        test_features = {
            "decompiled_code": """
            void *memcpy(void *dest, const void *src, size_t n) {
                char *d = (char *)dest;
                const char *s = (const char *)src;
                for (size_t i = 0; i < n; i++) {
                    d[i] = s[i];
                }
                return dest;
            }
            """,
            "semantic_features": {
                "context": {
                    "callers": [],
                    "callees": []
                },
                "functional_semantics": {
                    "functional_tags": ["memcpy_like"]
                }
            }
        }
        
        candidates = predictor.retrieve_candidates(test_features, top_k=5)
        print(f"  检索到 {len(candidates)} 个候选函数:")
        for i, (name, score, data) in enumerate(candidates[:5], 1):
            print(f"    {i}. {name} (相似度: {score:.3f})")
        
        # 测试预测（不使用LLM）
        print("\n测试预测（不使用LLM）...")
        name, confidence, reason = predictor.predict(test_features, use_llm=False)
        print(f"  预测函数名: {name}")
        print(f"  置信度: {confidence:.3f}")
        print(f"  理由: {reason}")
        
        # 测试预测（使用LLM）
        print("\n测试预测（使用LLM）...")
        try:
            name, confidence, reason = predictor.predict(test_features, use_llm=True, top_k=5)
            print(f"  预测函数名: {name}")
            print(f"  置信度: {confidence:.3f}")
            print(f"  理由: {reason}")
        except Exception as e:
            print(f"  [警告] LLM预测失败: {e}")
            print("  （这是正常的，如果API未配置或网络问题）")
        
        print("\n[OK] RAG预测器测试成功")
        return True
        
    except Exception as e:
        print(f"\n[错误] RAG预测器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("RAG功能测试")
    print("=" * 60)
    
    # 测试LLM客户端
    llm_ok = test_llm_client()
    
    # 测试RAG预测器
    rag_ok = test_rag_predictor()
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"  LLM客户端: {'✓' if llm_ok else '✗'}")
    print(f"  RAG预测器: {'✓' if rag_ok else '✗'}")
    
    if llm_ok and rag_ok:
        print("\n[OK] 所有测试通过！")
    else:
        print("\n[警告] 部分测试失败，请检查配置")


if __name__ == "__main__":
    main()
