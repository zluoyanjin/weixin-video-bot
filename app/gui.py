# -*- coding: utf-8 -*-
"""
图形配置界面（双击「配置账号.bat」打开）。

客户不需要碰 Python 文件：在这里改账号名、端口、发送间隔、直播间地址、文案，
点保存即可；也可以直接在这里启动 Chrome / 启动机器人 / 停止机器人。
"""
from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext, ttk
except Exception as _tk_err:
    # tkinter 不在标准库里（某些精简/商店版 Python 会缺），用系统对话框告知，避免窗口一闪而过
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0,
            "无法打开配置窗口：当前 Python 没有内置 tkinter 图形库。\n\n"
            "请重新安装 Python（安装时勾选 tcl/tk 和 IDLE），\n"
            "或改用「启动机器人.bat」直接运行，不影响发消息功能。\n\n"
            "技术信息：%s" % _tk_err,
            "配置账号",
            0x10,
        )
    except Exception:
        pass
    sys.exit(1)

import config as cfgmod
import chrome as chromemod
import main as bot_main  # 启动机器人按钮调用 bot_main.run_bot

DONE_FLAG = "__BOT_DONE__"


def _fail(msg: str):
    """界面初始化失败时：写日志 + 弹系统错误框，避免无声卡死。"""
    try:
        os.makedirs(cfgmod.APP_DIR, exist_ok=True)
        log_dir = os.path.join(cfgmod.APP_DIR, "logs")
        os.makedirs(log_dir, exist_ok=True)
        logp = os.path.join(log_dir, "gui_error.log")
        with open(logp, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + msg + "\n" + "=" * 40 + "\n")
    except Exception:
        pass
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, msg, "配置账号 - 错误", 0x10)
    except Exception:
        print(msg, flush=True)


