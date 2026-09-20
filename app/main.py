# -*- coding: utf-8 -*-
"""
微信视频号多账号自动发言机器人 - 主程序。

流程：
    读取 config/accounts.json
      -> 通过 CDP 连接每个已启动的 Chrome
      -> 每个账号一个调度器，按间隔循环发送文案
      -> 掉线自动重连，Ctrl+C 优雅退出

被 GUI 调用时用 run_bot(stop_event=...)，在线程里跑，不会阻塞界面。
"""
from __future__ import annotations

import sys
import time

import config
from browser import connect_account, is_alive
from scheduler import Scheduler


def _dry_sender(page, text):
    print(f"[DRY-RUN] 模拟发送：{text}", flush=True)
    return True


def run_bot(stop_event=None, interactive: bool = True):
    """启动机器人。stop_event 为 threading.Event，置位后循环退出。"""
    cfg = config.load_config()
    errors, warnings = config.validate_config(cfg)
    for w in warnings:
        print(f"[!!] {w}", flush=True)
    if errors:
        for e in errors:
            print(f"[XX] {e}", flush=True)
        print("[XX] 配置有误，请先运行「配置账号.bat」修正", flush=True)
        return False

    dry_run = bool(cfg.get("dry_run"))
    jitter = float(cfg.get("jitter_seconds") or 0)
    reconnect_gap = float(cfg.get("reconnect_seconds") or 30)
    gap_between = float(cfg.get("gap_seconds") or 2.5)
    pairs = config.enabled_accounts(cfg)

    print("=" * 58, flush=True)
    print("微信视频号多账号机器人", flush=True)
    print("=" * 58, flush=True)
    print(f"配置文件：{config.CONFIG_FILE}", flush=True)
    print(f"启用账号：{len(pairs)} 个" + ("（演练模式，不会真的发送）" if dry_run else ""), flush=True)
    print(flush=True)

    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        print(f"[XX] Playwright 未安装：{e}", flush=True)
        print("     请先双击运行「安装环境.bat」", flush=True)
        return False

    sender = _dry_sender if dry_run else None
    if sender is None:
        from sender import send_message
        sender = send_message

    sessions = []
    with sync_playwright() as p:
        for order, (index, acc) in enumerate(pairs):
            browser, page = connect_account(p, acc)
            if browser is None or page is None:
                continue
            sch = Scheduler(
                name=acc.get("name"),
                page=page,
                messages=acc.get("messages") or [],
                interval=acc.get("interval", 300),
                jitter=jitter,
                start_delay=5 + order * 3,   # 错开首条，避免同秒集体发言
                gap_between=gap_between,
                send_all=acc.get("send_all", True),
            )
            sessions.append(
                {"account": acc, "browser": browser, "page": page, "scheduler": sch, "last_try": 0.0}
            )

        print(flush=True)
        print(f"成功连接 {len(sessions)} / {len(pairs)} 个账号", flush=True)
        if not sessions:
            print("[XX] 没有连上任何视频号。请确认：", flush=True)
            print("     1) 已经双击运行「启动Chrome.bat」", flush=True)
            print("     2) Chrome 里已登录视频号、并且停留在直播间页面", flush=True)
            return False

        print("机器人开始运行，按 Ctrl+C 停止", flush=True)
        print("-" * 58, flush=True)

        stopped = False
        try:
            while True:
                if stop_event is not None and stop_event.is_set():
                    stopped = True
                    break

                now = time.time()
                for item in sessions:
                    acc = item["account"]
                    name = acc.get("name")
                    sch = item["scheduler"]

                    if not is_alive(item["browser"], item["page"]):
                        if now - item["last_try"] >= reconnect_gap:
                            item["last_try"] = now
                            print(f"[{name}] 连接已断开，尝试重连...", flush=True)
                            try:
                                browser, page = connect_account(p, acc, timeout_ms=5000)
                            except Exception as e:
                                browser, page = None, None
                                print(f"[{name}] 重连异常：{e}", flush=True)
                            if browser is not None and page is not None:
                                item["browser"], item["page"] = browser, page
                                sch.replace_page(page)
                                print(f"[{name}] 重连成功", flush=True)
                            else:
                                print(f"[{name}] 重连失败，{int(reconnect_gap)} 秒后重试", flush=True)
                        continue

                    try:
                        sch.check(sender)
                    except Exception as e:
                        print(f"[{name}] 运行异常：{e}", flush=True)

                # sleep 分片，方便及时响应停止信号
                for _ in range(10):
                    if stop_event is not None and stop_event.is_set():
                        break
                    time.sleep(0.1)

        except KeyboardInterrupt:
            stopped = True
        finally:
            print("-" * 58, flush=True)
            for item in sessions:
                sch = item["scheduler"]
                print(
                    f"[{sch.name}] 成功 {sch.sent_count} 条 / 失败 {sch.fail_count} 次",
                    flush=True,
                )
            print("机器人已停止（浏览器不会被关闭）", flush=True)

    return not stopped


