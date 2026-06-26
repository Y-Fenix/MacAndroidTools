import subprocess
import unittest
from pathlib import Path

import androidtools


class FirebaseDebugViewTest(unittest.TestCase):
    def setUp(self) -> None:
        self.old_module_log_history = androidtools.module_log_history
        self.old_current_log_module = androidtools.current_log_module
        self.old_ensure_adb_ready = androidtools.ensure_adb_ready
        self.old_run_adb = androidtools.run_adb
        self.old_parse_apk_metadata = androidtools.parse_apk_metadata
        self.old_firebase_debug_package = getattr(androidtools, "firebase_debug_package", "")
        self.old_firebase_package_var = getattr(androidtools, "firebase_package_var", None)

        androidtools.module_log_history = {key: [] for key in androidtools.LOG_MODULES}
        androidtools.current_log_module = "package"

    def tearDown(self) -> None:
        androidtools.module_log_history = self.old_module_log_history
        androidtools.current_log_module = self.old_current_log_module
        androidtools.ensure_adb_ready = self.old_ensure_adb_ready
        androidtools.run_adb = self.old_run_adb
        androidtools.parse_apk_metadata = self.old_parse_apk_metadata
        androidtools.firebase_debug_package = self.old_firebase_debug_package
        androidtools.firebase_package_var = self.old_firebase_package_var

    def test_builds_firebase_debugview_setprop_command(self) -> None:
        command = androidtools.build_firebase_debugview_command("com.example.game")

        self.assertEqual(
            ["shell", "setprop", "debug.firebase.analytics.app", "com.example.game"],
            command,
        )

    def test_enable_firebase_debugview_runs_adb_setprop(self) -> None:
        calls: list[list[str]] = []
        androidtools.module_log_history.setdefault("firebase", [])
        androidtools.firebase_debug_package = "com.example.game"
        androidtools.ensure_adb_ready = lambda: True

        def fake_run_adb(command: list[str]) -> subprocess.CompletedProcess:
            calls.append(command)
            return subprocess.CompletedProcess(command, 0, stdout=b"", stderr=b"")

        androidtools.run_adb = fake_run_adb

        androidtools.enable_firebase_debugview()

        self.assertEqual(
            [["shell", "setprop", "debug.firebase.analytics.app", "com.example.game"]],
            calls,
        )
        log_text = "".join(androidtools.module_log_history["firebase"])
        self.assertIn("[完成] Firebase DebugView 已开启：com.example.game", log_text)
        self.assertEqual("firebase", androidtools.current_log_module)

    def test_select_firebase_debug_package_reads_bundle_id_from_apk(self) -> None:
        androidtools.module_log_history.setdefault("firebase", [])

        def fake_parse_apk_metadata(_path: Path) -> dict[str, str]:
            return {
                "包类型": "APK",
                "bundle_ID": "com.example.game",
                "内存大小": "1 MB",
                "构建版本号": "1",
                "版本名称": "1.0",
            }

        androidtools.parse_apk_metadata = fake_parse_apk_metadata

        androidtools.run_select_firebase_debug_package(Path("/tmp/demo.apk"))

        self.assertEqual("com.example.game", androidtools.firebase_debug_package)
        log_text = "".join(androidtools.module_log_history["firebase"])
        self.assertIn("[选择] Firebase DebugView 文件：/tmp/demo.apk", log_text)
        self.assertIn("[目标] 包名：com.example.game", log_text)


if __name__ == "__main__":
    unittest.main()
