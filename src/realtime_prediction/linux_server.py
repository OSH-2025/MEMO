"""
Linux服务器 - 接收Windows客户端数据，运行LLM预测
"""

import os
import sys
import time
import json
import uuid
import asyncio
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque

# Web框架
from aiohttp import web, WSMsgType
import aiohttp_cors

# 添加项目路径
sys.path.append(os.path.dirname(__file__))

from client_server_architecture import (
    ActivityData, PredictionRequest, PredictionResponse,
    ActivityBuffer, ServerConfig, format_activities_for_llm, logger
)

# LLM相关导入
try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch
    from peft import PeftModel
    LLM_LIBS_AVAILABLE = True
except ImportError:
    logger.warning("LLM libraries not available, using mock predictor")
    LLM_LIBS_AVAILABLE = False

class LLMPredictor:
    """LLM预测器"""
    
    def __init__(self, model_path: str, lora_path: str, enable_gpu: bool = True):
        self.model_path = model_path
        self.lora_path = lora_path
        self.enable_gpu = enable_gpu
        
        self.model = None
        self.tokenizer = None
        self.is_loaded = False
        
        logger.info(f"🤖 LLM预测器初始化 - GPU: {enable_gpu}")
    
    async def load_model(self):
        """异步加载模型"""
        if not LLM_LIBS_AVAILABLE:
            logger.warning("🚫 LLM库不可用，使用模拟预测器")
            self.is_loaded = True
            return True
        
        try:
            logger.info("📥 开始加载LLM模型...")
            
            # 在线程池中加载模型以避免阻塞
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._load_model_sync)
            
            self.is_loaded = True
            logger.info("✅ LLM模型加载完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 模型加载失败: {e}")
            return False
    
    def _load_model_sync(self):
        """同步加载模型"""
        # 加载tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_path, 
            trust_remote_code=True
        )
        self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # 加载模型
        device_map = "auto" if self.enable_gpu else "cpu"
        torch_dtype = torch.bfloat16 if self.enable_gpu else torch.float32
        
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            device_map=device_map,
            torch_dtype=torch_dtype,
            trust_remote_code=True
        ).eval()
        
        # 加载LoRA权重
        if os.path.exists(self.lora_path):
            self.model = PeftModel.from_pretrained(self.model, model_id=self.lora_path)
            logger.info(f"📦 LoRA权重已加载: {self.lora_path}")
    
    async def predict_next_activity(self, activities: List[ActivityData]) -> Dict[str, Any]:
        """预测下一个活动"""
        start_time = time.time()
        
        if not self.is_loaded:
            return self._mock_prediction(activities, start_time)
        
        if not LLM_LIBS_AVAILABLE:
            return self._mock_prediction(activities, start_time)
        
        try:
            # 格式化活动序列
            activity_sequence = format_activities_for_llm(activities)
            
            # 构造prompt
            system_prompt = (
                "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
                "你是一个智能助手，请根据用户最近的活动序列，预测下一个最有可能的用户活动。"
                "输出格式类似\"2025-05-22 08:30:38 - 访问网站 github.com 的页面 'README.md'\"，"
                "注意这里的网页或应用只考虑已知确定的网页和应用。\n"
                "<|eot_id|>"
            )
            
            user_prompt = (
                "<|start_header_id|>user<|end_header_id|>\n\n"
                "根据用户之前的活动序列，预测下一个可能的活动。\n"
                "用户活动序列:\n"
                f"{activity_sequence}\n"
                "<|eot_id|>"
            )
            
            assistant_prompt = "<|start_header_id|>assistant<|end_header_id|>\n\n"
            
            full_prompt = system_prompt + user_prompt + assistant_prompt
            
            # 在线程池中运行推理
            loop = asyncio.get_event_loop()
            prediction = await loop.run_in_executor(
                None, 
                self._generate_prediction, 
                full_prompt
            )
            
            processing_time = time.time() - start_time
            
            return {
                'prediction': prediction.strip(),
                'confidence': 0.85,  # 暂时硬编码
                'processing_time': processing_time,
                'model_used': 'llama3-instruct-lora'
            }
            
        except Exception as e:
            logger.error(f"❌ 预测失败: {e}")
            return self._mock_prediction(activities, start_time)
    
    def _generate_prediction(self, prompt: str) -> str:
        """生成预测结果"""
        # 转token id
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        
        # 生成
        with torch.no_grad():
            generated_ids = self.model.generate(
                input_ids=inputs.input_ids,
                attention_mask=inputs.attention_mask,
                max_new_tokens=128,
                temperature=0.7,
                do_sample=True,
                top_p=0.95,
                eos_token_id=self.tokenizer.eos_token_id,
                pad_token_id=self.tokenizer.pad_token_id
            )
        
        # 解码，仅取新生成的部分
        response = self.tokenizer.decode(
            generated_ids[0][inputs.input_ids.shape[1]:], 
            skip_special_tokens=True
        )
        
        return response
    
    def _mock_prediction(self, activities: List[ActivityData], start_time: float) -> Dict[str, Any]:
        """模拟预测结果"""
        mock_predictions = [
            "2025-05-22 08:31:15 - 访问网站 github.com 的页面 'MEMO/README.md'",
            "2025-05-22 08:31:45 - 切换到应用 VSCode - 'main.py'",
            "2025-05-22 08:32:10 - 访问网站 stackoverflow.com 的页面 'Python async tutorial'",
            "2025-05-22 08:32:35 - 访问网站 docs.python.org 的页面 'asyncio documentation'",
        ]
        
        # 根据最近活动选择预测
        if activities:
            last_activity = activities[-1]
            if last_activity.activity_type == 'browser_history':
                prediction = mock_predictions[0]
            elif last_activity.activity_type == 'window_focus':
                prediction = mock_predictions[1]
            else:
                prediction = mock_predictions[2]
        else:
            prediction = mock_predictions[0]
        
        # 更新时间戳为当前时间
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        prediction = prediction.replace('2025-05-22 08:3', current_time[:16])
        
        processing_time = time.time() - start_time
        
        return {
            'prediction': prediction,
            'confidence': 0.75,
            'processing_time': processing_time,
            'model_used': 'mock-predictor'
        }

