# 结题报告

## 小组成员
* 于宛扬（组长）
* 杨玺禾
* 韩思琦
* 贾钰珩

## 引言

### 项目背景
随着人工智能技术的快速发展，尤其是大语言模型（如LLaMA、Qwen、GPT 等）在自然语言处理、上下文建模、意图理解等方面的突破，人机交互系统正逐步从“被动响应”向“主动预测”演进。传统的应用程序或操作系统仅在用户发出明确指令后执行操作，而随着用户对效率和智能化的期待不断提高，能够预判用户需求并提前执行操作的系统显得尤为重要。

本项目的核心目标是：利用大模型对用户的历史操作行为进行学习，从而预测其未来的操作，并进行智能反馈或预执行操作，从而优化用户体验和交互效率。

#### 一、技术背景

##### 1.用户行为建模的逐步成熟
在移动应用、操作系统和网页行为分析等领域，用户行为数据早已被广泛用于分析使用偏好和优化界面设计。然而传统方法多依赖于统计模型或浅层机器学习算法，难以捕捉长程依赖和复杂语义关系。而大模型特别是因上下文感知能力强、对多模态输入具备适配性的优势，已成为建模用户序列数据的理想选择。

##### 2.大模型 + LoRA 微调的有效融合
大模型虽强，但部署成本高，训练门槛高。Low-Rank Adaptation (LoRA) 提供了一种轻量级、低资源开销的参数微调方式，使得我们能够在保留大模型泛化能力的同时，专注于用户特定数据的学习，这对于个性化预测尤其重要。

##### 3.系统层集成与自动化反馈的趋势
随着本地大模型部署工具（如 llama.cpp、vLLM）与操作系统接口（如 Windows API、macOS Automation）的打通，未来可以实现“预测即响应”的闭环操作体验，例如在你即将打开某网页或文件前，系统就已预加载内容甚至提前打开目标应用。

#### 二、已有商业案例对比参考
* Google Now / Google Assistant：通过分析用户日程、搜索、位置数据提供“预测性卡片”，但模型粒度不够个性化，无法基于本地应用行为细粒度预测。
* Apple Siri Suggestions：能基于近期 App 使用习惯进行建议，但其模型为黑盒，无法在本地个性化训练或嵌入微调机制。

相比之下，本项目的优势在于：
* 使用LoRA 微调后的大语言模型，具备更强上下文理解与泛化能力；
* 基于真实用户的时间操作序列数据进行建模，更具个性化；
* 可集成到本地系统中形成完整闭环，实现预测—执行一体化。
### 项目成果概述



## 项目总体架构
![architecture](/final_report/asset/architecture.png)


## 各模块技术细节

### 数据收集



### LLM微调

#### 大模型微调背景
大规模预训练语言模型（如 LLaMA、Qwen、GPT 等）通常具备强大的泛化能力，但它们的参数规模巨大（通常数亿至数千亿参数），训练和更新成本高昂。直接对整个大模型进行微调：
* 需要大量计算资源和显存，
* 容易导致“灾难性遗忘”，使模型丧失原有通用知识，
* 微调后的模型体积庞大，部署困难。

因此，在实际应用中，往往采用更高效的微调技术，使模型能针对特定任务或领域快速适应，同时保留原模型权重不变。

#### LoRA（Low-Rank Adaptation）技术原理
LoRA 是一种近年来提出的轻量级微调方法，主要思想是在保持预训练模型主权重不变的基础上，仅学习一小部分低秩矩阵参数，以调整模型的表达能力。

具体原理如下：
* 对 Transformer 中的权重矩阵 $W_0\in \mathbb{R}^{m\times n}$ （例如查询、键、值矩阵）进行微调时，不直接更新 $W_0$ ，而是用两个低秩矩阵 $A\in \mathbb{R}^{m\times r}$， $B\in \mathbb{R}^{r\times m}$ 来近似微调参数增量，
* 微调后的权重表示为：
 $W_1=W_0+\Delta W=W_0+A\cdot B$
