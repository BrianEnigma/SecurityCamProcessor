"""Unit tests for main entry point: CLI validation, process guard, pipeline wiring."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import is_already_running, main  # noqa: E402


class TestCLIArgumentValidation:
    """Tests for CLI argument validation (Requirements 7.1, 7.2)."""

    def test_no_args_prints_usage_and_exits(self, capsys: pytest.CaptureFixture[str]) -> None:
        """With no arguments, should print usage and exit(1)."""
        with patch.object(sys, "argv", ["main.py"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Usage:" in captured.out

    def test_one_arg_prints_usage_and_exits(self, capsys: pytest.CaptureFixture[str]) -> None:
        """With only one argument, should print usage and exit(1)."""
        with patch.object(sys, "argv", ["main.py", "/input"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Usage:" in captured.out

    def test_three_args_prints_usage_and_exits(self, capsys: pytest.CaptureFixture[str]) -> None:
        """With three arguments (too many), should print usage and exit(1)."""
        with patch.object(sys, "argv", ["main.py", "/input", "/output", "/extra"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Usage:" in captured.out


class TestProcessGuard:
    """Tests for process guard detection (Requirements 7.3, 7.4)."""

    def test_already_running_returns_true_when_pgrep_finds_process(self) -> None:
        """is_already_running should return True when pgrep outputs PIDs."""
        mock_result = MagicMock()
        mock_result.stdout = b"12345\n67890\n"
        with patch("main.subprocess.run", return_value=mock_result) as mock_run:
            result = is_already_running()
        assert result is True
        mock_run.assert_called_once_with(
            ["pgrep", "-f", "main.py"],
            capture_output=True,
        )

    def test_already_running_returns_false_when_pgrep_empty(self) -> None:
        """is_already_running should return False when pgrep outputs nothing."""
        mock_result = MagicMock()
        mock_result.stdout = b""
        with patch("main.subprocess.run", return_value=mock_result):
            result = is_already_running()
        assert result is False

    def test_main_exits_zero_when_already_running(self, capsys: pytest.CaptureFixture[str]) -> None:
        """When another instance is running, main should exit(0) with a message."""
        with patch.object(sys, "argv", ["main.py", "/input", "/output"]):
            with patch("main.is_already_running", return_value=True):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "already running" in captured.out


class TestPipelineWiring:
    """Tests for pipeline wiring: Mover, Scanner, plugins (Requirements 7.5, 7.6, 7.7)."""

    @patch("main.Scanner")
    @patch("main.Summarizer")
    @patch("main.GifMaker")
    @patch("main.Tagger")
    @patch("main.Mover")
    @patch("main.is_already_running", return_value=False)
    def test_pipeline_creates_mover_with_correct_args(
        self,
        mock_guard: MagicMock,
        mock_mover_cls: MagicMock,
        mock_tagger_cls: MagicMock,
        mock_gifmaker_cls: MagicMock,
        mock_summarizer_cls: MagicMock,
        mock_scanner_cls: MagicMock,
    ) -> None:
        """Mover should be created with input_dir, output_dir, and stabilize_delay=2."""
        with patch.object(sys, "argv", ["main.py", "/my/input", "/my/output"]):
            main()
        mock_mover_cls.assert_called_once_with("/my/input", "/my/output", 2)
        mock_mover_cls.return_value.move.assert_called_once()

    @patch("main.Scanner")
    @patch("main.Summarizer")
    @patch("main.GifMaker")
    @patch("main.Tagger")
    @patch("main.Mover")
    @patch("main.is_already_running", return_value=False)
    def test_pipeline_creates_scanner_with_plugins(
        self,
        mock_guard: MagicMock,
        mock_mover_cls: MagicMock,
        mock_tagger_cls: MagicMock,
        mock_gifmaker_cls: MagicMock,
        mock_summarizer_cls: MagicMock,
        mock_scanner_cls: MagicMock,
    ) -> None:
        """Scanner should be created with output_dir, .mp4, [tagger, gifmaker], [summarizer]."""
        with patch.object(sys, "argv", ["main.py", "/my/input", "/my/output"]):
            main()
        mock_scanner_cls.assert_called_once_with(
            "/my/output",
            ".mp4",
            [mock_tagger_cls.return_value, mock_gifmaker_cls.return_value],
            [mock_summarizer_cls.return_value],
        )
        mock_scanner_cls.return_value.scan.assert_called_once()

    @patch("main.Scanner")
    @patch("main.Summarizer")
    @patch("main.GifMaker")
    @patch("main.Tagger")
    @patch("main.Mover")
    @patch("main.is_already_running", return_value=False)
    def test_pipeline_runs_mover_before_scanner(
        self,
        mock_guard: MagicMock,
        mock_mover_cls: MagicMock,
        mock_tagger_cls: MagicMock,
        mock_gifmaker_cls: MagicMock,
        mock_summarizer_cls: MagicMock,
        mock_scanner_cls: MagicMock,
    ) -> None:
        """Mover.move() should be called before Scanner.scan()."""
        call_order: list[str] = []
        mock_mover_cls.return_value.move.side_effect = lambda: call_order.append("mover")
        mock_scanner_cls.return_value.scan.side_effect = lambda: call_order.append("scanner")

        with patch.object(sys, "argv", ["main.py", "/in", "/out"]):
            main()

        assert call_order == ["mover", "scanner"]
