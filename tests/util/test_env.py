"""Unit tests for the environment-variable helpers."""

from __future__ import annotations

import builtins

import labapi.util.env
from labapi.util.env import getenv


def test_getenv_latches_when_dotenv_import_fails(monkeypatch):
    """Getenv attempts the dotenv import at most once, even when it fails."""
    labapi.util.env._loaded = False

    attempts = 0
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        nonlocal attempts
        if name == "dotenv":
            attempts += 1
            raise ImportError("No module named 'dotenv'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    getenv("SOME_MISSING_KEY")
    getenv("ANOTHER_MISSING_KEY")

    assert attempts == 1
    assert labapi.util.env._loaded is True
