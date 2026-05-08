#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_JAR="$SCRIPT_DIR/bundletool-all-1.18.3.jar"
TMP_JAR="$SCRIPT_DIR/bundletool-all-1.18.3.jar.download"

URLS=(
  "https://dl.google.com/dl/android/maven2/com/android/tools/build/bundletool/1.18.3/bundletool-1.18.3.jar"
  "https://github.com/google/bundletool/releases/download/1.18.3/bundletool-all-1.18.3.jar"
)

cleanup() {
  rm -f "$TMP_JAR"
}
trap cleanup EXIT

for url in "${URLS[@]}"; do
  echo "尝试下载：$url"
  if curl -L --fail --retry 3 --connect-timeout 20 --progress-bar "$url" -o "$TMP_JAR"; then
    mv "$TMP_JAR" "$TARGET_JAR"
    echo
    echo "安装完成：$TARGET_JAR"
    read -r "?按回车键结束..."
    exit 0
  fi
  echo
  echo "下载失败，切换下一个地址..."
done

echo
echo "安装失败。"
echo "你也可以手动下载后放到这个目录：$TARGET_JAR"
read -r "?按回车键结束..."
exit 1
