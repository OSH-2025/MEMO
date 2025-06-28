"""
端到端用户行为预测和应用预优化系统
使用SSH隧道连接云服务器上的LLM模型
"""

import os
import json
import time
import queue
import threading
import subprocess
import psutil
import win32gui
import win32process
import requests
import logging
from datetime import datetime, timedelta
from collections import deque
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import re
import atexit

# 导入现有模块
try:
    from activity_monitor import ActivityMonitor
    from activity_analyzer import ActivityAnalyzer
except ImportError:
    print("警告: 无法导入activity_monitor或activity_analyzer模块，将使用内置的简化版本")
    ActivityMonitor = None
    ActivityAnalyzer = None

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('end_to_end_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('end_to_end_system')

class SSHTunnelManager:
    """SSH隧道管理器"""
    
    def __init__(self, ssh_config: Dict[str, Any]):
        self.ssh_config = ssh_config
        self.tunnel_process = None
        
    def create_tunnel(self) -> bool:
        """创建SSH隧道"""
        try:
            local_port = self.ssh_config['tunnel_local_port']
            remote_port = self.ssh_config['tunnel_remote_port']
            ssh_host = self.ssh_config['host']
            ssh_port = self.ssh_config['port']
            username = self.ssh_config['username']
            
            # SSH隧道命令
            ssh_command = [
                'ssh',
                '-L', f"{local_port}:localhost:{remote_port}",
                '-N',  # 不执行远程命令
                '-T',  # 禁用伪终端分配
                '-o', 'StrictHostKeyChecking=no',  # 自动接受主机密钥
                '-o', 'UserKnownHostsFile=/dev/null',  # 不保存主机密钥
                f"{username}@{ssh_host}",
                '-p', str(ssh_port)
            ]
            
            logger.info("正在建立SSH隧道...")
            logger.info("请在SSH提示时输入密码")
            
            # 启动SSH隧道进程
            self.tunnel_process = subprocess.Popen(
                ssh_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # 等待隧道建立
            time.sleep(5)
            
            # 检查进程是否还在运行
            if self.tunnel_process.poll() is None:
                logger.info(f"SSH隧道建立成功！本地端口: {local_port}")
                return True
            else:
                stdout, stderr = self.tunnel_process.communicate()
                logger.error(f"SSH隧道建立失败:")
                logger.error(f"stdout: {stdout.decode()}")
                logger.error(f"stderr: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"建立SSH隧道出错: {e}")
            return False
    
    def is_tunnel_alive(self) -> bool:
        """检查隧道是否存活"""
        if self.tunnel_process is None:
            return False
        return self.tunnel_process.poll() is None
    
    def close_tunnel(self):
        """关闭SSH隧道"""
        if self.tunnel_process:
            try:
                self.tunnel_process.terminate()
                self.tunnel_process.wait(timeout=5)
                logger.info("SSH隧道已关闭")
            except:
                try:
                    self.tunnel_process.kill()
                    logger.info("SSH隧道已强制关闭")
                except:
                    pass
            finally:
                self.tunnel_process = None

class LLMPredictor:
    """LLM预测器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.use_ssh_tunnel = config['llm'].get('use_ssh_tunnel', True)
        self.ssh_tunnel_manager = None
        
        if self.use_ssh_tunnel:
            self.api_url = f"http://localhost:{config['ssh']['tunnel_local_port']}"
            self.ssh_tunnel_manager = SSHTunnelManager(config['ssh'])
            
            # 检查是否已有SSH隧道在运行
            if not self._test_local_connection():
                logger.info("未检测到SSH隧道，请手动建立SSH隧道：")
                logger.info(f"ssh -L {config['ssh']['tunnel_local_port']}:localhost:{config['ssh']['tunnel_remote_port']} {config['ssh']['username']}@{config['ssh']['host']} -p {config['ssh']['port']}")
                logger.info("或者等待自动建立隧道...")
                
                # 尝试自动建立隧道（可能需要密码输入）
                if not self.ssh_tunnel_manager.create_tunnel():
                    logger.error("自动建立SSH隧道失败，请手动建立")
        else:
            self.api_url = f"http://{config['llm']['server_host']}:{config['llm']['server_port']}"
        
        self.use_local_backup = False
        
        # 注册清理函数
        atexit.register(self._cleanup)
        
        # 测试连接
        self._test_connection()
    
    def _test_local_connection(self) -> bool:
        """测试本地连接"""
        try:
            response = requests.get(f"http://localhost:{self.config['ssh']['tunnel_local_port']}/health", timeout=3)
            return response.status_code == 200
        except:
            return False
    
    def _cleanup(self):
        """清理资源"""
        if self.ssh_tunnel_manager:
            self.ssh_tunnel_manager.close_tunnel()
    
    def _test_connection(self):
        """测试连接"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"测试连接到: {self.api_url} (尝试 {attempt + 1}/{max_retries})")
                
                response = requests.get(f"{self.api_url}/health", timeout=10)
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"连接成功！")
                    logger.info(f"模型状态: {result.get('model_status')}")
                    
                    if result.get("model_status") == "loaded":
                        logger.info("✓ 云服务器LLM模型已就绪")
                        self.use_local_backup = False
                        return
                    else:
                        logger.warning("连接成功但模型未加载")
                        
                else:
                    logger.warning(f"连接响应异常: {response.status_code}")
                    
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"连接失败 (尝试 {attempt + 1}): 连接被拒绝")
                if attempt < max_retries - 1:
                    logger.info("等待5秒后重试...")
                    time.sleep(5)
                    
            except Exception as e:
                logger.error(f"连接测试出错: {e}")
                break
        
        logger.warning("无法连接到云服务器LLM，将使用本地备用模型")
        self.use_local_backup = True
    
    def predict_next_activity(self, activity_sequence: List[str]) -> Optional[Dict[str, Any]]:
        """预测下一个用户活动"""
        try:
            if not self.use_local_backup:
                # 检查SSH隧道是否还活着
                if self.ssh_tunnel_manager and not self.ssh_tunnel_manager.is_tunnel_alive():
                    logger.warning("SSH隧道已断开，尝试重新连接...")
                    if not self.ssh_tunnel_manager.create_tunnel():
                        logger.error("重新建立SSH隧道失败，切换到本地备用模型")
                        self.use_local_backup = True
                        return self._predict_via_local_backup(activity_sequence)
                
                return self._predict_via_cloud_api(activity_sequence)
            else:
                return self._predict_via_local_backup(activity_sequence)
        except Exception as e:
            logger.error(f"预测失败: {e}")
            return None
    
    def _predict_via_cloud_api(self, activity_sequence: List[str]) -> Optional[Dict[str, Any]]:
        """通过云服务器API进行预测"""
        try:
            payload = {
                "instruction": "根据用户最近的活动序列，预测下一个最有可能的用户活动。请确保输出格式与输入格式一致，应为\"时间 - 操作\"的形式。",
                "input": "用户活动序列:\n" + "\n".join(activity_sequence)
            }
            
            logger.info("🔮 向云服务器LLM发送预测请求...")
            
            response = requests.post(
                f"{self.api_url}/predict",
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                prediction_text = result.get("prediction", "")
                confidence = result.get("confidence", 0.5)
                
                logger.info(f"✓ 云服务器预测完成，置信度: {confidence:.2f}")
                logger.info(f"📝 预测结果: {prediction_text}")
                
                parsed_result = self._parse_prediction(prediction_text)
                if parsed_result:
                    parsed_result["confidence"] = confidence
                    return parsed_result
                else:
                    logger.warning("❌ 无法解析云服务器预测结果")
                    return None
            else:
                logger.error(f"❌ API请求失败: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 云服务器API调用出错: {e}")
            return None
    
    def _predict_via_local_backup(self, activity_sequence: List[str]) -> Optional[Dict[str, Any]]:
        """使用本地备用模型进行预测"""
        try:
            logger.info("🏠 使用本地备用预测模型")
            return self._rule_based_prediction(activity_sequence)
        except Exception as e:
            logger.error(f"本地预测失败: {e}")
            return None
    
    def _rule_based_prediction(self, activity_sequence: List[str]) -> Optional[Dict[str, Any]]:
        """基于规则的预测"""
        if not activity_sequence:
            return None
        
        # 分析最近的活动
        recent_apps = []
        for activity in activity_sequence[-3:]:
            app_match = re.search(r'启动应用: (.+)', activity)
            if not app_match:
                app_match = re.search(r'切换到窗口: .+ \(应用: (.+)\)', activity)
            if not app_match:
                app_match = re.search(r'应用: (.+)\)', activity)
            
            if app_match:
                app_name = app_match.group(1).strip()
                recent_apps.append(app_name)
        
        if not recent_apps:
            return None
        
        # 简单的应用切换模式
        app_patterns = {
            'chrome.exe': ['notepad.exe', 'explorer.exe', 'code.exe'],
            'notepad.exe': ['chrome.exe', 'explorer.exe'],
            'explorer.exe': ['notepad.exe', 'chrome.exe'],
            'code.exe': ['chrome.exe', 'cmd.exe'],
            'cmd.exe': ['code.exe', 'explorer.exe']
        }
        
        most_recent_app = recent_apps[-1] if recent_apps else None
        if most_recent_app in app_patterns:
            predicted_app = app_patterns[most_recent_app][0]
        else:
            predicted_app = 'chrome.exe'
        
        predicted_time = datetime.now() + timedelta(minutes=2)
        prediction_text = f"{predicted_time.strftime('%Y-%m-%d %H:%M:%S')} - 启动应用: {predicted_app}"
        
        result = self._parse_prediction(prediction_text)
        if result:
            result["confidence"] = 0.6
        
        return result
    
    def _parse_prediction(self, prediction_text: str) -> Optional[Dict[str, Any]]:
        """解析预测文本 - 重点提取应用而非具体内容"""
        try:
            prediction_text = prediction_text.strip()
            logger.info(f"🔍 开始解析预测: {prediction_text}")
            
            # 解析时间
            time_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', prediction_text)
            if not time_match:
                predicted_time = datetime.now() + timedelta(minutes=2)
            else:
                predicted_time_str = time_match.group(1)
                predicted_time = datetime.strptime(predicted_time_str, '%Y-%m-%d %H:%M:%S')
            
            # 从预测中提取应用信息
            app_name = self._extract_app_from_prediction(prediction_text)
            
            if app_name:
                # 判断预测类型
                action_type = self._determine_action_type(prediction_text, app_name)
                
                logger.info(f"✅ 解析成功: {action_type} {app_name} 在 {predicted_time.strftime('%H:%M:%S')}")
                return {
                    "predicted_time": predicted_time,
                    "app_name": app_name,
                    "action_type": action_type,
                    "confidence": 0.7,
                    "raw_prediction": prediction_text,
                    "predicted_content": self._extract_content_info(prediction_text)
                }
            else:
                logger.warning(f"❌ 无法提取应用名: {prediction_text}")
                return None
                
        except Exception as e:
            logger.error(f"解析失败: {e}")
            return None

    def _extract_app_from_prediction(self, text: str) -> Optional[str]:
        """从预测文本中提取应用名"""
        
        # 方法1: 从(应用: xxx)中提取
        app_match = re.search(r'\(应用:\s*(.+?)\)', text)
        if app_match:
            app_name = app_match.group(1).strip()
            return self._normalize_app_name(app_name)
        
        # 方法2: 从已知模式中匹配
        app_patterns = {
            r'Visual Studio Code': 'Code.exe',
            r'Microsoft.*Edge': 'msedge.exe',
            r'Google Chrome': 'chrome.exe',
            r'文件资源管理器': 'explorer.exe',
            r'QQ': 'QQ.exe',
            r'微信': 'WeChat.exe',
            r'截图工具': 'SnippingTool.exe',
            r'记事本': 'notepad.exe',
            r'计算器': 'calc.exe'
        }
        
        for pattern, app_name in app_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                return app_name
        
        return None

    def _normalize_app_name(self, app_name: str) -> str:
        """标准化应用名"""
        app_mapping = {
            'Code.exe': 'Code.exe',
            'msedge.exe': 'msedge.exe', 
            'chrome.exe': 'chrome.exe',
            'explorer.exe': 'explorer.exe',
            'QQ.exe': 'QQ.exe',
            'WeChat.exe': 'WeChat.exe',
            'SnippingTool.exe': 'SnippingTool.exe',
            'notepad.exe': 'notepad.exe',
            'calc.exe': 'calc.exe'
        }
        
        return app_mapping.get(app_name, app_name)

    def _determine_action_type(self, text: str, app_name: str) -> str:
        """判断预测的动作类型"""
        if "切换到窗口" in text:
            return "切换窗口"
        elif "启动应用" in text:
            return "启动应用"
        else:
            return "使用应用"

    def _extract_content_info(self, text: str) -> Dict[str, Any]:
        """提取预测的内容信息（用于更精确的预加载）"""
        content_info = {}
        
        # 提取网页URL或标题
        if "切换到窗口:" in text:
            window_match = re.search(r'切换到窗口:\s*(.+?)\s*\(应用:', text)
            if window_match:
                window_title = window_match.group(1).strip()
                content_info['window_title'] = window_title
                
                # 检查是否是网页
                if any(indicator in window_title.lower() for indicator in ['http', 'www', '.com', '.cn', 'bilibili', 'github']):
                    content_info['content_type'] = 'webpage'
                    content_info['website'] = self._extract_website_info(window_title)
                else:
                    content_info['content_type'] = 'file_or_app'
        
        return content_info

    def _extract_website_info(self, title: str) -> str:
        """从窗口标题中提取网站信息"""
        website_patterns = {
            'bilibili': 'bilibili.com',
            'github': 'github.com', 
            'google': 'google.com',
            'baidu': 'baidu.com',
            '智星云': 'zh-galaxy.com'
        }
        
        title_lower = title.lower()
        for keyword, website in website_patterns.items():
            if keyword in title_lower:
                return website
        
        return 'unknown'

class ApplicationManager:
    """应用程序管理器"""
    
    def __init__(self):
        self.preloaded_apps = {}
        self.app_executables = {
            'notepad.exe': 'notepad.exe',
            'calc.exe': 'calc.exe',
            'chrome.exe': r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            'explorer.exe': 'explorer.exe',
            'cmd.exe': 'cmd.exe'
        }
        
        # 验证应用路径
        valid_apps = {}
        for app_name, path in self.app_executables.items():
            if os.path.exists(path) or app_name in ['notepad.exe', 'calc.exe', 'explorer.exe', 'cmd.exe']:
                valid_apps[app_name] = path
        self.app_executables = valid_apps
    
    def is_app_running(self, app_name: str) -> bool:
        """检查应用是否正在运行"""
        try:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'].lower() == app_name.lower():
                    return True
            return False
        except:
            return False
    
    def preload_application(self, app_name: str, predicted_time: datetime) -> bool:
        """预加载应用程序"""
        try:
            if self.is_app_running(app_name):
                logger.info(f"✓ 应用 {app_name} 已在运行")
                return True
            
            if app_name in self.preloaded_apps:
                logger.info(f"✓ 应用 {app_name} 已预加载")
                return True
            
            if app_name not in self.app_executables:
                logger.warning(f"❌ 未知应用: {app_name}")
                return False
            
            executable_path = self.app_executables[app_name]
            
            # 在预测时间前2分钟预加载
            preload_time = predicted_time - timedelta(minutes=2)
            current_time = datetime.now()
            
            if current_time >= preload_time:
                return self._launch_application(app_name, executable_path, predicted_time)
            else:
                delay_seconds = (preload_time - current_time).total_seconds()
                timer = threading.Timer(delay_seconds, self._launch_application, 
                                      args=(app_name, executable_path, predicted_time))
                timer.start()
                
                logger.info(f"⏰ 安排在 {delay_seconds:.1f} 秒后预加载应用 {app_name}")
                return True
                
        except Exception as e:
            logger.error(f"预加载应用 {app_name} 出错: {e}")
            return False
    
    def _launch_application(self, app_name: str, executable_path: str, predicted_time: datetime) -> bool:
        """启动应用程序"""
        try:
            logger.info(f"🚀 开始预加载应用: {app_name}")
            
            process = subprocess.Popen([executable_path], 
                                     stdout=subprocess.DEVNULL, 
                                     stderr=subprocess.DEVNULL)
            
            self.preloaded_apps[app_name] = {
                'process': process,
                'pid': process.pid,
                'predicted_time': predicted_time,
                'preload_time': datetime.now(),
                'used': False
            }
            
            logger.info(f"✓ 成功预加载应用 {app_name} (PID: {process.pid})")
            
            # 安排检查和清理
            cleanup_delay = (predicted_time + timedelta(minutes=3) - datetime.now()).total_seconds()
            if cleanup_delay > 0:
                timer = threading.Timer(cleanup_delay, self._check_and_cleanup_app, args=(app_name,))
                timer.start()
            
            return True
            
        except Exception as e:
            logger.error(f"启动应用 {app_name} 失败: {e}")
            return False
    
    def mark_app_as_used(self, app_name: str):
        """标记应用为已使用"""
        if app_name in self.preloaded_apps:
            self.preloaded_apps[app_name]['used'] = True
            logger.info(f"🎯 预测成功！用户使用了预加载的应用: {app_name}")
    
    def _check_and_cleanup_app(self, app_name: str):
        """检查并清理未使用的预加载应用"""
        if app_name not in self.preloaded_apps:
            return
        
        app_info = self.preloaded_apps[app_name]
        
        if not app_info['used']:
            try:
                process = app_info['process']
                if process.poll() is None:
                    process.terminate()
                    logger.info(f"🗑️ 预测失败，已关闭未使用的应用: {app_name}")
            except Exception as e:
                logger.error(f"关闭应用 {app_name} 出错: {e}")
        
        del self.preloaded_apps[app_name]

class RealTimeActivityQueue:
    """实时活动队列"""
    
    def __init__(self, max_size: int = 10):
        self.queue = deque(maxlen=max_size)
        self.lock = threading.Lock()
        
    def add_activity(self, activity: Dict[str, Any]):
        """添加新活动到队列"""
        with self.lock:
            formatted_activity = self._format_activity(activity)
            self.queue.append(formatted_activity)
            logger.info(f"📊 新活动: {formatted_activity}")
    
    def get_recent_activities(self, count: int = None) -> List[str]:
        """获取最近的活动"""
        with self.lock:
            if count is None:
                return list(self.queue)
            else:
                return list(self.queue)[-count:]
    
    def is_activity_queue_changed(self, last_hash: int) -> Tuple[bool, int]:
        """检查活动队列是否发生变化"""
        with self.lock:
            current_hash = hash(tuple(self.queue))
            return current_hash != last_hash, current_hash
    
    def _format_activity(self, activity: Dict[str, Any]) -> str:
        """格式化活动为字符串"""
        activity_type = activity.get('type', 'unknown')
        time_str = activity.get('datetime', datetime.now()).strftime('%Y-%m-%d %H:%M:%S')
        
        if activity_type == 'window_focus':
            return f"{time_str} - 切换到窗口: {activity.get('window_title', '')} (应用: {activity.get('process_name', '')})"
        elif activity_type == 'process_start':
            return f"{time_str} - 启动应用: {activity.get('process_name', '')}"
        elif activity_type == 'process_end':
            return f"{time_str} - 关闭应用: {activity.get('process_name', '')}"
        else:
            return f"{time_str} - {activity_type}"

class EndToEndSystem:
    """端到端预测和优化系统"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.queue_size = config['system']['queue_size']
        self.prediction_window = config['system']['prediction_window']
        
        # 初始化组件
        self.activity_queue = RealTimeActivityQueue(max_size=self.queue_size)
        self.llm_predictor = LLMPredictor(config)
        self.app_manager = ApplicationManager()
        
        # 运行状态
        self.running = False
        self.monitor_thread = None
        self.prediction_thread = None
        
        # 预测状态
        self.last_queue_hash = 0
        self.prediction_cooldown = config['system'].get('prediction_cooldown', 30)
        self.last_prediction_time = 0
        
        logger.info("🎉 端到端系统初始化完成")
    
    def start(self):
        """启动系统"""
        logger.info("🚀 启动端到端预测和优化系统...")
        self.running = True
        
        # 启动监控线程
        self.monitor_thread = threading.Thread(target=self._monitor_activities, daemon=True)
        self.monitor_thread.start()
        
        # 启动预测线程
        self.prediction_thread = threading.Thread(target=self._prediction_loop, daemon=True)
        self.prediction_thread.start()
        
        logger.info("✓ 端到端系统已启动")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("用户中断，正在停止系统...")
            self.stop()
    
    def stop(self):
        """停止系统"""
        logger.info("🛑 正在停止端到端系统...")
        self.running = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        if self.prediction_thread and self.prediction_thread.is_alive():
            self.prediction_thread.join(timeout=5)
        
        logger.info("✓ 端到端系统已停止")
    
    def _monitor_activities(self):
        """监控用户活动"""
        logger.info("👁️ 开始监控用户活动...")
        
        last_window = None
        check_count = 0
        
        while self.running:
            try:
                current_time = datetime.now()
                check_count += 1
                
                # 每10次检查输出一次心跳信息
                if check_count % 10 == 0:
                    logger.info(f"💓 系统心跳检查 #{check_count}")
                
                # 检查活跃窗口变化
                window_info = self._get_current_window_info()
                if window_info and window_info != last_window:
                    activity = {
                        'type': 'window_focus',
                        'datetime': current_time,
                        **window_info
                    }
                    self.activity_queue.add_activity(activity)
                    last_window = window_info
                    
                    # 检查是否使用了预加载的应用
                    app_name = window_info.get('process_name', '')
                    if app_name:
                        self.app_manager.mark_app_as_used(app_name)
                
                time.sleep(3)  # 每3秒检查一次
                
            except Exception as e:
                logger.error(f"监控活动时出错: {e}")
                time.sleep(5)
    
    def _get_current_window_info(self) -> Optional[Dict[str, Any]]:
        """获取当前活跃窗口信息"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd == 0:
                return None
                
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return None
                
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                process = psutil.Process(pid)
                process_name = process.name()
            except:
                process_name = "unknown"
                
            return {
                "window_title": title,
                "process_name": process_name,
                "process_id": pid
            }
        except:
            return None
    
    def _prediction_loop(self):
        """预测循环"""
        logger.info("🔮 开始预测循环...")
        
        while self.running:
            try:
                # 检查队列是否发生变化
                queue_changed, current_hash = self.activity_queue.is_activity_queue_changed(self.last_queue_hash)
                
                if queue_changed:
                    self.last_queue_hash = current_hash
                    
                    # 检查冷却时间
                    current_time = time.time()
                    if current_time - self.last_prediction_time >= self.prediction_cooldown:
                        self._make_prediction()
                        self.last_prediction_time = current_time
                
                time.sleep(5)  # 每5秒检查一次
                
            except Exception as e:
                logger.error(f"预测循环出错: {e}")
                time.sleep(10)
    
    def _make_prediction(self):
        """执行预测"""
        try:
            recent_activities = self.activity_queue.get_recent_activities(self.prediction_window)
            
            if len(recent_activities) < 3:
                return
            
            logger.info(f"🔮 开始预测，基于最近 {len(recent_activities)} 个活动")
            
            prediction = self.llm_predictor.predict_next_activity(recent_activities)
            
            if prediction:
                app_name = prediction['app_name']
                predicted_time = prediction['predicted_time']
                confidence = prediction.get('confidence', 0.0)
                
                logger.info(f"📈 预测结果: 用户可能在 {predicted_time.strftime('%H:%M:%S')} 使用 {app_name} (置信度: {confidence:.2f})")
                
                # 如果置信度足够高，执行预加载
                confidence_threshold = self.config['system'].get('confidence_threshold', 0.6)
                if confidence >= confidence_threshold:
                    success = self.app_manager.preload_application(app_name, predicted_time)
                    if success:
                        logger.info(f"✓ 已安排预加载应用: {app_name}")
                else:
                    logger.info(f"📊 置信度过低 ({confidence:.2f} < {confidence_threshold})，跳过预加载")
            else:
                logger.info("❌ 预测失败，未获得有效预测结果")
                
        except Exception as e:
            logger.error(f"执行预测时出错: {e}")

def create_default_config() -> Dict[str, Any]:
    """创建默认配置"""
    return {
        "system": {
            "queue_size": 10,
            "prediction_window": 5,
            "prediction_cooldown": 30,
            "confidence_threshold": 0.6
        },
        "llm": {
            "use_ssh_tunnel": True,
            "server_host": "js2.blockelite.cn",
            "server_port": 8000,
            "timeout": 15
        },
        "ssh": {
            "host": "js2.blockelite.cn",
            "port": 10116,
            "username": "root",
            "tunnel_local_port": 8000,
            "tunnel_remote_port": 8000
        }
    }

def main():
    """主函数"""
    print("🎯 端到端用户行为预测和应用优化系统")
    print("=" * 60)
    
    # 加载或创建配置
    config_path = "config.json"
    if not os.path.exists(config_path):
        print(f"📝 创建默认配置文件: {config_path}")
        config = create_default_config()
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    else:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    
    # 显示配置信息
    print(f"📋 系统配置:")
    print(f"  - 活动队列大小: {config['system']['queue_size']}")
    print(f"  - 预测窗口大小: {config['system']['prediction_window']}")
    print(f"  - 使用SSH隧道: {config['llm']['use_ssh_tunnel']}")
    if config['llm']['use_ssh_tunnel']:
        print(f"  - SSH服务器: {config['ssh']['host']}:{config['ssh']['port']}")
        print(f"  - 本地隧道端口: {config['ssh']['tunnel_local_port']}")
    print(f"  - 置信度阈值: {config['system']['confidence_threshold']}")
    print()
    
    print("⚠️  重要提示:")
    print("1. 请确保已在云服务器上启动了LLM API服务")
    print("2. 如果使用SSH隧道，请手动建立SSH连接：")
    print(f"   ssh -L {config['ssh']['tunnel_local_port']}:localhost:{config['ssh']['tunnel_remote_port']} {config['ssh']['username']}@{config['ssh']['host']} -p {config['ssh']['port']}")
    print("3. 系统将自动监控您的活动并进行预测")
    print()
    
    input("按回车键继续启动系统...")
    
    try:
        # 检查必要的目录
        for directory in ['logs']:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        # 初始化并启动系统
        system = EndToEndSystem(config)
        
        print("🚀 系统启动中...")
        print("📊 开始监控用户活动...")
        print("🔮 LLM预测服务已就绪...")
        print("按 Ctrl+C 停止系统")
        print()
        
        system.start()
        
    except KeyboardInterrupt:
        print("\n👋 用户中断，系统已安全停止")
    except Exception as e:
        print(f"❌ 系统运行出错: {e}")
        logger.error(f"系统运行出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()