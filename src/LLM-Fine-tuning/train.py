from datasets import Dataset
import pandas as pd
import torch
import re
import numpy as np
from transformers import AutoTokenizer, AutoModelForCausalLM, DataCollatorForSeq2Seq, TrainingArguments, Trainer, GenerationConfig
from peft import LoraConfig, TaskType, get_peft_model
import os
import glob
import pandas as pd
from datasets import Dataset


def process_func(example):
    global tokenizer
    MAX_LENGTH = 384

    # 1. system prompt - 修复了语法错误
    system_prompt = (
        "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
        "Cutting Knowledge Date: December 2023\n"
        "Today Date: 26 Jul 2024\n\n"
        "你是一个智能助手，请根据用户最近的活动序列，预测下一个最有可能的用户活动。请确保输出格式与输入格式一致，应为\"时间 - 操作\"的形式。\n"
        "<|eot_id|>"
    )

    # 2. user prompt（instruction+input拼接，紧跟 system 之后）
    user_prompt = (
        "<|start_header_id|>user<|end_header_id|>\n\n"
        f"{example['instruction']}\n{example['input']}"
        "<|eot_id|>"
    )

    # 3. assistant prompt（准备assistant的起始）
    assistant_prompt = "<|start_header_id|>assistant<|end_header_id|>\n\n"

    # 4. 用 tokenizer 拼接前半段
    prompt = system_prompt + user_prompt + assistant_prompt
    prompt_tokens = tokenizer(prompt, add_special_tokens=False)
    response_tokens = tokenizer(f"{example['output']}<|eot_id|>", add_special_tokens=False)

    # 5. 拼接所有 id
    input_ids = prompt_tokens["input_ids"] + response_tokens["input_ids"] + [tokenizer.pad_token_id]
    attention_mask = prompt_tokens["attention_mask"] + response_tokens["attention_mask"] + [1]

    # 6. labels：只有 assistant 部分有标签，其余为 -100
    labels = (
        [-100] * len(prompt_tokens["input_ids"]) +
        response_tokens["input_ids"] +
        [tokenizer.pad_token_id]
    )

    # 7. 截断
    if len(input_ids) > MAX_LENGTH:
        input_ids = input_ids[:MAX_LENGTH]
        attention_mask = attention_mask[:MAX_LENGTH]
        labels = labels[:MAX_LENGTH]

    return {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "labels": labels
    }

def generate_prediction(model, tokenizer, instruction, input_text):
    # 构建提示
    system_prompt = (
        "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
        "Cutting Knowledge Date: December 2023\n"
        "Today Date: 26 Jul 2024\n\n"
        "你是一个智能助手，请根据用户最近的活动序列，预测下一个最有可能的用户活动。请确保输出格式与输入格式一致，应为\"时间 - 操作\"的形式。\n"
        "<|eot_id|>"
    )
    
    user_prompt = (
        "<|start_header_id|>user<|end_header_id|>\n\n"
        f"{instruction}\n{input_text}"
        "<|eot_id|>"
    )
    
    assistant_prompt = "<|start_header_id|>assistant<|end_header_id|>\n\n"
    
    prompt = system_prompt + user_prompt + assistant_prompt
    
    # 生成回答
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    
    generation_config = GenerationConfig(
        max_new_tokens=100,
        do_sample=True,  # 启用随机采样
        temperature=0.7,
        top_p=0.9,
        pad_token_id=tokenizer.pad_token_id,
        eos_token_id=tokenizer.eos_token_id
    )
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            generation_config=generation_config
        )
    
    response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()
    return response

def parse_activity(activity_text):
    """从活动文本中提取时间、操作类型和应用/网站信息"""
    if not activity_text:
        return None, None, None
    
    # 尝试解析时间和操作
    pattern = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - (.+)"
    match = re.match(pattern, activity_text)
    if not match:
        return None, None, None
    
    timestamp = match.group(1)
    action_text = match.group(2)
    
    # 解析操作类型和目标应用/网站
    operation_type = None
    target = None
    
    # 启动应用
    if "启动应用:" in action_text:
        operation_type = "process_start"
        app_match = re.search(r"启动应用: (.+)", action_text)
        if app_match:
            target = app_match.group(1)
    
    # 关闭应用
    elif "关闭应用:" in action_text:
        operation_type = "process_end"
        app_match = re.search(r"关闭应用: (.+)", action_text)
        if app_match:
            target = app_match.group(1)
    
    # 访问网站
    elif "访问网站" in action_text:
        operation_type = "browser_history"
        website_match = re.search(r"访问网站 ([^ ]+)", action_text)
        if website_match:
            target = website_match.group(1)
    
    # 访问文件
    elif "访问文件:" in action_text:
        operation_type = "file_access"
        file_match = re.search(r"访问文件: (.+)", action_text)
        if file_match:
            target = file_match.group(1)
    
    # 应用聚焦
    elif "切换到窗口:" in action_text:
        operation_type = "window_focus"
        window_match = re.search(r"切换到窗口: (.+)", action_text)
        if window_match:
            target = window_match.group(1)
    
    # 应用使用时长
    elif "使用应用:" in action_text:
        operation_type = "app_usage"
        usage_match = re.search(r"使用应用: (.+)", action_text)
        if usage_match:
            target = usage_match.group(1)
    
    return timestamp, operation_type, target

