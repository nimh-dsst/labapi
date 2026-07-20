"""Unit tests for browser detection module."""

from __future__ import annotations

import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest


def import_browser_module():
    """Reload the browser module under test."""
    sys.modules.pop("labapi.util.browser", None)
    return importlib.import_module("labapi.util.browser")


@pytest.fixture
def browser_module():
    """Provide a freshly imported browser module."""
    return import_browser_module()


@pytest.fixture
def mock_installed_browsers():
    """Fixture to mock the optional installed_browsers dependency."""
    mock_module = MagicMock()
    with patch.dict("sys.modules", {"installed_browsers": mock_module}):
        yield mock_module


def test_browser_module_import_does_not_probe():
    """Test importing the module does not probe browser state."""
    installed_browsers = MagicMock()
    installed_browsers.browsers.side_effect = AssertionError("should not probe")
    installed_browsers.what_is_the_default_browser.side_effect = AssertionError(
        "should not probe"
    )
    installed_browsers.do_i_have_installed.side_effect = AssertionError(
        "should not probe"
    )

    with patch.dict("sys.modules", {"installed_browsers": installed_browsers}):
        browser = import_browser_module()

    assert callable(browser.detect_default_browser)
    installed_browsers.browsers.assert_not_called()
    installed_browsers.what_is_the_default_browser.assert_not_called()
    installed_browsers.do_i_have_installed.assert_not_called()


def test_browser_detection_env_var_is_resolved_at_call_time(
    browser_module, mock_installed_browsers, monkeypatch
):
    """Test LA_AUTH_BROWSER is read for each detection attempt."""
    mock_installed_browsers.do_i_have_installed.side_effect = lambda browser_name: (
        browser_name in {"firefox", "edge"}
    )

    monkeypatch.setenv("LA_AUTH_BROWSER", "firefox")
    assert browser_module.detect_default_browser() == "firefox"

    monkeypatch.setenv("LA_AUTH_BROWSER", "edge")
    assert browser_module.detect_default_browser() == "edge"


def test_env_browser_edge_found_via_linear_search(
    browser_module, mock_installed_browsers, monkeypatch
):
    """LA_AUTH_BROWSER=edge resolves via linear search when only 'msedge' is registered."""
    mock_installed_browsers.do_i_have_installed.return_value = False
    mock_installed_browsers.browsers.return_value = [{"name": "Microsoft Edge"}]

    monkeypatch.setenv("LA_AUTH_BROWSER", "edge")
    assert browser_module.detect_default_browser() == "edge"


def test_env_browser_msedge_spelling_accepted(
    browser_module, mock_installed_browsers, monkeypatch
):
    """LA_AUTH_BROWSER=msedge is accepted and matches the installed-browsers key."""
    mock_installed_browsers.do_i_have_installed.side_effect = lambda name: (
        name == "msedge"
    )

    monkeypatch.setenv("LA_AUTH_BROWSER", "msedge")
    assert browser_module.detect_default_browser() == "msedge"


def test_browser_detection_loads_dotenv_before_reading_env(browser_module, monkeypatch):
    """Test browser detection can populate LA_AUTH_BROWSER via python-dotenv."""
    mock_dotenv = MagicMock()

    def populate_env():
        monkeypatch.setenv("LA_AUTH_BROWSER", "terminal")

    mock_dotenv.load_dotenv.side_effect = populate_env
    monkeypatch.delenv("LA_AUTH_BROWSER", raising=False)

    with patch.dict("sys.modules", {"dotenv": mock_dotenv}):
        assert browser_module.detect_default_browser() == "terminal"

    mock_dotenv.load_dotenv.assert_called_once_with()


def test_browser_detection_default_system(
    browser_module, mock_installed_browsers, monkeypatch
):
    """Test browser selection based on system default."""
    monkeypatch.delenv("LA_AUTH_BROWSER", raising=False)
    mock_installed_browsers.what_is_the_default_browser.return_value = "Google Chrome"

    assert browser_module.detect_default_browser() == "chrome"


