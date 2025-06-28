"""
UniConnDBBridge - Universal auth-ready SQLAlchemy Database Manager

A universal database connection manager that supports multiple RDBMS
and authentication methods with both sync and async APIs.
"""

from .config import DBConfig, ConnectionInfo
from .core import DatabaseManager
from .async_ import AsyncDatabaseManager
from .discovery import ConnectionDiscovery
from .exceptions import (
    UniConnDBError,
    ConnectionError,
    AuthenticationError,
    DiscoveryError,
)

__version__ = "25.6.0"
__all__ = [
    "DBConfig",
    "ConnectionInfo",
    "DatabaseManager",
    "AsyncDatabaseManager",
    "ConnectionDiscovery",
    "UniConnDBError",
    "ConnectionError",
    "AuthenticationError",
    "DiscoveryError",
]