其中 $r\ll\mathrm{min}\{m,n\}$ ，即秩远小于矩阵维度，显著减少需要训练的参数量。
* 训练时只更新 $A$ 和 $B$ ，主权重 $W_0$保持冻结。

#### LoRA 的优点
* 参数量少，训练效率高

  只需训练低秩矩阵，参数量减少数百倍以上，显著节省显存和计算资源。
* 避免灾难性遗忘

  主模型权重保持不变，微调时保留原有知识，增强泛化能力。
* 易于集成和部署

  微调参数是增量权重，可以方便地与原始模型融合或分开存储，实现模块化更新。
* 适合个性化和增量训练

  对不同用户或任务可训练独立的低秩矩阵，支持模型快速适配。

#### LoRA 在本模块中的具体应用


### 端到端用户行为预测和应用优化系统

#### 系统概述

本系统是一个智能的用户行为预测系统，通过监控用户在Windows上的应用使用模式，利用部署在Linux云服务器上的大语言模型进行预测，并提前预加载用户可能要使用的应用程序，从而提升用户体验。



#### 环境要求

> **Windows端**
>- Python 3.8+
>- 必需库：`psutil`, `pywin32`, `requests`, `threading`
>- 支持SSH客户端（Windows 10/11自带）

> **Linux云服务器**
>- Python 3.8+
>- PyTorch + Transformers
>- FastAPI + Uvicorn
>- 微调后的LLM模型



#### 配置文件说明(json)

```r

{
  "system": {
    "queue_size": 10,              // 活动队列大小
    "prediction_window": 5,        // 预测窗口大小
    "prediction_cooldown": 30,     // 预测冷却时间(秒)
    "confidence_threshold": 0.6    // 预加载置信度阈值
  },
  "llm": {
    "use_ssh_tunnel": true,        // 是否使用SSH隧道
    "server_host": "js2.blockelite.cn",
    "server_port": 8000,
    "timeout": 15
  },
  "ssh": {
    "host": "js2.blockelite.cn",   // 云服务器地址
    "port": 17012,                 // SSH端口 (新端口)
    "username": "root",
    "tunnel_local_port": 8000,     // 本地隧道端口
    "tunnel_remote_port": 8000     // 远程隧道端口
  }
}
```

#### 系统启动流程

1. 启动云服务器LLM服务

```r
ssh root@js2.blockelite.cn -p 17012
cd /home/vipuser/llm
python model_api_server.py
```

2.  建立SSH隧道（新窗口）

```r
ssh -L 8000:localhost:8000 root@js2.blockelite.cn -p 17012
```

3. 启动Windows端系统（再开新窗口）

```r
python end_to_end_system.py
```

4.  系统运行状态

正常运行时，你会看到：

```r
🎯 端到端用户行为预测和应用优化系统
======================================

✅ 云服务器LLM模型已就绪
🚀 系统启动中...
📊 开始监控用户活动...
🔮 LLM预测服务已就绪...

📊 新活动: 2025-06-28 22:30:15 - 切换到窗口: Chrome (应用: chrome.exe)
🔮 开始预测，基于最近 5 个活动
✅ 解析成功: Code.exe 在 22:32:15
⏰ 将在 120.0 秒后预加载应用 Code.exe
```

支持的应用

- Code.exe - Visual Studio Code
- chrome.exe - Google Chrome
- msedge.exe - Microsoft Edge
- explorer.exe - 文件资源管理器
- notepad.exe - 记事本
- calc.exe - 计算器
- QQ.exe - QQ
- WeChat.exe - 微信
- SnippingTool.exe - 截图工具

#### 故障排除

**常见问题**

Q1: SSH连接失败

```r
ssh: connect to host js2.blockelite.cn port 17012: Connection refused
```
**解决办法：**
1. 检查网络连接
2. 确认端口号是否正确（17012）
3. 检查云服务器是否运行

 Q2: SSH隧道建立失败

```r
bind [127.0.0.1]:8000: Address already in use
```

