#!/usr/bin/env python3
"""
macOS 专用 Android 工具箱。
支持 Android/iOS 日志提取、截图、录屏、APK 安装、AAB 转 APKS 安装，以及 APK/AAB/APKS/IPA 信息解析。
"""

from __future__ import annotations

import json
import os
import platform
import plistlib
import re
import signal
import ssl
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path
from shutil import which

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, simpledialog, ttk

    TK_IMPORT_ERROR: Exception | None = None
except Exception as exc:  # pragma: no cover
    tk = None  # type: ignore[assignment]
    filedialog = messagebox = simpledialog = ttk = None  # type: ignore[assignment]
    TK_IMPORT_ERROR = exc


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        executable = Path(sys.executable).resolve()
        if ".app/Contents/MacOS" in executable.as_posix():
            return executable.parents[3]
        return executable.parent
    return Path(__file__).resolve().parent


BASE_DIR = get_base_dir()


def get_writable_data_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path.home() / "Library" / "Application Support" / "AndroidTools"
    return BASE_DIR


DATA_DIR = get_writable_data_dir()
SCREENSHOT_DIR = BASE_DIR / "screenshot"
RECORD_DIR = BASE_DIR / "movies"
APKS_OUTPUT_DIR = BASE_DIR / "output"
LOG_DIR = BASE_DIR / "logs"
REMOTE_RECORD_PATH = "/sdcard/screenrecord_tmp.mp4"

TOOLKIT_DIR = BASE_DIR.parent / "【aab_apks】"

JAR_NAME = "bundletool-all-1.18.3.jar"
BUNDLETOOL_DOWNLOAD_URLS = [
    "https://dl.google.com/dl/android/maven2/com/android/tools/build/bundletool/1.18.3/bundletool-1.18.3.jar",
    "https://github.com/google/bundletool/releases/download/1.18.3/bundletool-all-1.18.3.jar",
]
BUNDLETOOL_MAIN_CLASS = "com.android.tools.build.bundletool.BundleToolMain"
BUNDLETOOL_LIB_URLS = {
    "aapt2-proto-7.3.0-alpha07-8248216.jar": "https://dl.google.com/dl/android/maven2/com/android/tools/build/aapt2-proto/7.3.0-alpha07-8248216/aapt2-proto-7.3.0-alpha07-8248216.jar",
    "auto-value-annotations-1.6.2.jar": "https://repo.maven.apache.org/maven2/com/google/auto/value/auto-value-annotations/1.6.2/auto-value-annotations-1.6.2.jar",
    "protobuf-java-util-3.22.3.jar": "https://repo.maven.apache.org/maven2/com/google/protobuf/protobuf-java-util/3.22.3/protobuf-java-util-3.22.3.jar",
    "guava-32.0.1-jre.jar": "https://repo.maven.apache.org/maven2/com/google/guava/guava/32.0.1-jre/guava-32.0.1-jre.jar",
    "error_prone_annotations-2.18.0.jar": "https://repo.maven.apache.org/maven2/com/google/errorprone/error_prone_annotations/2.18.0/error_prone_annotations-2.18.0.jar",
    "protobuf-java-3.22.3.jar": "https://repo.maven.apache.org/maven2/com/google/protobuf/protobuf-java/3.22.3/protobuf-java-3.22.3.jar",
    "dagger-2.28.3.jar": "https://repo.maven.apache.org/maven2/com/google/dagger/dagger/2.28.3/dagger-2.28.3.jar",
    "javax.inject-1.jar": "https://repo.maven.apache.org/maven2/javax/inject/javax.inject/1/javax.inject-1.jar",
    "jose4j-0.9.5.jar": "https://repo.maven.apache.org/maven2/org/bitbucket/b_c/jose4j/0.9.5/jose4j-0.9.5.jar",
    "slf4j-api-1.7.30.jar": "https://repo.maven.apache.org/maven2/org/slf4j/slf4j-api/1.7.30/slf4j-api-1.7.30.jar",
    "failureaccess-1.0.1.jar": "https://repo.maven.apache.org/maven2/com/google/guava/failureaccess/1.0.1/failureaccess-1.0.1.jar",
    "listenablefuture-9999.0-empty-to-avoid-conflict-with-guava.jar": "https://repo.maven.apache.org/maven2/com/google/guava/listenablefuture/9999.0-empty-to-avoid-conflict-with-guava/listenablefuture-9999.0-empty-to-avoid-conflict-with-guava.jar",
    "jsr305-3.0.2.jar": "https://repo.maven.apache.org/maven2/com/google/code/findbugs/jsr305/3.0.2/jsr305-3.0.2.jar",
    "checker-qual-3.33.0.jar": "https://repo.maven.apache.org/maven2/org/checkerframework/checker-qual/3.33.0/checker-qual-3.33.0.jar",
    "j2objc-annotations-2.8.jar": "https://repo.maven.apache.org/maven2/com/google/j2objc/j2objc-annotations/2.8/j2objc-annotations-2.8.jar",
    "gson-2.8.9.jar": "https://repo.maven.apache.org/maven2/com/google/code/gson/gson/2.8.9/gson-2.8.9.jar",
}
BUNDLETOOL_EXTRA_LIB_URLS = {
    "kotlin-stdlib-1.9.25.jar": "https://repo.maven.apache.org/maven2/org/jetbrains/kotlin/kotlin-stdlib/1.9.25/kotlin-stdlib-1.9.25.jar",
    "kotlin-stdlib-jdk7-1.9.25.jar": "https://repo.maven.apache.org/maven2/org/jetbrains/kotlin/kotlin-stdlib-jdk7/1.9.25/kotlin-stdlib-jdk7-1.9.25.jar",
    "kotlin-stdlib-jdk8-1.9.25.jar": "https://repo.maven.apache.org/maven2/org/jetbrains/kotlin/kotlin-stdlib-jdk8/1.9.25/kotlin-stdlib-jdk8-1.9.25.jar",
    "annotations-13.0.jar": "https://repo.maven.apache.org/maven2/org/jetbrains/annotations/13.0/annotations-13.0.jar",
}
AAPT2_VERSION = "7.3.0-alpha07-8248216"
AAPT2_JAR_URL = f"https://dl.google.com/dl/android/maven2/com/android/tools/build/aapt2/{AAPT2_VERSION}/aapt2-{AAPT2_VERSION}-osx.jar"

KEYSTORE_NAME = "debug.keystore"
KEY_ALIAS = "androiddebugkey"
KEY_PASS = "android"
ADVERTISING_ID_RE = re.compile(
    r"\b[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\b"
)
ZERO_ADVERTISING_ID = "00000000-0000-0000-0000-000000000000"

UI_BG = "#F4F6FA"
UI_PANEL = "#FFFFFF"
UI_PANEL_ALT = "#F8FAFC"
UI_TEXT = "#101828"
UI_SUBTEXT = "#667085"
UI_MUTED = "#8A94A6"
UI_BORDER_SOFT = "#E7EBF1"
UI_CONSOLE_BG = "#0E1726"
UI_CONSOLE_TEXT = "#D7DEE8"
STATUS_SUCCESS = "#16824D"
STATUS_ERROR = "#C0362C"
BLUE = "#1D4ED8"
BLUE_HOVER = "#2563EB"
BLUE_PRESSED = "#1E40AF"
DANGER = "#DC2626"
DANGER_HOVER = "#EF4444"
DANGER_PRESSED = "#B91C1C"
SOFT_BLUE = "#E8F0FF"
SOFT_BLUE_HOVER = "#DCE8FF"
SOFT_BLUE_PRESSED = "#C7D8FF"
GREEN = "#E5F6ED"
GREEN_HOVER = "#D5F0E2"
GREEN_PRESSED = "#BFE5D0"
GREEN_TEXT = "#17663A"
TEAL = "#0F766E"
TEAL_HOVER = "#0D9488"
TEAL_PRESSED = "#115E59"

LOG_MODULES = {
    "app_log": "日志与 IDFA",
    "screenshot": "截图",
    "record": "录屏",
    "firebase": "Firebase DebugView",
    "package": "安装包",
}
ACTIVE_LOG_STYLES = {
    "app_log": "ActiveLogApp.TLabel",
    "screenshot": "ActiveLogScreenshot.TLabel",
    "record": "ActiveLogRecord.TLabel",
    "firebase": "ActiveLogFirebase.TLabel",
    "package": "ActiveLogPackage.TLabel",
}
record_proc: subprocess.Popen | None = None
record_start: datetime | None = None
timer_job: str | None = None
auto_recording = False
segment_index = 0
current_segment_pulled = True
recorded_files: list[Path] = []
last_record_log_second = -1
record_progress_log_index: int | None = None
status_var: tk.StringVar | None = None
status_label: ttk.Label | None = None
record_button: ttk.Button | None = None
adb_path: str | None = None
selected_file_var: tk.StringVar | None = None
firebase_file_var: tk.StringVar | None = None
firebase_package_var: tk.StringVar | None = None
install_log_widget: tk.Text | None = None
active_log_var: tk.StringVar | None = None
active_log_label: ttk.Label | None = None
current_log_module = "package"
module_log_history: dict[str, list[str]] = {key: [] for key in LOG_MODULES}
apk_button: ttk.Button | None = None
aab_button: ttk.Button | None = None
parse_button: ttk.Button | None = None
firebase_button: ttk.Button | None = None
firebase_debug_package = ""
ui_root: tk.Tk | None = None


def get_resource_dirs() -> list[Path]:
    dirs: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path | None) -> None:
        if path is None:
            return
        resolved = path.resolve()
        if resolved.exists() and resolved not in seen:
            seen.add(resolved)
            dirs.append(resolved)

    add(BASE_DIR)
    if getattr(sys, "frozen", False):
        add(Path(sys.executable).resolve().parent)
        add(Path(sys.executable).resolve().parent.parent / "Resources")
        if getattr(sys, "_MEIPASS", ""):
            add(Path(getattr(sys, "_MEIPASS")))
    return dirs


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def show_startup_error(title: str, message: str) -> None:
    if TK_IMPORT_ERROR is None and tk is not None and messagebox is not None:
        try:
            bootstrap_root = tk.Tk()
            bootstrap_root.withdraw()
            messagebox.showerror(title, message)
            bootstrap_root.destroy()
            return
        except Exception:
            pass
    print(f"{title}: {message}", file=sys.stderr)


def resource_file(name: str) -> Path | None:
    for resource_dir in get_resource_dirs():
        candidate = resource_dir / name
        if candidate.is_file():
            return candidate
    return None


def resource_dir_path(name: str) -> Path | None:
    for resource_dir in get_resource_dirs():
        candidate = resource_dir / name
        if candidate.is_dir():
            return candidate
    return None


def jdk_resource_names() -> list[str]:
    machine = platform.machine().lower()
    if machine in {"arm64", "aarch64"}:
        return ["jdk-arm64", "jdk"]
    if machine in {"x86_64", "amd64"}:
        return ["jdk-x86_64", "jdk-x64", "jdk"]
    return ["jdk"]


def bundled_jdk_bin_candidates(binary_name: str) -> list[Path]:
    candidates: list[Path] = []
    for resource_dir in get_resource_dirs():
        for jdk_name in jdk_resource_names():
            candidates.append(resource_dir / jdk_name / "Contents" / "Home" / "bin" / binary_name)
    return candidates


def resolve_icon_path() -> Path | None:
    for icon_name in ("Android.ico", "android.ico"):
        icon_path = resource_file(icon_name)
        if icon_path is not None:
            return icon_path
    return None


def apply_window_icon(root: tk.Tk) -> None:
    icon_path = resolve_icon_path()
    if icon_path is None:
        return
    try:
        root.iconbitmap(default=str(icon_path))
    except Exception:
        pass


