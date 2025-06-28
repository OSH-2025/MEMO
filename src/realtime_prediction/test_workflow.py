"""
测试版工作流 - 不需要真实模型，可以验证数据流和队列逻辑
"""

import os
import sys
import time
import json
import threading
import datetime
from typing import Dict, Any, Optional, List
from collections import deque

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'data_collection'))


class MockLLMPredictor:
    """模拟LLM预测器 - 用于测试"""
    
    def __init__(self, model_path: str = None, lora_path: str = None):
        """初始化模拟预测器"""
        print("🤖 使用模拟LLM预测器（测试模式）")
        self.model_path = model_path
        self.lora_path = lora_path
        
        # 预定义的测试预测结果
        self.mock_predictions = [
            "2025-05-22 08:31:15 - 访问网站 github.com 的页面 'MEMO/README.md at main · OSH-2025/MEMO'",
            "2025-05-22 08:31:45 - 切换到应用 VSCode - 'main.py'",
            "2025-05-22 08:32:10 - 访问网站 stackoverflow.com 的页面 'Python threading tutorial'",
            "2025-05-22 08:32:35 - 访问网站 docs.python.org 的页面 'Queue objects'",
            "2025-05-22 08:33:00 - 切换到应用 Chrome - 'GitHub'",
        ]
        self.prediction_index = 0
    
    def predict_next_activity(self, activity_sequence: str) -> str:
        """模拟预测下一个活动"""
        print(f"📝 输入活动序列长度: {len(activity_sequence.split(chr(10)))} 行")
        
        # 返回模拟预测结果
        prediction = self.mock_predictions[self.prediction_index % len(self.mock_predictions)]
        self.prediction_index += 1
        
        # 添加一些随机性
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        prediction = prediction.replace('2025-05-22 08:3', current_time[:16])
        
        return prediction


