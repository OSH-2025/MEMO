import os
import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import PCA

# 设置目录
EMBED_DIR = "embeddings"
embedding_vectors = []
model_labels = []

# 加载所有 JSON 嵌入
for file in sorted(os.listdir(EMBED_DIR)):
    if file.endswith(".json"):
        with open(os.path.join(EMBED_DIR, file), 'r', encoding='utf-8') as f:
            data = json.load(f)
            embedding = data.get("embedding")
            if embedding:
                embedding_vectors.append(embedding)
                model_labels.append(file.replace(".json", ""))

embeddings = np.array(embedding_vectors)

# -----------------------------
# 1️⃣ 相似度矩阵 + 热力图绘制
# -----------------------------
sim_matrix = cosine_similarity(embeddings)

plt.figure(figsize=(8, 6))
sns.heatmap(sim_matrix, annot=True, xticklabels=model_labels, yticklabels=model_labels, fmt=".2f", cmap="YlGnBu")
plt.title("Cosine Similarity Between Embedding Models")
plt.xticks(rotation=30, ha="right")
plt.yticks(rotation=0)
plt.tight_layout()
plt.savefig("similarity_heatmap.png")
plt.show()

# -----------------------------
# 2️⃣ 可选：PCA 2D 降维展示
# -----------------------------
pca = PCA(n_components=2)
reduced = pca.fit_transform(embeddings)

plt.figure(figsize=(6, 6))
for i, label in enumerate(model_labels):
    plt.scatter(reduced[i, 0], reduced[i, 1], label=label)
    plt.text(reduced[i, 0] + 0.01, reduced[i, 1], label, fontsize=9)

plt.title("PCA of Model Embeddings")
plt.xlabel("PC1")
plt.ylabel("PC2")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig("embedding_pca.png")
plt.show()