class ClientManager:
    """客户端管理器"""
    
    def __init__(self):
        self.clients: Dict[str, Dict[str, Any]] = {}
        self.client_activities: Dict[str, ActivityBuffer] = {}
        self.lock = threading.Lock()
        
        logger.info("👥 客户端管理器初始化完成")
    
    def register_client(self, client_id: str) -> bool:
        """注册新客户端"""
        with self.lock:
            if client_id not in self.clients:
                self.clients[client_id] = {
                    'id': client_id,
                    'connected_at': datetime.now().isoformat(),
                    'last_heartbeat': datetime.now().isoformat(),
                    'activities_count': 0,
                    'predictions_count': 0
                }
                
                self.client_activities[client_id] = ActivityBuffer(max_size=200)
                
                logger.info(f"📱 新客户端注册: {client_id}")
                return True
            
            return False
    
    def update_heartbeat(self, client_id: str) -> bool:
        """更新客户端心跳"""
        with self.lock:
            if client_id in self.clients:
                self.clients[client_id]['last_heartbeat'] = datetime.now().isoformat()
                return True
            return False
    
    def add_activities(self, client_id: str, activities: List[ActivityData]) -> bool:
        """添加客户端活动数据"""
        with self.lock:
            if client_id in self.client_activities:
                buffer = self.client_activities[client_id]
                for activity in activities:
                    buffer.add_activity(activity)
                
                self.clients[client_id]['activities_count'] += len(activities)
                logger.debug(f"📝 客户端 {client_id} 添加了 {len(activities)} 个活动")
                return True
            
            return False
    
    def get_client_activities(self, client_id: str, count: int = 20) -> List[ActivityData]:
        """获取客户端的最近活动"""
        with self.lock:
            if client_id in self.client_activities:
                return self.client_activities[client_id].get_recent_activities(count)
            return []
    
    def increment_prediction_count(self, client_id: str):
        """增加预测计数"""
        with self.lock:
            if client_id in self.clients:
                self.clients[client_id]['predictions_count'] += 1
    
    def get_client_info(self, client_id: str) -> Optional[Dict[str, Any]]:
        """获取客户端信息"""
        with self.lock:
            return self.clients.get(client_id)
    
    def get_all_clients(self) -> List[Dict[str, Any]]:
        """获取所有客户端信息"""
        with self.lock:
            return list(self.clients.values())
    
    def cleanup_inactive_clients(self, timeout_minutes: int = 10):
        """清理不活跃的客户端"""
        cutoff_time = datetime.now() - timedelta(minutes=timeout_minutes)
        
        with self.lock:
            inactive_clients = []
            
            for client_id, client_info in self.clients.items():
                last_heartbeat = datetime.fromisoformat(client_info['last_heartbeat'])
                if last_heartbeat < cutoff_time:
                    inactive_clients.append(client_id)
            
            for client_id in inactive_clients:
                del self.clients[client_id]
                del self.client_activities[client_id]
                logger.info(f"🗑️ 清理不活跃客户端: {client_id}")