class ActivityQueue:
    """活动队列（复用原有逻辑）"""
    
    def __init__(self, max_size: int = 20, history_window: int = 100):
        self.max_size = max_size
        self.history_window = history_window
        self.activity_history = deque(maxlen=history_window)
        self.total_activities = 0
        self.last_activity_time = None
        
        print(f"📦 活动队列初始化完成 - 预测窗口: {max_size}, 历史窗口: {history_window}")
    
    def add_activity(self, activity: Dict[str, Any]):
        """添加新活动到队列"""
        if 'timestamp' not in activity:
            activity['timestamp'] = datetime.datetime.now().isoformat()
        
        self.activity_history.append(activity)
        self.total_activities += 1
        self.last_activity_time = activity['timestamp']
        
        print(f"➕ 添加活动: {activity.get('type', 'unknown')} - {activity.get('domain', activity.get('process_name', 'N/A'))}")
    
    def get_recent_activities(self, count: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取最近的活动序列"""
        if count is None:
            count = self.max_size
        
        recent_count = min(count, len(self.activity_history))
        if recent_count == 0:
            return []
        
        return list(self.activity_history)[-recent_count:]
    
    def format_activities_for_llm(self, activities: List[Dict[str, Any]]) -> str:
        """格式化活动序列为文本"""
        formatted_activities = []
        
        for activity in activities:
            formatted = self._format_single_activity(activity)
            if formatted:
                formatted_activities.append(formatted)
        
        return '\n'.join(formatted_activities)
    
    def _format_single_activity(self, activity: Dict[str, Any]) -> str:
        """格式化单个活动"""
        activity_type = activity.get('type', '')
        timestamp = activity.get('timestamp', '')
        
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
        
        return f"{formatted_time} - {activity_type} 活动"
    
    def get_stats(self) -> Dict[str, Any]:
        """获取队列统计信息"""
        return {
            'total_activities': self.total_activities,
            'current_history_size': len(self.activity_history),
            'last_activity_time': self.last_activity_time,
            'queue_size': len(self.activity_history)
        }


class TestActivityPipeline:
    """测试版活动预测管道"""
    
    def __init__(self, 
                 model_path: str = "mock",
                 lora_path: str = "mock", 
                 queue_size: int = 20,
                 prediction_interval: int = 30):
        self.prediction_interval = prediction_interval
        
        print("🧪 初始化测试版活动预测管道...")
        self.activity_queue = ActivityQueue(max_size=queue_size)
        self.llm_predictor = MockLLMPredictor(model_path, lora_path)
        
        self.running = False
        self.prediction_thread = None
        self.prediction_history = deque(maxlen=50)
        
        print("✅ 测试版活动预测管道初始化完成")
    
    def add_activity(self, activity: Dict[str, Any]):
        """添加新活动"""
        self.activity_queue.add_activity(activity)
    
    def start_prediction_loop(self):
        """启动预测循环"""
        if self.running:
            print("🔄 预测循环已在运行")
            return
        
        self.running = True
        self.prediction_thread = threading.Thread(target=self._prediction_loop, daemon=True)
        self.prediction_thread.start()
        print("🚀 预测循环已启动")
    
    def stop_prediction_loop(self):
        """停止预测循环"""
        self.running = False
        if self.prediction_thread:
            self.prediction_thread.join(timeout=5)
        print("⏹️  预测循环已停止")
    
    def _prediction_loop(self):
        """预测循环主函数"""
        while self.running:
            try:
                recent_activities = self.activity_queue.get_recent_activities()
                
                if len(recent_activities) >= 3:
                    activity_sequence = self.activity_queue.format_activities_for_llm(recent_activities)
                    prediction = self.llm_predictor.predict_next_activity(activity_sequence)
                    
                    prediction_record = {
                        'timestamp': datetime.datetime.now().isoformat(),
                        'input_activities': recent_activities[-3:],
                        'prediction': prediction,
                        'activity_count': len(recent_activities)
                    }
                    
                    self.prediction_history.append(prediction_record)
                    
                    print(f"\n🔮 [{datetime.datetime.now().strftime('%H:%M:%S')}] 活动预测:")
                    print(f"📊 基于最近 {len(recent_activities)} 个活动的预测:")
                    print(f"🎯 预测结果: {prediction}")
                    print("-" * 60)
                
                else:
                    print(f"⏳ [{datetime.datetime.now().strftime('%H:%M:%S')}] 活动数据不足（当前: {len(recent_activities)}/3），等待更多数据...")
                
                time.sleep(self.prediction_interval)
                
            except Exception as e:
                print(f"❌ 预测循环错误: {e}")
                time.sleep(5)
    
    def get_latest_prediction(self) -> Optional[Dict[str, Any]]:
        """获取最新预测结果"""
        if self.prediction_history:
            return self.prediction_history[-1]
        return None
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """获取管道状态"""
        queue_stats = self.activity_queue.get_stats()
        
        return {
            'running': self.running,
            'queue_stats': queue_stats,
            'prediction_count': len(self.prediction_history),
            'latest_prediction_time': self.prediction_history[-1]['timestamp'] if self.prediction_history else None
        }


def demo_test_workflow():
    """演示测试工作流"""
    print("=" * 60)
    print("🧪 启动测试版实时活动预测演示")
    print("=" * 60)
    
    # 创建测试管道
    pipeline = TestActivityPipeline(prediction_interval=10)
    
    # 示例活动数据
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
        },
        {
            'type': 'window_focus',
            'process_name': 'Code.exe',
            'window_title': 'realtime_pipeline.py - Visual Studio Code'
        },
        {
            'type': 'browser_history',
            'domain': 'github.com',
            'title': 'MEMO/src at main · OSH-2025/MEMO'
        }
    ]
    
    try:
        # 启动预测循环
        pipeline.start_prediction_loop()
        
        print("📝 逐步添加测试活动数据...\n")
        
        # 逐步添加活动
        for i, activity in enumerate(test_activities, 1):
            print(f"📌 添加第 {i} 个活动:")
            pipeline.add_activity(activity)
            
            # 显示当前状态
            status = pipeline.get_pipeline_status()
            print(f"📈 当前队列中有 {status['queue_stats']['current_history_size']} 个活动")
            
            print("-" * 30)
            time.sleep(3)
        
        print("\n🔄 等待自动预测结果...")
        print("系统将每10秒自动进行一次预测\n")
        
        # 等待并显示预测结果
        for i in range(5):
            time.sleep(10)
            latest = pipeline.get_latest_prediction()
            if latest:
                print(f"🆕 [自动预测 {i+1}] {latest['timestamp']}")
                print(f"🎯 预测: {latest['prediction']}")
                print()
            else:
                print(f"⏳ [自动预测 {i+1}] 等待预测结果...")
    
    except KeyboardInterrupt:
        print("\n👋 用户中断演示")
    
    finally:
        pipeline.stop_prediction_loop()
        
        # 显示最终统计
        final_status = pipeline.get_pipeline_status()
        print("\n" + "=" * 60)
        print("📊 最终统计:")
        print(f"   总活动数: {final_status['queue_stats']['total_activities']}")
        print(f"   预测次数: {final_status['prediction_count']}")
        print(f"   队列大小: {final_status['queue_stats']['current_history_size']}")
        print("=" * 60)
        print("🎉 测试演示完成！")


if __name__ == "__main__":
    print("🚀 测试版实时活动预测系统")
    print("这个版本不需要真实的LLM模型，可以验证工作流逻辑")
    print()
    
    try:
        demo_test_workflow()
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc() 