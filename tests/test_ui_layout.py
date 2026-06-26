import inspect
import unittest

import androidtools


class FakeFrame:
    def __init__(self, _parent=None, **_kwargs) -> None:
        self.column_calls: list[tuple[object, dict[str, object]]] = []

    def columnconfigure(self, columns, **kwargs) -> None:
        self.column_calls.append((columns, kwargs))


class UiLayoutTest(unittest.TestCase):
    def test_button_bar_uses_three_equal_columns_by_default(self) -> None:
        old_frame = androidtools.ttk.Frame
        try:
            androidtools.ttk.Frame = FakeFrame

            bar = androidtools.build_button_bar(object())
        finally:
            androidtools.ttk.Frame = old_frame

        self.assertEqual(((0, 1, 2), {"weight": 1, "uniform": "action"}), bar.column_calls[0])

    def test_screenshot_and_recording_are_split_into_two_rows(self) -> None:
        source = inspect.getsource(androidtools.build_ui)

        self.assertIn("screenshot_row = ttk.Frame(media_body", source)
        self.assertIn("record_row = ttk.Frame(media_body", source)
        self.assertIn("screenshot_actions = build_button_bar(screenshot_row)", source)
        self.assertIn("record_actions = build_button_bar(record_row)", source)
        self.assertNotIn("media_actions = build_button_bar(media_body, columns=4)", source)

    def test_firebase_debugview_is_not_embedded_in_right_install_actions(self) -> None:
        source = inspect.getsource(androidtools.build_ui)

        self.assertNotIn("firebase_actions_right", source)
        self.assertIn("firebase_actions = build_button_bar(firebase_body)", source)
        self.assertIn('firebase_button = ttk.Button(firebase_actions, text="开启 DebugView", style="Debug.TButton"', source)
        self.assertNotIn("firebase_target_panel", source)
        self.assertNotIn("FIREBASE TARGET", source)


if __name__ == "__main__":
    unittest.main()