class ActivityPredictionServer:
    """活动预测服务器"""
    
    def __init__(self, config: ServerConfig):
        self.config = config
        self.client_manager = ClientManager()
        self.llm_predictor = LLMPredictor(
            config.model_path, 
            config.lora_path, 
            config.enable_gpu
        )
        
        self.app = web.Application()
        self.setup_routes()
        self.setup_cors()
        
        # 统计信息
        self.stats = {
            'start_time': None,
            'total_requests': 0,
            'total_predictions': 0,
            'total_activities': 0,
            'active_clients': 0
        }
        
        logger.info(f"🖥️ 服务器初始化完成 - 端口: {config.port}")
    
    def setup_cors(self):
        """设置CORS"""
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # 为所有路由添加CORS
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    def setup_routes(self):
        """设置路由"""
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/status', self.get_status)
        self.app.router.add_get('/clients', self.get_clients)
        
        self.app.router.add_post('/heartbeat', self.handle_heartbeat)
        self.app.router.add_post('/activity', self.handle_single_activity)
        self.app.router.add_post('/activities/batch', self.handle_batch_activities)
        self.app.router.add_post('/predict', self.handle_prediction_request)
        
        logger.info("🔗 HTTP路由设置完成")
    
    async def health_check(self, request):
        """健康检查"""
        return web.json_response({
            'status': 'healthy',
            'server': 'activity-prediction-server',
            'timestamp': datetime.now().isoformat(),
            'llm_loaded': self.llm_predictor.is_loaded
        })
    
    async def get_status(self, request):
        """获取服务器状态"""
        self.stats['active_clients'] = len(self.client_manager.clients)
        
        return web.json_response({
            'stats': self.stats,
            'config': self.config.to_dict(),
            'llm_status': {
                'loaded': self.llm_predictor.is_loaded,
                'model_path': self.config.model_path,
                'lora_path': self.config.lora_path
            }
        })
    
    async def get_clients(self, request):
        """获取客户端列表"""
        clients = self.client_manager.get_all_clients()
        return web.json_response({
            'clients': clients,
            'total_count': len(clients)
        })
    
    async def handle_heartbeat(self, request):
        """处理心跳包"""
        try:
            data = await request.json()
            client_id = data.get('client_id')
            
            if not client_id:
                return web.json_response(
                    {'error': 'missing client_id'}, 
                    status=400
                )
            
            # 注册或更新客户端
            if client_id not in self.client_manager.clients:
                self.client_manager.register_client(client_id)
            else:
                self.client_manager.update_heartbeat(client_id)
            
            self.stats['total_requests'] += 1
            
            return web.json_response({
                'status': 'ok',
                'server_time': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"❌ 心跳处理错误: {e}")
            return web.json_response(
                {'error': str(e)}, 
                status=500
            )
    
    async def handle_single_activity(self, request):
        """处理单个活动数据"""
        try:
            data = await request.json()
            activity = ActivityData.from_dict(data)
            
            # 注册客户端（如果需要）
            if activity.client_id not in self.client_manager.clients:
                self.client_manager.register_client(activity.client_id)
            
            # 添加活动
            success = self.client_manager.add_activities(activity.client_id, [activity])
            
            if success:
                self.stats['total_activities'] += 1
                return web.json_response({'status': 'received'})
            else:
                return web.json_response(
                    {'error': 'failed to store activity'}, 
                    status=500
                )
                
        except Exception as e:
            logger.error(f"❌ 单个活动处理错误: {e}")
            return web.json_response(
                {'error': str(e)}, 
                status=500
            )
    
    async def handle_batch_activities(self, request):
        """处理批量活动数据"""
        try:
            data = await request.json()
            client_id = data.get('client_id')
            activities_data = data.get('activities', [])
            
            if not client_id:
                return web.json_response(
                    {'error': 'missing client_id'}, 
                    status=400
                )
            
            # 转换为ActivityData对象
            activities = [ActivityData.from_dict(act) for act in activities_data]
            
            # 注册客户端（如果需要）
            if client_id not in self.client_manager.clients:
                self.client_manager.register_client(client_id)
            
            # 添加活动
            success = self.client_manager.add_activities(client_id, activities)
            
            if success:
                self.stats['total_activities'] += len(activities)
                logger.info(f"📦 收到批量活动: {client_id} - {len(activities)} 个")
                
                return web.json_response({
                    'status': 'received',
                    'count': len(activities)
                })
            else:
                return web.json_response(
                    {'error': 'failed to store activities'}, 
                    status=500
                )
                
        except Exception as e:
            logger.error(f"❌ 批量活动处理错误: {e}")
            return web.json_response(
                {'error': str(e)}, 
                status=500
            )
    
    async def handle_prediction_request(self, request):
        """处理预测请求"""
        try:
            data = await request.json()
            pred_request = PredictionRequest.from_dict(data)
            
            # 获取客户端最近的活动（如果请求中没有提供足够的活动）
            if len(pred_request.activities) < 3:
                client_activities = self.client_manager.get_client_activities(
                    pred_request.client_id, 20
                )
                if client_activities:
                    pred_request.activities = client_activities
            
            if len(pred_request.activities) < 1:
                return web.json_response(
                    {'error': 'insufficient activity data'}, 
                    status=400
                )
            
            # 执行预测
            prediction_result = await self.llm_predictor.predict_next_activity(
                pred_request.activities
            )
            
            # 创建响应
            response = PredictionResponse(
                request_id=pred_request.request_id,
                prediction=prediction_result['prediction'],
                confidence=prediction_result['confidence'],
                timestamp=datetime.now().isoformat(),
                processing_time=prediction_result['processing_time']
            )
            
            # 更新统计
            self.stats['total_predictions'] += 1
            self.client_manager.increment_prediction_count(pred_request.client_id)
            
            logger.info(f"🔮 预测完成: {pred_request.client_id} - {response.prediction[:50]}...")
            
            return web.json_response(response.to_dict())
            
        except Exception as e:
            logger.error(f"❌ 预测处理错误: {e}")
            return web.json_response(
                {'error': str(e)}, 
                status=500
            )
    
    async def start_server(self):
        """启动服务器"""
        logger.info("🚀 启动活动预测服务器")
        
        self.stats['start_time'] = datetime.now().isoformat()
        
        # 加载LLM模型
        logger.info("📥 加载LLM模型...")
        model_loaded = await self.llm_predictor.load_model()
        if not model_loaded:
            logger.warning("⚠️ LLM模型加载失败，将使用模拟预测器")
        
        # 启动清理任务
        cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        # 启动web服务器
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, self.config.host, self.config.port)
        await site.start()
        
        logger.info(f"✅ 服务器启动成功 - http://{self.config.host}:{self.config.port}")
        logger.info(f"📋 API端点:")
        logger.info(f"   健康检查: GET /health")
        logger.info(f"   服务器状态: GET /status")
        logger.info(f"   客户端列表: GET /clients")
        logger.info(f"   心跳: POST /heartbeat")
        logger.info(f"   活动数据: POST /activities/batch")
        logger.info(f"   预测请求: POST /predict")
        
        return runner, cleanup_task
    
    async def _cleanup_loop(self):
        """清理循环"""
        while True:
            try:
                await asyncio.sleep(300)  # 每5分钟清理一次
                self.client_manager.cleanup_inactive_clients()
            except Exception as e:
                logger.error(f"❌ 清理循环错误: {e}")

