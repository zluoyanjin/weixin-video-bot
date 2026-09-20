# -*- coding: utf-8 -*-
"""
发送调度：每个账号一个 Scheduler。

两种模式（由账号的 send_all 控制）：
  send_all=True （默认）：每次到点，把「全部话术」按顺序一条条依次发完，
                         然后等 interval 秒进入下一轮。即「到点把每一行都发一遍」。
  send_all=False：每次到点只发一条，按列表顺序循环（话术轮播）。

每条之间留 gap_between 秒，避免瞬间连发被平台限流。
"""
from __future__ import annotations

import random
import time


class Scheduler:
    def __init__(
        self,
        name,
        page,
        messages,
        interval,
        jitter=0,
        start_delay=0,
        gap_between=2.5,
        send_all=True,
    ):
        self.name = name
        self.page = page
        self.messages = [m for m in (messages or []) if str(m).strip()]
        self.interval = max(float(interval or 0), 1.0)
        self.jitter = max(float(jitter or 0), 0.0)
        self.gap_between = max(float(gap_between or 0), 0.5)
        self.send_all = bool(send_all)

        self.index = 0
        self.sent_count = 0
        self.fail_count = 0
        # 首次发送前的等待，避免所有账号在同一秒集体发言
        self.next_time = time.time() + max(float(start_delay or 0), 0.0)

    # ------------------------------------------------------------------
    def get_next_message(self):
        """轮流模式用：取出下一条话术并推进下标。"""
        if not self.messages:
            return None
        message = self.messages[self.index % len(self.messages)]
        self.index = (self.index + 1) % len(self.messages)
        return message

    def _delay(self):
        base = self.interval
        if self.jitter > 0:
            base += random.uniform(-self.jitter, self.jitter)
        return max(base, 1.0)

    def replace_page(self, page):
        """断线重连后换掉 page 对象。"""
        self.page = page

    # ------------------------------------------------------------------
    def check(self, sender):
        """到点则发送；未到点直接返回。sender(page, text) -> bool"""
        now = time.time()
        if now < self.next_time:
            return

        if not self.messages:
            self.next_time = time.time() + self._delay()
            return

        if self.send_all:
            total = len(self.messages)
            ok = 0
            for i, msg in enumerate(self.messages):
                print(f"[{self.name}] 发送第 {i + 1}/{total} 条：{msg}", flush=True)
                success = False
                try:
                    success = bool(sender(self.page, msg))
                except Exception as e:
                    print(f"[{self.name}] 发送异常：{e}", flush=True)
                    success = False
                if success:
                    self.sent_count += 1
                    ok += 1
                else:
                    self.fail_count += 1
                # 每条之间留一点间隔，避免瞬间连发被平台限流
                if i < total - 1:
                    time.sleep(self.gap_between)
            print(f"[{self.name}] 本轮发送完成：成功 {ok}/{total} 条", flush=True)
        else:
            # 轮流模式：每次只发一条
            message = self.get_next_message()
            if not message:
                self.next_time = time.time() + self._delay()
                return
            success = False
            try:
                success = bool(sender(self.page, message))
            except Exception as e:
                print(f"[{self.name}] 发送异常：{e}", flush=True)
                success = False
            if success:
                self.sent_count += 1
                print(f"[{self.name}] 发送成功（累计 {self.sent_count} 条）", flush=True)
            else:
                self.fail_count += 1
                print(f"[{self.name}] 发送失败（累计失败 {self.fail_count} 次）", flush=True)

        self.next_time = time.time() + self._delay()
