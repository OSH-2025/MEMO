"""
Windows客户端 - 收集活动数据并发送到Linux服务器
"""

import os
import sys
import time
import json
import uuid
import asyncio
import aiohttp
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'data_collection'))

from client_server_architecture import (
    ActivityData, PredictionRequest, PredictionResponse,
    NetworkProtocol, ActivityBuffer, ClientConfig,
    create_activity_from_monitor_data, logger
)

try:
    from activity_monitor import ActivityMonitor
    WINDOWS_LIBS_AVAILABLE = True
except ImportError:
    logger.warning("Windows libraries not available, using mock monitor")
    WINDOWS_LIBS_AVAILABLE = False
    
    class ActivityMonitor:
        """Mock ActivityMonitor for testing"""
        def __init__(self, output_dir="activity_data"):
            self.output_dir = output_dir
            self.activities = []
            self.running = False
        
        def start(self):
            self.running = True
        
        def stop(self):
            self.running = False
        
        def save_data(self):
            pass

class HTTPClient(NetworkProtocol):
    """HTTP客户端通信协议"""
    
    def __init__(self, config: ClientConfig):
        super().__init__()
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_url = f"http://{config.server_host}:{config.server_port}"
        
    async def connect(self) -> bool:
        """连接到服务器"""
        try:
            if self.session is None:
                timeout = aiohttp.ClientTimeout(total=30)
                self.session = aiohttp.ClientSession(timeout=timeout)
            
            # 测试连接
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    self.is_connected = True
                    logger.info(f"✅ 已连接到服务器 {self.base_url}")
                    return True
                else:
                    logger.error(f"❌ 服务器返回状态码: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ 连接服务器失败: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """断开连接"""
        if self.session:
            await self.session.close()
            self.session = None
        self.is_connected = False
        logger.info("🔌 已断开服务器连接")
    
    async def send_activity(self, activity: ActivityData) -> bool:
        """发送单个活动数据"""
        try:
            if not self.is_connected:
                return False
            
            async with self.session.post(
                f"{self.base_url}/activity",
                json=activity.to_dict()
            ) as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"❌ 发送活动数据失败: {e}")
            return False
    
    async def send_activities_batch(self, activities: List[ActivityData]) -> bool:
        """批量发送活动数据"""
        try:
            if not self.is_connected or not activities:
                return False
            
            data = {
                'activities': [activity.to_dict() for activity in activities],
                'client_id': self.config.client_id,
                'timestamp': datetime.now().isoformat()
            }
            
            async with self.session.post(
                f"{self.base_url}/activities/batch",
                json=data
            ) as response:
                success = response.status == 200
                if success:
                    logger.info(f"📤 成功发送 {len(activities)} 个活动数据")
                else:
                    logger.error(f"❌ 批量发送失败，状态码: {response.status}")
                return success
                
        except Exception as e:
            logger.error(f"❌ 批量发送活动数据失败: {e}")
            return False
    
    async def request_prediction(self, request: PredictionRequest) -> Optional[PredictionResponse]:
        """请求预测"""
        try:
            if not self.is_connected:
                return None
            
            async with self.session.post(
                f"{self.base_url}/predict",
                json=request.to_dict()
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return PredictionResponse.from_dict(data)
                else:
                    logger.error(f"❌ 预测请求失败，状态码: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ 预测请求失败: {e}")
            return None
    
    async def send_heartbeat(self) -> bool:
        """发送心跳包"""
        try:
            if not self.is_connected:
                return False
            
            data = {
                'client_id': self.config.client_id,
                'timestamp': datetime.now().isoformat()
            }
            
            async with self.session.post(
                f"{self.base_url}/heartbeat",
                json=data
            ) as response:
                success = response.status == 200
                if success:
                    self.last_heartbeat = datetime.now().isoformat()
                return success
                
        except Exception as e:
            logger.error(f"❌ 心跳发送失败: {e}")
            return False

class WindowsActivityClient:
    """Windows活动监控客户端"""
    
    def __init__(self, config_file: str = None):
        self.config = ClientConfig(config_file)
        self.buffer = ActivityBuffer(max_size=self.config.buffer_size)
        self.http_client = HTTPClient(self.config)
        
        # 活动监控器
        if WINDOWS_LIBS_AVAILABLE:
            self.monitor = ActivityMonitor("client_activity_data")
        else:
            self.monitor = ActivityMonitor("client_activity_data")  # Mock版本
        
        # 控制标志
        self.running = False
        self.tasks = []
        
        # 统计信息
        self.stats = {
            'activities_collected': 0,
            'activities_sent': 0,
            'predictions_received': 0,
            'connection_errors': 0,
            'start_time': None
        }
        
        logger.info(f"🔧 Windows客户端初始化完成 - 客户端ID: {self.config.client_id}")
    
    def _activity_monitor_hook(self, activity_data: Dict[str, Any]):
        """活动监控器回调函数"""
        try:
            activity = create_activity_from_monitor_data(activity_data, self.config.client_id)
            self.buffer.add_activity(activity)
            self.stats['activities_collected'] += 1
            
            logger.debug(f"📝 收集到活动: {activity.activity_type}")
            
        except Exception as e:
            logger.error(f"❌ 处理活动数据失败: {e}")
    
    async def start_monitoring(self):
        """启动活动监控"""
        try:
            # 使用装饰器模式替代直接替换append方法
            # 保存原始activities引用
            self.original_activities = self.monitor.activities
            
            # 替换整个activities列表为自定义列表
            class MonitoredList(list):
                def __init__(self, parent_client):
                    super().__init__()
                    self.client = parent_client
                
                def append(self, item):
                    super().append(item)
                    # 调用hook函数
                    self.client._activity_monitor_hook(item)
            
            # 创建新的监控列表
            monitored_list = MonitoredList(self)
            
            # 复制现有数据
            monitored_list.extend(self.monitor.activities)
            
            # 替换monitor的activities列表
            self.monitor.activities = monitored_list
            
            # 在线程中启动监控
            monitor_thread = threading.Thread(target=self.monitor.start, daemon=True)
            monitor_thread.start()
            
            logger.info("🔍 活动监控已启动")
            
        except Exception as e:
            logger.error(f"❌ 启动活动监控失败: {e}")
            # 如果出错，恢复原始activities
            if hasattr(self, 'original_activities'):
                self.monitor.activities = self.original_activities
    
    async def start_communication(self):
        """启动与服务器的通信"""
        # 连接到服务器
        connected = await self.http_client.connect()
        if not connected:
            logger.error("❌ 无法连接到服务器")
            return False
        
        # 启动后台任务
        self.tasks = [
            asyncio.create_task(self._heartbeat_loop()),
            asyncio.create_task(self._batch_send_loop()),
            asyncio.create_task(self._prediction_loop())
        ]
        
        logger.info("📡 服务器通信已启动")
        return True
    
    async def _heartbeat_loop(self):
        """心跳循环"""
        while self.running:
            try:
                success = await self.http_client.send_heartbeat()
                if not success:
                    self.stats['connection_errors'] += 1
                    logger.warning("💔 心跳发送失败")
                
                await asyncio.sleep(self.config.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"❌ 心跳循环错误: {e}")
                await asyncio.sleep(5)
    
    async def _batch_send_loop(self):
        """批量发送循环"""
        while self.running:
            try:
                # 获取待发送的活动
                activities = self.buffer.get_batch()
                
                if activities:
                    success = await self.http_client.send_activities_batch(activities)
                    if success:
                        self.buffer.mark_sent(len(activities))
                        self.stats['activities_sent'] += len(activities)
                    else:
                        self.stats['connection_errors'] += 1
                
                await asyncio.sleep(self.config.batch_send_interval)
                
            except Exception as e:
                logger.error(f"❌ 批量发送循环错误: {e}")
                await asyncio.sleep(5)
    
    async def _prediction_loop(self):
        """预测请求循环"""
        while self.running:
            try:
                # 获取最近的活动用于预测
                recent_activities = self.buffer.get_recent_activities(20)
                
                if len(recent_activities) >= 3:
                    request = PredictionRequest(
                        activities=recent_activities,
                        client_id=self.config.client_id,
                        request_id=str(uuid.uuid4()),
                        timestamp=datetime.now().isoformat()
                    )
                    
                    response = await self.http_client.request_prediction(request)
                    if response:
                        self.stats['predictions_received'] += 1
                        logger.info(f"🔮 收到预测: {response.prediction}")
                        logger.info(f"   置信度: {response.confidence:.2f}")
                        logger.info(f"   处理时间: {response.processing_time:.2f}秒")
                    else:
                        self.stats['connection_errors'] += 1
                
                await asyncio.sleep(self.config.prediction_interval)
                
            except Exception as e:
                logger.error(f"❌ 预测循环错误: {e}")
                await asyncio.sleep(10)
    
    async def start(self):
        """启动客户端"""
        logger.info("🚀 启动Windows活动监控客户端")
        
        self.running = True
        self.stats['start_time'] = datetime.now().isoformat()
        
        try:
            # 启动活动监控
            await self.start_monitoring()
            
            # 启动服务器通信
            communication_started = await self.start_communication()
            if not communication_started:
                logger.error("❌ 无法启动服务器通信")
                return False
            
            logger.info("✅ 客户端启动成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 客户端启动失败: {e}")
            return False
    
    async def stop(self):
        """停止客户端"""
        logger.info("⏹️ 停止Windows活动监控客户端")
        
        self.running = False
        
        # 停止活动监控
        if self.monitor:
            self.monitor.stop()
        
        # 取消所有任务
        for task in self.tasks:
            task.cancel()
        
        # 等待任务结束
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # 断开服务器连接
        await self.http_client.disconnect()
        
        # 显示统计信息
        self.print_stats()
        
        logger.info("✅ 客户端已停止")
    
    def print_stats(self):
        """打印统计信息"""
        buffer_stats = self.buffer.get_stats()
        
        print("\n" + "="*60)
        print("📊 客户端统计信息")
        print("="*60)
        print(f"运行时间: {self.stats['start_time']}")
        print(f"收集活动数: {self.stats['activities_collected']}")
        print(f"发送活动数: {self.stats['activities_sent']}")
        print(f"收到预测数: {self.stats['predictions_received']}")
        print(f"连接错误数: {self.stats['connection_errors']}")
        print(f"缓冲区状态: {buffer_stats['buffer_size']}/{buffer_stats['max_size']}")
        print(f"待发送数据: {buffer_stats['pending']}")
        print("="*60)

async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Windows活动监控客户端")
    parser.add_argument("--config", "-c", help="配置文件路径")
    parser.add_argument("--server", "-s", help="服务器地址 (host:port)")
    parser.add_argument("--test", "-t", action="store_true", help="测试模式")
    parser.add_argument("--demo", "-d", action="store_true", help="演示模式")
    
    args = parser.parse_args()
    
    # 创建客户端
    client = WindowsActivityClient(args.config)
    
    # 处理服务器地址参数
    if args.server:
        if ":" in args.server:
            host, port = args.server.split(":", 1)
            client.config.server_host = host
            client.config.server_port = int(port)
        else:
            client.config.server_host = args.server
    
    if args.demo:
        logger.info("🎬 演示模式：使用预设活动数据")
        # 在演示模式下添加一系列模拟数据
        demo_activities = [
            {
                'type': 'browser_history',
                'domain': 'www.douban.com',
                'title': '【盘个剧本押个C】【Game of Thrones】1st episode 《All men must die》',
                'timestamp': datetime.now().isoformat()
            },
            {
                'type': 'browser_history',
                'domain': 'github.com',
                'title': 'self-llm/examples/AMchat-高等数学 at master · datawhalechina/self-llm',
                'timestamp': datetime.now().isoformat()
            },
            {
                'type': 'browser_history',
                'domain': 'github.com',
                'title': 'MEMO/feasibility_report/Fine-tuning of LLM.md at main · OSH-2025/MEMO',
                'timestamp': datetime.now().isoformat()
            },
            {
                'type': 'browser_history',
                'domain': 'github.com',
                'title': 'MEMO/src at main · OSH-2025/MEMO',
                'timestamp': datetime.now().isoformat()
            },
            {
                'type': 'window_focus',
                'process_name': 'Code.exe',
                'window_title': 'windows_client.py - Visual Studio Code',
                'timestamp': datetime.now().isoformat()
            }
        ]
        
        # 添加演示数据到缓冲区
        for activity_data in demo_activities:
            client._activity_monitor_hook(activity_data)
        
        print(f"\n📊 已添加 {len(demo_activities)} 条演示活动数据")
        
    elif args.test:
        logger.info("🧪 测试模式：模拟活动数据")
        # 在测试模式下添加一些模拟数据
        test_activities = [
            {
                'type': 'browser_history',
                'domain': 'github.com',
                'title': 'MEMO Project',
                'timestamp': datetime.now().isoformat()
            },
            {
                'type': 'window_focus',
                'process_name': 'Code.exe',
                'window_title': 'client.py - VSCode',
                'timestamp': datetime.now().isoformat()
            }
        ]
        
        for activity_data in test_activities:
            client._activity_monitor_hook(activity_data)
    
    try:
        # 启动客户端
        started = await client.start()
        if not started:
            return
        
        if args.demo or args.test:
            print(f"\n🔄 {'演示' if args.demo else '测试'}模式运行中... 按 Ctrl+C 停止")
            # 在演示/测试模式下运行较短时间
            await asyncio.sleep(30)  # 运行30秒用于演示
            print(f"\n✅ {'演示' if args.demo else '测试'}模式完成")
        else:
            print("\n🔄 客户端运行中... 按 Ctrl+C 停止")
            # 保持运行直到中断
            while True:
                await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n👋 用户中断")
    except Exception as e:
        logger.error(f"❌ 运行时错误: {e}")
    finally:
        await client.stop()

if __name__ == "__main__":
    asyncio.run(main()) 