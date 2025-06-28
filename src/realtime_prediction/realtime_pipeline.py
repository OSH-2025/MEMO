"""
实时活动预测管道 - 串联monitor、analyzer和LLM预测
"""

import os
import sys
import time
import json
import queue
import threading
import datetime
from collections import deque
from typing import List, Dict, Any, Optional
from pathlib import Path

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'data_collection'))

from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from peft import PeftModel


class ActivityQueue:
    """实时活动数据队列管理器"""
    
    def __init__(self, max_size: int = 20, history_window: int = 100):
        """初始化活动队列
        
        Args:
            max_size: 用于预测的活动序列最大长度
            history_window: 保存的历史活动总数
        """
        self.max_size = max_size
        self.history_window = history_window
        
        # 使用deque来维护固定大小的活动历史
        self.activity_history = deque(maxlen=history_window)
        
        # 线程安全的队列，用于实时数据传递
        self.real_time_queue = queue.Queue()
        
        # 锁，用于保护共享数据
        self.lock = threading.Lock()
        
        # 统计信息
        self.total_activities = 0
        self.last_activity_time = None
        
        print(f"活动队列初始化完成 - 预测窗口: {max_size}, 历史窗口: {history_window}")
    
    def add_activity(self, activity: Dict[str, Any]):
        """添加新活动到队列
        
        Args:
            activity: 活动数据字典
        """
        with self.lock:
            # 添加时间戳（如果没有的话）
            if 'timestamp' not in activity:
                activity['timestamp'] = datetime.datetime.now().isoformat()
            
            # 添加到历史记录
            self.activity_history.append(activity)
            
            # 添加到实时队列
            try:
                self.real_time_queue.put_nowait(activity)
            except queue.Full:
                # 队列满了，移除最旧的项目
                try:
                    self.real_time_queue.get_nowait()
                    self.real_time_queue.put_nowait(activity)
                except queue.Empty:
                    pass
            
            # 更新统计信息
            self.total_activities += 1
            self.last_activity_time = activity['timestamp']
    
    def get_recent_activities(self, count: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取最近的活动序列用于预测
        
        Args:
            count: 要获取的活动数量，默认使用max_size
            
        Returns:
            最近的活动列表
        """
        with self.lock:
            if count is None:
                count = self.max_size
            
            # 从历史记录中获取最近的活动
            recent_count = min(count, len(self.activity_history))
            if recent_count == 0:
                return []
            
            return list(self.activity_history)[-recent_count:]
    
    def format_activities_for_llm(self, activities: List[Dict[str, Any]]) -> str:
        """将活动序列格式化为LLM可理解的文本
        
        Args:
            activities: 活动列表
            
        Returns:
            格式化后的活动序列文本
        """
        formatted_activities = []
        
        for activity in activities:
            formatted = self._format_single_activity(activity)
            if formatted:
                formatted_activities.append(formatted)
        
        return '\n'.join(formatted_activities)
    
    def _format_single_activity(self, activity: Dict[str, Any]) -> str:
        """格式化单个活动为文本
        
        Args:
            activity: 单个活动字典
            
        Returns:
            格式化后的活动描述
        """
        activity_type = activity.get('type', '')
        timestamp = activity.get('timestamp', '')
        
        # 格式化时间戳
        try:
            dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            formatted_time = timestamp
        
        if activity_type == 'browser_history':
            domain = activity.get('domain', '')
            title = activity.get('title', '')
            if domain and title:
                return f"{formatted_time} - 访问网站 {domain} 的页面 '{title}'"
            elif domain:
                return f"{formatted_time} - 访问网站 {domain}"
        
        elif activity_type == 'window_focus':
            process_name = activity.get('process_name', '')
            window_title = activity.get('window_title', '')
            if process_name and window_title:
                return f"{formatted_time} - 切换到应用 {process_name} - '{window_title}'"
        
        elif activity_type == 'file_access':
            path = activity.get('path', '')
            operation = activity.get('operation', 'access')
            if path:
                filename = os.path.basename(path)
                return f"{formatted_time} - {operation} 文件 '{filename}'"
        
        return ""
    
    def get_stats(self) -> Dict[str, Any]:
        """获取队列统计信息
        
        Returns:
            统计信息字典
        """
        with self.lock:
            return {
                'total_activities': self.total_activities,
                'current_history_size': len(self.activity_history),
                'last_activity_time': self.last_activity_time,
                'queue_size': self.real_time_queue.qsize()
            }


class RealTimeLLMPredictor:
    """实时LLM活动预测器"""
    
    def __init__(self, model_path: str, lora_path: str):
        """初始化LLM预测器
        
        Args:
            model_path: 基础模型路径
            lora_path: LoRA权重路径
        """
        self.model_path = model_path
        self.lora_path = lora_path
        
        print("正在加载LLM模型...")
        self._load_model()
        print("LLM模型加载完成")
        
        # 系统提示词
        self.system_prompt = (
            "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
            "你是一个智能助手，请根据用户最近的活动序列，预测下一个最有可能的用户活动。"
            "输出格式类似 \"2025-05-22 08:30:38 - 访问网站 github.com 的页面 'README.md at main · OSH-2025/MEMO'\"，"
            "注意这里的网页或应用只考虑已知确定的网页和应用。\n"
            "<|eot_id|>"
        )
    
    def _load_model(self):
        """加载模型和tokenizer"""
        # 加载tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, trust_remote_code=True)
        self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # 加载模型
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path, 
            device_map="auto",
            torch_dtype=torch.bfloat16,
            trust_remote_code=True
        ).eval()
        
        # 加载lora权重
        self.model = PeftModel.from_pretrained(self.model, model_id=self.lora_path)
    
    def predict_next_activity(self, activity_sequence: str) -> str:
        """预测下一个活动
        
        Args:
            activity_sequence: 格式化的活动序列
            
        Returns:
            预测的下一个活动
        """
        # 构造完整的prompt
        user_prompt = (
            "<|start_header_id|>user<|end_header_id|>\n\n"
            "根据用户之前的活动序列，预测下一个可能的活动。\n"
            "用户活动序列:\n"
            f"{activity_sequence}\n"
            "<|eot_id|>"
        )
        
        assistant_prompt = "<|start_header_id|>assistant<|end_header_id|>\n\n"
        full_prompt = self.system_prompt + user_prompt + assistant_prompt
        
        # 转token id
        inputs = self.tokenizer(full_prompt, return_tensors="pt").to(self.model.device)
        
        # 生成预测
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
        
        return response.strip()


class RealTimeActivityPipeline:
    """实时活动预测管道协调器"""
    
    def __init__(self, 
                 model_path: str = './LLM-Research/Meta-Llama-3___1-8B-Instruct',
                 lora_path: str = './output/llama3_1_instruct_lora/checkpoint-138',
                 queue_size: int = 20,
                 prediction_interval: int = 30):
        """初始化实时管道
        
        Args:
            model_path: 基础模型路径
            lora_path: LoRA权重路径
            queue_size: 活动队列大小
            prediction_interval: 预测间隔（秒）
        """
        self.prediction_interval = prediction_interval
        
        # 初始化组件
        print("初始化实时活动预测管道...")
        self.activity_queue = ActivityQueue(max_size=queue_size)
        self.llm_predictor = RealTimeLLMPredictor(model_path, lora_path)
        
        # 控制变量
        self.running = False
        self.prediction_thread = None
        
        # 预测历史
        self.prediction_history = deque(maxlen=50)
        
        print("实时活动预测管道初始化完成")
    
    def add_activity(self, activity: Dict[str, Any]):
        """添加新活动（由monitor调用）
        
        Args:
            activity: 活动数据
        """
        self.activity_queue.add_activity(activity)
    
    def start_prediction_loop(self):
        """启动预测循环"""
        if self.running:
            print("预测循环已在运行")
            return
        
        self.running = True
        self.prediction_thread = threading.Thread(target=self._prediction_loop, daemon=True)
        self.prediction_thread.start()
        print("预测循环已启动")
    
    def stop_prediction_loop(self):
        """停止预测循环"""
        self.running = False
        if self.prediction_thread:
            self.prediction_thread.join(timeout=5)
        print("预测循环已停止")
    
    def _prediction_loop(self):
        """预测循环主函数"""
        while self.running:
            try:
                # 获取最近的活动
                recent_activities = self.activity_queue.get_recent_activities()
                
                if len(recent_activities) >= 3:  # 至少需要3个活动来进行预测
                    # 格式化活动序列
                    activity_sequence = self.activity_queue.format_activities_for_llm(recent_activities)
                    
                    # 进行预测
                    prediction = self.llm_predictor.predict_next_activity(activity_sequence)
                    
                    # 记录预测结果
                    prediction_record = {
                        'timestamp': datetime.datetime.now().isoformat(),
                        'input_activities': recent_activities[-3:],  # 记录最后3个活动
                        'prediction': prediction,
                        'activity_count': len(recent_activities)
                    }
                    
                    self.prediction_history.append(prediction_record)
                    
                    # 输出预测结果
                    print(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] 活动预测:")
                    print(f"基于最近 {len(recent_activities)} 个活动的预测:")
                    print(f"预测结果: {prediction}")
                    print("-" * 50)
                
                else:
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 活动数据不足，等待更多数据...")
                
                # 等待下一次预测
                time.sleep(self.prediction_interval)
                
            except Exception as e:
                print(f"预测循环错误: {e}")
                time.sleep(5)
    
    def get_latest_prediction(self) -> Optional[Dict[str, Any]]:
        """获取最新的预测结果
        
        Returns:
            最新的预测记录，如果没有则返回None
        """
        if self.prediction_history:
            return self.prediction_history[-1]
        return None
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """获取管道状态信息
        
        Returns:
            管道状态字典
        """
        queue_stats = self.activity_queue.get_stats()
        
        return {
            'running': self.running,
            'queue_stats': queue_stats,
            'prediction_count': len(self.prediction_history),
            'latest_prediction_time': self.prediction_history[-1]['timestamp'] if self.prediction_history else None
        }


def create_realtime_pipeline(**kwargs) -> RealTimeActivityPipeline:
    """创建实时活动预测管道的工厂函数
    
    Args:
        **kwargs: 传递给RealTimeActivityPipeline的参数
        
    Returns:
        配置好的实时预测管道实例
    """
    return RealTimeActivityPipeline(**kwargs)


if __name__ == "__main__":
    # 测试用例
    print("创建实时活动预测管道...")
    pipeline = create_realtime_pipeline(
        prediction_interval=10  # 每10秒预测一次
    )
    
    # 启动预测循环
    pipeline.start_prediction_loop()
    
    try:
        # 模拟添加一些活动数据
        test_activities = [
            {
                'type': 'browser_history',
                'domain': 'www.douban.com',
                'title': '【盘个剧本押个C】【Game of Thrones】1st episode 《All men must die》'
            },
            {
                'type': 'browser_history',
                'domain': 'github.com',
                'title': 'self-llm/examples/AMchat-高等数学 at master · datawhalechina/self-llm'
            },
            {
                'type': 'browser_history',
                'domain': 'github.com',
                'title': 'MEMO/feasibility_report/Fine-tuning of LLM.md at main · OSH-2025/MEMO'
            }
        ]
        
        print("添加测试活动数据...")
        for activity in test_activities:
            pipeline.add_activity(activity)
            time.sleep(2)
        
        # 等待一段时间看预测结果
        print("等待预测结果...")
        time.sleep(30)
        
        # 显示状态
        status = pipeline.get_pipeline_status()
        print(f"管道状态: {json.dumps(status, indent=2, ensure_ascii=False)}")
        
    except KeyboardInterrupt:
        print("\n用户中断")
    finally:
        pipeline.stop_prediction_loop()
        print("测试完成") 