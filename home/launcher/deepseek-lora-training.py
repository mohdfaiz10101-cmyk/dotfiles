#!/usr/bin/env nix-shell
#! nix-shell -i python3 -p python3 python3Packages.torch python3Packages.transformers python3Packages.datasets python3Packages.peft python3Packages.trl python3Packages.accelerate

"""
DeepSeek LoRA Fine-tuning Pipeline
学习 Opus/Sonnet/GLM 优点，保留 DeepSeek 代码能力

数据来源：
1. Sonnet 成功案例（从 memory/lessons-learned.md 提取）
2. Opus 架构设计案例
3. GLM 中文对话案例

技术栈：
- PEFT (Parameter-Efficient Fine-Tuning)
- LoRA: r=16, alpha=32
- QLoRA: 4-bit quantization
- DPO: Direct Preference Optimization
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict

import torch
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
    TaskType,
)
from trl import SFTTrainer, DPOTrainer
from datasets import Dataset


class DeepSeekLoRATrainer:
    """DeepSeek LoRA 训练器"""

    def __init__(
        self,
        model_name: str = "deepseek-ai/DeepSeek-V3.2",
        output_dir: str = "/mnt/ai/deepseek-lora-adapters",
    ):
        self.model_name = model_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # LoRA 配置
        self.lora_config = LoraConfig(
            r=16,  # LoRA 秩
            lora_alpha=32,  # 缩放因子
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],  # 注意力层
            lora_dropout=0.1,
            bias="none",
            task_type=TaskType.CAUSAL_LM,
        )

        # 4-bit 量化配置（节省显存）
        self.bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )

    def extract_sonnet_cases(self) -> List[Dict]:
        """从 lessons-learned.md 提取 Sonnet 成功案例"""
        lessons_file = Path.home() / ".claude/projects/-home-charlie/memory/lessons-learned.md"

        if not lessons_file.exists():
            return []

        cases = []
        with open(lessons_file, "r") as f:
            content = f.read()

        # 提取 [Sonnet] 标记的条目
        for line in content.split("\n"):
            if "[Sonnet]" in line and "已完成" in line:
                # 格式：- [日期] [Sonnet] 场景：描述
                try:
                    parts = line.split("**", 1)
                    if len(parts) > 1:
                        scenario = parts[1].split("**")[0].strip()
                        description = parts[1].split("—", 1)[1].strip() if "—" in parts[1] else ""

                        cases.append({
                            "scenario": scenario,
                            "approach": description,
                            "model": "Sonnet",
                        })
                except Exception as e:
                    continue

        return cases

    def generate_training_dataset(self) -> Dataset:
        """生成 LoRA 训练数据集"""
        sonnet_cases = self.extract_sonnet_cases()

        # 转换为 instruction-following 格式
        training_data = []

        for case in sonnet_cases:
            # System prompt：注入 Sonnet 推理模式
            system = (
                "你是配备 Sonnet 推理能力的 DeepSeek 模型。"
                "处理任务遵循流程：Pre-Check → Plan → Validate → Execute → Verify。"
                "优先读取现有配置，理解上下文后再修改。"
            )

            # User input：场景描述
            user = f"在 NixOS 中{case['scenario']}"

            # Assistant output：Sonnet 方法
            assistant = case['approach']

            training_data.append({
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                    {"role": "assistant", "content": assistant},
                ]
            })

        return Dataset.from_list(training_data)

    def generate_dpo_dataset(self) -> Dataset:
        """生成 DPO 偏好数据集（好答案 vs 坏答案）"""
        dpo_data = [
            {
                "prompt": "在 NixOS 中安装 bat 工具",
                "chosen": (
                    "1. 读取 /etc/nixos/modules/packages.nix\n"
                    "2. 在系统工具部分添加 bat\n"
                    "3. nix flake check 验证\n"
                    "4. nixos-rebuild switch\n"
                    "5. which bat 确认安装"
                ),
                "rejected": (
                    "直接运行 nix-env -i bat"
                ),
            },
            # 更多对比样本...
        ]

        return Dataset.from_list(dpo_data)

    def train_lora(self, dataset: Dataset):
        """LoRA 微调"""
        print(f"[1/3] 加载模型：{self.model_name}")

        # 加载分词器
        tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        tokenizer.pad_token = tokenizer.eos_token

        # 加载量化模型
        model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            quantization_config=self.bnb_config,
            device_map="auto",
            torch_dtype=torch.bfloat16,
        )

        # 准备 LoRA 训练
        model = prepare_model_for_kbit_training(model)
        model = get_peft_model(model, self.lora_config)

        print(f"可训练参数：{model.print_trainable_parameters()}")

        # 训练参数
        training_args = TrainingArguments(
            output_dir=str(self.output_dir / "checkpoints"),
            num_train_epochs=3,
            per_device_train_batch_size=4,
            gradient_accumulation_steps=4,
            learning_rate=2e-4,
            fp16=False,
            bf16=True,
            logging_steps=10,
            save_steps=100,
            save_total_limit=3,
            report_to="none",
        )

        # SFT Trainer
        trainer = SFTTrainer(
            model=model,
            args=training_args,
            train_dataset=dataset,
            tokenizer=tokenizer,
            max_seq_length=2048,
        )

        print("[2/3] 开始训练...")
        trainer.train()

        print(f"[3/3] 保存 LoRA adapter 到 {self.output_dir}")
        model.save_pretrained(self.output_dir / "sonnet-lora-adapter")
        tokenizer.save_pretrained(self.output_dir / "sonnet-lora-adapter")

        # 保存元数据
        metadata = {
            "model_name": self.model_name,
            "lora_config": {
                "r": self.lora_config.r,
                "alpha": self.lora_config.lora_alpha,
                "target_modules": self.lora_config.target_modules,
            },
            "training_samples": len(dataset),
            "trained_at": datetime.now().isoformat(),
            "capabilities": [
                "Sonnet-style system reasoning",
                "NixOS configuration understanding",
                "Pre-Check → Validate → Execute flow",
            ],
        }

        with open(self.output_dir / "sonnet-lora-adapter/metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        print("✓ 训练完成")


def main():
    """主函数"""
    trainer = DeepSeekLoRATrainer()

    print("=== DeepSeek LoRA Fine-tuning ===")
    print("目标：学习 Sonnet 推理能力，保留 DeepSeek 代码强项\n")

    # 生成训练数据
    print("[数据准备] 从 lessons-learned.md 提取 Sonnet 案例...")
    dataset = trainer.generate_training_dataset()
    print(f"✓ 提取到 {len(dataset)} 个训练样本\n")

    if len(dataset) == 0:
        print("❌ 没有足够的训练数据，需要至少 50 个 Sonnet 成功案例")
        return

    # 训练 LoRA
    trainer.train_lora(dataset)

    print("\n=== 下一步 ===")
    print("1. 部署 LoRA adapter 到 LiteLLM:")
    print("   在 config.yaml 中添加：")
    print("   model: deepseek-ai/DeepSeek-V3.2")
    print("   adapter: /mnt/ai/deepseek-lora-adapters/sonnet-lora-adapter")
    print("\n2. 测试效果:")
    print("   ds '在 NixOS 中安装 ripgrep'")


if __name__ == "__main__":
    main()
