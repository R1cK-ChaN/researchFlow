"""uvicorn entry point. Launched by `researchflow-server` console script."""

from __future__ import annotations


def main() -> None:  # pragma: no cover
    import uvicorn

    uvicorn.run(
        "researchflow.server.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        timeout_keep_alive=300,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
