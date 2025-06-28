#!/bin/bash
set -e

echo "开始运行10个不同配置的训练实验..."

# 实验1：基础配置 - 中等学习率，小batch
echo "=== 实验1：基础配置 ==="
python train.py \
    --per_device_train_batch_size 2 \
    --per_device_eval_batch_size 2 \
    --max_length 512 \
    --learning_rate 0.0002 \
    --lora_r 8 \
    --lora_alpha 32 \
    --lora_dropout 0.1 \
    --gradient_accumulation_steps 4 \
    --num_train_epochs 3 \
    --output_dir output/exp1_lr0.0002_bs2_r8_a32 \
    --data_dir data

# 实验2：降低学习率
echo "=== 实验2：降低学习率 ==="
python train.py \
    --per_device_train_batch_size 2 \
    --per_device_eval_batch_size 2 \
    --max_length 512 \
    --learning_rate 0.0001 \
    --lora_r 8 \
    --lora_alpha 32 \
    --lora_dropout 0.1 \
    --gradient_accumulation_steps 4 \
    --num_train_epochs 3 \
    --output_dir output/exp2_lr0.0001_bs2_r8_a32 \
    --data_dir data

# 实验3：增大batch size
echo "=== 实验3：增大batch size ==="
python train.py \
    --per_device_train_batch_size 4 \
    --per_device_eval_batch_size 4 \
    --max_length 512 \
    --learning_rate 0.0002 \
    --lora_r 8 \
    --lora_alpha 32 \
    --lora_dropout 0.1 \
    --gradient_accumulation_steps 4 \
    --num_train_epochs 3 \
    --output_dir output/exp3_lr0.0002_bs4_r8_a32 \
    --data_dir data

# 实验4：增大LoRA rank
echo "=== 实验4：增大LoRA rank ==="
python train.py \
    --per_device_train_batch_size 2 \
    --per_device_eval_batch_size 2 \
    --max_length 512 \
    --learning_rate 0.0002 \
    --lora_r 16 \
    --lora_alpha 64 \
    --lora_dropout 0.1 \
    --gradient_accumulation_steps 4 \
    --num_train_epochs 3 \
    --output_dir output/exp4_lr0.0002_bs2_r16_a64 \
    --data_dir data

# 实验5：更高学习率
echo "=== 实验5：更高学习率 ==="
python train.py \
    --per_device_train_batch_size 2 \
    --per_device_eval_batch_size 2 \
    --max_length 512 \
    --learning_rate 0.0005 \
    --lora_r 8 \
    --lora_alpha 32 \
    --lora_dropout 0.1 \
    --gradient_accumulation_steps 4 \
    --num_train_epochs 3 \
    --output_dir output/exp5_lr0.0005_bs2_r8_a32 \
    --data_dir data

# 实验6：低学习率 + 大batch + 大rank
echo "=== 实验6：低学习率 + 大batch + 大rank ==="
python train.py \
    --per_device_train_batch_size 4 \
    --per_device_eval_batch_size 4 \
    --max_length 512 \
    --learning_rate 0.0001 \
    --lora_r 16 \
    --lora_alpha 64 \
    --lora_dropout 0.1 \
    --gradient_accumulation_steps 4 \
    --num_train_epochs 3 \
    --output_dir output/exp6_lr0.0001_bs4_r16_a64 \
    --data_dir data

# 实验7：更大的LoRA dropout
echo "=== 实验7：更大的LoRA dropout ==="
python train.py \
    --per_device_train_batch_size 2 \
    --per_device_eval_batch_size 2 \
    --max_length 512 \
    --learning_rate 0.0002 \
    --lora_r 8 \
    --lora_alpha 32 \
    --lora_dropout 0.2 \
    --gradient_accumulation_steps 4 \
    --num_train_epochs 3 \
    --output_dir output/exp7_lr0.0002_bs2_r8_a32_d0.2 \
    --data_dir data

# 实验8：更大的gradient accumulation
echo "=== 实验8：更大的gradient accumulation ==="
python train.py \
    --per_device_train_batch_size 1 \
    --per_device_eval_batch_size 1 \
    --max_length 512 \
    --learning_rate 0.0002 \
    --lora_r 8 \
    --lora_alpha 32 \
    --lora_dropout 0.1 \
    --gradient_accumulation_steps 8 \
    --num_train_epochs 3 \
    --output_dir output/exp8_lr0.0002_bs1_r8_a32_gs8 \
    --data_dir data

# 实验9：非常低的学习率
echo "=== 实验9：非常低的学习率 ==="
python train.py \
    --per_device_train_batch_size 2 \
    --per_device_eval_batch_size 2 \
    --max_length 512 \
    --learning_rate 0.00005 \
    --lora_r 8 \
    --lora_alpha 32 \
    --lora_dropout 0.1 \
    --gradient_accumulation_steps 4 \
    --num_train_epochs 3 \
    --output_dir output/exp9_lr0.00005_bs2_r8_a32 \
    --data_dir data

# 实验10：最大LoRA配置
echo "=== 实验10：最大LoRA配置 ==="
python train.py \
    --per_device_train_batch_size 2 \
    --per_device_eval_batch_size 2 \
    --max_length 512 \
    --learning_rate 0.0001 \
    --lora_r 32 \
    --lora_alpha 128 \
    --lora_dropout 0.1 \
    --gradient_accumulation_steps 4 \
    --num_train_epochs 3 \
    --output_dir output/exp10_lr0.0001_bs2_r32_a128 \
    --data_dir data

echo "所有实验完成！结果保存在各自的output目录下。"
echo "可以查看accuracy_summary.csv文件来比较各个实验的结果。"