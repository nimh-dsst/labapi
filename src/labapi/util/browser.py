"""Browser detection helpers for interactive authentication."""

from __future__ import annotations

import warnings
from typing import Literal, TypeAlias, TypeGuard

from .env import getenv

_DetectableBrowser: TypeAlias = Literal["chrome", "firefox", "edge"]
_ChoosableBrowser: TypeAlias = Literal[
    "chrome", "firefox", "edge", "msedge", "terminal"
]


_DETECTABLE_BROWSERS: tuple[_DetectableBrowser, ...] = ("chrome", "firefox", "edge")
_CHOOSEABLE_BROWSERS: tuple[_ChoosableBrowser, ...] = (
    "chrome",
    "firefox",
    "edge",
    "msedge",
    "terminal",
)


def _is_choosable(string: str) -> TypeGuard[_ChoosableBrowser]:
    return string in _CHOOSEABLE_BROWSERS


def _parse_detectable(string: str | None) -> _DetectableBrowser | Literal[False]:
    if string is None:
        return False

    lowered = string.lower().strip()
    for d in _DETECTABLE_BROWSERS:
        if d in lowered:
            return d
    return False


def _get_env_browser() -> _ChoosableBrowser | None:
    browser = getenv("LA_AUTH_BROWSER", "").strip().lower()

    if browser == "":
        return None
    if _is_choosable(browser):
        return browser

    warnings.warn(
        f"Unrecognized LA_AUTH_BROWSER value {browser!r}; "
        "supported values are chrome, firefox, edge, or terminal. "
        "Falling back to automatic browser detection.",
        stacklevel=2,
    )

    return None


def _find_chosen_browser(browser: _ChoosableBrowser | None) -> _ChoosableBrowser | None:
    if browser == "terminal":
        return browser
    if browser is None:
        return None

    try:
        import installed_browsers  # pyright: ignore[reportMissingImports, reportMissingTypeStubs]
    except ImportError:
        warnings.warn(
            "Non-terminal browsers require the optional 'builtin-auth' "
            "dependencies. Install them with: pip install 'labapi[builtin-auth]' "
            "or set LA_AUTH_BROWSER=terminal for manual authentication.",
            stacklevel=2,
        )
        return "terminal"

    try:
        if installed_browsers.do_i_have_installed(browser):
            return browser
    except OSError as exc:
        warnings.warn(
            f"Configured browser probe failed: {exc}. "
            "Falling back to automatic browser detection.",
            RuntimeWarning,
            stacklevel=2,
        )
        return None

    # Fall back to a linear search: installed-browsers may register a browser
    # under a key that differs from our canonical name (e.g. Edge as "msedge"),
    # so match on the same substring basis autodetection uses.
    try:
        installed = installed_browsers.browsers()
    # TODO(BLE001): intentional broad catch — installed-browsers probe may raise; fall back to an empty list; narrow if a specific type becomes known.
    except Exception:  # noqa: BLE001
        installed = []
    for entry in installed:
        if _parse_detectable(entry.get("name")) == browser:
            return browser

    warnings.warn(
        f"Configured LA_AUTH_BROWSER value {browser!r} is not installed. "
        "Falling back to automatic browser detection.",
        stacklevel=2,
    )
    return None


def _autodetect_browser() -> _DetectableBrowser | None:
    try:
        import installed_browsers  # pyright: ignore[reportMissingImports, reportMissingTypeStubs]
    except ImportError:
        warnings.warn(
            "Automatic browser detection requires the optional 'builtin-auth' "
            "dependencies. Install them with: pip install 'labapi[builtin-auth]' "
            "or set LA_AUTH_BROWSER=terminal for manual authentication.",
            stacklevel=2,
        )
        return None

    try:
        raw_default_browser = installed_browsers.what_is_the_default_browser()
        default_browser = _parse_detectable(raw_default_browser)

        if default_browser:
            return default_browser

        for browser in installed_browsers.browsers():
            name = _parse_detectable(browser.get("name"))
            if name:
                return name

        warnings.warn(
            "Automatic browser detection failed: No compatible browser. Falling back to terminal/manual auth.",
            RuntimeWarning,
            stacklevel=2,
        )
        return None
    # TODO(BLE001): intentional broad catch — auto browser detection may raise anything; fall back to terminal/manual auth; narrow if a specific type becomes known.
    except Exception as exc:  # noqa: BLE001
        warnings.warn(
            f"Automatic browser detection failed: {exc}. Falling back to terminal/manual auth.",
            RuntimeWarning,
            stacklevel=2,
        )
        return None


def detect_default_browser() -> _ChoosableBrowser:
    """Resolve the preferred browser for the current auth attempt."""
    env_browser = _get_env_browser()
    chosen_browser = _find_chosen_browser(env_browser)

    if chosen_browser is None:
        return _autodetect_browser() or "terminal"

    return chosen_browser
