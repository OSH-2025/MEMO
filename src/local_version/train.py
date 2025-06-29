from datasets import Dataset
import pandas as pd
import torch
import re
import numpy as np
from transformers import AutoTokenizer, AutoModelForCausalLM, DataCollatorForSeq2Seq, TrainingArguments, Trainer, GenerationConfig
from peft import LoraConfig, TaskType, get_peft_model
import os
import glob
import json
import argparse
import logging
from datetime import datetime

class Qwen3FineTuner:
    def __init__(self, config):
        self.config = config
        self.tokenizer = None
        self.model = None
        self.setup_logging()

    def setup_logging(self):
        logging.getLogger("transformers.modeling_utils").setLevel(logging.ERROR)
        logging.getLogger("transformers.modeling_outputs").setLevel(logging.ERROR)
        logging.getLogger("transformers.models.qwen3.modeling_qwen3").setLevel(logging.ERROR)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f"training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def load_model_and_tokenizer(self):
        self.logger.info(f"正在加载模型: {self.config['model_path']}")
        self.model = AutoModelForCausalLM.from_pretrained(
            self.config['model_path'],
            trust_remote_code=True,
            torch_dtype=getattr(torch, self.config.get('torch_dtype', 'float32'))
        )
        self.model.enable_input_require_grads()
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.config['model_path'],
            trust_remote_code=True
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.logger.info("模型和分词器加载完成")

    def process_func(self, example):
        MAX_LENGTH = self.config.get('max_length', 384)
        system_prompt = self.config.get('system_prompt', "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\nCutting Knowledge Date: December 2023\nToday Date: 26 Jul 2024\n\n你是一个智能助手，请根据用户最近的活动序列，预测下一个最有可能的用户活动。请确保输出格式与输入格式一致，应为\"时间 - 操作\"的形式。\n<|eot_id|>")
        user_prompt = f"<|start_header_id|>user<|end_header_id|>\n\n{example.get('instruction', '')}\n{example.get('input', '')}<|eot_id|>"
        assistant_prompt = "<|start_header_id|>assistant<|end_header_id|>\n\n"
        prompt = system_prompt + user_prompt + assistant_prompt
        prompt_tokens = self.tokenizer(prompt, add_special_tokens=False)
        response_tokens = self.tokenizer(f"{example['output']}<|eot_id|>", add_special_tokens=False)
        input_ids = prompt_tokens["input_ids"] + response_tokens["input_ids"]
        attention_mask = prompt_tokens["attention_mask"] + response_tokens["attention_mask"]
        labels = [-100] * len(prompt_tokens["input_ids"]) + response_tokens["input_ids"]
        if len(input_ids) > MAX_LENGTH:
            input_ids = input_ids[:MAX_LENGTH]
            attention_mask = attention_mask[:MAX_LENGTH]
            labels = labels[:MAX_LENGTH]
        return {"input_ids": input_ids, "attention_mask": attention_mask, "labels": labels}

    def load_datasets(self):
        data_dir = self.config['data_dir']
        if self.config.get('data_format') == 'single_file':
            file_path = self.config['data_file']
            df = pd.read_json(file_path) if file_path.endswith('.json') else pd.read_csv(file_path)
            train_df = df.sample(frac=self.config.get('train_ratio', 0.8), random_state=42)
            val_df = df.drop(train_df.index).reset_index(drop=True)
        else:
            json_files = glob.glob(os.path.join(data_dir, '*.json'))
            self.logger.info(f"检测到 {len(json_files)} 个json文件")
            train_dfs, val_dfs = [], []
            for json_file in json_files:
                df = pd.read_json(json_file)
                train_df = df.sample(frac=self.config.get('train_ratio', 0.8), random_state=42)
                val_df = df.drop(train_df.index).reset_index(drop=True)
                train_dfs.append(train_df)
                val_dfs.append(val_df)
                self.logger.info(f"{os.path.basename(json_file)}: 训练样本 {len(train_df)}, 验证样本 {len(val_df)}")
            train_df = pd.concat(train_dfs, ignore_index=True)
            val_df = pd.concat(val_dfs, ignore_index=True)
        self.logger.info(f"总训练集大小: {len(train_df)}, 总验证集大小: {len(val_df)}")
        train_ds = Dataset.from_pandas(train_df)
        val_ds = Dataset.from_pandas(val_df)
        train_tokenized = train_ds.map(self.process_func, remove_columns=train_ds.column_names)
        val_tokenized = val_ds.map(self.process_func, remove_columns=val_ds.column_names)
        return train_tokenized, val_tokenized, val_df

    def setup_lora(self):
        lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            target_modules=self.config.get('lora_target_modules', ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]),
            inference_mode=False,
            r=self.config.get('lora_r', 8),
            lora_alpha=self.config.get('lora_alpha', 32),
            lora_dropout=self.config.get('lora_dropout', 0.1)
        )
        self.model = get_peft_model(self.model, lora_config)
        self.model.print_trainable_parameters()
        self.logger.info("LoRA配置完成")

    def setup_trainer(self, train_dataset, val_dataset):
        training_args = TrainingArguments(
            output_dir=self.config['output_dir'],
            per_device_train_batch_size=self.config.get('per_device_train_batch_size', 4),
            per_device_eval_batch_size=self.config.get('per_device_eval_batch_size', 4),
            gradient_accumulation_steps=self.config.get('gradient_accumulation_steps', 4),
            logging_steps=self.config.get('logging_steps', 10),
            num_train_epochs=self.config.get('num_train_epochs', 3),
            save_steps=self.config.get('save_steps', 100),
            learning_rate=self.config.get('learning_rate', 1e-4),
            save_on_each_node=True,
            gradient_checkpointing=self.config.get('gradient_checkpointing', True),
            eval_strategy=self.config.get('eval_strategy', "steps"),
            eval_steps=self.config.get('eval_steps', 100),
            save_strategy="steps",
            load_best_model_at_end=self.config.get('load_best_model_at_end', True),
            metric_for_best_model="eval_loss",
            greater_is_better=False,
            warmup_steps=self.config.get('warmup_steps', 100),
            weight_decay=self.config.get('weight_decay', 0.01),
        )
        return Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            data_collator=DataCollatorForSeq2Seq(tokenizer=self.tokenizer, padding=True),
        )

    def generate_prediction(self, instruction, input_text):
        def clean_output(text):
            # Step 0: 清除所有特殊 token 和 HTML-like 标签
            text = re.sub(r'<\|.*?\|>', '', text)          # 清除 <|xxx|>
            text = re.sub(r'</?.*?>', '', text)            # 清除 <xxx> 和 </xxx>
            text = text.replace('</s>', '').strip()

            # Step 1: 清除 > 及其之后的内容（包括第一个 > 本身）
            if '>' in text:
                text = text.split('>')[0].strip()

            # Step 2: 拆行、清除空行
            lines = [line.strip() for line in text.split('\n') if line.strip()]

            # Step 3: 提取第一条合法活动
            for line in lines:
                match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - ([^:]+): (.+)$', line)
                if match:
                    t, op, target = match.groups()
                    if op in ['启动应用', '关闭应用', '访问网站', '访问文件', '切换到窗口', '使用应用']:
                        return f"{t} - {op}: {target}"

            return ""  # 如果没有合法预测


        system_prompt = self.config.get('system_prompt', "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\nYou are a helpful assistant.\n<|eot_id|>")
        user_prompt = f"<|start_header_id|>user<|end_header_id|>\n\n{instruction}\n{input_text}<|eot_id|>"
        assistant_prompt = "<|start_header_id|>assistant<|end_header_id|>\n\n"
        prompt = system_prompt + user_prompt + assistant_prompt
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        generation_config = GenerationConfig(
            max_new_tokens=self.config.get('max_new_tokens', 100),
            do_sample=self.config.get('do_sample', True),
            temperature=self.config.get('temperature', 0.7),
            top_p=self.config.get('top_p', 0.9),
            pad_token_id=self.tokenizer.pad_token_id,
            eos_token_id=self.tokenizer.eos_token_id
        )
        with torch.no_grad():
            outputs = self.model.generate(**inputs, generation_config=generation_config)
        raw = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=False).strip()
        return clean_output(raw)

    def evaluate_model(self, val_df):
        self.logger.info("开始在验证集上进行预测评估...")
        predictions = []
        references = val_df['output'].tolist()
        exact_matches, partial_matches, empty_predictions = 0, 0, 0

        def split_event(event):
            match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - ([^:]+): (.+)$', event.strip())
            return match.groups() if match else ("", "", "")

        for i, row in val_df.iterrows():
            prediction = self.generate_prediction(row.get('instruction', ''), row.get('input', ''))
            reference = row['output'].strip()
            predictions.append(prediction)
            pt, po, po2 = split_event(prediction)
            rt, ro, ro2 = split_event(reference)

            # 完全匹配 = 时间，操作类型和操作目标都匹配
            if pt == rt and po == ro and po2 == ro2 and pt and po and po2:
                exact_matches += 1

            # 部分匹配 = 操作类型和操作目标都匹配（时间不要求）
            if po == ro and po2 == ro2 and po and po2:
                partial_matches += 1

            if prediction == "":
                empty_predictions += 1
            if (i + 1) % 10 == 0:
                self.logger.info(f"已完成 {i + 1}/{len(val_df)} 条预测")

        total = len(references)
        acc = exact_matches / total if total else 0
        partial_acc = partial_matches / total if total else 0
        empty_ratio = empty_predictions / total if total else 0

        self.logger.info(f"完全匹配准确率: {acc:.4f} ({exact_matches}/{total})")
        self.logger.info(f"部分匹配准确率: {partial_acc:.4f} ({partial_matches}/{total})")
        self.logger.info(f"不合规预测占比: {empty_ratio:.4f} ({empty_predictions}/{total})")

        results_df = pd.DataFrame({
            'instruction': val_df['instruction'],
            'input': val_df['input'],
            'reference': references,
            'prediction': predictions,
            'exact_match': [
                (split_event(pred)[1] == split_event(ref)[1] and
                split_event(pred)[2] == split_event(ref)[2] and
                split_event(pred)[1] != "" and split_event(pred)[2] != "")
                for pred, ref in zip(predictions, references)
            ],

            'partial_match': [any(
                a == b and a != "" for a, b in zip(split_event(pred), split_event(ref))
            ) for pred, ref in zip(predictions, references)],
            'prediction_illegal': [pred == "" for pred in predictions]
        })
        output_file = os.path.join(self.config['output_dir'], "prediction_results.csv")
        results_df.to_csv(output_file, index=False)
        self.logger.info(f"清洗后的预测结果已保存到 {output_file}")
    def train(self):
        """主训练流程"""
        self.logger.info("开始训练流程")
        
        # 1. 加载模型和分词器
        self.load_model_and_tokenizer()
        
        # 2. 加载数据集
        train_dataset, val_dataset, val_df = self.load_datasets()
        
        # 3. 设置LoRA
        if self.config.get('use_lora', True):
            self.setup_lora()
        
        # 4. 设置训练器
        trainer = self.setup_trainer(train_dataset, val_dataset)
        
        # 5. 开始训练
        self.logger.info("开始训练...")
        trainer.train()
        
        # 6. 保存模型
        trainer.save_model()
        self.logger.info(f"模型已保存到 {self.config['output_dir']}")
        
        # 7. 评估模型
        self.evaluate_model(val_df)
        
        self.logger.info("训练完成!")