def is_working_java_binary(candidate: str | Path | None) -> bool:
    if not candidate:
        return False
    path = Path(candidate)
    if not path.is_file():
        return False
    result = subprocess.run(
        [str(path), "-version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return result.returncode == 0


def resolve_adb_path() -> str | None:
    candidates: list[str | Path | None] = [
        *(resource_dir / "platform-tools" / "adb" for resource_dir in get_resource_dirs()),
        BASE_DIR.parent / "platform-tools" / "adb",
        which("adb"),
        str(Path.home() / "Library/Android/sdk/platform-tools/adb"),
        "/opt/homebrew/bin/adb",
        "/usr/local/bin/adb",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate))
    return None


def resolve_java_path() -> str | None:
    candidates: list[str | Path | None] = [
        *bundled_jdk_bin_candidates("java"),
        *(resource_dir / "runtime" / "jdk" / "Contents" / "Home" / "bin" / "java" for resource_dir in get_resource_dirs()),
        Path(which("java")) if which("java") else None,
        "/opt/homebrew/opt/openjdk/bin/java",
        "/usr/local/opt/openjdk/bin/java",
        "/Library/Java/JavaVirtualMachines/openjdk.jdk/Contents/Home/bin/java",
        Path.home() / "Library/Java/JavaVirtualMachines/microsoft-21.jdk/Contents/Home/bin/java",
    ]
    for candidate in candidates:
        if is_working_java_binary(candidate):
            return str(Path(candidate))
    return None


def resolve_keytool_path() -> str | None:
    candidates: list[str | Path | None] = [
        *bundled_jdk_bin_candidates("keytool"),
        *(resource_dir / "runtime" / "jdk" / "Contents" / "Home" / "bin" / "keytool" for resource_dir in get_resource_dirs()),
        Path(which("keytool")) if which("keytool") else None,
        "/opt/homebrew/opt/openjdk/bin/keytool",
        "/usr/local/opt/openjdk/bin/keytool",
        "/Library/Java/JavaVirtualMachines/openjdk.jdk/Contents/Home/bin/keytool",
        Path.home() / "Library/Java/JavaVirtualMachines/microsoft-21.jdk/Contents/Home/bin/keytool",
    ]
    for candidate in candidates:
        if is_working_java_binary(candidate):
            return str(Path(candidate))
    return None


def resolve_aapt_path() -> str | None:
    direct = which("aapt")
    if direct and Path(direct).is_file():
        return direct

    for resource_dir in get_resource_dirs():
        local_aapt2 = resource_dir / "aapt2" / "aapt2"
        if local_aapt2.is_file():
            return str(local_aapt2)

        local_build_tools = resource_dir / "build-tools"
        if local_build_tools.is_dir():
            for candidate in sorted(local_build_tools.glob("*/aapt"), reverse=True):
                if candidate.is_file():
                    return str(candidate)

    sdk_build_tools = Path.home() / "Library/Android/sdk/build-tools"
    if sdk_build_tools.is_dir():
        for candidate in sorted(sdk_build_tools.glob("*/aapt"), reverse=True):
            if candidate.is_file():
                return str(candidate)
    return None


def run_adb(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [adb_path or "adb", *cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def run_command(cmd: list[str], *, timeout: int | None = None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=timeout,
    )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode(errors="ignore") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode(errors="ignore") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return subprocess.CompletedProcess(
            cmd,
            124,
            stdout=stdout,
            stderr=stderr or f"命令超时：{' '.join(cmd)}",
        )


def run_adb_text(cmd: list[str], *, timeout: int | None = None) -> subprocess.CompletedProcess:
    return run_command([adb_path or "adb", *cmd], timeout=timeout)


def set_status(text: str, *, tone: str = "neutral") -> None:
    if status_var is None:
        return
    prefix = {
        "neutral": "状态",
        "success": "完成",
        "error": "异常",
        "recording": "录制中",
    }.get(tone, "状态")
    status_var.set(f"{prefix} · {text}")
    if status_label is not None:
        style_name = {
            "neutral": "StatusNeutral.TLabel",
            "recording": "StatusNeutral.TLabel",
            "success": "StatusSuccess.TLabel",
            "error": "StatusError.TLabel",
        }.get(tone, "StatusNeutral.TLabel")
        status_label.configure(style=style_name)


def format_log_line(text: str) -> str:
    if not text:
        return "\n"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"[{timestamp}] {text.rstrip()}\n"


def render_active_log() -> None:
    if install_log_widget is None:
        return
    install_log_widget.delete("1.0", "end")
    for line in module_log_history.get(current_log_module, []):
        install_log_widget.insert("end", line)
    install_log_widget.see("end")


def select_log_module(module: str) -> None:
    global current_log_module
    if module not in LOG_MODULES:
        module = "package"
    current_log_module = module
    if active_log_var is not None:
        active_log_var.set(f"当前日志：{LOG_MODULES[module]}")
    if active_log_label is not None:
        active_log_label.configure(style=ACTIVE_LOG_STYLES.get(module, "ActiveLogPackage.TLabel"))
    render_active_log()


def append_module_log(module: str, text: str) -> None:
    if module not in LOG_MODULES:
        module = "package"
    line = format_log_line(text)
    module_log_history.setdefault(module, []).append(line)
    if module == current_log_module:
        render_active_log()


def append_install_log(text: str, *, module: str = "package") -> None:
    append_module_log(module, text)


def post_install_log(text: str, *, module: str = "package") -> None:
    if ui_root is None:
        return
    ui_root.after(0, lambda: append_install_log(text, module=module))


def post_status(text: str, *, tone: str = "neutral") -> None:
    if ui_root is None:
        return
    ui_root.after(0, lambda: set_status(text, tone=tone))


def run_with_log_module(module: str, callback) -> None:
    select_log_module(module)
    callback()


def copy_text_to_clipboard(text: str) -> None:
    if ui_root is None:
        return
    ui_root.clipboard_clear()
    ui_root.clipboard_append(text)
    ui_root.update_idletasks()


def set_selected_file(text: str) -> None:
    if selected_file_var is not None:
        selected_file_var.set(text)


def set_install_buttons_enabled(enabled: bool) -> None:
    state = ["!disabled"] if enabled else ["disabled"]
    for button in (apk_button, aab_button, parse_button):
        if button is not None:
            button.state(state)


def set_firebase_button_enabled(enabled: bool) -> None:
    if firebase_button is not None:
        firebase_button.state(["!disabled"] if enabled else ["disabled"])


def build_firebase_debugview_command(package_name: str) -> list[str]:
    return ["shell", "setprop", "debug.firebase.analytics.app", package_name]


def resolve_firebase_debug_package(package_path: Path) -> str:
    suffix = package_path.suffix.lower()
    if suffix == ".apk":
        metadata = parse_apk_metadata(package_path)
    elif suffix == ".aab":
        metadata = parse_aab_metadata(package_path)
    elif suffix == ".apks":
        metadata = parse_apks_metadata(package_path)
    else:
        raise RuntimeError("Firebase DebugView 仅支持 APK / AAB / APKS 文件。")

    package_name = metadata.get("bundle_ID", "-").strip()
    if not package_name or package_name == "-":
        raise RuntimeError("未能从所选文件中解析包名。")
    return package_name


def update_firebase_target(package_path: Path, package_name: str) -> None:
    global firebase_debug_package
    firebase_debug_package = package_name
    if firebase_file_var is not None:
        firebase_file_var.set(f"当前文件：{package_path}")
    if firebase_package_var is not None:
        firebase_package_var.set(f"当前包名：{package_name}")
    set_firebase_button_enabled(True)


def run_select_firebase_debug_package(package_path: Path) -> None:
    global firebase_debug_package
    select_log_module("firebase")
    append_install_log("", module="firebase")
    append_install_log(f"[选择] Firebase DebugView 文件：{package_path}", module="firebase")
    try:
        package_name = resolve_firebase_debug_package(package_path)
        update_firebase_target(package_path, package_name)
        append_install_log(f"[目标] 包名：{package_name}", module="firebase")
        set_status(f"已选择 Firebase DebugView：{package_name}", tone="success")
    except Exception as exc:
        if firebase_file_var is not None:
            firebase_file_var.set("当前文件：未选择 Android 安装包")
        if firebase_package_var is not None:
            firebase_package_var.set("当前包名：未选择")
        firebase_debug_package = ""
        set_firebase_button_enabled(False)
        append_install_log(f"[异常] Firebase DebugView 文件解析失败：{exc}", module="firebase")
        set_status("Firebase DebugView 文件解析失败", tone="error")


def choose_firebase_debug_package() -> None:
    select_log_module("firebase")
    package_path_str = filedialog.askopenfilename(
        title="选择 Firebase DebugView 文件",
        initialdir=str(BASE_DIR),
        filetypes=[
            ("Android package", "*.apk *.aab *.apks"),
            ("Android APK", "*.apk"),
            ("Android App Bundle", "*.aab"),
            ("Android APK Set", "*.apks"),
            ("All Files", "*.*"),
        ],
    )
    if not package_path_str:
        return
    run_select_firebase_debug_package(Path(package_path_str))


def enable_firebase_debugview() -> None:
    select_log_module("firebase")
    package_name = firebase_debug_package.strip()
    if not package_name and firebase_package_var is not None:
        current_value = firebase_package_var.get().strip()
        if current_value.startswith("当前包名："):
            package_name = current_value.replace("当前包名：", "", 1).strip()
    if not package_name or package_name == "未选择":
        append_install_log("[提示] 请先选择 Android 安装包。", module="firebase")
        set_status("请先选择 Firebase 目标包", tone="error")
        return
    if not ensure_adb_ready():
        append_install_log("[异常] 未找到可用的 Android 设备或 adb。", module="firebase")
        return

    append_install_log("[选择] 开启 Firebase DebugView", module="firebase")
    append_install_log(f"[目标] 包名：{package_name}", module="firebase")
    command = build_firebase_debugview_command(package_name)
    append_install_log("[命令] adb " + " ".join(command), module="firebase")
    result = run_adb(command)
    output = (result.stdout + result.stderr).decode(errors="ignore").strip()
    if result.returncode == 0:
        append_install_log(f"[完成] Firebase DebugView 已开启：{package_name}", module="firebase")
        append_install_log("[提示] 重新打开目标 App 后即可在 Firebase DebugView 看到事件。", module="firebase")
        set_status(f"Firebase DebugView 已开启：{package_name}", tone="success")
        return

    append_install_log(output or f"[失败] setprop 退出码：{result.returncode}", module="firebase")
    set_status("Firebase DebugView 开启失败", tone="error")


def format_size(size_bytes: int) -> str:
    value = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1000 or unit == "GB":
            return f"{int(value)} {unit}" if unit == "B" else f"{value:.2f} {unit}"
        value /= 1000
    return f"{size_bytes} B"


def extract_with_regex(pattern: str, text: str) -> str:
    match = re.search(pattern, text)
    return match.group(1) if match else "-"


def extract_advertising_id(text: str) -> str | None:
    match = ADVERTISING_ID_RE.search(text)
    return match.group(0).lower() if match else None


def clean_bundletool_output(text: str) -> str:
    cleaned_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("WARNING:"):
            continue
        if "sun.misc.Unsafe" in line:
            continue
        if "Please consider reporting this" in line:
            continue
        if "will be removed in a future release" in line:
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def ensure_adb_ready() -> bool:
    global adb_path

    adb_path = resolve_adb_path()
    if not adb_path:
        messagebox.showerror(
            "未找到 adb",
            "请先安装 Android Platform Tools。\n已检查常见路径：\n~/Library/Android/sdk/platform-tools/adb\n当前目录/platform-tools/adb\n/opt/homebrew/bin/adb\n/usr/local/bin/adb",
        )
        set_status("未找到 adb", tone="error")
        return False

    version_result = subprocess.run(
        [adb_path, "version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if version_result.returncode != 0:
        msg = version_result.stderr.decode(errors="ignore").strip() or "adb 无法启动"
        messagebox.showerror("adb 异常", msg)
        set_status("adb 无法启动", tone="error")
        return False

    device_result = run_adb(["get-state"])
    if device_result.returncode != 0 or device_result.stdout.decode(errors="ignore").strip() != "device":
        messagebox.showerror("未连接设备", "请先连接 Android 设备，并确认 USB 调试已授权。")
        set_status("未检测到可用设备", tone="error")
        return False
    return True


def has_android_device_connected() -> bool:
    current_adb = resolve_adb_path()
    if not current_adb:
        return False
    version_result = subprocess.run(
        [current_adb, "version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if version_result.returncode != 0:
        return False
    device_result = subprocess.run(
        [current_adb, "get-state"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return device_result.returncode == 0 and device_result.stdout.decode(errors="ignore").strip() == "device"


def resolve_ios_device_identifier() -> tuple[str, str] | None:
    result = run_command(["xcrun", "devicectl", "list", "devices"], timeout=20)
    output = result.stdout + result.stderr
    if result.returncode != 0 and not output.strip():
        return None

    pattern = re.compile(
        r"^(?P<name>.+?)\s{2,}(?P<hostname>.+?)\s{2,}(?P<identifier>[A-F0-9-]+)\s{2,}(?P<state>available \(paired\)|available)\s{2,}(?P<model>.+)$"
    )
    for line in output.splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue
        name = match.group("name").strip()
        identifier = match.group("identifier").strip()
        model = match.group("model").strip()
        if "iPhone" in model or "iPad" in model:
            return identifier, name
    return None


def run_devicectl_json(args: list[str]) -> dict | None:
    with tempfile.NamedTemporaryFile(prefix="devicectl_", suffix=".json", delete=False) as handle:
        json_path = Path(handle.name)
    try:
        result = run_command(["xcrun", "devicectl", *args, "--json-output", str(json_path)], timeout=35)
        if json_path.exists():
            try:
                payload = json.loads(json_path.read_text(encoding="utf-8"))
            except Exception:
                payload = None
        else:
            payload = None
        if payload is not None and payload.get("info", {}).get("outcome") != "failed":
            return payload
        if result.returncode == 0 and payload is not None:
            return payload
        return None
    finally:
        json_path.unlink(missing_ok=True)


def walk_dict_nodes(value: object) -> list[dict]:
    found: list[dict] = []
    if isinstance(value, dict):
        found.append(value)
        for child in value.values():
            found.extend(walk_dict_nodes(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(walk_dict_nodes(child))
    return found


def looks_like_bundle_id(value: str) -> bool:
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*(\.[A-Za-z0-9_-]+)+", value):
        return False
    return not re.fullmatch(r"[A-Fa-f0-9-]{20,}", value)


def extract_ios_app_records(payload: dict | None) -> list[tuple[str, str]]:
    if not payload:
        return []

    records: dict[str, str] = {}
    for node in walk_dict_nodes(payload):
        bundle_id = None
        for key, raw in node.items():
            key_lower = str(key).lower()
            if isinstance(raw, str) and "bundle" in key_lower and "identifier" in key_lower and looks_like_bundle_id(raw):
                bundle_id = raw.strip()
                break
        if bundle_id is None:
            for raw in node.values():
                if isinstance(raw, str) and looks_like_bundle_id(raw):
                    bundle_id = raw.strip()
                    break
        if not bundle_id or bundle_id.startswith(("com.apple.", "com.appleinternal.")):
            continue

        name = bundle_id
        for key in ("localizedName", "displayName", "name", "processName", "bundleName", "executableName"):
            raw = node.get(key)
            if isinstance(raw, str) and raw.strip() and not looks_like_bundle_id(raw.strip()):
                name = raw.strip()
                break
        records.setdefault(bundle_id, name)

    return sorted(records.items(), key=lambda item: item[1].lower())


def list_ios_candidate_apps(device_identifier: str) -> list[tuple[str, str]]:
    processes_payload = run_devicectl_json(["device", "info", "processes", "--device", device_identifier])
    process_records = extract_ios_app_records(processes_payload)
    if process_records:
        return process_records

    apps_payload = run_devicectl_json(["device", "info", "apps", "--device", device_identifier, "--include-all-apps"])
    return extract_ios_app_records(apps_payload)


def ask_ios_app_selection(candidates: list[tuple[str, str]]) -> tuple[str, str] | None:
    if ui_root is None or tk is None:
        return None

    selected: dict[str, tuple[str, str] | None] = {"value": None}
    dialog = tk.Toplevel(ui_root)
    dialog.title("选择 iOS 应用")
    dialog.configure(bg=UI_BG)
    dialog.resizable(False, False)
    dialog.transient(ui_root)
    dialog.grab_set()

    ttk.Label(
        dialog,
        text="未能自动识别前台 App，请选择要提取日志的 iOS 应用。",
        style="Caption.TLabel",
        wraplength=560,
        justify="left",
    ).pack(anchor="w", padx=18, pady=(16, 10))

    listbox = tk.Listbox(dialog, width=78, height=min(max(len(candidates), 6), 12), font=("SF Pro Text", 11))
    for bundle_id, name in candidates:
        listbox.insert("end", f"{name}   ({bundle_id})")
    listbox.pack(fill="both", padx=18, pady=(0, 12))
    if candidates:
        listbox.selection_set(0)

    actions = ttk.Frame(dialog, style="Content.TFrame")
    actions.pack(fill="x", padx=18, pady=(0, 16))

    def confirm() -> None:
        selection = listbox.curselection()
        if selection:
            selected["value"] = candidates[selection[0]]
        dialog.destroy()

    def cancel() -> None:
        selected["value"] = None
        dialog.destroy()

    ttk.Button(actions, text="使用所选应用", style="Action.TButton", command=confirm).pack(side="left")
    ttk.Button(actions, text="取消", style="Secondary.TButton", command=cancel).pack(side="left", padx=(12, 0))
    listbox.bind("<Double-Button-1>", lambda _event: confirm())
    dialog.protocol("WM_DELETE_WINDOW", cancel)

    dialog.update_idletasks()
    x = ui_root.winfo_rootx() + int((ui_root.winfo_width() - dialog.winfo_width()) / 2)
    y = ui_root.winfo_rooty() + int((ui_root.winfo_height() - dialog.winfo_height()) / 2)
    dialog.geometry(f"+{max(x, 0)}+{max(y, 0)}")
    ui_root.wait_window(dialog)
    return selected["value"]


def ask_ios_bundle_id() -> tuple[str, str] | None:
    if simpledialog is None:
        return None
    bundle_id = simpledialog.askstring(
        "输入 iOS Bundle ID",
        "未能自动识别前台 App，请输入目标 iOS App 的 Bundle ID：",
        parent=ui_root,
    )
    if not bundle_id:
        return None
    bundle_id = bundle_id.strip()
    if not looks_like_bundle_id(bundle_id):
        messagebox.showerror("Bundle ID 无效", "请输入类似 com.example.app 的 iOS Bundle ID。")
        return None
    return bundle_id, bundle_id


def resolve_ios_log_target(device_identifier: str) -> tuple[str, str] | None:
    foreground_app = pick_ios_foreground_app(device_identifier)
    if foreground_app:
        return foreground_app

    candidates = list_ios_candidate_apps(device_identifier)
    if candidates:
        selected = ask_ios_app_selection(candidates)
        if selected:
            return selected

    return ask_ios_bundle_id()


def pick_ios_foreground_app(device_identifier: str) -> tuple[str, str] | None:
    payload = run_devicectl_json(["device", "info", "processes", "--device", device_identifier])
    if not payload:
        return None

    best_candidate: tuple[int, str, str] | None = None
    for node in walk_dict_nodes(payload):
        bundle_id = None
        for key in ("bundleIdentifier", "bundleID", "applicationBundleIdentifier"):
            raw = node.get(key)
            if isinstance(raw, str) and "." in raw:
                bundle_id = raw
                break
        if not bundle_id:
            continue

        name = ""
        for key in ("name", "processName", "localizedName", "executableName"):
            raw = node.get(key)
            if isinstance(raw, str) and raw.strip():
                name = raw.strip()
                break

        score = 0
        if not bundle_id.startswith("com.apple."):
            score += 50
        if node.get("isApplication") is True:
            score += 15

        for key, value in node.items():
            key_lower = str(key).lower()
            value_text = str(value).lower()
            if "front" in key_lower or "foreground" in key_lower:
                if value is True or "front" in value_text or "foreground" in value_text or "active" in value_text:
                    score += 100
            if "visible" in key_lower and value is True:
                score += 40
            if "state" in key_lower and ("foreground" in value_text or "active" in value_text or "running" in value_text):
                score += 20

        if best_candidate is None or score > best_candidate[0]:
            best_candidate = (score, bundle_id, name or bundle_id)

    if best_candidate and best_candidate[0] > 0:
        return best_candidate[1], best_candidate[2]
    return None


def copy_ios_app_logs(device_identifier: str, bundle_id: str, app_name: str) -> Path | None:
    ensure_dir(LOG_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = LOG_DIR / f"{bundle_id}_{timestamp}_ios"
    ensure_dir(output_dir)

    subdirs = ["Library/Logs", "Library/Caches", "Documents", "tmp"]
    copied_any = False
    notes: list[str] = []
    for subdir in subdirs:
        destination = output_dir / subdir.replace("/", "_")
        ensure_dir(destination)
        cmd = [
            "xcrun",
            "devicectl",
            "device",
            "copy",
            "from",
            "--device",
            device_identifier,
            "--source",
            subdir,
            "--destination",
            str(destination),
            "--domain-type",
            "appDataContainer",
            "--domain-identifier",
            bundle_id,
        ]
        result = run_command(cmd, timeout=45)
        if result.returncode == 0:
            copied_any = True
            notes.append(f"已尝试复制：{subdir}")
        else:
            error_text = (result.stdout + result.stderr).strip()
            if error_text:
                notes.append(f"{subdir}：{error_text}")

    summary_path = output_dir / "_extract_summary.txt"
    summary_lines = [
        f"bundle_id={bundle_id}",
        f"app_name={app_name}",
        f"device_identifier={device_identifier}",
        f"generated_at={datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "说明：iOS 真机这里提取的是应用沙盒中的日志类文件（如 Library/Logs、Caches、Documents、tmp），",
        "不是 Android logcat 那种系统实时日志流。",
        "",
        *notes,
    ]
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    log_like_files = [
        path
        for path in output_dir.rglob("*")
        if path.is_file() and (
            path.suffix.lower() in {".log", ".txt", ".json", ".trace", ".ips", ".crash"}
            or "log" in path.name.lower()
        )
    ]
    if copied_any or log_like_files:
        return output_dir
    return None


def ensure_java_tools_ready() -> tuple[str | None, str | None]:
    java_path = resolve_java_path()
    keytool_path = resolve_keytool_path()
    if not java_path or not keytool_path:
        append_install_log("[异常] 未找到可用的 java 或 keytool，请先安装 JDK。")
        append_install_log(f"[提示] 可直接运行：{BASE_DIR / '安装JDK.command'}")
        set_status("未找到 java/keytool", tone="error")
        return None, None
    return java_path, keytool_path


def bundletool_path() -> Path | None:
    for resource_dir in get_resource_dirs():
        for candidate_name in (JAR_NAME, "bundletool-1.18.3.jar"):
            candidate = resource_dir / candidate_name
            if candidate.is_file():
                return candidate
    for candidate_name in (JAR_NAME, "bundletool-1.18.3.jar"):
        candidate = TOOLKIT_DIR / candidate_name
        if candidate.is_file():
            return candidate
    return None


def download_file(url: str, target: Path) -> None:
    curl_path = which("curl")
    if curl_path:
        result = subprocess.run(
            [curl_path, "-L", "--fail", "--retry", "2", "--connect-timeout", "20", url, "-o", str(target)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return
        if result.stdout.strip():
            append_install_log(result.stdout.strip())

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) Python AndroidTools",
            "Accept": "*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=120) as response, open(target, "wb") as handle:
        handle.write(response.read())


def ensure_bundletool_available() -> Path | None:
    existing = bundletool_path()
    if existing is not None:
        append_install_log(f"[步骤] 已检测到 bundletool：{existing}")
        return existing

    ensure_dir(DATA_DIR)
    target = DATA_DIR / JAR_NAME
    temp_target = target.with_suffix(".jar.download")
    append_install_log(f"[步骤] 未检测到 {JAR_NAME}，开始自动下载...")

    last_error: Exception | None = None
    try:
        for url in BUNDLETOOL_DOWNLOAD_URLS:
            append_install_log(f"[步骤] 尝试下载：{url}")
            if temp_target.exists():
                temp_target.unlink()
            try:
                download_file(url, temp_target)
                temp_target.replace(target)
                append_install_log(f"[完成] bundletool 下载完成：{target}")
                return target
            except (ssl.SSLCertVerificationError, urllib.error.URLError) as exc:
                last_error = exc
                if "CERTIFICATE_VERIFY_FAILED" in str(exc).upper():
                    try:
                        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(request, timeout=120, context=ssl._create_unverified_context()) as response, open(temp_target, "wb") as handle:
                            handle.write(response.read())
                        temp_target.replace(target)
                        append_install_log(f"[完成] bundletool 下载完成：{target}")
                        return target
                    except Exception as retry_exc:
                        last_error = retry_exc
                append_install_log(f"[警告] 下载失败：{exc}")
            except Exception as exc:
                last_error = exc
                append_install_log(f"[警告] 下载失败：{exc}")
        if last_error is not None:
            append_install_log(f"[异常] 自动下载 {JAR_NAME} 失败：{last_error}")
        append_install_log(f"[提示] 可直接运行：{BASE_DIR / '安装Bundletool.command'}")
        return None
    finally:
        if temp_target.exists():
            temp_target.unlink()


def read_jar_manifest(jar_path: Path) -> str:
    try:
        with zipfile.ZipFile(jar_path) as archive:
            return archive.read("META-INF/MANIFEST.MF").decode("utf-8", errors="ignore")
    except Exception:
        return ""


def parse_manifest_attributes_text(manifest_text: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    current_key: str | None = None
    for raw_line in manifest_text.splitlines():
        if raw_line.startswith(" ") and current_key is not None:
            attrs[current_key] += raw_line[1:]
            continue
        if ":" not in raw_line:
            current_key = None
            continue
        key, value = raw_line.split(":", 1)
        current_key = key.strip()
        attrs[current_key] = value.strip()
    return attrs


def build_bundletool_java_cmd(java_path: str, jar_path: Path) -> list[str]:
    manifest_text = read_jar_manifest(jar_path)
    manifest_attrs = parse_manifest_attributes_text(manifest_text)

    if manifest_attrs.get("Main-Class"):
        return [java_path, "-jar", str(jar_path)]

    class_path_items = [str(jar_path)]
    bundled_libs_dir = resource_dir_path("bundletool-libs")
    writable_libs_dir = DATA_DIR / "bundletool-libs"

    class_path_decl = manifest_attrs.get("Class-Path", "").strip()
    if class_path_decl:
        for jar_name in class_path_decl.split():
            bundled_target = bundled_libs_dir / jar_name if bundled_libs_dir is not None else None
            lib_target = bundled_target if bundled_target is not None and bundled_target.is_file() else writable_libs_dir / jar_name
            if not lib_target.is_file():
                url = BUNDLETOOL_LIB_URLS.get(jar_name)
                if url is None:
                    raise RuntimeError(f"缺少 bundletool 依赖：{jar_name}")
                writable_libs_dir.mkdir(parents=True, exist_ok=True)
                append_install_log(f"[步骤] 正在下载 bundletool 依赖：{jar_name}")
                download_file(url, lib_target)
            class_path_items.append(str(lib_target))

    for jar_name, url in BUNDLETOOL_EXTRA_LIB_URLS.items():
        bundled_target = bundled_libs_dir / jar_name if bundled_libs_dir is not None else None
        lib_target = bundled_target if bundled_target is not None and bundled_target.is_file() else writable_libs_dir / jar_name
        if not lib_target.is_file():
            writable_libs_dir.mkdir(parents=True, exist_ok=True)
            append_install_log(f"[步骤] 正在下载额外运行时依赖：{jar_name}")
            download_file(url, lib_target)
        class_path_items.append(str(lib_target))

    return [java_path, "-cp", os.pathsep.join(class_path_items), BUNDLETOOL_MAIN_CLASS]


def ensure_aapt2_available() -> str | None:
    existing = resolve_aapt_path()
    if existing is not None:
        return existing

    aapt2_dir = DATA_DIR / "aapt2"
    ensure_dir(aapt2_dir)
    jar_target = aapt2_dir / f"aapt2-{AAPT2_VERSION}-osx.jar"
    temp_target = jar_target.with_suffix(".jar.download")
    try:
        append_install_log(f"[步骤] 未检测到 aapt2，开始下载：{AAPT2_JAR_URL}")
        download_file(AAPT2_JAR_URL, temp_target)
        temp_target.replace(jar_target)
        with zipfile.ZipFile(jar_target) as archive:
            binary_name = next((name for name in archive.namelist() if name.endswith("/aapt2") or name == "aapt2"), None)
            if binary_name is None:
                raise RuntimeError("aapt2 压缩包中未找到可执行文件。")
            archive.extract(binary_name, path=aapt2_dir)
            extracted = aapt2_dir / binary_name
            final_binary = aapt2_dir / "aapt2"
            if extracted != final_binary:
                final_binary.write_bytes(extracted.read_bytes())
                extracted.unlink(missing_ok=True)
            final_binary.chmod(0o755)
            return str(final_binary)
    except Exception as exc:
        append_install_log(f"[异常] 自动准备 aapt2 失败：{exc}")
        return None
    finally:
        if temp_target.exists():
            temp_target.unlink()


def ensure_keystore(keytool_path: str) -> Path | None:
    for resource_dir in get_resource_dirs():
        candidate = resource_dir / KEYSTORE_NAME
        if candidate.is_file():
            return candidate
    toolkit_candidate = TOOLKIT_DIR / KEYSTORE_NAME
    if toolkit_candidate.is_file():
        return toolkit_candidate

    ensure_dir(DATA_DIR)
    generated_path = DATA_DIR / KEYSTORE_NAME
    result = subprocess.run(
        [
            keytool_path,
            "-genkeypair",
            "-v",
            "-keystore",
            str(generated_path),
            "-alias",
            KEY_ALIAS,
            "-storepass",
            KEY_PASS,
            "-keypass",
            KEY_PASS,
            "-keyalg",
            "RSA",
            "-keysize",
            "2048",
            "-validity",
            "10000",
            "-dname",
            "CN=Android Debug,O=Android,C=US",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        append_install_log(result.stdout.strip() or "生成 keystore 失败")
        return None
    return generated_path


def open_folder(path: Path) -> None:
    ensure_dir(path)
    result = subprocess.run(["open", str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        msg = result.stderr.decode(errors="ignore").strip() or "无法打开文件夹"
        messagebox.showerror("打开失败", msg)
        set_status(f"打开目录失败：{path.name}", tone="error")
        return
    set_status(f"已打开目录：{path.name}", tone="success")


def resolve_current_foreground_package() -> str | None:
    candidates = [
        ["shell", "dumpsys", "window", "windows"],
        ["shell", "dumpsys", "activity", "activities"],
    ]
    patterns = [
        r"mCurrentFocus=.*? ([A-Za-z0-9._]+?)/",
        r"mFocusedApp=.*? ([A-Za-z0-9._]+?)/",
        r"topResumedActivity:.*? ([A-Za-z0-9._]+?)/",
        r"ResumedActivity:.*? ([A-Za-z0-9._]+?)/",
    ]

    for cmd in candidates:
        result = run_adb(cmd)
        output = (result.stdout + result.stderr).decode(errors="ignore")
        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                package_name = match.group(1).strip()
                if package_name and package_name not in {"com.android.systemui"}:
                    return package_name
    return None


def resolve_package_pid(package_name: str) -> str | None:
    result = run_adb(["shell", "pidof", package_name])
    if result.returncode == 0:
        pids = result.stdout.decode(errors="ignore").strip().split()
        if pids:
            return pids[0]

    ps_result = run_adb(["shell", "ps", "-A"])
    if ps_result.returncode == 0:
        output = ps_result.stdout.decode(errors="ignore")
        for line in output.splitlines():
            if package_name in line:
                parts = line.split()
                if len(parts) >= 2 and parts[1].isdigit():
                    return parts[1]
    return None


def choose_current_app_log() -> None:
    select_log_module("app_log")
    append_install_log("", module="app_log")
    if has_android_device_connected():
        if not ensure_adb_ready():
            return
        package_name = resolve_current_foreground_package()
        if not package_name:
            messagebox.showerror("提取失败", "未能识别当前前台 Android 应用，请先打开目标应用并保持在前台。")
            set_status("未识别到当前前台 Android 应用", tone="error")
            return
        append_install_log(f"[选择] Android 日志提取目标：{package_name}", module="app_log")
        set_status(f"正在提取 Android 日志：{package_name}")
        threading.Thread(target=run_extract_android_app_log, args=(package_name,), daemon=True).start()
        return

    ios_device = resolve_ios_device_identifier()
    if ios_device is not None:
        device_identifier, device_name = ios_device
        ios_target = resolve_ios_log_target(device_identifier)
        if not ios_target:
            set_status("已取消 iOS 日志提取")
            return
        bundle_id, app_name = ios_target
        append_install_log(f"[选择] iOS 日志提取目标：{bundle_id} ({app_name})", module="app_log")
        append_install_log(f"[设备] iOS 真机：{device_name}", module="app_log")
        set_status(f"正在提取 iOS 日志：{app_name}")
        threading.Thread(target=run_extract_ios_app_log, args=(device_identifier, device_name, bundle_id, app_name), daemon=True).start()
        return

    messagebox.showerror("提取失败", "未检测到可用的 Android 设备或 iOS 真机。")
    set_status("未检测到可用设备", tone="error")


def run_extract_android_app_log(package_name: str) -> None:
    try:
        ensure_dir(LOG_DIR)
        pid = resolve_package_pid(package_name)
        if not pid:
            if ui_root is not None:
                ui_root.after(0, lambda: set_status(f"未找到应用进程：{package_name}", tone="error"))
                ui_root.after(0, lambda: append_install_log(f"[异常] 未找到前台应用进程：{package_name}", module="app_log"))
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = LOG_DIR / f"{package_name}_{timestamp}.log"
        log_cmd = [adb_path or "adb", "logcat", "-d", "-v", "threadtime", f"--pid={pid}"]

        if ui_root is not None:
            ui_root.after(0, lambda: append_install_log(f"[步骤] 提取前台应用日志：{package_name} (PID {pid})", module="app_log"))
            ui_root.after(0, lambda: append_install_log("[命令] " + " ".join(log_cmd), module="app_log"))

        result = subprocess.run(log_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
        output = result.stdout.strip()
        if result.returncode != 0:
            if ui_root is not None:
                ui_root.after(0, lambda: set_status(f"日志提取失败：{package_name}", tone="error"))
                ui_root.after(0, lambda: append_install_log(output or f"[失败] logcat 退出码：{result.returncode}", module="app_log"))
            return
        if not output:
            if ui_root is not None:
                ui_root.after(0, lambda: set_status(f"未抓到日志：{package_name}", tone="error"))
                ui_root.after(0, lambda: append_install_log(f"[异常] 未抓到 {package_name} 的日志输出。", module="app_log"))
            return

        log_path.write_text(output + "\n", encoding="utf-8")
        if ui_root is not None:
            ui_root.after(0, lambda: set_status(f"日志已保存：{log_path.name}", tone="success"))
            ui_root.after(0, lambda: append_install_log(f"[完成] 日志已保存：{log_path}", module="app_log"))
    except Exception as exc:
        if ui_root is not None:
            ui_root.after(0, lambda: set_status("日志提取异常", tone="error"))
            ui_root.after(0, lambda: append_install_log(f"[异常] 日志提取失败：{exc}", module="app_log"))


def run_extract_ios_app_log(device_identifier: str, device_name: str, bundle_id: str, app_name: str) -> None:
    try:
        if ui_root is not None:
            ui_root.after(0, lambda: append_install_log(f"[步骤] 提取 iOS 前台应用沙盒日志：{bundle_id} ({app_name})", module="app_log"))
            ui_root.after(0, lambda: append_install_log(f"[设备] {device_name} / {device_identifier}", module="app_log"))
        output_dir = copy_ios_app_logs(device_identifier, bundle_id, app_name)
        if output_dir is None:
            if ui_root is not None:
                ui_root.after(0, lambda: set_status(f"未提取到 iOS 日志：{app_name}", tone="error"))
                ui_root.after(0, lambda: append_install_log("[异常] 未在 iOS 应用沙盒中找到可提取的日志类文件。", module="app_log"))
                ui_root.after(
                    0,
                    lambda: append_install_log(
                        "[提示] iOS 真机通常只能提取应用自行写入沙盒的日志文件，无法像 Android 一样稳定抓取系统级实时 logcat。",
                        module="app_log",
                    ),
                )
            return

        if ui_root is not None:
            ui_root.after(0, lambda: set_status(f"iOS 日志已保存：{output_dir.name}", tone="success"))
            ui_root.after(0, lambda: append_install_log(f"[完成] iOS 日志目录已保存：{output_dir}", module="app_log"))
    except Exception as exc:
        if ui_root is not None:
            ui_root.after(0, lambda: set_status("iOS 日志提取异常", tone="error"))
            ui_root.after(0, lambda: append_install_log(f"[异常] iOS 日志提取失败：{exc}", module="app_log"))


def choose_output_idfa() -> None:
    select_log_module("app_log")
    append_install_log("", module="app_log")
    append_install_log("[选择] 输出 IDFA / 广告 ID", module="app_log")
    set_status("正在读取 IDFA / 广告 ID…")
    threading.Thread(target=run_output_idfa, daemon=True).start()


def run_output_idfa() -> None:
    if has_android_device_connected():
        run_output_android_advertising_id()
        return

    ios_device = resolve_ios_device_identifier()
    if ios_device is not None:
        device_identifier, device_name = ios_device
        post_install_log(f"[设备] iOS 真机：{device_name} / {device_identifier}", module="app_log")
        post_install_log("[提示] iOS 的 IDFA 只能由 App 通过系统 API 在获得用户授权后读取，Mac 侧工具无法直接从真机导出真实 IDFA。", module="app_log")
        post_install_log("[建议] 如需测试 IDFA，请在目标 App 内增加调试入口或日志输出，再用“提取当前应用日志”查看。", module="app_log")
        post_status("iOS 无法从 Mac 侧直接读取 IDFA", tone="error")
        return

    post_install_log("[异常] 未检测到可用的 Android 设备或 iOS 真机。", module="app_log")
    post_status("未检测到可用设备", tone="error")


def run_output_android_advertising_id() -> None:
    global adb_path

    adb_path = resolve_adb_path()
    if not adb_path:
        post_install_log("[异常] 未找到 adb，无法读取 Android 广告 ID。", module="app_log")
        post_status("未找到 adb", tone="error")
        return

    post_install_log("[设备] Android 设备已连接，开始尝试读取广告 ID。", module="app_log")
    post_install_log("[提示] 请先解锁 Android 设备屏幕，并保持亮屏；锁屏状态下无法读取广告设置页里的 IDFA/广告 ID。", module="app_log")
    commands = [
        (["shell", "settings", "get", "secure", "advertising_id"], "settings secure advertising_id"),
        (["shell", "settings", "get", "global", "advertising_id"], "settings global advertising_id"),
        (["shell", "settings", "get", "secure", "adid"], "settings secure adid"),
        (
            [
                "shell",
                "content",
                "query",
                "--uri",
                "content://com.google.android.gms.ads.identifier/advertising_id",
            ],
            "Google Play Services advertising_id provider",
        ),
    ]

    last_outputs: list[str] = []
    for cmd, label in commands:
        result = run_adb(cmd)
        output = (result.stdout + result.stderr).decode(errors="ignore").strip()
        if output:
            last_outputs.append(f"{label}: {output}")
        advertising_id = extract_advertising_id(output)
        if advertising_id and advertising_id != ZERO_ADVERTISING_ID:
            if ui_root is not None:
                ui_root.after(0, copy_text_to_clipboard, advertising_id)
            post_install_log(f"[完成] Android 广告 ID：{advertising_id}", module="app_log")
            post_install_log("[完成] 已复制到剪贴板。", module="app_log")
            post_status("广告 ID 已输出并复制", tone="success")
            return
        if advertising_id == ZERO_ADVERTISING_ID:
            post_install_log("[提示] 设备返回了全 0 广告 ID，可能是用户关闭了广告 ID 或系统限制读取。", module="app_log")
            post_status("广告 ID 为全 0", tone="error")
            return

    settings_page_id = read_android_advertising_id_from_settings_page()
    if settings_page_id and settings_page_id != ZERO_ADVERTISING_ID:
        if ui_root is not None:
            ui_root.after(0, copy_text_to_clipboard, settings_page_id)
        post_install_log(f"[完成] Android 广告 ID：{settings_page_id}", module="app_log")
        post_install_log("[完成] 已从设备广告设置页读取，并复制到剪贴板。", module="app_log")
        post_status("广告 ID 已输出并复制", tone="success")
        return
    if settings_page_id == ZERO_ADVERTISING_ID:
        post_install_log("[提示] 设备广告设置页返回了全 0 广告 ID，可能是用户关闭了广告 ID 或系统限制读取。", module="app_log")
        post_status("广告 ID 为全 0", tone="error")
        return

    post_install_log("[异常] 未能从当前 Android 设备读取广告 ID。", module="app_log")
    if last_outputs:
        post_install_log("[调试] 命令返回：", module="app_log")
        for output in last_outputs[-3:]:
            post_install_log(output, module="app_log")
    post_install_log("[建议] Android 新版本/部分系统会限制通过 ADB 读取广告 ID，可在 App 内调用 Advertising ID API 后输出到日志。", module="app_log")
    post_status("未读取到广告 ID", tone="error")


def read_android_advertising_id_from_settings_page() -> str | None:
    post_install_log("[步骤] 常规接口未返回广告 ID，尝试打开系统广告设置页读取。", module="app_log")
    post_install_log("[提示] 如果设备仍处于锁屏状态，请手动解锁后再次点击“输出 IDFA”。", module="app_log")
    start_commands = [
        ["shell", "am", "start", "-a", "com.google.android.gms.settings.ADS_PRIVACY"],
        ["shell", "am", "start", "-n", "com.google.android.gms/.adid.settings.AdsSettingsActivity"],
    ]
    last_error = ""
    for cmd in start_commands:
        result = run_adb_text(cmd, timeout=10)
        output = (result.stdout + result.stderr).strip()
        if result.returncode == 0:
            time.sleep(1.2)
            page_id = extract_android_advertising_id_from_ui_dump()
            if page_id:
                return page_id
        last_error = output or f"退出码：{result.returncode}"

    if last_error:
        post_install_log(f"[调试] 打开广告设置页失败：{last_error}", module="app_log")
    return None


def extract_android_advertising_id_from_ui_dump() -> str | None:
    dump_commands = [
        ["exec-out", "uiautomator", "dump", "/dev/tty"],
        ["shell", "uiautomator", "dump", "/dev/tty"],
    ]
    for cmd in dump_commands:
        result = run_adb_text(cmd, timeout=12)
        output = (result.stdout + result.stderr).strip()
        advertising_id = extract_advertising_id(output)
        if advertising_id:
            return advertising_id
    return None


def choose_apk() -> None:
    select_log_module("package")
    apk_path_str = filedialog.askopenfilename(
        title="选择 APK 文件",
        initialdir=str(BASE_DIR),
        filetypes=[("Android APK", "*.apk"), ("All Files", "*.*")],
    )
    if not apk_path_str:
        return
    apk_path = Path(apk_path_str)
    set_selected_file(f"当前文件：{apk_path}")
    append_install_log("")
    append_install_log(f"[选择] APK：{apk_path}")
    if not ensure_adb_ready():
        return
    set_install_buttons_enabled(False)
    set_status(f"正在安装 APK：{apk_path.name}")
    threading.Thread(target=run_install_apk, args=(apk_path,), daemon=True).start()


def run_install_apk(apk_path: Path) -> None:
    try:
        proc = subprocess.Popen(
            [adb_path or "adb", "install", "-r", str(apk_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            clean = line.strip()
            if clean:
                post_install_log(clean)
        proc.wait()
        if proc.returncode == 0:
            if ui_root is not None:
                ui_root.after(0, lambda: set_status(f"APK 安装完成：{apk_path.name}", tone="success"))
                ui_root.after(0, append_install_log, f"[完成] 安装成功：{apk_path.name}")
        else:
            if ui_root is not None:
                ui_root.after(0, lambda: set_status(f"APK 安装失败：{apk_path.name}", tone="error"))
                ui_root.after(0, append_install_log, f"[失败] 安装失败，退出码：{proc.returncode}")
    except Exception as exc:
        if ui_root is not None:
            ui_root.after(0, lambda: set_status("APK 安装异常", tone="error"))
            ui_root.after(0, append_install_log, f"[异常] {exc}")
    finally:
        if ui_root is not None:
            ui_root.after(0, set_install_buttons_enabled, True)


def choose_aab() -> None:
    select_log_module("package")
    aab_path_str = filedialog.askopenfilename(
        title="选择 AAB 文件",
        initialdir=str(BASE_DIR),
        filetypes=[("Android App Bundle", "*.aab"), ("All Files", "*.*")],
    )
    if not aab_path_str:
        return
    aab_path = Path(aab_path_str)
    set_selected_file(f"当前文件：{aab_path}")
    append_install_log("")
    append_install_log(f"[选择] AAB：{aab_path}")
    if not ensure_adb_ready():
        return
    set_install_buttons_enabled(False)
    set_status(f"正在转换并安装：{aab_path.name}")
    threading.Thread(target=run_convert_and_install_aab, args=(aab_path,), daemon=True).start()


def run_convert_and_install_aab(aab_path: Path) -> None:
    try:
        java_path, keytool_path = ensure_java_tools_ready()
        if not java_path or not keytool_path:
            return
        jar_path = ensure_bundletool_available()
        if jar_path is None:
            set_status(f"未找到 {JAR_NAME}", tone="error")
            return
        aapt2_path = ensure_aapt2_available()
        if aapt2_path is None:
            set_status("未找到 aapt2", tone="error")
            return
        keystore_path = ensure_keystore(keytool_path)
        if keystore_path is None:
            set_status("keystore 生成失败", tone="error")
            return

        ensure_dir(APKS_OUTPUT_DIR)
        out_path = APKS_OUTPUT_DIR / f"{aab_path.stem}.apks"
        out_path.unlink(missing_ok=True)

        append_install_log(f"[步骤] 使用 bundletool 转换：{aab_path.name}")
        build_cmd = [
            *build_bundletool_java_cmd(java_path, jar_path),
            "build-apks",
            f"--bundle={aab_path}",
            f"--output={out_path}",
            "--mode=default",
            f"--ks={keystore_path}",
            f"--ks-pass=pass:{KEY_PASS}",
            f"--ks-key-alias={KEY_ALIAS}",
            f"--key-pass=pass:{KEY_PASS}",
            f"--aapt2={aapt2_path}",
            "--local-testing",
        ]
        append_install_log("[命令] " + " ".join(build_cmd))
        build_result = subprocess.run(build_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
        if build_result.stdout.strip():
            append_install_log(build_result.stdout.strip())
        if build_result.returncode != 0:
            set_status(f"AAB 转换失败：{aab_path.name}", tone="error")
            append_install_log(f"[失败] build-apks 退出码：{build_result.returncode}")
            return

        append_install_log(f"[完成] 已生成 APKS：{out_path}")
        append_install_log(f"[步骤] 开始安装 APKS：{out_path.name}")
        install_cmd = [
            *build_bundletool_java_cmd(java_path, jar_path),
            "install-apks",
            f"--apks={out_path}",
            f"--adb={adb_path}",
        ]
        append_install_log("[命令] " + " ".join(install_cmd))
        proc = subprocess.Popen(
            install_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            clean = line.strip()
            if clean:
                post_install_log(clean)
        proc.wait()
        if proc.returncode == 0:
            if ui_root is not None:
                ui_root.after(0, lambda: set_status(f"AAB 转换并安装完成：{aab_path.name}", tone="success"))
                ui_root.after(0, append_install_log, f"[完成] 安装成功：{out_path.name}")
        else:
            if ui_root is not None:
                ui_root.after(0, lambda: set_status(f"APKS 安装失败：{out_path.name}", tone="error"))
                ui_root.after(0, append_install_log, f"[失败] install-apks 退出码：{proc.returncode}")
    except Exception as exc:
        if ui_root is not None:
            ui_root.after(0, lambda: set_status("AAB 转换/安装异常", tone="error"))
            ui_root.after(0, append_install_log, f"[异常] {exc}")
    finally:
        if ui_root is not None:
            ui_root.after(0, set_install_buttons_enabled, True)


def choose_package_for_parse() -> None:
    select_log_module("package")
    package_path_str = filedialog.askopenfilename(
        title="选择安装包文件",
        initialdir=str(BASE_DIR),
        filetypes=[
            ("Package files", "*.apk *.aab *.apks *.ipa"),
            ("Android APK", "*.apk"),
            ("Android App Bundle", "*.aab"),
            ("Android APK Set", "*.apks"),
            ("iOS IPA", "*.ipa"),
            ("All Files", "*.*"),
        ],
    )
    if not package_path_str:
        return
    package_path = Path(package_path_str)
    set_selected_file(f"当前文件：{package_path}")
    append_install_log("")
    append_install_log(f"[选择] 解析文件：{package_path}")
    set_install_buttons_enabled(False)
    set_status(f"正在解析：{package_path.name}")
    threading.Thread(target=run_parse_package, args=(package_path,), daemon=True).start()


def dump_apk_manifest(apk_path: Path) -> str:
    aapt_path = resolve_aapt_path()
    if aapt_path and Path(aapt_path).name == "aapt":
        result = subprocess.run(
            [aapt_path, "dump", "badging", str(apk_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout

    try:
        with zipfile.ZipFile(apk_path) as archive:
            manifest_data = archive.read("AndroidManifest.xml")
    except KeyError as exc:
        raise RuntimeError("APK 中未找到 AndroidManifest.xml。") from exc

    manifest = parse_binary_android_manifest(manifest_data)
    return (
        f"package: name='{manifest.get('package', '-')}' "
        f"versionCode='{manifest.get('versionCode', '-')}' "
        f"versionName='{manifest.get('versionName', '-')}'"
    )


class BinaryXmlParser:
    RES_XML_TYPE = 0x0003
    RES_STRING_POOL_TYPE = 0x0001
    RES_XML_START_ELEMENT_TYPE = 0x0102
    UTF8_FLAG = 0x00000100

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.strings: list[str] = []

    def parse_manifest_attributes(self) -> dict[str, str]:
        if len(self.data) < 8:
            raise RuntimeError("AndroidManifest.xml 数据无效。")
        xml_type, header_size, xml_size = struct.unpack_from("<HHI", self.data, 0)
        if xml_type != self.RES_XML_TYPE:
            raise RuntimeError("AndroidManifest.xml 不是有效的二进制 XML。")
        offset = header_size
        end = min(xml_size, len(self.data))
        while offset + 8 <= end:
            chunk_type, _, chunk_size = struct.unpack_from("<HHI", self.data, offset)
            if chunk_size <= 0:
                break
            if chunk_type == self.RES_STRING_POOL_TYPE:
                self.strings = self._parse_string_pool(offset)
            elif chunk_type == self.RES_XML_START_ELEMENT_TYPE:
                name_idx = struct.unpack_from("<I", self.data, offset + 20)[0]
                attr_count = struct.unpack_from("<H", self.data, offset + 28)[0]
                if self._get_string(name_idx) == "manifest":
                    return self._parse_manifest_start(offset, attr_count)
            offset += chunk_size
        raise RuntimeError("未能在 APK 中解析 manifest 信息。")

    def _parse_string_pool(self, offset: int) -> list[str]:
        header_size = struct.unpack_from("<H", self.data, offset + 2)[0]
        string_count, _, flags, strings_start, _ = struct.unpack_from("<IIIII", self.data, offset + 8)
        is_utf8 = bool(flags & self.UTF8_FLAG)
        indices = [struct.unpack_from("<I", self.data, offset + header_size + index * 4)[0] for index in range(string_count)]
        base = offset + strings_start
        strings: list[str] = []
        for string_offset in indices:
            absolute_offset = base + string_offset
            if is_utf8:
                value, _ = self._read_utf8_string(absolute_offset)
            else:
                value, _ = self._read_utf16_string(absolute_offset)
            strings.append(value)
        return strings

    def _parse_manifest_start(self, offset: int, attr_count: int) -> dict[str, str]:
        attributes: dict[str, str] = {}
        attr_offset = offset + 36
        for index in range(attr_count):
            base = attr_offset + index * 20
            _, name_idx, raw_value_idx, _, typed_value = struct.unpack_from("<IIIII", self.data, base)
            attr_name = self._get_string(name_idx)
            if not attr_name:
                continue
            attr_value = self._coerce_attr_value(raw_value_idx, typed_value)
            if attr_name in {"package", "versionCode", "versionName"}:
                attributes[attr_name] = attr_value
        return attributes

    def _coerce_attr_value(self, raw_value_idx: int, typed_value: int) -> str:
        if raw_value_idx != 0xFFFFFFFF:
            raw = self._get_string(raw_value_idx)
            if raw:
                return raw
        value_type = (typed_value >> 24) & 0xFF
        value_data = typed_value & 0x00FFFFFF
        if value_type == 0x03:
            return self._get_string(value_data)
        return str(value_data)

    def _get_string(self, index: int) -> str:
        if 0 <= index < len(self.strings):
            return self.strings[index]
        return ""

    def _read_utf8_string(self, offset: int) -> tuple[str, int]:
        _, offset = self._read_length8(offset)
        byte_len, offset = self._read_length8(offset)
        raw = self.data[offset : offset + byte_len]
        return raw.decode("utf-8", errors="replace"), offset + byte_len + 1

    def _read_utf16_string(self, offset: int) -> tuple[str, int]:
        char_len, offset = self._read_length16(offset)
        byte_len = char_len * 2
        raw = self.data[offset : offset + byte_len]
        return raw.decode("utf-16le", errors="replace"), offset + byte_len + 2

    def _read_length8(self, offset: int) -> tuple[int, int]:
        first = self.data[offset]
        offset += 1
        if first & 0x80:
            second = self.data[offset]
            offset += 1
            return ((first & 0x7F) << 8) | second, offset
        return first, offset

    def _read_length16(self, offset: int) -> tuple[int, int]:
        first = struct.unpack_from("<H", self.data, offset)[0]
        offset += 2
        if first & 0x8000:
            second = struct.unpack_from("<H", self.data, offset)[0]
            offset += 2
            return ((first & 0x7FFF) << 16) | second, offset
        return first, offset


def parse_binary_android_manifest(data: bytes) -> dict[str, str]:
    return BinaryXmlParser(data).parse_manifest_attributes()


def parse_apk_metadata(apk_path: Path) -> dict[str, str]:
    output = dump_apk_manifest(apk_path)
    return {
        "包类型": "APK",
        "bundle_ID": extract_with_regex(r"package: name='([^']+)'", output),
        "内存大小": format_size(apk_path.stat().st_size),
        "构建版本号": extract_with_regex(r"versionCode='([^']+)'", output),
        "版本名称": extract_with_regex(r"versionName='([^']+)'", output),
    }


def parse_aab_manifest_proto(aab_path: Path) -> dict[str, str]:
    try:
        with zipfile.ZipFile(aab_path) as archive:
            manifest_data = archive.read("base/manifest/AndroidManifest.xml")
    except KeyError:
        return {}
    except zipfile.BadZipFile as exc:
        raise RuntimeError("AAB 文件已损坏，无法读取 manifest。") from exc

    patterns = {
        "package": rb"package\x1a.\s*([A-Za-z0-9._]+)",
        "versionCode": rb"versionCode\x1a.\s*([0-9]+)",
        "versionName": rb"versionName\x1a.\s*([0-9A-Za-z._-]+)",
    }
    values: dict[str, str] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, manifest_data)
        if match:
            values[key] = match.group(1).decode("utf-8", errors="ignore")
    return values


def parse_aab_metadata(aab_path: Path) -> dict[str, str]:
    manifest_values = parse_aab_manifest_proto(aab_path)
    if manifest_values:
        return {
            "包类型": "AAB",
            "bundle_ID": manifest_values.get("package", "-"),
            "内存大小": format_size(aab_path.stat().st_size),
            "构建版本号": manifest_values.get("versionCode", "-"),
            "版本名称": manifest_values.get("versionName", "-"),
        }

    java_path, _ = ensure_java_tools_ready()
    if not java_path:
        raise RuntimeError("未找到 java，且无法直接解析 AAB manifest。")
    jar_path = ensure_bundletool_available()
    if jar_path is None:
        raise RuntimeError(f"未找到 {JAR_NAME}")

    def dump_xpath(xpath: str) -> str:
        result = subprocess.run(
            [
                *build_bundletool_java_cmd(java_path, jar_path),
                "dump",
                "manifest",
                f"--bundle={aab_path}",
                f"--xpath={xpath}",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        return clean_bundletool_output(result.stdout) if result.returncode == 0 else ""

    return {
        "包类型": "AAB",
        "bundle_ID": dump_xpath("/manifest/@package") or "-",
        "内存大小": format_size(aab_path.stat().st_size),
        "构建版本号": dump_xpath("/manifest/@android:versionCode") or dump_xpath("/manifest/@versionCode") or "-",
        "版本名称": dump_xpath("/manifest/@android:versionName") or dump_xpath("/manifest/@versionName") or "-",
    }


def parse_apks_metadata(apks_path: Path) -> dict[str, str]:
    with zipfile.ZipFile(apks_path) as archive:
        apk_names = [name for name in archive.namelist() if name.endswith(".apk")]
        if not apk_names:
            raise RuntimeError("APKS 中未找到可解析的 APK。")
        preferred_name = sorted(apk_names, key=lambda name: (0 if "universal" in name else 1 if "base-master" in name else 2, len(name)))[0]
        with tempfile.TemporaryDirectory() as temp_dir:
            extracted_apk = Path(archive.extract(preferred_name, path=temp_dir))
            metadata = parse_apk_metadata(extracted_apk)
    metadata["包类型"] = "APKS"
    metadata["内存大小"] = format_size(apks_path.stat().st_size)
    return metadata


def parse_ipa_metadata(ipa_path: Path) -> dict[str, str]:
    with zipfile.ZipFile(ipa_path) as archive:
        plist_name = next((name for name in archive.namelist() if name.startswith("Payload/") and name.endswith(".app/Info.plist")), None)
        if plist_name is None:
            raise RuntimeError("IPA 中未找到 Info.plist。")
        plist_data = plistlib.loads(archive.read(plist_name))
    return {
        "包类型": "IPA",
        "bundle_ID": str(plist_data.get("CFBundleIdentifier", "-")),
        "内存大小": format_size(ipa_path.stat().st_size),
        "构建版本号": str(plist_data.get("CFBundleVersion", "-")),
        "版本名称": str(plist_data.get("CFBundleShortVersionString", "-")),
    }


def run_parse_package(package_path: Path) -> None:
    try:
        suffix = package_path.suffix.lower()
        if suffix == ".apk":
            metadata = parse_apk_metadata(package_path)
        elif suffix == ".aab":
            metadata = parse_aab_metadata(package_path)
        elif suffix == ".apks":
            metadata = parse_apks_metadata(package_path)
        elif suffix == ".ipa":
            metadata = parse_ipa_metadata(package_path)
        else:
            raise RuntimeError(f"暂不支持解析该文件类型：{suffix or '无扩展名'}")

        append_install_log(f"[解析] {package_path.name}")
        append_install_log(f"bundle_ID：{metadata['bundle_ID']}")
        append_install_log(f"内存大小：{metadata['内存大小']}")
        append_install_log(f"构建版本号：{metadata['构建版本号']}")
        append_install_log(f"版本名称：{metadata['版本名称']}")
        set_status(f"解析完成：{package_path.name}", tone="success")
    except Exception as exc:
        append_install_log(f"[异常] 解析失败：{exc}")
        set_status(f"解析失败：{package_path.name}", tone="error")
    finally:
        if ui_root is not None:
            ui_root.after(0, set_install_buttons_enabled, True)


def take_screenshot() -> None:
    select_log_module("screenshot")
    append_install_log("", module="screenshot")
    append_install_log("[选择] 立即截图", module="screenshot")
    if not ensure_adb_ready():
        append_install_log("[异常] 未找到可用的 Android 设备或 adb。", module="screenshot")
        return
    ensure_dir(SCREENSHOT_DIR)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = SCREENSHOT_DIR / f"android_screenshot_{ts}.png"
    set_status("正在从设备抓取截图…")
    append_install_log("[步骤] 正在从设备抓取当前画面。", module="screenshot")
    result = run_adb(["exec-out", "screencap", "-p"])
    if result.returncode != 0:
        msg = result.stderr.decode(errors="ignore").strip() or "adb 执行失败"
        messagebox.showerror("截图失败", msg)
        append_install_log(f"[失败] 截图失败：{msg}", module="screenshot")
        set_status("截图失败", tone="error")
        return
    out_path.write_bytes(result.stdout)
    append_install_log(f"[完成] 截图已保存：{out_path}", module="screenshot")
    set_status(f"截图已保存：{out_path.name}", tone="success")
    messagebox.showinfo("截图完成", f"已保存到：\n{out_path}")


def format_record_elapsed(total_seconds: int) -> str:
    mins, secs = divmod(total_seconds, 60)
    hours, mins = divmod(mins, 60)
    return f"{hours:02d}:{mins:02d}:{secs:02d}"


def append_record_progress(total_seconds: int) -> None:
    global last_record_log_second, record_progress_log_index
    if total_seconds == last_record_log_second:
        return
    last_record_log_second = total_seconds
    line = format_log_line(f"[状态] 已录制 {format_record_elapsed(total_seconds)} · 当前第 {segment_index} 段")
    record_logs = module_log_history.setdefault("record", [])
    if record_progress_log_index is None or record_progress_log_index >= len(record_logs):
        record_logs.append(line)
        record_progress_log_index = len(record_logs) - 1
    else:
        record_logs[record_progress_log_index] = line
    if current_log_module == "record":
        render_active_log()


def update_timer_text() -> None:
    global timer_job
    if record_button is None:
        return
    if record_start is None:
        record_button.config(text="开始录屏")
        record_button.configure(style="Action.TButton")
        timer_job = None
        return
    if record_proc is not None and record_proc.poll() is not None:
        finalize_segment()
        if auto_recording:
            start_new_segment()
        else:
            record_button.config(text="开始录屏")
            record_button.configure(style="Action.TButton")
            timer_job = None
            return
    elapsed = datetime.now() - record_start
    total_seconds = int(elapsed.total_seconds())
    record_button.config(text="结束录屏")
    record_button.configure(style="Danger.TButton")
    elapsed_text = format_record_elapsed(total_seconds)
    set_status(f"持续录屏中，已录制 {elapsed_text}，当前第 {segment_index} 段", tone="recording")
    append_record_progress(total_seconds)
    timer_job = record_button.after(500, update_timer_text)


def toggle_recording() -> None:
    select_log_module("record")
    if record_start is None:
        start_recording()
    else:
        stop_recording()


def start_new_segment() -> None:
    global record_proc, current_segment_pulled
    record_proc = subprocess.Popen(
        [adb_path or "adb", "shell", "screenrecord", REMOTE_RECORD_PATH],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    current_segment_pulled = False


def finalize_segment() -> subprocess.CompletedProcess | None:
    global current_segment_pulled, segment_index, recorded_files
    if current_segment_pulled:
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    local_path = RECORD_DIR / f"android_record_{ts}_part{segment_index:02d}.mp4"
    append_install_log(f"[步骤] 拉取录屏分段：第 {segment_index} 段", module="record")
    pull_result = run_adb(["pull", REMOTE_RECORD_PATH, str(local_path)])
    run_adb(["shell", "rm", "-f", REMOTE_RECORD_PATH])
    current_segment_pulled = True
    if pull_result.returncode == 0:
        recorded_files.append(local_path)
        append_install_log(f"[完成] 已保存录屏分段：{local_path}", module="record")
        segment_index += 1
    else:
        output = (pull_result.stdout + pull_result.stderr).decode(errors="ignore").strip()
        append_install_log(output or f"[失败] adb pull 退出码：{pull_result.returncode}", module="record")
    return pull_result


def start_recording() -> None:
    global record_start, timer_job, auto_recording, segment_index, recorded_files, last_record_log_second, record_progress_log_index
    select_log_module("record")
    append_install_log("", module="record")
    append_install_log("[选择] 开始录屏", module="record")
    if record_proc and record_proc.poll() is None:
        messagebox.showinfo("提示", "已经在录制中。")
        append_install_log("[提示] 已经在录制中。", module="record")
        return
    if not ensure_adb_ready():
        append_install_log("[异常] 未找到可用的 Android 设备或 adb。", module="record")
        return
    ensure_dir(RECORD_DIR)
    auto_recording = True
    segment_index = 1
    recorded_files = []
    last_record_log_second = -1
    record_progress_log_index = None
    start_new_segment()
    append_install_log("[步骤] 已启动 Android screenrecord。", module="record")
    record_start = datetime.now()
    if timer_job and record_button is not None:
        record_button.after_cancel(timer_job)
    update_timer_text()


def stop_recording() -> None:
    global record_proc, record_start, timer_job, auto_recording
    select_log_module("record")
    if not record_proc and not record_start:
        messagebox.showinfo("提示", "当前没有录制任务。")
        append_install_log("[提示] 当前没有录制任务。", module="record")
        return
    auto_recording = False
    set_status("正在结束录屏并拉取文件…")
    append_install_log("[选择] 结束录屏", module="record")
    append_install_log("[步骤] 正在停止 screenrecord 并拉取文件。", module="record")
    if record_proc and record_proc.poll() is None:
        kill_result = run_adb(["shell", "pkill", "-l", "2", "screenrecord"])
        if kill_result.returncode != 0:
            pid_result = run_adb(["shell", "pidof", "screenrecord"])
            pids = pid_result.stdout.decode(errors="ignore").strip().split()
            if pid_result.returncode == 0 and pids:
                run_adb(["shell", "kill", "-2", *pids])
            else:
                try:
                    record_proc.send_signal(signal.SIGINT)
                except Exception:
                    record_proc.terminate()
    if record_proc:
        try:
            record_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            record_proc.kill()
            record_proc.wait()
    pull_result = finalize_segment()
    if timer_job and record_button is not None:
        record_button.after_cancel(timer_job)
    timer_job = None
    record_start = None
    record_proc = None
    update_timer_text()

    if pull_result is not None and pull_result.returncode != 0:
        msg = pull_result.stderr.decode(errors="ignore").strip() or "adb pull 失败"
        messagebox.showerror("录屏失败", msg)
        append_install_log(f"[失败] 录屏文件拉取失败：{msg}", module="record")
        set_status("录屏文件拉取失败", tone="error")
    elif recorded_files:
        if len(recorded_files) == 1:
            set_status(f"录屏已保存：{recorded_files[0].name}", tone="success")
            append_install_log(f"[完成] 录屏已保存：{recorded_files[0]}", module="record")
            messagebox.showinfo("录屏完成", f"已保存到：\n{recorded_files[0]}")
        else:
            set_status(f"录屏已保存，共 {len(recorded_files)} 段", tone="success")
            append_install_log(f"[完成] 录屏已保存，共 {len(recorded_files)} 段：{RECORD_DIR}", module="record")
            messagebox.showinfo("录屏完成", f"已保存 {len(recorded_files)} 段到：\n{RECORD_DIR}")


def build_card(parent: ttk.Frame, title: str, subtitle: str, *, wraplength: int = 520) -> tuple[ttk.Frame, ttk.Frame]:
    frame = ttk.Frame(parent, style="Card.TFrame", padding=(18, 16, 18, 18))
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(1, weight=1)

    header = ttk.Frame(frame, style="CardInner.TFrame")
    header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
    header.columnconfigure(0, weight=1)
    ttk.Label(header, text=title, style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
    if subtitle:
        ttk.Label(
            header,
            text=subtitle,
            style="CardCaption.TLabel",
            wraplength=wraplength,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(5, 0))

    body = ttk.Frame(frame, style="CardInner.TFrame")
    body.grid(row=1, column=0, sticky="nsew")
    frame.header = header  # type: ignore[attr-defined]
    return frame, body


def build_button_bar(parent: ttk.Frame, columns: int = 3) -> ttk.Frame:
    bar = ttk.Frame(parent, style="CardInner.TFrame")
    bar.columnconfigure(tuple(range(columns)), weight=1, uniform="action")
    return bar


def bind_log_module_area(widget, module: str, *, exclude: set | None = None) -> None:
    if exclude and widget in exclude:
        return
    if hasattr(widget, "winfo_class") and widget.winfo_class() in {"TButton", "Button"}:
        return
    widget.bind("<Button-1>", lambda _event, selected_module=module: select_log_module(selected_module), add="+")
    for child in widget.winfo_children():
        bind_log_module_area(child, module, exclude=exclude)


def build_ui() -> None:
    global status_var, status_label, record_button, selected_file_var, firebase_file_var, firebase_package_var, install_log_widget, active_log_var, active_log_label, apk_button, aab_button, parse_button, firebase_button, ui_root

    if platform.system() != "Darwin":
        show_startup_error("系统不支持", "这个版本仅面向 macOS。")
        raise SystemExit(1)
    if TK_IMPORT_ERROR is not None or tk is None or filedialog is None or messagebox is None or ttk is None:
        show_startup_error("Tk 初始化失败", f"当前 Python 缺少 tkinter 支持。\n\n详情：{TK_IMPORT_ERROR}")
        raise SystemExit(1)
    try:
        root = tk.Tk()
    except Exception as exc:
        show_startup_error("窗口启动失败", f"无法初始化图形界面。\n\n详情：{exc}")
        raise SystemExit(1)

    ui_root = root
    root.title("Android 工具箱")
    root.configure(bg=UI_BG)
    apply_window_icon(root)
    root.tk_setPalette(background=UI_BG, foreground=UI_TEXT, activeBackground=BLUE_HOVER, activeForeground="#FFFFFF")
    root.resizable(True, True)
    root.withdraw()

    win_w, win_h = 1120, 760
    root.update_idletasks()
    pos_x = int((root.winfo_screenwidth() - win_w) / 2)
    pos_y = int((root.winfo_screenheight() - win_h) / 2)
    root.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
    root.minsize(1040, 700)

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Root.TFrame", background=UI_BG, padding=0)
    style.configure("Content.TFrame", background=UI_BG)
    style.configure("Card.TFrame", background=UI_PANEL, bordercolor=UI_BORDER_SOFT, borderwidth=1, relief="solid")
    style.configure("CardInner.TFrame", background=UI_PANEL)
    style.configure("Header.TFrame", background=UI_BG)
    style.configure("Footer.TFrame", background=UI_PANEL_ALT, bordercolor=UI_BORDER_SOFT, borderwidth=1, relief="solid")
    style.configure("Inset.TFrame", background=UI_PANEL_ALT, bordercolor=UI_BORDER_SOFT, borderwidth=1, relief="solid")
    style.configure("Title.TLabel", background=UI_BG, foreground=UI_TEXT, font=("SF Pro Display", 24, "bold"))
    style.configure("Subtitle.TLabel", background=UI_BG, foreground=UI_SUBTEXT, font=("SF Pro Text", 12))
    style.configure("Eyebrow.TLabel", background=UI_BG, foreground=UI_MUTED, font=("SF Pro Text", 10, "bold"))
    style.configure("Caption.TLabel", background=UI_BG, foreground=UI_SUBTEXT, font=("SF Pro Text", 12))
    style.configure("CardTitle.TLabel", background=UI_PANEL, foreground=UI_TEXT, font=("SF Pro Display", 15, "bold"))
    style.configure("CardCaption.TLabel", background=UI_PANEL, foreground=UI_SUBTEXT, font=("SF Pro Text", 11))
    style.configure("ActiveLogApp.TLabel", background=UI_PANEL, foreground=BLUE, font=("SF Pro Text", 11, "bold"))
    style.configure("ActiveLogScreenshot.TLabel", background=UI_PANEL, foreground=BLUE_HOVER, font=("SF Pro Text", 11, "bold"))
    style.configure("ActiveLogRecord.TLabel", background=UI_PANEL, foreground=DANGER, font=("SF Pro Text", 11, "bold"))
    style.configure("ActiveLogFirebase.TLabel", background=UI_PANEL, foreground=TEAL, font=("SF Pro Text", 11, "bold"))
    style.configure("ActiveLogPackage.TLabel", background=UI_PANEL, foreground=GREEN_TEXT, font=("SF Pro Text", 11, "bold"))
    style.configure("StatusNeutral.TLabel", background=UI_PANEL_ALT, foreground=UI_SUBTEXT, font=("SF Pro Text", 11))
    style.configure("StatusSuccess.TLabel", background=UI_PANEL_ALT, foreground=STATUS_SUCCESS, font=("SF Pro Text", 11, "bold"))
    style.configure("StatusError.TLabel", background=UI_PANEL_ALT, foreground=STATUS_ERROR, font=("SF Pro Text", 11, "bold"))
    style.configure("Path.TLabel", background=UI_PANEL_ALT, foreground=UI_TEXT, font=("SF Pro Text", 11))
    style.configure("Meta.TLabel", background=UI_PANEL_ALT, foreground=UI_MUTED, font=("SF Pro Text", 10, "bold"))
    style.configure("Action.TButton", font=("SF Pro Text", 11, "bold"), padding=(14, 9))
    style.configure("Danger.TButton", font=("SF Pro Text", 11, "bold"), padding=(14, 9))
    style.configure("Install.TButton", font=("SF Pro Text", 11, "bold"), padding=(14, 9))
    style.configure("Debug.TButton", font=("SF Pro Text", 11, "bold"), padding=(14, 9))
    style.configure("Secondary.TButton", font=("SF Pro Text", 11), padding=(14, 9))
    style.map("Action.TButton", background=[("pressed", BLUE_PRESSED), ("active", BLUE_HOVER), ("!disabled", BLUE)], foreground=[("!disabled", "#FFFFFF")])
    style.map("Danger.TButton", background=[("pressed", DANGER_PRESSED), ("active", DANGER_HOVER), ("!disabled", DANGER)], foreground=[("!disabled", "#FFFFFF")])
    style.map("Install.TButton", background=[("pressed", GREEN_PRESSED), ("active", GREEN_HOVER), ("!disabled", GREEN)], foreground=[("!disabled", GREEN_TEXT)])
    style.map("Debug.TButton", background=[("pressed", TEAL_PRESSED), ("active", TEAL_HOVER), ("!disabled", TEAL)], foreground=[("!disabled", "#FFFFFF")])
    style.map("Secondary.TButton", background=[("pressed", SOFT_BLUE_PRESSED), ("active", SOFT_BLUE_HOVER), ("!disabled", SOFT_BLUE)], foreground=[("!disabled", BLUE)])

    root_frame = ttk.Frame(root, style="Root.TFrame", padding=(22, 18, 22, 16))
    root_frame.grid(row=0, column=0, sticky="nsew")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    root_frame.columnconfigure(0, weight=1)
    root_frame.rowconfigure(1, weight=1)

    header = ttk.Frame(root_frame, style="Header.TFrame")
    header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
    header.columnconfigure(0, weight=1)
    ttk.Label(header, text="专业测试工具", style="Eyebrow.TLabel").grid(row=0, column=0, sticky="w")
    ttk.Label(header, text="Android 工具箱", style="Title.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 0))
    ttk.Label(
        header,
        text="日志提取、广告 ID 输出、截图录屏、Firebase DebugView、安装与包体解析集中在一个工作台。",
        style="Subtitle.TLabel",
    ).grid(row=2, column=0, sticky="w", pady=(5, 0))

    content = ttk.Frame(root_frame, style="Content.TFrame")
    content.grid(row=1, column=0, sticky="nsew")
    content.columnconfigure(0, weight=0, minsize=520)
    content.columnconfigure(1, weight=1, minsize=500)
    content.rowconfigure(0, weight=1)

    left_column = ttk.Frame(content, style="Content.TFrame")
    left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
    left_column.columnconfigure(0, weight=1)

    log_card, log_body = build_card(
        left_column,
        "日志与 IDFA",
        "Android 读取当前前台应用日志并尝试输出广告 ID；iOS 读取当前前台应用日志文件。",
        wraplength=460,
    )
    log_card.grid(row=0, column=0, sticky="ew", pady=(0, 12))
    log_actions = build_button_bar(log_body)
    log_actions.grid(row=0, column=0, sticky="ew")
    ttk.Button(log_actions, text="提取应用日志", style="Action.TButton", command=choose_current_app_log).grid(row=0, column=0, sticky="ew", padx=(0, 10))
    ttk.Button(log_actions, text="输出 IDFA", style="Secondary.TButton", command=choose_output_idfa).grid(row=0, column=1, sticky="ew", padx=(0, 10))
    ttk.Button(log_actions, text="打开日志目录", style="Secondary.TButton", command=lambda: run_with_log_module("app_log", lambda: open_folder(LOG_DIR))).grid(row=0, column=2, sticky="ew")
    bind_log_module_area(log_card, "app_log")

    media_card, media_body = build_card(left_column, "截图与录屏", "从已连接 Android 设备抓取当前画面，或分段录制屏幕后自动拉取 MP4 文件到本地。", wraplength=460)
    media_card.grid(row=1, column=0, sticky="ew", pady=(0, 12))
    screenshot_row = ttk.Frame(media_body, style="CardInner.TFrame")
    screenshot_row.grid(row=0, column=0, sticky="ew")
    screenshot_row.columnconfigure(0, weight=1, uniform="media")
    screenshot_row.columnconfigure(1, weight=1, uniform="media")
    screenshot_actions = build_button_bar(screenshot_row)
    screenshot_actions.grid(row=0, column=0, columnspan=2, sticky="ew")
    ttk.Button(screenshot_actions, text="立即截图", style="Action.TButton", command=take_screenshot).grid(row=0, column=0, sticky="ew", padx=(0, 10))
    ttk.Button(screenshot_actions, text="截图目录", style="Secondary.TButton", command=lambda: run_with_log_module("screenshot", lambda: open_folder(SCREENSHOT_DIR))).grid(row=0, column=1, sticky="ew", padx=(0, 10))
    ttk.Label(screenshot_actions, text="", style="CardCaption.TLabel").grid(row=0, column=2, sticky="ew")
    bind_log_module_area(screenshot_row, "screenshot")

    record_row = ttk.Frame(media_body, style="CardInner.TFrame")
    record_row.grid(row=1, column=0, sticky="ew", pady=(12, 0))
    record_row.columnconfigure(0, weight=1, uniform="media")
    record_row.columnconfigure(1, weight=1, uniform="media")
    record_actions = build_button_bar(record_row)
    record_actions.grid(row=0, column=0, columnspan=2, sticky="ew")
    record_button = ttk.Button(record_actions, text="开始录屏", style="Action.TButton", command=toggle_recording)
    record_button.grid(row=0, column=0, sticky="ew", padx=(0, 10))
    ttk.Button(record_actions, text="录屏目录", style="Secondary.TButton", command=lambda: run_with_log_module("record", lambda: open_folder(RECORD_DIR))).grid(row=0, column=1, sticky="ew", padx=(0, 10))
    ttk.Label(record_actions, text="", style="CardCaption.TLabel").grid(row=0, column=2, sticky="ew")
    bind_log_module_area(record_row, "record")

    firebase_card, firebase_body = build_card(
        left_column,
        "Firebase DebugView",
        "选择 APK / AAB / APKS 提取包名后，开启实时 DebugView。",
        wraplength=460,
    )
    firebase_card.grid(row=2, column=0, sticky="ew")
    firebase_body.columnconfigure(0, weight=1)
    firebase_actions = build_button_bar(firebase_body)
    firebase_actions.grid(row=0, column=0, sticky="ew")
    ttk.Button(firebase_actions, text="选择文件", style="Action.TButton", command=choose_firebase_debug_package).grid(row=0, column=0, sticky="ew", padx=(0, 10))
    firebase_button = ttk.Button(firebase_actions, text="开启 DebugView", style="Debug.TButton", command=enable_firebase_debugview)
    firebase_button.grid(row=0, column=1, sticky="ew", padx=(0, 10))
    ttk.Label(firebase_actions, text="", style="CardCaption.TLabel").grid(row=0, column=2, sticky="ew")
    bind_log_module_area(firebase_card, "firebase")

    install_card, install_body = build_card(
        content,
        "模块运行日志",
        "点击左侧模块或安装包操作后，这里只显示当前模块的执行记录。",
        wraplength=480,
    )
    install_card.grid(row=0, column=1, sticky="nsew")
    install_body.columnconfigure(0, weight=1)
    install_body.rowconfigure(3, weight=1)

    install_actions = ttk.Frame(install_body, style="CardInner.TFrame")
    install_actions.grid(row=0, column=0, sticky="ew")
    install_actions.columnconfigure((0, 1, 2), weight=1, uniform="install")

    apk_button = ttk.Button(install_actions, text="选择 APK", style="Install.TButton", command=choose_apk)
    apk_button.grid(row=0, column=0, sticky="ew", padx=(0, 10))
    aab_button = ttk.Button(install_actions, text="选择 AAB", style="Install.TButton", command=choose_aab)
    aab_button.grid(row=0, column=1, sticky="ew", padx=(0, 10))
    parse_button = ttk.Button(install_actions, text="解析安装包", style="Action.TButton", command=choose_package_for_parse)
    parse_button.grid(row=0, column=2, sticky="ew")

    path_panel = ttk.Frame(install_body, style="Inset.TFrame", padding=(12, 9, 12, 9))
    path_panel.grid(row=1, column=0, sticky="ew", pady=(14, 12))
    path_panel.columnconfigure(0, weight=1)
    selected_file_var = tk.StringVar(value="当前文件：未选择 APK / AAB / APKS / IPA")
    ttk.Label(path_panel, text="CURRENT FILE", style="Meta.TLabel").grid(row=0, column=0, sticky="w")
    ttk.Label(path_panel, textvariable=selected_file_var, style="Path.TLabel", wraplength=430, justify="left").grid(row=1, column=0, sticky="ew", pady=(4, 0))

    active_log_var = tk.StringVar(value=f"当前日志：{LOG_MODULES[current_log_module]}")
    active_log_label = ttk.Label(
        install_body,
        textvariable=active_log_var,
        style=ACTIVE_LOG_STYLES.get(current_log_module, "ActiveLogPackage.TLabel"),
    )
    active_log_label.grid(row=2, column=0, sticky="w", pady=(0, 8))

    console_panel = tk.Frame(
        install_body,
        bg=UI_CONSOLE_BG,
        highlightthickness=1,
        highlightbackground=UI_BORDER_SOFT,
        highlightcolor=BLUE,
        bd=0,
    )
    console_panel.grid(row=3, column=0, sticky="nsew")
    console_panel.columnconfigure(0, weight=1)
    console_panel.rowconfigure(0, weight=1)

    install_log_widget = tk.Text(
        console_panel,
        height=18,
        bg=UI_CONSOLE_BG,
        fg=UI_CONSOLE_TEXT,
        insertbackground=UI_CONSOLE_TEXT,
        selectbackground=BLUE,
        selectforeground="#FFFFFF",
        relief="flat",
        borderwidth=0,
        highlightthickness=0,
        font=("SF Mono", 11),
        padx=14,
        pady=12,
        wrap="word",
    )
    install_log_widget.grid(row=0, column=0, sticky="nsew")
    log_scrollbar = ttk.Scrollbar(console_panel, orient="vertical", command=install_log_widget.yview)
    log_scrollbar.grid(row=0, column=1, sticky="ns")
    install_log_widget.configure(yscrollcommand=log_scrollbar.set)
    append_install_log("[日志] 安装、解析进度会显示在这里。")
    select_log_module("package")
    bind_log_module_area(install_card.header, "package")  # type: ignore[attr-defined]
    bind_log_module_area(install_actions, "package")
    bind_log_module_area(path_panel, "package")

    footer = ttk.Frame(root_frame, style="Footer.TFrame", padding=(14, 10, 14, 10))
    footer.grid(row=2, column=0, sticky="ew", pady=(14, 0))
    footer.columnconfigure(0, weight=1)
    status_var = tk.StringVar(value="状态 · 等待操作（支持 Android/iOS 日志提取 / IDFA输出 / 截图录屏 / Firebase DebugView / 安装 / 解析）")
    status_label = ttk.Label(footer, textvariable=status_var, style="StatusNeutral.TLabel")
    status_label.grid(row=0, column=0, sticky="w")

    root.deiconify()
    root.lift()
    root.focus_force()
    root.mainloop()


if __name__ == "__main__":
    build_ui()
