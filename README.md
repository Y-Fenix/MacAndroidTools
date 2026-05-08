# MacAndroidTools

MacAndroidTools is a macOS desktop helper for Android/iOS test workflows. It can start from source with Python, download required Android tools, and package itself as a macOS app with PyInstaller.

## Quick Start

1. Install Python 3 on macOS.
2. Double-click `一键启动.command`.
3. If ADB is missing, double-click `安装ADB.command`.
4. If Bundletool is missing, double-click `安装Bundletool.command`.
5. If JDK is missing for AAB parsing/conversion, double-click `安装JDK.command`.

## Build App

Double-click `一键打包.command`.

The packaged app will be generated under `dist/AndroidTools.app`.

## Repository Contents

This repository keeps source code, launch scripts, icons, and build requirements only.

Generated files and downloaded runtime dependencies such as `.venv/`, `dist/`, `build/`, `logs/`, `platform-tools/`, `jdk/`, and Bundletool jars are intentionally ignored.
