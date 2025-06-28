"""
客户端-服务器架构核心组件
Windows客户端收集数据 -> 网络传输 -> Linux服务器处理LLM预测
"""

import asyncio
import json
import time
import threading
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ActivityData:
    """活动数据结构"""
    activity_type: str
    timestamp: str
    data: Dict[str, Any]
    client_id: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActivityData':
        return cls(**data)

@dataclass
class PredictionRequest:
    """预测请求结构"""
    activities: List[ActivityData]
    client_id: str
    request_id: str
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'activities': [activity.to_dict() for activity in self.activities],
            'client_id': self.client_id,
            'request_id': self.request_id,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PredictionRequest':
        activities = [ActivityData.from_dict(act) for act in data['activities']]
        return cls(
            activities=activities,
            client_id=data['client_id'],
            request_id=data['request_id'],
            timestamp=data['timestamp']
        )

@dataclass
class PredictionResponse:
    """预测响应结构"""
    request_id: str
    prediction: str
    confidence: float
    timestamp: str
    processing_time: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PredictionResponse':
        return cls(**data)

class NetworkProtocol:
    """网络通信协议基类"""
    
    def __init__(self):
        self.is_connected = False
        self.last_heartbeat = None
    
    async def send_activity(self, activity: ActivityData) -> bool:
        """发送活动数据"""
        raise NotImplementedError
    
    async def request_prediction(self, request: PredictionRequest) -> Optional[PredictionResponse]:
        """请求预测"""
        raise NotImplementedError
    
    async def send_heartbeat(self) -> bool:
        """发送心跳包"""
        raise NotImplementedError
    
    def get_connection_status(self) -> Dict[str, Any]:
        """获取连接状态"""
        return {
            'is_connected': self.is_connected,
            'last_heartbeat': self.last_heartbeat,
            'timestamp': datetime.now().isoformat()
        }

