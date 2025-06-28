# 🚀 实时活动预测系统

一个基于LLM的跨平台实时用户活动预测系统，支持Windows客户端数据收集和Linux服务器AI预测。

## 📋 系统架构

```
Windows客户端 (活动监控) ←→ HTTP/JSON ←→ Linux服务器 (LLM预测)
```

- **Windows客户端**: 监控用户活动，发送数据到服务器
- **Linux服务器**: 接收数据，使用微调的Llama3模型进行预测

## ⚡ 快速开始

### 🖥️ Linux服务器部署

1. **上传代码到服务器**：
   ```bash
   scp -P 18324 -r src/realtime_prediction/ root@js1.blockelite.cn:/home/vipuser/
   ```

2. **SSH连接并部署**：
   ```bash
   ssh root@js1.blockelite.cn -p 18324
   cd /home/vipuser/realtime_prediction/
   chmod +x deploy.sh
   ./deploy.sh
   ```

3. **启动服务器**：
   ```bash
   ./start_server.sh
   ```

### 💻 Windows客户端使用

1. **直接运行**：双击 `start_client.bat`

2. **或命令行运行**：
   ```cmd
   python windows_client.py -c configs/client_config.json
   ```

## 📁 项目结构

```
src/realtime_prediction/
├── 🐧 Linux服务器端
│   ├── linux_server.py           # HTTP API服务器
│   ├── client_server_architecture.py  # 架构基础
│   └── deploy.sh                  # 自动部署脚本
│
├── 🪟 Windows客户端
│   ├── windows_client.py          # 活动监控客户端
│   └── start_client.bat           # 一键启动脚本
│
├── ⚙️ 配置文件
│   ├── configs/
│   │   ├── server_config.json     # 服务器配置
│   │   └── client_config.json     # 客户端配置
│   └── requirements.txt           # Python依赖
│
├── 📚 文档
│   ├── README.md                  # 本文件
│   └── configs/deployment_guide.md  # 详细部署指南
│
└── 🧪 测试工具
    ├── demo_client_server.py      # 演示脚本
    └── test_workflow.py           # 本地测试
```

## 🔧 配置说明

### 服务器配置 (server_config.json)
```json
{
  "host": "0.0.0.0",
  "port": 8888,
  "model_path": "/home/vipuser/llm/LLM-Research",
  "lora_path": "/home/vipuser/llm/output/exp16_lr0.0003_bs2_r32_a128_ep4_d0.05/checkpoint-356"
}
```

### 客户端配置 (client_config.json)
```json
{
  "server_host": "js1.blockelite.cn",
  "server_port": 8888,
  "client_id": "windows_client_001",
  "heartbeat_interval": 30,
  "prediction_interval": 60
}
```

## 🌐 API端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/clients` | GET | 查看连接的客户端 |
| `/status` | GET | 服务器统计信息 |
| `/send_activities` | POST | 发送活动数据 |
| `/request_prediction` | POST | 请求预测 |
| `/heartbeat` | POST | 客户端心跳 |

## 🎯 使用模式

### 1. 演示模式
使用预设数据演示系统功能：
```bash
python windows_client.py --demo --server js1.blockelite.cn:8888
```

### 2. 实时监控模式
监控真实用户活动：
```bash
python windows_client.py -c configs/client_config.json
```

### 3. 测试连接模式
验证服务器连接：
```bash
python windows_client.py --test --server js1.blockelite.cn:8888
```

## 📊 监控和维护

### 服务器状态检查
```bash
./check_status.sh          # 检查服务器状态
curl http://js1.blockelite.cn:8888/health  # 健康检查
tail -f server.log         # 查看实时日志
```

### 客户端状态
客户端会自动发送心跳包并显示连接状态。

## 🔍 故障排除

### 常见问题

1. **连接被拒绝**
   - 检查服务器是否运行：`./check_status.sh`
   - 检查防火墙设置：`ufw status`
   - 验证端口开放：`netstat -tuln | grep 8888`

2. **模型加载失败**
   - 验证模型路径：`ls -la /home/vipuser/llm/LLM-Research/`
   - 检查依赖安装：`pip list | grep transformers`

3. **客户端无法连接**
   - 测试网络连通性：`ping js1.blockelite.cn`
   - 检查配置文件路径
   - 验证Python依赖

### 重启服务
```bash
./stop_server.sh    # 停止服务
./start_server.sh   # 重新启动
```

## 🛠️ 开发和自定义

### 模型路径修改
编辑 `configs/server_config.json` 中的 `model_path` 和 `lora_path`。

### 监控频率调整
编辑 `configs/client_config.json` 中的时间间隔参数。

### 添加新的活动类型
在 `client_server_architecture.py` 中扩展 `ActivityData` 类。

## 📞 技术支持

如果遇到问题：

1. 查看日志文件：`server.log`
2. 检查服务器状态：`./check_status.sh`
3. 验证配置文件格式
4. 确认网络连接和防火墙设置

## 🏗️ 系统要求

### Linux服务器
- Python 3.8+
- 8GB+ RAM (用于LLM推理)
- NVIDIA GPU (可选，推荐)
- 网络端口 8888 开放

### Windows客户端  
- Windows 10+
- Python 3.8+
- 网络连接到服务器

## 📄 许可证

本项目用于学术研究和教育目的。
 