# 实时活动预测模块

本目录包含实时用户活动预测系统的核心组件，将活动监控、数据处理和LLM预测串联成完整的工作流。

## 目录结构

```
src/realtime_prediction/
├── README.md                 # 本文档
├── realtime_pipeline.py      # 实时预测管道核心组件
├── integrated_monitor.py     # 集成活动监控器
├── realtime_test.py          # 实时预测测试工具
└── unified_workflow.py       # 统一工作流协调器
```

## 核心组件说明

### 1. realtime_pipeline.py
**实时活动预测管道** - 系统的核心组件

- **ActivityQueue**: 管理实时活动数据队列
  - 维护固定大小的活动历史
  - 线程安全的实时数据传递
  - 格式化活动数据为LLM可理解的文本

- **RealTimeLLMPredictor**: LLM活动预测器
  - 加载微调后的Llama模型和LoRA权重
  - 根据活动序列预测下一个可能的用户活动

- **RealTimeActivityPipeline**: 预测管道协调器
  - 整合队列管理和LLM预测
  - 支持自动化的定时预测循环

### 2. integrated_monitor.py
**集成活动监控器** - 连接monitor和实时预测

- 继承原有的`ActivityMonitor`功能
- 同时将活动数据保存到文件和推送到实时队列
- 支持启用/禁用实时预测功能

### 3. realtime_test.py
**实时预测测试工具** - 独立的预测接口

- 提供演示模式（使用示例数据）
- 提供交互模式（手动添加活动）
- 支持手动预测和自动预测循环

### 4. unified_workflow.py
**统一工作流协调器** - 完整的端到端解决方案

- 整合监控、分析和实时预测
- 支持多种运行模式（仅监控、仅预测、完整集成）
- 提供命令行接口和配置文件支持
- 实时状态监控和报告

## 使用方法

### 快速开始

#### 1. 完整集成模式（推荐）
```bash
cd src/realtime_prediction
python unified_workflow.py --test-mode
```

#### 2. 仅实时预测测试
```bash
cd src/realtime_prediction
python realtime_test.py
```

#### 3. 集成监控器（监控+预测）
```bash
cd src/realtime_prediction
python integrated_monitor.py
```

### 高级配置

#### 命令行参数
```bash
python unified_workflow.py \
    --model-path ./LLM-Research/Meta-Llama-3___1-8B-Instruct \
    --lora-path ./output/llama3_1_instruct_lora/checkpoint-138 \
    --prediction-interval 30 \
    --data-dir activity_data \
    --test-mode
```

#### 配置文件
创建 `config.json`：
```json
{
    "model_path": "./LLM-Research/Meta-Llama-3___1-8B-Instruct",
    "lora_path": "./output/llama3_1_instruct_lora/checkpoint-138",
    "data_dir": "activity_data",
    "prediction_interval": 30,
    "enable_monitoring": true,
    "enable_prediction": true
}
```

然后运行：
```bash
python unified_workflow.py --config config.json
```

### 运行模式

1. **完整集成模式**: 同时进行活动监控和实时预测
   ```bash
   python unified_workflow.py
   ```

2. **仅监控模式**: 只收集活动数据，不进行预测
   ```bash
   python unified_workflow.py --monitor-only
   ```

3. **仅预测模式**: 只进行实时预测，需要手动添加数据
   ```bash
   python unified_workflow.py --predict-only
   ```

## 系统架构

```
用户活动 → ActivityMonitor → ActivityQueue → LLMPredictor → 预测结果
     ↓              ↓              ↓              ↓
  文件保存    实时队列管理    格式化处理    模型推理
```

### 数据流

1. **活动收集**: `ActivityMonitor` 监控用户的浏览器历史、窗口切换、文件操作等
2. **实时队列**: `ActivityQueue` 维护最近的活动历史，支持线程安全的读写
3. **数据格式化**: 将活动数据转换为LLM可理解的时间序列文本
4. **预测生成**: `RealTimeLLMPredictor` 使用微调的Llama模型进行下一步活动预测
5. **结果输出**: 预测结果实时显示，同时保存预测历史

### 队列管理

- **历史窗口**: 默认保存最近100个活动
- **预测窗口**: 使用最近20个活动进行预测
- **最小预测阈值**: 至少需要3个活动才能进行预测
- **线程安全**: 支持多线程并发访问

## 依赖要求

确保已安装以下依赖：

```bash
pip install transformers torch peft
pip install psutil pywin32  # Windows系统监控
pip install pandas numpy    # 数据处理
```

## 性能优化

- **预测间隔**: 默认30秒，可根据需要调整
- **队列大小**: 可配置历史窗口和预测窗口大小
- **频率限制**: 内置活动记录频率限制，避免数据过载
- **模型推理**: 使用半精度浮点数(bfloat16)优化内存使用

## 故障排除

### 常见问题

1. **模型加载失败**
   - 检查模型路径是否正确
   - 确保有足够的显存/内存
   - 验证LoRA权重路径

2. **活动监控异常**
   - 检查Windows权限设置
   - 确保浏览器历史文件可访问
   - 验证Win32API权限

3. **预测结果异常**
   - 检查活动数据格式
   - 验证模型是否正确加载
   - 确认预测提示词格式

### 日志和调试

系统提供详细的控制台输出，包括：
- 组件初始化状态
- 活动数据收集情况
- 预测循环状态
- 错误和异常信息

## 扩展开发

### 添加新的活动类型

在 `ActivityQueue._format_single_activity()` 中添加新的活动类型处理：

```python
elif activity_type == 'new_activity_type':
    # 处理新活动类型的格式化逻辑
    return formatted_string
```

### 自定义预测逻辑

继承 `RealTimeLLMPredictor` 类并重写 `predict_next_activity()` 方法。

### 集成其他模型

修改 `RealTimeLLMPredictor._load_model()` 方法以支持其他LLM模型。

## 许可和贡献

本模块是MEMO项目的一部分，遵循项目的开源许可协议。欢迎提交Issue和Pull Request。 