class ActivityBuffer:
    """活动数据缓冲区"""
    
    def __init__(self, max_size: int = 100, batch_size: int = 10):
        self.max_size = max_size
        self.batch_size = batch_size
        self.buffer: List[ActivityData] = []
        self.lock = threading.Lock()
        self.total_received = 0
        self.total_sent = 0
    
    def add_activity(self, activity: ActivityData) -> bool:
        """添加活动到缓冲区"""
        with self.lock:
            if len(self.buffer) >= self.max_size:
                # 删除最旧的活动
                self.buffer.pop(0)
            
            self.buffer.append(activity)
            self.total_received += 1
            
            logger.debug(f"Activity added to buffer: {activity.activity_type}")
            return True
    
    def get_batch(self, size: Optional[int] = None) -> List[ActivityData]:
        """获取一批活动数据"""
        if size is None:
            size = self.batch_size
        
        with self.lock:
            batch = self.buffer[-size:] if self.buffer else []
            return batch.copy()
    
    def get_recent_activities(self, count: int = 20) -> List[ActivityData]:
        """获取最近的活动"""
        with self.lock:
            return self.buffer[-count:] if self.buffer else []
    
    def mark_sent(self, count: int):
        """标记已发送的活动数量"""
        self.total_sent += count
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓冲区统计信息"""
        with self.lock:
            return {
                'buffer_size': len(self.buffer),
                'max_size': self.max_size,
                'total_received': self.total_received,
                'total_sent': self.total_sent,
                'pending': len(self.buffer)
            }

class ClientConfig:
    """客户端配置"""
    
    def __init__(self, config_file: str = None):
        self.server_host = "localhost"
        self.server_port = 8888
        self.client_id = f"windows_client_{int(time.time())}"
        self.heartbeat_interval = 30  # 秒
        self.batch_send_interval = 10  # 秒
        self.retry_attempts = 3
        self.retry_delay = 5  # 秒
        self.buffer_size = 100
        self.prediction_interval = 60  # 秒
        
        if config_file:
            self.load_from_file(config_file)
    
    def load_from_file(self, config_file: str):
        """从文件加载配置"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            for key, value in config.items():
                if hasattr(self, key):
                    setattr(self, key, value)
                    
            logger.info(f"Configuration loaded from {config_file}")
        except Exception as e:
            logger.error(f"Failed to load config from {config_file}: {e}")
    
    def save_to_file(self, config_file: str):
        """保存配置到文件"""
        try:
            config = {
                'server_host': self.server_host,
                'server_port': self.server_port,
                'client_id': self.client_id,
                'heartbeat_interval': self.heartbeat_interval,
                'batch_send_interval': self.batch_send_interval,
                'retry_attempts': self.retry_attempts,
                'retry_delay': self.retry_delay,
                'buffer_size': self.buffer_size,
                'prediction_interval': self.prediction_interval
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Configuration saved to {config_file}")
        except Exception as e:
            logger.error(f"Failed to save config to {config_file}: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'server_host': self.server_host,
            'server_port': self.server_port,
            'client_id': self.client_id,
            'heartbeat_interval': self.heartbeat_interval,
            'batch_send_interval': self.batch_send_interval,
            'retry_attempts': self.retry_attempts,
            'retry_delay': self.retry_delay,
            'buffer_size': self.buffer_size,
            'prediction_interval': self.prediction_interval
        }

class ServerConfig:
    """服务器配置"""
    
    def __init__(self, config_file: str = None):
        self.host = "0.0.0.0"
        self.port = 8888
        self.model_path = "./models/llama3-instruct"
        self.lora_path = "./models/lora-checkpoint"
        self.max_clients = 50
        self.activity_history_size = 200
        self.prediction_batch_size = 20
        self.enable_gpu = True
        self.model_cache_size = 2
        
        if config_file:
            self.load_from_file(config_file)
    
    def load_from_file(self, config_file: str):
        """从文件加载配置"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            for key, value in config.items():
                if hasattr(self, key):
                    setattr(self, key, value)
                    
            logger.info(f"Server configuration loaded from {config_file}")
        except Exception as e:
            logger.error(f"Failed to load server config from {config_file}: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'host': self.host,
            'port': self.port,
            'model_path': self.model_path,
            'lora_path': self.lora_path,
            'max_clients': self.max_clients,
            'activity_history_size': self.activity_history_size,
            'prediction_batch_size': self.prediction_batch_size,
            'enable_gpu': self.enable_gpu,
            'model_cache_size': self.model_cache_size
        }

# 工具函数
def create_activity_from_monitor_data(data: Dict[str, Any], client_id: str) -> ActivityData:
    """从监控器数据创建ActivityData对象"""
    return ActivityData(
        activity_type=data.get('type', 'unknown'),
        timestamp=data.get('timestamp', datetime.now().isoformat()),
        data=data,
        client_id=client_id
    )

def format_activities_for_llm(activities: List[ActivityData]) -> str:
    """格式化活动数据为LLM输入格式"""
    formatted_lines = []
    
    for activity in activities:
        data = activity.data
        activity_type = activity.activity_type
        timestamp = activity.timestamp
        
        # 解析时间戳
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            formatted_time = timestamp
        
        # 根据活动类型格式化
        if activity_type == 'browser_history':
            domain = data.get('domain', '')
            title = data.get('title', '')
            if domain and title:
                formatted_lines.append(f"{formatted_time} - 访问网站 {domain} 的页面 '{title}'")
            elif domain:
                formatted_lines.append(f"{formatted_time} - 访问网站 {domain}")
        
        elif activity_type == 'window_focus':
            process_name = data.get('process_name', '')
            window_title = data.get('window_title', '')
            if process_name and window_title:
                formatted_lines.append(f"{formatted_time} - 切换到应用 {process_name} - '{window_title}'")
        
        elif activity_type == 'file_access':
            file_path = data.get('path', '')
            if file_path:
                formatted_lines.append(f"{formatted_time} - 访问文件 {file_path}")
        
        else:
            formatted_lines.append(f"{formatted_time} - {activity_type} 活动")
    
    return '\n'.join(formatted_lines)

if __name__ == "__main__":
    # 测试数据结构
    print("🧪 测试客户端-服务器架构组件")
    
    # 测试活动数据
    activity = ActivityData(
        activity_type="browser_history",
        timestamp=datetime.now().isoformat(),
        data={
            "domain": "github.com",
            "title": "MEMO Project Repository"
        },
        client_id="test_client"
    )
    
    print(f"Activity: {activity}")
    print(f"Activity JSON: {json.dumps(activity.to_dict(), indent=2)}")
    
    # 测试缓冲区
    buffer = ActivityBuffer(max_size=5, batch_size=3)
    for i in range(7):
        test_activity = ActivityData(
            activity_type="test",
            timestamp=datetime.now().isoformat(),
            data={"index": i},
            client_id="test"
        )
        buffer.add_activity(test_activity)
    
    print(f"\nBuffer stats: {buffer.get_stats()}")
    print(f"Recent activities: {len(buffer.get_recent_activities(3))}")
    
    # 测试配置
    config = ClientConfig()
    print(f"\nClient config: {json.dumps(config.to_dict(), indent=2)}") 