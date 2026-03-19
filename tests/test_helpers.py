"""
Unit tests for Telegram MCP Server helper functions.

Run with:  pytest tests/ -v
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

# Import the helpers we want to test — these are pure functions
# that don't require a Telegram connection.
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server import _ok, _err, _validate_file, _check_file_size, _RateLimiter


# ──────────────────────────────────────────────────────────────────────────────
# _ok / _err
# ──────────────────────────────────────────────────────────────────────────────


class TestOk:
    def test_returns_valid_json(self):
        result = json.loads(_ok({"key": "value"}))
        assert result["ok"] is True
        assert result["result"]["key"] == "value"

    def test_string_result(self):
        result = json.loads(_ok("hello"))
        assert result["ok"] is True
        assert result["result"] == "hello"

    def test_numeric_result(self):
        result = json.loads(_ok(42))
        assert result["ok"] is True
        assert result["result"] == 42

    def test_unicode_characters(self):
        result = json.loads(_ok("বাংলা 🤖"))
        assert result["ok"] is True
        assert "বাংলা" in result["result"]


class TestErr:
    def test_returns_valid_json(self):
        result = json.loads(_err("something broke"))
        assert result["ok"] is False
        assert result["error"] == "something broke"

    def test_empty_message(self):
        result = json.loads(_err(""))
        assert result["ok"] is False
        assert result["error"] == ""


# ──────────────────────────────────────────────────────────────────────────────
# _validate_file
# ──────────────────────────────────────────────────────────────────────────────


class TestValidateFile:
    def test_valid_file(self, tmp_path: Path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        result = _validate_file(str(f))
        assert result == f.resolve()

    def test_nonexistent_file(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            _validate_file("/nonexistent/path/file.txt")

    def test_directory_instead_of_file(self, tmp_path: Path):
        with pytest.raises(ValueError, match="not a file"):
            _validate_file(str(tmp_path))

    def test_custom_label(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError, match="Photo"):
            _validate_file(str(tmp_path / "missing.jpg"), label="Photo")


# ──────────────────────────────────────────────────────────────────────────────
# _check_file_size
# ──────────────────────────────────────────────────────────────────────────────


class TestCheckFileSize:
    def test_small_file_no_warning(self, tmp_path: Path):
        f = tmp_path / "small.txt"
        f.write_text("x" * 100)
        assert _check_file_size(f) is None

    def test_large_file_warning(self, tmp_path: Path):
        f = tmp_path / "big.bin"
        # Create a file just over 50 MB
        f.write_bytes(b"\x00" * (50 * 1024 * 1024 + 1))
        warning = _check_file_size(f)
        assert warning is not None
        assert "50 MB" in warning

    def test_too_large_file_raises(self, tmp_path: Path):
        """Files over 2 GB should raise ValueError."""
        # We can't create a 2 GB file in tests, so we mock the stat
        f = tmp_path / "huge.bin"
        f.write_bytes(b"\x00" * 10)

        # Monkey-patch stat to return a huge size
        import unittest.mock as mock

        fake_stat = mock.MagicMock()
        fake_stat.st_size = 3 * 1024 * 1024 * 1024  # 3 GB

        with mock.patch.object(Path, "stat", return_value=fake_stat):
            with pytest.raises(ValueError, match="2 GB"):
                _check_file_size(f)


# ──────────────────────────────────────────────────────────────────────────────
# _RateLimiter
# ──────────────────────────────────────────────────────────────────────────────


class TestRateLimiter:
    @pytest.mark.asyncio
    async def test_acquire_does_not_block_under_limit(self):
        limiter = _RateLimiter()
        # Should not block for a few calls
        for _ in range(5):
            await limiter.acquire("12345")

    @pytest.mark.asyncio
    async def test_tracks_global_timestamps(self):
        limiter = _RateLimiter()
        await limiter.acquire()
        assert len(limiter._global_timestamps) == 1

    @pytest.mark.asyncio
    async def test_tracks_per_chat_timestamps(self):
        limiter = _RateLimiter()
        await limiter.acquire("chat_1")
        await limiter.acquire("chat_2")
        assert "chat_1" in limiter._chat_timestamps
        assert "chat_2" in limiter._chat_timestamps
        assert len(limiter._chat_timestamps["chat_1"]) == 1
        assert len(limiter._chat_timestamps["chat_2"]) == 1
