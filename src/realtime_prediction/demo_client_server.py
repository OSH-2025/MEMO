"""
客户端-服务器演示脚本
用于测试Windows客户端与Linux服务器的通信
"""

import asyncio
import time
import json
from datetime import datetime
from typing import Dict, Any

# 导入我们的组件
from client_server_architecture import ActivityData, ClientConfig, ServerConfig
from windows_client import WindowsActivityClient
from linux_server import ActivityPredictionServer

async def demo_server():
    """演示服务器"""
    print("🖥️ 启动演示服务器...")
    
    # 创建服务器配置（使用模拟模型）
    config = ServerConfig()
    config.host = "localhost"
    config.port = 8888
    config.model_path = "mock"  # 使用模拟模型
    config.lora_path = "mock"
    config.enable_gpu = False
    
    # 创建服务器
    server = ActivityPredictionServer(config)
    
    # 启动服务器
    runner, cleanup_task = await server.start_server()
    
    return server, runner, cleanup_task

async def demo_client():
    """演示客户端"""
    print("💻 启动演示客户端...")
    
    # 等待服务器启动
    await asyncio.sleep(2)
    
    # 创建客户端配置
    config = ClientConfig()
    config.server_host = "localhost"
    config.server_port = 8888
    config.heartbeat_interval = 15  # 更频繁的心跳
    config.batch_send_interval = 5   # 更频繁的数据发送
    config.prediction_interval = 20  # 更频繁的预测
    
    # 创建客户端
    client = WindowsActivityClient()
    client.config = config
    
    # 添加一些测试数据
    test_activities = [
        {
            'type': 'browser_history',
            'domain': 'github.com',
            'title': 'MEMO Project Repository',
            'timestamp': datetime.now().isoformat()
        },
        {
            'type': 'window_focus',
            'process_name': 'Code.exe',
            'window_title': 'demo_client_server.py - VSCode',
            'timestamp': datetime.now().isoformat()
        },
        {
            'type': 'browser_history',
            'domain': 'stackoverflow.com',
            'title': 'Python asyncio tutorial',
            'timestamp': datetime.now().isoformat()
        },
        {
            'type': 'file_access',
            'path': '/home/user/project/demo.py',
            'timestamp': datetime.now().isoformat()
        }
    ]
    
    # 启动客户端
    started = await client.start()
    if not started:
        print("❌ 客户端启动失败")
        return None
    
    # 模拟添加活动数据
    print("📝 添加测试活动数据...")
    for activity_data in test_activities:
        client._activity_monitor_hook(activity_data)
        await asyncio.sleep(1)  # 间隔添加
    
    return client

async def demo_interaction():
    """演示客户端-服务器交互"""
    print("🚀 开始客户端-服务器演示")
    print("=" * 60)
    
    server = None
    client = None
    runner = None
    cleanup_task = None
    
    try:
        # 启动服务器
        server, runner, cleanup_task = await demo_server()
        
        # 启动客户端
        client = await demo_client()
        
        if not client:
            print("❌ 客户端启动失败")
            return
        
        print("\n🔄 系统运行中，观察客户端-服务器交互...")
        print("📊 监控数据流: 活动收集 → 批量发送 → 预测请求 → 预测结果")
        print("\n按 Enter 键查看实时状态，按 Ctrl+C 停止演示\n")
        
        # 运行演示循环
        start_time = time.time()
        status_count = 0
        
        while True:
            # 检查是否有用户输入
            try:
                # 等待一段时间或用户输入
                await asyncio.wait_for(asyncio.sleep(5), timeout=5)
                
                # 每隔一段时间显示状态
                status_count += 1
                if status_count % 6 == 0:  # 每30秒显示一次状态
                    print(f"\n⏰ 运行时间: {int(time.time() - start_time)} 秒")
                    
                    # 显示客户端状态
                    client_stats = client.buffer.get_stats()
                    print(f"📱 客户端: 收集 {client.stats['activities_collected']} 个活动, "
                          f"发送 {client.stats['activities_sent']} 个, "
                          f"预测 {client.stats['predictions_received']} 次")
                    
                    # 显示服务器状态
                    print(f"🖥️ 服务器: 处理 {server.stats['total_activities']} 个活动, "
                          f"完成 {server.stats['total_predictions']} 次预测, "
                          f"活跃客户端 {len(server.client_manager.clients)} 个")
                    
                    print("-" * 40)
                
            except asyncio.TimeoutError:
                pass
            except KeyboardInterrupt:
                break
    
    except KeyboardInterrupt:
        print("\n👋 用户中断演示")
    except Exception as e:
        print(f"❌ 演示出错: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理资源
        print("\n🧹 清理资源...")
        
        if client:
            try:
                await client.stop()
            except:
                pass
        
        if cleanup_task:
            cleanup_task.cancel()
        
        if runner:
            try:
                await runner.cleanup()
            except:
                pass
        
        print("✅ 演示结束")

def print_usage():
    """打印使用说明"""
    print("📖 客户端-服务器架构演示")
    print("=" * 60)
    print("🎯 目标: 解决Windows监控器无法在Linux上运行LLM的问题")
    print("\n📋 架构说明:")
    print("   Windows客户端 → 收集活动数据 → HTTP发送到Linux服务器")
    print("   Linux服务器  → 接收数据 → LLM预测 → 返回结果")
    print("\n🔧 组件:")
    print("   • WindowsActivityClient - Windows客户端")
    print("   • ActivityPredictionServer - Linux服务器")
    print("   • HTTP REST API - 通信协议")
    print("   • ActivityBuffer - 数据缓冲")
    print("   • LLMPredictor - 模型预测")
    print("\n🚀 启动步骤:")
    print("   1. 在Linux服务器上运行: python linux_server.py")
    print("   2. 在Windows客户端上运行: python windows_client.py")
    print("   3. 观察数据流和预测结果")
    print("\n📁 配置文件:")
    print("   • configs/server_config.json - 服务器配置")
    print("   • configs/client_config.json - 客户端配置")
    print("=" * 60)

async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="客户端-服务器演示")
    parser.add_argument("--demo", "-d", action="store_true", help="运行演示")
    parser.add_argument("--info", "-i", action="store_true", help="显示使用说明")
    
    args = parser.parse_args()
    
    if args.info:
        print_usage()
        return
    
    if args.demo:
        await demo_interaction()
        return
    
    # 默认显示使用说明和演示选项
    print_usage()
    print("\n🎮 运行选项:")
    print("   python demo_client_server.py --demo    # 运行演示")
    print("   python demo_client_server.py --info    # 显示使用说明")
    
    choice = input("\n是否要运行演示？(y/n): ").lower().strip()
    if choice in ['y', 'yes', '是']:
        await demo_interaction()

if __name__ == "__main__":
    asyncio.run(main()) 