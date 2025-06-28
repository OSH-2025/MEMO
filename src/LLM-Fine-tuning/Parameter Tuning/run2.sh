#!/bin/bash
set -e

echo "开始第二轮优化实验..."

# 实验11: 基于最佳配置，尝试更高的学习率
echo "=== 实验11: 更高学习率 (0.001) ==="
python train.py \
    --per_device_train_batch_size 2 \
    --per_device_eval_batch_size 2 \
    --max_length 512 \
    --learning_rate 0.001 \
    --lora_r 8 \
    --lora_alpha 32 \
    --lora_dropout 0.1 \
    --gradient_accumulation_steps 4 \
    --num_train_epochs 3 \
    --output_dir output/exp11_lr0.001_bs2_r8_a32 \
    --data_dir data

# 实验12: 最佳学习率 + 大LoRA rank + 更大alpha
echo "=== 实验12: 高rank高alpha配置 ==="
python train.py \
    --per_device_train_batch_size 2 \
    --per_device_eval_batch_size 2 \
    --max_length 512 \
    --learning_rate 0.0005 \
    --lora_r 32 \
    --lora_alpha 128 \
    --lora_dropout 0.1 \
    --gradient_accumulation_steps 4 \
    --num_train_epochs 3 \
    --output_dir output/exp12_lr0.0005_bs2_r32_a128 \
    --data_dir data

# 实验13: 尝试更大的LoRA rank
echo "=== 实验13: 超大LoRA rank ==="
python train.py \
    --per_device_train_batch_size 2 \
    --per_device_eval_batch_size 2 \
    --max_length 512 \
    --learning_rate 0.0002 \
    --lora_r 64 \
    --lora_alpha 256 \
    --lora_dropout 0.1 \
    --gradient_accumulation_steps 4 \
    --num_train_epochs 3 \
    --output_dir output/exp13_lr0.0002_bs2_r64_a256 \
    --data_dir data

# 实验14: 更多训练轮次
echo "=== 实验14: 更多训练轮次 (5 epochs) ==="
python train.py \
    --per_device_train_batch_size 2 \
    --per_device_eval_batch_size 2 \
    --max_length 512 \
    --learning_rate 0.0002 \
    --lora_r 8 \
    --lora_alpha 32 \
    --lora_dropout 0.1 \
    --gradient_accumulation_steps 4 \
    --num_train_epochs 5 \
    --output_dir output/exp14_lr0.0002_bs2_r8_a32_ep5 \
    --data_dir data

# 实验15: 最佳配置 + 梯度检查点 + 更长序列
echo "=== 实验15: 启用梯度检查点 + 更长序列 ==="
python train.py \
    --per_device_train_batch_size 2 \
    --per_device_eval_batch_size 2 \
    --max_length 768 \
    --learning_rate 0.0002 \
    --lora_r 8 \
    --lora_alpha 32 \
    --lora_dropout 0.1 \
    --gradient_accumulation_steps 4 \
    --num_train_epochs 3 \
    --gradient_checkpointing \
    --output_dir output/exp15_lr0.0002_bs2_r8_a32_ml768_gc \
    --data_dir data

# 实验16: 组合最优参数：中等lr + 大rank + 更多epochs
echo "=== 实验16: 综合最优配置 ==="
python train.py \
    --per_device_train_batch_size 2 \
    --per_device_eval_batch_size 2 \
    --max_length 512 \
    --learning_rate 0.0003 \
    --lora_r 32 \
    --lora_alpha 128 \
    --lora_dropout 0.05 \
    --gradient_accumulation_steps 4 \
    --num_train_epochs 4 \
    --output_dir output/exp16_lr0.0003_bs2_r32_a128_ep4_d0.05 \
    --data_dir data

echo "第二轮实验完成！"
echo "建议重点关注实验12、14和16的结果。"