def load_config(config_path):
    """加载配置文件"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_default_config():
    """创建默认配置文件"""
    default_config = {
        "model_path": "./models/qwen/Qwen3-0___6B",
        "data_dir": "data",
        "data_format": "multiple_files",  # "single_file" or "multiple_files"
        "data_file": "data/train.json",  # 当data_format为single_file时使用
        "output_dir": "./output/qwen3-finetune",
        "train_ratio": 0.8,
        
        # 模型配置
        "torch_dtype": "float32",
        "max_length": 384,
        
        # LoRA配置
        "use_lora": True,
        "lora_target_modules": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        "lora_r": 8,
        "lora_alpha": 32,
        "lora_dropout": 0.1,
        
        # 训练配置
        "per_device_train_batch_size": 4,
        "per_device_eval_batch_size": 4,
        "gradient_accumulation_steps": 4,
        "num_train_epochs": 3,
        "learning_rate": 1e-4,
        "warmup_steps": 100,
        "weight_decay": 0.01,
        "logging_steps": 10,
        "save_steps": 100,
        "eval_steps": 100,
        "eval_strategy": "steps",
        "load_best_model_at_end": True,
        "gradient_checkpointing": True,
        "fp16": False,
        
        # 生成配置
        "max_new_tokens": 100,
        "do_sample": True,
        "temperature": 0.7,
        "top_p": 0.9,
        
        # 系统提示词
        "system_prompt": "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\nYou are a helpful assistant.\n<|eot_id|>",
        
        # 评估配置
        "run_evaluation": True
    }
    
    return default_config

def main():
    parser = argparse.ArgumentParser(description="Qwen3-0.6B Fine-tuning Script")
    parser.add_argument("--config", type=str, default="config.json", help="配置文件路径")
    parser.add_argument("--create-config", action="store_true", help="创建默认配置文件")
    
    args = parser.parse_args()
    
    if args.create_config:
        config = create_default_config()
        with open("config.json", 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print("默认配置文件已创建: config.json")
        print("请修改配置文件中的路径和参数，然后运行训练")
        return
    
    # 加载配置
    if os.path.exists(args.config):
        config = load_config(args.config)
    else:
        print(f"配置文件 {args.config} 不存在，使用默认配置")
        config = create_default_config()
    
    # 创建输出目录
    os.makedirs(config['output_dir'], exist_ok=True)
    
    # 开始训练
    fine_tuner = Qwen3FineTuner(config)
    fine_tuner.train()

if __name__ == "__main__":
    main()