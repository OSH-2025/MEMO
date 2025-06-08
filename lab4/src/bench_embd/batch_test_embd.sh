# Description: 批量测试 Qwen3-Embedding-4B 模型的性能和质量
# Usage: ./batch_test_embd.sh
# Suggestion: 放在llama.cpp/build/bin 目录下

#!/bin/bash
models=(
  "Qwen3-Embedding-4B-Q4_K_M.gguf"
  "Qwen3-Embedding-4B-Q5_0.gguf"
  "Qwen3-Embedding-4B-Q5_K_M.gguf"
  "Qwen3-Embedding-4B-Q6_K.gguf"
  "Qwen3-Embedding-4B-Q8_0.gguf"
)

for model in "${models[@]}"
do
  echo "Testing $model"

  # 首次 Token 生成延迟
  ./llama-bench -m models/Qwen/Qwen3-Embedding-4B-GGUF/$model -p 512 -r 5

  # 总生成延迟
  ./llama-bench -m models/Qwen/Qwen3-Embedding-4B-GGUF/$model -pg 512,128 -r 5

  # 显存占用
  nvidia-smi
  
   # Embedding 向量生成 + 保存
  ./llama-embedding \
    -m models/Qwen/Qwen3-Embedding-4B-GGUF/$model \
    -p "早上好，世界！" \
    --pooling mean \
    --embd-normalize 2 \
    --embd-output-format json > embeddings/${base_name}.json

  echo ""
done