class QueueWriter:
    """把 print 输出接到界面日志区。"""

    def __init__(self, q: queue.Queue):
        self.q = q

    def write(self, text):
        if text and text.strip():
            self.q.put(text)

    def flush(self):
        pass


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("微信视频号机器人 - 配置与运行")
        self.root.geometry("1000x680")

        self.cfg = cfgmod.load_config()
        self.accounts = self.cfg.get("accounts", [])
        self.current_index = None

        self.q = queue.Queue()
        self.bot_thread = None
        self.stop_event = None

        print("[1/4] 载入配置完成", flush=True)
        self._build_ui()
        print("[2/4] 界面构建完成", flush=True)
        self._refresh_list()
        print("[3/4] 账号列表刷新完成", flush=True)
        if self.accounts:
            # 选中第 0 个账号，触发 <<TreeviewSelect>> -> _select 加载数据
            # 注意：_select 内部不再调用 selection_set，避免事件互触发死循环
            self.tree.selection_set("0")

        self.root.after(120, self._drain_queue)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        # 确保窗口弹出到最前，避免被启动器的黑窗口挡住而误以为“没反应”
        # 1 秒后取消置顶，否则会一直压在所有窗口上面
        self.root.after(50, lambda: self.root.lift())
        self.root.after(50, lambda: self.root.attributes("-topmost", True))
        self.root.after(1050, lambda: self.root.attributes("-topmost", False))
        print("[4/4] 配置窗口已打开（这就是操作界面，不是黑窗口）", flush=True)

    # ------------------------------------------------------------ 界面
    def _build_ui(self):
        top = ttk.Frame(self.root, padding=6)
        top.pack(fill=tk.X)

        ttk.Button(top, text="启动 Chrome", command=self.start_chrome).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="启动机器人", command=self.start_bot).pack(side=tk.LEFT, padx=3)
        self.btn_stop = ttk.Button(top, text="停止机器人", command=self.stop_bot, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=3)
        ttk.Separator(top, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        ttk.Button(top, text="保存配置", command=self.save_config).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="重新加载", command=self.reload_config).pack(side=tk.LEFT, padx=3)
        ttk.Button(top, text="打开程序目录", command=self.open_folder).pack(side=tk.LEFT, padx=3)

        body = ttk.Frame(self.root, padding=(6, 0))
        body.pack(fill=tk.BOTH, expand=True)

        # 左：账号列表
        left = ttk.Frame(body)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

        cols = ("name", "port", "interval", "enabled")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", height=14, selectmode="browse")
        self.tree.heading("name", text="账号")
        self.tree.heading("port", text="端口")
        self.tree.heading("interval", text="间隔(s)")
        self.tree.heading("enabled", text="启用")
        self.tree.column("name", width=120)
        self.tree.column("port", width=60, anchor=tk.CENTER)
        self.tree.column("interval", width=70, anchor=tk.CENTER)
        self.tree.column("enabled", width=50, anchor=tk.CENTER)
        self.tree.pack(side=tk.TOP, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        btns = ttk.Frame(left)
        btns.pack(side=tk.TOP, fill=tk.X, pady=6)
        ttk.Button(btns, text="新增账号", command=self.add_account).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="删除账号", command=self.del_account).pack(side=tk.LEFT, padx=2)

        # 右：编辑区
        right = ttk.Frame(body)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        form = ttk.LabelFrame(right, text="账号设置", padding=8)
        form.pack(fill=tk.X)

        self.var_name = tk.StringVar()
        self.var_port = tk.StringVar()
        self.var_interval = tk.StringVar()
        self.var_room = tk.StringVar()
        self.var_enabled = tk.BooleanVar(value=True)
        self.var_send_all = tk.BooleanVar(value=True)

        row = 0
        ttk.Label(form, text="账号名称：").grid(row=row, column=0, sticky=tk.W, pady=3)
        ttk.Entry(form, textvariable=self.var_name, width=22).grid(row=row, column=1, sticky=tk.W)

        ttk.Label(form, text="CDP 端口：").grid(row=row, column=2, sticky=tk.W, padx=(16, 0))
        ttk.Entry(form, textvariable=self.var_port, width=10).grid(row=row, column=3, sticky=tk.W)

        row += 1
        ttk.Label(form, text="发送间隔(秒)：").grid(row=row, column=0, sticky=tk.W, pady=3)
        ttk.Entry(form, textvariable=self.var_interval, width=22).grid(row=row, column=1, sticky=tk.W)

        ttk.Label(form, text="启用：").grid(row=row, column=2, sticky=tk.W, padx=(16, 0))
        ttk.Checkbutton(form, variable=self.var_enabled).grid(row=row, column=3, sticky=tk.W)

        row += 1
        ttk.Label(form, text="直播间地址(可选)：").grid(row=row, column=0, sticky=tk.W, pady=3)
        ttk.Entry(form, textvariable=self.var_room, width=60).grid(row=row, column=1, columnspan=3, sticky=tk.W)

        ttk.Label(form, text="填了地址后，机器人会自动打开该直播间", foreground="#888888").grid(
            row=row + 1, column=1, columnspan=3, sticky=tk.W
        )

        row += 2
        ttk.Checkbutton(form, text="每轮把全部话术发一遍（不勾则每条按间隔轮流发）", variable=self.var_send_all).grid(
            row=row, column=0, columnspan=4, sticky=tk.W, pady=3
        )

        msg = ttk.LabelFrame(right, text="发送文案（一行一条，每轮按顺序全部发出）", padding=8)
        msg.pack(fill=tk.BOTH, expand=True, pady=8)
        self.txt_messages = scrolledtext.ScrolledText(msg, height=10, wrap=tk.WORD)
        self.txt_messages.pack(fill=tk.BOTH, expand=True)

        adv = ttk.LabelFrame(right, text="全局设置", padding=8)
        adv.pack(fill=tk.X)

        self.var_dry = tk.BooleanVar(value=bool(self.cfg.get("dry_run")))
        self.var_jitter = tk.StringVar(value=str(self.cfg.get("jitter_seconds", 0)))
        self.var_reconnect = tk.StringVar(value=str(self.cfg.get("reconnect_seconds", 30)))
        self.var_gap = tk.StringVar(value=str(self.cfg.get("gap_seconds", 2.5)))

        ttk.Checkbutton(adv, text="演练模式（只打印不发送）", variable=self.var_dry).pack(side=tk.LEFT)
        ttk.Label(adv, text="每条间隔(秒)：").pack(side=tk.LEFT, padx=(16, 0))
        ttk.Entry(adv, textvariable=self.var_gap, width=8).pack(side=tk.LEFT)
        ttk.Label(adv, text="间隔抖动(秒)：").pack(side=tk.LEFT, padx=(16, 0))
        ttk.Entry(adv, textvariable=self.var_jitter, width=8).pack(side=tk.LEFT)
        ttk.Label(adv, text="重连间隔(秒)：").pack(side=tk.LEFT, padx=(16, 0))
        ttk.Entry(adv, textvariable=self.var_reconnect, width=8).pack(side=tk.LEFT)
        ttk.Button(adv, text="选择 Chrome 路径", command=self.pick_chrome).pack(side=tk.LEFT, padx=(16, 0))

        logf = ttk.LabelFrame(self.root, text="运行日志", padding=6)
        logf.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))
        self.txt_log = scrolledtext.ScrolledText(logf, height=12, wrap=tk.WORD)
        self.txt_log.pack(fill=tk.BOTH, expand=True)

    # ------------------------------------------------------------ 列表
    def _refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for i, acc in enumerate(self.accounts):
            self.tree.insert(
                "",
                tk.END,
                iid=str(i),
                values=(
                    acc.get("name", ""),
                    acc.get("cdp_port", ""),
                    acc.get("interval", ""),
                    "是" if acc.get("enabled", True) else "否",
                ),
            )

    def _on_tree_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if idx == self.current_index:
            # 已经是当前账号，不重复加载，避免与 selection_set 互触发
            return
        self._select(idx)

    def _select(self, index: int):
        self._collect_form()  # 先保存上一个账号的编辑
        self.current_index = index
        acc = self.accounts[index]
        self.var_name.set(acc.get("name", ""))
        self.var_port.set(str(acc.get("cdp_port", "")))
        self.var_interval.set(str(acc.get("interval", "")))
        self.var_room.set(acc.get("room_url", "") or "")
        self.var_enabled.set(bool(acc.get("enabled", True)))
        self.var_send_all.set(bool(acc.get("send_all", True)))
        self.txt_messages.delete("1.0", tk.END)
        for m in acc.get("messages") or []:
            self.txt_messages.insert(tk.END, str(m) + "\n")
        # 注意：这里不要调用 selection_set，否则会再次触发 <<TreeviewSelect>>
        # 形成事件互触发死循环，导致窗口卡住无响应。

    def _collect_form(self):
        """把表单内容写回当前账号对象。"""
        if self.current_index is None:
            return
        if self.current_index >= len(self.accounts):
            return
        acc = self.accounts[self.current_index]
        acc["name"] = self.var_name.get().strip()
        try:
            acc["cdp_port"] = int(self.var_port.get().strip())
        except ValueError:
            pass
        try:
            acc["interval"] = float(self.var_interval.get().strip())
        except ValueError:
            pass
        acc["room_url"] = self.var_room.get().strip()
        acc["enabled"] = bool(self.var_enabled.get())
        acc["send_all"] = bool(self.var_send_all.get())
        raw = self.txt_messages.get("1.0", tk.END).splitlines()
        acc["messages"] = [line.strip() for line in raw if line.strip()]

    # ------------------------------------------------------------ 操作
    def add_account(self):
        self._collect_form()
        ports = [a.get("cdp_port", 9222) for a in self.accounts]
        port = max(ports) + 1 if ports else 9222
        self.accounts.append(
            {
                "name": f"视频号{len(self.accounts) + 1}",
                "enabled": True,
                "cdp_port": port,
                "interval": 300,
                "room_url": "",
                "messages": ["欢迎大家来到直播间～"],
            }
        )
        self.cfg["accounts"] = self.accounts
        self._refresh_list()
        self.tree.selection_set(str(len(self.accounts) - 1))

    def del_account(self):
        self._collect_form()
        if self.current_index is None or not self.accounts:
            return
        name = self.accounts[self.current_index].get("name", "")
        if not messagebox.askyesno("确认", f"确定删除账号「{name}」吗？"):
            return
        del self.accounts[self.current_index]
        self.cfg["accounts"] = self.accounts
        self.current_index = None
        self._refresh_list()
        if self.accounts:
            self.tree.selection_set("0")

    def pick_chrome(self):
        path = filedialog.askopenfilename(title="选择 Chrome", filetypes=[("chrome.exe", "*.exe")])
        if path:
            self.cfg["chrome_path"] = path
            self._log(f"已设置 Chrome 路径：{path}")

    def save_config(self):
        self._collect_form()
        try:
            self.cfg["dry_run"] = bool(self.var_dry.get())
            self.cfg["jitter_seconds"] = float(self.var_jitter.get().strip() or 0)
            self.cfg["reconnect_seconds"] = float(self.var_reconnect.get().strip() or 30)
            self.cfg["gap_seconds"] = float(self.var_gap.get().strip() or 2.5)
        except ValueError:
            messagebox.showwarning("提示", "抖动 / 重连间隔必须是数字")
            return

        errors, warnings = cfgmod.validate_config(self.cfg)
        if errors:
            messagebox.showerror("配置有误", "\n".join(errors))
            return
        if cfgmod.save_config(self.cfg):
            self._refresh_list()
            self._log("配置已保存到 config/accounts.json")
            if warnings:
                self._log("提醒：" + "；".join(warnings))
            messagebox.showinfo("完成", "配置已保存")

    def reload_config(self):
        self.cfg = cfgmod.load_config()
        self.accounts = self.cfg.get("accounts", [])
        self.current_index = None
        self._refresh_list()
        if self.accounts:
            self.tree.selection_set("0")
        self._log("已重新加载配置")

    def open_folder(self):
        try:
            os.startfile(cfgmod.APP_DIR)
        except Exception:
            subprocess.Popen(["explorer", cfgmod.APP_DIR])

    # ------------------------------------------------------------ 运行
    def start_chrome(self):
        self.save_config()
        self._log("正在启动 Chrome，请稍候...")

        def run():
            old = sys.stdout
            sys.stdout = QueueWriter(self.q)
            try:
                chromemod.launch_all(cfgmod.load_config())
            except Exception:
                traceback.print_exc()
            finally:
                sys.stdout = old

        threading.Thread(target=run, daemon=True).start()

    def start_bot(self):
        self.save_config()
        if self.bot_thread and self.bot_thread.is_alive():
            messagebox.showinfo("提示", "机器人已经在运行中")
            return

        self.stop_event = threading.Event()
        self.btn_stop.config(state=tk.NORMAL)

        def run():
            old = sys.stdout
            sys.stdout = QueueWriter(self.q)
            try:
                bot_main.run_bot(stop_event=self.stop_event, interactive=False)
            except Exception:
                traceback.print_exc()
            finally:
                sys.stdout = old
                self.q.put(DONE_FLAG)

        self.bot_thread = threading.Thread(target=run, daemon=True)
        self.bot_thread.start()
        self._log("机器人启动中...")

    def stop_bot(self):
        if self.stop_event:
            self.stop_event.set()
            self._log("已发送停止信号，等待机器人退出...")
        self.btn_stop.config(state=tk.DISABLED)

    # ------------------------------------------------------------ 日志
    def _log(self, text):
        self.txt_log.insert(tk.END, text + "\n")
        self.txt_log.see(tk.END)

    def _drain_queue(self):
        try:
            while True:
                item = self.q.get_nowait()
                if item == DONE_FLAG:
                    self.btn_stop.config(state=tk.DISABLED)
                    continue
                self.txt_log.insert(tk.END, item)
                self.txt_log.see(tk.END)
                lines = int(self.txt_log.index("end-1c").split(".")[0])
                if lines > 3000:
                    self.txt_log.delete("1.0", "500.0")
        except queue.Empty:
            pass
        self.root.after(120, self._drain_queue)

    # ------------------------------------------------------------ 退出
    def _on_close(self):
        if self.bot_thread and self.bot_thread.is_alive():
            if not messagebox.askyesno("确认", "机器人正在运行，确定退出吗？"):
                return
            self.stop_bot()
        self.root.destroy()


def main():
    print("正在启动配置窗口...", flush=True)
    try:
        root = tk.Tk()
    except Exception as e:
        _fail("无法创建图形窗口（Tk 初始化失败）：%s\n\n"
              "通常是 Python 的 tcl/tk 图形库缺失，请重新安装 Python 并勾选 tcl/tk 与 IDLE。" % e)
        return

    try:
        App(root)
    except Exception:
        _fail("界面初始化失败：\n" + traceback.format_exc())
        try:
            root.destroy()
        except Exception:
            pass
        return

    try:
        root.mainloop()
    except Exception:
        _fail("运行异常：\n" + traceback.format_exc())


if __name__ == "__main__":
    main()
