"""
Comprehensive tests for log_monitor module.
Tests legacy auto-repair file watcher functionality.
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, call


# ==============================================================================
# Module Import and Initialization Tests
# ==============================================================================


class TestLogMonitorImport:
    """Test log_monitor module import behavior"""

    def test_module_constants(self):
        """Module defines expected constants"""
        # Import in test to avoid side effects
        import sys
        import importlib

        # Remove module if already imported
        if 'nexuscore.utils.log_monitor' in sys.modules:
            del sys.modules['nexuscore.utils.log_monitor']

        # Mock auto_cycle_manager before import
        mock_auto = MagicMock()
        sys.modules['auto_cycle_manager'] = mock_auto

        # Mock threading to prevent daemon thread start
        with patch('threading.Thread'):
            import nexuscore.utils.log_monitor as log_monitor

            assert hasattr(log_monitor, 'LOG_FILE')
            assert log_monitor.LOG_FILE == "run.log"
            assert hasattr(log_monitor, 'WATCH_DIR')
            assert log_monitor.WATCH_DIR == "watch_folder"
            assert hasattr(log_monitor, 'already_seen')
            assert isinstance(log_monitor.already_seen, set)

        # Clean up
        del sys.modules['auto_cycle_manager']
        if 'nexuscore.utils.log_monitor' in sys.modules:
            del sys.modules['nexuscore.utils.log_monitor']


# ==============================================================================
# log_watcher Function Tests
# ==============================================================================


class TestLogWatcher:
    """Test log_watcher function"""

    @pytest.fixture(autouse=True)
    def setup_module_mock(self):
        """Set up mock for auto_cycle_manager"""
        import sys
        self.mock_auto = MagicMock()
        self.mock_auto.auto_repair_cycle = MagicMock(return_value=("fixed_code", "output"))
        sys.modules['auto_cycle_manager'] = self.mock_auto
        yield
        # Clean up
        if 'auto_cycle_manager' in sys.modules:
            del sys.modules['auto_cycle_manager']
        if 'nexuscore.utils.log_monitor' in sys.modules:
            del sys.modules['nexuscore.utils.log_monitor']

    def test_log_watcher_detects_new_file(self):
        """log_watcher detects and processes new .py file"""
        import sys

        # Mock threading to prevent daemon thread start
        with patch('threading.Thread'):
            import nexuscore.utils.log_monitor as log_monitor

        # Reset already_seen
        log_monitor.already_seen.clear()

        test_code = "def test():\n    pass"

        with patch('os.listdir', return_value=['test.py']), \
             patch('builtins.open', mock_open(read_data=test_code)) as mock_file, \
             patch('time.sleep', side_effect=[None, KeyboardInterrupt]):  # Stop after 1 iteration

            try:
                log_monitor.log_watcher()
            except KeyboardInterrupt:
                pass

            # Verify auto_repair_cycle was called
            self.mock_auto.auto_repair_cycle.assert_called_once_with(test_code)

            # Verify file was written
            write_calls = [c for c in mock_file().write.call_args_list]
            assert len(write_calls) > 0
            assert write_calls[0][0][0] == "fixed_code"

    def test_log_watcher_ignores_non_py_files(self):
        """log_watcher ignores non-.py files"""
        import sys

        with patch('threading.Thread'):
            import nexuscore.utils.log_monitor as log_monitor

        log_monitor.already_seen.clear()

        with patch('os.listdir', return_value=['test.txt', 'readme.md', 'data.json']), \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('time.sleep', side_effect=[None, KeyboardInterrupt]):

            try:
                log_monitor.log_watcher()
            except KeyboardInterrupt:
                pass

            # auto_repair_cycle should not be called for non-.py files
            self.mock_auto.auto_repair_cycle.assert_not_called()

    def test_log_watcher_ignores_already_seen_files(self):
        """log_watcher ignores files already in already_seen"""
        import sys

        with patch('threading.Thread'):
            import nexuscore.utils.log_monitor as log_monitor

        log_monitor.already_seen.clear()
        log_monitor.already_seen.add('seen.py')

        with patch('os.listdir', return_value=['seen.py']), \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('time.sleep', side_effect=[None, KeyboardInterrupt]):

            try:
                log_monitor.log_watcher()
            except KeyboardInterrupt:
                pass

            # auto_repair_cycle should not be called for already seen files
            self.mock_auto.auto_repair_cycle.assert_not_called()

    def test_log_watcher_processes_multiple_new_files(self):
        """log_watcher processes multiple new .py files"""
        import sys

        with patch('threading.Thread'):
            import nexuscore.utils.log_monitor as log_monitor

        log_monitor.already_seen.clear()

        test_code = "def test():\n    pass"

        with patch('os.listdir', return_value=['file1.py', 'file2.py', 'file3.py']), \
             patch('builtins.open', mock_open(read_data=test_code)) as mock_file, \
             patch('time.sleep', side_effect=[None, KeyboardInterrupt]):

            try:
                log_monitor.log_watcher()
            except KeyboardInterrupt:
                pass

            # auto_repair_cycle should be called 3 times
            assert self.mock_auto.auto_repair_cycle.call_count == 3

    def test_log_watcher_adds_files_to_already_seen(self):
        """log_watcher adds processed files to already_seen"""
        import sys

        with patch('threading.Thread'):
            import nexuscore.utils.log_monitor as log_monitor

        log_monitor.already_seen.clear()

        test_code = "def test():\n    pass"

        with patch('os.listdir', return_value=['new_file.py']), \
             patch('builtins.open', mock_open(read_data=test_code)), \
             patch('time.sleep', side_effect=[None, KeyboardInterrupt]):

            try:
                log_monitor.log_watcher()
            except KeyboardInterrupt:
                pass

            assert 'new_file.py' in log_monitor.already_seen

    def test_log_watcher_creates_fixed_file(self):
        """log_watcher creates _fixed.py file"""
        import sys

        with patch('threading.Thread'):
            import nexuscore.utils.log_monitor as log_monitor

        log_monitor.already_seen.clear()

        test_code = "def test():\n    pass"
        fixed_code = "def test():\n    return True"
        self.mock_auto.auto_repair_cycle.return_value = (fixed_code, "output")

        with patch('os.listdir', return_value=['script.py']), \
             patch('builtins.open', mock_open(read_data=test_code)) as mock_file, \
             patch('time.sleep', side_effect=[None, KeyboardInterrupt]):

            try:
                log_monitor.log_watcher()
            except KeyboardInterrupt:
                pass

            # Check that fixed file was opened for writing
            open_calls = mock_file.call_args_list
            write_paths = [str(call[0][0]) for call in open_calls if len(call[0]) > 0]

            # Should have opened watch_folder/script_fixed.py for writing
            assert any('script_fixed.py' in path for path in write_paths)

    def test_log_watcher_sleeps_between_iterations(self):
        """log_watcher sleeps 10 seconds between iterations"""
        import sys

        with patch('threading.Thread'):
            import nexuscore.utils.log_monitor as log_monitor

        log_monitor.already_seen.clear()

        with patch('os.listdir', return_value=[]), \
             patch('time.sleep', side_effect=[None, None, KeyboardInterrupt]) as mock_sleep:

            try:
                log_monitor.log_watcher()
            except KeyboardInterrupt:
                pass

            # Verify sleep was called with 10 seconds
            sleep_calls = [c[0][0] for c in mock_sleep.call_args_list if c[0]]
            assert 10 in sleep_calls

    def test_log_watcher_reads_file_with_utf8(self):
        """log_watcher reads files with UTF-8 encoding"""
        import sys

        with patch('threading.Thread'):
            import nexuscore.utils.log_monitor as log_monitor

        log_monitor.already_seen.clear()

        test_code = "# 日本語コメント\ndef test():\n    pass"

        with patch('os.listdir', return_value=['unicode_test.py']), \
             patch('builtins.open', mock_open(read_data=test_code)) as mock_file, \
             patch('time.sleep', side_effect=[None, KeyboardInterrupt]):

            try:
                log_monitor.log_watcher()
            except KeyboardInterrupt:
                pass

            # Verify auto_repair_cycle was called with UTF-8 content
            # This confirms the file was read successfully
            self.mock_auto.auto_repair_cycle.assert_called_once_with(test_code)

    def test_log_watcher_infinite_loop(self):
        """log_watcher runs in infinite loop"""
        import sys

        with patch('threading.Thread'):
            import nexuscore.utils.log_monitor as log_monitor

        log_monitor.already_seen.clear()

        iteration_count = 0

        def sleep_side_effect(seconds):
            nonlocal iteration_count
            iteration_count += 1
            if iteration_count >= 3:
                raise KeyboardInterrupt

        with patch('os.listdir', return_value=[]), \
             patch('time.sleep', side_effect=sleep_side_effect):

            try:
                log_monitor.log_watcher()
            except KeyboardInterrupt:
                pass

            # Verify multiple iterations occurred
            assert iteration_count == 3


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestLogMonitorIntegration:
    """Integration tests for log_monitor module"""

    @pytest.fixture(autouse=True)
    def setup_module_mock(self):
        """Set up mock for auto_cycle_manager"""
        import sys
        self.mock_auto = MagicMock()
        self.mock_auto.auto_repair_cycle = MagicMock(return_value=("fixed_code", "output"))
        sys.modules['auto_cycle_manager'] = self.mock_auto
        yield
        # Clean up
        if 'auto_cycle_manager' in sys.modules:
            del sys.modules['auto_cycle_manager']
        if 'nexuscore.utils.log_monitor' in sys.modules:
            del sys.modules['nexuscore.utils.log_monitor']

    def test_full_workflow_new_file_detection(self):
        """Full workflow: detect new file, repair, save fixed version"""
        import sys

        with patch('threading.Thread'):
            import nexuscore.utils.log_monitor as log_monitor

        log_monitor.already_seen.clear()

        original_code = "def broken():\n    x = 1/0"
        fixed_code = "def broken():\n    try:\n        x = 1/0\n    except ZeroDivisionError:\n        pass"
        self.mock_auto.auto_repair_cycle.return_value = (fixed_code, "Fixed division by zero")

        with patch('os.listdir', return_value=['broken.py']), \
             patch('builtins.open', mock_open(read_data=original_code)) as mock_file, \
             patch('time.sleep', side_effect=[None, KeyboardInterrupt]):

            try:
                log_monitor.log_watcher()
            except KeyboardInterrupt:
                pass

            # Verify auto_repair_cycle called with original code
            self.mock_auto.auto_repair_cycle.assert_called_once_with(original_code)

            # Verify write was called (fixed file was created)
            assert mock_file().write.called
            # Verify the fixed code was written
            write_args = [call[0][0] for call in mock_file().write.call_args_list]
            assert fixed_code in write_args

            # Verify file added to already_seen
            assert 'broken.py' in log_monitor.already_seen

    def test_second_iteration_ignores_seen_files(self):
        """Second iteration ignores files seen in first iteration"""
        import sys

        with patch('threading.Thread'):
            import nexuscore.utils.log_monitor as log_monitor

        log_monitor.already_seen.clear()

        test_code = "def test():\n    pass"
        iteration = [0]

        def listdir_side_effect(path):
            iteration[0] += 1
            return ['same_file.py']

        def sleep_side_effect(seconds):
            if iteration[0] >= 2:
                raise KeyboardInterrupt

        with patch('os.listdir', side_effect=listdir_side_effect), \
             patch('builtins.open', mock_open(read_data=test_code)), \
             patch('time.sleep', side_effect=sleep_side_effect):

            try:
                log_monitor.log_watcher()
            except KeyboardInterrupt:
                pass

            # auto_repair_cycle should only be called once (first iteration)
            assert self.mock_auto.auto_repair_cycle.call_count == 1


# ==============================================================================
# Edge Cases
# ==============================================================================


class TestLogMonitorEdgeCases:
    """Test edge cases for log_monitor module"""

    @pytest.fixture(autouse=True)
    def setup_module_mock(self):
        """Set up mock for auto_cycle_manager"""
        import sys
        self.mock_auto = MagicMock()
        self.mock_auto.auto_repair_cycle = MagicMock(return_value=("fixed_code", "output"))
        sys.modules['auto_cycle_manager'] = self.mock_auto
        yield
        # Clean up
        if 'auto_cycle_manager' in sys.modules:
            del sys.modules['auto_cycle_manager']
        if 'nexuscore.utils.log_monitor' in sys.modules:
            del sys.modules['nexuscore.utils.log_monitor']

    def test_empty_watch_directory(self):
        """Handle empty watch directory"""
        import sys

        with patch('threading.Thread'):
            import nexuscore.utils.log_monitor as log_monitor

        log_monitor.already_seen.clear()

        with patch('os.listdir', return_value=[]), \
             patch('time.sleep', side_effect=[None, KeyboardInterrupt]):

            try:
                log_monitor.log_watcher()
            except KeyboardInterrupt:
                pass

            # Should not crash, auto_repair_cycle not called
            self.mock_auto.auto_repair_cycle.assert_not_called()

    def test_file_with_special_characters_in_name(self):
        """Handle .py file with special characters in name"""
        import sys

        with patch('threading.Thread'):
            import nexuscore.utils.log_monitor as log_monitor

        log_monitor.already_seen.clear()

        test_code = "def test():\n    pass"

        with patch('os.listdir', return_value=['test-file_2024.py']), \
             patch('builtins.open', mock_open(read_data=test_code)), \
             patch('time.sleep', side_effect=[None, KeyboardInterrupt]):

            try:
                log_monitor.log_watcher()
            except KeyboardInterrupt:
                pass

            # Should process file normally
            self.mock_auto.auto_repair_cycle.assert_called_once()
            assert 'test-file_2024.py' in log_monitor.already_seen

    def test_mixed_file_types(self):
        """Process only .py files from mixed file types"""
        import sys

        with patch('threading.Thread'):
            import nexuscore.utils.log_monitor as log_monitor

        log_monitor.already_seen.clear()

        test_code = "def test():\n    pass"

        files = ['test.py', 'data.json', 'readme.md', 'script.py', 'image.png']

        with patch('os.listdir', return_value=files), \
             patch('builtins.open', mock_open(read_data=test_code)), \
             patch('time.sleep', side_effect=[None, KeyboardInterrupt]):

            try:
                log_monitor.log_watcher()
            except KeyboardInterrupt:
                pass

            # Should process only 2 .py files
            assert self.mock_auto.auto_repair_cycle.call_count == 2
            assert 'test.py' in log_monitor.already_seen
            assert 'script.py' in log_monitor.already_seen
            assert 'data.json' not in log_monitor.already_seen

    def test_empty_py_file(self):
        """Handle empty .py file"""
        import sys

        with patch('threading.Thread'):
            import nexuscore.utils.log_monitor as log_monitor

        log_monitor.already_seen.clear()

        with patch('os.listdir', return_value=['empty.py']), \
             patch('builtins.open', mock_open(read_data="")), \
             patch('time.sleep', side_effect=[None, KeyboardInterrupt]):

            try:
                log_monitor.log_watcher()
            except KeyboardInterrupt:
                pass

            # Should process empty file
            self.mock_auto.auto_repair_cycle.assert_called_once_with("")
            assert 'empty.py' in log_monitor.already_seen
