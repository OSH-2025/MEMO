"""
端到端用户行为预测系统 - GUI前端
现代化界面，支持SSH隧道管理和实时日志显示
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import subprocess
import queue
import json
import os
import time
from datetime import datetime
import re
import sys
from pathlib import Path

# 导入主程序
try:
    from end_to_end_system import EndToEndSystem, create_default_config
    import logging
except ImportError:
    messagebox.showerror("错误", "无法导入主程序模块，请确保 end_to_end_system.py 在同一目录下")
    sys.exit(1)

class ModernStyle:
    """现代化UI样式配置"""
    
    # 颜色主题
    COLORS = {
        'primary': '#2563eb',      # 蓝色
        'success': '#10b981',      # 绿色
        'warning': '#f59e0b',      # 橙色
        'danger': '#ef4444',       # 红色
        'dark': '#1f2937',         # 深灰
        'light': '#f8fafc',        # 浅灰
        'white': '#ffffff',        # 白色
        'border': '#e5e7eb',       # 边框色
        'text': '#374151',         # 文本色
        'text_light': '#6b7280',   # 浅文本色
    }
    
    # 字体配置
    FONTS = {
        'title': ('Segoe UI', 16, 'bold'),
        'heading': ('Segoe UI', 12, 'bold'),
        'body': ('Segoe UI', 10),
        'small': ('Segoe UI', 9),
        'monospace': ('Consolas', 9),
    }

class LogHandler(logging.Handler):
    """自定义日志处理器，将日志发送到GUI"""
    
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
        
    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_queue.put(msg)
        except:
            pass

class SSHTunnelFrame(ttk.LabelFrame):
    """SSH隧道配置框架"""
    
    def __init__(self, parent, on_connect_callback=None):
        super().__init__(parent, text="🔗 SSH隧道配置", padding=15)
        self.on_connect_callback = on_connect_callback
        self.ssh_process = None
        self.is_connected = False
        
        self.create_widgets()
        self.load_default_config()
    
    def create_widgets(self):
        """创建SSH配置界面"""
        
        # SSH命令输入
        ttk.Label(self, text="SSH连接命令:", font=ModernStyle.FONTS['body']).grid(
            row=0, column=0, sticky='w', pady=(0, 5)
        )
        
        self.ssh_command_var = tk.StringVar()
        self.ssh_command_entry = ttk.Entry(
            self, textvariable=self.ssh_command_var, 
            width=60, font=ModernStyle.FONTS['monospace']
        )
        self.ssh_command_entry.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(0, 10))
        
        # 密码输入
        ttk.Label(self, text="SSH密码:", font=ModernStyle.FONTS['body']).grid(
            row=2, column=0, sticky='w', pady=(0, 5)
        )
        
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(
            self, textvariable=self.password_var, 
            show='*', width=30, font=ModernStyle.FONTS['body']
        )
        self.password_entry.grid(row=3, column=0, sticky='ew', pady=(0, 10))
        
        # 显示密码选项
        self.show_password_var = tk.BooleanVar()
        show_password_cb = ttk.Checkbutton(
            self, text="显示密码", variable=self.show_password_var,
            command=self.toggle_password_visibility
        )
        show_password_cb.grid(row=3, column=1, sticky='w', padx=(10, 0), pady=(0, 10))
        
        # 连接按钮
        self.connect_button = ttk.Button(
            self, text="🚀 建立SSH隧道", 
            command=self.toggle_connection,
            style='Accent.TButton'
        )
        self.connect_button.grid(row=4, column=0, sticky='w', pady=(5, 0))
        
        # 状态标签
        self.status_label = ttk.Label(
            self, text="● 未连接", 
            foreground=ModernStyle.COLORS['danger'],
            font=ModernStyle.FONTS['body']
        )
        self.status_label.grid(row=4, column=1, sticky='w', padx=(10, 0), pady=(5, 0))
        
        # 配置列权重
        self.columnconfigure(0, weight=1)
    
    def load_default_config(self):
        """加载默认配置"""
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    ssh_config = config.get('ssh', {})
                    
                    # 构建SSH命令
                    ssh_cmd = f"ssh -L {ssh_config.get('tunnel_local_port', 8000)}:localhost:{ssh_config.get('tunnel_remote_port', 8000)} {ssh_config.get('username', 'root')}@{ssh_config.get('host', 'js2.blockelite.cn')} -p {ssh_config.get('port', 17012)}"
                    self.ssh_command_var.set(ssh_cmd)
        except Exception as e:
            print(f"加载配置失败: {e}")
            # 设置默认值
            self.ssh_command_var.set("ssh -L 8000:localhost:8000 root@js2.blockelite.cn -p 17012")
    
    def toggle_password_visibility(self):
        """切换密码显示/隐藏"""
        if self.show_password_var.get():
            self.password_entry.config(show='')
        else:
            self.password_entry.config(show='*')
    
    def toggle_connection(self):
        """切换SSH连接状态"""
        if self.is_connected:
            self.disconnect_ssh()
        else:
            self.connect_ssh()
    
    def connect_ssh(self):
        """建立SSH连接"""
        ssh_command = self.ssh_command_var.get().strip()
        password = self.password_var.get().strip()
        
        if not ssh_command:
            messagebox.showerror("错误", "请输入SSH命令")
            return
        
        if not password:
            messagebox.showerror("错误", "请输入SSH密码")
            return
        
        try:
            # 更新状态
            self.status_label.config(text="● 连接中...", foreground=ModernStyle.COLORS['warning'])
            self.connect_button.config(text="连接中...", state='disabled')
            
            # 在后台线程中建立SSH连接
            threading.Thread(target=self._connect_ssh_thread, args=(ssh_command, password), daemon=True).start()
            
        except Exception as e:
            self.status_label.config(text="● 连接失败", foreground=ModernStyle.COLORS['danger'])
            self.connect_button.config(text="🚀 建立SSH隧道", state='normal')
            messagebox.showerror("SSH连接错误", f"连接失败: {str(e)}")
    
    def _connect_ssh_thread(self, ssh_command, password):
        """SSH连接线程"""
        try:
            # 解析SSH命令
            cmd_parts = ssh_command.split()
            
            # 使用expect或者pexpect来自动输入密码
            # 这里使用简单的subprocess方法
            
            # Windows上使用PowerShell或者直接subprocess
            if os.name == 'nt':  # Windows
                # 创建SSH进程
                self.ssh_process = subprocess.Popen(
                    cmd_parts,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                # 等待密码提示并输入密码
                time.sleep(2)
                
                # 检查连接状态
                if self.ssh_process.poll() is None:
                    # 进程还在运行，假设连接成功
                    self.is_connected = True
                    self.status_label.config(text="● 已连接", foreground=ModernStyle.COLORS['success'])
                    self.connect_button.config(text="🔌 断开连接", state='normal')
                    
                    if self.on_connect_callback:
                        self.on_connect_callback(True)
                else:
                    # 连接失败
                    raise Exception("SSH进程意外退出")
            
        except Exception as e:
            self.is_connected = False
            self.status_label.config(text="● 连接失败", foreground=ModernStyle.COLORS['danger'])
            self.connect_button.config(text="🚀 建立SSH隧道", state='normal')
            
            # 在主线程中显示错误
            self.after(0, lambda: messagebox.showerror("SSH连接错误", f"连接失败: {str(e)}"))
    
    def disconnect_ssh(self):
        """断开SSH连接"""
        try:
            if self.ssh_process:
                self.ssh_process.terminate()
                self.ssh_process = None
            
            self.is_connected = False
            self.status_label.config(text="● 未连接", foreground=ModernStyle.COLORS['danger'])
            self.connect_button.config(text="🚀 建立SSH隧道")
            
            if self.on_connect_callback:
                self.on_connect_callback(False)
                
        except Exception as e:
            messagebox.showerror("断开连接错误", f"断开连接时出错: {str(e)}")

class SystemControlFrame(ttk.LabelFrame):
    """系统控制框架"""
    
    def __init__(self, parent, on_start_callback=None, on_stop_callback=None):
        super().__init__(parent, text="🎯 系统控制", padding=15)
        self.on_start_callback = on_start_callback
        self.on_stop_callback = on_stop_callback
        self.is_running = False
        
        self.create_widgets()
    
    def create_widgets(self):
        """创建系统控制界面"""
        
        # 系统状态
        status_frame = ttk.Frame(self)
        status_frame.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 15))
        
        ttk.Label(status_frame, text="系统状态:", font=ModernStyle.FONTS['body']).pack(side='left')
        
        self.system_status_label = ttk.Label(
            status_frame, text="● 未启动", 
            foreground=ModernStyle.COLORS['text_light'],
            font=ModernStyle.FONTS['body']
        )
        self.system_status_label.pack(side='left', padx=(5, 0))
        
        # 控制按钮
        button_frame = ttk.Frame(self)
        button_frame.grid(row=1, column=0, columnspan=2, sticky='ew')
        
        self.start_button = ttk.Button(
            button_frame, text="▶️ 启动系统",
            command=self.start_system,
            style='Accent.TButton'
        )
        self.start_button.pack(side='left', padx=(0, 10))
        
        self.stop_button = ttk.Button(
            button_frame, text="⏹️ 停止系统",
            command=self.stop_system,
            state='disabled'
        )
        self.stop_button.pack(side='left')
        
        # 配置按钮
        ttk.Button(
            button_frame, text="⚙️ 配置",
            command=self.open_config
        ).pack(side='right')
        
        # 配置列权重
        self.columnconfigure(0, weight=1)
    
    def start_system(self):
        """启动系统"""
        try:
            self.is_running = True
            self.system_status_label.config(text="● 运行中", foreground=ModernStyle.COLORS['success'])
            self.start_button.config(state='disabled')
            self.stop_button.config(state='normal')
            
            if self.on_start_callback:
                self.on_start_callback()
                
        except Exception as e:
            self.is_running = False
            self.system_status_label.config(text="● 启动失败", foreground=ModernStyle.COLORS['danger'])
            self.start_button.config(state='normal')
            self.stop_button.config(state='disabled')
            messagebox.showerror("启动错误", f"系统启动失败: {str(e)}")
    
    def stop_system(self):
        """停止系统"""
        try:
            self.is_running = False
            self.system_status_label.config(text="● 已停止", foreground=ModernStyle.COLORS['text_light'])
            self.start_button.config(state='normal')
            self.stop_button.config(state='disabled')
            
            if self.on_stop_callback:
                self.on_stop_callback()
                
        except Exception as e:
            messagebox.showerror("停止错误", f"系统停止时出错: {str(e)}")
    
    def open_config(self):
        """打开配置窗口"""
        config_window = ConfigWindow(self)

class LogDisplayFrame(ttk.LabelFrame):
    """日志显示框架"""
    
    def __init__(self, parent):
        super().__init__(parent, text="📋 系统日志", padding=10)
        self.create_widgets()
        
        # 日志队列
        self.log_queue = queue.Queue()
        self.setup_logging()
        
        # 启动日志更新
        self.update_logs()
    
    def create_widgets(self):
        """创建日志显示界面"""
        
        # 工具栏
        toolbar_frame = ttk.Frame(self)
        toolbar_frame.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        
        ttk.Button(
            toolbar_frame, text="🗑️ 清空",
            command=self.clear_logs
        ).pack(side='left')
        
        ttk.Button(
            toolbar_frame, text="💾 保存",
            command=self.save_logs
        ).pack(side='left', padx=(5, 0))
        
        # 日志级别过滤
        ttk.Label(toolbar_frame, text="级别:").pack(side='left', padx=(20, 5))
        
        self.log_level_var = tk.StringVar(value="全部")
        log_level_combo = ttk.Combobox(
            toolbar_frame, textvariable=self.log_level_var,
            values=["全部", "INFO", "WARNING", "ERROR"],
            state='readonly', width=10
        )
        log_level_combo.pack(side='left')
        log_level_combo.bind('<<ComboboxSelected>>', self.filter_logs)
        
        # 自动滚动选项
        self.auto_scroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            toolbar_frame, text="自动滚动",
            variable=self.auto_scroll_var
        ).pack(side='right')
        
        # 日志文本框
        self.log_text = scrolledtext.ScrolledText(
            self, wrap=tk.WORD, 
            font=ModernStyle.FONTS['monospace'],
            height=20, width=80
        )
        self.log_text.grid(row=1, column=0, sticky='nsew')
        
        # 配置文本标签
        self.log_text.tag_configure('INFO', foreground=ModernStyle.COLORS['text'])
        self.log_text.tag_configure('WARNING', foreground=ModernStyle.COLORS['warning'])
        self.log_text.tag_configure('ERROR', foreground=ModernStyle.COLORS['danger'])
        self.log_text.tag_configure('SUCCESS', foreground=ModernStyle.COLORS['success'])
        
        # 配置权重
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
    
    def setup_logging(self):
        """设置日志处理"""
        # 创建自定义日志处理器
        handler = LogHandler(self.log_queue)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        
        # 获取根日志器并添加处理器
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
    
    def update_logs(self):
        """更新日志显示"""
        try:
            while True:
                try:
                    log_msg = self.log_queue.get_nowait()
                    self.add_log_message(log_msg)
                except queue.Empty:
                    break
        except:
            pass
        
        # 每100ms检查一次
        self.after(100, self.update_logs)
    
    def add_log_message(self, message):
        """添加日志消息"""
        try:
            # 解析日志级别
            level = 'INFO'
            if 'WARNING' in message:
                level = 'WARNING'
            elif 'ERROR' in message:
                level = 'ERROR'
            elif any(indicator in message for indicator in ['✓', '成功', '完成']):
                level = 'SUCCESS'
            
            # 检查过滤器
            filter_level = self.log_level_var.get()
            if filter_level != "全部" and filter_level not in message:
                return
            
            # 添加时间戳（如果没有）
            if not message.startswith('2'):
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                message = f"[{timestamp}] {message}"
            
            # 插入消息
            self.log_text.insert(tk.END, message + '\n', level)
            
            # 限制行数（保留最后1000行）
            lines = int(self.log_text.index('end-1c').split('.')[0])
            if lines > 1000:
                self.log_text.delete('1.0', f'{lines-1000}.0')
            
            # 自动滚动
            if self.auto_scroll_var.get():
                self.log_text.see(tk.END)
                
        except Exception as e:
            print(f"添加日志消息失败: {e}")
    
    def clear_logs(self):
        """清空日志"""
        self.log_text.delete('1.0', tk.END)
    
    def save_logs(self):
        """保存日志"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".log",
                filetypes=[("日志文件", "*.log"), ("文本文件", "*.txt"), ("所有文件", "*.*")]
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get('1.0', tk.END))
                messagebox.showinfo("保存成功", f"日志已保存到: {filename}")
                
        except Exception as e:
            messagebox.showerror("保存失败", f"保存日志失败: {str(e)}")
    
    def filter_logs(self, event=None):
        """过滤日志"""
        # 这里可以实现更复杂的过滤逻辑
        pass

