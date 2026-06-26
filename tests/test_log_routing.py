import unittest

import androidtools


class FakeText:
    def __init__(self) -> None:
        self.content = ""
        self.seen = False

    def insert(self, _index: str, text: str) -> None:
        self.content += text

    def delete(self, _start: str, _end: str) -> None:
        self.content = ""

    def see(self, _index: str) -> None:
        self.seen = True


class FakeLabel:
    def __init__(self) -> None:
        self.configured: dict[str, object] = {}

    def configure(self, **kwargs) -> None:
        self.configured.update(kwargs)


class FakeWidget:
    def __init__(self, widget_class: str = "Frame", children: list["FakeWidget"] | None = None) -> None:
        self.widget_class = widget_class
        self.children = children or []
        self.bindings: dict[str, object] = {}

    def bind(self, event_name: str, callback: object, add: str | None = None) -> None:
        self.bindings[event_name] = (callback, add)

    def winfo_children(self) -> list["FakeWidget"]:
        return self.children

    def winfo_class(self) -> str:
        return self.widget_class


class LogRoutingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.widget = FakeText()
        androidtools.install_log_widget = self.widget
        androidtools.active_log_var = None
        androidtools.active_log_label = None
        androidtools.current_log_module = "package"
        androidtools.module_log_history = {key: [] for key in androidtools.LOG_MODULES}

    def tearDown(self) -> None:
        androidtools.install_log_widget = None
        androidtools.active_log_var = None
        androidtools.active_log_label = None

    def test_appends_only_render_for_active_module(self) -> None:
        androidtools.append_module_log("screenshot", "[选择] 立即截图")

        self.assertEqual("", self.widget.content)

        androidtools.select_log_module("screenshot")

        self.assertIn("[选择] 立即截图", self.widget.content)
        self.assertTrue(self.widget.seen)

    def test_switching_modules_keeps_logs_independent(self) -> None:
        androidtools.append_module_log("package", "[选择] APK：demo.apk")
        androidtools.append_module_log("record", "[选择] 开始录屏")

        androidtools.select_log_module("record")
        self.assertIn("[选择] 开始录屏", self.widget.content)
        self.assertNotIn("demo.apk", self.widget.content)

        androidtools.select_log_module("package")
        self.assertIn("demo.apk", self.widget.content)
        self.assertNotIn("开始录屏", self.widget.content)

    def test_active_log_label_style_follows_selected_module(self) -> None:
        label = FakeLabel()
        androidtools.active_log_label = label

        androidtools.select_log_module("firebase")
        self.assertEqual("ActiveLogFirebase.TLabel", label.configured["style"])

        androidtools.select_log_module("record")
        self.assertEqual("ActiveLogRecord.TLabel", label.configured["style"])

    def test_module_click_binding_includes_card_text_but_skips_buttons(self) -> None:
        button = FakeWidget("TButton")
        label = FakeWidget("TLabel")
        nested_frame = FakeWidget("TFrame", [label, button])
        card = FakeWidget("TFrame", [nested_frame])

        androidtools.bind_log_module_area(card, "record")

        self.assertIn("<Button-1>", card.bindings)
        self.assertIn("<Button-1>", nested_frame.bindings)
        self.assertIn("<Button-1>", label.bindings)
        self.assertNotIn("<Button-1>", button.bindings)

    def test_module_click_binding_skips_excluded_log_area(self) -> None:
        text_widget = FakeWidget("Text")
        console_frame = FakeWidget("Frame", [text_widget])
        card = FakeWidget("TFrame", [console_frame])

        androidtools.bind_log_module_area(card, "package", exclude={console_frame})

        self.assertIn("<Button-1>", card.bindings)
        self.assertNotIn("<Button-1>", console_frame.bindings)
        self.assertNotIn("<Button-1>", text_widget.bindings)


if __name__ == "__main__":
    unittest.main()
