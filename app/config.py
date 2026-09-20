# -*- coding: utf-8 -*-
"""
配置读写与路径解析。

原则：所有路径都由「程序自身所在目录」推导，不写死任何盘符 / 用户名。
因此客户把整个文件夹放到 C 盘、D 盘、桌面、U 盘都能直接跑。
"""
from __future__ import annotations

import copy
import json
import os
import sys

# ---------------------------------------------------------------- 路径解析
if getattr(sys, "frozen", False):
    # 打包成 exe 后：程序目录 = exe 所在目录
    APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    # 源码运行：本文件在 <APP_DIR>/app/config.py
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

APP_DIRNAME = "app"
CONFIG_DIR = os.path.join(APP_DIR, "config")
PROFILE_DIR = os.path.join(APP_DIR, "chrome_profiles")
LOG_DIR = os.path.join(APP_DIR, "logs")
CONFIG_FILE = os.path.join(CONFIG_DIR, "accounts.json")


DEFAULT_CONFIG = {
    "chrome_path": "",          # 留空 = 自动查找 Chrome
    "dry_run": False,           # True = 只打印不真正发送（调试用）
    "jitter_seconds": 0,        # 发送间隔随机抖动，0 表示不抖动
    "reconnect_seconds": 30,    # 掉线后每隔多少秒重试连接
    "gap_seconds": 2.5,         # 同一轮内，每条话术之间留的间隔（秒）
    "accounts": [
        {
            "name": "视频号A",
            "enabled": True,
            "cdp_port": 9222,
            "interval": 300,
            "room_url": "",
            "send_all": True,    # True = 每轮把全部话术依次发完；False = 每条按间隔轮流发
            "messages": [
                "欢迎大家来到直播间～",
                "有问题可以直接留言咨询哦～",
                "感谢大家的关注和支持～",
            ],
        },
        {
            "name": "视频号B",
            "enabled": True,
            "cdp_port": 9223,
            "interval": 300,
            "room_url": "",
            "send_all": True,
            "messages": [
                "欢迎新朋友来到直播间～",
                "大家有问题可以直接留言哦～",
            ],
        },
        {
            "name": "视频号C",
            "enabled": False,
            "cdp_port": 9224,
            "interval": 600,
            "room_url": "",
            "send_all": True,
            "messages": [
                "晚上好，欢迎来到直播间～",
                "感谢大家来到直播间～",
            ],
        },
    ],
}


def ensure_dirs() -> None:
    """确保 config / chrome_profiles / logs 三个目录存在。"""
    for d in (CONFIG_DIR, PROFILE_DIR, LOG_DIR):
        os.makedirs(d, exist_ok=True)


def _fill_defaults(cfg: dict) -> dict:
    """用默认配置补齐缺失字段（兼容旧版本配置文件）。"""
    base = copy.deepcopy(DEFAULT_CONFIG)
    if not isinstance(cfg, dict):
        return base

    for key in ("chrome_path", "dry_run", "jitter_seconds", "reconnect_seconds", "gap_seconds"):
        if key in cfg and cfg[key] not in (None, ""):
            base[key] = cfg[key]

    accounts = cfg.get("accounts")
    if isinstance(accounts, list) and accounts:
        result = []
        for idx, acc in enumerate(accounts):
            if not isinstance(acc, dict):
                continue
            tpl = copy.deepcopy(
                DEFAULT_CONFIG["accounts"][idx % len(DEFAULT_CONFIG["accounts"])]
            )
            merged = copy.deepcopy(tpl)
            merged.update({k: v for k, v in acc.items() if v is not None})
            merged.setdefault("enabled", True)
            merged.setdefault("room_url", "")
            merged.setdefault("send_all", True)
            merged.setdefault("messages", [])
            result.append(merged)
        base["accounts"] = result
    return base


def load_config() -> dict:
    """读取配置；文件不存在则生成默认配置。"""
    ensure_dirs()
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return copy.deepcopy(DEFAULT_CONFIG)

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception as e:
        print(f"[!!] 配置文件读取失败（{e}），已使用默认配置")
        return copy.deepcopy(DEFAULT_CONFIG)

    return _fill_defaults(raw)


def save_config(cfg: dict) -> bool:
    ensure_dirs()
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[!!] 配置文件保存失败：{e}")
        return False


def enabled_accounts(cfg: dict):
    """返回 [(原始下标, 账号dict), ...]，只含 enabled 的账号。"""
    out = []
    for idx, acc in enumerate(cfg.get("accounts", [])):
        if acc.get("enabled", True):
            out.append((idx, acc))
    return out


def profile_dir(account: dict, index: int) -> str:
    """账号对应的 Chrome 用户数据目录（保存登录状态）。"""
    name = account.get("profile") or f"account_{index + 1:02d}"
    return os.path.join(PROFILE_DIR, name)


def validate_config(cfg: dict):
    """校验配置，返回 (错误列表, 警告列表)。错误会阻止运行。"""
    errors, warnings = [], []
    accounts = cfg.get("accounts") or []
    if not accounts:
        errors.append("没有配置任何视频号账号")
        return errors, warnings

    seen_ports = {}
    for idx, acc in enumerate(accounts):
        tag = acc.get("name") or f"第{idx + 1}个账号"

        if not acc.get("name"):
            errors.append(f"第{idx + 1}个账号缺少名称")
        try:
            port = int(acc.get("cdp_port", 0))
        except (TypeError, ValueError):
            errors.append(f"[{tag}] 端口不是数字：{acc.get('cdp_port')}")
            port = 0
        if port < 1 or port > 65535:
            errors.append(f"[{tag}] 端口非法：{port}")
        if port in seen_ports:
            errors.append(f"[{tag}] 端口 {port} 与「{seen_ports[port]}」重复")
        seen_ports[port] = tag

        try:
            interval = float(acc.get("interval", 0))
        except (TypeError, ValueError):
            errors.append(f"[{tag}] 间隔不是数字：{acc.get('interval')}")
            interval = 0
        if interval < 10:
            warnings.append(f"[{tag}] 间隔 {interval}s 过短（建议 >= 60s，容易被平台限制）")

        msgs = [m for m in (acc.get("messages") or []) if str(m).strip()]
        if not msgs:
            warnings.append(f"[{tag}] 没有配置任何发送文案（启用后不会发送）")

    return errors, warnings
