## 📘 Embedding 向量生成与质量分析工具集

本项目包含一套用于评估多个 GGUF 模型嵌入质量的自动化脚本，适用于如 Qwen3-Embedding-4B 系列模型。支持向量生成、保存与分析，包含批处理 Bash 脚本与 Python 分析工具。

---

### 📁 项目结构

```
.
├── batch_test_embd.sh         # 批量生成嵌入向量脚本（Bash）
├── embedding_analysis.py      # 向量分析与可视化脚本（Python）
├── embeddings/                # 自动生成的嵌入向量文件目录
│   ├── Qwen3-Embedding-4B-Q4_K_M.json
│   └── ...
├── similarity_heatmap.png     # 余弦相似度热力图输出
└── embedding_pca.png          # PCA 降维分布图输出
```

---

## 一、嵌入向量生成

### 脚本：`batch_test_embd.sh`

批量对多个 GGUF 模型执行以下操作：

1. 测试首次 token 延迟、总生成延迟（llama-bench）
2. 打印显存占用（nvidia-smi）
3. 生成文本 `"早上好，世界！"` 的嵌入向量（llama-embedding）
4. 向量以 `.json` 格式保存至 `embeddings/` 文件夹

#### 用法

```bash
chmod +x batch_test_embd.sh
./batch_test_embd.sh
```

---

##  二、嵌入质量分析

### 脚本：`embedding_analysis.py`

基于 `embeddings/` 文件夹中嵌入向量文件，执行以下分析：

1. 计算模型嵌入之间的余弦相似度（cosine similarity matrix）
2. 绘制热力图（Heatmap）
3. 执行 PCA 降维并可视化（2D scatter plot）

#### 用法

```bash
pip install numpy matplotlib seaborn scikit-learn
python embedding_analysis.py
```

#### 输出文件

- `similarity_heatmap.png`：展示所有模型输出嵌入向量间的语义相似性
- `embedding_pca.png`：模型嵌入的分布可视化（2D）

---

##  注意事项

- `llama-embedding` 工具必须支持 `--embd-output-format json`
- 模型路径应在脚本中手动指定或调整
- 输入文本目前固定为 `"早上好，世界！"`，可根据测试任务自行替换

---

##  推荐后续扩展

- 支持批量文本向量比较（多输入对比）
- 集成 MTEB 评估框架进行标准化嵌入评测
- 保存为 CSV 或 NumPy 格式，支持向量数据库接入
