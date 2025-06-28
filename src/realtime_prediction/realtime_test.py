"""
实时LLM预测测试 - 从实时活动队列获取数据进行预测
"""

import os
import sys
import time
import json
from typing import Optional, Dict, Any

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'data_collection'))

from realtime_pipeline import create_realtime_pipeline


class RealTimeActivityPredictor:
    """实时活动预测器接口类"""
    
    def __init__(self, 
                 model_path: str = './LLM-Research/Meta-Llama-3___1-8B-Instruct',
                 lora_path: str = './output/llama3_1_instruct_lora/checkpoint-138',
                 prediction_interval: int = 20,
                 min_activities: int = 3):
        """初始化实时预测器
        
        Args:
            model_path: 基础模型路径
            lora_path: LoRA权重路径  
            prediction_interval: 预测间隔（秒）
            min_activities: 进行预测所需的最少活动数量
        """
        self.min_activities = min_activities
        self.prediction_interval = prediction_interval
        
        print("正在初始化实时活动预测器...")
        
        # 创建实时管道
        self.pipeline = create_realtime_pipeline(
            model_path=model_path,
            lora_path=lora_path,
            prediction_interval=prediction_interval
        )
        
        print("实时活动预测器初始化完成")
    
    def add_activity(self, activity: Dict[str, Any]):
        """添加活动到预测队列
        
        Args:
            activity: 活动数据字典
        """
        self.pipeline.add_activity(activity)
        print(f"已添加活动: {activity.get('type', 'unknown')} - {activity.get('timestamp', 'no timestamp')}")
    
    def start_prediction(self):
        """开始实时预测"""
        print("开始实时活动预测...")
        self.pipeline.start_prediction_loop()
    
    def stop_prediction(self):
        """停止实时预测"""
        print("停止实时活动预测...")
        self.pipeline.stop_prediction_loop()
    
    def get_current_activities(self) -> list:
        """获取当前的活动序列"""
        return self.pipeline.activity_queue.get_recent_activities()
    
    def get_formatted_activities(self) -> str:
        """获取格式化的活动序列"""
        activities = self.get_current_activities()
        return self.pipeline.activity_queue.format_activities_for_llm(activities)
    
    def predict_manually(self) -> Optional[str]:
        """手动进行一次预测
        
        Returns:
            预测结果，如果数据不足则返回None
        """
        activities = self.get_current_activities()
        
        if len(activities) < self.min_activities:
            print(f"活动数据不足，当前: {len(activities)}, 需要: {self.min_activities}")
            return None
        
        # 格式化活动序列
        activity_sequence = self.pipeline.activity_queue.format_activities_for_llm(activities)
        
        print("\n当前活动序列:")
        print(activity_sequence)
        print("\n正在进行预测...")
        
        # 进行预测
        prediction = self.pipeline.llm_predictor.predict_next_activity(activity_sequence)
        
        print(f"\n预测结果: {prediction}")
        return prediction
    
    def get_status(self) -> Dict[str, Any]:
        """获取预测器状态"""
        return self.pipeline.get_pipeline_status()
    
    def get_latest_prediction(self) -> Optional[Dict[str, Any]]:
        """获取最新的预测结果"""
        return self.pipeline.get_latest_prediction()


