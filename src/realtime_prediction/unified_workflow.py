"""
统一工作流协调器 - 整合monitor、analyzer和实时LLM预测
"""

import os
import sys
import time
import json
import threading
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'data_collection'))

from integrated_monitor import create_integrated_monitor
from realtime_pipeline import create_realtime_pipeline


class UnifiedWorkflow:
    """统一工作流协调器"""
    
    def __init__(self,
                 model_path: str = './LLM-Research/Meta-Llama-3___1-8B-Instruct',
                 lora_path: str = './output/llama3_1_instruct_lora/checkpoint-138',
                 data_dir: str = "activity_data",
                 prediction_interval: int = 30,
                 enable_monitoring: bool = True,
                 enable_prediction: bool = True):
        """初始化统一工作流
        
        Args:
            model_path: LLM模型路径
            lora_path: LoRA权重路径
            data_dir: 数据保存目录
            prediction_interval: 预测间隔（秒）
            enable_monitoring: 是否启用活动监控
            enable_prediction: 是否启用实时预测
        """
        self.model_path = model_path
        self.lora_path = lora_path
        self.data_dir = data_dir
        self.prediction_interval = prediction_interval
        self.enable_monitoring = enable_monitoring
        self.enable_prediction = enable_prediction
        
        # 组件
        self.monitor = None
        self.pipeline = None
        
        # 状态
        self.running = False
        self.status_update_interval = 60  # 每分钟输出一次状态
        self.status_thread = None
        
        print("统一工作流协调器初始化中...")
        self._initialize_components()
        print("统一工作流协调器初始化完成")
    
    def _initialize_components(self):
        """初始化各组件"""
        
        # 确保数据目录存在
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        
        if self.enable_monitoring and self.enable_prediction:
            # 集成模式：使用集成监控器
            print("初始化集成监控和预测模式...")
            self.monitor = create_integrated_monitor(
                output_dir=self.data_dir,
                enable_realtime_prediction=True,
                model_path=self.model_path,
                lora_path=self.lora_path,
                prediction_interval=self.prediction_interval
            )
            
        elif self.enable_monitoring:
            # 仅监控模式
            print("初始化仅监控模式...")
            from activity_monitor import ActivityMonitor
            self.monitor = ActivityMonitor(output_dir=self.data_dir)
            
        elif self.enable_prediction:
            # 仅预测模式
            print("初始化仅预测模式...")
            self.pipeline = create_realtime_pipeline(
                model_path=self.model_path,
                lora_path=self.lora_path,
                prediction_interval=self.prediction_interval
            )
    
    def start(self):
        """启动工作流"""
        if self.running:
            print("工作流已在运行")
            return
        
        print("启动统一工作流...")
        self.running = True
        
        try:
            if self.enable_monitoring:
                # 启动监控器（如果是集成监控器，会自动启动预测）
                print("启动活动监控...")
                monitor_thread = threading.Thread(target=self.monitor.start, daemon=True)
                monitor_thread.start()
                
            elif self.enable_prediction and self.pipeline:
                # 仅启动预测管道
                print("启动实时预测...")
                self.pipeline.start_prediction_loop()
            
            # 启动状态更新线程
            self.status_thread = threading.Thread(target=self._status_update_loop, daemon=True)
            self.status_thread.start()
            
            print("统一工作流已启动")
            print("按 Ctrl+C 停止工作流")
            
            # 主循环
            self._main_loop()
            
        except KeyboardInterrupt:
            print("\n用户中断，停止工作流...")
            self.stop()
        except Exception as e:
            print(f"工作流运行错误: {e}")
            self.stop()
    
    def stop(self):
        """停止工作流"""
        if not self.running:
            return
        
        print("停止统一工作流...")
        self.running = False
        
        # 停止监控器
        if self.monitor:
            self.monitor.stop()
        
        # 停止预测管道
        if self.pipeline:
            self.pipeline.stop_prediction_loop()
        
        print("统一工作流已停止")
    
    def _main_loop(self):
        """主循环 - 保持工作流运行"""
        while self.running:
            time.sleep(1)
    
    def _status_update_loop(self):
        """状态更新循环"""
        while self.running:
            try:
                self._print_status()
                time.sleep(self.status_update_interval)
            except Exception as e:
                print(f"状态更新错误: {e}")
                time.sleep(10)
    
    def _print_status(self):
        """打印当前状态"""
        print(f"\n=== 工作流状态 ({time.strftime('%H:%M:%S')}) ===")
        
        if hasattr(self.monitor, 'get_prediction_status'):
            # 集成监控器状态
            prediction_status = self.monitor.get_prediction_status()
            if prediction_status:
                queue_stats = prediction_status['queue_stats']
                print(f"监控状态: 运行中")
                print(f"活动队列: {queue_stats['current_history_size']} 个活动")
                print(f"预测状态: {'运行中' if prediction_status['running'] else '已停止'}")
                print(f"总预测次数: {prediction_status['prediction_count']}")
                
                # 显示最新预测
                latest_prediction = self.monitor.get_latest_prediction()
                if latest_prediction:
                    print(f"最新预测: {latest_prediction['prediction'][:100]}...")
                else:
                    print("最新预测: 暂无")
        
        elif self.monitor:
            # 仅监控模式
            print(f"监控状态: 运行中")
            print(f"已收集活动: {len(self.monitor.activities)} 个")
        
        elif self.pipeline:
            # 仅预测模式
            status = self.pipeline.get_pipeline_status()
            queue_stats = status['queue_stats']
            print(f"预测状态: {'运行中' if status['running'] else '已停止'}")
            print(f"活动队列: {queue_stats['current_history_size']} 个活动")
            print(f"总预测次数: {status['prediction_count']}")
        
        print("=" * 40)
    
    def add_test_activity(self, activity: Dict[str, Any]):
        """添加测试活动（用于测试目的）
        
        Args:
            activity: 活动数据
        """
        if hasattr(self.monitor, 'realtime_pipeline') and self.monitor.realtime_pipeline:
            self.monitor.realtime_pipeline.add_activity(activity)
        elif self.pipeline:
            self.pipeline.add_activity(activity)
        else:
            print("没有可用的活动队列")
    
    def get_status(self) -> Dict[str, Any]:
        """获取完整状态信息
        
        Returns:
            状态信息字典
        """
        status = {
            'running': self.running,
            'enable_monitoring': self.enable_monitoring,
            'enable_prediction': self.enable_prediction,
            'data_dir': self.data_dir
        }
        
        if hasattr(self.monitor, 'get_prediction_status'):
            status['prediction_status'] = self.monitor.get_prediction_status()
        elif self.pipeline:
            status['prediction_status'] = self.pipeline.get_pipeline_status()
        
        return status


