#!/bin/bash

# 活动预测系统服务器端部署脚本
# 服务器: js1.blockelite.cn:18324

echo "🚀 开始部署活动预测系统..."

# 检查Python和pip
echo "📋 检查Python环境..."
python3 --version || { echo "❌ Python3未安装"; exit 1; }
pip3 --version || { echo "❌ pip3未安装"; exit 1; }

# 安装依赖
echo "📦 安装Python依赖包..."
pip3 install aiohttp aiohttp-cors transformers torch peft accelerate

# 验证模型路径
echo "📁 验证模型文件路径..."
MODEL_PATH="/home/vipuser/llm/LLM-Research"
LORA_PATH="/home/vipuser/llm/output/exp16_lr0.0003_bs2_r32_a128_ep4_d0.05/checkpoint-356"

if [ ! -d "$MODEL_PATH" ]; then
    echo "❌ 模型路径不存在: $MODEL_PATH"
    echo "请检查模型是否已下载到正确位置"
    exit 1
fi

if [ ! -d "$LORA_PATH" ]; then
    echo "❌ LoRA权重路径不存在: $LORA_PATH"
    echo "请检查LoRA权重是否已训练并保存到正确位置"
    exit 1
fi

echo "✅ 模型文件路径验证通过"

# 检查防火墙
echo "🔥 检查防火墙配置..."
if command -v ufw &> /dev/null; then
    echo "检测到ufw防火墙"
    ufw status | grep 8888 || {
        echo "⚠️ 端口8888未开放，正在配置..."
        sudo ufw allow 8888
    }
elif command -v firewall-cmd &> /dev/null; then
    echo "检测到firewalld防火墙"
    firewall-cmd --list-ports | grep 8888 || {
        echo "⚠️ 端口8888未开放，正在配置..."
        sudo firewall-cmd --zone=public --add-port=8888/tcp --permanent
        sudo firewall-cmd --reload
    }
else
    echo "⚠️ 请手动确认端口8888已开放"
fi

# 测试基本功能
echo "🧪 测试Python依赖..."
python3 -c "
import aiohttp
import transformers
import torch
import peft
print('✅ 所有依赖包安装成功')
print(f'✅ PyTorch版本: {torch.__version__}')
print(f'✅ Transformers版本: {transformers.__version__}')
print(f'✅ PEFT版本: {peft.__version__}')
"

# 创建启动脚本
echo "📝 创建服务启动脚本..."
cat > start_server.sh << 'EOF'
#!/bin/bash
# 活动预测服务器启动脚本

echo "🚀 启动活动预测服务器..."
echo "📍 服务器地址: http://0.0.0.0:8888"
echo "📍 外网访问: http://js1.blockelite.cn:8888"

# 后台运行
nohup python3 linux_server.py -c configs/server_config.json > server.log 2>&1 &

SERVER_PID=$!
echo "✅ 服务器已启动，PID: $SERVER_PID"
echo "📄 日志文件: server.log"

# 等待几秒让服务器启动
sleep 3

# 测试健康检查
echo "🔍 测试服务器健康状态..."
curl -s http://localhost:8888/health && echo "✅ 服务器运行正常" || echo "❌ 服务器启动失败"

echo "📊 查看实时日志："
echo "  tail -f server.log"
echo ""
echo "🛑 停止服务器："
echo "  kill $SERVER_PID"
echo "  或者: pkill -f linux_server.py"
EOF

chmod +x start_server.sh

# 创建停止脚本
echo "📝 创建服务停止脚本..."
cat > stop_server.sh << 'EOF'
#!/bin/bash
# 停止活动预测服务器

echo "🛑 停止活动预测服务器..."
pkill -f linux_server.py
echo "✅ 服务器已停止"
EOF

chmod +x stop_server.sh

# 创建状态检查脚本
echo "📝 创建状态检查脚本..."
cat > check_status.sh << 'EOF'
#!/bin/bash
# 检查服务器状态

echo "🔍 检查活动预测服务器状态..."

# 检查进程
if pgrep -f linux_server.py > /dev/null; then
    echo "✅ 服务器进程运行中"
    echo "📊 进程信息:"
    ps aux | grep linux_server.py | grep -v grep
else
    echo "❌ 服务器未运行"
fi

# 检查端口
if netstat -tuln | grep :8888 > /dev/null 2>&1; then
    echo "✅ 端口8888已监听"
else
    echo "❌ 端口8888未监听"
fi

# 健康检查
echo "🏥 健康检查:"
curl -s http://localhost:8888/health | python3 -m json.tool 2>/dev/null || echo "❌ 健康检查失败"

echo ""
echo "📄 查看日志: tail -f server.log"
echo "🚀 启动服务: ./start_server.sh"
echo "🛑 停止服务: ./stop_server.sh"
EOF

chmod +x check_status.sh

echo ""
echo "🎉 部署完成！"
echo ""
echo "📋 可用命令:"
echo "  🚀 启动服务器: ./start_server.sh"
echo "  🛑 停止服务器: ./stop_server.sh"
echo "  🔍 检查状态:   ./check_status.sh"
echo ""
echo "📍 服务器地址:"
echo "  本地访问: http://localhost:8888"
echo "  外网访问: http://js1.blockelite.cn:8888"
echo ""
echo "🔗 API端点:"
echo "  健康检查: /health"
echo "  客户端状态: /clients"
echo "  服务器统计: /status"
echo ""
echo "📄 查看日志: tail -f server.log"
echo "🧪 测试连接: curl http://localhost:8888/health" 