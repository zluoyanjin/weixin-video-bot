# -*- coding: utf-8 -*-
"""
自检脚本（双击「自检.bat」运行）。

不用真实视频号账号，就能把整条链路跑一遍：
    1. 环境检查   Python / Playwright / Chrome
    2. 配置检查   config/accounts.json 是否合法
    3. 联调检查   开一个临时 Chrome，用「模拟直播间页面」验证
                  a) 输入框定位   b) 回车发送   c) 发送按钮兜底   d) 断线检测
    4. 端口检查   accounts.json 里配置的端口有没有真的启动

临时 Chrome 用独立临时目录，测完自动清理，不会碰到你平时用的浏览器和登录态。
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import chrome as chromemod
import config as cfgmod
from browser import connect_account, is_alive
from sender import send_message

RESULTS = []


def check(name: str, ok: bool, detail: str = ""):
    RESULTS.append((name, ok))
    mark = "[PASS]" if ok else "[FAIL]"
    print(f"  {mark} {name}" + (f"  {detail}" if detail else ""), flush=True)
    return ok


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def wait_port(port: int, timeout: int = 20) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if chromemod.port_open(port):
            return True
        time.sleep(0.5)
    return False


PAGE_ENTER = """<!doctype html><html><body>
<div id="box" contenteditable="true" style="width:420px;height:60px;border:1px solid #333"></div>
<button id="btn">发送</button>
<div id="log"></div>
<script>
var box=document.getElementById('box');
function send(){var t=box.innerText.trim();if(t){var d=document.createElement('div');
d.className='msg';d.textContent=t;document.getElementById('log').appendChild(d);box.innerText='';}}
box.addEventListener('keydown',function(e){if(e.key==='Enter'){e.preventDefault();send();}});
document.getElementById('btn').addEventListener('click',send);
</script></body></html>"""

PAGE_BUTTON = """<!doctype html><html><body>
<div id="box" contenteditable="true" style="width:420px;height:60px;border:1px solid #333"></div>
<button id="btn">发送</button>
<div id="log"></div>
<script>
var box=document.getElementById('box');
function send(){var t=box.innerText.trim();if(t){var d=document.createElement('div');
d.className='msg';d.textContent=t;document.getElementById('log').appendChild(d);box.innerText='';}}
document.getElementById('btn').addEventListener('click',send);
</script></body></html>"""


# ---------------------------------------------------------------- 1 环境
def step_env():
    print("\n[1/4] 环境检查", flush=True)
    v = sys.version_info
    check("Python 版本", v >= (3, 9), f"{v.major}.{v.minor}.{v.micro}")

    try:
        import playwright

        check("Playwright 已安装", True, getattr(playwright, "__version__", "") or "")
        return True
    except Exception as e:
        check("Playwright 已安装", False, "请先双击 安装环境.bat")
        return False


# ---------------------------------------------------------------- 2 配置
def step_config():
    print("\n[2/4] 配置检查", flush=True)
    cfg = cfgmod.load_config()
    check("配置文件存在", os.path.exists(cfgmod.CONFIG_FILE), cfgmod.CONFIG_FILE)
    errors, warnings = cfgmod.validate_config(cfg)
    check("配置合法", not errors, ("；".join(errors)) if errors else "")
    for w in warnings:
        print(f"        提醒：{w}", flush=True)
    pairs = cfgmod.enabled_accounts(cfg)
    check("至少启用 1 个账号", len(pairs) > 0, f"当前 {len(pairs)} 个")
    return cfg


# ---------------------------------------------------------------- 3 联调
def step_live(cfg):
    print("\n[3/4] 模拟直播间联调（会临时弹出一个 Chrome，测完自动关闭）", flush=True)
    chrome_path = chromemod.find_chrome((cfg.get("chrome_path") or "").strip())
    if not check("找到 Chrome", bool(chrome_path), chrome_path or ""):
        return False

    tmp = tempfile.mkdtemp(prefix="bot_selftest_")
    proc = None
    ok_all = True
    try:
        p1 = os.path.join(tmp, "enter.html")
        p2 = os.path.join(tmp, "button.html")
        with open(p1, "w", encoding="utf-8") as f:
            f.write(PAGE_ENTER)
        with open(p2, "w", encoding="utf-8") as f:
            f.write(PAGE_BUTTON)
        url1 = "file:///" + p1.replace("\\", "/")
        url2 = "file:///" + p2.replace("\\", "/")

        port = free_port()
        profile = os.path.join(tmp, "profile")
        proc = subprocess.Popen([
            chrome_path,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile}",
            "--no-first-run",
            "--no-default-browser-check",
            url1,
        ])
        if not check(f"临时 Chrome 已启动（端口 {port}）", wait_port(port)):
            return False
        time.sleep(1)

        from playwright.sync_api import sync_playwright

        account = {"name": "自检", "cdp_port": port, "room_url": url1, "interval": 60}
        with sync_playwright() as p:
            browser, page = connect_account(p, account)
            if not check("CDP 连接成功", page is not None):
                return False
            check("页面存活检测", is_alive(browser, page))

            # a) 回车发送
            r1 = send_message(page, "自检消息一")
            time.sleep(0.4)
            r2 = send_message(page, "自检消息二")
            time.sleep(0.4)
            msgs = page.locator("#log .msg")
            got = [msgs.nth(i).inner_text() for i in range(msgs.count())]
            ok_all &= check("回车发送", r1 and r2 and got == ["自检消息一", "自检消息二"], str(got))

            # b) 按钮兜底：这个页面不响应回车，只能点发送按钮
            page.goto(url2)
            time.sleep(0.5)
            r3 = send_message(page, "按钮兜底消息")
            time.sleep(0.5)
            msgs = page.locator("#log .msg")
            got = [msgs.nth(i).inner_text() for i in range(msgs.count())]
            ok_all &= check("发送按钮兜底", r3 and got == ["按钮兜底消息"], str(got))

            # c) 断线检测
            page.close()
            time.sleep(0.5)
            ok_all &= check("断线能被识别", not is_alive(browser, page))
        return ok_all
    except Exception as e:
        check("联调过程未抛异常", False, str(e))
        return False
    finally:
        if proc:
            proc.terminate()
            time.sleep(1)
        shutil.rmtree(tmp, ignore_errors=True)
        print("        临时 Chrome 已关闭、临时文件已清理", flush=True)


# ---------------------------------------------------------------- 4 端口
def step_ports(cfg):
    """仅作提示，不计入通过/失败——没开 Chrome 时端口本来就是关的。"""
    print("\n[4/4] 端口提示（对应 accounts.json 里配置的账号）", flush=True)
    for _, acc in cfgmod.enabled_accounts(cfg):
        port = int(acc.get("cdp_port", 0))
        opened = chromemod.port_open(port)
        state = "已启动" if opened else "未启动（先运行 启动Chrome.bat 才会启动）"
        print(f"  [提示] {acc.get('name')} 端口 {port}：{state}", flush=True)
    return True


def main():
    print("=" * 58, flush=True)
    print("微信视频号机器人 - 自检", flush=True)
    print("=" * 58, flush=True)

    if not step_env():
        step_config()
    else:
        cfg = step_config()
        step_live(cfg)
        step_ports(cfg)

    total = len(RESULTS)
    passed = sum(1 for _, ok in RESULTS if ok)
    print("\n" + "=" * 58, flush=True)
    print(f"自检结果：{passed}/{total} 项通过", flush=True)
    failed = [n for n, ok in RESULTS if not ok]
    if failed:
        print("未通过：", flush=True)
        for n in failed:
            print(f"  - {n}", flush=True)
    print("=" * 58, flush=True)
    return 0 if not failed else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"自检脚本异常：{e}", flush=True)
        sys.exit(1)