def compute_accuracy(predictions, references):
    """计算预测准确度"""
    correct = 0
    partial_correct = 0  # 部分正确（比如时间正确但操作不同）
    total = len(predictions)
    
    print(f"\n计算准确率，共有 {total} 个样本")
    
    # 用于记录正确和错误的示例
    correct_examples = []
    incorrect_examples = []
    
    for i, (pred, ref) in enumerate(zip(predictions, references)):
        # 解析预测和参考
        pred_time, pred_op, pred_target = parse_activity(pred)
        ref_time, ref_op, ref_target = parse_activity(ref)
        
        # 记录详细信息（仅前几个样本和部分错误样本）
        if i < 5 or (pred != ref and len(incorrect_examples) < 5):
            print(f"\n样本 {i}:")
            print(f"预测: '{pred}'")
            print(f"参考: '{ref}'")
            print(f"解析结果 - 预测: 时间={pred_time}, 操作={pred_op}, 目标={pred_target}")
            print(f"解析结果 - 参考: 时间={ref_time}, 操作={ref_op}, 目标={ref_target}")
        
        # 计算准确度
        if pred == ref:  # 完全匹配
            correct += 1
            if len(correct_examples) < 3:
                correct_examples.append({
                    "预测": pred,
                    "参考": ref
                })
        elif pred_target == ref_target and pred_op == ref_op:  # 操作和目标相同，但时间可能不同
            partial_correct += 1
            if len(incorrect_examples) < 10:
                incorrect_examples.append({
                    "预测": pred,
                    "参考": ref,
                    "状态": "部分正确（操作和目标相同）"
                })
        else:
            if len(incorrect_examples) < 10:
                incorrect_examples.append({
                    "预测": pred,
                    "参考": ref,
                    "状态": "不正确"
                })
    
    # 输出一些正确的例子
    if correct_examples:
        print("\n部分正确预测示例:")
        for i, example in enumerate(correct_examples):
            print(f"\n正确示例 {i+1}:")
            for k, v in example.items():
                print(f"{k}: {v}")
    
    # 输出一些不正确的例子
    if incorrect_examples:
        print("\n部分不正确的预测:")
        for i, example in enumerate(incorrect_examples):
            print(f"\n错误示例 {i+1}:")
            for k, v in example.items():
                print(f"{k}: {v}")
    
    accuracy = correct / total if total > 0 else 0
    partial_accuracy = partial_correct / total if total > 0 else 0
    
    print(f"\n完全正确预测: {correct}/{total} ({accuracy:.4f})")
    print(f"部分正确预测: {partial_correct}/{total} ({partial_accuracy:.4f})")
    print(f"总体准确率: {(correct + partial_correct/2)/total:.4f} (完全正确+一半部分正确的权重)")
    
    return accuracy

