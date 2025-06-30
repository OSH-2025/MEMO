"""
端到端用户行为预测和应用预优化系统 - 增强版
支持应用预加载和智能网页预加载
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
import webbrowser
import urllib.parse
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

class WebContentPreloader:
    """网页内容预加载器"""
    
    def __init__(self):
        self.preloaded_pages = {}
        self.website_patterns = self._load_website_patterns()
        self.browser_paths = self._detect_browsers()
        
    def _load_website_patterns(self) -> Dict[str, Dict[str, Any]]:
        """加载网站模式识别配置"""
        return {
            'bilibili': {
                'domains': ['bilibili.com', 'b23.tv'],
                'common_urls': [
                    'https://www.bilibili.com',
                    'https://www.bilibili.com/video/',
                    'https://live.bilibili.com'
                ],
                'keywords': ['bilibili', '哔哩哔哩', 'b站'],
                'preload_strategy': 'homepage_first'
            },
            'github': {
                'domains': ['github.com'],
                'common_urls': [
                    'https://github.com',
                    'https://github.com/trending'
                ],
                'keywords': ['github'],
                'preload_strategy': 'homepage_first'
            },
            'google': {
                'domains': ['google.com', 'google.cn'],
                'common_urls': [
                    'https://www.google.com',
                    'https://www.google.com/search'
                ],
                'keywords': ['google', '谷歌'],
                'preload_strategy': 'search_ready'
            },
            'baidu': {
                'domains': ['baidu.com'],
                'common_urls': [
                    'https://www.baidu.com',
                    'https://www.baidu.com/s'
                ],
                'keywords': ['baidu', '百度'],
                'preload_strategy': 'search_ready'
            },
            'zhihu': {
                'domains': ['zhihu.com'],
                'common_urls': [
                    'https://www.zhihu.com',
                    'https://www.zhihu.com/hot'
                ],
                'keywords': ['zhihu', '知乎'],
                'preload_strategy': 'homepage_first'
            },
            'youtube': {
                'domains': ['youtube.com', 'youtu.be'],
                'common_urls': [
                    'https://www.youtube.com',
                    'https://www.youtube.com/trending'
                ],
                'keywords': ['youtube'],
                'preload_strategy': 'homepage_first'
            },
            'weibo': {
                'domains': ['weibo.com'],
                'common_urls': [
                    'https://weibo.com',
                    'https://weibo.com/hot'
                ],
                'keywords': ['weibo', '微博'],
                'preload_strategy': 'homepage_first'
            }
        }
    
    def _detect_browsers(self) -> Dict[str, str]:
        """检测系统中可用的浏览器"""
        browsers = {}
        
        # Chrome
        chrome_paths = [
            r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
            r'C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe'.format(os.getenv('USERNAME', ''))
        ]
        
        for path in chrome_paths:
            if os.path.exists(path):
                browsers['chrome'] = path
                break
        
        # Edge
        edge_paths = [
            r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
            r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
        ]
        
        for path in edge_paths:
            if os.path.exists(path):
                browsers['edge'] = path
                break
        
        # Firefox
        firefox_paths = [
            r'C:\Program Files\Mozilla Firefox\firefox.exe',
            r'C:\Program Files (x86)\Mozilla Firefox\firefox.exe'
        ]
        
        for path in firefox_paths:
            if os.path.exists(path):
                browsers['firefox'] = path
                break
        
        logger.info(f"🌐 检测到的浏览器: {list(browsers.keys())}")
        return browsers
    
    def extract_website_info(self, window_title: str, window_url: str = None) -> Optional[Dict[str, Any]]:
        """从窗口标题和URL中提取网站信息"""
        try:
            website_info = {
                'website_type': 'unknown',
                'predicted_url': None,
                'preload_strategy': 'default',
                'confidence': 0.0
            }
            
            title_lower = window_title.lower()
            
            # 检查每个网站模式
            for site_name, config in self.website_patterns.items():
                confidence = 0.0
                
                # 关键词匹配
                for keyword in config['keywords']:
                    if keyword in title_lower:
                        confidence += 0.3
                
                # 域名匹配
                for domain in config['domains']:
                    if domain in title_lower:
                        confidence += 0.5
                
                # URL匹配（如果提供了URL）
                if window_url:
                    for domain in config['domains']:
                        if domain in window_url:
                            confidence += 0.4
                
                # 如果置信度足够高，选择这个网站
                if confidence > website_info['confidence']:
                    website_info.update({
                        'website_type': site_name,
                        'predicted_url': config['common_urls'][0],
                        'preload_strategy': config['preload_strategy'],
                        'confidence': confidence,
                        'all_urls': config['common_urls']
                    })
            
            return website_info if website_info['confidence'] > 0.2 else None
            
        except Exception as e:
            logger.error(f"提取网站信息失败: {e}")
            return None
    
    def preload_webpage(self, website_info: Dict[str, Any], browser_preference: str = 'chrome') -> bool:
        """预加载网页"""
        try:
            website_type = website_info['website_type']
            predicted_url = website_info['predicted_url']
            strategy = website_info['preload_strategy']
            
            logger.info(f"🌐 开始预加载网页: {website_type} ({predicted_url})")
            
            # 选择浏览器
            browser_path = self._select_browser(browser_preference)
            if not browser_path:
                logger.warning("未找到可用的浏览器")
                return False
            
            # 根据策略预加载
            success = False
            if strategy == 'homepage_first':
                success = self._preload_homepage(browser_path, predicted_url, website_type)
            elif strategy == 'search_ready':
                success = self._preload_search_page(browser_path, predicted_url, website_type)
            else:
                success = self._preload_default(browser_path, predicted_url, website_type)
            
            if success:
                self.preloaded_pages[website_type] = {
                    'url': predicted_url,
                    'browser': browser_preference,
                    'preload_time': datetime.now(),
                    'used': False
                }
                logger.info(f"✅ 网页预加载成功: {website_type}")
            
            return success
            
        except Exception as e:
            logger.error(f"预加载网页失败: {e}")
            return False
    
    def _select_browser(self, preference: str) -> Optional[str]:
        """选择浏览器"""
        # 优先使用指定的浏览器
        if preference in self.browser_paths:
            return self.browser_paths[preference]
        
        # 备选方案
        priority_order = ['chrome', 'edge', 'firefox']
        for browser in priority_order:
            if browser in self.browser_paths:
                return self.browser_paths[browser]
        
        return None
    
    def _preload_homepage(self, browser_path: str, url: str, website_type: str) -> bool:
        """预加载网站首页"""
        try:
            # 在新窗口中打开，但最小化
            subprocess.Popen([
                browser_path, 
                '--new-window',
                '--start-minimized',
                url
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            logger.info(f"🚀 已预加载 {website_type} 首页")
            return True
            
        except Exception as e:
            logger.error(f"预加载首页失败: {e}")
            return False
    
    def _preload_search_page(self, browser_path: str, url: str, website_type: str) -> bool:
        """预加载搜索页面"""
        try:
            # 对于搜索引擎，预加载搜索页面
            subprocess.Popen([
                browser_path,
                '--new-window', 
                '--start-minimized',
                url
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            logger.info(f"🔍 已预加载 {website_type} 搜索页面")
            return True
            
        except Exception as e:
            logger.error(f"预加载搜索页面失败: {e}")
            return False
    
    def _preload_default(self, browser_path: str, url: str, website_type: str) -> bool:
        """默认预加载策略"""
        try:
            subprocess.Popen([
                browser_path,
                '--new-window',
                '--start-minimized', 
                url
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            logger.info(f"📄 已预加载 {website_type} 默认页面")
            return True
            
        except Exception as e:
            logger.error(f"默认预加载失败: {e}")
            return False
    
    def mark_webpage_as_used(self, website_type: str):
        """标记网页为已使用"""
        if website_type in self.preloaded_pages:
            self.preloaded_pages[website_type]['used'] = True
            logger.info(f"🎯 网页预测成功！用户访问了预加载的网站: {website_type}")
    
    def cleanup_unused_pages(self):
        """清理未使用的预加载页面"""
        current_time = datetime.now()
        to_remove = []
        
        for website_type, info in self.preloaded_pages.items():
            preload_time = info['preload_time']
            used = info['used']
            
            # 如果超过10分钟未使用，标记为清理
            if not used and (current_time - preload_time).total_seconds() > 600:
                to_remove.append(website_type)
                logger.info(f"🗑️ 清理未使用的预加载页面: {website_type}")
        
        for website_type in to_remove:
            del self.preloaded_pages[website_type]

class SmartApplicationManager:
    """智能应用程序管理器 - 支持应用和网页预加载"""
    
    def __init__(self):
        self.preloaded_apps = {}
        self.web_preloader = WebContentPreloader()
        self.app_executables = self._detect_applications()
        
    def _detect_applications(self) -> Dict[str, str]:
        """检测系统中可用的应用程序"""
        apps = {
            'notepad.exe': 'notepad.exe',
            'calc.exe': 'calc.exe', 
            'explorer.exe': 'explorer.exe',
            'cmd.exe': 'cmd.exe'
        }
        
        # 检测常用应用
        app_paths = {
            'Code.exe': [
                r'C:\Users\{}\AppData\Local\Programs\Microsoft VS Code\Code.exe'.format(os.getenv('USERNAME', '')),
                r'C:\Program Files\Microsoft VS Code\Code.exe'
            ],
            'chrome.exe': [
                r'C:\Program Files\Google\Chrome\Application\chrome.exe',
                r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
            ],
            'msedge.exe': [
                r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
                r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
            ],
            'QQ.exe': [
                r'C:\Program Files (x86)\Tencent\QQ\Bin\QQ.exe',
                r'C:\Program Files\Tencent\QQ\Bin\QQ.exe'
            ],
            'WeChat.exe': [
                r'C:\Program Files (x86)\Tencent\WeChat\WeChat.exe',
                r'C:\Program Files\Tencent\WeChat\WeChat.exe'
            ]
        }
        
        for app_name, paths in app_paths.items():
            for path in paths:
                if os.path.exists(path):
                    apps[app_name] = path
                    break
        
        logger.info(f"📱 检测到的应用: {list(apps.keys())}")
        return apps
    
    def is_app_running(self, app_name: str) -> bool:
        """检查应用是否正在运行"""
        try:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'].lower() == app_name.lower():
                    return True
            return False
        except:
            return False
    
    def smart_preload(self, prediction: Dict[str, Any]) -> bool:
        """智能预加载 - 支持应用和网页"""
        try:
            app_name = prediction['app_name']
            predicted_time = prediction['predicted_time']
            confidence = prediction.get('confidence', 0.0)
            content_info = prediction.get('predicted_content', {})
            
            logger.info(f"🤖 智能预加载分析: {app_name} (置信度: {confidence:.2f})")
            
            # 检查置信度阈值
            if confidence < 0.6:
                logger.info(f"📊 置信度过低，跳过预加载")
                return False
            
            success = False
            
            # 如果是浏览器应用且预测了网页内容
            if app_name in ['chrome.exe', 'msedge.exe'] and content_info:
                success = self._preload_browser_with_content(app_name, content_info, predicted_time)
            else:
                # 普通应用预加载
                success = self._preload_application(app_name, predicted_time)
            
            return success
            
        except Exception as e:
            logger.error(f"智能预加载失败: {e}")
            return False
    
    def _preload_browser_with_content(self, browser_app: str, content_info: Dict[str, Any], predicted_time: datetime) -> bool:
        """预加载浏览器及其内容"""
        try:
            window_title = content_info.get('window_title', '')
            content_type = content_info.get('content_type', 'unknown')
            
            logger.info(f"🌐 预加载浏览器内容: {window_title}")
            
            # 提取网站信息
            website_info = self.web_preloader.extract_website_info(window_title)
            
            if website_info and content_type == 'webpage':
                # 预加载网页内容
                browser_pref = 'chrome' if 'chrome' in browser_app else 'edge'
                
                # 计算预加载时间
                preload_time = predicted_time - timedelta(minutes=1)
                current_time = datetime.now()
                
                if current_time >= preload_time:
                    return self.web_preloader.preload_webpage(website_info, browser_pref)
                else:
                    delay = (preload_time - current_time).total_seconds()
                    timer = threading.Timer(delay, self.web_preloader.preload_webpage, 
                                          args=(website_info, browser_pref))
                    timer.start()
                    logger.info(f"⏰ 安排在 {delay:.1f} 秒后预加载网页")
                    return True
            else:
                # 普通浏览器预加载
                return self._preload_application(browser_app, predicted_time)
                
        except Exception as e:
            logger.error(f"预加载浏览器内容失败: {e}")
            return False
    
    def _preload_application(self, app_name: str, predicted_time: datetime) -> bool:
        """预加载普通应用程序"""
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
            
            # 计算预加载时间
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
            
            # 特殊处理某些应用
            if app_name in ['chrome.exe', 'msedge.exe']:
                # 浏览器最小化启动
                process = subprocess.Popen([executable_path, '--start-minimized'], 
                                         stdout=subprocess.DEVNULL, 
                                         stderr=subprocess.DEVNULL)
            else:
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
            
            logger.info(f"✅ 成功预加载应用 {app_name} (PID: {process.pid})")
            
            # 安排检查和清理
            cleanup_delay = (predicted_time + timedelta(minutes=5) - datetime.now()).total_seconds()
            if cleanup_delay > 0:
                timer = threading.Timer(cleanup_delay, self._check_and_cleanup_app, args=(app_name,))
                timer.start()
            
            return True
            
        except Exception as e:
            logger.error(f"启动应用 {app_name} 失败: {e}")
            return False
    
    def mark_app_as_used(self, app_name: str, window_title: str = ""):
        """标记应用为已使用，并处理网页使用情况"""
        # 标记应用使用
        if app_name in self.preloaded_apps:
            self.preloaded_apps[app_name]['used'] = True
            logger.info(f"🎯 应用预测成功！用户使用了预加载的应用: {app_name}")
        
        # 如果是浏览器，尝试标记网页使用
        if app_name in ['chrome.exe', 'msedge.exe'] and window_title:
            website_info = self.web_preloader.extract_website_info(window_title)
            if website_info:
                website_type = website_info['website_type']
                self.web_preloader.mark_webpage_as_used(website_type)
    
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
    
    def periodic_cleanup(self):
        """定期清理"""
        try:
            self.web_preloader.cleanup_unused_pages()
        except Exception as e:
            logger.error(f"定期清理出错: {e}")

# 更新LLMPredictor类的解析方法
class LLMPredictor:
    """LLM预测器 - 增强版本"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.use_ssh_tunnel = config['llm'].get('use_ssh_tunnel', True)
        self.ssh_tunnel_manager = None
        
        if self.use_ssh_tunnel:
            self.api_url = f"http://localhost:{config['ssh']['tunnel_local_port']}"
            self.ssh_tunnel_manager = SSHTunnelManager(config['ssh'])
            
            if not self._test_local_connection():
                logger.info("未检测到SSH隧道，请手动建立SSH隧道：")
                logger.info(f"ssh -L {config['ssh']['tunnel_local_port']}:localhost:{config['ssh']['tunnel_remote_port']} {config['ssh']['username']}@{config['ssh']['host']} -p {config['ssh']['port']}")
        else:
            self.api_url = f"http://{config['llm']['server_host']}:{config['llm']['server_port']}"
        
        self.use_local_backup = False
        atexit.register(self._cleanup)
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
            # 增强的指令，明确要求预测应用和内容
            payload = {
                "instruction": """
根据用户最近的活动序列，预测下一个最有可能的用户活动。

请按以下格式输出：
时间 - 操作类型: 具体内容

支持的操作类型：
1. 启动应用: [应用名.exe]
2. 切换到窗口: [窗口标题] (应用: [应用名.exe])
3. 访问网页: [网站URL] (应用: [浏览器.exe])

示例：
2025-06-29 15:30:00 - 启动应用: chrome.exe
2025-06-29 15:30:00 - 切换到窗口: GitHub - Microsoft/vscode (应用: chrome.exe)
2025-06-29 15:30:00 - 访问网页: https://www.bilibili.com (应用: chrome.exe)
""",
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
        """基于规则的预测 - 增强版"""
        if not activity_sequence:
            return None
        
        # 分析最近的活动模式
        recent_patterns = self._analyze_activity_patterns(activity_sequence)
        
        # 生成预测
        prediction = self._generate_pattern_based_prediction(recent_patterns)
        
        return prediction
    
    def _analyze_activity_patterns(self, activity_sequence: List[str]) -> Dict[str, Any]:
        """分析活动模式"""
        patterns = {
            'recent_apps': [],
            'browser_activities': [],
            'frequent_websites': [],
            'time_patterns': []
        }
        
        for activity in activity_sequence[-5:]:
            # 提取应用信息
            app_match = re.search(r'\(应用: (.+?)\)', activity)
            if app_match:
                app_name = app_match.group(1).strip()
                patterns['recent_apps'].append(app_name)
                
                # 如果是浏览器活动，提取网站信息
                if app_name in ['chrome.exe', 'msedge.exe']:
                    window_match = re.search(r'切换到窗口: (.+?) \(应用:', activity)
                    if window_match:
                        window_title = window_match.group(1).strip()
                        patterns['browser_activities'].append(window_title)
                        
                        # 提取网站类型
                        website_patterns = ['bilibili', 'github', 'google', 'baidu', 'zhihu']
                        for site in website_patterns:
                            if site in window_title.lower():
                                patterns['frequent_websites'].append(site)
        
        return patterns
    
    def _generate_pattern_based_prediction(self, patterns: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """基于模式生成预测"""
        try:
            recent_apps = patterns['recent_apps']
            browser_activities = patterns['browser_activities']
            frequent_websites = patterns['frequent_websites']
            
            # 应用切换模式
            app_transitions = {
                'chrome.exe': ['Code.exe', 'notepad.exe', 'explorer.exe'],
                'Code.exe': ['chrome.exe', 'cmd.exe'],
                'explorer.exe': ['notepad.exe', 'Code.exe'],
                'notepad.exe': ['chrome.exe', 'explorer.exe']
            }
            
            # 网站访问模式
            website_transitions = {
                'bilibili': ['github', 'zhihu'],
                'github': ['bilibili', 'google'],
                'google': ['bilibili', 'github'],
                'zhihu': ['bilibili', 'baidu']
            }
            
            predicted_time = datetime.now() + timedelta(minutes=2)
            
            # 如果最近主要是浏览器活动
            if recent_apps and recent_apps[-1] in ['chrome.exe', 'msedge.exe']:
                browser_app = recent_apps[-1]
                
                # 如果有网站访问历史，预测下一个网站
                if frequent_websites:
                    last_website = frequent_websites[-1]
                    if last_website in website_transitions:
                        next_website = website_transitions[last_website][0]
                        
                        # 构建网页访问预测
                        website_urls = {
                            'bilibili': 'https://www.bilibili.com',
                            'github': 'https://github.com',
                            'google': 'https://www.google.com',
                            'baidu': 'https://www.baidu.com',
                            'zhihu': 'https://www.zhihu.com'
                        }
                        
                        predicted_url = website_urls.get(next_website, 'https://www.google.com')
                        window_title = f"{next_website.title()} Homepage"
                        
                        return {
                            "predicted_time": predicted_time,
                            "app_name": browser_app,
                            "action_type": "访问网页",
                            "confidence": 0.7,
                            "raw_prediction": f"{predicted_time.strftime('%Y-%m-%d %H:%M:%S')} - 访问网页: {predicted_url} (应用: {browser_app})",
                            "predicted_content": {
                                "content_type": "webpage",
                                "website": next_website,
                                "window_title": window_title,
                                "predicted_url": predicted_url
                            }
                        }
            
            # 普通应用切换预测
            if recent_apps:
                last_app = recent_apps[-1]
                if last_app in app_transitions:
                    next_app = app_transitions[last_app][0]
                    
                    return {
                        "predicted_time": predicted_time,
                        "app_name": next_app,
                        "action_type": "启动应用",
                        "confidence": 0.6,
                        "raw_prediction": f"{predicted_time.strftime('%Y-%m-%d %H:%M:%S')} - 启动应用: {next_app}",
                        "predicted_content": {}
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"生成模式预测失败: {e}")
            return None
    
    def _parse_prediction(self, prediction_text: str) -> Optional[Dict[str, Any]]:
        """解析预测文本 - 增强版支持网页预测"""
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
            
            # 解析不同类型的预测
            result = None
            
            # 网页访问预测
            webpage_match = re.search(r'访问网页:\s*(.+?)\s*\(应用:\s*(.+?)\)', prediction_text)
            if webpage_match:
                url = webpage_match.group(1).strip()
                app_name = webpage_match.group(2).strip()
                result = {
                    "predicted_time": predicted_time,
                    "app_name": self._normalize_app_name(app_name),
                    "action_type": "访问网页",
                    "raw_prediction": prediction_text,
                    "predicted_content": {
                        "content_type": "webpage",
                        "predicted_url": url,
                        "window_title": f"网页: {url}"
                    }
                }
            
            # 窗口切换预测
            elif "切换到窗口:" in prediction_text:
                window_match = re.search(r'切换到窗口:\s*(.+?)\s*\(应用:\s*(.+?)\)', prediction_text)
                if window_match:
                    window_title = window_match.group(1).strip()
                    app_name = window_match.group(2).strip()
                    result = {
                        "predicted_time": predicted_time,
                        "app_name": self._normalize_app_name(app_name),
                        "action_type": "切换窗口",
                        "raw_prediction": prediction_text,
                        "predicted_content": {
                            "window_title": window_title,
                            "content_type": "webpage" if any(indicator in window_title.lower() 
                                           for indicator in ['http', 'www', '.com', '.cn', 'bilibili', 'github']) 
                                           else "file_or_app"
                        }
                    }
            
            # 应用启动预测
            elif "启动应用:" in prediction_text:
                app_match = re.search(r'启动应用:\s*(.+)', prediction_text)
                if app_match:
                    app_name = app_match.group(1).strip()
                    result = {
                        "predicted_time": predicted_time,
                        "app_name": self._normalize_app_name(app_name),
                        "action_type": "启动应用",
                        "raw_prediction": prediction_text,
                        "predicted_content": {}
                    }
            
            if result:
                logger.info(f"✅ 解析成功: {result['action_type']} {result['app_name']} 在 {predicted_time.strftime('%H:%M:%S')}")
                return result
            else:
                logger.warning(f"❌ 无法解析预测结果: {prediction_text}")
                return None
                
        except Exception as e:
            logger.error(f"解析失败: {e}")
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

# 其他类保持不变，但更新使用新的SmartApplicationManager
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
            
            ssh_command = [
                'ssh',
                '-L', f"{local_port}:localhost:{remote_port}",
                '-N',
                '-T',
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                f"{username}@{ssh_host}",
                '-p', str(ssh_port)
            ]
            
            logger.info("正在建立SSH隧道...")
            logger.info("请在SSH提示时输入密码")
            
            self.tunnel_process = subprocess.Popen(
                ssh_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            time.sleep(5)
            
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
    """端到端预测和优化系统 - 增强版"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.queue_size = config['system']['queue_size']
        self.prediction_window = config['system']['prediction_window']
        
        # 初始化组件 - 使用智能应用管理器
        self.activity_queue = RealTimeActivityQueue(max_size=self.queue_size)
        self.llm_predictor = LLMPredictor(config)
        self.app_manager = SmartApplicationManager()
        
        # 运行状态
        self.running = False
        self.monitor_thread = None
        self.prediction_thread = None
        self.cleanup_thread = None
        
        # 预测状态
        self.last_queue_hash = 0
        self.prediction_cooldown = config['system'].get('prediction_cooldown', 30)
        self.last_prediction_time = 0
        
        logger.info("🎉 增强版端到端系统初始化完成")
    
    def start(self):
        """启动系统"""
        logger.info("🚀 启动增强版端到端预测和优化系统...")
        self.running = True
        
        # 启动监控线程
        self.monitor_thread = threading.Thread(target=self._monitor_activities, daemon=True)
        self.monitor_thread.start()
        
        # 启动预测线程
        self.prediction_thread = threading.Thread(target=self._prediction_loop, daemon=True)
        self.prediction_thread.start()
        
        # 启动清理线程
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        
        logger.info("✓ 增强版端到端系统已启动")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("用户中断，正在停止系统...")
            self.stop()
    
    def stop(self):
        """停止系统"""
        logger.info("🛑 正在停止增强版端到端系统...")
        self.running = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        if self.prediction_thread and self.prediction_thread.is_alive():
            self.prediction_thread.join(timeout=5)
            
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5)
        
        logger.info("✓ 增强版端到端系统已停止")
    
    def _monitor_activities(self):
        """监控用户活动"""
        logger.info("👁️ 开始监控用户活动...")
        
        last_window = None
        check_count = 0
        
        while self.running:
            try:
                current_time = datetime.now()
                check_count += 1
                
                if check_count % 20 == 0:
                    logger.info(f"💓 系统心跳检查 #{check_count}")
                
                window_info = self._get_current_window_info()
                if window_info and window_info != last_window:
                    activity = {
                        'type': 'window_focus',
                        'datetime': current_time,
                        **window_info
                    }
                    self.activity_queue.add_activity(activity)
                    last_window = window_info
                    
                    # 标记应用和网页使用
                    app_name = window_info.get('process_name', '')
                    window_title = window_info.get('window_title', '')
                    if app_name:
                        self.app_manager.mark_app_as_used(app_name, window_title)
                
                time.sleep(3)
                
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
        logger.info("🔮 开始增强版预测循环...")
        
        while self.running:
            try:
                queue_changed, current_hash = self.activity_queue.is_activity_queue_changed(self.last_queue_hash)
                
                if queue_changed:
                    self.last_queue_hash = current_hash
                    
                    current_time = time.time()
                    if current_time - self.last_prediction_time >= self.prediction_cooldown:
                        self._make_prediction()
                        self.last_prediction_time = current_time
                
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"预测循环出错: {e}")
                time.sleep(10)
    
    def _cleanup_loop(self):
        """清理循环"""
        logger.info("🧹 开始定期清理循环...")
        
        while self.running:
            try:
                self.app_manager.periodic_cleanup()
                time.sleep(300)  # 每5分钟清理一次
                
            except Exception as e:
                logger.error(f"清理循环出错: {e}")
                time.sleep(60)
    
    def _make_prediction(self):
        """执行预测"""
        try:
            recent_activities = self.activity_queue.get_recent_activities(self.prediction_window)
            
            if len(recent_activities) < 3:
                return
            
            logger.info(f"🔮 开始增强版预测，基于最近 {len(recent_activities)} 个活动")
            
            prediction = self.llm_predictor.predict_next_activity(recent_activities)
            
            if prediction:
                app_name = prediction['app_name']
                predicted_time = prediction['predicted_time']
                confidence = prediction.get('confidence', 0.0)
                action_type = prediction.get('action_type', '未知')
                content_info = prediction.get('predicted_content', {})
                
                logger.info(f"📈 预测结果: {action_type} {app_name} 在 {predicted_time.strftime('%H:%M:%S')} (置信度: {confidence:.2f})")
                
                if content_info.get('content_type') == 'webpage':
                    logger.info(f"🌐 预测网页内容: {content_info.get('window_title', 'N/A')}")
                
                # 智能预加载
                confidence_threshold = self.config['system'].get('confidence_threshold', 0.6)
                if confidence >= confidence_threshold:
                    success = self.app_manager.smart_preload(prediction)
                    if success:
                        logger.info(f"✅ 已安排智能预加载: {app_name}")
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
            "port": 17012,  # 更新为新端口
            "username": "root",
            "tunnel_local_port": 8000,
            "tunnel_remote_port": 8000
        }
    }

def main():
    """主函数"""
    print("🎯 增强版端到端用户行为预测和应用优化系统")
    print("=" * 70)
    print("🌐 新增功能: 智能网页预加载")
    print("🤖 新增功能: 增强的内容识别")
    print("🚀 新增功能: 智能预加载策略")
    print("=" * 70)
    
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
    print("3. 系统将自动监控您的活动并进行智能预测")
    print("4. 新增功能: 自动识别和预加载网页内容")
    print()
    
    input("按回车键继续启动增强版系统...")
    
    try:
        # 检查必要的目录
        for directory in ['logs']:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        # 初始化并启动系统
        system = EndToEndSystem(config)
        
        print("🚀 增强版系统启动中...")
        print("📊 开始监控用户活动...")
        print("🔮 LLM预测服务已就绪...")
        print("🌐 网页内容预加载器已就绪...")
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