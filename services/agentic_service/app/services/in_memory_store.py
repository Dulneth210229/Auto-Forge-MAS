"""
Temporary in-memory database.

Important:
This is only for the first MVP foundation.

Why we use this now:
- It lets us test backend APIs quickly.
- We can focus on agent workflow first.
- Later, this will be replaced with PostgreSQL or MongoDB.

Do not use this for production.
"""

from typing import Any


class InMemoryStore:
    """
    Very simple in-memory storage.

    Data will be lost when the backend restarts.
    """

    def __init__(self):
        self.projects: dict[str, dict[str, Any]] = {}
        self.features: dict[str, dict[str, Any]] = {}
        self.artifacts: dict[str, dict[str, Any]] = {}
        self.approvals: dict[str, dict[str, Any]] = {}

    def reset(self) -> None:
        """
        Clear all in-memory data.
        Useful for local testing.
        """
        self.projects.clear()
        self.features.clear()
        self.artifacts.clear()
        self.approvals.clear()


store = InMemoryStore()