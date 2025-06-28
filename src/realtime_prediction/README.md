# 客户端-服务器架构实时活动预测系统

## 🎯 解决方案概述

解决Windows监控器无法在Linux云主机上运行的问题，通过**客户端-服务器架构**实现：
- **Windows客户端**: 收集活动数据，发送到云服务器
- **Linux服务器**: 接收数据，运行LLM预测，返回结果

## 📋 架构图

```
Windows客户端                    网络传输                Linux服务器
┌─────────────────┐             HTTP/JSON            ┌─────────────────┐
│  ActivityMonitor │ ────────────────────────────────▶ │  HTTP Server    │
│  (收集活动)       │                                  │  (接收数据)      │
├─────────────────┤                                  ├─────────────────┤
│  ActivityBuffer │                                  │  ClientManager  │
│  (数据缓冲)       │                                  │  (客户端管理)    │
├─────────────────┤             预测结果              ├─────────────────┤
│  HTTPClient     │ ◀──────────────────────────────── │  LLMPredictor   │
│  (网络通信)       │                                  │  (模型预测)      │
└─────────────────┘                                  └─────────────────┘
```

## 🔧 核心组件

### Windows客户端 (`windows_client.py`)
- **ActivityMonitor集成**: 收集用户活动数据
- **ActivityBuffer**: 缓冲和管理活动数据
- **HTTPClient**: 与服务器通信
- **自动重连**: 网络中断自动恢复
- **批量发送**: 优化网络传输效率

### Linux服务器 (`linux_server.py`)
- **HTTP API服务**: 接收客户端数据和请求
- **ClientManager**: 管理多个客户端连接
- **LLMPredictor**: 运行Llama3+LoRA模型预测
- **活动历史管理**: 维护客户端活动历史
- **异步处理**: 高性能异步服务器

### 通信协议 (`client_server_architecture.py`)
- **标准化数据结构**: ActivityData, PredictionRequest, PredictionResponse
- **配置管理**: ClientConfig, ServerConfig
- **网络协议抽象**: NetworkProtocol基类

## 🚀 快速开始

### 1. 环境准备

**Linux服务器依赖**:
```bash
pip install aiohttp aiohttp-cors transformers torch peft
```

**Windows客户端依赖**:
```bash
pip install aiohttp psutil pywin32
```

### 2. 配置文件

**服务器配置** (`configs/server_config.json`):
```json
{
  "host": "0.0.0.0",
  "port": 8888,
  "model_path": "./models/llama3-instruct",
  "lora_path": "./models/lora-checkpoint-138",
  "enable_gpu": true
}
```

**客户端配置** (`configs/client_config.json`):
```json
{
  "server_host": "your-linux-server.com",
  "server_port": 8888,
  "heartbeat_interval": 30,
  "batch_send_interval": 10,
  "prediction_interval": 60
}
```

### 3. 启动系统

**启动Linux服务器**:
```bash
# 使用配置文件
python linux_server.py -c configs/server_config.json

# 或直接指定参数
python linux_server.py --host 0.0.0.0 --port 8888 --model ./models/llama3

# 测试模式（不需要真实模型）
python linux_server.py --model mock --lora mock --no-gpu
```

**启动Windows客户端**:
```bash
# 使用配置文件
python windows_client.py -c configs/client_config.json

# 或直接指定服务器
python windows_client.py --server your-server.com:8888

# 测试模式
python windows_client.py --test --server localhost:8888
```

## 🧪 演示和测试

### 本地演示
```bash
# 运行完整演示（同时启动服务器和客户端）
python demo_client_server.py --demo

# 查看架构说明
python demo_client_server.py --info
```

### API测试
```bash
# 健康检查
curl http://localhost:8888/health

# 查看服务器状态
curl http://localhost:8888/status

# 查看连接的客户端
curl http://localhost:8888/clients
```

## 📡 API接口

### 服务器端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/status` | GET | 服务器状态和统计 |
| `/clients` | GET | 活跃客户端列表 |
| `/heartbeat` | POST | 客户端心跳 |
| `/activities/batch` | POST | 批量活动数据 |
| `/predict` | POST | 预测请求 |

