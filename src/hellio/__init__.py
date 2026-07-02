"""Official Python SDK for the Hellio Messaging API.

Example:
    >>> from hellio import Hellio
    >>> client = Hellio("your-token-here")
    >>> client.sms("233241234567", "Hello!")
"""

from __future__ import annotations

from .client import Hellio
from .errors import (
    HellioError,
    InsufficientBalanceError,
    InvalidApiTokenError,
    RateLimitError,
    ValidationError,
)

__version__ = "0.1.0"

__all__ = [
    "Hellio",
    "HellioError",
    "InvalidApiTokenError",
    "InsufficientBalanceError",
    "ValidationError",
    "RateLimitError",
    "__version__",
]