**解决办法：**
本地8000端口被占用 ,关闭其他占用8000端口的程序：

```r
netstat -ano | findstr :8000
taskkill /PID <PID号> /F
```




Q3: API连接失败

```r
❌ 连接失败: 连接被拒绝
```

**解决办法：**
1. 确认SSH隧道已建立
2. 确认云服务器API服务正在运行
3. 测试本地连接：curl http://localhost:8000/health

Q4: 预测解析失败

```r

❌ 无法解析云服务器预测结果
```
**可能原因以及解决办法：**
1. LLM返回格式不标准，这是正常的。系统会尝试智能提取应用信息
2. 可以降低 confidence_threshold 阈值

Q5: 应用预加载失败
```r

❌ 不支持的应用: xxx.exe
```

**解决办法：**

1. 检查应用是否在支持列表中
2. 确认应用路径在 ApplicationManager 中正确配置
   

#### 调试模式
启用详细日志，查看日志文件：：

```r
logging.basicConfig(level=logging.DEBUG)
```


#### 性能调优
**系统参数调整**
1. 提高预测频率：

```r
"prediction_cooldown": 15  // 降低到15秒
```

2. 提高预加载门槛：

```r
"confidence_threshold": 0.8  // 提高到0.8
```

3. 增加监控范围：

```r
"queue_size": 15,
"prediction_window": 8
```

4. 网络优化: 使用更稳定的SSH连接：

```r
ssh -L 8000:localhost:8000 -o ServerAliveInterval=60 -o ServerAliveCountMax=3 root@js2.blockelite.cn -p 17012
```

#### 系统监控
**关键指标**
1. 预测成功率: 成功解析的预测比例
2. 应用命中率: 预加载应用被实际使用的比例
3. 响应时间: LLM预测响应时间
4. 资源使用: CPU和内存占用日志分析

```r

# 统计预测成功率

grep "✅ 解析成功" end_to_end_system.log | wc -l

# 统计预加载次数  

grep "🚀 已预加载应用" end_to_end_system.log | wc -l

# 查看最近的错误

grep "ERROR" end_to_end_system.log | tail -10
```

#### 开发指南

**添加新应用支持**

在 ApplicationManager 中添加应用路径：

```r
self.app_executables = {

    # 现有应用...

​    'new_app.exe': r'C:\Path\To\New\App.exe'
}
```

在 _extract_app_from_prediction 中添加识别规则：

```r
app_patterns = {

    # 现有规则...

​    r'New App Name': 'new_app.exe'
}
```

**自定义预测逻辑**

修改 _predict_via_cloud_api 中的指令：

```r
instruction = """
自定义的预测指令...
"""
```

#### 安全注意事项

**1. SSH密钥认证（推荐）：**

```r
ssh-keygen -t rsa -b 4096
ssh-copy-id root@js2.blockelite.cn -p 17012
```

**2. 限制SSH隧道绑定：**

```r

ssh -L 127.0.0.1:8000:localhost:8000 root@js2.blockelite.cn -p 17012
```

**3. 配置防火墙：**

1. 仅允许必要的端口访问
2. 配置云服务器安全组



### 模拟强化学习调度

#### 实现背景

**与星期的关联性**

根据个人的PC使用偏好，我们认为PC软件的使用时间与星期呈现较大的相关性。对于学生和老师而言，由于课程的安排规划常常按照课程表（按照周为单位）进行。因此，他们的PC软件使用情况理应与星期呈现较大的关联性。这一发现不仅仅适用于师生群体。一项发表于PLOS ONE的研究分析了美国得克萨斯州一家大型能源公司789名办公室员工在两年内的电脑使用数据。研究发现：

1. 工作量在一个星期内逐日增加：从周一到周四，员工的电脑使用量（包括打字数量、鼠标点击和滚动）逐渐增加。

2. 周五显著下降：到了周五，尤其是下午，电脑使用量显著减少，打字数量下降了约19%，而打字错误仅减少了1.65%，表明工作效率下降。

