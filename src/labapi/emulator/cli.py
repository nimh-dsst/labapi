"""CLI for running the LabArchives emulator."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from .backend import EmulatorBackend


def build_parser() -> argparse.ArgumentParser:
    """Build the emulator CLI parser."""
    parser = argparse.ArgumentParser(
        prog="python -m labapi.emulator",
        description="Run a local LabArchives emulator server.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host interface to bind the emulator to.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="TCP port to bind the emulator to.",
    )
    parser.add_argument(
        "--db",
        default=":memory:",
        help='SQLite database path. Use ":memory:" for an in-memory emulator.',
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable uvicorn auto-reload during development.",
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=("critical", "error", "warning", "info", "debug", "trace"),
        help="Set the uvicorn log level.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the emulator CLI."""
    args = build_parser().parse_args(argv)
    EmulatorBackend(args.db).serve(
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
    )
    return 0
