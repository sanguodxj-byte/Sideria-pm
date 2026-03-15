#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sideria Process Manager - Enhanced GUI v3.0
希德莉亚进程管理器 - 增强版现代界面
Features: Dark theme, sidebar nav, gcli gateway panel, openclaw.json editor
"""

import os, sys, subprocess, json, threading, time, webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog

# Windows DPI & console hide
if sys.platform == 'win32':
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    try: ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except:
        try: ctypes.windll.user32.SetProcessDPIAware()
        except: pass

try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'requests'])
    import requests

# ═══════════════════════════════════════════════════
# Design System - Dark Theme
# ═══════════════════════════════════════════════════
COLORS = {
    'bg_primary': '#0D1117',
    'bg_secondary': '#161B22',
    'bg_tertiary': '#21262D',
    'bg_card': '#161B22',
    'bg_card_hover': '#1C2128',
    'bg_input': '#0D1117',
    'border': '#30363D',
    'border_active': '#58A6FF',
    'text_primary': '#F0F6FC',
    'text_secondary': '#8B949E',
    'text_muted': '#484F58',
    'accent_blue': '#58A6FF',
    'accent_green': '#3FB950',
    'accent_red': '#F85149',
    'accent_yellow': '#D29922',
    'accent_purple': '#BC8CFF',
    'accent_orange': '#F0883E',
    'sidebar_bg': '#010409',
    'sidebar_active': '#161B22',
    'sidebar_hover': '#0D1117',
    'header_bg': '#0D1117',
    'scrollbar': '#30363D',
    'scrollbar_active': '#484F58',
}

# ═══════════════════════════════════════════════════
# Tooltip Helper
# ═══════════════════════════════════════════════════
class ToolTip:
    """Create a tooltip for a widget with proper resource management"""
    def __init__(self, widget, text, delay=500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tip_window = None
        self.id = None
        self._bindings = []
        try:
            self._bindings.append(widget.bind('<Enter>', self._enter))
            self._bindings.append(widget.bind('<Leave>', self._leave))
            # Clean up when widget is destroyed
            widget.bind('<Destroy>', self._cleanup, add='+')
        except tk.TclError:
            pass  # Widget may already be destroyed

    def _enter(self, event=None):
        self._schedule()

    def _schedule(self):
        if self.tip_window:
            return
        try:
            self.id = self.widget.after(self.delay, self._show_tip)
        except tk.TclError:
            pass  # Widget may be destroyed

    def _leave(self, event=None):
        self._cancel()
        self._hide_tip()

    def _cancel(self):
        if self.id:
            try:
                self.widget.after_cancel(self.id)
            except tk.TclError:
                pass  # Widget may be destroyed
            self.id = None

    def _show_tip(self):
        if self.tip_window:
            return
        try:
            x = self.widget.winfo_rootx() + 20
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
            self.tip_window = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            label = tk.Label(tw, text=self.text, font=FONTS['small'],
                            bg=COLORS['bg_tertiary'], fg=COLORS['text_primary'],
                            relief='solid', borderwidth=1, padx=6, pady=4)
            label.pack()
        except tk.TclError:
            self.tip_window = None

    def _hide_tip(self):
        if self.tip_window:
            try:
                self.tip_window.destroy()
            except tk.TclError:
                pass  # Window may already be destroyed
            self.tip_window = None

    def _cleanup(self, event=None):
        """Clean up resources when widget is destroyed"""
        self._cancel()
        self._hide_tip()

def run_threaded(target, daemon=True, log_errors=True):
    """Run a function in a thread with optional error logging"""
    def wrapper():
        try:
            target()
        except Exception as e:
            if log_errors:
                print(f"[Thread Error] {e}")
    threading.Thread(target=wrapper, daemon=daemon).start()

FONT_FAMILY = 'Segoe UI'
FONTS = {
    'h1': (FONT_FAMILY, 18, 'bold'),
    'h2': (FONT_FAMILY, 14, 'bold'),
    'h3': (FONT_FAMILY, 12, 'bold'),
    'body': (FONT_FAMILY, 10),
    'body_bold': (FONT_FAMILY, 10, 'bold'),
    'small': (FONT_FAMILY, 9),
    'tiny': (FONT_FAMILY, 8),
    'mono': ('Consolas', 10),
    'mono_small': ('Consolas', 9),
    'icon': ('Segoe UI Emoji', 14),
    'icon_small': ('Segoe UI Emoji', 11),
}

OPENCLAW_CONFIG_PATH = Path.home() / '.openclaw' / 'openclaw.json'

# ═══════════════════════════════════════════════════
# Rounded Card Widget
# ═══════════════════════════════════════════════════
class CardFrame(tk.Frame):
    """Dark themed card with border"""
    def __init__(self, parent, **kw):
        kw.setdefault('bg', COLORS['bg_card'])
        kw.setdefault('highlightbackground', COLORS['border'])
        kw.setdefault('highlightthickness', 1)
        kw.setdefault('padx', 16)
        kw.setdefault('pady', 12)
        super().__init__(parent, **kw)

# ═══════════════════════════════════════════════════
# Animated Status Dot
# ═══════════════════════════════════════════════════
class StatusDot(tk.Canvas):
    def __init__(self, parent, size=10, **kw):
        kw['bg'] = kw.get('bg', parent['bg'])
        kw['highlightthickness'] = 0
        super().__init__(parent, width=size+4, height=size+4, **kw)
        self.size = size
        self.color = COLORS['text_muted']
        self.pulse_id = None
        self.glow = self.create_oval(0, 0, size+4, size+4, fill='', outline='', width=0)
        self.dot = self.create_oval(2, 2, size+2, size+2, fill=self.color, outline='')

    def set_status(self, running):
        if running:
            self.color = COLORS['accent_green']
            self.itemconfig(self.dot, fill=self.color)
            self._start_pulse()
        else:
            self.color = COLORS['accent_red']
            self.itemconfig(self.dot, fill=self.color)
            self.itemconfig(self.glow, fill='', outline='')
            self._stop_pulse()

    def _start_pulse(self):
        self._stop_pulse()
        self._pulse_step(0)

    def _stop_pulse(self):
        if self.pulse_id:
            self.after_cancel(self.pulse_id)
            self.pulse_id = None

    def _pulse_step(self, step):
        alpha = abs((step % 20) - 10) / 10.0
        r, g, b = 63, 185, 80
        bg = self['bg']
        try:
            br = int(bg[1:3], 16); bg_ = int(bg[3:5], 16); bb = int(bg[5:7], 16)
        except: br, bg_, bb = 22, 27, 34
        nr = int(br + (r - br) * alpha * 0.3)
        ng = int(bg_ + (g - bg_) * alpha * 0.3)
        nb = int(bb + (b - bb) * alpha * 0.3)
        self.itemconfig(self.glow, fill=f'#{nr:02x}{ng:02x}{nb:02x}', outline='')
        self.pulse_id = self.after(100, self._pulse_step, step + 1)

# ═══════════════════════════════════════════════════
# Modern Button
# ═══════════════════════════════════════════════════
class ModernBtn(tk.Label):
    def __init__(self, parent, text, command, bg=None, fg=None, width=None, **kw):
        bg = bg or COLORS['accent_blue']
        fg = fg or '#FFFFFF'
        super().__init__(parent, text=text, bg=bg, fg=fg,
                        font=FONTS['small'], padx=12, pady=5,
                        cursor='hand2', **kw)
        self._cmd = command
        self._bg = bg
        self._fg = fg
        self.bind('<Button-1>', lambda e: self._cmd())
        self.bind('<Enter>', lambda e: self.config(bg=self._lighten(bg)))
        self.bind('<Leave>', lambda e: self.config(bg=self._bg))
        if width:
            self.config(width=width)

    def _lighten(self, color):
        try:
            r, g, b = int(color[1:3],16), int(color[3:5],16), int(color[5:7],16)
            return f'#{min(255,r+25):02x}{min(255,g+25):02x}{min(255,b+25):02x}'
        except: return color

# ═══════════════════════════════════════════════════
# Service Card
# ═══════════════════════════════════════════════════
class ServiceCard(CardFrame):
    def __init__(self, parent, svc_name, svc_info, controller):
        super().__init__(parent)
        self.svc_name = svc_name
        self.controller = controller
        self.svc_info = svc_info  # Store for later access

        top = tk.Frame(self, bg=COLORS['bg_card'])
        top.pack(fill=tk.X)

        self.status_dot = StatusDot(top, bg=COLORS['bg_card'])
        self.status_dot.pack(side=tk.LEFT, padx=(0, 8))

        name_text = svc_info.get('name', svc_name)
        tk.Label(top, text=name_text, font=FONTS['body_bold'],
                bg=COLORS['bg_card'], fg=COLORS['text_primary']).pack(side=tk.LEFT)

        self.status_lbl = tk.Label(top, text="—", font=FONTS['tiny'],
                                   bg=COLORS['bg_card'], fg=COLORS['text_secondary'])
        self.status_lbl.pack(side=tk.RIGHT)

        self.info_lbl = tk.Label(self, text="PID: — | Uptime: —", font=FONTS['tiny'],
                                 bg=COLORS['bg_card'], fg=COLORS['text_muted'])
        self.info_lbl.pack(anchor=tk.W, pady=(4, 4))

        btns = tk.Frame(self, bg=COLORS['bg_card'])
        btns.pack(anchor=tk.W)

        ModernBtn(btns, "▶ 启动", lambda: controller.start_service(svc_name),
                 bg=COLORS['accent_green']).pack(side=tk.LEFT, padx=(0,4))
        ModernBtn(btns, "⏹ 停止", lambda: controller.stop_service(svc_name),
                 bg=COLORS['accent_red']).pack(side=tk.LEFT, padx=(0,4))
        ModernBtn(btns, "↻ 重启", lambda: controller.restart_service(svc_name),
                 bg=COLORS['accent_yellow']).pack(side=tk.LEFT, padx=(0,4))
        ModernBtn(btns, "📋 日志", lambda: controller.show_service_log(svc_name),
                 bg=COLORS['bg_tertiary']).pack(side=tk.LEFT)

    
        self.is_enabled = svc_info.get('enabled', True)
        self.enable_btn = ModernBtn(btns, '✅ 启用' if self.is_enabled else '❌ 禁用',
                                   lambda: controller.toggle_service_enabled(self.svc_name, self.is_enabled),
                                   bg=COLORS['accent_green'] if self.is_enabled else COLORS['text_muted'])
        self.enable_btn.pack(side=tk.LEFT, padx=(0,4))
        
        # Browse folder button - opens service working directory
        ModernBtn(btns, "📁 浏览", self._browse_folder,
                 bg=COLORS['accent_purple']).pack(side=tk.LEFT, padx=(0,4))
    
    def _browse_folder(self):
        """Open the service's working directory in file explorer"""
        cwd = self.svc_info.get('cwd', '')
        if cwd:
            import subprocess
            import platform
            try:
                if platform.system() == 'Windows':
                    subprocess.run(['explorer', cwd], check=False)
                elif platform.system() == 'Darwin':  # macOS
                    subprocess.run(['open', cwd], check=False)
                else:  # Linux
                    subprocess.run(['xdg-open', cwd], check=False)
            except Exception as e:
                print(f"Failed to open folder: {e}")
    def update_status(self, info):
        running = info.get('status') == 'running'
        self.status_dot.set_status(running)
        self.status_lbl.config(text="运行中" if running else "已停止",
                              fg=COLORS['accent_green'] if running else COLORS['accent_red'])
        pid = info.get('pid', '—') or '—'
        uptime = info.get('uptime', 0)
        if uptime > 0:
            h, rem = divmod(uptime, 3600)
            m, s = divmod(rem, 60)
            ustr = f"{h}h {m}m {s}s" if h else (f"{m}m {s}s" if m else f"{s}s")
        else:
            ustr = "—"
        
        self.is_enabled = info.get('enabled', True)
        self.enable_btn.config(text='✅ 启用' if self.is_enabled else '❌ 禁用', bg=COLORS['accent_green'] if self.is_enabled else COLORS['text_muted'])
        self.enable_btn._bg = COLORS['accent_green'] if self.is_enabled else COLORS['text_muted']
        restarts = info.get('restarts', 0)
        self.info_lbl.config(text=f"PID: {pid} | Uptime: {ustr} | Restarts: {restarts}")