### 数据格式

**活动数据**:
```json
{
  "activity_type": "browser_history",
  "timestamp": "2025-01-01T10:30:00",
  "data": {
    "domain": "github.com",
    "title": "MEMO Project"
  },
  "client_id": "windows_client_001"
}
```

**预测请求**:
```json
{
  "activities": [...],
  "client_id": "windows_client_001",
  "request_id": "uuid-string",
  "timestamp": "2025-01-01T10:30:00"
}
```

**预测响应**:
```json
{
  "request_id": "uuid-string",
  "prediction": "2025-01-01 10:31:00 - 访问网站 github.com 的页面 'README.md'",
  "confidence": 0.85,
  "timestamp": "2025-01-01T10:30:05",
  "processing_time": 1.23
}
```

## 🔒 部署建议

### 生产环境配置

**Linux服务器**:
```bash
# 使用systemd服务
sudo systemctl enable activity-prediction-server
sudo systemctl start activity-prediction-server

# 使用nginx反向代理
location /api/ {
    proxy_pass http://localhost:8888/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

**Windows客户端**:
```bash
# 使用Windows服务或计划任务自动启动
schtasks /create /tn "ActivityClient" /tr "python windows_client.py" /sc onstart
```

### 安全考虑

1. **HTTPS通信**: 在生产环境使用SSL/TLS
2. **API认证**: 添加客户端认证机制
3. **防火墙**: 限制服务器端口访问
4. **数据加密**: 敏感活动数据加密传输

## 📊 监控和调试

### 日志配置
```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('activity_system.log'),
        logging.StreamHandler()
    ]
)
```

### 性能监控
- 客户端: 活动收集速率、发送成功率、网络延迟
- 服务器: 预测处理时间、并发客户端数、资源使用率

### 故障排除

**常见问题**:
1. **连接失败**: 检查网络和防火墙设置
2. **模型加载失败**: 确认模型路径和权限
3. **预测速度慢**: 检查GPU配置和模型大小
4. **内存不足**: 调整batch_size和cache_size

## 🔧 扩展开发

### 添加新的活动类型
```python
# 在client_server_architecture.py中扩展格式化函数
def format_activities_for_llm(activities):
    # 添加新的活动类型处理逻辑
    elif activity_type == 'new_activity_type':
        # 自定义格式化逻辑
        pass
```

### 自定义网络协议
```python
# 继承NetworkProtocol实现自定义通信
class CustomProtocol(NetworkProtocol):
    async def send_activity(self, activity):
        # 自定义发送逻辑
        pass
```

### 模型集成
```python
# 在linux_server.py中自定义LLMPredictor
class CustomLLMPredictor(LLMPredictor):
    def _load_model_sync(self):
        # 加载自定义模型
        pass
```

## 📈 性能优化

### 客户端优化
- **数据压缩**: 使用gzip压缩HTTP请求
- **批量发送**: 合并多个活动减少网络请求
- **本地缓存**: 缓存预测结果避免重复请求

### 服务器优化
- **模型缓存**: 缓存加载的模型避免重复初始化
- **连接池**: 复用数据库和网络连接
- **异步处理**: 使用队列处理预测请求

## 📝 更新日志

### v1.0.0 (2025-01-01)
- ✅ 完整的客户端-服务器架构
- ✅ Windows活动监控集成
- ✅ Linux LLM预测服务
- ✅ HTTP REST API通信
- ✅ 配置文件管理
- ✅ 演示和测试脚本

## 🤝 贡献指南

1. Fork项目
2. 创建功能分支: `git checkout -b feature/new-feature`
3. 提交更改: `git commit -am 'Add new feature'`
4. 推送分支: `git push origin feature/new-feature`
5. 创建Pull Request

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🙋‍♂️ 支持

如有问题或建议，请：
1. 查看[故障排除](#故障排除)部分
2. 创建[GitHub Issue](https://github.com/your-repo/issues)
3. 联系开发团队

---

**🎉 现在您可以在Windows上收集活动数据，在Linux云服务器上运行LLM预测了！** 