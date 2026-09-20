#!/bin/bash
# 微信视频号机器人 - 自检（不需要真实视频号账号）
# 用法：bash 自检.sh
cd "$(dirname "$0")"

PY=python3
command -v "$PY" >/dev/null 2>&1 || PY=python
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "[XX] 没有检测到 Python，请先运行 安装环境.sh"
  exit 1
fi

if ! "$PY" -c "import playwright" 2>/dev/null; then
  echo "[XX] 还没安装 Playwright，请先运行 安装环境.sh"
  exit 1
fi

"$PY" app/selftest.py

echo
echo "========================================"
echo " 全部 PASS 才能放心交付"
echo "========================================"
echo
