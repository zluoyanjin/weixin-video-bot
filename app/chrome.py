# -*- coding: utf-8 -*-
"""
Chrome 管理：自动查找 Chrome -> 为每个账号创建独立 profile -> 带调试端口启动。

每个账号一个独立 --user-data-dir，登录状态互相隔离：
    chrome_profiles/account_01  视频号A
    chrome_profiles/account_02  视频号B
    ...
第一次启动后客户各自扫码登录，之后登录状态就保存在本地，不用重复登录。
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time

import config


# ---------------------------------------------------------------- 查找 Chrome
def _from_registry():
    try:
        import winreg

        for root, path in (
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"),
        ):
            try:
                with winreg.OpenKey(root, path) as key:
                    value, _ = winreg.QueryValueEx(key, "")
                    if value and os.path.exists(value):
                        return value
            except Exception:
                continue
    except Exception:
        pass
    return None


def find_chrome(custom_path: str = ""):
    if custom_path and os.path.exists(custom_path):
        return custom_path

    env = os.environ
    candidates = [
        _from_registry(),
        os.path.join(env.get("ProgramFiles", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(env.get("ProgramFiles(x86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(env.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(env.get("ProgramFiles", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(env.get("ProgramFiles(x86)", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


def port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except Exception:
        return False


# -------------------------------------------------- 启动标识页（让每个窗口一眼看出对应哪个账号/端口）
_LABEL_COLORS = ["#2e7d32", "#1565c0", "#c62828", "#6a1b9a", "#ef6c00", "#00838f"]


def make_label_html(name: str, port: int, index: int) -> str:
    color = _LABEL_COLORS[index % len(_LABEL_COLORS)]
    return f"""<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>机器人标识 - {name}</title>
<style>
 body {{ margin:0; font-family:-apple-system,"Microsoft YaHei",sans-serif; background:{color};
        color:#fff; display:flex; flex-direction:column; align-items:center; justify-content:center;
        height:100vh; text-align:center; }}
 .box {{ background:rgba(0,0,0,.25); padding:42px 64px; border-radius:18px; max-width:620px; }}
 .sub {{ font-size:20px; opacity:.9; }}
 h1 {{ font-size:46px; margin:8px 0; }}
 .port {{ font-size:30px; margin:16px 0; letter-spacing:1px; }}
 .tip {{ font-size:18px; opacity:.92; line-height:1.7; }}
 b {{ font-size:22px; }}
 button {{ margin-top:26px; font-size:20px; padding:13px 30px; border:0; border-radius:10px;
           background:#fff; color:{color}; cursor:pointer; font-weight:bold; }}
 button:hover {{ opacity:.88; }}
</style>
</head>
<body>
 <div class="box">
   <div class="sub">这是「启动机器人」要使用的浏览器窗口</div>
   <h1>{name}</h1>
   <div class="port">CDP 端口：{port}</div>
   <div class="tip">请在这个窗口里登录 <b>{name}</b> 的视频号，并进入要发言的直播间。<br>
       登录完成后点下面按钮进入视频号页面，再双击「启动机器人.bat」。</div>
   <button onclick="location.href='https://channels.weixin.qq.com/'">&#9654; 进入视频号页面</button>
 </div>
</body>
</html>
"""


def label_path(name: str, port: int, index: int) -> str:
    d = os.path.join(config.APP_DIR, "labels")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"label_{port}.html")
    with open(p, "w", encoding="utf-8") as f:
        f.write(make_label_html(name, port, index))
    return p


# ---------------------------------------------------------------- 启动
def launch_one(chrome_path: str, account: dict, index: int, dry: bool = False):
    name = account.get("name", f"账号{index + 1}")
    port = int(account.get("cdp_port", 9222))
    profile = config.profile_dir(account, index)
    room_url = (account.get("room_url") or "").strip()

    if not dry:
        os.makedirs(profile, exist_ok=True)

    args = [
        chrome_path,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-popup-blocking",
        f"--remote-allow-origins=*",
    ]
    # 用一个独立的 --user-data-dir 时，Chrome 可能拒绝复用已有实例，
    # 加 --no-startup-window 反而会导致没有窗口，所以这里不加。
    if room_url:
        args.append(room_url)
    else:
        # 先打开标识页，让用户一眼看出这个窗口对应哪个账号/端口，
        # 登录完成后再点页面上的按钮进入视频号。
        args.append("file:///" + label_path(name, port, index).replace("\\", "/"))

    if dry:
        print(f"[{name}] 计划启动 -> 端口 {port} / 目录 {profile}", flush=True)
        return True

    if port_open(port):
        print(f"[{name}] 端口 {port} 已在监听，跳过（Chrome 可能已开着）", flush=True)
        return True

    try:
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"[{name}] 已启动 -> 端口 {port}", flush=True)
        return True
    except Exception as e:
        print(f"[{name}] 启动失败：{e}", flush=True)
        return False


def launch_all(cfg: dict, dry: bool = False):
    print("=" * 58, flush=True)
    print("微信视频号 Chrome 启动器", flush=True)
    print("=" * 58, flush=True)

    chrome_path = find_chrome((cfg.get("chrome_path") or "").strip())
    if not chrome_path:
        print("[XX] 找不到 Google Chrome / Edge。", flush=True)
        print("     请先安装 Chrome，或在 config/accounts.json 里填 chrome_path。", flush=True)
        return 1

    print(f"浏览器：{chrome_path}", flush=True)
    print(f"配置：{config.CONFIG_FILE}", flush=True)
    print(flush=True)

    pairs = config.enabled_accounts(cfg)
    if not pairs:
        print("[!!] 配置里没有启用任何账号（enabled: true）", flush=True)
        return 1

    print("每个 Chrome 窗口打开后会显示它对应的账号名和端口，一眼就能区分。", flush=True)
    print(flush=True)

    for index, acc in pairs:
        launch_one(chrome_path, acc, index, dry=dry)
        if not dry:
            time.sleep(3)

    print(flush=True)
    print("=" * 58, flush=True)
    for order, (index, acc) in enumerate(pairs, start=1):
        print(f"  第{order}个窗口  {acc.get('name')}  ->  端口 {acc.get('cdp_port')}", flush=True)
    print("=" * 58, flush=True)
    print(flush=True)
    if not dry:
        print("每个窗口登录对应视频号 -> 点页面按钮进视频号 -> 运行「启动机器人.bat」", flush=True)
    return 0


def show_status(cfg: dict):
    print("端口状态：", flush=True)
    for index, acc in config.enabled_accounts(cfg):
        port = int(acc.get("cdp_port", 0))
        state = "已启动" if port_open(port) else "未启动"
        print(f"  [{state}] {acc.get('name')}  {port}", flush=True)


def main():
    args = sys.argv[1:]
    cfg = config.load_config()
    errors, warnings = config.validate_config(cfg)
    for w in warnings:
        print(f"[!!] {w}", flush=True)
    if errors:
        for e in errors:
            print(f"[XX] {e}", flush=True)
        return 1

    if "--status" in args:
        show_status(cfg)
        return 0
    return launch_all(cfg, dry=("--dry" in args))


if __name__ == "__main__":
    sys.exit(main())