if __name__ == "__main__":
    model = AutoModelForCausalLM.from_pretrained(
        './LLM-Research/Meta-Llama-3___1-8B-Instruct',
        device_map="auto",
        torch_dtype=torch.bfloat16
    )
    model.enable_input_require_grads() # 开启梯度检查点时，要执行该方法
    tokenizer = AutoTokenizer.from_pretrained(
        './LLM-Research/Meta-Llama-3___1-8B-Instruct',
        use_fast=False,
        trust_remote_code=True
    )
    tokenizer.pad_token = tokenizer.eos_token

    DATA_DIR = 'data'  # 假设所有json都在data目录下

    # 1. 收集所有json文件路径
    json_files = glob.glob(os.path.join(DATA_DIR, '*.json'))
    print(f"检测到 {len(json_files)} 个json文件: {json_files}")

    # 2. 分别读取每个json文件，单独做8:2划分
    train_dfs = []
    val_dfs = []

    for json_file in json_files:
        df = pd.read_json(json_file)
        # 设定随机种子保证可复现
        train_df = df.sample(frac=0.8, random_state=42)
        val_df = df.drop(train_df.index).reset_index(drop=True)
        train_dfs.append(train_df)
        val_dfs.append(val_df)
        print(f"{os.path.basename(json_file)}: 训练样本 {len(train_df)}, 验证样本 {len(val_df)}")

    # 3. 合并所有训练集和验证集
    final_train_df = pd.concat(train_dfs, ignore_index=True)
    final_val_df = pd.concat(val_dfs, ignore_index=True)
    print(f"\n合并后总训练集大小: {len(final_train_df)}, 总验证集大小: {len(final_val_df)}")

    # 4. 创建HuggingFace数据集（用合并后的df）
    train_ds = Dataset.from_pandas(final_train_df)
    val_ds = Dataset.from_pandas(final_val_df)

    # 5. 处理数据集
    train_tokenized = train_ds.map(process_func, remove_columns=train_ds.column_names)
    val_tokenized = val_ds.map(process_func, remove_columns=val_ds.column_names)

    config = LoraConfig(
        task_type=TaskType.CAUSAL_LM, 
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        inference_mode=False, # 训练模式
        r=8, # Lora 秩
        lora_alpha=32, # Lora alaph，具体作用参见 Lora 原理
        lora_dropout=0.1# Dropout 比例
    )
    model = get_peft_model(model, config)
    model.print_trainable_parameters() # 打印总训练参数

    args = TrainingArguments(
        output_dir="./output/llama3_1_instruct_lora",
        per_device_train_batch_size=4,
        per_device_eval_batch_size=4,
        gradient_accumulation_steps=4,
        logging_steps=10,
        num_train_epochs=3,
        save_steps=10, # 为了快速演示，这里设置10，建议你设置成100
        learning_rate=1e-4,
        save_on_each_node=True,
        gradient_checkpointing=True,
        evaluation_strategy="epoch", # 每个epoch评估一次
        save_strategy="epoch", # 每个epoch保存一次
        load_best_model_at_end=True, # 训练结束后加载最佳模型
        metric_for_best_model="eval_loss" # 以验证集损失为指标选择最佳模型
    )
    
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_tokenized,
        eval_dataset=val_tokenized,
        data_collator=DataCollatorForSeq2Seq(tokenizer=tokenizer, padding=True),
    )
    
    # 开始训练
    trainer.train()
    
    # 训练完成后，在验证集上进行预测评估
    print("开始在验证集上进行预测评估...")
    predictions = []
    references = final_val_df['output'].tolist()
    
    # 修复进度显示逻辑
    total_samples = len(final_val_df)
    for i, row in final_val_df.iterrows():
        instruction = row['instruction']
        input_text = row['input']
        prediction = generate_prediction(model, tokenizer, instruction, input_text)
        predictions.append(prediction)
        
        # 每10个样本显示一次进度，确保不会超过总样本数
        if (i + 1) % 10 == 0:
            print(f"已完成 {i + 1}/{total_samples} 条预测")
    
    # 确保进度条显示100%
    if total_samples % 10 != 0:
        print(f"已完成 {total_samples}/{total_samples} 条预测")
    
    # 计算准确率
    accuracy = compute_accuracy(predictions, references)
    print(f"验证集预测准确率: {accuracy:.4f}")
    
    # 保存预测结果
    all_results = []
    for i in range(len(predictions)):
        pred_time, pred_op, pred_target = parse_activity(predictions[i])
        ref_time, ref_op, ref_target = parse_activity(references[i])
        
        all_results.append({
            "instruction": final_val_df.iloc[i]['instruction'],
            "input": final_val_df.iloc[i]['input'],
            "reference": references[i],
            "prediction": predictions[i],
            "ref_time": ref_time,
            "ref_operation": ref_op,
            "ref_target": ref_target,
            "pred_time": pred_time,
            "pred_operation": pred_op,
            "pred_target": pred_target,
            "exact_match": predictions[i] == references[i],
            "operation_match": pred_op == ref_op,
            "target_match": pred_target == ref_target
        })
    
    # 保存结果
    pd.DataFrame(all_results).to_csv("prediction_results.csv", index=False)
    print("所有预测结果已保存到 prediction_results.csv")