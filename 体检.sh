#!/bin/bash
# 微信视频号机器人 - 真实账号体检（只连接、只检查，不会发送任何消息）
# 用法：先运行 启动Chrome.sh 并登录进直播间，再运行本脚本
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

echo "========================================"
echo "   真实账号体检"
echo "   只连接、只检查，不会发送任何消息"
echo "========================================"
echo "   用法："
echo "   1. 先运行 启动Chrome.sh"
echo "   2. 在 Chrome 里登录视频号、进入直播间"
echo "   3. 再运行本脚本"
echo "========================================"
echo

"$PY" app/main.py --probe

echo
echo "========================================"
echo "   体检结束"
echo "========================================"
echo