def run_probe(cfg=None):
    """
    真实账号体检：只连接、只检查，不发送任何消息。

    用真实视频号测试时先跑这个：确认机器人能看到直播间页面、能定位到输入框，
    再关掉演练模式真发，避免一上来就在直播间里乱发。
    """
    cfg = cfg or config.load_config()
    errors, warnings = config.validate_config(cfg)
    for w in warnings:
        print(f"[!!] {w}", flush=True)
    if errors:
        for e in errors:
            print(f"[XX] {e}", flush=True)
        return False

    print("=" * 58, flush=True)
    print("真实账号体检（只检查，不发送任何消息）", flush=True)
    print("=" * 58, flush=True)

    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        print(f"[XX] Playwright 未安装：{e}", flush=True)
        print("     请先双击运行「安装环境.bat」", flush=True)
        return False

    from sender import find_input

    ok_count = 0
    pairs = config.enabled_accounts(cfg)
    with sync_playwright() as p:
        for index, acc in pairs:
            name = acc.get("name")
            port = acc.get("cdp_port")
            print(flush=True)
            print(f"--- {name}（端口 {port}）---", flush=True)

            browser, page = connect_account(p, acc, timeout_ms=5000)
            if page is None:
                print("  [FAIL] 连不上。检查：Chrome 是否已启动、是否已登录视频号", flush=True)
                continue

            try:
                url = page.url
            except Exception:
                url = "(读取失败)"
            try:
                title = page.title()
            except Exception:
                title = "(读取失败)"
            print(f"  页面：{title}", flush=True)
            print(f"  地址：{url}", flush=True)

            on_channels = "channels.weixin.qq.com" in (url or "")
            print(f"  {'[OK]' if on_channels else '[!!]'} 是否在视频号页面", flush=True)
            if not on_channels:
                print("       建议：在这个 Chrome 里手动进入直播间，或填 room_url 让机器人自动打开", flush=True)

            box = None
            try:
                box = find_input(page)
            except Exception as e:
                print(f"  查找输入框异常：{e}", flush=True)
            if box is None:
                print("  [FAIL] 没找到输入框。确认当前页面停在直播间，且评论框已加载出来", flush=True)
                continue

            print("  [OK] 已找到输入框，可以发送", flush=True)
            ok_count += 1

    print(flush=True)
    print("=" * 58, flush=True)
    print(f"体检结果：{ok_count}/{len(pairs)} 个账号可用", flush=True)
    if ok_count == len(pairs) and pairs:
        print("下一步：把 dry_run 改回 false，先用 1 个账号、间隔 300 秒以上试发", flush=True)
    else:
        print("有账号不可用，先按上面的提示处理，不要急着真发", flush=True)
    print("=" * 58, flush=True)
    return ok_count > 0


def main():
    args = sys.argv[1:]
    try:
        if "--probe" in args:
            run_probe()
        else:
            run_bot()
    except Exception as e:
        print(f"[XX] 启动失败：{e}", flush=True)
    print(flush=True)
    try:
        input("按回车键退出...")
    except Exception:
        pass


if __name__ == "__main__":
    main()
