#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ZIP_PATH="$SCRIPT_DIR/platform-tools-latest-darwin.zip"
TARGET_DIR="$SCRIPT_DIR/platform-tools"
DOWNLOAD_URL="https://dl.google.com/android/repository/platform-tools-latest-darwin.zip"

cleanup() {
  rm -f "$ZIP_PATH"
}
trap cleanup EXIT

echo "正在下载 Android Platform Tools..."
curl -L --fail --progress-bar "$DOWNLOAD_URL" -o "$ZIP_PATH"

echo
echo "正在解压到项目目录..."
rm -rf "$TARGET_DIR"
unzip -q "$ZIP_PATH" -d "$SCRIPT_DIR"
chmod +x "$TARGET_DIR/adb"

echo
echo "安装完成：$TARGET_DIR/adb"
echo "现在可以重新双击“一键启动.command”了。"
read -r "?按回车键结束..."