async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Linux活动预测服务器")
    parser.add_argument("--config", "-c", help="配置文件路径")
    parser.add_argument("--host", help="服务器主机地址")
    parser.add_argument("--port", "-p", type=int, help="服务器端口")
    parser.add_argument("--model", "-m", help="模型路径")
    parser.add_argument("--lora", "-l", help="LoRA权重路径")
    parser.add_argument("--no-gpu", action="store_true", help="禁用GPU")
    
    args = parser.parse_args()
    
    # 创建服务器配置
    config = ServerConfig(args.config)
    
    # 处理命令行参数
    if args.host:
        config.host = args.host
    if args.port:
        config.port = args.port
    if args.model:
        config.model_path = args.model
    if args.lora:
        config.lora_path = args.lora
    if args.no_gpu:
        config.enable_gpu = False
    
    # 创建服务器
    server = ActivityPredictionServer(config)
    
    try:
        # 启动服务器
        runner, cleanup_task = await server.start_server()
        
        print("\n🔄 服务器运行中... 按 Ctrl+C 停止")
        
        # 保持运行直到中断
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n👋 用户中断")
    except Exception as e:
        logger.error(f"❌ 服务器运行错误: {e}")
    finally:
        # 清理资源
        if 'cleanup_task' in locals():
            cleanup_task.cancel()
        if 'runner' in locals():
            await runner.cleanup()
        
        logger.info("✅ 服务器已停止")

if __name__ == "__main__":
    asyncio.run(main()) 