"""
活动分析脚本 - 分析用户文件操作序列
对收集的用户活动数据进行分析，生成可供大语言模型学习的训练数据集
"""

import os
import json
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import List, Dict, Any, Tuple, Optional
import re
from pathlib import Path
import matplotlib

# 设置中文字体
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Bitstream Vera Sans', 'Arial', 'sans-serif']
matplotlib.rcParams['axes.unicode_minus'] = False  # 正确显示负号

class ActivityAnalyzer:
    """分析用户活动数据并生成训练数据集"""
    
    def __init__(self, data_dir: str = "activity_data", output_dir: str = "dataset"):
        """初始化活动分析器
        
        Args:
            data_dir: 保存活动数据的目录
            output_dir: 保存生成的数据集的目录
        """
        self.data_dir = data_dir
        self.output_dir = output_dir
        
        # 确保输出目录存在
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # 原始活动数据
        self.activities = []
        
        # 按时间分段的活动序列
        self.activity_sequences = []
        
    def load_data(self):
        """加载所有活动数据文件"""
        print("加载活动数据...")
        
        # 查找所有活动数据文件
        data_files = glob.glob(os.path.join(self.data_dir, "activity_data_*.json"))
        if not data_files:
            raise FileNotFoundError(f"在 {self.data_dir} 目录下未找到任何活动数据文件")
        
        # 加载所有数据
        activities = []
        for file_path in sorted(data_files):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    activities.extend(data)
                    print(f"从 {file_path} 加载了 {len(data)} 条记录")
            except Exception as e:
                print(f"加载文件 {file_path} 时出错: {e}")
        
        # 按时间戳排序
        self.activities = sorted(activities, key=lambda x: x.get('timestamp', ''))
        
        print(f"共加载了 {len(self.activities)} 条活动记录")
        return self.activities
    
    def preprocess_data(self):
        """预处理活动数据
        
        处理空值、标准化时间戳等
        """
        print("预处理活动数据...")
        
        # 过滤掉没有时间戳的记录
        self.activities = [a for a in self.activities if 'timestamp' in a]
        
        # 确保所有记录都有类型字段
        for activity in self.activities:
            if 'type' not in activity:
                activity['type'] = 'unknown'
        
        # 转换时间戳为datetime对象，便于后续处理
        for activity in self.activities:
            try:
                activity['datetime'] = datetime.fromisoformat(activity['timestamp'])
            except:
                # 如果时间戳格式有问题，使用当前时间
                activity['datetime'] = datetime.now()
        
        # 重新按时间排序
        self.activities = sorted(self.activities, key=lambda x: x['datetime'])
        
        print(f"预处理后剩余 {len(self.activities)} 条记录")
        return self.activities
    
    def segment_by_time(self, time_window: int = 30):
        """将活动按时间窗口分段
        
        Args:
            time_window: 时间窗口大小(分钟)
        
        Returns:
            List of activity sequences
        """
        print(f"按 {time_window} 分钟时间窗口分段活动序列...")
        
        if not self.activities:
            return []
        
        sequences = []
        current_seq = []
        last_time = None
        
        for activity in self.activities:
            current_time = activity['datetime']
            
            # 如果是第一个活动或者与上一个活动的时间间隔小于窗口，加入当前序列
            if last_time is None or (current_time - last_time).total_seconds() < time_window * 60:
                current_seq.append(activity)
            else:
                # 如果时间间隔大于窗口，开始新序列
                if len(current_seq) > 1:  # 只有包含多个活动的序列才有意义
                    sequences.append(current_seq)
                current_seq = [activity]
            
            last_time = current_time
        
        # 添加最后一个序列
        if len(current_seq) > 1:
            sequences.append(current_seq)
        
        self.activity_sequences = sequences
        print(f"共生成 {len(sequences)} 个活动序列")
        
        return sequences
    
    def segment_by_session(self, inactive_threshold: int = 30):
        """按用户会话分段
        
        Args:
            inactive_threshold: 不活跃阈值(分钟)，超过此时间无活动视为会话结束
        
        Returns:
            List of activity sequences
        """
        print(f"按用户会话分段活动序列(不活跃阈值={inactive_threshold}分钟)...")
        
        if not self.activities:
            return []
        
        sequences = []
        current_seq = []
        
        for i, activity in enumerate(self.activities):
            current_time = activity['datetime']
            
            # 第一个活动，开始新序列
            if i == 0:
                current_seq = [activity]
                continue
            
            # 计算与上一个活动的时间差
            time_diff = (current_time - self.activities[i-1]['datetime']).total_seconds() / 60
            
            # 如果时间差小于阈值，继续当前序列
            if time_diff < inactive_threshold:
                current_seq.append(activity)
            else:
                # 时间差大于阈值，结束当前序列，开始新序列
                if len(current_seq) > 1:
                    sequences.append(current_seq)
                current_seq = [activity]
        
        # 添加最后一个序列
        if len(current_seq) > 1:
            sequences.append(current_seq)
        
        self.activity_sequences = sequences
        print(f"共生成 {len(sequences)} 个活动会话")
        
        return sequences
    
    def generate_sequence_dataset(self, window_size: int = 5, step_size: int = 1):
        """生成序列预测数据集
        
        Args:
            window_size: 用于预测的窗口大小（活动数量）
            step_size: 滑动窗口的步长
            
        Returns:
            预测数据集
        """
        print(f"生成序列预测数据集(窗口大小={window_size}, 步长={step_size})...")
        
        dataset = []
        
        for sequence in self.activity_sequences:
            if len(sequence) <= window_size:
                continue
                
            # 生成滑动窗口
            for i in range(0, len(sequence) - window_size, step_size):
                input_seq = sequence[i:i+window_size]
                target = sequence[i+window_size]
                
                # 格式化为可训练的数据
                input_formatted = self._format_sequence(input_seq)
                target_formatted = self._format_activity(target)
                
                dataset.append({
                    "input_sequence": input_formatted,
                    "target": target_formatted
                })
        
        print(f"生成了 {len(dataset)} 条训练数据")
        return dataset
    
    def _format_sequence(self, sequence: List[Dict[str, Any]]) -> List[str]:
        """格式化活动序列为字符串列表
        
        Args:
            sequence: 活动序列
            
        Returns:
            格式化后的字符串列表
        """
        formatted = []
        
        for activity in sequence:
            formatted.append(self._format_activity(activity))
        
        return formatted
    
    def _format_activity(self, activity: Dict[str, Any]) -> str:
        """将单个活动格式化为字符串
        
        Args:
            activity: 活动数据
            
        Returns:
            格式化后的字符串
        """
        activity_type = activity.get('type', 'unknown')
        time_str = activity.get('datetime').strftime('%H:%M:%S')
        
        if activity_type == 'window_focus':
            return f"{time_str} [窗口] {activity.get('window_title', '')} ({activity.get('process_name', '')})"
        
        elif activity_type == 'browser_history':
            url = activity.get('url', '')
            # 简化URL
            simplified_url = self._simplify_url(url)
            return f"{time_str} [浏览器] {simplified_url} - {activity.get('title', '')}"
        
        elif activity_type == 'process_start':
            return f"{time_str} [启动] {activity.get('process_name', '')} ({activity.get('executable_path', '')})"
        
        elif activity_type == 'process_end':
            return f"{time_str} [结束] {activity.get('process_name', '')} (进程ID: {activity.get('process_id', '')})"
        
        elif activity_type == 'file_access':
            return f"{time_str} [文件] {activity.get('path', '')}"
        
        else:
            return f"{time_str} [{activity_type}] {json.dumps(activity, ensure_ascii=False)}"
    
    def _simplify_url(self, url: str) -> str:
        """简化URL，去除参数和锚点
        
        Args:
            url: 原始URL
            
        Returns:
            简化后的URL
        """
        # 去除协议头
        url = re.sub(r'^https?://', '', url)
        
        # 去除URL参数和锚点
        url = re.sub(r'\?.*$', '', url)
        url = re.sub(r'#.*$', '', url)
        
        return url
    
    def analyze_activity_patterns(self):
        """分析活动模式
        
        Returns:
            包含分析结果的字典
        """
        print("分析活动模式...")
        
        if not self.activities:
            return {}
        
        # 活动类型分布
        activity_types = Counter([a.get('type', 'unknown') for a in self.activities])
        
        # 按小时分析活动频率
        hourly_activity = defaultdict(int)
        for activity in self.activities:
            hour = activity['datetime'].hour
            hourly_activity[hour] += 1
        
        # 找出最常访问的网站和应用
        top_websites = Counter()
        top_apps = Counter()
        
        for activity in self.activities:
            if activity.get('type') == 'browser_history':
                url = activity.get('url', '')
                domain = re.sub(r'^https?://', '', url)
                domain = domain.split('/')[0]
                top_websites[domain] += 1
                
            elif activity.get('type') == 'window_focus':
                app = activity.get('process_name', '')
                if app:
                    top_apps[app] += 1
        
        # 计算平均会话长度
        avg_session_length = 0
        if self.activity_sequences:
            session_lengths = []
            for seq in self.activity_sequences:
                if len(seq) >= 2:
                    start = seq[0]['datetime']
                    end = seq[-1]['datetime']
                    duration = (end - start).total_seconds() / 60  # 分钟
                    session_lengths.append(duration)
            
            if session_lengths:
                avg_session_length = sum(session_lengths) / len(session_lengths)
        
        analysis = {
            "activity_type_distribution": dict(activity_types),
            "hourly_activity": dict(hourly_activity),
            "top_websites": dict(top_websites.most_common(10)),
            "top_apps": dict(top_apps.most_common(10)),
            "total_activities": len(self.activities),
            "total_sessions": len(self.activity_sequences),
            "avg_session_length_minutes": avg_session_length
        }
        
        return analysis
    
    def visualize_activity_patterns(self, output_path: str = None):
        """可视化活动模式
        
        Args:
            output_path: 输出图表的路径，如果为None则显示图表
        """
        print("可视化活动模式...")
        
        if not self.activities:
            print("没有数据可供可视化")
            return
        
        analysis = self.analyze_activity_patterns()
        
        # 设置样式
        plt.style.use('ggplot')
        
        # 创建图表
        fig = plt.figure(figsize=(15, 12))
        plt.suptitle('用户活动模式分析', fontsize=16, y=0.98)
        
        # 1. 活动类型分布
        ax1 = fig.add_subplot(2, 2, 1)
        activity_types = analysis['activity_type_distribution']
        types = list(activity_types.keys())
        counts = list(activity_types.values())
        
        # 简化标签，避免显示问题
        simplified_types = []
        for t in types:
            if len(t) > 15:
                simplified_types.append(t[:12] + '...')
            else:
                simplified_types.append(t)
                
        ax1.pie(counts, labels=simplified_types, autopct='%1.1f%%', startangle=90)
        ax1.set_title('活动类型分布', fontsize=12)
        
        # 2. 小时活动频率
        ax2 = fig.add_subplot(2, 2, 2)
        hourly_activity = analysis['hourly_activity']
        hours = list(range(24))
        activity_counts = [hourly_activity.get(h, 0) for h in hours]
        bars = ax2.bar(hours, activity_counts)
        
        # 为每个条形添加数值标签
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax2.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        '%d' % int(height), ha='center', va='bottom', fontsize=8)
                
        ax2.set_xlabel('小时', fontsize=10)
        ax2.set_ylabel('活动数量', fontsize=10)
        ax2.set_title('小时活动频率', fontsize=12)
        ax2.set_xticks(hours)
        ax2.set_xticklabels([str(h) for h in hours], fontsize=8, rotation=45)
        
        # 3. 最常访问的网站
        ax3 = fig.add_subplot(2, 2, 3)
        top_websites = analysis['top_websites']
        if top_websites:
            websites = list(top_websites.keys())[:10]  # 最多显示前10个
            website_counts = list(top_websites.values())[:10]
            
            # 截断过长的网站名
            simplified_websites = []
            for site in websites:
                if len(site) > 25:
                    simplified_websites.append(site[:22] + '...')
                else:
                    simplified_websites.append(site)
            
            y_pos = np.arange(len(simplified_websites))
            bars = ax3.barh(y_pos, website_counts)
            ax3.set_yticks(y_pos)
            ax3.set_yticklabels(simplified_websites, fontsize=8)
            
            # 为每个条形添加数值标签
            for i, bar in enumerate(bars):
                width = bar.get_width()
                if width > 0:
                    ax3.text(width + 0.1, bar.get_y() + bar.get_height()/2.,
                            '%d' % int(width), ha='left', va='center', fontsize=8)
            
            ax3.set_xlabel('访问次数', fontsize=10)
            ax3.set_title('最常访问的网站', fontsize=12)
        else:
            ax3.text(0.5, 0.5, '没有网站访问数据', 
                   horizontalalignment='center', verticalalignment='center',
                   fontsize=10)
        
        # 4. 最常用的应用
        ax4 = fig.add_subplot(2, 2, 4)
        top_apps = analysis['top_apps']
        if top_apps:
            apps = list(top_apps.keys())[:10]  # 最多显示前10个
            app_counts = list(top_apps.values())[:10]
            
            # 截断过长的应用名
            simplified_apps = []
            for app in apps:
                if len(app) > 25:
                    simplified_apps.append(app[:22] + '...')
                else:
                    simplified_apps.append(app)
            
            y_pos = np.arange(len(simplified_apps))
            bars = ax4.barh(y_pos, app_counts)
            ax4.set_yticks(y_pos)
            ax4.set_yticklabels(simplified_apps, fontsize=8)
            
            # 为每个条形添加数值标签
            for i, bar in enumerate(bars):
                width = bar.get_width()
                if width > 0:
                    ax4.text(width + 0.1, bar.get_y() + bar.get_height()/2.,
                            '%d' % int(width), ha='left', va='center', fontsize=8)
            
            ax4.set_xlabel('使用次数', fontsize=10)
            ax4.set_title('最常用的应用', fontsize=12)
        else:
            ax4.text(0.5, 0.5, '没有应用使用数据', 
                   horizontalalignment='center', verticalalignment='center',
                   fontsize=10)
        
        plt.tight_layout(rect=[0, 0, 1, 0.96])  # 调整布局，为顶部标题留出空间
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"图表已保存到: {output_path}")
        else:
            plt.show()
    
    def save_dataset(self, dataset, filename: str = "activity_prediction_dataset.json"):
        """保存生成的数据集
        
        Args:
            dataset: 数据集
            filename: 文件名
        """
        output_path = os.path.join(self.output_dir, filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)
        
        print(f"数据集已保存到: {output_path}")
    
    def save_analysis(self, analysis, filename: str = "activity_analysis.json"):
        """保存活动分析结果
        
        Args:
            analysis: 分析结果
            filename: 文件名
        """
        output_path = os.path.join(self.output_dir, filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        
        print(f"分析结果已保存到: {output_path}")
    
    def generate_training_data(self):
        """生成用于训练大语言模型的数据
        
        格式化为适合大语言模型学习的序列到序列格式
        
        Returns:
            训练数据列表
        """
        print("生成大语言模型训练数据...")
        
        training_data = []
        
        # 为每个活动序列生成若干训练样本
        for i, sequence in enumerate(self.activity_sequences):
            if len(sequence) < 3:  # 至少需要3个活动
                continue
            
            # 生成不同长度的输入序列和目标序列
            for split_point in range(2, len(sequence)):
                input_seq = sequence[:split_point]
                target_seq = sequence[split_point:]
                
                # 限制目标序列长度，避免过长
                if len(target_seq) > 5:
                    target_seq = target_seq[:5]
                
                # 格式化为文本
                input_text = "\n".join(self._format_sequence(input_seq))
                target_text = "\n".join(self._format_sequence(target_seq))
                
                training_data.append({
                    "input": input_text,
                    "output": target_text,
                    "session_id": f"session_{i}",
                    "input_length": len(input_seq),
                    "output_length": len(target_seq)
                })
        
        print(f"生成了 {len(training_data)} 条训练数据")
        return training_data
    
    def export_for_fine_tuning(self, format_type="alpaca"):
        """导出用于微调大语言模型的数据集
        
        Args:
            format_type: 微调数据集格式，支持"alpaca"和"instruct"
            
        Returns:
            导出的数据集路径
        """
        print(f"导出 {format_type} 格式的微调数据集...")
        
        # 获取训练数据
        training_data = self.generate_training_data()
        
        if format_type == "alpaca":
            # Alpaca 格式
            formatted_data = []
            for item in training_data:
                formatted_data.append({
                    "instruction": "根据用户的历史活动序列，预测用户接下来最有可能执行的操作。",
                    "input": item["input"],
                    "output": item["output"]
                })
            
            output_file = os.path.join(self.output_dir, "alpaca_fine_tuning_data.json")
            
        elif format_type == "instruct":
            # 类似ChatGPT微调的格式，对话形式
            formatted_data = []
            for item in training_data:
                formatted_data.append({
                    "messages": [
                        {"role": "system", "content": "你是一个可以预测用户接下来操作的助手。根据用户的历史活动序列，预测用户接下来最有可能执行的操作。"},
                        {"role": "user", "content": f"这是我最近的活动序列:\n{item['input']}\n\n请预测我接下来可能会执行的操作。"},
                        {"role": "assistant", "content": item["output"]}
                    ]
                })
            
            output_file = os.path.join(self.output_dir, "instruct_fine_tuning_data.jsonl")
            
        else:
            raise ValueError(f"不支持的格式: {format_type}")
        
        # 保存数据集
        if format_type == "instruct":
            # jsonl格式，每行一个json对象
            with open(output_file, 'w', encoding='utf-8') as f:
                for item in formatted_data:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
        else:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(formatted_data, f, ensure_ascii=False, indent=2)
        
        print(f"{format_type}格式微调数据集已保存到: {output_file}")
        return output_file

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="分析用户活动数据并生成训练数据集")
    parser.add_argument("--data-dir", default="activity_data", help="活动数据目录")
    parser.add_argument("--output-dir", default="dataset", help="输出数据集目录")
    parser.add_argument("--window-size", type=int, default=5, help="预测窗口大小")
    parser.add_argument("--step-size", type=int, default=1, help="滑动窗口步长")
    parser.add_argument("--inactive-threshold", type=int, default=30, help="会话不活跃阈值(分钟)")
    parser.add_argument("--export-format", choices=["alpaca", "instruct"], default="alpaca", help="导出格式")
    parser.add_argument("--visualize", action="store_true", help="是否可视化活动模式")
    
    args = parser.parse_args()
    
    analyzer = ActivityAnalyzer(args.data_dir, args.output_dir)
    
    # 加载和预处理数据
    analyzer.load_data()
    analyzer.preprocess_data()
    
    # 分段
    analyzer.segment_by_session(args.inactive_threshold)
    
    # 分析模式
    analysis = analyzer.analyze_activity_patterns()
    analyzer.save_analysis(analysis)
    
    # 可视化
    if args.visualize:
        viz_path = os.path.join(args.output_dir, "activity_patterns.png")
        analyzer.visualize_activity_patterns(viz_path)
    
    # 生成训练数据集
    dataset = analyzer.generate_sequence_dataset(args.window_size, args.step_size)
    analyzer.save_dataset(dataset)
    
    # 导出微调数据集
    analyzer.export_for_fine_tuning(args.export_format)
    
    print("数据分析和数据集生成完成！")

if __name__ == "__main__":
    main() 