import unittest
from datetime import datetime, timedelta

import androidtools


class FakeRecordButton:
    def __init__(self) -> None:
        self.text = ""
        self.style = ""
        self.after_delay = None
        self.after_callback = None

    def config(self, **kwargs) -> None:
        if "text" in kwargs:
            self.text = kwargs["text"]

    def configure(self, **kwargs) -> None:
        if "style" in kwargs:
            self.style = kwargs["style"]

    def after(self, delay: int, callback):
        self.after_delay = delay
        self.after_callback = callback
        return "timer-id"


class RecordingUiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.old_record_button = androidtools.record_button
        self.old_record_start = androidtools.record_start
        self.old_record_proc = androidtools.record_proc
        self.old_segment_index = androidtools.segment_index
        self.old_timer_job = androidtools.timer_job
        self.old_last_record_log_second = androidtools.last_record_log_second
        self.old_record_progress_log_index = androidtools.record_progress_log_index
        self.old_module_log_history = androidtools.module_log_history
        androidtools.module_log_history = {key: [] for key in androidtools.LOG_MODULES}

    def tearDown(self) -> None:
        androidtools.record_button = self.old_record_button
        androidtools.record_start = self.old_record_start
        androidtools.record_proc = self.old_record_proc
        androidtools.segment_index = self.old_segment_index
        androidtools.timer_job = self.old_timer_job
        androidtools.last_record_log_second = self.old_last_record_log_second
        androidtools.record_progress_log_index = self.old_record_progress_log_index
        androidtools.module_log_history = self.old_module_log_history

    def test_record_button_text_stays_fixed_while_recording(self) -> None:
        button = FakeRecordButton()
        androidtools.record_button = button
        androidtools.record_start = datetime.now()
        androidtools.record_proc = None
        androidtools.segment_index = 1

        androidtools.update_timer_text()

        self.assertEqual("结束录屏", button.text)
        self.assertEqual("Danger.TButton", button.style)
        self.assertEqual(500, button.after_delay)

    def test_recording_progress_is_written_to_record_log(self) -> None:
        button = FakeRecordButton()
        androidtools.record_button = button
        androidtools.record_start = datetime.now() - timedelta(seconds=5)
        androidtools.record_proc = None
        androidtools.segment_index = 2
        androidtools.last_record_log_second = -1
        androidtools.record_progress_log_index = None

        androidtools.update_timer_text()

        log_text = "".join(androidtools.module_log_history["record"])
        self.assertIn("[状态] 已录制 00:00:05 · 当前第 2 段", log_text)

    def test_recording_progress_updates_one_live_log_line(self) -> None:
        androidtools.segment_index = 1
        androidtools.last_record_log_second = -1
        androidtools.record_progress_log_index = None

        androidtools.append_record_progress(5)
        androidtools.append_record_progress(6)

        status_lines = [line for line in androidtools.module_log_history["record"] if "[状态]" in line]
        self.assertEqual(1, len(status_lines))
        self.assertIn("00:00:06", status_lines[0])


if __name__ == "__main__":
    unittest.main()
