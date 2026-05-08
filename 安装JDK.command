#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ARCH="$(uname -m)"
JDK_DIR="$SCRIPT_DIR/jdk"
ARCHIVE_PATH="$SCRIPT_DIR/temurin-jdk.tar.gz"

if [ "$ARCH" = "arm64" ]; then
  API_URL="https://aka.ms/download-jdk/microsoft-jdk-21.0.10-macos-aarch64.tar.gz"
elif [ "$ARCH" = "x86_64" ]; then
  API_URL="https://aka.ms/download-jdk/microsoft-jdk-21.0.10-macos-x64.tar.gz"
else
  echo "不支持的架构：$ARCH"
  read -r "?按回车键结束..."
  exit 1
fi

cleanup() {
  rm -f "$ARCHIVE_PATH"
}
trap cleanup EXIT

echo "正在下载 JDK..."
curl -L --fail --retry 1 --connect-timeout 15 --progress-bar "$API_URL" -o "$ARCHIVE_PATH"

echo
echo "正在安装到项目目录..."
rm -rf "$JDK_DIR"
mkdir -p "$JDK_DIR"
tar -xzf "$ARCHIVE_PATH" -C "$SCRIPT_DIR"

EXTRACTED_DIR="$(find "$SCRIPT_DIR" -maxdepth 1 -type d -name 'jdk-*' | head -n 1)"
if [ -z "$EXTRACTED_DIR" ]; then
  echo "JDK 解压失败，未找到目录。"
  read -r "?按回车键结束..."
  exit 1
fi

mv "$EXTRACTED_DIR/Contents" "$JDK_DIR/"
rmdir "$EXTRACTED_DIR" 2>/dev/null || true

if [ ! -x "$JDK_DIR/Contents/Home/bin/java" ]; then
  echo "JDK 安装失败，未找到 java 可执行文件。"
  read -r "?按回车键结束..."
  exit 1
fi

echo
echo "安装完成：$JDK_DIR/Contents/Home/bin/java"
echo "现在可以重新打开工具继续安装或解析 AAB。"
read -r "?按回车键结束..."
