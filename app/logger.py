# -*- coding: utf-8 -*-
"""
日志：同时输出到控制台和 logs/YYYY-MM-DD.log。

刻意不使用 emoji —— Windows 中文控制台（GBK）打印 emoji 会直接抛
UnicodeEncodeError 导致程序崩溃。
"""
from __future__ import annotations

import os
import sys
import threading
import time

import config


_LEVELS = {"DEBUG": 10, "INFO": 20, "WARN": 30, "ERROR": 40}


class Logger:
    def __init__(self, log_dir: str | None = None, level: str = "INFO", echo=True):
        self.log_dir = log_dir or config.LOG_DIR
        self.level = _LEVELS.get(level, 20)
        self.echo = echo
        self._lock = threading.Lock()
        self._file = None
        self._day = ""
        try:
            os.makedirs(self.log_dir, exist_ok=True)
        except Exception:
            pass

    # ------------------------------------------------------------ 内部
    def _rotate(self):
        day = time.strftime("%Y-%m-%d")
        if day != self._day or self._file is None:
            if self._file:
                try:
                    self._file.close()
                except Exception:
                    pass
            self._day = day
            try:
                path = os.path.join(self.log_dir, f"{day}.log")
                self._file = open(path, "a", encoding="utf-8")
            except Exception:
                self._file = None

    def _write(self, line: str):
        with self._lock:
            self._rotate()
            if self.echo:
                try:
                    print(line, flush=True)
                except Exception:
                    pass
            if self._file:
                try:
                    self._file.write(line + "\n")
                    self._file.flush()
                except Exception:
                    pass

    # ------------------------------------------------------------ 对外
    def log(self, msg, level: str = "INFO"):
        if _LEVELS.get(level, 20) < self.level:
            return
        stamp = time.strftime("%H:%M:%S")
        prefix = {"DEBUG": "[--]", "INFO": "[OK]", "WARN": "[!!]", "ERROR": "[XX]"}.get(level, "[OK]")
        self._write(f"{stamp} {prefix} {msg}")

    def info(self, msg):
        self.log(msg, "INFO")

    def warn(self, msg):
        self.log(msg, "WARN")

    def error(self, msg):
        self.log(msg, "ERROR")

    def debug(self, msg):
        self.log(msg, "DEBUG")


# 全局默认 logger（各模块直接 from logger import LOG）
LOG = Logger()


def write_stdout(msg: str):
    """兼容旧调用：直接写一行。"""
    LOG.info(msg)