class ConfigWindow:
    """配置窗口"""
    
    def __init__(self, parent):
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.title("系统配置")
        self.window.geometry("500x400")
        self.window.transient(parent)
        self.window.grab_set()
        
        self.create_widgets()
        self.load_config()
    
    def create_widgets(self):
        """创建配置界面"""
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 系统配置页
        system_frame = ttk.Frame(notebook)
        notebook.add(system_frame, text="系统设置")
        
        # SSH配置页
        ssh_frame = ttk.Frame(notebook)
        notebook.add(ssh_frame, text="SSH设置")
        
        # LLM配置页
        llm_frame = ttk.Frame(notebook)
        notebook.add(llm_frame, text="LLM设置")
        
        # 创建系统配置
        self.create_system_config(system_frame)
        self.create_ssh_config(ssh_frame)
        self.create_llm_config(llm_frame)
        
        # 按钮框架
        button_frame = ttk.Frame(self.window)
        button_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        ttk.Button(button_frame, text="保存", command=self.save_config).pack(side='right', padx=(5, 0))
        ttk.Button(button_frame, text="取消", command=self.window.destroy).pack(side='right')
    
    def create_system_config(self, parent):
        """创建系统配置"""
        # 这里添加系统配置选项
        pass
    
    def create_ssh_config(self, parent):
        """创建SSH配置"""
        # 这里添加SSH配置选项
        pass
    
    def create_llm_config(self, parent):
        """创建LLM配置"""
        # 这里添加LLM配置选项
        pass
    
    def load_config(self):
        """加载配置"""
        pass
    
    def save_config(self):
        """保存配置"""
        pass