def create_workflow_from_config(config_file: str) -> UnifiedWorkflow:
    """从配置文件创建工作流
    
    Args:
        config_file: 配置文件路径
        
    Returns:
        配置好的工作流实例
    """
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    return UnifiedWorkflow(**config)


def main():
    """主函数 - 命令行接口"""
    parser = argparse.ArgumentParser(description='统一活动监控和预测工作流')
    
    parser.add_argument('--model-path', 
                       default='./LLM-Research/Meta-Llama-3___1-8B-Instruct',
                       help='LLM模型路径')
    
    parser.add_argument('--lora-path', 
                       default='./output/llama3_1_instruct_lora/checkpoint-138',
                       help='LoRA权重路径')
    
    parser.add_argument('--data-dir', 
                       default='activity_data',
                       help='数据保存目录')
    
    parser.add_argument('--prediction-interval', 
                       type=int, default=30,
                       help='预测间隔（秒）')
    
    parser.add_argument('--monitor-only', 
                       action='store_true',
                       help='仅启用监控，不进行预测')
    
    parser.add_argument('--predict-only', 
                       action='store_true',
                       help='仅启用预测，不进行监控')
    
    parser.add_argument('--config', 
                       help='从配置文件加载参数')
    
    parser.add_argument('--test-mode', 
                       action='store_true',
                       help='测试模式，添加示例数据')
    
    args = parser.parse_args()
    
    try:
        if args.config:
            # 从配置文件创建
            workflow = create_workflow_from_config(args.config)
        else:
            # 从命令行参数创建
            enable_monitoring = not args.predict_only
            enable_prediction = not args.monitor_only
            
            workflow = UnifiedWorkflow(
                model_path=args.model_path,
                lora_path=args.lora_path,
                data_dir=args.data_dir,
                prediction_interval=args.prediction_interval,
                enable_monitoring=enable_monitoring,
                enable_prediction=enable_prediction
            )
        
        # 测试模式：添加示例数据
        if args.test_mode:
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
            
            # 启动工作流后添加测试数据
            def add_test_data():
                time.sleep(5)  # 等待工作流启动
                print("\n添加测试数据...")
                for activity in test_activities:
                    workflow.add_test_activity(activity)
                    time.sleep(2)
                print("测试数据添加完成\n")
            
            test_thread = threading.Thread(target=add_test_data, daemon=True)
            test_thread.start()
        
        # 启动工作流
        workflow.start()
        
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 