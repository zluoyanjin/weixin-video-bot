#!/bin/bash
# 微信视频号机器人 - 打开配置窗口（macOS / Linux）
# 用法：bash 配置账号.sh
cd "$(dirname "$0")"

PY=python3
command -v "$PY" >/dev/null 2>&1 || PY=python
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "[XX] 没有检测到 Python，请先运行 安装环境.sh"
  exit 1
fi

echo "========================================"
echo " 正在打开【配置账号】图形窗口..."
echo " 弹出的【图形窗口】才是操作界面（改账号/文案/端口）"
echo " 这个终端窗口不要关，关掉图形窗口它会自动结束"
echo "========================================"
echo

"$PY" app/gui.py

echo
if [ $? -ne 0 ]; then
  echo "[XX] 配置窗口异常退出，请查看上方错误信息。"
  echo "      若提示 No module named '_tkinter'，请安装 Tk："
  echo "      macOS(python.org 版自带)；brew 版执行  brew install python-tk"
  echo "      Linux 执行  sudo apt install python3-tk"
else
  echo "配置窗口已关闭。"
fi