def test_browser_detection_fallback_list(
    browser_module, mock_installed_browsers, monkeypatch
):
    """Test fallback to first detected compatible browser."""
    monkeypatch.delenv("LA_AUTH_BROWSER", raising=False)
    mock_installed_browsers.what_is_the_default_browser.return_value = None
    mock_installed_browsers.browsers.return_value = [
        {"name": "Firefox Nightly", "path": "/path/to/firefox"}
    ]

    assert browser_module.detect_default_browser() == "firefox"


def test_browser_detection_terminal_fallback(
    browser_module, mock_installed_browsers, monkeypatch
):
    """Test terminal fallback when no compatible browser is found."""
    monkeypatch.delenv("LA_AUTH_BROWSER", raising=False)
    mock_installed_browsers.what_is_the_default_browser.return_value = None
    mock_installed_browsers.browsers.return_value = []

    with pytest.warns(
        RuntimeWarning,
        match="Automatic browser detection failed: No compatible browser",
    ):
        assert browser_module.detect_default_browser() == "terminal"


def test_browser_detection_import_error(browser_module, monkeypatch):
    """Test terminal fallback when installed_browsers cannot be imported."""
    monkeypatch.delenv("LA_AUTH_BROWSER", raising=False)

    with (
        patch.dict("sys.modules", {"installed_browsers": None}),
        pytest.warns(
            UserWarning,
            match="Automatic browser detection requires the optional 'builtin-auth' dependencies",
        ),
    ):
        assert browser_module.detect_default_browser() == "terminal"


def test_browser_detection_warns_for_invalid_env_value_and_falls_back(
    browser_module, mock_installed_browsers, monkeypatch
):
    """Test invalid LA_AUTH_BROWSER values warn before autodetect fallback."""
    monkeypatch.setenv("LA_AUTH_BROWSER", "safari")
    mock_installed_browsers.what_is_the_default_browser.return_value = "Microsoft Edge"

    with pytest.warns(UserWarning, match="Unrecognized LA_AUTH_BROWSER value 'safari'"):
        assert browser_module.detect_default_browser() == "edge"


def test_browser_detection_warns_when_nonterminal_env_requires_optional_deps(
    browser_module, monkeypatch
):
    """Test non-terminal LA_AUTH_BROWSER values fall back to terminal when builtin-auth is absent."""
    monkeypatch.setenv("LA_AUTH_BROWSER", "chrome")

    with (
        patch.dict("sys.modules", {"installed_browsers": None}),
        pytest.warns(
            UserWarning,
            match="Non-terminal browsers require the optional 'builtin-auth' dependencies",
        ),
    ):
        assert browser_module.detect_default_browser() == "terminal"


def test_browser_detection_warns_and_autodetects_when_preferred_browser_missing(
    browser_module, mock_installed_browsers, monkeypatch
):
    """Test missing preferred browsers warn and fall back to autodetect."""
    monkeypatch.setenv("LA_AUTH_BROWSER", "chrome")
    mock_installed_browsers.do_i_have_installed.return_value = False
    mock_installed_browsers.what_is_the_default_browser.return_value = "Mozilla Firefox"

    with pytest.warns(
        UserWarning,
        match="Configured LA_AUTH_BROWSER value 'chrome' is not installed",
    ):
        assert browser_module.detect_default_browser() == "firefox"


def test_browser_detection_runtime_failure_warns(
    browser_module, mock_installed_browsers, monkeypatch
):
    """Test runtime probe failures fall back to terminal auth without crashing."""
    monkeypatch.delenv("LA_AUTH_BROWSER", raising=False)
    mock_installed_browsers.browsers.side_effect = OSError("registry unavailable")

    with pytest.warns(RuntimeWarning, match="Automatic browser detection failed"):
        assert browser_module.detect_default_browser() == "terminal"


def test_browser_detection_explicit_terminal_override(browser_module, monkeypatch):
    """Test terminal override from LA_AUTH_BROWSER."""
    monkeypatch.setenv("LA_AUTH_BROWSER", "terminal")
    assert browser_module.detect_default_browser() == "terminal"
