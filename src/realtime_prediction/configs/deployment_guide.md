# 部署指南 - js1.blockelite.cn 服务器

## 🎯 您的环境配置

- **服务器**: js1.blockelite.cn:18324
- **SSH密钥**: Uroof9zu
- **模型路径**: `/home/vipuser/llm/LLM-Research`
- **LoRA路径**: `/home/vipuser/llm/output/exp16_lr0.0003_bs2_r32_a128_ep4_d0.05/checkpoint-356`

## 🚀 部署步骤

### 1. 上传代码到Linux服务器

```bash
# 在Windows上，将项目打包
tar -czf realtime_prediction.tar.gz src/realtime_prediction/

# 使用scp上传到服务器
scp -P 18324 -i ~/.ssh/Uroof9zu realtime_prediction.tar.gz root@js1.blockelite.cn:/home/vipuser/
```

### 2. 在Linux服务器上解压和配置

```bash
# SSH连接到服务器
ssh root@js1.blockelite.cn -p 18324 -i ~/.ssh/Uroof9zu

# 切换到工作目录
cd /home/vipuser/

# 解压代码
tar -xzf realtime_prediction.tar.gz

# 进入项目目录
cd src/realtime_prediction/

# 安装Python依赖
pip install aiohttp aiohttp-cors transformers torch peft
```

### 3. 验证模型路径

```bash
# 检查模型文件是否存在
ls -la /home/vipuser/llm/LLM-Research/
ls -la /home/vipuser/llm/output/exp16_lr0.0003_bs2_r32_a128_ep4_d0.05/checkpoint-356/

# 如果路径不存在，需要调整config中的路径
```

### 4. 配置防火墙

```bash
# 开放8888端口（如果需要）
iptables -A INPUT -p tcp --dport 8888 -j ACCEPT

# 或使用ufw（Ubuntu/Debian）
ufw allow 8888

# 或使用firewalld（CentOS/RHEL）
firewall-cmd --zone=public --add-port=8888/tcp --permanent
firewall-cmd --reload
```

### 5. 启动服务器

```bash
# 使用配置文件启动
python linux_server.py -c configs/server_config.json

# 或直接指定参数
python linux_server.py \
    --host 0.0.0.0 \
    --port 8888 \
    --model /home/vipuser/llm/LLM-Research \
    --lora /home/vipuser/llm/output/exp16_lr0.0003_bs2_r32_a128_ep4_d0.05/checkpoint-356

# 后台运行（推荐生产环境）
nohup python linux_server.py -c configs/server_config.json > server.log 2>&1 &
```

### 6. 在Windows客户端测试连接

```bash
# 在Windows上测试连接
python windows_client.py -c configs/client_config.json

# 或直接指定服务器
python windows_client.py --server js1.blockelite.cn:8888 --test
```

## 🔧 配置文件说明

### server_config.json
- `host: "0.0.0.0"` - 监听所有网络接口
- `port: 8888` - 服务端口
- `model_path` - 您的Llama模型绝对路径
- `lora_path` - 您的LoRA微调权重绝对路径

### client_config.json
- `server_host: "js1.blockelite.cn"` - 您的服务器域名
- `server_port: 8888` - 服务器端口
- `heartbeat_interval: 30` - 心跳间隔（秒）
- `prediction_interval: 60` - 预测请求间隔（秒）

## 🔍 测试连接

### 健康检查
```bash
# 在服务器上测试
curl http://localhost:8888/health

# 在Windows上测试（或任何有网络访问的机器）
curl http://js1.blockelite.cn:8888/health
```

### 预期响应
```json
{
  "status": "healthy",
  "server": "activity-prediction-server",
  "timestamp": "2025-01-01T10:30:00.000000",
  "llm_loaded": true
}
```

## ⚠️ 故障排除

### 1. 连接被拒绝
- 检查防火墙设置
- 确认服务器正在运行
- 验证端口8888是否开放

### 2. 模型加载失败
```bash
# 检查模型文件权限
ls -la /home/vipuser/llm/LLM-Research/
ls -la /home/vipuser/llm/output/exp16_lr0.0003_bs2_r32_a128_ep4_d0.05/checkpoint-356/

# 检查Python路径和依赖
python -c "import transformers, torch, peft; print('Dependencies OK')"
```

### 3. GPU内存不足
在server_config.json中设置：
```json
{
  "enable_gpu": false
}
```

### 4. 网络延迟高
调整客户端配置：
```json
{
  "heartbeat_interval": 60,
  "batch_send_interval": 20,
  "retry_attempts": 5,
  "retry_delay": 10
}
```

## 🔐 安全考虑

### 1. SSH隧道（推荐）
如果不想开放8888端口，可以使用SSH隧道：

```bash
# 在Windows上创建SSH隧道
ssh -N -L 8888:localhost:8888 root@js1.blockelite.cn -p 18324 -i ~/.ssh/Uroof9zu

# 然后客户端连接到localhost:8888
python windows_client.py --server localhost:8888
```

### 2. 防火墙限制
只允许特定IP访问：
```bash
iptables -A INPUT -p tcp --dport 8888 -s YOUR_WINDOWS_IP -j ACCEPT
iptables -A INPUT -p tcp --dport 8888 -j DROP
```

## 📊 监控和维护

### 查看服务器状态
```bash
# 查看服务器统计
curl http://js1.blockelite.cn:8888/status

# 查看连接的客户端
curl http://js1.blockelite.cn:8888/clients

# 查看日志
tail -f server.log
```

### 自动启动服务
创建systemd服务：

```bash
# 创建服务文件
sudo nano /etc/systemd/system/activity-prediction.service
```

服务文件内容：
```ini
[Unit]
Description=Activity Prediction Server
After=network.target

[Service]
Type=simple
User=vipuser
WorkingDirectory=/home/vipuser/src/realtime_prediction
ExecStart=/usr/bin/python linux_server.py -c configs/server_config.json
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：
```bash
sudo systemctl enable activity-prediction
sudo systemctl start activity-prediction
sudo systemctl status activity-prediction
```

## 📞 需要帮助？

如果遇到问题，请检查：
1. 服务器日志：`tail -f server.log`
2. 网络连通性：`ping js1.blockelite.cn`
3. 端口开放：`netstat -tuln | grep 8888`
4. 模型文件完整性 