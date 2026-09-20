#!/bin/bash
# 微信视频号机器人 - 环境安装（macOS / Linux）
# 用法：在终端里 cd 到本文件夹，执行  bash 安装环境.sh
#      （也可先 chmod +x 安装环境.sh，之后直接 ./安装环境.sh）

cd "$(dirname "$0")"

PY=python3
command -v "$PY" >/dev/null 2>&1 || PY=python
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "[XX] 没有检测到 Python，请先安装 Python 3.10+"
  echo "     macOS:  brew install python   或去 https://www.python.org/downloads/"
  echo "     Linux:  sudo apt install python3 python3-pip"
  exit 1
fi

echo "========================================"
echo "   微信视频号机器人 - 环境安装"
echo "========================================"
echo
echo "[1/2] Python 版本："
"$PY" --version
echo

echo "[2/2] 正在安装 Playwright，请耐心等待..."
"$PY" -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
  echo
  echo "[XX] 安装失败，请把上面的红色错误发给我"
  exit 1
fi

echo
echo "========================================"
echo "   安装完成"
echo "========================================"
echo
echo "说明：不会下载浏览器内核，机器人连接的是你自己的 Chrome。"
echo "      如果是 macOS，运行时若提示缺少系统依赖，可另执行："
echo "        $PY -m playwright install-deps"
echo
echo "下一步：运行 配置账号.sh 打开图形窗口"
echo "========================================"
echo
