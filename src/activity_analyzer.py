"""
活动分析脚本 - 分析用户文件操作序列
对收集的用户活动数据进行分析，生成可供大语言模型学习的训练数据集
"""

import os
import json
import glob
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import List, Dict, Any, Tuple, Optional, Set
import re
from pathlib import Path
import matplotlib
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from urllib.parse import urlparse
import networkx as nx
from tqdm import tqdm

# 设置中文字体
try:
    matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial', 'sans-serif']
    matplotlib.rcParams['axes.unicode_minus'] = False  # 正确显示负号
except:
    pass  # 在某些环境中可能无法设置字体

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
        
        # 数据帧形式的活动数据
        self.activities_df = None
        
        # 按时间分段的活动序列
        self.activity_sequences = []
        
        # 应用使用统计
        self.app_usage_stats = {}
        
        # 域名访问统计
        self.domain_stats = {}
        
        # 文件访问统计
        self.file_stats = {}
        
        # 活动模式
        self.activity_patterns = {}
        
        # 时间模式
        self.time_patterns = {}
        
        print(f"活动分析器初始化完成，数据目录: {data_dir}, 输出目录: {output_dir}")
    
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
        
        if not self.activities:
            self.load_data()
        
        # 过滤掉没有时间戳或类型的记录
        self.activities = [a for a in self.activities if 'timestamp' in a and 'type' in a]
        
        # 转换时间戳为datetime对象，便于后续处理
        for activity in self.activities:
            try:
                activity['datetime'] = datetime.fromisoformat(activity['timestamp'])
            except:
                # 如果时间戳格式有问题，使用当前时间
                activity['datetime'] = datetime.now()
        
        # 标准化浏览器历史记录
        for activity in self.activities:
            if activity['type'] == 'browser_history':
                # 如果已经有域名字段，使用现有域名
                if 'domain' not in activity or not activity['domain']:
                    # 提取域名
                    url = activity.get('url', '')
                    try:
                        parsed_url = urlparse(url)
                        activity['domain'] = parsed_url.netloc
                    except:
                        activity['domain'] = ''
                
                # 简化URL
                activity['simplified_url'] = self._simplify_url(url)
                
                # 添加有意义的描述
                activity['description'] = self._generate_browser_description(activity)
        
        # 标准化文件路径
        for activity in self.activities:
            if activity['type'] == 'file_access':
                path = activity.get('path', '')
                activity['file_extension'] = os.path.splitext(path)[1].lower() if path else ''
                activity['filename'] = os.path.basename(path) if path else ''
                activity['directory'] = os.path.dirname(path) if path else ''
        
        # 重新按时间排序
        self.activities = sorted(self.activities, key=lambda x: x['datetime'])
        
        # 转换为DataFrame以便更高效的分析
        self.activities_df = pd.DataFrame(self.activities)
        
        print(f"预处理后剩余 {len(self.activities)} 条记录")
        return self.activities
    
    def _simplify_url(self, url: str) -> str:
        """简化URL，去除查询参数和锚点
        
        Args:
            url: 原始URL
            
        Returns:
            简化后的URL
        """
        try:
            parsed = urlparse(url)
            # 保留协议、域名和路径，去除查询参数和锚点
            simplified = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            
            # 移除常见ID参数路径 (如 /123456/)
            simplified = re.sub(r'/\d+/?$', '/', simplified)
            
            # 移除常见的页面标识符
            simplified = re.sub(r'/page/\d+/?$', '/', simplified)
            simplified = re.sub(r'/p/\d+/?$', '/', simplified)
            
            return simplified
        except:
            return url
    
    def _generate_browser_description(self, activity):
        """生成浏览器活动的描述性文本
        
        Args:
            activity: 浏览器活动记录
            
        Returns:
            描述性文本
        """
        title = activity.get('title', '')
        url = activity.get('url', '')
        domain = activity.get('domain', '')
        browser = activity.get('browser', '浏览器')
        
        if domain and title:
            return f"访问网站 {domain} 的页面 '{title}'"
        elif domain:
            return f"访问网站 {domain}"
        elif title:
            return f"打开标题为 '{title}' 的网页"
        else:
            return f"浏览网页 {url}"
    
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
            self.preprocess_data()
        
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
                
            # 如果遇到session_end事件，强制结束当前会话
            if activity['type'] == 'session_end' and len(current_seq) > 1:
                sequences.append(current_seq)
                current_seq = []
        
        # 添加最后一个序列
        if len(current_seq) > 1:
            sequences.append(current_seq)
        
        self.activity_sequences = sequences
        print(f"共生成 {len(sequences)} 个活动会话")
        
        return sequences
    
    def segment_by_context_change(self, max_sequence_length: int = 50):
        """按上下文变化分段
        
        Args:
            max_sequence_length: 最大序列长度，超过此长度强制开始新序列
        
        Returns:
            List of activity sequences
        """
        print("按上下文变化分段活动序列...")
        
        if not self.activities:
            self.preprocess_data()
            
        sequences = []
        current_seq = []
        current_context = None
        
        # 时间阈值：如果两个活动间隔超过10分钟，视为上下文变化
        max_time_diff = 600  # 10分钟，单位秒
        last_time = None
        
        for activity in self.activities:
            # 检查时间间隔
            current_time = activity['datetime']
            if last_time is not None:
                time_diff = (current_time - last_time).total_seconds()
                if time_diff > max_time_diff:
                    # 时间间隔太长，视为上下文变化
                    if len(current_seq) > 0:
                        sequences.append(current_seq)
                        current_seq = []
                        current_context = None
            
            last_time = current_time
            
            # 定义上下文变化条件
            new_context = False
            
            # 如果是会话开始/结束，强制开始新序列
            if activity['type'] in ['session_start', 'session_end', 'time_context']:
                new_context = True
            
            # 如果是进程开始，可能是上下文变化
            elif activity['type'] == 'process_start' and 'process_name' in activity:
                if not current_context or current_context.get('app') != activity['process_name']:
                    new_context = True
                    current_context = {'app': activity['process_name']}
                    
            # 窗口焦点变化可能是上下文变化
            elif activity['type'] == 'window_focus' and 'process_name' in activity:
                if not current_context or current_context.get('app') != activity['process_name']:
                    new_context = True
                    current_context = {'app': activity['process_name']}
            
            # 浏览器域名变化可能是上下文变化，使用domain字段
            elif activity['type'] == 'browser_history' and 'domain' in activity:
                domain = activity.get('domain', '')
                if domain:
                    # 检查是否切换了域名
                    browser_in_context = (current_context and current_context.get('app') in 
                                        ['chrome.exe', 'msedge.exe', 'firefox.exe', 'chrome', 'edge', 'firefox'])
                    
                    if (not current_context or 
                        (browser_in_context and 
                         current_context.get('domain') != domain and 
                         current_context.get('domain') is not None)):
                        new_context = True
                        browser_name = activity.get('browser', 'browser')
                        current_context = {'app': browser_name, 'domain': domain}
            
            # 当前序列过长，强制开始新序列
            if len(current_seq) >= max_sequence_length:
                new_context = True
            
            # 处理上下文变化
            if new_context and len(current_seq) > 0:
                sequences.append(current_seq)
                current_seq = [activity]
            else:
                current_seq.append(activity)
        
        # 添加最后一个序列
        if len(current_seq) > 0:
            sequences.append(current_seq)
        
        self.activity_sequences = sequences
        print(f"共生成 {len(sequences)} 个上下文序列")
        
        return sequences
    
    def extract_sequence_features(self):
        """从活动序列中提取特征"""
        print("提取序列特征...")
        
        if not self.activity_sequences:
            self.segment_by_session()
        
        sequence_features = []
        
        for i, sequence in enumerate(self.activity_sequences):
            if len(sequence) < 2:
                continue
                
            # 基本特征
            start_time = sequence[0]['datetime']
            end_time = sequence[-1]['datetime']
            duration = (end_time - start_time).total_seconds()
            
            # 活动类型统计
            activity_types = Counter([a['type'] for a in sequence])
            
            # 应用使用统计
            apps_used = set()
            for a in sequence:
                if a['type'] == 'window_focus' and 'process_name' in a:
                    apps_used.add(a['process_name'])
                elif a['type'] == 'process_start' and 'process_name' in a:
                    apps_used.add(a['process_name'])
            
            # 浏览域名统计
            domains_visited = Counter()
            for a in sequence:
                if a['type'] == 'browser_history' and 'domain' in a:
                    domains_visited[a['domain']] += 1
            
            # 文件访问统计
            files_accessed = Counter()
            for a in sequence:
                if a['type'] == 'file_access' and 'file_extension' in a:
                    files_accessed[a['file_extension']] += 1
            
            # 时间上下文
            day_of_week = start_time.weekday()
            hour_of_day = start_time.hour
            is_weekend = day_of_week >= 5
            
            # 构建特征字典
            feature = {
                'sequence_id': i,
                'start_time': start_time,
                'end_time': end_time,
                'duration': duration,
                'activity_count': len(sequence),
                'activity_types': dict(activity_types),
                'apps_used': list(apps_used),
                'domains_visited': dict(domains_visited),
                'files_accessed': dict(files_accessed),
                'day_of_week': day_of_week,
                'hour_of_day': hour_of_day,
                'is_weekend': is_weekend,
                'avg_activity_rate': len(sequence) / (duration / 60) if duration > 0 else 0  # 每分钟活动数
            }
            
            sequence_features.append(feature)
        
        print(f"从 {len(self.activity_sequences)} 个序列中提取了 {len(sequence_features)} 个特征集")
        return sequence_features
    
    def generate_sequence_dataset(self, window_size: int = 5, step_size: int = 1, max_samples_per_sequence: int = 5):
        """生成序列预测数据集
        
        Args:
            window_size: 用于预测的窗口大小（活动数量）
            step_size: 滑动窗口的步长
            max_samples_per_sequence: 每个序列最多生成的样本数，避免长序列产生过多相似样本
            
        Returns:
            预测数据集
        """
        print(f"生成序列预测数据集(窗口大小={window_size}, 步长={step_size})...")
        
        if not self.activity_sequences:
            self.segment_by_context_change()
            
        dataset = []
        sequence_hashes = set()  # 用于在生成阶段进行初步去重
        
        for sequence in self.activity_sequences:
            if len(sequence) <= window_size:
                continue
            
            # 为每个序列控制生成的样本数量
            samples_from_this_sequence = 0
            
            # 计算可能的起始位置
            possible_starts = list(range(0, len(sequence) - window_size, step_size))
            
            # 如果序列很长，均匀采样起始位置而不是生成所有可能的窗口
            if len(possible_starts) > max_samples_per_sequence:
                # 均匀采样
                sampling_step = len(possible_starts) // max_samples_per_sequence
                selected_starts = possible_starts[::sampling_step][:max_samples_per_sequence]
            else:
                selected_starts = possible_starts
            
            # 根据选定的起始位置生成样本
            for i in selected_starts:
                input_seq = sequence[i:i+window_size]
                target = sequence[i+window_size]
                
                # 格式化为可训练的数据
                input_formatted = self._format_sequence(input_seq)
                target_formatted = self._format_activity(target)
                
                # 生成样本的唯一标识，用于初步去重
                sample_hash = hash("".join(input_formatted) + target_formatted)
                
                if sample_hash not in sequence_hashes:
                    sequence_hashes.add(sample_hash)
                    dataset.append({
                        "input_sequence": input_formatted,
                        "target": target_formatted,
                        "raw_input": input_seq,
                        "raw_target": target
                    })
                    samples_from_this_sequence += 1
                
                # 如果从当前序列已生成足够样本，提前结束
                if samples_from_this_sequence >= max_samples_per_sequence:
                    break
        
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
        time_str = activity.get('datetime').strftime('%Y-%m-%d %H:%M:%S')
        
        # 根据不同活动类型生成不同的描述
        if activity_type == 'window_focus':
            return f"{time_str} - 切换到窗口: {activity.get('window_title', '')} (应用: {activity.get('process_name', '')})"
            
        elif activity_type == 'process_start':
            return f"{time_str} - 启动应用: {activity.get('process_name', '')}"
            
        elif activity_type == 'process_end':
            return f"{time_str} - 关闭应用: {activity.get('process_name', '')}"
            
        elif activity_type == 'browser_history':
            # 使用预先生成的描述，避免显示冗长的URL
            if 'description' in activity:
                return f"{time_str} - {activity['description']}"
            # 回退到原始格式
            domain = activity.get('domain', '')
            title = activity.get('title', '')
            if domain and title:
                return f"{time_str} - 访问网站: {domain} - {title}"
            return f"{time_str} - 访问网页: {activity.get('title', '')} ({activity.get('url', '')})"
            
        elif activity_type == 'file_access':
            # 简化文件路径显示
            path = activity.get('path', '')
            filename = os.path.basename(path) if path else ''
            directory = os.path.dirname(path) if path else ''
            if filename and directory:
                short_dir = self._shorten_path(directory)
                return f"{time_str} - 访问文件: {filename} (位于 {short_dir})"
            return f"{time_str} - 访问文件: {path}"
            
        elif activity_type == 'app_usage':
            return f"{time_str} - 使用应用: {activity.get('process_name', '')} (时长: {activity.get('duration', 0)}秒)"
            
        elif activity_type == 'time_context':
            day_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
            day = day_names[activity.get('day_of_week', 0)] if 'day_of_week' in activity else '未知'
            hour = activity.get('hour_of_day', 0)
            return f"{time_str} - 时间上下文: {day} {hour}时"
            
        elif activity_type == 'session_start':
            return f"{time_str} - 会话开始"
            
        elif activity_type == 'session_end':
            return f"{time_str} - 会话结束 (持续时间: {activity.get('session_duration', 0)}秒)"
            
        else:
            # 通用格式
            return f"{time_str} - {activity_type}: {', '.join([f'{k}={v}' for k, v in activity.items() if k not in ['type', 'datetime', 'timestamp']])}"
    
    def _shorten_path(self, path: str, max_length: int = 30) -> str:
        """缩短路径以便于显示
        
        Args:
            path: 完整路径
            max_length: 最大长度
            
        Returns:
            缩短后的路径
        """
        if len(path) <= max_length:
            return path
            
        # 保留驱动器名称和最后两级目录
        parts = path.split(os.path.sep)
        if len(parts) <= 3:
            return path
            
        return f"{parts[0]}{os.path.sep}...{os.path.sep}{os.path.sep.join(parts[-2:])}"
    
    def analyze_activity_patterns(self):
        """分析活动模式和习惯"""
        print("分析活动模式和习惯...")
        
        if not self.activities:
            self.preprocess_data()
        
        patterns = {}
        
        # 分析每日活跃时间段
        hourly_activity = defaultdict(int)
        weekday_activity = defaultdict(int)
        
        for activity in self.activities:
            dt = activity['datetime']
            hourly_activity[dt.hour] += 1
            weekday_activity[dt.weekday()] += 1
        
        patterns['hourly_distribution'] = dict(hourly_activity)
        patterns['weekday_distribution'] = dict(weekday_activity)
        
        # 分析应用使用频率和持续时间
        app_frequency = defaultdict(int)
        app_durations = defaultdict(list)
        
        for activity in self.activities:
            if activity['type'] == 'app_usage' and 'process_name' in activity and 'duration' in activity:
                process_name = activity['process_name']
                duration = activity['duration']
                app_frequency[process_name] += 1
                app_durations[process_name].append(duration)
        
        # 计算平均持续时间
        app_avg_duration = {}
        for app, durations in app_durations.items():
            if durations:
                app_avg_duration[app] = sum(durations) / len(durations)
        
        patterns['app_frequency'] = dict(app_frequency)
        patterns['app_avg_duration'] = app_avg_duration
        
        # 排序得到最常用的应用
        top_apps = sorted(app_frequency.items(), key=lambda x: x[1], reverse=True)[:10]
        patterns['top_apps'] = dict(top_apps)
        
        # 分析浏览器域名访问频率
        domain_frequency = defaultdict(int)
        
        for activity in self.activities:
            if activity['type'] == 'browser_history' and 'domain' in activity:
                domain = activity['domain']
                if domain:
                    domain_frequency[domain] += 1
        
        # 排序得到最常访问的域名
        top_domains = sorted(domain_frequency.items(), key=lambda x: x[1], reverse=True)[:20]
        patterns['top_domains'] = dict(top_domains)
        
        # 分析文件类型访问频率
        file_ext_frequency = defaultdict(int)
        
        for activity in self.activities:
            if activity['type'] == 'file_access' and 'file_extension' in activity:
                ext = activity['file_extension']
                if ext:
                    file_ext_frequency[ext] += 1
        
        patterns['file_extension_frequency'] = dict(file_ext_frequency)
        
        # 分析应用切换模式
        app_transitions = defaultdict(int)
        prev_app = None
        
        for activity in self.activities:
            if activity['type'] == 'window_focus' and 'process_name' in activity:
                current_app = activity['process_name']
                if prev_app and prev_app != current_app:
                    app_transitions[(prev_app, current_app)] += 1
                prev_app = current_app
        
        # 排序得到最常见的应用切换模式
        top_transitions = sorted(app_transitions.items(), key=lambda x: x[1], reverse=True)[:15]
        patterns['top_app_transitions'] = {f"{src} -> {dst}": cnt for (src, dst), cnt in top_transitions}
        
        self.activity_patterns = patterns
        print("活动模式分析完成")
        
        return patterns
    
    def visualize_activity_patterns(self, save_dir: str = None):
        """可视化活动模式
        
        Args:
            save_dir: 保存可视化图表的目录，默认为输出目录
        """
        if not save_dir:
            save_dir = self.output_dir
            
        Path(save_dir).mkdir(parents=True, exist_ok=True)
            
        if not self.activity_patterns:
            self.analyze_activity_patterns()
        
        patterns = self.activity_patterns
        
        print("生成活动模式可视化...")
        
        # 设置绘图样式
        plt.style.use('ggplot')
        
        # 1. 每小时活动分布
        plt.figure(figsize=(12, 6))
        hours = range(24)
        counts = [patterns['hourly_distribution'].get(h, 0) for h in hours]
        plt.bar(hours, counts, color='skyblue')
        plt.title('每小时活动分布')
        plt.xlabel('小时')
        plt.ylabel('活动数')
        plt.xticks(hours)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.savefig(os.path.join(save_dir, 'hourly_activity.png'), dpi=300, bbox_inches='tight')
        plt.close()
        
        # 2. 星期活动分布
        plt.figure(figsize=(10, 6))
        weekdays = range(7)
        weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        counts = [patterns['weekday_distribution'].get(w, 0) for w in weekdays]
        plt.bar(weekday_names, counts, color='lightcoral')
        plt.title('星期活动分布')
        plt.xlabel('星期')
        plt.ylabel('活动数')
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.savefig(os.path.join(save_dir, 'weekday_activity.png'), dpi=300, bbox_inches='tight')
        plt.close()
        
        # 3. 热力图：星期+小时
        if self.activities_df is not None:
            plt.figure(figsize=(14, 8))
            
            # 提取小时和星期
            hour_data = [dt.hour for dt in self.activities_df['datetime']]
            weekday_data = [dt.weekday() for dt in self.activities_df['datetime']]
            
            # 创建热力图数据
            heatmap_data = np.zeros((7, 24))
            for w, h in zip(weekday_data, hour_data):
                heatmap_data[w, h] += 1
            
            # 绘制热力图
            sns.heatmap(heatmap_data, cmap='YlOrRd', 
                       xticklabels=range(24),
                       yticklabels=weekday_names)
            plt.title('活动时间热力图')
            plt.xlabel('小时')
            plt.ylabel('星期')
            plt.savefig(os.path.join(save_dir, 'activity_heatmap.png'), dpi=300, bbox_inches='tight')
            plt.close()
        
        # 4. 常用应用饼图
        if patterns.get('top_apps'):
            plt.figure(figsize=(12, 8))
            apps = list(patterns['top_apps'].keys())
            usage = list(patterns['top_apps'].values())
            
            # 只展示前8个，其余归为"其他"
            if len(apps) > 8:
                other_usage = sum(usage[8:])
                apps = apps[:8] + ['其他']
                usage = usage[:8] + [other_usage]
            
            plt.pie(usage, labels=apps, autopct='%1.1f%%', startangle=90, shadow=True)
            plt.axis('equal')
            plt.title('常用应用分布')
            plt.savefig(os.path.join(save_dir, 'top_apps.png'), dpi=300, bbox_inches='tight')
            plt.close()
        
        # 5. 常访问域名条形图
        if patterns.get('top_domains'):
            plt.figure(figsize=(14, 8))
            domains = list(patterns['top_domains'].keys())[:15]  # 最多展示15个
            visits = [patterns['top_domains'][d] for d in domains]
            
            plt.barh(domains, visits, color='lightgreen')
            plt.title('常访问网站域名')
            plt.xlabel('访问次数')
            plt.grid(axis='x', linestyle='--', alpha=0.7)
            plt.savefig(os.path.join(save_dir, 'top_domains.png'), dpi=300, bbox_inches='tight')
            plt.close()
        
        # 6. 文件类型访问频率
        if patterns.get('file_extension_frequency'):
            plt.figure(figsize=(12, 7))
            exts = list(patterns['file_extension_frequency'].keys())
            if len(exts) > 0:
                counts = [patterns['file_extension_frequency'][e] for e in exts]
                
                # 仅显示前10种类型
                if len(exts) > 10:
                    exts = exts[:10]
                    counts = counts[:10]
                
                plt.bar(exts, counts, color='lightblue')
                plt.title('文件类型访问频率')
                plt.xlabel('文件类型')
                plt.ylabel('访问次数')
                plt.grid(axis='y', linestyle='--', alpha=0.7)
                plt.xticks(rotation=45)
                plt.savefig(os.path.join(save_dir, 'file_extensions.png'), dpi=300, bbox_inches='tight')
                plt.close()
        
        # 7. 应用使用时长对比
        if patterns.get('app_avg_duration'):
            plt.figure(figsize=(14, 8))
            apps = list(patterns['app_avg_duration'].keys())
            
            # 只展示前10个
            if len(apps) > 10:
                apps = apps[:10]
                
            durations = [patterns['app_avg_duration'][a] for a in apps]
            
            plt.barh(apps, durations, color='salmon')
            plt.title('应用平均使用时长 (秒)')
            plt.xlabel('平均时长(秒)')
            plt.grid(axis='x', linestyle='--', alpha=0.7)
            plt.savefig(os.path.join(save_dir, 'app_durations.png'), dpi=300, bbox_inches='tight')
            plt.close()
            
        print(f"活动模式可视化已保存到 {save_dir} 目录")
    
    def save_dataset(self, dataset, filename: str = "activity_prediction_dataset.json"):
        """保存生成的数据集
        
        Args:
            dataset: 数据集
            filename: 保存的文件名
        """
        output_path = os.path.join(self.output_dir, filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2, default=str)
            
        print(f"数据集已保存到 {output_path}")
    
    def save_analysis(self, filename: str = "activity_analysis.json"):
        """保存分析结果
        
        Args:
            filename: 保存的文件名
        """
        if not self.activity_patterns:
            self.analyze_activity_patterns()
            
        output_path = os.path.join(self.output_dir, filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.activity_patterns, f, ensure_ascii=False, indent=2, default=str)
            
        print(f"分析结果已保存到 {output_path}")
    
    def generate_training_data(self, window_size: int = 5, step_size: int = 1, 
                            max_samples_per_sequence: int = 5, remove_duplicates: bool = True):
        """生成完整的训练数据集
        
        Args:
            window_size: 预测窗口大小
            step_size: 滑动窗口步长
            max_samples_per_sequence: 每个序列最多生成的样本数
            remove_duplicates: 是否删除重复的序列
            
        Returns:
            生成的数据集
        """
        print("开始生成训练数据集...")
        
        # 1. 预处理数据
        self.preprocess_data()
        
        # 2. 分段活动序列 - 使用多种分段方法
        print("使用多种分段方法...")
        
        # 会话分段
        self.activity_sequences = []  # 确保为空
        session_sequences = self.segment_by_session(inactive_threshold=30)
        
        # 上下文分段 - 注意：避免重复处理相同的原始数据
        self.activities = self.activities.copy()  # 创建副本防止影响之前的分段结果
        self.activity_sequences = []  # 清空之前的分段结果
        context_sequences = self.segment_by_context_change(max_sequence_length=50)
        
        # 合并分段结果前去除重复序列
        if remove_duplicates:
            # 通过哈希序列的开始/结束时间和长度，去除非常相似的序列
            unique_sequence_hashes = set()
            unique_sequences = []
            
            for sequence_list in [session_sequences, context_sequences]:
                for seq in sequence_list:
                    if len(seq) < 2:
                        continue
                        
                    # 生成序列特征指纹
                    start_time = seq[0]['datetime']
                    end_time = seq[-1]['datetime']
                    duration = (end_time - start_time).total_seconds()
                    seq_hash = hash(f"{start_time}_{end_time}_{len(seq)}_{duration}")
                    
                    if seq_hash not in unique_sequence_hashes:
                        unique_sequence_hashes.add(seq_hash)
                        unique_sequences.append(seq)
            
            self.activity_sequences = unique_sequences
            print(f"去重后共有 {len(self.activity_sequences)} 个唯一序列")
        else:
            # 不去重，直接合并
            self.activity_sequences = session_sequences + context_sequences
            print(f"合并后共有 {len(self.activity_sequences)} 个序列")
        
        # 3. 生成序列预测数据集
        dataset = self.generate_sequence_dataset(
            window_size=window_size, 
            step_size=step_size,
            max_samples_per_sequence=max_samples_per_sequence
        )
        
        # 4. 保存数据集
        self.save_dataset(dataset)
        
        # 5. 分析活动模式
        self.analyze_activity_patterns()
        self.save_analysis()
        
        return dataset
    
    def export_for_fine_tuning(self, format_type: str = "alpaca", output_file: str = None):
        """导出适合微调大语言模型的数据集
        
        Args:
            format_type: 数据格式类型，支持 "alpaca" 或 "instruct"
            output_file: 输出文件名，默认根据格式类型自动生成
            
        Returns:
            输出文件路径
        """
        if not output_file:
            if format_type.lower() == "alpaca":
                output_file = "alpaca_fine_tuning_data.json"
            else:
                output_file = "instruct_fine_tuning_data.jsonl"
                
        output_path = os.path.join(self.output_dir, output_file)
        
        # 确保有数据集
        dataset = []
        try:
            dataset_path = os.path.join(self.output_dir, "activity_prediction_dataset.json")
            if os.path.exists(dataset_path):
                with open(dataset_path, 'r', encoding='utf-8') as f:
                    dataset = json.load(f)
            else:
                dataset = self.generate_training_data()
        except Exception as e:
            print(f"加载数据集出错: {e}")
            dataset = self.generate_training_data()
            
        print(f"原始训练数据: {len(dataset)} 条")
        
        # 进行数据去重处理
        unique_samples = set()
        deduplicated_dataset = []
        
        for item in dataset:
            # 对输入序列和目标组合生成哈希值，用于去重
            combined_text = "".join(item["input_sequence"]) + item["target"]
            sample_hash = hash(combined_text)
            
            if sample_hash not in unique_samples:
                unique_samples.add(sample_hash)
                deduplicated_dataset.append(item)
        
        # 进一步减少相似样本（可选）
        if len(deduplicated_dataset) > 1000:  # 如果样本太多
            # 对序列采样，保留更多样性
            sampling_step = max(1, len(deduplicated_dataset) // 1000)
            deduplicated_dataset = deduplicated_dataset[::sampling_step]
        
        print(f"去重后训练数据: {len(deduplicated_dataset)} 条")
            
        print(f"准备以 {format_type} 格式导出 {len(deduplicated_dataset)} 条训练数据...")
        
        if format_type.lower() == "alpaca":
            # Alpaca格式: 适合基于指令的微调
            alpaca_data = []
            
            for i, item in enumerate(deduplicated_dataset):
                input_sequence = item["input_sequence"]
                target = item["target"]
                
                # 构建指令式样本
                alpaca_sample = {
                    "instruction": "根据用户之前的活动序列，预测下一个可能的活动。",
                    "input": "用户活动序列:\n" + "\n".join(input_sequence),
                    "output": target
                }
                
                alpaca_data.append(alpaca_sample)
                
            # 保存为JSON格式
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(alpaca_data, f, ensure_ascii=False, indent=2)
                
        else:
            # Instruct格式: 适合对话式模型
            with open(output_path, 'w', encoding='utf-8') as f:
                for i, item in enumerate(deduplicated_dataset):
                    input_sequence = item["input_sequence"]
                    target = item["target"]
                    
                    # 构建对话式样本
                    instruct_sample = {
                        "messages": [
                            {"role": "system", "content": "你是一个智能助手，能够根据用户的活动历史预测下一个可能的活动。"},
                            {"role": "user", "content": "我最近的活动序列如下，请预测我接下来可能进行什么活动：\n" + "\n".join(input_sequence)},
                            {"role": "assistant", "content": f"根据你的活动历史，你接下来可能会：\n{target}"}
                        ]
                    }
                    
                    # 保存为JSONL格式
                    f.write(json.dumps(instruct_sample, ensure_ascii=False) + "\n")
        
        print(f"微调数据集已导出至 {output_path}")
        return output_path

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="分析用户活动数据并生成训练数据集")
    parser.add_argument("--data-dir", default="activity_data", help="活动数据目录")
    parser.add_argument("--output-dir", default="dataset", help="输出数据集目录")
    parser.add_argument("--window-size", type=int, default=5, help="预测窗口大小")
    parser.add_argument("--step-size", type=int, default=1, help="滑动窗口步长")
    parser.add_argument("--inactive-threshold", type=int, default=30, help="会话不活跃阈值(分钟)")
    parser.add_argument("--export-format", default="alpaca", choices=["alpaca", "instruct"], help="微调数据集格式")
    parser.add_argument("--visualize", action="store_true", help="是否生成可视化图表")
    parser.add_argument("--max-samples", type=int, default=5, help="每个序列最多生成的样本数")
    parser.add_argument("--no-dedup", action="store_true", help="禁用序列去重")
    parser.add_argument("--max-dataset-size", type=int, default=1000, help="最终数据集的最大样本数")
    
    args = parser.parse_args()
    
    try:
        analyzer = ActivityAnalyzer(data_dir=args.data_dir, output_dir=args.output_dir)
        
        # 生成训练数据
        analyzer.generate_training_data(
            window_size=args.window_size,
            step_size=args.step_size,
            max_samples_per_sequence=args.max_samples,
            remove_duplicates=not args.no_dedup
        )
        
        # 导出微调数据集
        analyzer.export_for_fine_tuning(format_type=args.export_format)
        
        # 可视化活动模式
        if args.visualize:
            analyzer.visualize_activity_patterns()
            
        print("分析和数据集生成完成！")
        
    except Exception as e:
        print(f"运行出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 