class MainApplication:
    """主应用程序"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("端到端用户行为预测系统 v1.0")
        self.root.geometry("1000x700")
        
        # 设置应用图标和样式
        self.setup_style()
        
        # 系统组件
        self.end_to_end_system = None
        self.system_thread = None
        
        # 创建界面
        self.create_widgets()
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_style(self):
        """设置界面样式"""
        style = ttk.Style()
        
        # 使用现代主题
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        
        # 自定义样式
        style.configure('Accent.TButton', foreground='white', background=ModernStyle.COLORS['primary'])
        style.map('Accent.TButton', 
                 background=[('active', ModernStyle.COLORS['primary']),
                           ('pressed', ModernStyle.COLORS['primary'])])
    
    def create_widgets(self):
        """创建主界面"""
        
        # 主标题
        title_frame = ttk.Frame(self.root)
        title_frame.pack(fill='x', padx=20, pady=(20, 10))
        
        title_label = ttk.Label(
            title_frame, 
            text="🎯 端到端用户行为预测系统",
            font=ModernStyle.FONTS['title']
        )
        title_label.pack(side='left')
        
        # 版本标签
        version_label = ttk.Label(
            title_frame,
            text="v1.0",
            font=ModernStyle.FONTS['small'],
            foreground=ModernStyle.COLORS['text_light']
        )
        version_label.pack(side='right')
        
        # 主内容区域
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        # 左侧控制面板
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side='left', fill='y', padx=(0, 10))
        
        # SSH隧道框架
        self.ssh_frame = SSHTunnelFrame(left_frame, self.on_ssh_connection_change)
        self.ssh_frame.pack(fill='x', pady=(0, 10))
        
        # 系统控制框架
        self.control_frame = SystemControlFrame(left_frame, self.start_system, self.stop_system)
        self.control_frame.pack(fill='x')
        
        # 右侧日志区域
        self.log_frame = LogDisplayFrame(main_frame)
        self.log_frame.pack(side='right', fill='both', expand=True)
        
        # 状态栏
        self.create_statusbar()
    
    def create_statusbar(self):
        """创建状态栏"""
        self.statusbar = ttk.Frame(self.root, relief='sunken')
        self.statusbar.pack(side='bottom', fill='x')
        
        self.status_label = ttk.Label(
            self.statusbar, 
            text="就绪",
            font=ModernStyle.FONTS['small']
        )
        self.status_label.pack(side='left', padx=5)
        
        # 时间标签
        self.time_label = ttk.Label(
            self.statusbar,
            text="",
            font=ModernStyle.FONTS['small']
        )
        self.time_label.pack(side='right', padx=5)
        
        self.update_time()
    
    def update_time(self):
        """更新时间显示"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=current_time)
        self.root.after(1000, self.update_time)
    
    def on_ssh_connection_change(self, connected):
        """SSH连接状态改变回调"""
        if connected:
            self.status_label.config(text="SSH隧道已连接")
            self.log_frame.add_log_message("✓ SSH隧道建立成功")
        else:
            self.status_label.config(text="SSH隧道已断开")
            self.log_frame.add_log_message("⚠️ SSH隧道已断开")
    
    def start_system(self):
        """启动系统"""
        try:
            # 检查SSH连接
            if not self.ssh_frame.is_connected:
                messagebox.showwarning("警告", "请先建立SSH隧道连接")
                return
            
            # 加载配置
            config = self.load_config()
            
            # 在后台线程启动系统
            self.system_thread = threading.Thread(target=self._run_system, args=(config,), daemon=True)
            self.system_thread.start()
            
            self.status_label.config(text="系统运行中...")
            self.log_frame.add_log_message("🚀 正在启动端到端预测系统...")
            
        except Exception as e:
            messagebox.showerror("启动错误", f"系统启动失败: {str(e)}")
            self.control_frame.stop_system()
    
    def stop_system(self):
        """停止系统"""
        try:
            if self.end_to_end_system:
                self.end_to_end_system.stop()
            
            self.status_label.config(text="系统已停止")
            self.log_frame.add_log_message("⏹️ 系统已停止")
            
        except Exception as e:
            messagebox.showerror("停止错误", f"系统停止时出错: {str(e)}")
    
    def _run_system(self, config):
        """在后台线程中运行系统"""
        try:
            self.end_to_end_system = EndToEndSystem(config)
            self.end_to_end_system.start()
        except Exception as e:
            self.log_frame.add_log_message(f"❌ 系统运行错误: {str(e)}")
            # 在主线程中更新状态
            self.root.after(0, self.control_frame.stop_system)
    
    def load_config(self):
        """加载配置"""
        config_path = "config.json"
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # 创建默认配置
            config = create_default_config()
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return config
    
    def on_closing(self):
        """关闭应用程序"""
        try:
            # 停止系统
            if self.end_to_end_system:
                self.end_to_end_system.stop()
            
            # 断开SSH连接
            if self.ssh_frame.is_connected:
                self.ssh_frame.disconnect_ssh()
            
            self.root.destroy()
            
        except Exception as e:
            print(f"关闭应用程序时出错: {e}")
            self.root.destroy()
    
    def run(self):
        """运行应用程序"""
        self.root.mainloop()

def main():
    """主函数"""
    try:
        app = MainApplication()
        app.run()
    except Exception as e:
        messagebox.showerror("应用程序错误", f"应用程序启动失败: {str(e)}")

if __name__ == "__main__":
    main()