#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sideria Process Manager - Modern GUI
希德莉亚进程管理器 - 现代化界面
"""

import os
import sys
import subprocess
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import requests

# Windows 下隐藏控制台窗口和 DPI 感知
if sys.platform == 'win32':
    import ctypes
    # 隐藏控制台
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    # 设置 DPI 感知，修复字体模糊
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except:
            pass

class ModernButton(tk.Canvas):
    """现代化按钮"""
    def __init__(self, parent, text, command, bg="#4A90E2", fg="white", width=120, height=40):
        super().__init__(parent, width=width, height=height, 
                        highlightthickness=0, bg=parent['bg'])
        self.command = command
        self.bg = bg
        self.fg = fg
        self.text = text
        self.hover_bg = self.lighten_color(bg)
        
        self.rect = self.create_rectangle(0, 0, width, height, 
                                         fill=bg, outline="", 
                                         tags="button")
        self.text_id = self.create_text(width/2, height/2, 
                                       text=text, fill=fg, 
                                       font=("Segoe UI", 10, "bold"),
                                       tags="button")
        
        self.bind("<Button-1>", self.on_click)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.tag_bind("button", "<Button-1>", self.on_click)
    
    def lighten_color(self, color):
        """使颜色变亮"""
        if color.startswith('#'):
            r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
            r = min(255, r + 30)
            g = min(255, g + 30)
            b = min(255, b + 30)
            return f'#{r:02x}{g:02x}{b:02x}'
        return color
    
    def on_click(self, event=None):
        if self.command:
            self.command()
    
    def on_enter(self, event):
        self.itemconfig(self.rect, fill=self.hover_bg)
    
    def on_leave(self, event):
        self.itemconfig(self.rect, fill=self.bg)

class ServiceCard(tk.Frame):
    """服务卡片 - 紧凑版"""
    def __init__(self, parent, service_name, service_info, controller):
        super().__init__(parent, bg="white", relief=tk.FLAT, bd=0)
        self.service_name = service_name
        self.controller = controller
        
        # 减小内边距
        self.config(padx=10, pady=8)
        
        # 顶部：服务名称和状态
        top_frame = tk.Frame(self, bg="white")
        top_frame.pack(fill=tk.X)
        
        # 状态指示器（更小）
        self.status_dot = tk.Canvas(top_frame, width=8, height=8, 
                                   bg="white", highlightthickness=0)
        self.status_dot.pack(side=tk.LEFT, padx=(0, 8))
        self.status_circle = self.status_dot.create_oval(1, 1, 7, 7, 
                                                         fill="#95A5A6", outline="")
        
        # 服务名称（更小字体）
        name_label = tk.Label(top_frame, text=service_info.get('name', service_name),
                             font=("Segoe UI", 10, "bold"), bg="white", fg="#2C3E50")
        name_label.pack(side=tk.LEFT)
        
        # 状态文本
        self.status_label = tk.Label(top_frame, text="检查中...", 
                                     font=("Segoe UI", 8), bg="white", fg="#7F8C8D")
        self.status_label.pack(side=tk.RIGHT)
        
        # 按钮区域（更紧凑）
        button_frame = tk.Frame(self, bg="white")
        button_frame.pack(anchor=tk.W, pady=(5, 0))
        
        self.start_btn = self.create_small_button(button_frame, "启动", 
                                                  lambda: controller.start_service(service_name),
                                                  "#27AE60")
        self.start_btn.pack(side=tk.LEFT, padx=(0, 3))
        
        self.stop_btn = self.create_small_button(button_frame, "停止",
                                                 lambda: controller.stop_service(service_name),
                                                 "#E74C3C")
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 3))
        
        self.restart_btn = self.create_small_button(button_frame, "重启",
                                                    lambda: controller.restart_service(service_name),
                                                    "#F39C12")
        self.restart_btn.pack(side=tk.LEFT, padx=(0, 3))
        
        self.disable_btn = self.create_small_button(button_frame, "禁用",
                                                    lambda: controller.disable_service(service_name),
                                                    "#95A5A6")
        self.disable_btn.pack(side=tk.LEFT)
    
    def create_small_button(self, parent, text, command, color):
        """创建小按钮 - 更紧凑"""
        btn = tk.Button(parent, text=text, command=command,
                       bg=color, fg="white", font=("Segoe UI", 7),
                       relief=tk.FLAT, padx=8, pady=2,
                       cursor="hand2", activebackground=color)
        return btn
    
    def update_status(self, is_running):
        """更新状态"""
        if is_running:
            color, text = "#27AE60", "运行中"
        else:
            color, text = "#E74C3C", "已停止"
        
        self.status_dot.itemconfig(self.status_circle, fill=color)
        self.status_label.config(text=text, fg=color)

class SideriaPMGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Sideria Process Manager")
        self.root.geometry("1200x750")
        self.root.configure(bg="#ECF0F1")
        
        # 获取脚本所在目录
        if getattr(sys, 'frozen', False):
            exe_dir = Path(sys.executable).parent
            self.pm_dir = exe_dir.parent if exe_dir.name == 'dist' else exe_dir
        else:
            self.pm_dir = Path(__file__).parent
        
        self.pm_js = self.pm_dir / "sideria-pm.js"
        self.services_json = self.pm_dir / "services.json"
        self.pm_api = "http://127.0.0.1:29997"
        
        # 检查 Node.js
        self.node_cmd = self.find_node()
        if not self.node_cmd:
            messagebox.showerror("错误", "未找到 Node.js！请先安装 Node.js")
            sys.exit(1)
        
        # 检查核心文件
        if not self.pm_js.exists():
            messagebox.showerror("错误", f"未找到核心文件: {self.pm_js}")
            sys.exit(1)
        
        self.service_cards = {}
        self.service_manager_window = None  # 服务管理窗口引用
        self.setup_ui()
        
        # 首次运行检查
        if not self.services_json.exists():
            self.show_first_run_dialog()
        else:
            self.load_services()
            # 延迟检查 PM 和刷新状态
            self.root.after(500, self.check_pm_running)
    
    def find_node(self):
        """查找 Node.js"""
        try:
            result = subprocess.run(['node', '--version'], 
                                  capture_output=True, text=True, timeout=5,
                                  creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
            if result.returncode == 0:
                return 'node'
        except:
            pass
        return None
    
    def check_pm_running(self):
        """检查 PM 是否运行"""
        try:
            response = requests.get(f"{self.pm_api}/status", timeout=2)
            if response.status_code == 200:
                self.log("PM 服务已运行", "success")
                # 立即刷新状态（增加延迟确保 GUI 完全加载）
                self.root.after(500, self.refresh_status)
                return True
        except:
            pass
        
        self.log("PM 服务未运行，正在启动...", "info")
        self.start_pm_daemon()
        # 启动后延迟刷新（增加延迟确保 PM 完全启动）
        self.root.after(5000, self.refresh_status)
        return False
    
    def start_pm_daemon(self):
        """启动 PM 守护进程"""
        try:
            cmd = [self.node_cmd, str(self.pm_js), 'start']
            subprocess.Popen(cmd, cwd=str(self.pm_dir),
                           creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
            time.sleep(2)
            self.log("PM 守护进程已启动", "success")
            self.refresh_status()
        except Exception as e:
            self.log(f"启动 PM 失败: {str(e)}", "error")
    
    def setup_ui(self):
        """设置界面"""
        # 顶部栏
        header = tk.Frame(self.root, bg="#2C3E50", height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        # 标题
        title_label = tk.Label(header, text="Sideria Process Manager",
                              font=("Segoe UI", 20, "bold"), 
                              bg="#2C3E50", fg="white")
        title_label.pack(side=tk.LEFT, padx=20, pady=20)
        
        # 版本标签
        version_label = tk.Label(header, text="v2.0",
                                font=("Segoe UI", 10), 
                                bg="#2C3E50", fg="#95A5A6")
        version_label.pack(side=tk.LEFT, pady=20)
        
        # 主容器
        main_container = tk.Frame(self.root, bg="#ECF0F1")
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 左侧：控制面板
        left_panel = tk.Frame(main_container, bg="#ECF0F1")
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 全局控制按钮
        control_frame = tk.Frame(left_panel, bg="white", relief=tk.RAISED, bd=1)
        control_frame.pack(fill=tk.X, pady=(0, 15))
        
        control_title = tk.Label(control_frame, text="全局控制",
                                font=("Segoe UI", 12, "bold"),
                                bg="white", fg="#2C3E50")
        control_title.pack(anchor=tk.W, padx=15, pady=(15, 10))
        
        btn_container = tk.Frame(control_frame, bg="white")
        btn_container.pack(padx=15, pady=(0, 15))
        
        ModernButton(btn_container, "启动全部", self.start_all, 
                    bg="#27AE60", width=110, height=35).pack(side=tk.LEFT, padx=5)
        ModernButton(btn_container, "停止全部", self.stop_all, 
                    bg="#E74C3C", width=110, height=35).pack(side=tk.LEFT, padx=5)
        ModernButton(btn_container, "重启全部", self.restart_all, 
                    bg="#F39C12", width=110, height=35).pack(side=tk.LEFT, padx=5)
        ModernButton(btn_container, "刷新状态", self.refresh_status, 
                    bg="#3498DB", width=110, height=35).pack(side=tk.LEFT, padx=5)
        ModernButton(btn_container, "服务管理", self.show_service_manager, 
                    bg="#9B59B6", width=110, height=35).pack(side=tk.LEFT, padx=5)
        
        # 服务列表
        services_frame = tk.Frame(left_panel, bg="white", relief=tk.RAISED, bd=1)
        services_frame.pack(fill=tk.BOTH, expand=True)
        
        services_title = tk.Label(services_frame, text="服务列表",
                                 font=("Segoe UI", 11, "bold"),
                                 bg="white", fg="#2C3E50")
        services_title.pack(anchor=tk.W, padx=15, pady=(10, 5))
        
        # 服务容器（网格布局，2列）
        self.services_container = tk.Frame(services_frame, bg="white")
        self.services_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # 右侧：日志面板
        right_panel = tk.Frame(main_container, bg="white", 
                              relief=tk.RAISED, bd=1, width=350)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(15, 0))
        right_panel.pack_propagate(False)
        
        log_title = tk.Label(right_panel, text="系统日志",
                            font=("Segoe UI", 12, "bold"),
                            bg="white", fg="#2C3E50")
        log_title.pack(anchor=tk.W, padx=15, pady=(15, 10))
        
        # 日志文本框
        log_frame = tk.Frame(right_panel, bg="white")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        self.log_text = scrolledtext.ScrolledText(log_frame,
                                                  font=("Consolas", 9),
                                                  bg="#2C3E50", fg="#ECF0F1",
                                                  relief=tk.FLAT,
                                                  wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 底部工具栏
        toolbar = tk.Frame(right_panel, bg="white")
        toolbar.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        ModernButton(toolbar, "清空日志", self.clear_log, 
                    bg="#95A5A6", width=100, height=30).pack(side=tk.LEFT, padx=5)
        ModernButton(toolbar, "打开日志目录", self.open_logs, 
                    bg="#3498DB", width=120, height=30).pack(side=tk.LEFT, padx=5)
        
        # 状态栏
        self.status_bar = tk.Frame(self.root, bg="#34495E", height=30)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_bar.pack_propagate(False)
        
        self.status_label = tk.Label(self.status_bar, text="就绪",
                                     font=("Segoe UI", 9),
                                     bg="#34495E", fg="white")
        self.status_label.pack(side=tk.LEFT, padx=15)
    
    def load_services(self):
        """加载服务列表"""
        try:
            with open(self.services_json, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
                services = data.get('services', {})
            
            # 清空现有卡片
            for widget in self.services_container.winfo_children():
                widget.destroy()
            self.service_cards.clear()
            
            # 只显示启用的服务
            enabled_services = {name: info for name, info in services.items() 
                              if info.get('enabled', True)}
            
            # 使用网格布局，2列显示
            row = 0
            col = 0
            for service_name, service_info in enabled_services.items():
                card = ServiceCard(self.services_container, service_name, 
                                 service_info, self)
                card.grid(row=row, column=col, sticky="ew", padx=5, pady=3)
                self.service_cards[service_name] = card
                
                col += 1
                if col >= 2:  # 2列布局
                    col = 0
                    row += 1
            
            # 配置列权重，使卡片均匀分布
            self.services_container.grid_columnconfigure(0, weight=1)
            self.services_container.grid_columnconfigure(1, weight=1)
            
            disabled_count = len(services) - len(enabled_services)
            if disabled_count > 0:
                self.log(f"已加载 {len(enabled_services)} 个服务 ({disabled_count} 个已禁用)", "success")
            else:
                self.log(f"已加载 {len(enabled_services)} 个服务", "success")
            
        except Exception as e:
            self.log(f"加载服务列表失败: {str(e)}", "error")
    
    def show_first_run_dialog(self):
        """首次运行对话框"""
        msg = "检测到首次运行，需要先进行配置\n\n配置向导将在新窗口中打开"
        if messagebox.askokcancel("首次运行", msg):
            self.run_setup()
        else:
            try:
                with open(self.services_json, 'w', encoding='utf-8') as f:
                    json.dump({"services": {}}, f, indent=2, ensure_ascii=False)
                self.log("已创建空配置文件", "info")
            except Exception as e:
                messagebox.showerror("错误", f"创建配置文件失败: {str(e)}")
    
    def api_call(self, endpoint, method='GET'):
        """调用 PM API"""
        try:
            url = f"{self.pm_api}{endpoint}"
            if method == 'GET':
                response = requests.get(url, timeout=5)
            else:
                response = requests.post(url, timeout=5)
            
            if response.status_code == 200:
                return response.json()
            else:
                self.log(f"API 返回错误状态码: {response.status_code}", "error")
                return None
        except requests.exceptions.Timeout:
            self.log(f"API 调用超时: {endpoint}", "error")
            return None
        except requests.exceptions.ConnectionError:
            self.log(f"无法连接到 PM: {endpoint}", "error")
            return None
        except Exception as e:
            self.log(f"API 调用失败: {str(e)}", "error")
            return None
    
    def start_all(self):
        """启动全部"""
        self.log("启动全部服务...", "info")
        threading.Thread(target=self._start_all_thread, daemon=True).start()
    
    def _start_all_thread(self):
        result = self.api_call('/start', 'POST')
        if result:
            self.root.after(0, lambda: self.log("启动命令已发送", "success"))
            time.sleep(2)
            self.root.after(0, self.refresh_status)
        else:
            self.root.after(0, lambda: self.log("启动失败", "error"))
    
    def stop_all(self):
        """停止全部"""
        self.log("停止全部服务...", "info")
        threading.Thread(target=self._stop_all_thread, daemon=True).start()
    
    def _stop_all_thread(self):
        result = self.api_call('/stop', 'POST')
        if result:
            self.root.after(0, lambda: self.log("停止命令已发送", "success"))
            time.sleep(1)
            self.root.after(0, self.refresh_status)
        else:
            self.root.after(0, lambda: self.log("停止失败", "error"))
    
    def restart_all(self):
        """重启全部"""
        self.log("重启全部服务...", "info")
        threading.Thread(target=self._restart_all_thread, daemon=True).start()
    
    def _restart_all_thread(self):
        result = self.api_call('/restart', 'POST')
        if result:
            self.root.after(0, lambda: self.log("重启命令已发送", "success"))
            time.sleep(2)
            self.root.after(0, self.refresh_status)
        else:
            self.root.after(0, lambda: self.log("重启失败", "error"))
    
    def refresh_status(self):
        """刷新状态"""
        self.log("刷新服务状态...", "info")
        threading.Thread(target=self._refresh_status_thread, daemon=True).start()
    
    def _refresh_status_thread(self):
        result = self.api_call('/status')
        if result:
            # PM 返回的格式是 {service_name: {status, pid, ...}, ...}
            updated_count = 0
            for service_name, status_info in result.items():
                if service_name in self.service_cards:
                    is_running = status_info.get('status') == 'running'
                    self.root.after(0, lambda n=service_name, r=is_running: 
                                  self.service_cards[n].update_status(r))
                    updated_count += 1
            self.root.after(0, lambda c=updated_count: self.log(f"状态已更新 ({c} 个服务)", "success"))
        else:
            self.root.after(0, lambda: self.log("获取状态失败 - PM 可能未响应", "error"))
    
    def start_service(self, service_name):
        """启动服务"""
        self.log(f"启动服务: {service_name}", "info")
        threading.Thread(target=self._start_service_thread, 
                        args=(service_name,), daemon=True).start()
    
    def _start_service_thread(self, service_name):
        result = self.api_call(f'/start?name={service_name}', 'POST')
        if result:
            self.root.after(0, lambda: self.log(f"{service_name} 启动命令已发送", "success"))
            time.sleep(1)
            self.root.after(0, self.refresh_status)
        else:
            self.root.after(0, lambda: self.log(f"{service_name} 启动失败", "error"))
    
    def stop_service(self, service_name):
        """停止服务"""
        self.log(f"停止服务: {service_name}", "info")
        threading.Thread(target=self._stop_service_thread, 
                        args=(service_name,), daemon=True).start()
    
    def _stop_service_thread(self, service_name):
        result = self.api_call(f'/stop?name={service_name}', 'POST')
        if result:
            self.root.after(0, lambda: self.log(f"{service_name} 停止命令已发送", "success"))
            time.sleep(1)
            self.root.after(0, self.refresh_status)
        else:
            self.root.after(0, lambda: self.log(f"{service_name} 停止失败", "error"))
    
    def restart_service(self, service_name):
        """重启服务"""
        self.log(f"重启服务: {service_name}", "info")
        threading.Thread(target=self._restart_service_thread, 
                        args=(service_name,), daemon=True).start()
    
    def _restart_service_thread(self, service_name):
        result = self.api_call(f'/restart?name={service_name}', 'POST')
        if result:
            self.root.after(0, lambda: self.log(f"{service_name} 重启命令已发送", "success"))
            time.sleep(1)
            self.root.after(0, self.refresh_status)
        else:
            self.root.after(0, lambda: self.log(f"{service_name} 重启失败", "error"))
    
    def run_setup(self):
        """运行配置向导"""
        try:
            cmd = [self.node_cmd, str(self.pm_js), 'setup']
            subprocess.Popen(cmd, cwd=str(self.pm_dir),
                           creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0)
            self.log("配置向导已在新窗口中打开", "info")
        except Exception as e:
            self.log(f"启动配置向导失败: {str(e)}", "error")
    
    def open_logs(self):
        """打开日志目录"""
        log_dir = self.pm_dir / "pm-logs"
        if log_dir.exists():
            os.startfile(str(log_dir))
        else:
            self.log("日志目录不存在", "error")
    
    def disable_service(self, service_name):
        """禁用服务"""
        if messagebox.askyesno("确认", f"确定要禁用服务 {service_name} 吗？\n禁用后需要重新启用才能使用。"):
            try:
                with open(self.services_json, 'r', encoding='utf-8-sig') as f:
                    config = json.load(f)
                
                if service_name in config['services']:
                    config['services'][service_name]['enabled'] = False
                    
                    with open(self.services_json, 'w', encoding='utf-8') as f:
                        json.dump(config, f, indent=2, ensure_ascii=False)
                    
                    self.log(f"已禁用服务: {service_name}", "success")
                    self.stop_service(service_name)
                    time.sleep(0.5)
                    self.load_services()
            except Exception as e:
                self.log(f"禁用服务失败: {str(e)}", "error")
    
    def show_service_manager(self):
        """显示服务管理窗口"""
        # 如果窗口已存在，激活它
        if self.service_manager_window and self.service_manager_window.winfo_exists():
            self.service_manager_window.lift()
            self.service_manager_window.focus_force()
            return
        
        manager = tk.Toplevel(self.root)
        self.service_manager_window = manager
        manager.title("服务管理")
        manager.geometry("650x550")
        manager.configure(bg="#ECF0F1")
        
        # 窗口关闭时清理引用
        def on_close():
            self.service_manager_window = None
            manager.destroy()
        
        manager.protocol("WM_DELETE_WINDOW", on_close)
        
        # 标题
        title_frame = tk.Frame(manager, bg="#2C3E50", height=60)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        title = tk.Label(title_frame, text="服务管理",
                        font=("Segoe UI", 14, "bold"),
                        bg="#2C3E50", fg="white")
        title.pack(side=tk.LEFT, padx=20, pady=15)
        
        subtitle = tk.Label(title_frame, text="启用或禁用服务",
                           font=("Segoe UI", 9),
                           bg="#2C3E50", fg="#95A5A6")
        subtitle.pack(side=tk.LEFT, pady=15)
        
        # 服务列表框架
        list_frame = tk.Frame(manager, bg="white", relief=tk.RAISED, bd=1)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 滚动区域
        canvas = tk.Canvas(list_frame, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        services_container = tk.Frame(canvas, bg="white")
        
        services_container.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=services_container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        def refresh_service_list():
            """刷新服务列表"""
            # 清空现有内容
            for widget in services_container.winfo_children():
                widget.destroy()
            
            # 加载所有服务
            try:
                with open(self.services_json, 'r', encoding='utf-8-sig') as f:
                    config = json.load(f)
                    all_services = config.get('services', {})
                
                for service_name, service_info in all_services.items():
                    service_frame = tk.Frame(services_container, bg="white",
                                            relief=tk.GROOVE, bd=1)
                    service_frame.pack(fill=tk.X, pady=5, padx=10)
                    
                    # 内容框架
                    content_frame = tk.Frame(service_frame, bg="white")
                    content_frame.pack(fill=tk.X, padx=15, pady=10)
                    
                    # 服务名称
                    name_label = tk.Label(content_frame, 
                                         text=service_info.get('name', service_name),
                                         font=("Segoe UI", 11, "bold"),
                                         bg="white", fg="#2C3E50", anchor=tk.W)
                    name_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
                    
                    # 状态标签
                    enabled = service_info.get('enabled', True)
                    status_text = "已启用" if enabled else "已禁用"
                    status_color = "#27AE60" if enabled else "#95A5A6"
                    
                    status_label = tk.Label(content_frame,
                                           text=status_text,
                                           font=("Segoe UI", 9),
                                           bg="white", fg=status_color)
                    status_label.pack(side=tk.LEFT, padx=10)
                    
                    # 切换按钮
                    def make_toggle_command(sname=service_name):
                        def toggle():
                            try:
                                with open(self.services_json, 'r', encoding='utf-8-sig') as f:
                                    cfg = json.load(f)
                                
                                current_state = cfg['services'][sname].get('enabled', True)
                                cfg['services'][sname]['enabled'] = not current_state
                                
                                with open(self.services_json, 'w', encoding='utf-8') as f:
                                    json.dump(cfg, f, indent=2, ensure_ascii=False)
                                
                                action = "启用" if not current_state else "禁用"
                                self.log(f"已{action}服务: {sname}", "success")
                                
                                # 刷新服务列表和主界面
                                refresh_service_list()
                                self.load_services()
                                self.refresh_status()
                            except Exception as e:
                                messagebox.showerror("错误", f"操作失败: {str(e)}")
                        return toggle
                    
                    if enabled:
                        btn = tk.Button(content_frame, text="禁用",
                                       bg="#E74C3C", fg="white",
                                       font=("Segoe UI", 9),
                                       relief=tk.FLAT, padx=20, pady=5,
                                       cursor="hand2",
                                       command=make_toggle_command())
                    else:
                        btn = tk.Button(content_frame, text="启用",
                                       bg="#27AE60", fg="white",
                                       font=("Segoe UI", 9),
                                       relief=tk.FLAT, padx=20, pady=5,
                                       cursor="hand2",
                                       command=make_toggle_command())
                    btn.pack(side=tk.RIGHT)
                    
            except Exception as e:
                error_label = tk.Label(services_container,
                                      text=f"加载失败: {str(e)}",
                                      bg="white", fg="#E74C3C",
                                      font=("Segoe UI", 10))
                error_label.pack(pady=20)
        
        # 初始加载
        refresh_service_list()
        
        # 底部按钮
        bottom_frame = tk.Frame(manager, bg="#ECF0F1")
        bottom_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        close_btn = tk.Button(bottom_frame, text="关闭",
                             bg="#95A5A6", fg="white",
                             font=("Segoe UI", 10),
                             relief=tk.FLAT, padx=30, pady=8,
                             cursor="hand2",
                             command=on_close)
        close_btn.pack(side=tk.RIGHT)
    
    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
    
    def log(self, message, level="info"):
        """添加日志"""
        timestamp = time.strftime("%H:%M:%S")
        prefix = {"info": "ℹ", "error": "✖", "success": "✓"}.get(level, "•")
        
        self.log_text.insert(tk.END, f"[{timestamp}] {prefix} {message}\n")
        self.log_text.see(tk.END)

def main():
    root = tk.Tk()
    app = SideriaPMGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
