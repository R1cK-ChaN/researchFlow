"""HTTP service wrapper around the researchFlow library."""

from researchflow.server.main import app, create_app

__all__ = ["app", "create_app"]