def demo_with_sample_data():
    """使用示例数据演示实时预测功能"""
    
    # 创建预测器
    predictor = RealTimeActivityPredictor(prediction_interval=15)
    
    # 示例活动数据（和原test.py中相同的数据）
    sample_activities = [
        {
            'type': 'browser_history',
            'domain': 'www.douban.com',
            'title': '【盘个剧本押个C】【Game of Thrones】1st episode 《All men must die》',
            'url': 'https://www.douban.com/group/topic/12345/'
        },
        {
            'type': 'browser_history', 
            'domain': 'github.com',
            'title': 'self-llm/examples/AMchat-高等数学 at master · datawhalechina/self-llm',
            'url': 'https://github.com/datawhalechina/self-llm/tree/master/examples/AMchat-%E9%AB%98%E7%AD%89%E6%95%B0%E5%AD%A6'
        },
        {
            'type': 'browser_history',
            'domain': 'github.com', 
            'title': 'MEMO/feasibility_report/Fine-tuning of LLM.md at main · OSH-2025/MEMO',
            'url': 'https://github.com/OSH-2025/MEMO/blob/main/feasibility_report/Fine-tuning%20of%20LLM.md'
        },
        {
            'type': 'browser_history',
            'domain': 'github.com',
            'title': 'MEMO/src at main · OSH-2025/MEMO',
            'url': 'https://github.com/OSH-2025/MEMO/tree/main/src'
        }
    ]
    
    try:
        print("=== 实时活动预测演示 ===\n")
        
        # 启动自动预测循环
        predictor.start_prediction()
        
        print("逐步添加示例活动数据...\n")
        
        # 逐步添加活动
        for i, activity in enumerate(sample_activities, 1):
            print(f"添加第 {i} 个活动:")
            predictor.add_activity(activity)
            
            # 显示当前状态
            status = predictor.get_status()
            print(f"当前队列中有 {status['queue_stats']['current_history_size']} 个活动")
            
            # 如果数据足够，进行手动预测
            if i >= 3:
                print("\n尝试手动预测:")
                prediction = predictor.predict_manually()
                if prediction:
                    print(f"手动预测结果: {prediction}")
            
            print("-" * 50)
            time.sleep(3)  # 等待3秒再添加下一个活动
        
        print("\n等待自动预测结果...")
        print("系统将每15秒自动进行一次预测\n")
        
        # 等待一段时间观察自动预测
        for i in range(3):
            time.sleep(15)
            latest = predictor.get_latest_prediction()
            if latest:
                print(f"\n[自动预测 {i+1}] {latest['timestamp']}")
                print(f"预测: {latest['prediction']}")
            else:
                print(f"\n[自动预测 {i+1}] 暂无预测结果")
    
    except KeyboardInterrupt:
        print("\n用户中断演示")
    
    finally:
        predictor.stop_prediction()
        print("演示结束")


def interactive_mode():
    """交互模式 - 手动添加活动并查看预测"""
    
    predictor = RealTimeActivityPredictor()
    
    print("=== 交互式实时预测模式 ===")
    print("您可以手动添加活动并查看预测结果")
    print("命令:")
    print("  add - 添加浏览器活动")
    print("  predict - 手动进行预测")
    print("  status - 查看状态")
    print("  activities - 查看当前活动序列")
    print("  start - 启动自动预测")
    print("  stop - 停止自动预测")
    print("  quit - 退出")
    print()
    
    try:
        while True:
            command = input("请输入命令: ").strip().lower()
            
            if command == 'add':
                print("添加浏览器活动:")
                domain = input("  网站域名: ").strip()
                title = input("  页面标题: ").strip()
                
                if domain and title:
                    activity = {
                        'type': 'browser_history',
                        'domain': domain,
                        'title': title
                    }
                    predictor.add_activity(activity)
                    print("活动已添加")
                else:
                    print("域名和标题不能为空")
            
            elif command == 'predict':
                prediction = predictor.predict_manually()
                if not prediction:
                    print("数据不足或预测失败")
            
            elif command == 'status':
                status = predictor.get_status()
                print(f"状态: {json.dumps(status, indent=2, ensure_ascii=False)}")
            
            elif command == 'activities':
                formatted = predictor.get_formatted_activities()
                if formatted:
                    print("当前活动序列:")
                    print(formatted)
                else:
                    print("暂无活动数据")
            
            elif command == 'start':
                predictor.start_prediction()
            
            elif command == 'stop':
                predictor.stop_prediction()
            
            elif command == 'quit':
                break
            
            else:
                print("未知命令")
            
            print()
    
    except KeyboardInterrupt:
        print("\n用户中断")
    
    finally:
        predictor.stop_prediction()
        print("交互模式结束")


if __name__ == "__main__":
    print("实时LLM活动预测系统")
    print("选择运行模式:")
    print("1. 演示模式 (使用示例数据)")
    print("2. 交互模式 (手动添加活动)")
    
    try:
        choice = input("请选择 (1 或 2): ").strip()
        
        if choice == '1':
            demo_with_sample_data()
        elif choice == '2':
            interactive_mode()
        else:
            print("无效选择，启动演示模式...")
            demo_with_sample_data()
    
    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc() 