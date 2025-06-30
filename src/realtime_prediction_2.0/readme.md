# 实时用户行为预测和应用优化系统（MEMO）

## 系统概述

本系统是一个智能的用户行为预测系统，通过监控用户在Windows上的应用使用模式，利用部署在Linux云服务器上的大语言模型进行预测，并提前预加载用户可能要使用的应用程序，从而提升用户体验。

2025.6.29 更新用户图形界面( `gui.py` )，极大简化操作流程

## 环境要求

### Windows端
- Python 3.8+
- 必需库：`psutil`, `pywin32`, `requests`, `threading`
- 支持SSH客户端（Windows 10/11自带）

### Linux云服务器
- Python 3.8+
- PyTorch + Transformers
- FastAPI + Uvicorn
- 微调后的LLM模型

## 使用说明

在 `\MEMO\src\realtime_prediction_2.0\windows` 目录下执行

```python 
  python gui.py
```
看到图形化界面，输入SSH连接命令及密码即可

#### 系统运行状态

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

### 目前支持的应用

- Code.exe - Visual Studio Code
- chrome.exe - Google Chrome
- msedge.exe - Microsoft Edge
- explorer.exe - 文件资源管理器
- notepad.exe - 记事本
- calc.exe - 计算器
- QQ.exe - QQ
- WeChat.exe - 微信
- SnippingTool.exe - 截图工具

## 故障排除

### 常见问题

#### Q1: SSH连接失败

```r
ssh: connect to host js2.blockelite.cn port 17012: Connection refused
```

- 检查网络连接

- 确认端口号是否正确（17012）
- 检查云服务器是否运行

#### Q2: SSH隧道建立失败

```r
bind [127.0.0.1]:8000: Address already in use
```

本地8000端口被占用，尝试关闭其他占用8000端口的程序：

```r
netstat -ano | findstr :8000
taskkill /PID <PID号> /F
```


#### Q3: API连接失败

```r
❌ 连接失败: 连接被拒绝
```

- 确认SSH隧道已建立

- 确认云服务器API服务正在运行
- 测试本地连接：curl http://localhost:8000/health

#### Q4: 预测解析失败

```r

❌ 无法解析云服务器预测结果
```

- LLM返回格式不标准，这是正常的，系统会尝试智能提取应用信息

- 可以降低 confidence_threshold 阈值

#### Q5: 应用预加载失败

```python
❌ 不支持的应用: xxx.exe
```

- 检查应用是否在支持列表中
- 确认应用路径在 ApplicationManager 中正确配置

### 调试模式

启用详细日志：

```r
logging.basicConfig(level=logging.DEBUG)
```

查看日志文件：

- 性能调优
- 系统参数调整

提高预测频率：

```r
"prediction_cooldown": 15  // 降低到15秒
```

提高预加载门槛：

```r
"confidence_threshold": 0.8  // 提高到0.8
```

增加监控范围：

```r
"queue_size": 15,
"prediction_window": 8
```

网络优化
使用更稳定的SSH连接：

```r
ssh -L 8000:localhost:8000 -o ServerAliveInterval=60 -o ServerAliveCountMax=3 root@js2.blockelite.cn -p 17012
```

### 系统监控

#### 关键指标

- 预测成功率: 成功解析的预测比例
- 应用命中率: 预加载应用被实际使用的比例
- 响应时间: LLM预测响应时间
- 资源使用: CPU和内存占用

#### 日志分析

```r

# 统计预测成功率

grep "✅ 解析成功" end_to_end_system.log | wc -l

# 统计预加载次数  

grep "🚀 已预加载应用" end_to_end_system.log | wc -l

# 查看最近的错误

grep "ERROR" end_to_end_system.log | tail -10
```

## 开发指南

### 添加新应用支持

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

### 自定义预测逻辑

修改 _predict_via_cloud_api 中的指令：

```r
instruction = """
自定义的预测指令...
"""
```

## 安全注意事项

SSH密钥认证（推荐）：

```r
ssh-keygen -t rsa -b 4096
ssh-copy-id root@js2.blockelite.cn -p 17012
```

限制SSH隧道绑定：

```r

ssh -L 127.0.0.1:8000:localhost:8000 root@js2.blockelite.cn -p 17012
```

防火墙配置：

1. 仅允许必要的端口访问
2. 配置云服务器安全组

版本信息:

1. 当前版本: v1.0.0
2. Python版本: 3.8+
3. 最后更新: 2025-06-28