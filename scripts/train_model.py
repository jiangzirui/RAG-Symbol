#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型训练脚本
用于训练符号恢复模型
"""

import sys
import json
import argparse
from pathlib import Path
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments, Trainer

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.model_manager import ModelManager


class FunctionDataset(Dataset):
    """函数数据集"""
    
    def __init__(self, data_file, tokenizer, max_length=512):
        """
        初始化数据集
        
        Args:
            data_file: 数据文件路径
            tokenizer: 分词器
            max_length: 最大长度
        """
        with open(data_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        self.tokenizer = tokenizer
        self.max_length = max_length
        
        # 构建标签映射
        self.label_map = self._build_label_map()
        
    def _build_label_map(self):
        """构建标签映射"""
        labels = set()
        for func in self.data["functions"]:
            if "label" in func:  # 假设数据中有标签
                labels.add(func["label"])
        
        label_list = sorted(list(labels))
        return {label: idx for idx, label in enumerate(label_list)}
    
    def __len__(self):
        return len(self.data["functions"])
    
    def __getitem__(self, idx):
        func = self.data["functions"][idx]
        
        # 获取函数代码或操作码序列
        if "decompiled_code" in func and func["decompiled_code"]:
            text = func["decompiled_code"]
        elif "opcodes" in func:
            text = " ".join(func["opcodes"][:200])
        else:
            text = ""
        
        # 编码
        encoding = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )
        
        # 获取标签
        if "label" in func:
            label = self.label_map.get(func["label"], 0)
        else:
            label = 0
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }


def train_model(data_file, output_dir, config_path="config/config.yaml"):
    """
    训练模型
    
    Args:
        data_file: 训练数据文件
        output_dir: 输出目录
        config_path: 配置文件路径
    """
    print("=" * 60)
    print("模型训练")
    print("=" * 60)
    
    # 加载配置
    manager = ModelManager(config_path)
    config = manager.config
    
    # 加载分词器
    model_name = config["model"]["base_model"]
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    # 加载数据集
    print(f"\n加载数据集: {data_file}")
    dataset = FunctionDataset(data_file, tokenizer)
    print(f"  样本数: {len(dataset)}")
    print(f"  标签数: {len(dataset.label_map)}")
    
    # 加载模型
    print(f"\n加载模型: {model_name}")
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=len(dataset.label_map)
    )
    
    # 训练参数
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=config["model"]["fine_tuning"]["epochs"],
        per_device_train_batch_size=config["model"]["fine_tuning"]["batch_size"],
        learning_rate=config["model"]["fine_tuning"]["learning_rate"],
        logging_dir=f"{output_dir}/logs",
        save_strategy="epoch",
        evaluation_strategy="no",
    )
    
    # 创建训练器
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
    )
    
    # 训练
    print("\n开始训练...")
    trainer.train()
    
    # 保存模型
    print(f"\n保存模型到: {output_dir}")
    trainer.save_model()
    tokenizer.save_pretrained(output_dir)
    
    # 保存标签映射
    label_map_file = Path(output_dir) / "label_map.json"
    with open(label_map_file, 'w', encoding='utf-8') as f:
        json.dump(dataset.label_map, f, indent=2, ensure_ascii=False)
    
    print("训练完成！")


def main():
    parser = argparse.ArgumentParser(description="模型训练脚本")
    parser.add_argument("data_file", help="训练数据文件路径")
    parser.add_argument("-o", "--output", default="models/trained_model", help="输出目录")
    parser.add_argument("-c", "--config", default="config/config.yaml", help="配置文件路径")
    
    args = parser.parse_args()
    
    train_model(args.data_file, args.output, args.config)


if __name__ == "__main__":
    main()

