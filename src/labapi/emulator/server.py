"""FastAPI application and runner for the LabArchives emulator."""

from __future__ import annotations

from typing import Any

from .backend import EmulatorBackend


def create_app(backend: EmulatorBackend | None = None) -> Any:
    """Create a FastAPI app for serving the emulator backend."""
    try:
        from fastapi import FastAPI
    except ImportError as exc:  # pragma: no cover - dependency boundary
        raise RuntimeError(
            "FastAPI is required for the emulator server. Install labapi[emulator]."
        ) from exc

    app = FastAPI(
        title="LabArchives Emulator",
        summary="Local LabArchives-compatible development server.",
    )
    app.state.backend = backend if backend is not None else EmulatorBackend()

    @app.get("/")
    def root() -> dict[str, str]:
        """Return a minimal emulator status payload."""
        return {
            "service": "labapi-emulator",
            "status": "ok",
        }

    @app.get("/health")
    def health() -> dict[str, str]:
        """Return a health check payload."""
        return {"status": "ok"}

    return app


def serve(
    backend: EmulatorBackend | None = None,
    *,
    host: str = "127.0.0.1",
    port: int = 8080,
    reload: bool = False,
    log_level: str = "info",
) -> None:
    """Run the emulator FastAPI app with uvicorn."""
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover - dependency boundary
        raise RuntimeError(
            "uvicorn is required to run the emulator server. Install labapi[emulator]."
        ) from exc

    uvicorn.run(
        create_app(backend),
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )
