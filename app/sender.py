# -*- coding: utf-8 -*-
"""
消息发送：定位直播间输入框 -> 输入 -> 回车 -> 校验是否真的发出去。
"""
from __future__ import annotations

import time

# 候选选择器，按优先级排列（视频号直播间评论框多为 contenteditable div）
INPUT_SELECTORS = [
    "div[contenteditable='true']",
    "[contenteditable='true']",
    "textarea",
    "input[type='text']",
]

SEND_BUTTON_SELECTORS = [
    "button:has-text('发送')",
    "div[role='button']:has-text('发送')",
    "span:has-text('发送')",
]


def _is_usable(item) -> bool:
    try:
        if not item.is_visible():
            return False
        if not item.is_enabled():
            return False
        box = item.bounding_box()
        if not box or box.get("width", 0) < 20 or box.get("height", 0) < 10:
            return False
        return True
    except Exception:
        return False


def find_input(page):
    """找到最可能可用的输入框。"""
    for selector in INPUT_SELECTORS:
        try:
            locator = page.locator(selector)
            count = locator.count()
        except Exception:
            continue
        for i in range(count):
            item = locator.nth(i)
            if _is_usable(item):
                return item
    return None


def _read_text(item) -> str:
    try:
        return (item.input_value() or "").strip()
    except Exception:
        pass
    try:
        return (item.inner_text() or "").strip()
    except Exception:
        return ""


def _click_send_button(page) -> bool:
    for selector in SEND_BUTTON_SELECTORS:
        try:
            locator = page.locator(selector)
            count = locator.count()
        except Exception:
            continue
        for i in range(count):
            button = locator.nth(i)
            try:
                if button.is_visible() and button.is_enabled():
                    button.click()
                    return True
            except Exception:
                continue
    return False


def send_message(page, text) -> bool:
    """发送一条消息，成功返回 True。"""
    if text is None:
        return False
    text = str(text).strip()
    if not text:
        return False

    try:
        input_box = find_input(page)
        if input_box is None:
            print("[XX] 找不到消息输入框（页面可能已离开直播间）", flush=True)
            return False

        input_box.click()
        time.sleep(0.2)

        # 清空旧内容
        try:
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
        except Exception:
            pass
        time.sleep(0.2)

        # 逐行输入：行内换行用 Shift+Enter（不发送），最后整条用 Enter 发送。
        # 注意：keyboard.type 遇到 \n 会被当成回车触发发送，所以必须拆行处理。
        lines = text.split("\n")
        sent_all = True
        for i, seg in enumerate(lines):
            try:
                page.keyboard.type(seg, delay=25)
            except Exception:
                try:
                    page.keyboard.type(seg)
                except Exception:
                    try:
                        input_box.fill(text)
                    except Exception:
                        pass
                    sent_all = False
                    break
            if i < len(lines) - 1:
                # 行与行之间插入换行（不发送）
                try:
                    page.keyboard.press("Shift+Enter")
                except Exception:
                    pass
                time.sleep(0.12)
        time.sleep(0.4)

        # 回车发送（整条消息）
        try:
            page.keyboard.press("Enter")
        except Exception:
            pass
        time.sleep(0.8)

        # 校验：输入框还留着原文说明没发出去
        try:
            remain = _read_text(input_box)
        except Exception:
            remain = ""
        if remain and remain == text:
            if _click_send_button(page):
                time.sleep(0.6)
                try:
                    remain2 = _read_text(input_box)
                except Exception:
                    remain2 = ""
                if remain2 != text:
                    return True
            print("[XX] 回车与发送按钮都无效，本次未发送", flush=True)
            return False

        return True

    except Exception as e:
        print(f"[XX] 发送异常：{e}", flush=True)
        return False