# ═══════════════════════════════════════════════════
# Main Application
# ═══════════════════════════════════════════════════
class SideriaPMGUI:
    PAGES = [
        ('dashboard', '🏠', '总览'),
        ('services', '📦', '服务管理'),
        ('webui', '🌐', '拓展面板'),
        ('config', '⚙️', 'OpenClaw 配置'),
        ('logs', '📋', '日志中心'),
        ('about', 'ℹ️', '关于'),
    ]

    def __init__(self, root):
        self.root = root
        self.root.title("Sideria PM Enhanced v3.0")
        self.root.geometry("1300x820")
        self.root.configure(bg=COLORS['bg_primary'])
        self.root.minsize(1000, 600)

        if getattr(sys, 'frozen', False):
            exe_dir = Path(sys.executable).parent
            self.pm_dir = exe_dir.parent if exe_dir.name == 'dist' else exe_dir
        else:
            self.pm_dir = Path(__file__).parent

        self.pm_js = self.pm_dir / "sideria-pm.js"
        self.services_json = self.pm_dir / "services.json"
        self.pm_api = "http://127.0.0.1:29997"
        self.node_cmd = self._find_node()
        self.service_cards = {}
        self.webui_widgets = {}
        self.current_page = None
        self.pages = {}
        self.auto_refresh_id = None

        self._build_ui()
        self.switch_page('dashboard')

        if not self.services_json.exists():
            self.root.after(500, self._first_run)
        else:
            self.root.after(500, self._check_pm)

    def _find_node(self):
        try:
            r = subprocess.run(['node', '--version'], capture_output=True, text=True, timeout=5,
                              creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0)
            if r.returncode == 0: return 'node'
        except: pass
        return None

    def _build_ui(self):
        # Scrollbar styling for dark theme
        style = ttk.Style()
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        style.configure("Vertical.TScrollbar",
            background=COLORS['border'],
            troughcolor=COLORS['bg_primary'],
            bordercolor=COLORS['bg_primary'],
            arrowcolor=COLORS['text_primary'],
            relief='flat'
        )
        style.map("Vertical.TScrollbar",
            background=[('active', COLORS['accent_blue']), ('pressed', COLORS['accent_blue'])]
        )

        # Sidebar
        self.sidebar = tk.Frame(self.root, bg=COLORS['sidebar_bg'], width=200)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        # Sidebar header
        hdr = tk.Frame(self.sidebar, bg=COLORS['sidebar_bg'])
        hdr.pack(fill=tk.X, padx=16, pady=(20, 24))
        tk.Label(hdr, text="🐉", font=('Segoe UI Emoji', 24),
                bg=COLORS['sidebar_bg'], fg=COLORS['accent_blue']).pack(anchor=tk.W)
        tk.Label(hdr, text="Sideria PM", font=FONTS['h2'],
                bg=COLORS['sidebar_bg'], fg=COLORS['text_primary']).pack(anchor=tk.W)
        tk.Label(hdr, text="Enhanced v3.0", font=FONTS['tiny'],
                bg=COLORS['sidebar_bg'], fg=COLORS['text_muted']).pack(anchor=tk.W)

        # Nav items
        self.nav_items = {}
        for key, icon, label in self.PAGES:
            item = tk.Frame(self.sidebar, bg=COLORS['sidebar_bg'], cursor='hand2')
            item.pack(fill=tk.X, padx=8, pady=1)
            lbl = tk.Label(item, text=f"  {icon}  {label}", font=FONTS['body'],
                          bg=COLORS['sidebar_bg'], fg=COLORS['text_secondary'],
                          anchor=tk.W, padx=8, pady=8)
            lbl.pack(fill=tk.X)
            for w in (item, lbl):
                w.bind('<Button-1>', lambda e, k=key: self.switch_page(k))
                w.bind('<Enter>', lambda e, i=item, l=lbl, k=key: self._nav_hover(i, l, k, True))
                w.bind('<Leave>', lambda e, i=item, l=lbl, k=key: self._nav_hover(i, l, k, False))
            self.nav_items[key] = (item, lbl)

        # Status indicator at bottom of sidebar
        tk.Frame(self.sidebar, bg=COLORS['sidebar_bg']).pack(fill=tk.BOTH, expand=True)
        self.pm_status_frame = tk.Frame(self.sidebar, bg=COLORS['sidebar_bg'])
        self.pm_status_frame.pack(fill=tk.X, padx=16, pady=16)
        self.pm_status_dot = StatusDot(self.pm_status_frame, size=8, bg=COLORS['sidebar_bg'])
        self.pm_status_dot.pack(side=tk.LEFT, padx=(0,6))
        self.pm_status_lbl = tk.Label(self.pm_status_frame, text="PM: 检查中...",
                                      font=FONTS['tiny'], bg=COLORS['sidebar_bg'],
                                      fg=COLORS['text_muted'])
        self.pm_status_lbl.pack(side=tk.LEFT)

        # Main content area
        self.content = tk.Frame(self.root, bg=COLORS['bg_primary'])
        self.content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create page containers
        for key, _, _ in self.PAGES:
            frame = tk.Frame(self.content, bg=COLORS['bg_primary'])
            self.pages[key] = frame

    def _nav_hover(self, item, lbl, key, entering):
        if key == self.current_page: return
        c = COLORS['sidebar_hover'] if entering else COLORS['sidebar_bg']
        fc = COLORS['text_primary'] if entering else COLORS['text_secondary']
        item.config(bg=c); lbl.config(bg=c, fg=fc)

    def switch_page(self, key):
        if self.current_page == key: return
        # Hide current
        if self.current_page and self.current_page in self.pages:
            self.pages[self.current_page].pack_forget()
        # Update nav styling
        if self.current_page and self.current_page in self.nav_items:
            old_item, old_lbl = self.nav_items[self.current_page]
            old_item.config(bg=COLORS['sidebar_bg'])
            old_lbl.config(bg=COLORS['sidebar_bg'], fg=COLORS['text_secondary'])
        self.current_page = key
        item, lbl = self.nav_items[key]
        item.config(bg=COLORS['sidebar_active'])
        lbl.config(bg=COLORS['sidebar_active'], fg=COLORS['accent_blue'])
        # Build page if empty
        page = self.pages[key]
        if not page.winfo_children():
            builder = getattr(self, f'_build_{key}_page', None)
            if builder: builder(page)
        page.pack(fill=tk.BOTH, expand=True)

    # ══════════ API Helper ══════════
    def api_call(self, endpoint):
        try:
            r = requests.get(f"{self.pm_api}{endpoint}", timeout=5)
            if r.status_code == 200: return r.json()
        except: pass
        return None

    def api_call_text(self, endpoint):
        try:
            r = requests.get(f"{self.pm_api}{endpoint}", timeout=5)
            if r.status_code == 200: return r.text
        except: pass
        return None

    # ══════════ PM Management ══════════
    def _check_pm(self):
        def check():
            try:
                r = requests.get(f"{self.pm_api}/health", timeout=2)
                if r.status_code == 200:
                    self.root.after(0, lambda: self._set_pm_status(True))
                    self.root.after(0, self.refresh_status)
                    return
            except: pass
            self.root.after(0, lambda: self._set_pm_status(False))
            self.root.after(0, lambda: self.log("PM 未运行，正在启动...", "info"))
            self._start_pm()
            time.sleep(1)
            self.root.after(0, lambda: self._set_pm_status(True))
            self.root.after(0, self.refresh_status)
            time.sleep(3)
            self.root.after(0, self.refresh_status)
        run_threaded(check)

    def _start_pm(self):
        if not self.node_cmd: return
        try:
            subprocess.Popen([self.node_cmd, str(self.pm_js), 'start'],
                           cwd=str(self.pm_dir),
                           creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0)
        except Exception as e:
            self.root.after(0, lambda: self.log(f"启动 PM 失败: {e}", "error"))

    def _set_pm_status(self, running):
        self.pm_status_dot.set_status(running)
        self.pm_status_lbl.config(text=f"PM: {'运行中' if running else '已停止'}",
                                  fg=COLORS['accent_green'] if running else COLORS['accent_red'])

    def _first_run(self):
        if messagebox.askokcancel("首次运行", "检测到首次运行，需要先进行配置\n配置向导将在新窗口中打开"):
            self._run_setup()
        else:
            with open(self.services_json, 'w', encoding='utf-8') as f:
                json.dump({"services": {}}, f, indent=2, ensure_ascii=False)

    def _run_setup(self):
        if not self.node_cmd: return
        try:
            subprocess.Popen([self.node_cmd, str(self.pm_js), 'setup'],
                           cwd=str(self.pm_dir),
                           creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform=='win32' else 0)
        except: pass

    # ══════════ Service Operations ══════════
    def start_service(self, name):
        self.log(f"启动 {name}...", "info")
        run_threaded(lambda: self._svc_op('start', name))

    
    def toggle_service_enabled(self, name, current_state):
        try:
            action = 'disable' if current_state else 'enable'
            act = '禁用' if current_state else '启用'
            self.log(f'请求后端{act}服务: {name}...', 'info')
            def op():
                res = self.api_call(f'/{action}?name={name}')
                if res and res.get('ok'):
                    self.root.after(0, lambda: self.log(f'✅ 已成功{act}服务: {name}', 'success'))
                else:
                    self.root.after(0, lambda: self.log(f'❌ {act}服务 {name} 失败', 'error'))
                self.root.after(1000, self.refresh_status)
            run_threaded(op)
        except Exception as e:
            self.log(f'调用 API 修改状态失败: {e}', 'error')
    def stop_service(self, name):
        self.log(f"停止 {name}...", "info")
        run_threaded(lambda: self._svc_op('stop', name))

    def restart_service(self, name):
        self.log(f"重启 {name}...", "info")
        run_threaded(lambda: self._svc_op('restart', name))

    def _svc_op(self, action, name):
        result = self.api_call(f'/{action}?name={name}')
        time.sleep(1.5)
        self.root.after(0, self.refresh_status)

    def show_service_log(self, name):
        txt = self.api_call_text(f'/logs?name={name}&lines=80')
        if not txt: txt = "(无日志)"
        win = tk.Toplevel(self.root)
        win.title(f"日志 - {name}")
        win.geometry("800x500")
        win.configure(bg=COLORS['bg_primary'])
        st = scrolledtext.ScrolledText(win, font=FONTS['mono_small'],
                                       bg=COLORS['bg_secondary'], fg=COLORS['text_primary'],
                                       insertbackground=COLORS['text_primary'],
                                       relief=tk.FLAT, wrap=tk.WORD)
        st.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        st.insert(tk.END, txt)
        st.see(tk.END)

    # ══════════ Refresh ══════════
    def refresh_status(self):
        run_threaded(self._refresh_thread)

    def _refresh_thread(self):
        result = self.api_call('/status')
        if result is not None:
            for name, card in self.service_cards.items():
                if name in result:
                    self.root.after(0, lambda n=name, i=result[name]: self.service_cards[n].update_status(i))
                else:
                    info = { 'status': 'stopped', 'pid': None, 'uptime': 0, 'restarts': 0, 'health': 'no-check', 'enabled': False }
                    self.root.after(0, lambda n=name, i=info: self.service_cards[n].update_status(i))
            self.root.after(0, lambda: self.log(f"状态已刷新 ({len(result)} 个运行池服务)", "success"))
            # Update dashboard counters
            self.root.after(0, lambda r=result: self._update_dashboard_stats(r))
        self._schedule_auto_refresh()

    def _schedule_auto_refresh(self):
        if self.auto_refresh_id:
            self.root.after_cancel(self.auto_refresh_id)
        self.auto_refresh_id = self.root.after(15000, self.refresh_status)

    def _update_dashboard_stats(self, data):
        if not hasattr(self, 'dash_stats'): return
        total = len(data)
        running = sum(1 for s in data.values() if s.get('status') == 'running')
        healthy = sum(1 for s in data.values() if s.get('health') == 'healthy')
        stopped = total - running
        stats = [
            (str(total), '总服务', COLORS['accent_blue']),
            (str(running), '运行中', COLORS['accent_green']),
            (str(stopped), '已停止', COLORS['accent_red']),
            (str(healthy), '健康', COLORS['accent_green']),
        ]
        for i, (val, _, color) in enumerate(stats):
            if i < len(self.dash_stats):
                self.dash_stats[i].config(text=val, fg=color)

    # ══════════ Logger ══════════
    def log(self, msg, level="info"):
        if not hasattr(self, 'log_text_widget'): return
        ts = time.strftime("%H:%M:%S")
        prefix = {"info": "ℹ", "error": "✖", "success": "✓", "warn": "⚠"}.get(level, "•")
        colors = {"info": COLORS['accent_blue'], "error": COLORS['accent_red'],
                  "success": COLORS['accent_green'], "warn": COLORS['accent_yellow']}
        tag = f"log_{level}"
        self.log_text_widget.config(state=tk.NORMAL)
        self.log_text_widget.insert(tk.END, f"[{ts}] {prefix} {msg}\n", tag)
        self.log_text_widget.tag_config(tag, foreground=colors.get(level, COLORS['text_primary']))
        self.log_text_widget.see(tk.END)
        self.log_text_widget.config(state=tk.DISABLED)

    # ══════════════════════════════════════════════
    # PAGE: Dashboard
    # ══════════════════════════════════════════════
    def _build_dashboard_page(self, page):
        inner = self._make_scrollable_frame(page)
        pad = tk.Frame(inner, bg=COLORS['bg_primary'])
        pad.pack(fill=tk.BOTH, expand=True, padx=24, pady=16)

        # Header
        tk.Label(pad, text="🏠 总览 Dashboard", font=FONTS['h1'],
                bg=COLORS['bg_primary'], fg=COLORS['text_primary']).pack(anchor=tk.W, pady=(0,16))

        # Stats row
        stats_frame = tk.Frame(pad, bg=COLORS['bg_primary'])
        stats_frame.pack(fill=tk.X, pady=(0, 16))
        self.dash_stats = []
        for val, label, color in [("—", "总服务", COLORS['accent_blue']),
                                   ("—", "运行中", COLORS['accent_green']),
                                   ("—", "已停止", COLORS['accent_red']),
                                   ("—", "健康", COLORS['accent_green'])]:
            card = CardFrame(stats_frame)
            card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
            val_lbl = tk.Label(card, text=val, font=(FONT_FAMILY, 28, 'bold'),
                              bg=COLORS['bg_card'], fg=color)
            val_lbl.pack(anchor=tk.W)
            tk.Label(card, text=label, font=FONTS['small'],
                    bg=COLORS['bg_card'], fg=COLORS['text_secondary']).pack(anchor=tk.W)
            self.dash_stats.append(val_lbl)

        # Quick Actions
        actions_card = CardFrame(pad)
        actions_card.pack(fill=tk.X, pady=(0, 16))
        tk.Label(actions_card, text="快速操作", font=FONTS['h3'],
                bg=COLORS['bg_card'], fg=COLORS['text_primary']).pack(anchor=tk.W, pady=(0,8))
        btn_row = tk.Frame(actions_card, bg=COLORS['bg_card'])
        btn_row.pack(anchor=tk.W)
        for text, cmd, color in [
            ("▶ 启动全部", lambda: self._global_op('start'), COLORS['accent_green']),
            ("⏹ 停止全部", lambda: self._global_op('stop'), COLORS['accent_red']),
            ("↻ 重启全部", lambda: self._global_op('restart'), COLORS['accent_yellow']),
            ("🔄 刷新状态", self.refresh_status, COLORS['accent_blue']),
            ("🔧 配置向导", self._run_setup, COLORS['accent_purple']),
        ]:
            ModernBtn(btn_row, text, cmd, bg=color).pack(side=tk.LEFT, padx=(0,6))

        # Log widget embedded in dashboard
        log_card = CardFrame(pad)
        log_card.pack(fill=tk.BOTH, expand=True)
        tk.Label(log_card, text="系统日志", font=FONTS['h3'],
                bg=COLORS['bg_card'], fg=COLORS['text_primary']).pack(anchor=tk.W, pady=(0,8))
        self.log_text_widget = scrolledtext.ScrolledText(
            log_card, font=FONTS['mono_small'], bg=COLORS['bg_primary'],
            fg=COLORS['text_primary'], insertbackground=COLORS['text_primary'],
            relief=tk.FLAT, height=10, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text_widget.pack(fill=tk.BOTH, expand=True)

    def _global_op(self, action):
        self.log(f"{action} 全部服务...", "info")
        def op():
            self.api_call(f'/{action}')
            time.sleep(2)
            self.root.after(0, self.refresh_status)
        run_threaded(op)

    # ══════════════════════════════════════════════
    # PAGE: Services
    # ══════════════════════════════════════════════
    def _build_services_page(self, page):
        inner = self._make_scrollable_frame(page)
        pad = tk.Frame(inner, bg=COLORS['bg_primary'])
        pad.pack(fill=tk.BOTH, expand=True, padx=24, pady=16)

        hdr = tk.Frame(pad, bg=COLORS['bg_primary'])
        hdr.pack(fill=tk.X, pady=(0, 16))
        tk.Label(hdr, text="📦 服务管理", font=FONTS['h1'],
                bg=COLORS['bg_primary'], fg=COLORS['text_primary']).pack(side=tk.LEFT)
        ModernBtn(hdr, "🔄 刷新", self.refresh_status,
                 bg=COLORS['accent_blue']).pack(side=tk.RIGHT)

        # Service grid
        self.svc_grid = tk.Frame(pad, bg=COLORS['bg_primary'])
        self.svc_grid.pack(fill=tk.BOTH, expand=True)
        self._load_service_cards()

    def _load_service_cards(self):
        for w in self.svc_grid.winfo_children():
            w.destroy()
        self.service_cards.clear()
        try:
            with open(self.services_json, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
            services = data.get('services', {})
            row, col = 0, 0
            for name, info in services.items():
                card = ServiceCard(self.svc_grid, name, info, self)
                card.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
                self.service_cards[name] = card
                col += 1
                if col >= 2:
                    col = 0; row += 1
            self.svc_grid.grid_columnconfigure(0, weight=1)
            self.svc_grid.grid_columnconfigure(1, weight=1)
        except Exception as e:
            tk.Label(self.svc_grid, text=f"加载失败: {e}", fg=COLORS['accent_red'],
                    bg=COLORS['bg_primary'], font=FONTS['body']).pack(pady=20)

    # ══════════════════════════════════════════════
    # PAGE: WebUI Ext Integration
    # ══════════════════════════════════════════════
    def _build_webui_page(self, page):
        container = self._make_scrollable_frame(page)
        
        hdr = tk.Frame(container, bg=COLORS['bg_primary'])
        hdr.pack(fill=tk.X, padx=4, pady=(0, 16))
        tk.Label(hdr, text="🌐 拓展 WebUI 面板", font=FONTS['h1'],
                bg=COLORS['bg_primary'], fg=COLORS['text_primary']).pack(side=tk.LEFT)
        ModernBtn(hdr, "🔄 全部刷新", self._refresh_webui_status,
                 bg=COLORS['accent_purple']).pack(side=tk.RIGHT)

        services = [
            ('comfyui', '🎨 ComfyUI (绘梦引擎)', 'http://127.0.0.1:8188'),
            ('napcat', '🐱 NapCat (QQ/微信底层)', 'http://127.0.0.1:6099/webui'),
            ('gcli2api', '🔌 gcli2api (API 网关)', 'http://127.0.0.1:7861/front/control_panel.html')
        ]

        for svc_key, title, url in services:
            self._build_webui_card(container, svc_key, title, url)

        self._refresh_webui_status()

    def _build_webui_card(self, parent, svc_key, title, url):
        card = CardFrame(parent)
        card.pack(fill=tk.X, padx=4, pady=(0, 12))
        
        # Header
        tk.Label(card, text=title, font=FONTS['h3'],
                bg=COLORS['bg_card'], fg=COLORS['text_primary']).pack(anchor=tk.W, pady=(0,8))
        
        # Status Row
        row = tk.Frame(card, bg=COLORS['bg_card'])
        row.pack(fill=tk.X, pady=(0, 12))
        dot = StatusDot(row, bg=COLORS['bg_card'])
        dot.pack(side=tk.LEFT, padx=(0,8))
        status_lbl = tk.Label(row, text="检查中...", font=FONTS['body_bold'],
                             bg=COLORS['bg_card'], fg=COLORS['text_secondary'])
        status_lbl.pack(side=tk.LEFT)
        info_lbl = tk.Label(row, text="PID: — | Uptime: —", font=FONTS['small'],
                           bg=COLORS['bg_card'], fg=COLORS['text_muted'])
        info_lbl.pack(side=tk.RIGHT)
        
        self.webui_widgets[svc_key] = {'dot': dot, 'status_lbl': status_lbl, 'info_lbl': info_lbl}

        # Actions
        btn_row = tk.Frame(card, bg=COLORS['bg_card'])
        btn_row.pack(anchor=tk.W)
        ModernBtn(btn_row, "▶ 启动", lambda k=svc_key: self.start_service(k),
                 bg=COLORS['accent_green']).pack(side=tk.LEFT, padx=(0,6))
        ModernBtn(btn_row, "⏹ 停止", lambda k=svc_key: self.stop_service(k),
                 bg=COLORS['accent_red']).pack(side=tk.LEFT, padx=(0,6))
        ModernBtn(btn_row, "↻ 重启", lambda k=svc_key: self.restart_service(k),
                 bg=COLORS['accent_yellow']).pack(side=tk.LEFT, padx=(0,6))
        ModernBtn(btn_row, "🌐 打开网页", lambda u=url: webbrowser.open(u),
                 bg=COLORS['accent_blue']).pack(side=tk.LEFT, padx=(0,6))
        ModernBtn(btn_row, "📋 查看日志", lambda k=svc_key: self.show_service_log(k),
                 bg=COLORS['bg_tertiary']).pack(side=tk.LEFT)

    def _refresh_webui_status(self):
        def check():
            status = self.api_call('/status') or {}
            for svc_key, widgets in self.webui_widgets.items():
                svc_data = status.get(svc_key, {})
                running = svc_data.get('status') == 'running'
                pid = svc_data.get('pid', '—')
                uptime = svc_data.get('uptime', 0)
                
                if uptime > 0:
                    h, rem = divmod(uptime, 3600)
                    m, s = divmod(rem, 60)
                    ustr = f"{h}h {m}m {s}s" if h else (f"{m}m {s}s" if m else f"{s}s")
                else:
                    ustr = "—"

                self.root.after(0, lambda w=widgets, r=running: w['dot'].set_status(r))
                self.root.after(0, lambda w=widgets, r=running: w['status_lbl'].config(
                    text="运行中" if r else "已停止",
                    fg=COLORS['accent_green'] if r else COLORS['accent_red']))
                self.root.after(0, lambda w=widgets, p=pid, u=ustr: w['info_lbl'].config(
                    text=f"PID: {p or '—'} | Uptime: {u}"))
        run_threaded(check)

    # ══════════════════════════════════════════════
    # PAGE: OpenClaw Config
    # ══════════════════════════════════════════════
    def _build_config_page(self, page):
        pad = tk.Frame(page, bg=COLORS['bg_primary'])
        pad.pack(fill=tk.BOTH, expand=True, padx=24, pady=16)

        hdr = tk.Frame(pad, bg=COLORS['bg_primary'])
        hdr.pack(fill=tk.X, pady=(0,12))
        tk.Label(hdr, text="⚙️ OpenClaw 配置编辑器", font=FONTS['h1'],
                bg=COLORS['bg_primary'], fg=COLORS['text_primary']).pack(side=tk.LEFT)

        btn_row = tk.Frame(hdr, bg=COLORS['bg_primary'])
        btn_row.pack(side=tk.RIGHT)
        ModernBtn(btn_row, "📂 重新加载", self._load_openclaw_config,
                 bg=COLORS['accent_blue']).pack(side=tk.LEFT, padx=(0,6))
        ModernBtn(btn_row, "💾 保存配置", self._save_openclaw_config,
                 bg=COLORS['accent_green']).pack(side=tk.LEFT)

        path_lbl = tk.Label(pad, text=f"配置文件: {OPENCLAW_CONFIG_PATH}",
                           font=FONTS['tiny'], bg=COLORS['bg_primary'], fg=COLORS['text_muted'])
        path_lbl.pack(anchor=tk.W, pady=(0,8))

        # Tabs
        tab_frame = tk.Frame(pad, bg=COLORS['bg_primary'])
        tab_frame.pack(fill=tk.X, pady=(0, 8))
        self.cfg_tabs = {}
        self.cfg_tab_btns = {}
        self.cfg_current_tab = None
        self.cfg_container = tk.Frame(pad, bg=COLORS['bg_primary'])
        self.cfg_container.pack(fill=tk.BOTH, expand=True)

        for key, label in [('models', '🤖 模型/提供者'), ('gateway', '🌐 网关设置'),
                           ('agents', '🎯 Agent 默认值'), ('channels', '📡 频道/插件'),
                           ('raw', '📝 原始JSON')]:
            btn = tk.Label(tab_frame, text=label, font=FONTS['small'],
                          bg=COLORS['bg_tertiary'], fg=COLORS['text_secondary'],
                          padx=14, pady=6, cursor='hand2')
            btn.pack(side=tk.LEFT, padx=(0, 4))
            btn.bind('<Button-1>', lambda e, k=key: self._switch_cfg_tab(k))
            self.cfg_tab_btns[key] = btn
            f = tk.Frame(self.cfg_container, bg=COLORS['bg_primary'])
            self.cfg_tabs[key] = f

        self.openclaw_data = {}
        self._load_openclaw_config()
        self._switch_cfg_tab('models')

    def _switch_cfg_tab(self, key):
        if self.cfg_current_tab == key: return
        if self.cfg_current_tab:
            self.cfg_tabs[self.cfg_current_tab].pack_forget()
            self.cfg_tab_btns[self.cfg_current_tab].config(
                bg=COLORS['bg_tertiary'], fg=COLORS['text_secondary'])
        self.cfg_current_tab = key
        self.cfg_tab_btns[key].config(bg=COLORS['accent_blue'], fg='#FFFFFF')
        f = self.cfg_tabs[key]
        # Always rebuild tab content to ensure fresh data (e.g., updated model list in agents tab)
        for w in f.winfo_children():
            w.destroy()
        builder = getattr(self, f'_build_cfg_{key}', None)
        if builder: builder(f)
        f.pack(fill=tk.BOTH, expand=True)

    def _load_openclaw_config(self):
        try:
            with open(OPENCLAW_CONFIG_PATH, 'r', encoding='utf-8') as f:
                self.openclaw_data = json.load(f)
            self.log("openclaw.json 已加载", "success")
            # Rebuild current tab
            if self.cfg_current_tab:
                f = self.cfg_tabs[self.cfg_current_tab]
                for w in f.winfo_children(): w.destroy()
                builder = getattr(self, f'_build_cfg_{self.cfg_current_tab}', None)
                if builder: builder(f)
        except FileNotFoundError:
            self.log("未找到 openclaw.json", "error")
            self.openclaw_data = {}
        except Exception as e:
            self.log(f"加载 openclaw.json 失败: {e}", "error")

    def _save_openclaw_config(self):
        # Force grab focus from any active Entry to immediately fire dangling <FocusOut> events
        self.root.focus_set()
        
        # If raw tab, parse from editor
        if self.cfg_current_tab == 'raw' and hasattr(self, 'raw_editor'):
            try:
                self.openclaw_data = json.loads(self.raw_editor.get('1.0', tk.END))
            except json.JSONDecodeError as e:
                messagebox.showerror("JSON 错误", f"JSON 格式无效:\n{e}")
                return
        
        # Validate config structure
        validation_errors = self._validate_config()
        if validation_errors:
            if not messagebox.askyesno("配置验证警告",
                    f"配置存在以下问题:\n\n" + "\n".join(validation_errors[:5]) +
                    f"\n\n共 {len(validation_errors)} 个警告\n是否仍要保存？"):
                return
        
        # Create versioned backup before saving
        backup_paths = []
        try:
            import shutil
            from datetime import datetime
            
            # Keep the last 5 backups with timestamps
            if OPENCLAW_CONFIG_PATH.exists():
                # Create timestamped backup
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                versioned_backup = OPENCLAW_CONFIG_PATH.with_suffix(f'.json.{timestamp}')
                shutil.copy2(OPENCLAW_CONFIG_PATH, versioned_backup)
                backup_paths.append(versioned_backup)
                
                # Also update the simple .bak
                simple_backup = OPENCLAW_CONFIG_PATH.with_suffix('.json.bak')
                shutil.copy2(OPENCLAW_CONFIG_PATH, simple_backup)
                
                # Clean up old backups (keep last 5)
                config_dir = OPENCLAW_CONFIG_PATH.parent
                backup_files = sorted(config_dir.glob('openclaw.json.????????_??????'))
                if len(backup_files) > 5:
                    for old_backup in backup_files[:-5]:
                        try:
                            old_backup.unlink()
                            self.log(f"已清理旧备份: {old_backup.name}", "info")
                        except:
                            pass
            
            # Write new config
            with open(OPENCLAW_CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.openclaw_data, f, indent=2, ensure_ascii=False)
            
            self.log("openclaw.json 已保存 (已备份旧版)", "success")
            messagebox.showinfo("成功", "配置已保存！\n旧配置已备份")
            
            # Refresh current tab to reflect any changes
            if self.cfg_current_tab:
                f = self.cfg_tabs[self.cfg_current_tab]
                for w in f.winfo_children():
                    w.destroy()
                builder = getattr(self, f'_build_cfg_{self.cfg_current_tab}', None)
                if builder: builder(f)
                
        except Exception as e:
            self.log(f"保存失败: {e}", "error")
            # Rollback from backup if available
            if backup_paths and backup_paths[0].exists():
                try:
                    import shutil
                    shutil.copy2(backup_paths[0], OPENCLAW_CONFIG_PATH)
                    self.log("已从备份回滚", "warn")
                    messagebox.showerror("错误", f"保存失败:\n{e}\n\n已从备份恢复配置。")
                except Exception as rollback_err:
                    self.log(f"回滚失败: {rollback_err}", "error")
                    messagebox.showerror("错误", f"保存失败:\n{e}\n\n回滚也失败，请手动恢复备份:\n{backup_paths[0]}")
            else:
                messagebox.showerror("错误", f"保存失败:\n{e}")

    def _validate_config(self):
        """Validate configuration structure and values. Returns list of error messages."""
        errors = []
        
        # Validate channels.napcat
        napcat = self.openclaw_data.get('channels', {}).get('napcat', {})
        if napcat.get('enabled'):
            url = napcat.get('url', '')
            if url and not url.startswith(('http://', 'https://')):
                errors.append("NapCat URL 需以 http:// 或 https:// 开头")
            
            delay = napcat.get('pseudoStreamingDelay', 800)
            if isinstance(delay, (int, float)):
                if delay < 0:
                    errors.append("伪流式延迟不能为负数")
                elif delay > 10000:
                    errors.append("伪流式延迟过大 (>10秒)，可能影响体验")
        
        # Validate gateway port
        gateway = self.openclaw_data.get('gateway', {})
        port = gateway.get('port')
        if port:
            if not isinstance(port, int) or port < 1 or port > 65535:
                errors.append(f"Gateway 端口无效: {port}")
        
        # Validate models
        providers = self.openclaw_data.get('models', {}).get('providers', {})
        for pname, pdata in providers.items():
            if not pdata.get('baseUrl'):
                errors.append(f"Provider '{pname}' 缺少 baseUrl")
            for mi, m in enumerate(pdata.get('models', [])):
                if not m.get('id'):
                    errors.append(f"Provider '{pname}' 的模型 #{mi+1} 缺少 ID")
        
        return errors

    def _rollback_config(self, backup_path):
        """Rollback configuration from a backup file."""
        try:
            import shutil
            shutil.copy2(backup_path, OPENCLAW_CONFIG_PATH)
            self._load_openclaw_config()
            self.log(f"已从备份恢复: {backup_path.name}", "success")
            return True
        except Exception as e:
            self.log(f"回滚失败: {e}", "error")
            return False

    def _build_cfg_models(self, frame):
        """Build models/providers tab - fully interactive"""
        providers = self.openclaw_data.get('models', {}).get('providers', {})

        # Toolbar
        toolbar = tk.Frame(frame, bg=COLORS['bg_primary'])
        toolbar.pack(fill=tk.X, padx=4, pady=(4, 8))
        ModernBtn(toolbar, "➕ 添加 Provider", self._add_provider,
                 bg=COLORS['accent_green']).pack(side=tk.LEFT, padx=(0, 6))

        if not providers:
            tk.Label(frame, text="未找到模型配置，请添加 Provider", font=FONTS['body'],
                    bg=COLORS['bg_primary'], fg=COLORS['text_muted']).pack(pady=20)
            return

        inner = self._make_scrollable_frame(frame)

        API_TYPES = ['openai-completions', 'openai-responses', 'anthropic-messages', 'google-generative-ai', 'github-copilot', 'bedrock-converse-stream', 'ollama']
        AUTH_TYPES = ['api-key', 'aws-sdk', 'oauth', 'token']

        for pname, pdata in providers.items():
            card = CardFrame(inner)
            card.pack(fill=tk.X, pady=4, padx=4)

            # Provider header with delete button
            hdr = tk.Frame(card, bg=COLORS['bg_card'])
            hdr.pack(fill=tk.X)
            tk.Label(hdr, text=f"📦 {pname}", font=FONTS['h3'],
                    bg=COLORS['bg_card'], fg=COLORS['accent_blue']).pack(side=tk.LEFT)
            ModernBtn(hdr, "🗑", lambda p=pname: self._delete_provider(p),
                     bg=COLORS['accent_red']).pack(side=tk.RIGHT)
            ModernBtn(hdr, "📡 获取模型列表", lambda p=pname: self._fetch_models(p),
                     bg=COLORS['accent_purple']).pack(side=tk.RIGHT, padx=(0, 4))

            fields = tk.Frame(card, bg=COLORS['bg_card'])
            fields.pack(fill=tk.X, pady=(4, 4))

            # BaseURL - editable
            self._make_entry_row(fields, "节点地址 (Base URL):", pdata.get('baseUrl', ''),
                                lambda v, p=pname: self._update_provider(p, 'baseUrl', v))

            # API Key - masked editable
            self._make_entry_row(fields, "准入密钥 (API Key):", pdata.get('apiKey', ''),
                                lambda v, p=pname: self._update_provider(p, 'apiKey', v), masked=True)

            # API Type - dropdown
            r_api = tk.Frame(fields, bg=COLORS['bg_card'])
            r_api.pack(fill=tk.X, pady=2)
            tk.Label(r_api, text="API 类型:", font=FONTS['small'], width=12, anchor=tk.W,
                    bg=COLORS['bg_card'], fg=COLORS['text_secondary']).pack(side=tk.LEFT)
            api_var = tk.StringVar(value=pdata.get('api', 'openai-completions'))
            api_combo = ttk.Combobox(r_api, textvariable=api_var, values=API_TYPES,
                                     font=FONTS['mono_small'], state='readonly', width=25)
            api_combo.pack(side=tk.LEFT, padx=4)
            api_combo.bind('<<ComboboxSelected>>',
                          lambda e, p=pname, v=api_var: self._update_provider(p, 'api', v.get()))

            # Auth type - dropdown (optional)
            if 'auth' in pdata:
                r_auth = tk.Frame(fields, bg=COLORS['bg_card'])
                r_auth.pack(fill=tk.X, pady=2)
                tk.Label(r_auth, text="认证方式:", font=FONTS['small'], width=12, anchor=tk.W,
                        bg=COLORS['bg_card'], fg=COLORS['text_secondary']).pack(side=tk.LEFT)
                auth_var = tk.StringVar(value=pdata.get('auth', 'api-key'))
                auth_combo = ttk.Combobox(r_auth, textvariable=auth_var, values=AUTH_TYPES,
                                          font=FONTS['mono_small'], state='readonly', width=25)
                auth_combo.pack(side=tk.LEFT, padx=4)
                auth_combo.bind('<<ComboboxSelected>>',
                               lambda e, p=pname, v=auth_var: self._update_provider(p, 'auth', v.get()))

            # Models list - editable
            models = pdata.get('models', [])
            models_hdr = tk.Frame(card, bg=COLORS['bg_card'])
            models_hdr.pack(fill=tk.X, pady=(8, 4))
            tk.Label(models_hdr, text=f"模型 ({len(models)}):", font=FONTS['body_bold'],
                    bg=COLORS['bg_card'], fg=COLORS['text_primary']).pack(side=tk.LEFT)
            ModernBtn(models_hdr, "➕ 添加模型",
                     lambda p=pname: self._add_model(p),
                     bg=COLORS['accent_green']).pack(side=tk.RIGHT)

            for mi, m in enumerate(models):
                mf = tk.Frame(card, bg=COLORS['bg_tertiary'], padx=8, pady=6,
                             highlightbackground=COLORS['border'], highlightthickness=1)
                mf.pack(fill=tk.X, pady=2, padx=4)

                # Model header row
                mhdr = tk.Frame(mf, bg=COLORS['bg_tertiary'])
                mhdr.pack(fill=tk.X)
                # Fast set primary model button
                def _set_active(p=pname, i=m.get('id', '')):
                    self._update_nested('agents.defaults.model', 'primary', f"{i}")
                    self._save_openclaw_config()
                    messagebox.showinfo("成功", f"Agent主模型已快速切换至:\n{i}")
                    
                # Pack RHS elements first so they reserve space
                ModernBtn(mhdr, "✖", lambda p=pname, i=mi: self._delete_model(p, i),
                         bg=COLORS['accent_red']).pack(side=tk.RIGHT)
                ModernBtn(mhdr, "✨ 设为主模型", _set_active,
                         bg=COLORS['border_active']).pack(side=tk.RIGHT, padx=8)

                # Pack LHS element last with expand and fill to take remaining space
                reasoning_icon = " 🧠" if m.get('reasoning') else ""
                tk.Label(mhdr, text=f"{m.get('name', '?')}{reasoning_icon}",
                        font=FONTS['mono_small'], bg=COLORS['bg_tertiary'],
                        fg=COLORS['text_primary'], anchor=tk.W).pack(side=tk.LEFT, fill=tk.X, expand=True)

                # Editable fields
                detail = tk.Frame(mf, bg=COLORS['bg_tertiary'])
                detail.pack(fill=tk.X, pady=(4, 0))

                self._make_model_field(detail, "内部标识(ID):", m.get('id', ''), 14,
                                      lambda v, p=pname, i=mi: self._update_model(p, i, 'id', v))
                self._make_model_field(detail, "展示名称:", m.get('name', ''), 30,
                                      lambda v, p=pname, i=mi: self._update_model(p, i, 'name', v))

                # Reasoning toggle + context + maxTokens on one row
                opts = tk.Frame(detail, bg=COLORS['bg_tertiary'])
                opts.pack(fill=tk.X, pady=2)

                # Reasoning checkbox
                reasoning_var = tk.BooleanVar(value=m.get('reasoning', False))
                cb = tk.Checkbutton(opts, text="🧠 深度思考(Reasoning)", variable=reasoning_var,
                                   bg=COLORS['bg_tertiary'], fg=COLORS['text_primary'],
                                   selectcolor=COLORS['bg_primary'], font=FONTS['small'],
                                   activebackground=COLORS['bg_tertiary'],
                                   command=lambda p=pname, i=mi, v=reasoning_var:
                                       self._update_model(p, i, 'reasoning', v.get()))
                cb.pack(side=tk.LEFT, padx=(0, 12))

                # Context Window
                tk.Label(opts, text="上下文长度:", font=FONTS['small'],
                        bg=COLORS['bg_tertiary'], fg=COLORS['text_secondary']).pack(side=tk.LEFT)
                ctx_var = tk.StringVar(value=str(m.get('contextWindow', 200000)))
                ctx_e = tk.Entry(opts, textvariable=ctx_var, font=FONTS['mono_small'], width=10,
                                bg=COLORS['bg_input'], fg=COLORS['text_primary'],
                                insertbackground=COLORS['text_primary'], relief=tk.FLAT)
                ctx_e.pack(side=tk.LEFT, padx=4)
                ctx_e.bind('<FocusOut>', lambda ev, p=pname, i=mi, v=ctx_var:
                          self._update_model(p, i, 'contextWindow', int(v.get()) if v.get().isdigit() else 200000))

                # Max Tokens
                tk.Label(opts, text="回复Token限制:", font=FONTS['small'],
                        bg=COLORS['bg_tertiary'], fg=COLORS['text_secondary']).pack(side=tk.LEFT, padx=(8, 0))
                mt_var = tk.StringVar(value=str(m.get('maxTokens', 8192)))
                mt_e = tk.Entry(opts, textvariable=mt_var, font=FONTS['mono_small'], width=8,
                               bg=COLORS['bg_input'], fg=COLORS['text_primary'],
                               insertbackground=COLORS['text_primary'], relief=tk.FLAT)
                mt_e.pack(side=tk.LEFT, padx=4)
                mt_e.bind('<FocusOut>', lambda ev, p=pname, i=mi, v=mt_var:
                          self._update_model(p, i, 'maxTokens', int(v.get()) if v.get().isdigit() else 8192))

                # Input types
                input_types = m.get('input', ['text'])
                inp_frame = tk.Frame(detail, bg=COLORS['bg_tertiary'])
                inp_frame.pack(fill=tk.X, pady=2)
                tk.Label(inp_frame, text="支持模态:", font=FONTS['small'],
                        bg=COLORS['bg_tertiary'], fg=COLORS['text_secondary']).pack(side=tk.LEFT)
                for itype in ['text', 'image']:
                    displays = {'text': '文本', 'image': '图像'}
                    iv = tk.BooleanVar(value=itype in input_types)
                    tcb = tk.Checkbutton(inp_frame, text=displays[itype], variable=iv,
                                        bg=COLORS['bg_tertiary'], fg=COLORS['text_primary'],
                                        selectcolor=COLORS['bg_primary'], font=FONTS['tiny'],
                                        activebackground=COLORS['bg_tertiary'],
                                        command=lambda p=pname, i=mi, t=itype, vv=iv:
                                            self._toggle_model_input(p, i, t, vv.get()))
                    tcb.pack(side=tk.LEFT, padx=2)

                # Cost configuration (expandable)
                cost_data = m.get('cost', {})
                cost_frame = tk.Frame(detail, bg=COLORS['bg_tertiary'])
                cost_frame.pack(fill=tk.X, pady=2)
                tk.Label(cost_frame, text="成本设置:", font=FONTS['small'],
                        bg=COLORS['bg_tertiary'], fg=COLORS['text_secondary']).pack(side=tk.LEFT)
                
                # Input cost
                tk.Label(cost_frame, text="输入:", font=FONTS['tiny'],
                        bg=COLORS['bg_tertiary'], fg=COLORS['text_muted']).pack(side=tk.LEFT, padx=(4, 0))
                cost_input_var = tk.StringVar(value=str(cost_data.get('input', 0)))
                cost_input_e = tk.Entry(cost_frame, textvariable=cost_input_var, font=FONTS['tiny'], width=6,
                                bg=COLORS['bg_input'], fg=COLORS['text_primary'],
                                insertbackground=COLORS['text_primary'], relief=tk.FLAT)
                cost_input_e.pack(side=tk.LEFT, padx=2)
                cost_input_e.bind('<FocusOut>', lambda ev, p=pname, i=mi, v=cost_input_var:
                    self._update_model_cost(p, i, 'input', float(v.get()) if v.get() else 0))

                # Output cost
                tk.Label(cost_frame, text="输出:", font=FONTS['tiny'],
                        bg=COLORS['bg_tertiary'], fg=COLORS['text_muted']).pack(side=tk.LEFT, padx=(4, 0))
                cost_output_var = tk.StringVar(value=str(cost_data.get('output', 0)))
                cost_output_e = tk.Entry(cost_frame, textvariable=cost_output_var, font=FONTS['tiny'], width=6,
                                bg=COLORS['bg_input'], fg=COLORS['text_primary'],
                                insertbackground=COLORS['text_primary'], relief=tk.FLAT)
                cost_output_e.pack(side=tk.LEFT, padx=2)
                cost_output_e.bind('<FocusOut>', lambda ev, p=pname, i=mi, v=cost_output_var:
                    self._update_model_cost(p, i, 'output', float(v.get()) if v.get() else 0))

                # Cache Read cost
                tk.Label(cost_frame, text="缓存读:", font=FONTS['tiny'],
                        bg=COLORS['bg_tertiary'], fg=COLORS['text_muted']).pack(side=tk.LEFT, padx=(4, 0))
                cost_cr_var = tk.StringVar(value=str(cost_data.get('cacheRead', 0)))
                cost_cr_e = tk.Entry(cost_frame, textvariable=cost_cr_var, font=FONTS['tiny'], width=6,
                                bg=COLORS['bg_input'], fg=COLORS['text_primary'],
                                insertbackground=COLORS['text_primary'], relief=tk.FLAT)
                cost_cr_e.pack(side=tk.LEFT, padx=2)
                cost_cr_e.bind('<FocusOut>', lambda ev, p=pname, i=mi, v=cost_cr_var:
                    self._update_model_cost(p, i, 'cacheRead', float(v.get()) if v.get() else 0))

                # Cache Write cost
                tk.Label(cost_frame, text="缓存写:", font=FONTS['tiny'],
                        bg=COLORS['bg_tertiary'], fg=COLORS['text_muted']).pack(side=tk.LEFT, padx=(4, 0))
                cost_cw_var = tk.StringVar(value=str(cost_data.get('cacheWrite', 0)))
                cost_cw_e = tk.Entry(cost_frame, textvariable=cost_cw_var, font=FONTS['tiny'], width=6,
                                bg=COLORS['bg_input'], fg=COLORS['text_primary'],
                                insertbackground=COLORS['text_primary'], relief=tk.FLAT)
                cost_cw_e.pack(side=tk.LEFT, padx=2)
                cost_cw_e.bind('<FocusOut>', lambda ev, p=pname, i=mi, v=cost_cw_var:
                    self._update_model_cost(p, i, 'cacheWrite', float(v.get()) if v.get() else 0))

    # ── Helper: entry row ──
    def _make_entry_row(self, parent, label, value, on_change, masked=False):
        r = tk.Frame(parent, bg=COLORS['bg_card'])
        r.pack(fill=tk.X, pady=2)
        tk.Label(r, text=label, font=FONTS['small'], width=12, anchor=tk.W,
                bg=COLORS['bg_card'], fg=COLORS['text_secondary']).pack(side=tk.LEFT)
        var = tk.StringVar(value=value)
        e = tk.Entry(r, textvariable=var, font=FONTS['mono_small'],
                    bg=COLORS['bg_input'], fg=COLORS['text_primary'],
                    insertbackground=COLORS['text_primary'], relief=tk.FLAT,
                    show='•' if masked else '')
        e.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        e.bind('<FocusOut>', lambda ev: on_change(var.get()))
        e.bind('<KeyRelease>', lambda ev: on_change(e.get()))
        if masked:
            def toggle(entry=e):
                entry.config(show='' if entry.cget('show') == '•' else '•')
            ModernBtn(r, "👁", toggle, bg=COLORS['bg_tertiary']).pack(side=tk.LEFT)
        return var

    def _make_model_field(self, parent, label, value, width, on_change):
        r = tk.Frame(parent, bg=COLORS['bg_tertiary'])
        r.pack(fill=tk.X, pady=1)
        tk.Label(r, text=label, font=FONTS['tiny'], width=6, anchor=tk.W,
                bg=COLORS['bg_tertiary'], fg=COLORS['text_secondary']).pack(side=tk.LEFT)
        var = tk.StringVar(value=value)
        e = tk.Entry(r, textvariable=var, font=FONTS['mono_small'], width=width,
                    bg=COLORS['bg_input'], fg=COLORS['text_primary'],
                    insertbackground=COLORS['text_primary'], relief=tk.FLAT)
        e.pack(side=tk.LEFT, padx=2)
        e.bind('<FocusOut>', lambda ev: on_change(var.get()))
        e.bind('<KeyRelease>', lambda ev: on_change(e.get()))

    # ── Provider/Model CRUD ──
    def _update_provider(self, provider, key, value):
        self.openclaw_data.setdefault('models', {}).setdefault('providers', {}).setdefault(provider, {})[key] = value

    def _add_provider(self):
        name = simpledialog.askstring("添加 Provider", "Provider 名称:", parent=self.root)
        if not name: return
        self.openclaw_data.setdefault('models', {}).setdefault('providers', {})[name] = {
            'baseUrl': '', 'apiKey': '', 'api': 'openai-completions', 'models': []
        }
        self._reload_cfg_tab('models')

    def _delete_provider(self, name):
        if messagebox.askyesno("确认", f"删除 Provider '{name}'？"):
            self.openclaw_data.get('models', {}).get('providers', {}).pop(name, None)
            self._reload_cfg_tab('models')

    def _add_model(self, provider):
        models = self.openclaw_data['models']['providers'][provider].setdefault('models', [])
        models.append({
            'id': 'new-model', 'name': 'provider/model-name', 'reasoning': False,
            'input': ['text', 'image'], 'cost': {'input': 0, 'output': 0, 'cacheRead': 0, 'cacheWrite': 0},
            'contextWindow': 200000, 'maxTokens': 8192
        })
        self._reload_cfg_tab('models')

    def _delete_model(self, provider, index):
        models = self.openclaw_data['models']['providers'][provider].get('models', [])
        if 0 <= index < len(models):
            models.pop(index)
            self._reload_cfg_tab('models')

    def _update_model(self, provider, index, key, value):
        models = self.openclaw_data['models']['providers'][provider].get('models', [])
        if 0 <= index < len(models):
            models[index][key] = value

    def _toggle_model_input(self, provider, index, input_type, enabled):
        models = self.openclaw_data['models']['providers'][provider].get('models', [])
        if 0 <= index < len(models):
            inputs = models[index].setdefault('input', [])
            if enabled and input_type not in inputs:
                inputs.append(input_type)
            elif not enabled and input_type in inputs:
                inputs.remove(input_type)

    def _update_model_cost(self, provider, index, cost_key, value):
        """Update a specific cost field for a model"""
        models = self.openclaw_data['models']['providers'][provider].get('models', [])
        if 0 <= index < len(models):
            cost = models[index].setdefault('cost', {'input': 0, 'output': 0, 'cacheRead': 0, 'cacheWrite': 0})
            cost[cost_key] = value

    def _fetch_models(self, provider):
        """Fetch available models from provider's baseUrl/models endpoint"""
        pdata = self.openclaw_data.get('models', {}).get('providers', {}).get(provider, {})
        base_url = pdata.get('baseUrl', '').rstrip('/')
        api_key = pdata.get('apiKey', '')
        if not base_url:
            messagebox.showwarning("警告", "请先填写 Base URL")
            return
        self.log(f"正在从 {base_url}/models 获取模型列表...", "info")
        def fetch():
            try:
                headers = {}
                if api_key:
                    headers['Authorization'] = f'Bearer {api_key}'
                    headers['x-goog-api-key'] = api_key
                r = requests.get(f"{base_url}/models", headers=headers, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    # OpenAI format
                    model_list = data.get('data', data.get('models', []))
                    if isinstance(model_list, list):
                        names = []
                        for m in model_list:
                            if isinstance(m, dict):
                                names.append(m.get('id', m.get('name', str(m))))
                            else:
                                names.append(str(m))
                        self.root.after(0, lambda n=names: self._show_fetched_models(provider, n))
                    else:
                        self.root.after(0, lambda: self.log("返回格式无法解析", "error"))
                else:
                    self.root.after(0, lambda: self.log(f"获取失败: HTTP {r.status_code}", "error"))
            except Exception as e:
                self.root.after(0, lambda: self.log(f"获取失败: {e}", "error"))
        run_threaded(fetch)

    def _show_fetched_models(self, provider, model_names):
        if not model_names:
            self.log("未获取到模型", "warn")
            return
        self.log(f"获取到 {len(model_names)} 个模型", "success")
        win = tk.Toplevel(self.root)
        win.title(f"选择模型 - {provider}")
        win.geometry("600x500")
        win.configure(bg=COLORS['bg_primary'])
        tk.Label(win, text=f"从 {provider} 获取到 {len(model_names)} 个模型",
                font=FONTS['h3'], bg=COLORS['bg_primary'], fg=COLORS['text_primary']).pack(pady=8)
        tk.Label(win, text="勾选要添加的模型，然后点击确认", font=FONTS['small'],
                bg=COLORS['bg_primary'], fg=COLORS['text_secondary']).pack()

        list_frame = tk.Frame(win, bg=COLORS['bg_primary'])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        canvas = tk.Canvas(list_frame, bg=COLORS['bg_primary'], highlightthickness=0)
        sb = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=COLORS['bg_primary'])
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        check_vars = {}
        for name in model_names:
            var = tk.BooleanVar(value=False)
            cb = tk.Checkbutton(inner, text=name, variable=var,
                               bg=COLORS['bg_primary'], fg=COLORS['text_primary'],
                               selectcolor=COLORS['bg_secondary'], font=FONTS['mono_small'],
                               activebackground=COLORS['bg_primary'], anchor=tk.W)
            cb.pack(fill=tk.X, padx=4, pady=1)
            check_vars[name] = var

        def add_selected():
            selected = [n for n, v in check_vars.items() if v.get()]
            if not selected: return
            models = self.openclaw_data['models']['providers'][provider].setdefault('models', [])
            existing_ids = {m.get('id') for m in models}
            added = 0
            for name in selected:
                short_id = name.split('/')[-1] if '/' in name else name
                if short_id not in existing_ids:
                    models.append({
                        'id': short_id, 'name': name, 'reasoning': False,
                        'input': ['text', 'image'],
                        'cost': {'input': 0, 'output': 0, 'cacheRead': 0, 'cacheWrite': 0},
                        'contextWindow': 200000, 'maxTokens': 8192
                    })
                    added += 1
            win.destroy()
            self.log(f"已添加 {added} 个模型到 {provider}", "success")
            self._reload_cfg_tab('models')

        ModernBtn(win, f"✓ 确认添加选中模型", add_selected,
                 bg=COLORS['accent_green']).pack(pady=8)

    def _reload_cfg_tab(self, tab_key):
        f = self.cfg_tabs[tab_key]
        for w in f.winfo_children(): w.destroy()
        builder = getattr(self, f'_build_cfg_{tab_key}', None)
        if builder: builder(f)

    def _make_scrollable_frame(self, parent):
        """Create a canvas-based scrollable container for long form pages with smooth scrolling"""
        canvas = tk.Canvas(parent, bg=COLORS['bg_primary'], highlightthickness=0, bd=0)
        sb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=COLORS['bg_primary'])

        # Update scrollregion when inner frame resizes
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=inner, anchor="nw")

        # Make inner frame match canvas width
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))

        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        def _on_mousewheel(event):
            """Handle mousewheel scrolling for Windows/macOS"""
            try:
                if event.delta:
                    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except: pass

        def _on_linux_scroll(event):
            """Handle Linux button-4/button-5 scrolling"""
            try:
                canvas.yview_scroll(-1 if event.num == 4 else 1, "units")
            except: pass

        # Recursively bind scroll events to all widgets in the hierarchy
        def _bind_to_all(widget):
            widget.bind("<MouseWheel>", _on_mousewheel, add='+')
            widget.bind("<Button-4>", _on_linux_scroll, add='+')
            widget.bind("<Button-5>", _on_linux_scroll, add='+')
            for child in widget.winfo_children():
                _bind_to_all(child)

        # Bind after a short delay to ensure all children are created
        def _delayed_bind():
            _bind_to_all(canvas)
            _bind_to_all(inner)
            _bind_to_all(parent)
        
        # Also use bind_all when mouse enters any part of the scrollable area
        def _on_enter(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel, add='+')
            canvas.bind_all("<Button-4>", _on_linux_scroll, add='+')
            canvas.bind_all("<Button-5>", _on_linux_scroll, add='+')

        def _on_leave(event):
            try:
                canvas.unbind_all("<MouseWheel>")
            except: pass
            try:
                canvas.unbind_all("<Button-4>")
            except: pass
            try:
                canvas.unbind_all("<Button-5>")
            except: pass

        # Bind to canvas and parent
        canvas.bind("<Enter>", _on_enter)
        canvas.bind("<Leave>", _on_leave)
        parent.bind("<Enter>", _on_enter)
        parent.bind("<Leave>", _on_leave)

        # Schedule delayed binding after widgets are created
        parent.after(100, _delayed_bind)

        return inner

    def _build_cfg_gateway(self, frame):
        """Build gateway settings tab - with dropdowns"""
        frame = self._make_scrollable_frame(frame)
        gw = self.openclaw_data.get('gateway', {})

        # Main settings card
        card = CardFrame(frame)
        card.pack(fill=tk.X, pady=4, padx=4)
        tk.Label(card, text="网关核心设置", font=FONTS['h3'],
                bg=COLORS['bg_card'], fg=COLORS['text_primary']).pack(anchor=tk.W, pady=(0,8))

        # Port - entry
        self._make_cfg_entry(card, "端口 (port)", str(gw.get('port', 18789)),
                            lambda v: self._update_nested('gateway', 'port', int(v) if v.isdigit() else 18789))
        self._make_cfg_combo(card, "运行模式 (mode)", gw.get('mode', 'local'),
                           ['local', 'remote'],
                           lambda v: self._update_nested('gateway', 'mode', v),
                           display_options=['仅本地 (local)', '公开访问 (remote)'])
        self._make_cfg_combo(card, "监听绑定 (bind)", gw.get('bind', 'loopback'),
                           ['loopback', 'custom', 'lan', 'tailnet', 'auto'],
                           lambda v: self._update_nested('gateway', 'bind', v),
                           display_options=['仅内环回环 (loopback)', '全网段暴露自定义 (custom)', '局域网限定 (lan)', 'Tailscale网络 (tailnet)', '自动 (auto)'])
        # customBindHost - only needed when bind is 'custom'
        self._make_cfg_entry(card, "自定义绑定地址 (customBindHost)", gw.get('customBindHost', '127.0.0.1'),
                            lambda v: self._update_nested('gateway', 'customBindHost', v))

        # Auth card
        auth_card = CardFrame(frame)
        auth_card.pack(fill=tk.X, pady=4, padx=4)
        tk.Label(auth_card, text="认证设置", font=FONTS['h3'],
                bg=COLORS['bg_card'], fg=COLORS['text_primary']).pack(anchor=tk.W, pady=(0,8))
        auth = gw.get('auth', {})
        self._make_cfg_combo(auth_card, "接口认证核验", auth.get('mode', 'token'),
                           ['token', 'password'],
                           lambda v: self._update_nested('gateway.auth', 'mode', v),
                           display_options=['固定密钥验证 (token)', '账号密码验证 (password)'])
        self._make_cfg_entry(auth_card, "Token", auth.get('token', ''),
                            lambda v: self._update_nested('gateway.auth', 'token', v), masked=True)

        # Reload card
        reload_card = CardFrame(frame)
        reload_card.pack(fill=tk.X, pady=4, padx=4)
        tk.Label(reload_card, text="热重载设置", font=FONTS['h3'],
                bg=COLORS['bg_card'], fg=COLORS['text_primary']).pack(anchor=tk.W, pady=(0,8))
        reload = gw.get('reload', {})
        self._make_cfg_combo(reload_card, "重载接管模式", reload.get('mode', 'hybrid'),
                           ['hybrid', 'restart', 'off'],
                           lambda v: self._update_nested('gateway.reload', 'mode', v),
                           display_options=['动态无缝重载 (hybrid)', '强制深度重启 (restart)', '关闭重载反馈 (off)'])
        self._make_cfg_entry(reload_card, "防抖延迟(ms)", str(reload.get('debounceMs', 5000)),
                            lambda v: self._update_nested('gateway.reload', 'debounceMs', int(v) if v.isdigit() else 5000))

        # HTTP endpoints card
        http_card = CardFrame(frame)
        http_card.pack(fill=tk.X, pady=4, padx=4)
        tk.Label(http_card, text="HTTP API 对外挂载点", font=FONTS['h3'],
                bg=COLORS['bg_card'], fg=COLORS['text_primary']).pack(anchor=tk.W, pady=(0,8))
        endpoints = gw.get('http', {}).get('endpoints', {})
        cc = endpoints.get('chatCompletions', {})
        cc_var = tk.BooleanVar(value=cc.get('enabled', True))
        tk.Checkbutton(http_card, text="暴露 OpenAI 兼容 API接口", variable=cc_var,
                      bg=COLORS['bg_card'], fg=COLORS['text_primary'],
                      selectcolor=COLORS['bg_primary'], font=FONTS['body'],
                      activebackground=COLORS['bg_card'],
                      command=lambda: self._update_nested('gateway.http.endpoints.chatCompletions', 'enabled', cc_var.get())
                      ).pack(anchor=tk.W)

        # Tailscale card
        ts = gw.get('tailscale', {})
        ts_card = CardFrame(frame)
        ts_card.pack(fill=tk.X, pady=4, padx=4)
        tk.Label(ts_card, text="虚拟局域网穿透 (Tailscale)", font=FONTS['h3'],
                bg=COLORS['bg_card'], fg=COLORS['text_primary']).pack(anchor=tk.W, pady=(0,8))
        self._make_cfg_combo(ts_card, "节点接驳穿透", ts.get('mode', 'off'),
                           ['off', 'funnel', 'serve'],
                           lambda v: self._update_nested('gateway.tailscale', 'mode', v),
                           display_options=['关闭穿透 (off)', '公网漏斗曝光 (funnel)', 'VPC局域私服 (serve)'])
        ts_reset = tk.BooleanVar(value=ts.get('resetOnExit', True))
        tk.Checkbutton(ts_card, text="退出时重置 (resetOnExit)", variable=ts_reset,
                      bg=COLORS['bg_card'], fg=COLORS['text_primary'],
                      selectcolor=COLORS['bg_primary'], font=FONTS['body'],
                      activebackground=COLORS['bg_card'],
                      command=lambda: self._update_nested('gateway.tailscale', 'resetOnExit', ts_reset.get())
                      ).pack(anchor=tk.W)

    # ── Config field helpers with validation ──
    def _make_cfg_entry(self, parent, label, value, on_change, masked=False, tooltip=None, validator=None):
        """Create a config entry with optional validation.
        
        Args:
            parent: Parent widget
            label: Label text
            value: Initial value
            on_change: Callback when value changes
            masked: Show as password field
            tooltip: Tooltip text
            validator: Optional validation function (value) -> (valid, error_msg)
        """
        r = tk.Frame(parent, bg=COLORS['bg_card'])
        r.pack(fill=tk.X, pady=3)
        lbl_widget = tk.Label(r, text=label, font=FONTS['small'], width=16, anchor=tk.W,
                bg=COLORS['bg_card'], fg=COLORS['text_secondary'])
        lbl_widget.pack(side=tk.LEFT)
        var = tk.StringVar(value=value)
        
        # Error label for validation feedback
        err_label = tk.Label(r, text="", font=FONTS['tiny'],
                            bg=COLORS['bg_card'], fg=COLORS['accent_red'])
        err_label.pack(side=tk.RIGHT, padx=4)
        
        e = tk.Entry(r, textvariable=var, font=FONTS['mono_small'],
                    bg=COLORS['bg_input'], fg=COLORS['text_primary'],
                    insertbackground=COLORS['text_primary'], relief=tk.FLAT,
                    highlightthickness=1, highlightbackground=COLORS['border'],
                    highlightcolor=COLORS['accent_blue'],
                    show='•' if masked else '')
        e.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        
        def validate_and_change(val):
            if validator:
                is_valid, err_msg = validator(val)
                if is_valid:
                    e.config(highlightbackground=COLORS['accent_green'])
                    err_label.config(text="")
                else:
                    e.config(highlightbackground=COLORS['accent_red'])
                    err_label.config(text=err_msg or "✗")
                if is_valid:
                    on_change(val)
            else:
                on_change(val)
        
        e.bind('<FocusOut>', lambda ev: validate_and_change(var.get()))
        e.bind('<KeyRelease>', lambda ev: validate_and_change(e.get()))
        # Focus visual feedback
        def on_focus_in(ev, entry=e):
            if not validator:  # Only change color if no validator
                entry.config(highlightbackground=COLORS['accent_blue'])
        def on_focus_out(ev, entry=e):
            if not validator:
                entry.config(highlightbackground=COLORS['border'])
        e.bind('<FocusIn>', on_focus_in)
        e.bind('<FocusOut>', on_focus_out)
        if tooltip:
            ToolTip(lbl_widget, tooltip)
        if masked:
            def toggle(entry=e):
                entry.config(show='' if entry.cget('show') == '•' else '•')
            ModernBtn(r, "👁", toggle, bg=COLORS['bg_tertiary']).pack(side=tk.LEFT)
        return var, e

    def _validate_url(self, value):
        """Validate URL format."""
        if not value:
            return True, ""
        if value.startswith(('http://', 'https://')):
            return True, ""
        return False, "需以 http:// 或 https:// 开头"

    def _validate_port(self, value):
        """Validate port number."""
        if not value:
            return True, ""
        try:
            port = int(value)
            if 1 <= port <= 65535:
                return True, ""
            return False, "端口范围: 1-65535"
        except ValueError:
            return False, "需为数字"

    def _validate_number(self, value):
        """Validate numeric value."""
        if not value:
            return True, ""
        try:
            int(value)
            return True, ""
        except ValueError:
            return False, "需为整数"

    def _make_cfg_combo(self, parent, label, value, options, on_change, display_options=None):
        r = tk.Frame(parent, bg=COLORS['bg_card'])
        r.pack(fill=tk.X, pady=3)
        tk.Label(r, text=label, font=FONTS['small'], width=16, anchor=tk.W,
                bg=COLORS['bg_card'], fg=COLORS['text_secondary']).pack(side=tk.LEFT)
        
        if display_options and len(display_options) == len(options):
            rev_map = dict(zip(options, display_options))
            fwd_map = dict(zip(display_options, options))
            ui_val = rev_map.get(value, value)
            var = tk.StringVar(value=ui_val)
            combo = ttk.Combobox(r, textvariable=var, values=display_options,
                                font=FONTS['mono_small'], state='readonly', width=20)
            combo.pack(side=tk.LEFT, padx=4)
            combo.bind('<<ComboboxSelected>>', lambda e: on_change(fwd_map.get(var.get(), var.get())))
        else:
            var = tk.StringVar(value=value)
            combo = ttk.Combobox(r, textvariable=var, values=options,
                                font=FONTS['mono_small'], state='readonly', width=20)
            combo.pack(side=tk.LEFT, padx=4)
            combo.bind('<<ComboboxSelected>>', lambda e: on_change(var.get()))

    def _make_cfg_checkbox(self, parent, label, value, on_change, tooltip=None):
        """Create a styled checkbox with optional tooltip"""
        var = tk.BooleanVar(value=value)
        cb = tk.Checkbutton(parent, text=label, variable=var,
                           bg=COLORS['bg_card'], fg=COLORS['text_primary'],
                           selectcolor=COLORS['bg_primary'], font=FONTS['body'],
                           activebackground=COLORS['bg_card'],
                           activeforeground=COLORS['accent_blue'],
                           highlightthickness=0,
                           command=lambda: on_change(var.get()))
        cb.pack(anchor=tk.W, pady=1)
        if tooltip:
            ToolTip(cb, tooltip)
        return var, cb

    def _update_nested(self, path, key, value):
        """Update a nested config value using dot-separated path"""
        parts = path.split('.')
        obj = self.openclaw_data
        for p in parts:
            obj = obj.setdefault(p, {})
        obj[key] = value

    def _update_plugins_allow(self, value_str):
        """Update plugins.allow from comma-separated string"""
        # Parse comma-separated string into list
        items = [item.strip() for item in value_str.split(',') if item.strip()]
        self.openclaw_data.setdefault('plugins', {})['allow'] = items

    def _update_nested_list(self, path, key, value_str):
        """Update a nested config list value using dot-separated path"""
        parts = path.split('.')
        obj = self.openclaw_data
        for p in parts:
            obj = obj.setdefault(p, {})
        # Parse comma-separated string into list
        items = [item.strip() for item in value_str.split(',') if item.strip()]
        obj[key] = items

    def _build_cfg_agents(self, frame):
        """Build agents defaults tab - fully editable"""
        frame = self._make_scrollable_frame(frame)
        agents = self.openclaw_data.get('agents', {}).get('defaults', {})

        # Build model choices from configured providers
        model_choices = []
        for pname, pdata in self.openclaw_data.get('models', {}).get('providers', {}).items():
            for m in pdata.get('models', []):
                model_choices.append(f"{pname}/{m.get('id', '')}")

        # Core settings card
        card = CardFrame(frame)
        card.pack(fill=tk.X, pady=4, padx=4)
        tk.Label(card, text="模型选择", font=FONTS['h3'],
                bg=COLORS['bg_card'], fg=COLORS['text_primary']).pack(anchor=tk.W, pady=(0,8))

        # Primary model - combo if choices available, else entry
        primary = agents.get('model', {}).get('primary', '')
        if model_choices:
            r = tk.Frame(card, bg=COLORS['bg_card'])
            r.pack(fill=tk.X, pady=3)
            tk.Label(r, text="主模型", font=FONTS['small'], width=14, anchor=tk.W,
                    bg=COLORS['bg_card'], fg=COLORS['text_secondary']).pack(side=tk.LEFT)
            pv = tk.StringVar(value=primary)
            combo = ttk.Combobox(r, textvariable=pv, values=model_choices + [primary],
                                font=FONTS['mono_small'], width=45)
            combo.pack(side=tk.LEFT, padx=4)
            combo.bind('<<ComboboxSelected>>',
                      lambda e: self._update_nested('agents.defaults.model', 'primary', pv.get()))
            combo.bind('<FocusOut>',
                      lambda e: self._update_nested('agents.defaults.model', 'primary', pv.get()))
        else:
            self._make_cfg_entry(card, "主模型", primary,
                               lambda v: self._update_nested('agents.defaults.model', 'primary', v))

        # Image model
        img_primary = agents.get('imageModel', {}).get('primary', '')
        self._make_cfg_entry(card, "图像模型", img_primary,
                            lambda v: self._update_nested('agents.defaults.imageModel', 'primary', v))

        # Workspace & performance card
        perf_card = CardFrame(frame)
        perf_card.pack(fill=tk.X, pady=4, padx=4)
        tk.Label(perf_card, text="性能与工作流路径", font=FONTS['h3'],
                bg=COLORS['bg_card'], fg=COLORS['text_primary']).pack(anchor=tk.W, pady=(0,8))

        self._make_cfg_entry(perf_card, "工作区目录", agents.get('workspace', ''),
                            lambda v: self._update_nested('agents.defaults', 'workspace', v))
        self._make_cfg_entry(perf_card, "挂起超时(秒)", str(agents.get('timeoutSeconds', 300)),
                            lambda v: self._update_nested('agents.defaults', 'timeoutSeconds', int(v) if v.isdigit() else 300))
        self._make_cfg_entry(perf_card, "最大并发", str(agents.get('maxConcurrent', 12)),
                            lambda v: self._update_nested('agents.defaults', 'maxConcurrent', int(v) if v.isdigit() else 12))
        self._make_cfg_entry(perf_card, "子Agent并发", str(agents.get('subagents', {}).get('maxConcurrent', 12)),
                            lambda v: self._update_nested('agents.defaults.subagents', 'maxConcurrent', int(v) if v.isdigit() else 12))

        # Compaction card
        comp = agents.get('compaction', {})
        comp_card = CardFrame(frame)
        comp_card.pack(fill=tk.X, pady=4, padx=4)
        tk.Label(comp_card, text="记忆压缩与折叠 (Compaction)", font=FONTS['h3'],
                bg=COLORS['bg_card'], fg=COLORS['text_primary']).pack(anchor=tk.W, pady=(0,8))
        self._make_cfg_combo(comp_card, "压缩强度模式", comp.get('mode', 'default'),
                           ['default', 'safeguard'],
                           lambda v: self._update_nested('agents.defaults.compaction', 'mode', v),
                           display_options=['标准推荐 (default)', '稳妥保守 (safeguard)'])
        self._make_cfg_entry(comp_card, "短期记忆保留底线", str(comp.get('reserveTokensFloor', 2000)),
                            lambda v: self._update_nested('agents.defaults.compaction', 'reserveTokensFloor', int(v) if v.isdigit() else 2000))

        # Context pruning
        prune = agents.get('contextPruning', {}).get('hardClear', {})
        prune_var = tk.BooleanVar(value=prune.get('enabled', True))
        tk.Checkbutton(comp_card, text="允许灾难性遗忘清理 (hardClear)", variable=prune_var,
                      bg=COLORS['bg_card'], fg=COLORS['text_primary'],
                      selectcolor=COLORS['bg_primary'], font=FONTS['body'],
                      activebackground=COLORS['bg_card'],
                      command=lambda: self._update_nested('agents.defaults.contextPruning.hardClear', 'enabled', prune_var.get())
                      ).pack(anchor=tk.W, pady=(4,0))

        # Memory search card
        mem = agents.get('memorySearch', {})
        mem_card = CardFrame(frame)
        mem_card.pack(fill=tk.X, pady=4, padx=4)
        tk.Label(mem_card, text="记忆检索后端 (Memory Search)", font=FONTS['h3'],
                bg=COLORS['bg_card'], fg=COLORS['text_primary']).pack(anchor=tk.W, pady=(0,8))
        self._make_cfg_combo(mem_card, "服务承载方", mem.get('provider', 'openai'),
                           ['openai', 'google', 'local', 'none'],
                           lambda v: self._update_nested('agents.defaults.memorySearch', 'provider', v),
                           display_options=['OpenAI 接口 (openai)', 'Google 接口 (google)', '本地向量化 (local)', '系统关闭 (none)'])
        self._make_cfg_entry(mem_card, "向量基地址", mem.get('remote', {}).get('baseUrl', ''),
                            lambda v: self._update_nested('agents.defaults.memorySearch.remote', 'baseUrl', v))
        self._make_cfg_entry(mem_card, "向量模型名", mem.get('model', ''),
                            lambda v: self._update_nested('agents.defaults.memorySearch', 'model', v))

    def _build_cfg_channels(self, frame):
        """Build channels/plugins tab - with toggles and editable fields"""
        frame = self._make_scrollable_frame(frame)
        channels = self.openclaw_data.get('channels', {})
        plugins = self.openclaw_data.get('plugins', {}).get('entries', {})

        # Discord card (main channel)
        discord = channels.get('discord', {})
        if discord:
            dc = CardFrame(frame)
            dc.pack(fill=tk.X, pady=4, padx=4)
            tk.Label(dc, text="📡 Discord", font=FONTS['h3'],
                    bg=COLORS['bg_card'], fg=COLORS['accent_purple']).pack(anchor=tk.W, pady=(0,8))

            # Enabled toggle
            dc_en = tk.BooleanVar(value=discord.get('enabled', False))
            tk.Checkbutton(dc, text="启用 Discord", variable=dc_en,
                          bg=COLORS['bg_card'], fg=COLORS['text_primary'],
                          selectcolor=COLORS['bg_primary'], font=FONTS['body_bold'],
                          activebackground=COLORS['bg_card'],
                          command=lambda: self._update_nested('channels.discord', 'enabled', dc_en.get())
                          ).pack(anchor=tk.W)

            self._make_cfg_entry(dc, "机器人令牌(Token)", discord.get('token', ''),
                               lambda v: self._update_nested('channels.discord', 'token', v), masked=True)
            bs_en = tk.BooleanVar(value=discord.get('blockStreaming', False))
            tk.Checkbutton(dc, text="打字机连续推流 (blockStreaming)", variable=bs_en,
                          bg=COLORS['bg_card'], fg=COLORS['text_primary'],
                          selectcolor=COLORS['bg_primary'], font=FONTS['body'],
                          activebackground=COLORS['bg_card'],
                          command=lambda: self._update_nested('channels.discord', 'blockStreaming', bs_en.get())
                          ).pack(anchor=tk.W)

            self._make_cfg_combo(dc, "加群自动同意策略", discord.get('groupPolicy', 'allowlist'),
                               ['open', 'disabled', 'allowlist'],
                               lambda v: self._update_nested('channels.discord', 'groupPolicy', v),
                               display_options=['直接全部放行 (open)', '静默全部拒绝 (disabled)', '仅核验白名单 (allowlist)'])

            # Allow bots
            ab = tk.BooleanVar(value=discord.get('allowBots', True))
            tk.Checkbutton(dc, text="允许其他机器人唤醒", variable=ab,
                          bg=COLORS['bg_card'], fg=COLORS['text_primary'],
                          selectcolor=COLORS['bg_primary'], font=FONTS['small'],
                          activebackground=COLORS['bg_card'],
                          command=lambda: self._update_nested('channels.discord', 'allowBots', ab.get())
                          ).pack(anchor=tk.W)

            # Actions toggles
            actions = discord.get('actions', {})
            tk.Label(dc, text="动作读写权限 (Actions):", font=FONTS['body_bold'],
                    bg=COLORS['bg_card'], fg=COLORS['text_primary']).pack(anchor=tk.W, pady=(8,4))
                    
            action_map = {'emojiUploads': '允许上传表情包', 'channelInfo': '频道元数据读写', 'events': '日程事件管理', 'channels': '频道与板块管理'}
            for aname in ['emojiUploads', 'channelInfo', 'events', 'channels']:
                av = tk.BooleanVar(value=actions.get(aname, True))
                tk.Checkbutton(dc, text=action_map[aname], variable=av,
                              bg=COLORS['bg_card'], fg=COLORS['text_primary'],
                              selectcolor=COLORS['bg_primary'], font=FONTS['small'],
                              activebackground=COLORS['bg_card'],
                              command=lambda a=aname, v=av: self._update_nested('channels.discord.actions', a, v.get())
                              ).pack(anchor=tk.W, padx=16)

            # Intents
            intents = discord.get('intents', {})
            tk.Label(dc, text="特权网关意图 (Intents):", font=FONTS['body_bold'],
                    bg=COLORS['bg_card'], fg=COLORS['text_primary']).pack(anchor=tk.W, pady=(8,4))
                    
            intent_map = {'presence': '实时在线状态监控', 'guildMembers': '全量群成员列表拉取'}
            for iname in ['presence', 'guildMembers']:
                iv = tk.BooleanVar(value=intents.get(iname, True))
                tk.Checkbutton(dc, text=intent_map[iname], variable=iv,
                              bg=COLORS['bg_card'], fg=COLORS['text_primary'],
                              selectcolor=COLORS['bg_primary'], font=FONTS['small'],
                              activebackground=COLORS['bg_card'],
                              command=lambda i=iname, v=iv: self._update_nested('channels.discord.intents', i, v.get())
                              ).pack(anchor=tk.W, padx=16)

        # NapCat card (QQ channel)
        napcat = channels.get('napcat', {})
        # Initialize all NapCat fields with defaults if missing (ensures save works even if user doesn't interact)
        napcat_defaults = {
            'enabled': False,
            'url': 'http://127.0.0.1:3000',
            'token': '',
            'streaming_mode': False,
            'enableGroupMessages': True,
            'groupMentionOnly': True,
            'groupWhitelist': [],
            'mediaProxyEnabled': True,
            'publicBaseUrl': 'http://127.0.0.1:18789',
            'pseudoStreaming': False,
            'pseudoStreamingDelay': 800
        }
        for key, default_val in napcat_defaults.items():
            if key not in napcat:
                self._update_nested('channels.napcat', key, default_val)
        if napcat:
            nc = CardFrame(frame)
            nc.pack(fill=tk.X, pady=4, padx=4)
            tk.Label(nc, text="🐧 NapCat (QQ)", font=FONTS['h3'],
                    bg=COLORS['bg_card'], fg=COLORS['accent_blue']).pack(anchor=tk.W, pady=(0,8))

            # Enabled toggle with tooltip
            self._make_cfg_checkbox(nc, "启用 NapCat", napcat.get('enabled', False),
                                   lambda v: self._update_nested('channels.napcat', 'enabled', v),
                                   tooltip="开启/关闭 NapCat QQ 渠道集成")

            self._make_cfg_entry(nc, "NapCat URL", napcat.get('url', 'http://127.0.0.1:3000'),
                               lambda v: self._update_nested('channels.napcat', 'url', v),
                               tooltip="NapCat OneBot API 地址，默认 127.0.0.1:3000",
                               validator=self._validate_url)
            self._make_cfg_entry(nc, "Token", napcat.get('token', ''),
                               lambda v: self._update_nested('channels.napcat', 'token', v), masked=True,
                               tooltip="NapCat access_token 鉴权令牌")

            # Streaming mode with tooltip
            self._make_cfg_checkbox(nc, "流式响应模式 (streaming_mode)", napcat.get('streaming_mode', False),
                                   lambda v: self._update_nested('channels.napcat', 'streaming_mode', v),
                                   tooltip="启用后消息将以打字机效果逐字发送")

            # Group messages with tooltip
            self._make_cfg_checkbox(nc, "启用群消息 (enableGroupMessages)", napcat.get('enableGroupMessages', True),
                                   lambda v: self._update_nested('channels.napcat', 'enableGroupMessages', v),
                                   tooltip="是否处理群聊消息，关闭则只响应私聊")

            # Group mention only with tooltip
            self._make_cfg_checkbox(nc, "群聊仅响应@提及 (groupMentionOnly)", napcat.get('groupMentionOnly', True),
                                   lambda v: self._update_nested('channels.napcat', 'groupMentionOnly', v),
                                   tooltip="开启后机器人只响应@它的群消息，避免干扰普通聊天")

            self._make_cfg_entry(nc, "群白名单 (groupWhitelist)",
                               ', '.join(napcat.get('groupWhitelist', [])) if isinstance(napcat.get('groupWhitelist'), list) else str(napcat.get('groupWhitelist', '')),
                               lambda v: self._update_nested_list('channels.napcat', 'groupWhitelist', v),
                               tooltip="群号白名单，用逗号分隔，留空则处理所有群")

            # Media proxy with tooltip
            self._make_cfg_checkbox(nc, "媒体代理 (mediaProxyEnabled)", napcat.get('mediaProxyEnabled', True),
                                   lambda v: self._update_nested('channels.napcat', 'mediaProxyEnabled', v),
                                   tooltip="启用后通过 Gateway 代理图片/语音等媒体文件")

            self._make_cfg_entry(nc, "公网地址 (publicBaseUrl)", napcat.get('publicBaseUrl', 'http://127.0.0.1:18789'),
                               lambda v: self._update_nested('channels.napcat', 'publicBaseUrl', v),
                               tooltip="Gateway 公网访问地址，用于生成媒体链接",
                               validator=self._validate_url)

            # Pseudo streaming with tooltip
            self._make_cfg_checkbox(nc, "伪流式传输 (pseudoStreaming)", napcat.get('pseudoStreaming', False),
                                   lambda v: self._update_nested('channels.napcat', 'pseudoStreaming', v),
                                   tooltip="启用后按换行符分割消息分段发送，模拟打字效果")

            self._make_cfg_entry(nc, "伪流式延迟 (pseudoStreamingDelay)", str(napcat.get('pseudoStreamingDelay', 800)),
                               lambda v: self._update_nested('channels.napcat', 'pseudoStreamingDelay', max(100, min(10000, int(v) if v.isdigit() else 800))),
                               tooltip="伪流式传输分段延迟时间（毫秒），默认800，范围100-10000",
                               validator=lambda v: (v.isdigit() and 100 <= int(v) <= 10000, "范围: 100-10000"))

        # Other settings card
        misc_card = CardFrame(frame)
        misc_card.pack(fill=tk.X, pady=4, padx=4)
        tk.Label(misc_card, text="其他设置", font=FONTS['h3'],
                bg=COLORS['bg_card'], fg=COLORS['text_primary']).pack(anchor=tk.W, pady=(0,8))

        # Cron with tooltip
        self._make_cfg_checkbox(misc_card, "📅 定时任务 (Cron)", self.openclaw_data.get('cron', {}).get('enabled', False),
                               lambda v: self._update_nested('cron', 'enabled', v),
                               tooltip="启用定时任务调度功能")

        # Canvas Host
        ch_en = tk.BooleanVar(value=self.openclaw_data.get('canvasHost', {}).get('enabled', True))
        tk.Checkbutton(misc_card, text="🎨 Canvas Host", variable=ch_en,
                      bg=COLORS['bg_card'], fg=COLORS['text_primary'],
                      selectcolor=COLORS['bg_primary'], font=FONTS['body'],
                      activebackground=COLORS['bg_card'],
                      command=lambda: self._update_nested('canvasHost', 'enabled', ch_en.get())
                      ).pack(anchor=tk.W)

        # Commands restart
        cmd_restart = tk.BooleanVar(value=self.openclaw_data.get('commands', {}).get('restart', True))
        tk.Checkbutton(misc_card, text="🔄 命令重启 (commands.restart)", variable=cmd_restart,
                      bg=COLORS['bg_card'], fg=COLORS['text_primary'],
                      selectcolor=COLORS['bg_primary'], font=FONTS['body'],
                      activebackground=COLORS['bg_card'],
                      command=lambda: self._update_nested('commands', 'restart', cmd_restart.get())
                      ).pack(anchor=tk.W)

        # Plugins allow list
        plugins_allow = self.openclaw_data.get('plugins', {}).get('allow', [])
        tk.Label(misc_card, text="\n插件信任列表 (plugins.allow):", font=FONTS['body_bold'],
                bg=COLORS['bg_card'], fg=COLORS['text_primary']).pack(anchor=tk.W, pady=(4,4))
        allow_var = tk.StringVar(value=', '.join(plugins_allow) if isinstance(plugins_allow, list) else str(plugins_allow))
        allow_entry = tk.Entry(misc_card, textvariable=allow_var, font=FONTS['mono_small'],
                              bg=COLORS['bg_input'], fg=COLORS['text_primary'],
                              insertbackground=COLORS['text_primary'], relief=tk.FLAT, width=50)
        allow_entry.pack(anchor=tk.W, padx=16, pady=2)
        allow_entry.bind('<FocusOut>', lambda e: self._update_plugins_allow(allow_var.get()))
        
        # Plugins entries
        if plugins:
            tk.Label(misc_card, text="\n插件启用状态:", font=FONTS['body_bold'],
                    bg=COLORS['bg_card'], fg=COLORS['text_primary']).pack(anchor=tk.W, pady=(4,4))
            for pl_name, pl_data in plugins.items():
                pv = tk.BooleanVar(value=pl_data.get('enabled', False))
                tk.Checkbutton(misc_card, text=f"🔌 {pl_name}", variable=pv,
                              bg=COLORS['bg_card'], fg=COLORS['text_primary'],
                              selectcolor=COLORS['bg_primary'], font=FONTS['body'],
                              activebackground=COLORS['bg_card'],
                              command=lambda n=pl_name, v=pv: self._update_nested(f'plugins.entries.{n}', 'enabled', v.get())
                              ).pack(anchor=tk.W, padx=16)

    def _build_cfg_raw(self, frame):
        """Build raw JSON editor tab"""
        self.raw_editor = scrolledtext.ScrolledText(
            frame, font=FONTS['mono_small'], bg=COLORS['bg_secondary'],
            fg=COLORS['text_primary'], insertbackground=COLORS['text_primary'],
            relief=tk.FLAT, wrap=tk.NONE)
        self.raw_editor.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        try:
            self.raw_editor.insert(tk.END, json.dumps(self.openclaw_data, indent=2, ensure_ascii=False))
        except: pass

    # ══════════════════════════════════════════════
    # PAGE: Logs
    # ══════════════════════════════════════════════
    def _build_logs_page(self, page):
        pad = tk.Frame(page, bg=COLORS['bg_primary'])
        pad.pack(fill=tk.BOTH, expand=True, padx=24, pady=16)

        hdr = tk.Frame(pad, bg=COLORS['bg_primary'])
        hdr.pack(fill=tk.X, pady=(0, 12))
        tk.Label(hdr, text="📋 日志中心", font=FONTS['h1'],
                bg=COLORS['bg_primary'], fg=COLORS['text_primary']).pack(side=tk.LEFT)
        ModernBtn(hdr, "📂 打开日志目录", self._open_logs_dir,
                 bg=COLORS['accent_blue']).pack(side=tk.RIGHT)

        # Service log selector
        sel_frame = tk.Frame(pad, bg=COLORS['bg_primary'])
        sel_frame.pack(fill=tk.X, pady=(0, 8))
        tk.Label(sel_frame, text="选择服务:", font=FONTS['small'],
                bg=COLORS['bg_primary'], fg=COLORS['text_secondary']).pack(side=tk.LEFT, padx=(0,8))

        try:
            with open(self.services_json, 'r', encoding='utf-8-sig') as f:
                svc_names = list(json.load(f).get('services', {}).keys())
        except: svc_names = []
        svc_names.insert(0, 'pm')

        self.log_svc_var = tk.StringVar(value='pm')
        for name in svc_names:
            rb = tk.Radiobutton(sel_frame, text=name, variable=self.log_svc_var, value=name,
                               bg=COLORS['bg_primary'], fg=COLORS['text_secondary'],
                               selectcolor=COLORS['bg_secondary'], font=FONTS['small'],
                               activebackground=COLORS['bg_primary'],
                               activeforeground=COLORS['accent_blue'],
                               command=self._load_selected_log)
            rb.pack(side=tk.LEFT, padx=4)

        self.log_viewer = scrolledtext.ScrolledText(
            pad, font=FONTS['mono_small'], bg=COLORS['bg_secondary'],
            fg=COLORS['text_primary'], insertbackground=COLORS['text_primary'],
            relief=tk.FLAT, wrap=tk.WORD)
            
        # Syntax Highlight Tags for Logs
        self.log_viewer.tag_config('ts', foreground=COLORS['text_muted'])
        self.log_viewer.tag_config('info', foreground=COLORS['text_secondary'])
        self.log_viewer.tag_config('warn', foreground=COLORS['accent_yellow'])
        self.log_viewer.tag_config('error', foreground=COLORS['accent_red'])
        self.log_viewer.tag_config('important', foreground=COLORS['accent_purple'], font=FONTS['body_bold'])
        self.log_viewer.tag_config('success', foreground=COLORS['accent_green'])
        self.log_viewer.tag_config('pid', foreground=COLORS['accent_blue'])
        
        self.log_viewer.pack(fill=tk.BOTH, expand=True)
        self._load_selected_log()

    def _load_selected_log(self):
        name = self.log_svc_var.get()
        def load():
            if name == 'pm':
                log_dir = self.pm_dir / 'pm-logs'
                today = time.strftime('%Y-%m-%d')
                log_file = log_dir / f'pm-{today}.log'
                try:
                    txt = log_file.read_text(encoding='utf-8', errors='replace')[-5000:]
                except: txt = "(无PM日志)"
            else:
                txt = self.api_call_text(f'/logs?name={name}&lines=100') or "(无日志)"
            self.root.after(0, lambda t=txt: self._set_log_viewer(t))
        run_threaded(load)

    def _set_log_viewer(self, text):
        import re
        self.log_viewer.delete('1.0', tk.END)
        for line in text.splitlines():
            m1 = re.match(r'^(\[[^\]]+\])\s+(.*)$', line)
            if not m1:
                hl = 'error' if any(w in line.lower() for w in ['error', 'exception', 'fail', 'traceback']) else None
                self.log_viewer.insert(tk.END, line + '\n', hl)
                continue
                
            ts, rest = m1.groups()
            self.log_viewer.insert(tk.END, ts + ' ', 'ts')
            
            m2 = re.match(r'^(\[([a-zA-Z]+)\])\s+(.*)$', rest)
            if m2:
                tag, lvl, msg = m2.groups()
                lvl = lvl.lower()
                valid_tags = ['info', 'warn', 'error', 'important', 'success']
                self.log_viewer.insert(tk.END, tag + ' ', lvl if lvl in valid_tags else 'info')
            else:
                msg = rest
            
            last = 0
            for pm in re.finditer(r'(PID:\s*\d+)', msg):
                self.log_viewer.insert(tk.END, msg[last:pm.start()])
                self.log_viewer.insert(tk.END, pm.group(1), 'pid')
                last = pm.end()
            self.log_viewer.insert(tk.END, msg[last:] + '\n')
            
        self.log_viewer.see(tk.END)

    def _open_logs_dir(self):
        log_dir = self.pm_dir / 'pm-logs'
        if log_dir.exists():
            os.startfile(str(log_dir))

    # ══════════════════════════════════════════════
    # PAGE: About
    # ══════════════════════════════════════════════
    def _build_about_page(self, page):
        pad = tk.Frame(page, bg=COLORS['bg_primary'])
        pad.pack(fill=tk.BOTH, expand=True, padx=24, pady=16)

        card = CardFrame(pad)
        card.pack(fill=tk.X, pady=(40, 0))

        tk.Label(card, text="🐉", font=('Segoe UI Emoji', 48),
                bg=COLORS['bg_card'], fg=COLORS['accent_blue']).pack(pady=(16,8))
        tk.Label(card, text="Sideria Process Manager", font=(FONT_FAMILY, 22, 'bold'),
                bg=COLORS['bg_card'], fg=COLORS['text_primary']).pack()
        tk.Label(card, text="Enhanced v3.0", font=FONTS['body'],
                bg=COLORS['bg_card'], fg=COLORS['accent_blue']).pack(pady=(0,12))
        tk.Label(card, text="希德莉亚进程管理器 - 增强版", font=FONTS['body'],
                bg=COLORS['bg_card'], fg=COLORS['text_secondary']).pack()

        for line in [
            "",
            "✦ 深色主题 + 侧边栏导航",
            "✦ gcli2api 网关集成管理",
            "✦ 图形化 openclaw.json 编辑器",
            "✦ 服务状态脉冲动画",
            "✦ 多级日志着色显示",
            "",
            "Built with 💙 for OpenClaw",
        ]:
            tk.Label(card, text=line, font=FONTS['small'],
                    bg=COLORS['bg_card'], fg=COLORS['text_secondary']).pack()

        tk.Label(card, text="", bg=COLORS['bg_card']).pack(pady=8)


# ═══════════════════════════════════════════════════
# Entry Point
# ═══════════════════════════════════════════════════
def main():
    root = tk.Tk()
    # Set icon if available
    try:
        icon_path = Path(__file__).parent / 'sideria-pm.ico'
        if icon_path.exists():
            root.iconbitmap(str(icon_path))
    except: pass
    app = SideriaPMGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
