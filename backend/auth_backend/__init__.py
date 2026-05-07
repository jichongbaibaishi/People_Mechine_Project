"""Authentication, anonymous access, and privacy backend package."""

from .api import CURRENT_PRIVACY_VERSION, make_handler
from .store import Database

__all__ = ["CURRENT_PRIVACY_VERSION", "Database", "make_handler"]
