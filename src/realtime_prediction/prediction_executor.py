#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预测执行器 - 根据LLM预测结果自动执行操作
"""

import os
import re
import time
import webbrowser
import subprocess
import threading
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class PredictionExecutor:
    """预测结果执行器"""
    
    def __init__(self, enable_auto_execution=True, preview_delay=3):
        self.enable_auto_execution = enable_auto_execution
        self.preview_delay = preview_delay  # 预览延迟时间（秒）
        self.execution_history = []
        self.pending_executions = []
        
        # 支持的应用程序路径
        self.app_paths = {
            'chrome': self._find_chrome_path(),
            'edge': self._find_edge_path(),
            'vscode': self._find_vscode_path(),
            'notepad': 'notepad.exe',
            'calculator': 'calc.exe'
        }
        
        logger.info(f"🎯 预测执行器初始化完成 - 自动执行: {enable_auto_execution}")
    
    def _find_chrome_path(self) -> Optional[str]:
        """查找Chrome浏览器路径"""
        possible_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(os.getenv('USERNAME', ''))
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None
    
    def _find_edge_path(self) -> Optional[str]:
        """查找Edge浏览器路径"""
        possible_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None
    
    def _find_vscode_path(self) -> Optional[str]:
        """查找VSCode路径"""
        possible_paths = [
            r"C:\Users\{}\AppData\Local\Programs\Microsoft VS Code\Code.exe".format(os.getenv('USERNAME', '')),
            r"C:\Program Files\Microsoft VS Code\Code.exe",
            r"C:\Program Files (x86)\Microsoft VS Code\Code.exe"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None
    
    def parse_prediction(self, prediction_text: str) -> Optional[Dict]:
        """解析预测文本，提取执行信息"""
        try:
            # 预测格式: "2025-05-22 08:30:38 - 访问网站 github.com 的页面 'README.md at main · OSH-2025/MEMO'"
            
            # 提取网站访问模式
            website_pattern = r"访问网站\s+([^\s]+)(?:\s+的页面\s+'([^']+)')?|访问网站\s+([^\s]+)"
            website_match = re.search(website_pattern, prediction_text)
            
            if website_match:
                domain = website_match.group(1) or website_match.group(3)
                page_title = website_match.group(2)
                
                return {
                    'type': 'website',
                    'domain': domain,
                    'page_title': page_title,
                    'url': f"https://{domain}",
                    'confidence': 0.8  # 默认置信度
                }
            
            # 提取应用程序模式
            app_pattern = r"切换到应用\s+([^\s]+)(?:\s+-\s+'([^']+)')?|打开应用\s+([^\s]+)"
            app_match = re.search(app_pattern, prediction_text)
            
            if app_match:
                app_name = app_match.group(1) or app_match.group(3)
                window_title = app_match.group(2)
                
                return {
                    'type': 'application',
                    'app_name': app_name,
                    'window_title': window_title,
                    'confidence': 0.7
                }
            
            # 提取文件访问模式
            file_pattern = r"访问文件\s+([^\s]+)"
            file_match = re.search(file_pattern, prediction_text)
            
            if file_match:
                file_path = file_match.group(1)
                
                return {
                    'type': 'file',
                    'file_path': file_path,
                    'confidence': 0.6
                }
            
            logger.warning(f"⚠️ 无法解析预测文本: {prediction_text}")
            return None
            
        except Exception as e:
            logger.error(f"❌ 解析预测失败: {e}")
            return None
    
    def schedule_execution(self, prediction: Dict, delay_seconds: int = 0):
        """调度执行预测结果"""
        execution_time = datetime.now() + timedelta(seconds=delay_seconds)
        
        execution_item = {
            'prediction': prediction,
            'scheduled_time': execution_time,
            'executed': False,
            'execution_id': len(self.pending_executions)
        }
        
        self.pending_executions.append(execution_item)
        
        if delay_seconds > 0:
            logger.info(f"⏰ 预测执行已调度，将在 {delay_seconds} 秒后执行")
            # 在后台线程中延迟执行
            threading.Timer(delay_seconds, self._execute_prediction, args=[execution_item]).start()
        else:
            # 立即执行
            self._execute_prediction(execution_item)
    
    def _execute_prediction(self, execution_item: Dict):
        """执行预测结果"""
        prediction = execution_item['prediction']
        
        if not self.enable_auto_execution:
            logger.info(f"🔍 预览模式: {prediction}")
            return
        
        try:
            success = False
            
            if prediction['type'] == 'website':
                success = self._open_website(prediction)
            elif prediction['type'] == 'application':
                success = self._open_application(prediction)
            elif prediction['type'] == 'file':
                success = self._open_file(prediction)
            
            # 记录执行结果
            execution_result = {
                'prediction': prediction,
                'executed_at': datetime.now().isoformat(),
                'success': success,
                'execution_id': execution_item['execution_id']
            }
            
            self.execution_history.append(execution_result)
            execution_item['executed'] = True
            
            if success:
                logger.info(f"✅ 预测执行成功: {prediction['type']}")
            else:
                logger.error(f"❌ 预测执行失败: {prediction['type']}")
                
        except Exception as e:
            logger.error(f"❌ 执行预测时出错: {e}")
    
    def _open_website(self, prediction: Dict) -> bool:
        """打开网站"""
        try:
            url = prediction['url']
            domain = prediction['domain']
            
            # 特殊处理一些常见网站
            if domain == 'github.com' and prediction['page_title']:
                # 尝试构建更具体的GitHub URL
                if 'MEMO' in prediction['page_title']:
                    url = "https://github.com/OSH-2025/MEMO"
                elif 'self-llm' in prediction['page_title']:
                    url = "https://github.com/datawhalechina/self-llm"
            elif domain == 'www.douban.com':
                url = "https://www.douban.com"
            
            logger.info(f"🌐 打开网站: {url}")
            
            # 优先使用Chrome，其次Edge，最后默认浏览器
            if self.app_paths['chrome']:
                subprocess.Popen([self.app_paths['chrome'], url])
            elif self.app_paths['edge']:
                subprocess.Popen([self.app_paths['edge'], url])
            else:
                webbrowser.open(url)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 打开网站失败: {e}")
            return False
    
    def _open_application(self, prediction: Dict) -> bool:
        """打开应用程序"""
        try:
            app_name = prediction['app_name'].lower()
            
            # 映射应用程序名称
            app_mapping = {
                'code.exe': 'vscode',
                'chrome.exe': 'chrome',
                'msedge.exe': 'edge',
                'notepad.exe': 'notepad',
                'calc.exe': 'calculator'
            }
            
            app_key = app_mapping.get(app_name, app_name)
            app_path = self.app_paths.get(app_key)
            
            if app_path and os.path.exists(app_path):
                logger.info(f"🖥️ 打开应用: {app_path}")
                subprocess.Popen([app_path])
                return True
            else:
                # 尝试直接执行
                logger.info(f"🖥️ 尝试打开应用: {app_name}")
                subprocess.Popen([app_name])
                return True
                
        except Exception as e:
            logger.error(f"❌ 打开应用失败: {e}")
            return False
    
    def _open_file(self, prediction: Dict) -> bool:
        """打开文件"""
        try:
            file_path = prediction['file_path']
            
            if os.path.exists(file_path):
                logger.info(f"📄 打开文件: {file_path}")
                os.startfile(file_path)
                return True
            else:
                logger.warning(f"⚠️ 文件不存在: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 打开文件失败: {e}")
            return False
    
    def get_execution_stats(self) -> Dict:
        """获取执行统计信息"""
        total_executions = len(self.execution_history)
        successful_executions = sum(1 for item in self.execution_history if item['success'])
        
        return {
            'total_executions': total_executions,
            'successful_executions': successful_executions,
            'success_rate': successful_executions / total_executions if total_executions > 0 else 0,
            'pending_executions': len([item for item in self.pending_executions if not item['executed']]),
            'execution_history': self.execution_history[-10:]  # 最近10次执行
        }
    
    def preview_prediction(self, prediction_text: str) -> bool:
        """预览预测结果（不执行）"""
        parsed = self.parse_prediction(prediction_text)
        
        if parsed:
            print(f"\n🔮 预测解析结果:")
            print(f"   类型: {parsed['type']}")
            
            if parsed['type'] == 'website':
                print(f"   网站: {parsed['domain']}")
                print(f"   页面: {parsed.get('page_title', '未指定')}")
                print(f"   URL: {parsed['url']}")
            elif parsed['type'] == 'application':
                print(f"   应用: {parsed['app_name']}")
                print(f"   窗口: {parsed.get('window_title', '未指定')}")
            elif parsed['type'] == 'file':
                print(f"   文件: {parsed['file_path']}")
            
            print(f"   置信度: {parsed['confidence']:.1%}")
            
            return True
        else:
            print(f"\n❌ 无法解析预测: {prediction_text}")
            return False

class PredictionValidator:
    """预测准确性验证器"""
    
    def __init__(self):
        self.validation_history = []
        self.pending_validations = []
    
    def add_prediction_for_validation(self, prediction: Dict, actual_activity_window: int = 60):
        """添加预测以供验证"""
        validation_item = {
            'prediction': prediction,
            'predicted_at': datetime.now(),
            'validation_window_end': datetime.now() + timedelta(seconds=actual_activity_window),
            'validated': False,
            'accuracy': None
        }
        
        self.pending_validations.append(validation_item)
        logger.info(f"📊 预测已加入验证队列，验证窗口: {actual_activity_window}秒")
    
    def validate_with_actual_activity(self, actual_activity: Dict):
        """用实际活动验证预测"""
        current_time = datetime.now()
        
        for validation_item in self.pending_validations:
            if validation_item['validated']:
                continue
                
            if current_time > validation_item['validation_window_end']:
                # 验证窗口过期，标记为不准确
                validation_item['validated'] = True
                validation_item['accuracy'] = 0.0
                continue
            
            # 计算预测与实际活动的匹配度
            accuracy = self._calculate_accuracy(
                validation_item['prediction'], 
                actual_activity
            )
            
            if accuracy > 0.5:  # 阈值可调整
                validation_item['validated'] = True
                validation_item['accuracy'] = accuracy
                
                result = {
                    'prediction': validation_item['prediction'],
                    'actual_activity': actual_activity,
                    'accuracy': accuracy,
                    'validated_at': current_time.isoformat()
                }
                
                self.validation_history.append(result)
                logger.info(f"✅ 预测验证成功，准确度: {accuracy:.1%}")
    
    def _calculate_accuracy(self, prediction: Dict, actual: Dict) -> float:
        """计算预测准确度"""
        try:
            if prediction['type'] != actual.get('type'):
                return 0.0
            
            if prediction['type'] == 'website':
                domain_match = prediction['domain'] == actual.get('domain')
                return 0.8 if domain_match else 0.0
            
            elif prediction['type'] == 'application':
                app_match = prediction['app_name'].lower() in actual.get('process_name', '').lower()
                return 0.7 if app_match else 0.0
            
            return 0.0
            
        except Exception as e:
            logger.error(f"❌ 计算准确度失败: {e}")
            return 0.0
    
    def get_validation_stats(self) -> Dict:
        """获取验证统计信息"""
        total_validations = len(self.validation_history)
        avg_accuracy = sum(item['accuracy'] for item in self.validation_history) / total_validations if total_validations > 0 else 0
        
        return {
            'total_validations': total_validations,
            'average_accuracy': avg_accuracy,
            'pending_validations': len([item for item in self.pending_validations if not item['validated']]),
            'recent_validations': self.validation_history[-5:]
        } 