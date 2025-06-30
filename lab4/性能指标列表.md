# 📊 LLM 部署性能指标列表

在部署大语言模型（LLM）时，性能评估是确保系统稳定、高效运行的关键。本列表列出了常用的 LLM 性能评估指标，并简要说明各指标的定义和合理性。

## 1. **T<sub>PP</sub>/s（Token Preprocessing Time per second）**

- **定义**：每秒用于预处理 Token 的时间，包括文本编码、分词、Token ID 映射等。
- **合理性**：该指标衡量输入数据在进入模型之前的处理效率，对于高吞吐率场景尤为关键。

## 2. **S<sub>P</sub>/s（Sample Preprocessing per second）**

- **定义**：每秒可完成的输入样本预处理数量。
- **合理性**：在高并发部署场景中，样本的处理能力直接决定了系统的实时响应能力。

## 3. **T<sub>TG</sub>（Token Generation Time）**

- **定义**：生成一个 Token 所需的平均时间。
- **合理性**：这是衡量推理性能的关键指标，尤其在用户交互式应用中，影响生成流畅度和响应速度。

## 4. **S<sub>TG</sub>（Sequence Generation Speed）**

- **定义**：每秒生成的 Token 数（Tokens/s）。
- **合理性**：反映了整体推理吞吐能力，是部署系统扩展性（scalability）的基础指标之一。

## 5. **T（End-to-End Latency）**

- **定义**：从用户发送请求到接收到完整响应的总时间。
- **合理性**：该指标直接影响用户体验，特别是在实时交互系统（如聊天机器人）中是最关键的响应时间衡量。

## 6. **S（Throughput, Requests per Second）**

- **定义**：每秒能够处理的请求数。
- **合理性**：衡量系统承载能力和可伸缩性，尤其重要于多用户并发使用的生产环境。

## 7. **Perplexity（困惑度）**

- **定义**：衡量语言模型预测下一个 Token 不确定性的指标，越低表示模型越准确。
- **合理性**：Perplexity 是评价模型语言质量的核心指标之一，尤其在离线评估中广泛使用。

---

## ✅ 总结

| 指标名称        | 全称/单位                              | 作用说明                              |
|------------------|------------------------------------------|----------------------------------------|
| T<sub>PP</sub>/s | Token Preprocessing per second           | 输入Token预处理的效率                  |
| S<sub>P</sub>/s  | Sample Preprocessing per second          | 样本预处理能力，影响并发性能           |
| T<sub>TG</sub>   | Token Generation Time                    | 单个Token生成耗时，影响响应延迟        |
| S<sub>TG</sub>   | Sequence Generation Speed (Tokens/s)     | 每秒生成的Token数量，体现模型吞吐      |
| T                | End-to-End Latency (ms)                  | 用户完整请求处理时间                   |
| S                | System Throughput (req/s)                | 系统每秒处理请求的数量，体现并发能力    |
| Perplexity       | N/A                                      | 模型输出文本的语言质量衡量             |