这些结果表明，员工在一周的不同工作日中，电脑使用模式存在显著差异，可能受到心理和行为因素的影响。[1] 根据对自身行为的理解以及如上相关研究，我们打算以星期为单位对用户的软件使用进行预测，从而提高预测的准确率。


**纠错机制**
我们在使用中发现，预测失败的惩罚力度较高。首先，站在操作系统的维度，错误的预测会导致不需要执行的程序占用处理器及内存，是一种极大的资源浪费。由于错误的程序占用系统资源，处理器需要把这些程序再调出内存，增加了上下文转换的工作量。在预测不精确的情况下也会为系统带来不菲的开销。

因此我们提出了一种**提前纠错机制**。首先，如果预测结果显示在某时刻应该启用某软件时，在启用软件之前，我们会先询问用户是否需要启动该软件。如果用户同意，那么正常起启动该软件；如果用户不同意，那么不启用该软件，同时会将这一启动操作在启动队列中对应的表项删除。这表示用户认为预测失败，或者认为与自己的使用需求不相符。通过这样的方式，可以实现对预测结果与用户需求的综合考量，在极大程度上优化了用户的体验感。

#### 实现原理
微调的预测结果会被写入prediction_results.csv中，而根据星期为周期的预测结果将会被写入prediction_buffer.csv中。系统调用程序将根据prediction_buffer.csv中的预测结果来执行。prediction_buffer.csv相当于一个在预测和执行中间的缓冲区，给缓冲区的内容对用户是透明的，但是直接的预测结果（prediction_results.csv）对用户不透明。

对于buffer的填充原理，我们采用预测即填充的方式，即根据用户一个周期的使用情况结果会根据用户使用数据的更新不断被写入至这一buffer中。

对于buffer的删除原理，我们考虑了用户的实际使用需求。在系统调用前，我们会提醒用户根据预测结果，有某软件需要被启用，并询问它的需求。如果用户拒绝该请求，不仅这一预测结果不会被执行，它同时会从prediction_buffer.csv中被删除。这样<span style="color:red;">从一定程度上降低了预测失败的惩罚，同时优化了用户的体验。</span>

#### 核心代码
1. 解析prediction_buffer.csv中的内容
![alt text](/final_report/asset/parse.png)

根据预测的条件，我们将prediction_buffer.csv中的条目解析成4个部分。type分成apps和urls两类，分别表示应用和网页。weekday即是启动的星期，time是启用的具体的时间，target对于应用来说是启用的路径，对于网页来说是相应的网址。

2. 预测结果调用前判断
![alt text](/final_report/asset/call.png)
如果星期和时间都对应相等，则会启用相应的软件或者网址。

3. 启动程序/网页
![alt text](/final_report/asset/launch.png)

根据网页或者程序类型的不同，启动网页或者程序。
4. 主循环
![alt text](/final_report/asset/circle.png)

预测程序启用即进入主循环。首先从buffer中不断读取entries；然后解析该entry，提取出对应的时间、路径的网址。如果判断需要启动该程序，则让用户进行选择是否需要启动。如果用户点击yes，则启动该程序，同时把该条目加入updated_entries；如果用户点击no，则不把这一条目加入updated entries。如果还没有到启用时间，则无论如何将这一条目加入到updated entries。这样即实现了模拟删除的过程。


## 实验结果



## 总结

### 项目成果回顾

### 未来工作展望

## References

1. Ravenscraft, Eric (2012-10-29). "Google Search Updated, Brings New Google Now Cards And Voice Actions - Yes, You Can Set Calendar Events". Android Police. Retrieved 2012-10-31. https://www.androidpolice.com/2012/10/29/google-search-updated-brings-new-google-now-cards-and-voice-actions-yes-you-can-set-calendar-events/
2. Gartenberg, Chaim (June 5, 2017). "Siri on iOS 11 gets improved speech and can suggest actions based on how you use it". The Verge. Vox Media. Retrieved June 10, 2017. https://www.theverge.com/2017/6/5/15732136/apple-siri-update-announced-new-features-wwdc-2017
3. 