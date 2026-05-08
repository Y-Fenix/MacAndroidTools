#!/bin/zsh
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON_BIN="$(command -v python3 || true)"

pause_on_error() {
  local exit_code="$1"
  if [ "$exit_code" -ne 0 ]; then
    echo
    echo "启动失败，按回车键关闭窗口..."
    read
  fi
  exit "$exit_code"
}

if [ -z "$PYTHON_BIN" ]; then
  echo "未找到 python3，请先安装 Python 3。"
  pause_on_error 1
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "正在创建虚拟环境..."
  "$PYTHON_BIN" -m venv "$VENV_DIR" || pause_on_error 1
fi

PYTHON_IN_VENV="$VENV_DIR/bin/python"

if [ ! -x "$PYTHON_IN_VENV" ]; then
  echo "虚拟环境损坏，正在重建..."
  rm -rf "$VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR" || pause_on_error 1
fi

echo "正在检查基础环境..."
"$PYTHON_IN_VENV" -c "import tkinter" >/dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "当前 Python 缺少 tkinter，无法启动图形界面。"
  pause_on_error 1
fi

if [ ! -x "$SCRIPT_DIR/platform-tools/adb" ] && ! command -v adb >/dev/null 2>&1; then
  echo "提示：当前未检测到 adb。"
  echo "请先双击运行：$SCRIPT_DIR/安装ADB.command"
  echo
fi

cd "$SCRIPT_DIR" || pause_on_error 1
exec "$PYTHON_IN_VENV" "$SCRIPT_DIR/androidtools.py"
