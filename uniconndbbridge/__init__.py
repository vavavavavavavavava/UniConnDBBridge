"""
UniConnDBBridge - Universal auth-ready SQLAlchemy Database Manager

A universal database connection manager that supports multiple RDBMS
and authentication methods with both sync and async APIs.
"""

from .async_ import AsyncDatabaseManager
from .config import ConnectionInfo, DBConfig
from .core import DatabaseManager
from .exceptions import (
    AuthenticationError,
    ConnectionError,
    UniConnDBError,
)

__version__ = "0.1.0"
__all__ = [
    "DBConfig",
    "ConnectionInfo",
    "DatabaseManager",
    "AsyncDatabaseManager",
    "UniConnDBError",
    "ConnectionError",
    "AuthenticationError",
]
