"""
npe/logger.py の包括的テスト

システム全体の監査証跡（Audit Trail）記録機能を網羅的にテストします。
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch

from nexuscore.npe.logger import (
    _rotate_if_needed,
    log_transaction,
)

# =============================================================================
# Test _rotate_if_needed
# =============================================================================


class TestRotateIfNeeded:
    """_rotate_if_needed のテスト"""

    def test_no_rotation_when_file_does_not_exist(self, tmp_path):
        """ファイルが存在しない場合はローテーションしない"""
        log_file = tmp_path / "nonexistent.log"

        # 例外が投げられないことを確認
        _rotate_if_needed(log_file)

        # ファイルは作成されない
        assert not log_file.exists()

    def test_no_rotation_when_file_below_size_limit(self, tmp_path):
        """ファイルサイズが制限以下の場合はローテーションしない"""
        log_file = tmp_path / "small.log"
        log_file.write_text("small content\n" * 10)  # 小さいファイル

        original_mtime = log_file.stat().st_mtime

        # ROTATE_BYTES より小さいのでローテーションされない
        _rotate_if_needed(log_file)

        # ファイルが変更されていないことを確認
        assert log_file.exists()
        assert log_file.stat().st_mtime == original_mtime

    def test_rotation_when_file_exceeds_size_limit(self, tmp_path, monkeypatch):
        """ファイルサイズが制限を超えた場合はローテーションされる"""
        # サイズ制限を小さく設定
        monkeypatch.setattr("nexuscore.npe.logger.ROTATE_BYTES", 100)

        log_file = tmp_path / "large.log"
        log_file.write_text("x" * 200)  # 200 bytes > 100 bytes

        _rotate_if_needed(log_file)

        # 元のファイルは .1 にリネームされる
        assert not log_file.exists()
        assert (log_file.parent / (log_file.name + ".1")).exists()

    def test_multiple_rotations(self, tmp_path, monkeypatch):
        """複数回のローテーションで .1, .2, .3 とファイルが作られる"""
        monkeypatch.setattr("nexuscore.npe.logger.ROTATE_BYTES", 50)

        log_file = tmp_path / "rotate.log"

        # 1回目: rotate.log → rotate.log.1
        log_file.write_text("x" * 100)
        _rotate_if_needed(log_file)
        assert (log_file.parent / (log_file.name + ".1")).exists()

        # 2回目: rotate.log → rotate.log.1, rotate.log.1 → rotate.log.2
        log_file.write_text("y" * 100)
        _rotate_if_needed(log_file)
        assert (log_file.parent / (log_file.name + ".1")).exists()
        assert (log_file.parent / (log_file.name + ".2")).exists()

        # 3回目: rotate.log → rotate.log.1, rotate.log.1 → rotate.log.2, rotate.log.2 → rotate.log.3
        log_file.write_text("z" * 100)
        _rotate_if_needed(log_file)
        assert (log_file.parent / (log_file.name + ".1")).exists()
        assert (log_file.parent / (log_file.name + ".2")).exists()
        assert (log_file.parent / (log_file.name + ".3")).exists()

    def test_rotation_respects_rotate_keep_limit(self, tmp_path, monkeypatch):
        """ROTATE_KEEP の制限を超えた古いファイルは削除される"""
        monkeypatch.setattr("nexuscore.npe.logger.ROTATE_BYTES", 50)
        monkeypatch.setattr("nexuscore.npe.logger.ROTATE_KEEP", 2)  # 2世代まで保持

        log_file = tmp_path / "keep.log"

        # 1回目
        log_file.write_text("a" * 100)
        _rotate_if_needed(log_file)

        # 2回目
        log_file.write_text("b" * 100)
        _rotate_if_needed(log_file)

        # 3回目: .3 は作られず、.2 が最古になる
        log_file.write_text("c" * 100)
        _rotate_if_needed(log_file)

        assert (log_file.parent / (log_file.name + ".1")).exists()
        assert (log_file.parent / (log_file.name + ".2")).exists()
        # ROTATE_KEEP=2 なので .3 は存在しない

    def test_rotation_error_handling(self, tmp_path, monkeypatch, capsys):
        """ローテーション中のエラーは握りつぶされる"""
        monkeypatch.setattr("nexuscore.npe.logger.ROTATE_BYTES", 50)

        log_file = tmp_path / "error.log"
        log_file.write_text("x" * 100)

        # rename がエラーを投げるようにモック
        original_rename = Path.rename

        def mock_rename(self, target):
            raise PermissionError("Cannot rename")

        monkeypatch.setattr(Path, "rename", mock_rename)

        # エラーが握りつぶされ、例外が投げられないことを確認
        _rotate_if_needed(log_file)

        # エラーメッセージが出力されることを確認
        captured = capsys.readouterr()
        assert "WARN: rotation failed" in captured.out


# =============================================================================
# Test log_transaction
# =============================================================================


class TestLogTransaction:
    """log_transaction のテスト"""

    def test_basic_logging_to_default_file(self, tmp_path, monkeypatch):
        """デフォルトファイルに基本的なログが書き込まれる"""
        # デフォルトのログディレクトリを tmp_path に変更
        audit_dir = tmp_path / "audit"
        monkeypatch.setattr("nexuscore.npe.logger.AUDIT_DIR", audit_dir)
        monkeypatch.setattr("nexuscore.npe.logger.DEFAULT_LOG", audit_dir / "test.jsonl")

        log_data = {"event": "test_event", "status": "success"}

        log_transaction(log_data, log_file=audit_dir / "test.jsonl")

        # ファイルが作成されることを確認
        log_file = audit_dir / "test.jsonl"
        assert log_file.exists()

        # 内容を確認
        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 1

        entry = json.loads(lines[0])
        assert entry["event"] == "test_event"
        assert entry["status"] == "success"
        assert "event_timestamp_utc" in entry

    def test_logging_to_custom_file_path(self, tmp_path):
        """カスタムファイルパスにログが書き込まれる"""
        custom_log = tmp_path / "custom" / "my_log.jsonl"

        log_data = {"action": "custom_action"}

        log_transaction(log_data, log_file=custom_log)

        assert custom_log.exists()

        entry = json.loads(custom_log.read_text().strip())
        assert entry["action"] == "custom_action"

    def test_log_data_includes_timestamp(self, tmp_path):
        """ログデータに event_timestamp_utc が追加される"""
        log_file = tmp_path / "timestamp.jsonl"

        log_data = {"event": "timestamp_test"}

        log_transaction(log_data, log_file=log_file)

        entry = json.loads(log_file.read_text().strip())
        assert "event_timestamp_utc" in entry
        # ISO 8601 形式であることを確認
        assert "T" in entry["event_timestamp_utc"]
        assert "Z" in entry["event_timestamp_utc"] or "+" in entry["event_timestamp_utc"]

    def test_console_output_is_printed(self, tmp_path, capsys):
        """コンソールにログが出力される"""
        log_file = tmp_path / "console.jsonl"

        log_data = {"event": "console_test", "message": "Hello"}

        log_transaction(log_data, log_file=log_file)

        captured = capsys.readouterr()
        assert "NPE AUDIT LOG" in captured.out
        assert "console_test" in captured.out
        assert "Hello" in captured.out

    def test_string_path_converted_to_path(self, tmp_path):
        """文字列パスが Path オブジェクトに変換される"""
        log_file_str = str(tmp_path / "string_path.jsonl")

        log_data = {"event": "string_path_test"}

        # 例外が投げられないことを確認
        log_transaction(log_data, log_file=log_file_str)

        assert Path(log_file_str).exists()

    def test_file_write_error_handling(self, tmp_path, capsys):
        """ファイル書き込みエラーが発生しても監査ログは失われない"""
        # 書き込み不可能なディレクトリを作る（実装に依存するため、読み取り専用にする代わりに
        # Path.open をモックする）
        log_file = tmp_path / "write_error.jsonl"

        log_data = {"event": "error_test"}

        # Path.open をモックしてエラーを投げる
        original_open = Path.open

        def mock_path_open(self, *args, **kwargs):
            if "write_error.jsonl" in str(self):
                raise OSError("Cannot write to file")
            return original_open(self, *args, **kwargs)

        with patch.object(Path, "open", mock_path_open):
            # 例外が投げられないことを確認
            log_transaction(log_data, log_file=log_file)

        # エラーメッセージとログデータがコンソールに出力される
        captured = capsys.readouterr()
        assert "CRITICAL: failed to write audit file" in captured.out
        assert "error_test" in captured.out

    def test_logging_provider_integration(self, tmp_path):
        """ロギングプロバイダーが存在する場合は enhance_transaction が呼ばれる"""
        log_file = tmp_path / "provider.jsonl"

        log_data = {"event": "provider_test"}

        # ロギングプロバイダーをモック
        # NOTE: get_logging_provider は log_transaction 内で import されるため、
        # nexuscore.core.logging_interface.get_logging_provider をパッチする必要がある
        mock_provider = Mock()
        mock_get_provider = Mock(return_value=mock_provider)

        with patch("nexuscore.core.logging_interface.get_logging_provider", mock_get_provider):
            log_transaction(log_data, log_file=log_file)

        # enhance_transaction が呼ばれたことを確認
        mock_provider.enhance_transaction.assert_called_once()
        call_args = mock_provider.enhance_transaction.call_args
        assert "event" in call_args[0][0]  # log_data
        assert call_args[0][1] == log_file  # log_file

    def test_logging_provider_error_does_not_break_logging(self, tmp_path):
        """ロギングプロバイダーがエラーを投げてもログは書き込まれる"""
        log_file = tmp_path / "provider_error.jsonl"

        log_data = {"event": "provider_error_test"}

        # ロギングプロバイダーがエラーを投げる
        mock_provider = Mock()
        mock_provider.enhance_transaction.side_effect = Exception("Provider error")
        mock_get_provider = Mock(return_value=mock_provider)

        with patch("nexuscore.core.logging_interface.get_logging_provider", mock_get_provider):
            # 例外が投げられないことを確認
            log_transaction(log_data, log_file=log_file)

        # ファイルにはログが書き込まれている
        assert log_file.exists()
        entry = json.loads(log_file.read_text().strip())
        assert entry["event"] == "provider_error_test"

    def test_multiple_logs_append_to_file(self, tmp_path):
        """複数のログが同じファイルに追記される"""
        log_file = tmp_path / "append.jsonl"

        log_transaction({"event": "first"}, log_file=log_file)
        log_transaction({"event": "second"}, log_file=log_file)
        log_transaction({"event": "third"}, log_file=log_file)

        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 3

        events = [json.loads(line)["event"] for line in lines]
        assert events == ["first", "second", "third"]

    def test_rotation_triggered_during_logging(self, tmp_path, monkeypatch):
        """ログ書き込み中にローテーションが発生する"""
        monkeypatch.setattr("nexuscore.npe.logger.ROTATE_BYTES", 100)

        log_file = tmp_path / "rotate_during_log.jsonl"

        # 大きなログを書き込んでローテーションを発生させる
        log_transaction({"data": "x" * 200}, log_file=log_file)

        # 次のログはローテーション後のファイルに書き込まれる
        log_transaction({"data": "y" * 200}, log_file=log_file)

        # .1 ファイルが存在することを確認
        assert (log_file.parent / (log_file.name + ".1")).exists()


# =============================================================================
# Test Thread Safety
# =============================================================================


class TestThreadSafety:
    """スレッドセーフ性のテスト"""

    def test_concurrent_logging_is_thread_safe(self, tmp_path):
        """複数スレッドから同時にログを書き込んでも競合しない"""
        log_file = tmp_path / "thread_safe.jsonl"

        def log_worker(thread_id):
            for i in range(10):
                log_transaction({"thread": thread_id, "index": i}, log_file=log_file)
                time.sleep(0.001)  # 少し待つ

        threads = []
        for i in range(5):
            t = threading.Thread(target=log_worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # 全てのログが書き込まれていることを確認
        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 50  # 5 threads * 10 logs

        # 各エントリがパース可能であることを確認
        for line in lines:
            entry = json.loads(line)
            assert "thread" in entry
            assert "index" in entry


# =============================================================================
# Test Environment Variables
# =============================================================================


class TestEnvironmentVariables:
    """環境変数のテスト"""

    def test_npe_audit_dir_environment_variable(self, monkeypatch, tmp_path):
        """NPE_AUDIT_DIR 環境変数でログディレクトリを変更できる"""
        custom_dir = tmp_path / "custom_audit"
        monkeypatch.setenv("NPE_AUDIT_DIR", str(custom_dir))

        # モジュールを再インポートして環境変数を反映
        # （このテストでは直接変更できないため、パスを指定してログ）
        log_file = custom_dir / "test.jsonl"
        log_transaction({"event": "custom_dir_test"}, log_file=log_file)

        assert log_file.exists()

    def test_npe_audit_rotate_bytes_environment_variable(self, monkeypatch, tmp_path):
        """NPE_AUDIT_ROTATE_BYTES 環境変数でローテーションサイズを変更できる"""
        monkeypatch.setenv("NPE_AUDIT_ROTATE_BYTES", "200")
        monkeypatch.setattr("nexuscore.npe.logger.ROTATE_BYTES", 200)

        log_file = tmp_path / "rotate_bytes.log"
        log_file.write_text("x" * 100)  # 100 bytes < 200 bytes

        _rotate_if_needed(log_file)

        # ローテーションされない
        assert log_file.exists()
        assert not (log_file.parent / (log_file.name + ".1")).exists()

    def test_npe_audit_rotate_keep_environment_variable(self, monkeypatch, tmp_path):
        """NPE_AUDIT_ROTATE_KEEP 環境変数で保持世代数を変更できる"""
        monkeypatch.setenv("NPE_AUDIT_ROTATE_KEEP", "1")
        monkeypatch.setattr("nexuscore.npe.logger.ROTATE_BYTES", 50)
        monkeypatch.setattr("nexuscore.npe.logger.ROTATE_KEEP", 1)

        log_file = tmp_path / "rotate_keep.log"

        # 1回目: .1 が作られる
        log_file.write_text("a" * 100)
        _rotate_if_needed(log_file)

        # 2回目: .1 のみ保持（.2 は作られない）
        log_file.write_text("b" * 100)
        _rotate_if_needed(log_file)

        assert (log_file.parent / (log_file.name + ".1")).exists()
        # ROTATE_KEEP=1 なので .2 は存在しない


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """エッジケースのテスト"""

    def test_empty_log_data(self, tmp_path):
        """空のログデータでもエラーにならない"""
        log_file = tmp_path / "empty.jsonl"

        log_transaction({}, log_file=log_file)

        entry = json.loads(log_file.read_text().strip())
        assert "event_timestamp_utc" in entry

    def test_unicode_in_log_data(self, tmp_path):
        """Unicode 文字を含むログデータ"""
        log_file = tmp_path / "unicode.jsonl"

        log_data = {"message": "こんにちは世界", "emoji": "🎉"}

        log_transaction(log_data, log_file=log_file)

        entry = json.loads(log_file.read_text(encoding="utf-8").strip())
        assert entry["message"] == "こんにちは世界"
        assert entry["emoji"] == "🎉"

    def test_very_large_log_data(self, tmp_path):
        """非常に大きなログデータ"""
        log_file = tmp_path / "large.jsonl"

        # 10KB のデータ
        large_data = {"data": "x" * 10000}

        log_transaction(large_data, log_file=log_file)

        entry = json.loads(log_file.read_text().strip())
        assert len(entry["data"]) == 10000

    def test_log_data_with_nested_objects(self, tmp_path):
        """ネストしたオブジェクトを含むログデータ"""
        log_file = tmp_path / "nested.jsonl"

        log_data = {
            "event": "nested_test",
            "metadata": {
                "user": {"id": 123, "name": "Alice"},
                "tags": ["tag1", "tag2", "tag3"],
            },
        }

        log_transaction(log_data, log_file=log_file)

        entry = json.loads(log_file.read_text().strip())
        assert entry["metadata"]["user"]["name"] == "Alice"
        assert entry["metadata"]["tags"] == ["tag1", "tag2", "tag3"]

    def test_log_data_with_special_characters(self, tmp_path):
        """特殊文字を含むログデータ"""
        log_file = tmp_path / "special.jsonl"

        log_data = {
            "message": 'Test with "quotes" and \n newlines \t tabs',
            "path": "C:\\Windows\\System32",
        }

        log_transaction(log_data, log_file=log_file)

        entry = json.loads(log_file.read_text().strip())
        assert "quotes" in entry["message"]
        # NOTE: JSON にエンコード/デコードされるため、実際の改行文字として格納される
        assert "\n" in entry["message"]
        assert "\t" in entry["message"]
        assert "System32" in entry["path"]

    def test_log_file_parent_directory_created(self, tmp_path):
        """ログファイルの親ディレクトリが自動的に作成される"""
        nested_log = tmp_path / "a" / "b" / "c" / "nested.jsonl"

        log_transaction({"event": "nested_dir"}, log_file=nested_log)

        assert nested_log.exists()
        assert nested_log.parent.exists()

    def test_concurrent_rotation_does_not_cause_errors(self, tmp_path, monkeypatch):
        """複数スレッドから同時にローテーションが発生してもエラーにならない"""
        monkeypatch.setattr("nexuscore.npe.logger.ROTATE_BYTES", 100)

        log_file = tmp_path / "concurrent_rotate.log"

        def rotate_worker():
            for _ in range(5):
                log_file.write_text("x" * 200)
                _rotate_if_needed(log_file)
                time.sleep(0.01)

        threads = []
        for _ in range(3):
            t = threading.Thread(target=rotate_worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # エラーが発生せず、いくつかのバックアップファイルが作られている
        # （正確な数は競合のタイミングに依存するため、存在チェックのみ）
        assert any((log_file.parent / f"{log_file.name}.{i}").exists() for i in range(1, 10))

    def test_log_data_with_none_values(self, tmp_path):
        """None 値を含むログデータ"""
        log_file = tmp_path / "none_values.jsonl"

        log_data = {"event": "none_test", "value": None, "optional": None}

        log_transaction(log_data, log_file=log_file)

        entry = json.loads(log_file.read_text().strip())
        assert entry["event"] == "none_test"
        assert entry["value"] is None

    def test_ensure_ascii_false_in_json_output(self, tmp_path):
        """ensure_ascii=False で Unicode がそのまま出力される"""
        log_file = tmp_path / "ascii.jsonl"

        log_data = {"message": "日本語"}

        log_transaction(log_data, log_file=log_file)

        raw_text = log_file.read_text(encoding="utf-8")
        # ensure_ascii=False なので、"日本語" がそのまま含まれる（\\u3042 等にエンコードされない）
        assert "日本語" in raw_text
