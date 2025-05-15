"""
活动监控脚本 - 收集用户文件操作序列
收集带时间戳的用户活动数据，为大语言模型预测提供训练数据
"""

import os
import time
import json
import psutil
import winreg
import logging
import datetime
import threading
import win32gui
import win32process
from pathlib import Path
from typing import Dict, List, Any, Set, Optional
import pythoncom
import win32com.client
from win32com.shell import shell, shellcon
import sqlite3
import re
from collections import defaultdict

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='activity_monitor.log'
)
logger = logging.getLogger('activity_monitor')

class ActivityMonitor:
    """监控用户活动并记录相关操作"""
    
    def __init__(self, output_dir: str = "activity_data"):
        """初始化活动监控器
        
        Args:
            output_dir: 保存活动数据的目录
        """
        self.output_dir = output_dir
        self.activities: List[Dict[str, Any]] = []
        self.running = False
        self.known_processes: Dict[int, Dict[str, Any]] = {}  # 存储进程ID到进程信息的映射
        self.last_active_window = None
        self.last_save_time = time.time()
        self.save_interval = 300  # 每5分钟保存一次数据
        
        # 确保输出目录存在
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # 浏览器历史记录数据库路径
        self.chrome_history_path = os.path.join(os.getenv('LOCALAPPDATA'), 
                                            'Google\\Chrome\\User Data\\Default\\History')
        self.edge_history_path = os.path.join(os.getenv('LOCALAPPDATA'), 
                                            'Microsoft\\Edge\\User Data\\Default\\History')
        
        # 上次检查的浏览历史时间
        self.last_browser_check = time.time()
        
        # 用于浏览器历史去重
        self.known_visited_urls = set()  # 存储已访问的URL标识符
        self.url_visit_times = {}  # 记录URL访问时间，用于清理
        self.last_url_cleanup = time.time()  # 最后一次清理时间
        
        # 创建文件操作监控线程
        self.file_monitor_thread = None
        
        # 上次文件访问时间戳缓存
        self.last_file_access_time = {}
        
        # 配置
        self.min_window_focus_interval = 2  # 最小窗口焦点变化间隔(秒)
        self.last_window_focus_time = 0
        
        # GUI进程缓存
        self.gui_processes = set()
        self.last_gui_check = 0
        self.gui_check_interval = 60  # 每60秒更新一次GUI进程列表
        
        # 频率限制
        self.activity_frequency = {}  # 记录活动类型的频率
        self.frequency_limits = {
            "browser_history": 10,  # 每分钟最多记录10条浏览记录
            "window_focus": 20,     # 每分钟最多记录20次窗口焦点变化
            "file_access": 15       # 每分钟最多记录15次文件访问
        }
        self.last_minute_counts = defaultdict(int)
        self.last_minute_reset = time.time()
        
        # 时间上下文
        self.time_context = {
            "last_update": time.time(),
            "day_of_week": datetime.datetime.now().weekday(),
            "hour_of_day": datetime.datetime.now().hour,
            "is_weekend": datetime.datetime.now().weekday() >= 5,
            "session_start": time.time()
        }
        
        # 应用使用历史
        self.app_usage_history = defaultdict(list)  # 应用名称 -> 使用时间列表
        self.current_active_app = None
        self.current_app_start_time = None
        
        logger.info("活动监控器初始化完成")
    
    def _get_active_window_info(self) -> Dict[str, Any]:
        """获取当前活跃窗口信息"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd == 0:
                return {}
                
            # 获取窗口标题
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return {}
                
            # 获取进程ID和进程名
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                process = psutil.Process(pid)
                process_name = process.name()
                exe_path = process.exe()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                process_name = "unknown"
                exe_path = "unknown"
                
            return {
                "window_title": title,
                "process_name": process_name,
                "process_id": pid,
                "executable_path": exe_path,
                "timestamp": datetime.datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"获取活跃窗口信息出错: {e}")
            return {}
    
    def _get_browser_history(self) -> List[Dict[str, Any]]:
        """获取浏览器历史记录，改进为仅捕获新访问的网页
        
        返回:
            新访问的网页列表
        """
        history_entries = []
        
        # 检查距离上次浏览器历史检查是否已经过去了至少30秒
        current_time = time.time()
        if current_time - self.last_browser_check < 30:
            return []
            
        self.last_browser_check = current_time
        
        # 使用更短的时间窗口，减少重复条目
        # 仅查询最近30秒内的历史记录，而不是1分钟
        timeframe = int((current_time - 30) * 1000000)  
        
        # 每10分钟清理一次旧的URL记录
        if current_time - self.last_url_cleanup > 600:
            cleanup_threshold = current_time - 3600  # 1小时前的记录
            # 清理超过1小时的URL记录
            old_urls = [url for url, visit_time in self.url_visit_times.items() 
                        if visit_time < cleanup_threshold]
            for url in old_urls:
                self.known_visited_urls.discard(url)
                self.url_visit_times.pop(url, None)
            self.last_url_cleanup = current_time
        
        # 处理Chrome历史
        chrome_entries = self._get_browser_specific_history(
            self.chrome_history_path, 'chrome', timeframe
        )
        history_entries.extend(chrome_entries)
        
        # 处理Edge历史
        edge_entries = self._get_browser_specific_history(
            self.edge_history_path, 'edge', timeframe
        )
        history_entries.extend(edge_entries)
        
        return history_entries
    
    def _get_browser_specific_history(self, db_path: str, browser_name: str, timeframe: int) -> List[Dict[str, Any]]:
        """获取特定浏览器的历史记录
        
        Args:
            db_path: 浏览器历史数据库路径
            browser_name: 浏览器名称
            timeframe: 时间阈值
            
        Returns:
            历史记录条目列表
        """
        history_entries = []
        
        if not os.path.exists(db_path):
            return []
            
        try:
            # 复制数据库以避免锁定
            temp_db = os.path.join(self.output_dir, f"temp_{browser_name}_history")
            try:
                import shutil
                shutil.copy2(db_path, temp_db)
            
                # 连接复制的数据库
                conn = sqlite3.connect(temp_db)
                cursor = conn.cursor()
                
                # 查询最近的历史记录，按访问时间排序
                cursor.execute(
                    """
                    SELECT url, title, last_visit_time 
                    FROM urls 
                    WHERE last_visit_time > ? 
                    ORDER BY last_visit_time DESC
                    LIMIT 10
                    """, 
                    (timeframe,)
                )
                
                current_time = time.time()
                
                for row in cursor.fetchall():
                    url, title, visit_time = row
                    
                    # 转换Chrome/Edge时间戳格式
                    chrome_epoch = datetime.datetime(1601, 1, 1)
                    visit_datetime = chrome_epoch + datetime.timedelta(microseconds=visit_time)
                    
                    # 创建唯一标识符：URL+标题
                    url_identifier = f"{url}:{title}"
                    
                    # 仅记录新访问的URL
                    if url_identifier not in self.known_visited_urls:
                        # 过滤掉不应记录的URL
                        if not self._should_filter_url(url):
                            # 记录新的访问
                            self.known_visited_urls.add(url_identifier)
                            self.url_visit_times[url_identifier] = current_time
                            
                            # 从URL提取域名
                            domain = ""
                            try:
                                from urllib.parse import urlparse
                                parsed_url = urlparse(url)
                                domain = parsed_url.netloc
                            except:
                                pass
                            
                            history_entries.append({
                                "type": "browser_history",
                                "browser": browser_name,
                                "url": url,
                                "title": title,
                                "domain": domain,
                                "timestamp": visit_datetime.isoformat()
                            })
                            
                cursor.close()
                conn.close()
            finally:
                # 删除临时数据库文件
                try:
                    os.remove(temp_db)
                except:
                    pass
        except Exception as e:
            logger.error(f"读取{browser_name}历史记录出错: {e}")
        
        return history_entries
    
    def _should_filter_url(self, url: str) -> bool:
        """判断是否应该过滤掉某个URL
        
        返回:
            True表示应该过滤掉，False表示应该保留
        """
        # 敏感模式匹配 - 保护隐私
        sensitive_patterns = [
            r'password',
            r'login',
            r'signin',
            r'account',
            r'auth',
            r'token',
            r'credential',
            r'private',
            r'secret',
            r'email',
            r'mail\.',
            r'payment',
            r'checkout',
            r'billing',
            r'bank',
            r'wallet',
            r'finance',
            r'admin',
            r'manage',
            r'dashboard'
        ]
        
        for pattern in sensitive_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
                
        # 过滤系统或自动同步URLs
        system_urls = [
            'chrome-extension://',
            'edge-extension://',
            'chrome://newtab',
            'edge://newtab',
            'about:blank',
            'chrome://',
            'edge://',
            'about:',
            'file:///',
            'chrome://extensions',
            'edge://extensions',
            'chrome-search://',
            'edge-search://',
            'chrome://sync',
            'chrome://settings',
            'edge://settings',
            'chrome://history',
            'edge://history'
        ]
        
        for sys_url in system_urls:
            if url.startswith(sys_url):
                return True
        
        # 过滤掉网站噪音
        noise_patterns = [
            r'/ads/',
            r'/analytics/',
            r'/metrics/',
            r'/tracking/',
            r'/beacon/',
            r'/pixel/',
            r'/telemetry/',
            r'favicon\.ico$',
            r'\.woff',
            r'\.ttf',
            r'\.svg',
            r'\.png$',
            r'\.jpg$',
            r'\.gif$',
            r'\.css$',
            r'\.js$'
        ]
        
        for pattern in noise_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        
        # 提取和清理域名用于统计和重复过滤
        domain_match = re.search(r'https?://([^/]+)', url)
        if domain_match:
            domain = domain_match.group(1)
            
            # 忽略常见的广告和跟踪域名
            ad_domains = [
                'ads.', 'adservice.', 'analytics.', 'tracker.', 
                'pixel.', 'metrics.', 'logging.', 'stats.'
            ]
            
            for ad_domain in ad_domains:
                if ad_domain in domain:
                    return True
                
        return False
    
    def _monitor_processes(self) -> List[Dict[str, Any]]:
        """监控新启动的应用程序和关闭的应用程序"""
        process_events = []
        
        try:
            current_processes_pids = set()
            
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline', 'create_time']):
                try:
                    # 只记录可见的用户进程，忽略系统进程
                    if self._is_user_process(proc):
                        pid = proc.info['pid']
                        current_processes_pids.add(pid)
                        
                        # 检查是否是新进程
                        if pid not in self.known_processes:
                            process_info = {
                                "process_name": proc.info['name'],
                                "executable_path": proc.info['exe'] if proc.info['exe'] else '',
                                "command_line": ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else '',
                                "start_time": proc.info['create_time']
                            }
                            self.known_processes[pid] = process_info
                            
                            process_events.append({
                                "type": "process_start",
                                "process_name": process_info["process_name"],
                                "process_id": pid,
                                "executable_path": process_info["executable_path"],
                                "command_line": process_info["command_line"],
                                "timestamp": datetime.datetime.fromtimestamp(process_info["start_time"]).isoformat()
                            })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # 检查已关闭的进程
            closed_processes = set(self.known_processes.keys()) - current_processes_pids
            for pid in closed_processes:
                process_info = self.known_processes.get(pid, {})
                process_name = process_info.get("process_name", "unknown")
                exe_path = process_info.get("executable_path", "")
                
                process_events.append({
                    "type": "process_end",
                    "process_id": pid,
                    "process_name": process_name,
                    "executable_path": exe_path,
                    "timestamp": datetime.datetime.now().isoformat()
                })
                
                # 从已知进程字典中删除
                self.known_processes.pop(pid, None)
            
        except Exception as e:
            logger.error(f"监控进程时出错: {e}")
            
        return process_events
    
    def _is_user_process(self, proc: psutil.Process) -> bool:
        """判断是否是用户进程而非系统进程
        
        Args:
            proc: psutil进程对象
            
        Returns:
            是否是用户进程
        """
        try:
            # 基本过滤
            if not proc.info['exe'] or not proc.info['name']:
                return False
                
            # 过滤系统进程
            system_processes = [
                'svchost.exe', 'services.exe', 'lsass.exe', 'csrss.exe',
                'smss.exe', 'winlogon.exe', 'wininit.exe', 'System',
                'Registry', 'fontdrvhost.exe', 'dwm.exe', 'conhost.exe',
                'taskhostw.exe', 'SgrmBroker.exe', 'spoolsv.exe',
                'SearchIndexer.exe', 'ShellExperienceHost.exe', 'ctfmon.exe',
                'RuntimeBroker.exe', 'WmiPrvSE.exe', 'dllhost.exe',
                'sihost.exe', 'SecurityHealthService.exe', 'Memory Compression',
                'WUDFHost.exe', 'NVDisplay.Container.exe', 'SearchUI.exe',
                'smartscreen.exe', 'SystemSettings.exe', 'TextInputHost.exe',
                'ApplicationFrameHost.exe', 'Idle'
            ]
            
            process_name_lower = proc.info['name'].lower()
            
            if process_name_lower in [p.lower() for p in system_processes]:
                return False
                
            # 过滤系统路径下的进程
            system_paths = [
                os.environ.get('SystemRoot', 'C:\\Windows'),
                os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32'),
                os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'SysWOW64'),
                os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'SystemApps')
            ]
            
            if proc.info['exe']:
                exe_path_lower = proc.info['exe'].lower()
                
                for path in system_paths:
                    path_lower = path.lower()
                    if exe_path_lower.startswith(path_lower):
                        # 保留一些重要的用户应用
                        important_apps = [
                            'notepad.exe', 'wordpad.exe', 'mspaint.exe', 
                            'calc.exe', 'cmd.exe', 'powershell.exe',
                            'explorer.exe', 'mstsc.exe', 'taskmgr.exe',
                            'winword.exe', 'excel.exe', 'powerpnt.exe',
                            'outlook.exe', 'onenote.exe', 'code.exe',
                            'devenv.exe', 'msedge.exe', 'chrome.exe'
                        ]
                        
                        if process_name_lower in [app.lower() for app in important_apps]:
                            return True
                        
                        return False
            
            # 检查通用命名模式的系统进程
            system_patterns = [
                r'^Microsoft\.', r'^Windows\.', r'^WinStore', 
                r'Service$', r'Svc$', r'Host$', r'Agent$'
            ]
            
            for pattern in system_patterns:
                if re.search(pattern, proc.info['name'], re.IGNORECASE):
                    return False
            
            # 进程有GUI窗口更可能是用户进程
            try:
                if proc.info['pid'] in self.gui_processes:
                    return True
            except:
                pass
                
            return True
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    def _monitor_file_operations(self):
        """监控文件操作(打开、保存等)"""
        try:
            pythoncom.CoInitialize()
            recent_folder = shell.SHGetFolderPath(0, shellcon.CSIDL_RECENT, None, 0)
            
            last_check_files = set()
            
            while self.running:
                try:
                    # 获取Recent文件夹中的文件
                    current_files = set()
                    for item in os.listdir(recent_folder):
                        full_path = os.path.join(recent_folder, item)
                        if os.path.isfile(full_path):
                            # 获取快捷方式信息
                            shortcut = None
                            try:
                                shell_link = win32com.client.Dispatch("WScript.Shell").CreateShortCut(full_path)
                                target_path = shell_link.Targetpath
                                if target_path and os.path.exists(target_path):
                                    # 获取文件修改时间
                                    modified_time = os.path.getmtime(full_path)
                                    current_time = time.time()
                                    
                                    # 仅记录最近30分钟内修改的文件
                                    if (current_time - modified_time) < 1800:  # 30分钟 = 1800秒
                                        file_info = {
                                            "shortcut_path": full_path,
                                            "target_path": target_path,
                                            "modified_time": modified_time
                                        }
                                        current_files.add(json.dumps(file_info))
                            except:
                                pass
                    
                    # 找出新的文件操作
                    new_files = current_files - last_check_files
                    for file_info_json in new_files:
                        file_info = json.loads(file_info_json)
                        target_path = file_info["target_path"]
                        modified_time = file_info["modified_time"]
                        
                        # 检查是否是重复操作，或者时间间隔太短
                        last_access_time = self.last_file_access_time.get(target_path, 0)
                        if modified_time - last_access_time > 5:  # 至少5秒间隔
                            # 记录新的文件活动
                            self.activities.append({
                                "type": "file_access",
                                "path": target_path,
                                "timestamp": datetime.datetime.fromtimestamp(modified_time).isoformat()
                            })
                            
                            # 更新最后访问时间
                            self.last_file_access_time[target_path] = modified_time
                        
                    # 更新上次检查的文件列表
                    last_check_files = current_files
                    
                    # 每5秒检查一次
                    time.sleep(5)
                    
                except Exception as e:
                    logger.error(f"监控文件操作时出错: {e}")
                    time.sleep(10)  # 出错后等待时间更长
                    
            pythoncom.CoUninitialize()
            
        except Exception as e:
            logger.error(f"文件操作监控线程初始化出错: {e}")
    
    def start(self):
        """开始监控用户活动"""
        logger.info("开始监控用户活动")
        self.running = True
        
        # 启动文件操作监控线程
        self.file_monitor_thread = threading.Thread(target=self._monitor_file_operations)
        self.file_monitor_thread.daemon = True
        self.file_monitor_thread.start()
        
        # 初始化会话开始时间
        self.time_context["session_start"] = time.time()
        
        # 记录会话开始事件
        self.activities.append({
            "type": "session_start",
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        # 初始化已知进程集合
        for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline', 'create_time']):
            try:
                if self._is_user_process(proc):
                    pid = proc.info['pid']
                    self.known_processes[pid] = {
                        "process_name": proc.info['name'],
                        "executable_path": proc.info['exe'] if proc.info['exe'] else '',
                        "command_line": ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else '',
                        "start_time": proc.info['create_time']
                    }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # 初始化GUI进程列表
        self._update_gui_processes()
        
        try:
            while self.running:
                try:
                    # 更新时间上下文
                    self._update_time_context()
                    
                    # 更新GUI进程列表
                    self._update_gui_processes()
                    
                    # 获取当前活跃窗口信息
                    window_info = self._get_active_window_info()
                    
                    # 检查窗口焦点是否改变且最小间隔时间已过
                    current_time = time.time()
                    if (window_info and 
                        window_info.get("window_title") != self.last_active_window and
                        current_time - self.last_window_focus_time >= self.min_window_focus_interval):
                        
                        self.last_active_window = window_info.get("window_title")
                        self.last_window_focus_time = current_time
                        
                        # 检查记录频率
                        if self._check_frequency_limit("window_focus"):
                            self.activities.append({
                                "type": "window_focus",
                                **window_info
                            })
                        
                        # 跟踪应用使用时长
                        self._track_app_usage(window_info)
                    
                    # 获取进程启动和关闭信息
                    process_events = self._monitor_processes()
                    self.activities.extend(process_events)
                    
                    # 获取浏览器历史
                    browser_history = self._get_browser_history()
                    
                    # 筛选浏览器历史，应用频率限制
                    filtered_history = []
                    for entry in browser_history:
                        if self._check_frequency_limit("browser_history"):
                            filtered_history.append(entry)
                    
                    self.activities.extend(filtered_history)
                    
                    # 检查是否需要保存数据
                    current_time = time.time()
                    if current_time - self.last_save_time > self.save_interval:
                        self.save_data()
                        self.last_save_time = current_time
                    
                    # 暂停一小段时间
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"监控循环出错: {e}")
                    time.sleep(5)  # 出错后等待时间更长
        
        except KeyboardInterrupt:
            logger.info("用户中断，停止监控")
            self.stop()
    
    def stop(self):
        """停止监控用户活动"""
        logger.info("停止监控用户活动")
        self.running = False
        
        # 记录会话结束事件
        self.activities.append({
            "type": "session_end",
            "session_duration": time.time() - self.time_context["session_start"],
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        # 如果当前有活跃应用，记录其使用时长
        if self.current_active_app and self.current_app_start_time:
            usage_duration = time.time() - self.current_app_start_time
            if usage_duration >= 5:
                self.activities.append({
                    "type": "app_usage",
                    "process_name": self.current_active_app,
                    "duration": round(usage_duration, 2),
                    "timestamp": datetime.datetime.now().isoformat()
                })
        
        self.save_data()
        
        # 等待文件监控线程结束
        if self.file_monitor_thread and self.file_monitor_thread.is_alive():
            self.file_monitor_thread.join(timeout=2)
    
    def save_data(self):
        """保存收集的活动数据"""
        if not self.activities:
            return
            
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.output_dir, f"activity_data_{timestamp}.json")
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.activities, f, ensure_ascii=False, indent=2)
        
        logger.info(f"保存了 {len(self.activities)} 条活动记录到 {filename}")
        self.activities = []

    def _update_gui_processes(self):
        """更新具有GUI窗口的进程列表"""
        current_time = time.time()
        if current_time - self.last_gui_check < self.gui_check_interval:
            return
            
        self.last_gui_check = current_time
        self.gui_processes = set()
        
        try:
            def callback(hwnd, ctx):
                if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    ctx.add(pid)
                return True
                
            win32gui.EnumWindows(callback, self.gui_processes)
        except Exception as e:
            logger.error(f"更新GUI进程列表时出错: {e}")
    
    def _update_time_context(self):
        """更新时间上下文信息"""
        now = datetime.datetime.now()
        current_time = time.time()
        
        # 每小时更新一次时间上下文
        if current_time - self.time_context["last_update"] >= 3600:
            self.time_context.update({
                "last_update": current_time,
                "day_of_week": now.weekday(),
                "hour_of_day": now.hour,
                "is_weekend": now.weekday() >= 5
            })
            
            # 将时间上下文作为一个事件记录
            self.activities.append({
                "type": "time_context",
                "day_of_week": self.time_context["day_of_week"],
                "hour_of_day": self.time_context["hour_of_day"],
                "is_weekend": self.time_context["is_weekend"],
                "timestamp": now.isoformat()
            })
    
    def _check_frequency_limit(self, activity_type: str) -> bool:
        """检查是否超过频率限制
        
        Args:
            activity_type: 活动类型
            
        Returns:
            是否允许记录此活动
        """
        current_time = time.time()
        
        # 每分钟重置一次计数
        if current_time - self.last_minute_reset >= 60:
            self.last_minute_counts = defaultdict(int)
            self.last_minute_reset = current_time
        
        # 检查是否超过限制
        limit = self.frequency_limits.get(activity_type, 30)  # 默认每分钟最多30条
        if self.last_minute_counts[activity_type] >= limit:
            return False
            
        # 增加计数
        self.last_minute_counts[activity_type] += 1
        return True
        
    def _track_app_usage(self, window_info):
        """跟踪应用使用时长
        
        Args:
            window_info: 当前窗口信息
        """
        current_time = time.time()
        current_app = window_info.get("process_name")
        
        # 如果有活跃的应用且不同于当前应用
        if self.current_active_app and self.current_app_start_time and self.current_active_app != current_app:
            usage_duration = current_time - self.current_app_start_time
            
            # 只记录使用时间超过5秒的应用
            if usage_duration >= 5:
                # 记录应用使用时长
                self.activities.append({
                    "type": "app_usage",
                    "process_name": self.current_active_app,
                    "duration": round(usage_duration, 2),
                    "timestamp": datetime.datetime.now().isoformat()
                })
        
        # 更新当前活跃应用
        self.current_active_app = current_app
        self.current_app_start_time = current_time

if __name__ == "__main__":
    try:
        print("开始监控用户活动...")
        print("按 Ctrl+C 停止监控")
        
        monitor = ActivityMonitor()
        monitor.start()
    except KeyboardInterrupt:
        print("\n监控已停止")
    except Exception as e:
        print(f"发生错误: {e}")
        logger.error(f"主程序错误: {e}") 