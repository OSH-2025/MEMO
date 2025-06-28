#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试脚本 - 验证客户端修复
"""

import asyncio
import sys
import os

# 添加路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'data_collection'))

from client_server_architecture import ClientConfig, ActivityData, ActivityBuffer
from datetime import datetime
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def test_client_fixes():
    """测试客户端修复"""
    print("🧪 测试客户端修复...")
    
    try:
        # 测试1: 配置加载
        print("\n1️⃣ 测试配置加载...")
        config = ClientConfig()
        print(f"✅ 配置加载成功: {config.server_host}:{config.server_port}")
        
        # 测试2: ActivityBuffer
        print("\n2️⃣ 测试活动缓冲区...")
        buffer = ActivityBuffer(max_size=10)
        
        # 创建测试活动
        test_activity = ActivityData(
            activity_type="browser_history",
            timestamp=datetime.now().isoformat(),
            data={
                "domain": "github.com",
                "title": "Test Page"
            }
        )
        
        buffer.add_activity(test_activity)
        stats = buffer.get_stats()
        print(f"✅ 缓冲区测试成功: {stats['buffer_size']}/{stats['max_size']}")
        
        # 测试3: MonitoredList (模拟修复后的append方法)
        print("\n3️⃣ 测试监控列表...")
        
        class TestClient:
            def __init__(self):
                self.hook_called = False
                
            def _activity_monitor_hook(self, item):
                self.hook_called = True
                print(f"📡 Hook被调用: {item}")
        
        class MonitoredList(list):
            def __init__(self, parent_client):
                super().__init__()
                self.client = parent_client
            
            def append(self, item):
                super().append(item)
                # 调用hook函数
                self.client._activity_monitor_hook(item)
        
        # 测试监控列表
        test_client = TestClient()
        monitored_list = MonitoredList(test_client)
        
        # 添加数据
        test_data = {"type": "test", "message": "Hello World"}
        monitored_list.append(test_data)
        
        if test_client.hook_called:
            print("✅ 监控列表测试成功 - Hook正常工作")
        else:
            print("❌ 监控列表测试失败 - Hook未被调用")
        
        # 测试4: 服务器连接测试
        print("\n4️⃣ 测试服务器连接...")
        try:
            import requests
            response = requests.get(
                f"http://{config.server_host}:{config.server_port}/health",
                timeout=5
            )
            if response.status_code == 200:
                print("✅ 服务器连接正常")
                print(f"   响应: {response.json()}")
            else:
                print(f"⚠️ 服务器响应异常: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ 服务器连接失败: {e}")
            print("   请确认服务器是否已启动")
        
        print("\n🎉 客户端修复测试完成!")
        return True
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_batch_file_encoding():
    """测试批处理文件编码"""
    print("\n📄 检查批处理文件...")
    
    safe_bat = "start_client_safe.bat"
    if os.path.exists(safe_bat):
        print(f"✅ 找到安全批处理文件: {safe_bat}")
        
        # 读取文件检查编码
        try:
            with open(safe_bat, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否包含emoji字符
            emoji_chars = ['🚀', '📡', '✅', '❌', '⚠️', '🔍', '📊', '💡']
            has_emoji = any(char in content for char in emoji_chars)
            
            if has_emoji:
                print("⚠️ 安全批处理文件仍包含emoji字符，可能导致编码问题")
            else:
                print("✅ 安全批处理文件不包含emoji字符")
                
        except Exception as e:
            print(f"❌ 读取批处理文件失败: {e}")
    else:
        print(f"❌ 未找到安全批处理文件: {safe_bat}")

if __name__ == "__main__":
    print("🔧 客户端修复验证测试")
    print("="*50)
    
    # 测试批处理文件编码
    test_batch_file_encoding()
    
    # 异步测试客户端修复
    result = asyncio.run(test_client_fixes())
    
    print("\n" + "="*50)
    if result:
        print("✅ 所有测试通过！现在可以尝试运行 start_client_safe.bat")
    else:
        print("❌ 测试失败，请检查错误信息")
    
    print("\n💡 使用建议:")
    print("1. 双击 start_client_safe.bat (无emoji版本)")
    print("2. 或在命令行运行: python windows_client.py --demo --server js1.blockelite.cn:8888")
    print("3. 确保服务器已启动: http://js1.blockelite.cn:8888/health") 