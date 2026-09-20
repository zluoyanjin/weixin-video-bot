#!/bin/bash
# 微信视频号机器人 - 启动 Chrome（macOS / Linux）
# 用法：bash 启动Chrome.sh
cd "$(dirname "$0")"

PY=python3
command -v "$PY" >/dev/null 2>&1 || PY=python
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "[XX] 没有检测到 Python，请先运行 安装环境.sh"
  exit 1
fi

"$PY" app/chrome.py

echo
echo "========================================"
echo " 请在每个 Chrome 窗口中："
echo " 1. 登录对应的视频号"
echo " 2. 进入要发言的直播间"
echo " 然后运行 启动机器人.sh"
echo "========================================"
echo
