#!/bin/bash
set -e

echo "=== 最终精细调优实验 ==="

# 实验17: 最佳lr + 最大LoRA容量
echo "实验17: 学习率0.0003 + 超大LoRA"
python train.py \
    --per_device_train_batch_size 2 \
    --per_device_eval_batch_size 2 \
    --max_length 512 \
    --learning_rate 0.0003 \
    --lora_r 64 \
    --lora_alpha 256 \
    --lora_dropout 0.05 \
    --gradient_accumulation_steps 4 \
    --num_train_epochs 4 \
    --output_dir output/exp18_lr0.0003_bs2_r64_a256_ep4_d0.05 \
    --data_dir data

# 实验18: 更高学习率 + 最佳其他配置
echo "实验18: 更高学习率0.0015"
python train.py \
    --per_device_train_batch_size 2 \
    --per_device_eval_batch_size 2 \
    --max_length 512 \
    --learning_rate 0.0015 \
    --lora_r 32 \
    --lora_alpha 128 \
    --lora_dropout 0.05 \
    --gradient_accumulation_steps 4 \
    --num_train_epochs 4 \
    --output_dir output/exp19_lr0.0015_bs2_r32_a128_ep4_d0.05 \
    --data_dir data

# 实验19: 最佳配置 + 更长序列
echo "实验19: 最佳配置 + ml=768"
python train.py \
    --per_device_train_batch_size 2 \
    --per_device_eval_batch_size 2 \
    --max_length 768 \
    --learning_rate 0.0003 \
    --lora_r 32 \
    --lora_alpha 128 \
    --lora_dropout 0.05 \
    --gradient_accumulation_steps 4 \
    --num_train_epochs 4 \
    --gradient_checkpointing \
    --output_dir output/exp20_lr0.0003_bs2_r32_a128_ep4_d0.05_ml768 \
    --data_dir data

echo "精细调优完成！"