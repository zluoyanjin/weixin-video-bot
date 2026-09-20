# -*- coding: utf-8 -*-
"""
浏览器连接：通过 CDP 端口连到「启动Chrome.bat」开出来的 Chrome 实例。
不负责启动 Chrome（那件事在 chrome.py 里），只负责连接 + 选页面。

重要：绝不自己拉起一个新 Chrome，也绝不关掉客户的 Chrome，
因为登录状态和直播间页面都在客户的浏览器里。
"""
from __future__ import annotations

TARGET_HOST = "channels.weixin.qq.com"


def connect_account(playwright, account, timeout_ms: int = 8000):
    """返回 (browser, page)；失败返回 (None, None)。"""
    name = account.get("name", "?")
    port = account.get("cdp_port")
    room_url = (account.get("room_url") or "").strip()
    cdp_url = f"http://127.0.0.1:{port}"

    try:
        browser = playwright.chromium.connect_over_cdp(cdp_url, timeout=timeout_ms)
    except Exception as e:
        print(f"[{name}] 连接失败 {cdp_url}：{e}", flush=True)
        return None, None

    try:
        if not browser.contexts:
            print(f"[{name}] Chrome 已连接但没有浏览器上下文，请先打开一个页面", flush=True)
            return None, None

        context = browser.contexts[0]
        pages = context.pages

        # 优先找已经在视频号域名的页面
        for page in pages:
            try:
                if TARGET_HOST in (page.url or ""):
                    print(f"[{name}] 已连接直播间页面", flush=True)
                    return browser, page
            except Exception:
                continue

        # 配置了直播间地址：自动打开
        if room_url:
            try:
                page = context.new_page()
                page.goto(room_url, timeout=30000)
                print(f"[{name}] 已自动打开：{room_url}", flush=True)
                return browser, page
            except Exception as e:
                print(f"[{name}] 打开直播间失败：{e}", flush=True)

        # 兜底：用最后一个页面
        if pages:
            page = pages[-1]
            try:
                print(f"[{name}] 未找到视频号页面，使用当前页：{page.url}", flush=True)
            except Exception:
                print(f"[{name}] 未找到视频号页面，使用当前页", flush=True)
            return browser, page

        print(f"[{name}] Chrome 里没有任何页面", flush=True)
        return None, None

    except Exception as e:
        print(f"[{name}] 连接过程异常：{e}", flush=True)
        return None, None


def is_alive(browser, page) -> bool:
    """判断连接是否还活着。"""
    try:
        if browser is None or page is None:
            return False
        if not browser.is_connected():
            return False
        if page.is_closed():
            return False
        return True
    except Exception:
        return False
