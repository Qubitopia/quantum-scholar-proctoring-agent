"""Project-wide configuration constants.

Environment variables:
- QS_API_BASE_URL: Override the API base URL (default: http://localhost:8000)
"""

from __future__ import annotations

import os


API_BASE_URL: str = os.getenv("QS_API_BASE_URL", "http://localhost:8000")


class Endpoints:
    LOGIN = f"{API_BASE_URL}/auth/test-portal/login"
    INIT_TEST = f"{API_BASE_URL}/test-portal/init"
    START_TEST = f"{API_BASE_URL}/test-portal/start"


__all__ = ["API_BASE_URL", "Endpoints"]
