# 针对大模型微调（Fine-tuning）的可行性报告

小组成员：于宛扬 杨玺禾 韩思琦 贾钰珩

我们希望模型在理解和预测用户文件操作这个垂直领域取得较好的表现，要达成这个目的，必然需要进行微调（Fine-tuning）。什么是微调？具体有哪些方法？在算力有限的前提下能否实现？
本报告由 韩思琦撰写，试图回答以上问题。

- [大模型微调（Fine-tuning）](#大模型微调fine-tuning)
  - [1 本质和核心](#1-本质和核心)
  - [2 fine-tuning 原理](#2-fine-tuning-原理)
    - [**核心步骤**](#核心步骤)
  - [3 前置知识（具体见其他文件）](#3-前置知识具体见其他文件)
    - [3.1 基础知识](#31-基础知识)
      - [注意力机制](#注意力机制)
      - [transformer结构](#transformer结构)
    - [3.2 大模型相关知识](#32-大模型相关知识)
      - [预训练](#预训练)
  - [4 fine-tuning的应用](#4-fine-tuning的应用)
      - [（1）全量微调（Full Fine-Tuning）](#1全量微调full-fine-tuning)
      - [（2）参数高效微调（Parameter-Efficient Fine-Tuning, PEFT）](#2参数高效微调parameter-efficient-fine-tuning-peft)
        - [1 前缀调优 Prefix Tuning](#1-前缀调优-prefix-tuning)
        - [2 提示调优 Prompt Tuning](#2-提示调优-prompt-tuning)
        - [3 LoRA](#3-lora)
        - [4 P-Tuning](#4-p-tuning)
        - [5 P-Tuning v2](#5-p-tuning-v2)
        - [6 Adapter Tuning](#6-adapter-tuning)
      - [（3）监督式微调（Supervised Fine-Tuning, SFT）](#3监督式微调supervised-fine-tuning-sft)
      - [（4）基于人类反馈的强化学习微调（RLHF）](#4基于人类反馈的强化学习微调rlhf)
        - [a）使用监督数据微调语言模型](#a使用监督数据微调语言模型)
        - [b）训练奖励模型](#b训练奖励模型)
        - [c）训练RL模型](#c训练rl模型)
      - [（5）基于AI反馈的强化学习微调（RLAIF）](#5基于ai反馈的强化学习微调rlaif)
      - [总结](#总结)
  - [5 模型微调的主要参数](#5-模型微调的主要参数)
    - [基础微调参数](#基础微调参数)
    - [高效微调（PEFT）参数](#高效微调peft参数)
  - [6 实操注意点](#6-实操注意点)
    - [支持微调的模型](#支持微调的模型)
    - [数据集](#数据集)
  - [7 具体例子--Chat-嬛嬛](#7-具体例子--chat-嬛嬛)


## 1 本质和核心

**DEF：**

- <u>Fine-tuning（微调）</u>通过特定领域数据对预训练模型进行针对性优化，以提升其在特定任务上的性能。
- <u>定制化功能</u>：微调的核心原因是赋予大模型更加定制化的功能。通用大模型虽然强大，但在特定领域可能表现不佳。通过微调，可以使模型更好地适应特定领域的需求和特征。



> **PS: ChatGPT 大模型微调**
>
> Hugging Face：一个提供丰富预训练模型和工具的领先平台，助力自然语言处理（NLP）任务的快速开发与部署。
>
> 跨平台兼容性：与 TensorFlow、PyTorch 和 Keras 等主流深度学习框架兼容。



## 2 fine-tuning 原理

在选定相关数据集和预训练模型的基础上，通过设置合适的超参数并对模型进行必要的调整，使用特定任务的数据对模型进行训练以优化其性能。

### **核心步骤**

1. 数据准备

   - 选择与任务相关的数据集。
   - 对数据进行预处理，包括清洗、分词、编码等。

2. 选择基础模型（eg BERT/GPT-3等）

3. 设置微调参数（设置需要的超参数）

4. 微调

   - 加载预训练的模型和权重。
   - 根据任务需求对模型进行必要的修改，如更改输出层。
   - 选择合适的损失函数和优化器。
   - 使用选定的数据集进行微调训练，包括前向传播、损失计算、反向传播和权重更新。


## 3 前置知识（具体见其他文件）

https://jalammar.github.io/illustrated-transformer/ 图解transformer

https://arxiv.org/abs/1706.03762 Attention Is All You Need论文



### 3.1 基础知识

#### 注意力机制

**参考**：

1. https://blog.csdn.net/m0_37605642/article/details/135958384
2. https://zh-v2.d2l.ai/chapter_attention-mechanisms/index.html

#### transformer结构

![../_images/transformer.svg](https://zh-v2.d2l.ai/_images/transformer.svg)

### 3.2 大模型相关知识

#### 预训练

参考：https://zh-v2.d2l.ai/chapter_natural-language-processing-pretraining/index.html

## 4 fine-tuning的应用

可通过全量调整所有参数以充分适应**新任务**，或采用参数高效微调技术仅优化部分参数以实现快速且低成本的**迁移学习**。

#### （1）全量微调（Full Fine-Tuning）

全量微调利用特定任务数据调整预训练模型的**所有参数**，以充分适应新任务。它依赖**大规模计算资源**，但能有效利用预训练模型的通用特征。

#### （2）参数高效微调（Parameter-Efficient Fine-Tuning, PEFT）

https://huggingface.co/docs/peft/index HuggingFace官方PEFT教程



PEFT旨在通过**最小化微调参数**数量和计算复杂度，实现高效的迁移学习。<u>它仅更新模型中的部分参数，显著降低训练时间和成本</u>，适用于计算资源有限的情况。PEFT技术包括Prefix Tuning、Prompt Tuning、Adapter Tuning等多种方法，可根据任务和模型需求灵活选择。

> ※ 大概率会选择prefix tuning，prompt tuning，LoRA 其一。

##### 1 前缀调优 Prefix Tuning

前缀调优的灵感来自于语言模型提示，前缀就好像是“虚拟标记”一样，这种方法可在特定任务的上下文中引导模型生成文本。前缀调优的独特之处在于它<u>不改变语言模型的参数，而是通过冻结LM参数</u>，仅优化一系列连续的任务特定向量（即前缀）来实现优化任务。前缀调优的架构下图所示。

![img](https://pic2.zhimg.com/v2-b3b00d7d2d31ac5faf12f30952379663_1440w.jpg)

由于在训练中只需要为每个任务存储前缀，前缀调优的轻量级设计避免了存储和计算资源的浪费，同时保持了模型的性能，具有模块化和高效利用空间的特点，有望在NLP任务中提供高效的解决方案。

> 在模型的输入序列前面加一些固定的“前缀向量”，这些向量在训练中被优化，用来引导模型输出特定任务的结果。

**可调参数：**

1. 虚拟Token数（num_virtual_tokens）：
   作用：在输入前添加的可训练前缀长度，影响任务适配能力。
   
   示例：文本生成任务常用 num_virtual_tokens=20：
   
   ```python
   peft_config = PrefixTuningConfig(task_type="CAUSAL_LM", num_virtual_tokens=20)
   ```
   
   

- 方法：在输入前添加可学习的virtual tokens作为Prefix。
- 特点：仅更新Prefix参数，Transformer其他部分固定。
- 优点：减少需要更新的参数数量，提高训练效率。

##### 2 提示调优 Prompt Tuning

> 不改变模型参数，而是为每个任务训练一些小的附加参数（比如一些提示词），这些参数会影响模型的输入表示。

- 方法：在输入层加入prompt tokens。


- 特点：简化版的Prefix Tuning，无需MLP调整。


- 优点：随着模型规模增大，效果接近full fine-tuning。

##### 3 LoRA



> 通过低秩分解的方式，给模型添加少量参数，让模型快速适应新任务。这些参数可以轻松切换，适合多任务场景。

**可调参数**：

1. 秩（Rank, r）：
   作用：低秩矩阵的维度，决定新增参数量。r=8时，7B模型仅新增0.1%参数。
   示例：Qwen2-1.5B微调文本分类，设置 r=8。
2. Alpha（lora_alpha）：
   作用：缩放低秩矩阵权重，通常设为 r的倍数（如r=8时alpha=16）。
3. Dropout（lora_dropout）：
   作用：防止新增层过拟合，推荐 0.1



- 方法：在矩阵相乘模块中引入低秩矩阵来模拟full fine-tuning。

- 特点：更新语言模型中的关键低秩维度。


- 优点：实现高效的参数调整，降低计算复杂度。

##### 4 P-Tuning

- 方法：将Prompt转换为可学习的Embedding层，并用MLP+LSTM处理。


- 特点：解决Prompt构造对下游任务效果的影响。


- 优点：提供更大的灵活性和更强的表示能力。

##### 5 P-Tuning v2

- 方法：在多层加入Prompt tokens。


- 特点：增加可学习参数数量，对模型预测产生更直接影响。


- 优点：在不同任务和模型规模上实现更好的性能。

##### 6 Adapter Tuning

**可调参数**：

1. 瓶颈维度（bottleneck_size）

   - **作用**：Adapter层中间层的维度，控制参数效率。

   - **示例**：BERT-base适配器微调，设置 `bottleneck_size=64`，参数量增加约0.5%

     

   方法：设计Adapter结构并嵌入Transformer中。

   特点：仅对新增的Adapter结构进行微调，原模型参数固定。

   优点：保持高效性的同时引入少量额外参数。



![图片](https://i-blog.csdnimg.cn/blog_migrate/681bed8452c6993165d7e8deaba1ac45.png)

#### （3）监督式微调（Supervised Fine-Tuning, SFT）

> 用带**标签**的数据集，通过传统的监督学习方式对模型进行微调。比如你有一堆标注好的电影评论（正面/负面），让模型学习这些数据。



#### （4）基于人类反馈的强化学习微调（RLHF）

> 通过**人类**的反馈来调整模型，让它输出的结果更符合人类的期望。比如ChatGPT就是用RLHF来微调的，让它生成的回答更人性化。

**RLHF**（Reinforcement Learning from Human Feedback）：一种利用人类反馈作为奖励信号来训练强化学习模型的方法，旨在提升模型生成文本等内容的质量，使其更符合人类偏好。

**强化学习**（Reinforcement Learning）结合人类反馈（Human Feedback）来微调大语言模型（Large Language Models）的**一般过程**：

##### a）使用监督数据微调语言模型

这一步与传统的fine-tuning类似，即使用标注过的数据来调整预训练模型的参数，使其更好地适应特定任务或领域。

<img src="https://i-blog.csdnimg.cn/blog_migrate/f06782ce6bad2ed8f9e4bf5c6bdc3ad1.png" alt="图片" style="zoom:67%;" />

##### b）训练奖励模型

**奖励模型**用于评估文本序列的质量，它接受一个文本作为输入，<u>并输出一个数值，表示该文本符合人类偏好的程度</u>。训练数据通常由多个语言模型生成的文本序列组成，这些序列经过人工评估或使用其他模型（如ChatGPT）进行打分。这个奖励信号在后续的强化学习训练中至关重要，因为它指导模型生成更符合人类期望的文本。

<img src="https://i-blog.csdnimg.cn/blog_migrate/eeaa63c3cd210d3a4fbe40ac3439979f.png" alt="图片" style="zoom:67%;" />

##### c）训练RL模型

在强化学习框架中，需要**定义状态空间、动作空间、策略函数和价值函数**。<u>状态空间</u>是输入序列的分布，<u>动作空间</u>是所有可能的token（即词汇表中的词）。<u>价值函数</u>结合了奖励模型的输出和策略约束，用于评估在给定状态下采取特定动作的价值。<u>策略函数</u>就是经过微调的大型语言模型，它根据当前状态选择下一个动作（token），以最大化累计奖励。



<img src="https://i-blog.csdnimg.cn/blog_migrate/378fc7efedceb2a6fb681925d60afaf2.png" alt="图片" style="zoom:67%;" />



#### （5）基于AI反馈的强化学习微调（RLAIF）



#### 总结

| 方法             | 核心思想                   | 优点                   | 缺点                         | 适用场景             |
| ---------------- | -------------------------- | ---------------------- | ---------------------------- | -------------------- |
| 全量微调 (FFT)   | 重新训练所有参数           | 性能提升显著           | 计算资源大，可能遗忘通用知识 | 数据量大，任务复杂   |
| Prompt Tuning    | 训练小型附加参数（提示词） | 计算成本低，避免遗忘   | 需要设计好的提示词           | 小数据量，多任务场景 |
| Prefix Tuning    | 在输入前加前缀向量         | 高效，适合特定任务     | 需要优化前缀向量             | 任务导向型场景       |
| LoRA             | 通过低秩分解添加少量参数   | 快速适应，轻松切换任务 | 需要设计低秩结构             | 多任务，资源有限场景 |
| 监督式微调 (SFT) | 用带标签的数据训练         | 简单直接，效果好       | 需要大量标注数据             | 有标注数据的任务     |
| RLHF             | 通过人类反馈调整模型       | 输出更符合人类期望     | 需要大量人类反馈，成本高     | 对话系统，生成任务   |
| RLAIF            | 通过AI反馈调整模型         | 成本低，效率高         | 依赖AI反馈的质量             | 低成本，高效率场景   |

## 5 模型微调的主要参数

### 基础微调参数

1. 学习率
2. batch size
3. epochs
4. weight decay

### 高效微调（PEFT）参数

见 section 4

## 6 实操注意点

> **参考项目：**
>
> 1. https://github.com/datawhalechina/self-llm

### 支持微调的模型

上面项目中支持的模型，包括以下：

- [Qwen系列](https://github.com/QwenLM/Qwen3)
- [Kimi](https://github.com/MoonshotAI/Kimi-VL)
- [Llama4](https://huggingface.co/meta-llama/Llama-4-Scout-17B-16E-Instruct)
- [SpatialLM](https://github.com/manycore-research/SpatialLM)
- [Hunyuan3D-2](https://huggingface.co/tencent/Hunyuan3D-2)
- [Gemma3](https://huggingface.co/google/gemma-3-4b-it)
- [DeepSeek-R1-Distill](https://www.modelscope.cn/models/deepseek-ai/DeepSeek-R1-Distill-Qwen-7B)
- [Apple OpenELM](https://machinelearning.apple.com/research/openelm)
- [Llama3_1-8B-Instruct](https://huggingface.co/meta-llama/Meta-Llama-3.1-8B-Instruct)
- [Gemma-2-9b-it](https://huggingface.co/google/gemma-2-9b-it)
- [Yuan2.0](https://github.com/IEIT-Yuan/Yuan-2.0)
- [DeepSeek-Coder-V2](https://github.com/deepseek-ai/DeepSeek-Coder-V2)
- [Qwen2](https://github.com/QwenLM/Qwen2)
- [GLM-4](https://github.com/THUDM/GLM-4.git)
- [Qwen 1.5](https://github.com/QwenLM/Qwen1.5.git)
- [谷歌-Gemma](https://huggingface.co/google/gemma-7b-it)
- [phi-3](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct)
- [CharacterGLM-6B](https://github.com/thu-coai/CharacterGLM-6B)
- [LLaMA3-8B-Instruct](https://github.com/meta-llama/llama3.git)
- [XVERSE-7B-Chat](https://modelscope.cn/models/xverse/XVERSE-7B-Chat/summary)
- [TransNormerLLM](https://github.com/OpenNLPLab/TransnormerLLM.git)
- [BlueLM Vivo 蓝心大模型](https://github.com/vivo-ai-lab/BlueLM.git)
- [InternLM2](https://github.com/InternLM/InternLM)
- [DeepSeek 深度求索](https://github.com/deepseek-ai/DeepSeek-LLM)
- [MiniCPM](https://github.com/OpenBMB/MiniCPM.git)



以及可能使用的以下一些常见的模型

| Model     | Model size                  | Default module  | Template  |
| --------- | --------------------------- | --------------- | --------- |
| LLaMA     | 7B/13B/33B/65B              | q_proj,v_proj   | -         |
| LLaMA-2   | 7B/13B/70B                  | q_proj,v_proj   | llama2    |
| BLOOM     | 560M/1.1B/1.7B/3B/7.1B/176B | query_key_value | -         |
| BLOOMZ    | 560M/1.1B/1.7B/3B/7.1B/176B | query_key_value | -         |
| Falcon    | 7B/40B                      | query_key_value | -         |
| Baichuan  | 7B/13B                      | W_pack          | baichuan  |
| Baichuan2 | 7B/13B                      | W_pack          | baichuan2 |
| InternLM  | 7B/20B                      | q_proj,v_proj   | intern    |
| Qwen      | 7B/14B                      | c_attn          | chatml    |
| ChatGLM3  | 6B                          | query_key_value | chatglm3  |

### 数据集

可能会用到的数据集：

1. Microsoft RDP User Command Prediction Dataset 微软为RDP（远程桌面协议）用户操作预测任务，包含用户在不同任务下的命令序列。（似乎主要是游戏？）https://www.kaggle.com/competitions/msbd5001-fall2019/overview

2. 虽是恶意软件样本，但包含详细进程操作序列，可提取用于行为序列建模。 https://www.kaggle.com/competitions/malware-classification/data

3.  **Custom Data Collection (自采集)**
   - 由于桌面操作日志的隐私性，很多研究都是自己开发工具，<u>记录用户的窗口切换、应用启动、文件操作、鼠标点击、键盘</u>输入等事件，然后对这些日志做序列建模。可以用 [AutoHotkey](https://www.autohotkey.com/)、[AutoIt](https://www.autoitscript.com/)、[pywinauto](https://pywinauto.readthedocs.io/en/latest/) 等工具自定义采集脚本。
   - 自己采集相关的数据（写代码），可能包括：
     - 进程名、PID
     - 启动/关闭时间
     - 当前占用内存（如Working Set/Private Bytes等）
     - 进程父子关系
     - 用户ID（如果有多用户）
   
4. 桌面环境数据模拟器，有些开源项目模拟了桌面环境下的操作，可以人工生成训练数据。示例：[OpenAI Gym Desktop](https://github.com/jamesacampbell/gym-desktop)（模拟桌面环境交互）

5. 可能的论文提及




**常用中文微调数据集：**

- 中文问答数据集（如CMRC 2018、DRCD等），用于训练问答系统。

- 中文情感分析数据集（如ChnSentiCorp、Fudan News等），用于训练情感分类模型。

- 中文文本相似度数据集（如LCQMC、BQ Corpus等），用于训练句子对匹配和相似度判断任务。

- 中文摘要生成数据集（如LCSTS、NLPCC等），用于训练文本摘要生成模型。

- 中文对话数据集（如LCCC、ECDT等），用于训练聊天机器人或对话系统。
  

## 7 具体例子--Chat-嬛嬛

经过模型下载，整理数据，模型微调（LoRA)等步骤，我们成功复现了这个模型的微调。

![image-20250502213800001](.\graph\image-20250502213800001.png)
