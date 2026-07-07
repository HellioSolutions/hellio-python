"""Official Python SDK for the Hellio Messaging API.

Example:
    >>> from hellio import Hellio
    >>> client = Hellio("your-token-here")
    >>> client.sms("233241234567", "Hello!")
"""

from __future__ import annotations

from .client import Hellio
from .errors import (
    ConflictError,
    HellioError,
    InsufficientBalanceError,
    InvalidApiTokenError,
    RateLimitError,
    ServiceUnavailableError,
    ValidationError,
)
from .ussd import Ussd

__version__ = "1.1.0"

__all__ = [
    "Hellio",
    "Ussd",
    "HellioError",
    "InvalidApiTokenError",
    "InsufficientBalanceError",
    "ConflictError",
    "ValidationError",
    "RateLimitError",
    "ServiceUnavailableError",
    "__version__",
]
