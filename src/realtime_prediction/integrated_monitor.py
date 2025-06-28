"""
集成活动监控器 - 连接monitor和实时预测管道
"""

import os
import sys
import time
import threading
from typing import Dict, Any, Optional

# 添加路径以导入原始monitor
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'data_collection'))

from activity_monitor import ActivityMonitor
from realtime_pipeline import RealTimeActivityPipeline


class IntegratedActivityMonitor(ActivityMonitor):
    """集成的活动监控器，同时支持文件保存和实时预测"""
    
    def __init__(self, 
                 output_dir: str = "activity_data",
                 enable_realtime_prediction: bool = True,
                 model_path: str = './LLM-Research/Meta-Llama-3___1-8B-Instruct',
                 lora_path: str = './output/llama3_1_instruct_lora/checkpoint-138',
                 prediction_interval: int = 30):
        """初始化集成监控器
        
        Args:
            output_dir: 保存活动数据的目录
            enable_realtime_prediction: 是否启用实时预测
            model_path: LLM模型路径
            lora_path: LoRA权重路径
            prediction_interval: 预测间隔（秒）
        """
        # 初始化基础监控器
        super().__init__(output_dir)
        
        self.enable_realtime_prediction = enable_realtime_prediction
        self.realtime_pipeline = None
        
        # 如果启用实时预测，初始化预测管道
        if enable_realtime_prediction:
            try:
                print("正在初始化实时预测管道...")
                self.realtime_pipeline = RealTimeActivityPipeline(
                    model_path=model_path,
                    lora_path=lora_path,
                    prediction_interval=prediction_interval
                )
                print("实时预测管道初始化完成")
            except Exception as e:
                print(f"实时预测管道初始化失败: {e}")
                print("将以文件模式运行")
                self.enable_realtime_prediction = False
                self.realtime_pipeline = None
    
    def _add_activity_to_pipeline(self, activity: Dict[str, Any]):
        """将活动添加到实时预测管道
        
        Args:
            activity: 活动数据
        """
        if self.enable_realtime_prediction and self.realtime_pipeline:
            try:
                self.realtime_pipeline.add_activity(activity)
            except Exception as e:
                print(f"添加活动到预测管道失败: {e}")
    
    def start(self):
        """启动监控器和预测管道"""
        print("启动集成活动监控器...")
        
        # 如果启用实时预测，启动预测循环
        if self.enable_realtime_prediction and self.realtime_pipeline:
            self.realtime_pipeline.start_prediction_loop()
        
        # 启动基础监控器
        try:
            self.running = True
            print("开始监控用户活动...")
            print("按 Ctrl+C 停止监控")
            
            # 更新GUI进程列表
            self._update_gui_processes()
            
            # 启动文件操作监控线程
            if not self.file_monitor_thread:
                self.file_monitor_thread = threading.Thread(target=self._monitor_file_operations, daemon=True)
                self.file_monitor_thread.start()
            
            while self.running:
                try:
                    # 更新时间上下文
                    self._update_time_context()
                    
                    # 获取当前活跃窗口信息
                    window_info = self._get_active_window_info()
                    
                    # 检查窗口焦点变化
                    current_time = time.time()
                    if (window_info and 
                        window_info.get("window_title") != self.last_active_window and
                        current_time - self.last_window_focus_time >= self.min_window_focus_interval):
                        
                        self.last_active_window = window_info.get("window_title")
                        self.last_window_focus_time = current_time
                        
                        # 检查记录频率
                        if self._check_frequency_limit("window_focus"):
                            activity = {
                                "type": "window_focus",
                                **window_info
                            }
                            self.activities.append(activity)
                            
                            # 添加到实时管道
                            self._add_activity_to_pipeline(activity)
                        
                        # 跟踪应用使用时长
                        self._track_app_usage(window_info)
                    
                    # 获取进程启动和关闭信息
                    process_events = self._monitor_processes()
                    self.activities.extend(process_events)
                    
                    # 将进程事件添加到实时管道
                    for event in process_events:
                        self._add_activity_to_pipeline(event)
                    
                    # 获取浏览器历史
                    browser_history = self._get_browser_history()
                    
                    # 筛选浏览器历史，应用频率限制
                    filtered_history = []
                    for entry in browser_history:
                        if self._check_frequency_limit("browser_history"):
                            filtered_history.append(entry)
                            # 添加到实时管道
                            self._add_activity_to_pipeline(entry)
                    
                    self.activities.extend(filtered_history)
                    
                    # 检查是否需要保存数据
                    current_time = time.time()
                    if current_time - self.last_save_time > self.save_interval:
                        self.save_data()
                        self.last_save_time = current_time
                    
                    # 暂停一小段时间
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"监控循环出错: {e}")
                    time.sleep(5)  # 出错后等待时间更长
        
        except KeyboardInterrupt:
            print("\n用户中断，停止监控")
            self.stop()
    
    def stop(self):
        """停止监控器和预测管道"""
        print("停止集成活动监控器...")
        
        # 停止预测管道
        if self.enable_realtime_prediction and self.realtime_pipeline:
            self.realtime_pipeline.stop_prediction_loop()
        
        # 调用基础监控器的停止方法
        super().stop()
        
        print("集成活动监控器已停止")
    
    def get_prediction_status(self) -> Optional[Dict[str, Any]]:
        """获取预测管道状态
        
        Returns:
            预测管道状态，如果未启用则返回None
        """
        if self.enable_realtime_prediction and self.realtime_pipeline:
            return self.realtime_pipeline.get_pipeline_status()
        return None
    
    def get_latest_prediction(self) -> Optional[Dict[str, Any]]:
        """获取最新的预测结果
        
        Returns:
            最新的预测结果，如果未启用或无预测则返回None
        """
        if self.enable_realtime_prediction and self.realtime_pipeline:
            return self.realtime_pipeline.get_latest_prediction()
        return None


def create_integrated_monitor(**kwargs) -> IntegratedActivityMonitor:
    """创建集成活动监控器的工厂函数
    
    Args:
        **kwargs: 传递给IntegratedActivityMonitor的参数
        
    Returns:
        配置好的集成监控器实例
    """
    return IntegratedActivityMonitor(**kwargs)


if __name__ == "__main__":
    try:
        print("启动集成活动监控和预测系统...")
        
        # 创建集成监控器
        monitor = create_integrated_monitor(
            enable_realtime_prediction=True,
            prediction_interval=20  # 每20秒预测一次
        )
        
        # 启动监控
        monitor.start()
        
    except KeyboardInterrupt:
        print("\n监控已停止")
    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc() 