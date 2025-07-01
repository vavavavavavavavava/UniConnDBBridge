"""
Driver registry system for managing database drivers and dialects.
"""

import importlib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .exceptions import DriverNotFoundError


@dataclass
class DialectInfo:
    """Information about a database dialect."""

    name: str
    default_driver: str
    default_port: int
    async_drivers: List[str]
    sync_drivers: List[str]
    required_packages: Dict[str, List[str]]  # driver -> list of required packages
    install_commands: Dict[str, str]  # driver -> pip install command


class DriverRegistry:
    """Registry for database drivers and dialects."""

    _dialects: Dict[str, DialectInfo] = {}
    _initialized = False

    @classmethod
    def initialize(cls) -> None:
        """Initialize the driver registry with default dialects."""
        if cls._initialized:
            return

        # PostgreSQL
        cls._dialects["postgresql"] = DialectInfo(
            name="postgresql",
            default_driver="psycopg2",
            default_port=5432,
            async_drivers=["asyncpg"],
            sync_drivers=["psycopg2", "pg8000"],
            required_packages={
                "psycopg2": ["psycopg2-binary"],
                "asyncpg": ["asyncpg"],
                "pg8000": ["pg8000"],
            },
            install_commands={
                "psycopg2": "pip install psycopg2-binary",
                "asyncpg": "pip install asyncpg",
                "pg8000": "pip install pg8000",
            },
        )

        # MySQL
        cls._dialects["mysql"] = DialectInfo(
            name="mysql",
            default_driver="mysqlclient",
            default_port=3306,
            async_drivers=["aiomysql", "asyncmy"],
            sync_drivers=["mysqlclient", "pymysql"],
            required_packages={
                "mysqlclient": ["mysqlclient"],
                "pymysql": ["pymysql"],
                "aiomysql": ["aiomysql"],
                "asyncmy": ["asyncmy"],
            },
            install_commands={
                "mysqlclient": "pip install mysqlclient",
                "pymysql": "pip install pymysql",
                "aiomysql": "pip install aiomysql",
                "asyncmy": "pip install asyncmy",
            },
        )

        # SQLite
        cls._dialects["sqlite"] = DialectInfo(
            name="sqlite",
            default_driver="pysqlite",
            default_port=0,  # N/A for SQLite
            async_drivers=["aiosqlite"],
            sync_drivers=["pysqlite"],
            required_packages={
                "pysqlite": [],  # Built into Python
                "aiosqlite": ["aiosqlite"],
            },
            install_commands={
                "pysqlite": "",  # Built-in
                "aiosqlite": "pip install aiosqlite",
            },
        )

        # Oracle
        cls._dialects["oracle"] = DialectInfo(
            name="oracle",
            default_driver="oracledb",
            default_port=1521,
            async_drivers=["oracledb"],
            sync_drivers=["oracledb", "cx_oracle"],
            required_packages={
                "oracledb": ["oracledb"],
                "cx_oracle": ["cx_oracle"],
            },
            install_commands={
                "oracledb": "pip install oracledb",
                "cx_oracle": "pip install cx_oracle",
            },
        )

        # SQL Server
        cls._dialects["mssql"] = DialectInfo(
            name="mssql",
            default_driver="pyodbc",
            default_port=1433,
            async_drivers=["aioodbc"],
            sync_drivers=["pyodbc", "pymssql"],
            required_packages={
                "pyodbc": ["pyodbc"],
                "pymssql": ["pymssql"],
                "aioodbc": ["aioodbc"],
            },
            install_commands={
                "pyodbc": "pip install pyodbc",
                "pymssql": "pip install pymssql",
                "aioodbc": "pip install aioodbc",
            },
        )

        cls._initialized = True

    @classmethod
    def get_dialect_info(cls, dialect: str) -> Optional[DialectInfo]:
        """Get information about a dialect."""
        cls.initialize()
        return cls._dialects.get(dialect)

    @classmethod
    def get_supported_dialects(cls) -> List[str]:
        """Get list of supported dialects."""
        cls.initialize()
        return list(cls._dialects.keys())

    @classmethod
    def is_driver_available(cls, driver: str) -> bool:
        """Check if a driver is available (installed)."""
        cls.initialize()

        # Find which dialect this driver belongs to
        for dialect_info in cls._dialects.values():
            if (
                driver in dialect_info.sync_drivers
                or driver in dialect_info.async_drivers
            ):
                required_packages = dialect_info.required_packages.get(driver, [])

                # Check if all required packages are available
                for package in required_packages:
                    try:
                        importlib.import_module(package.replace("-", "_"))
                    except ImportError:
                        return False

                return True

        return False

    @classmethod
    def get_available_drivers(cls, dialect: str, is_async: bool = False) -> List[str]:
        """Get list of available drivers for a dialect."""
        cls.initialize()

        dialect_info = cls._dialects.get(dialect)
        if not dialect_info:
            return []

        drivers = dialect_info.async_drivers if is_async else dialect_info.sync_drivers
        available_drivers = []

        for driver in drivers:
            if cls.is_driver_available(driver):
                available_drivers.append(driver)

        return available_drivers

    @classmethod
    def get_best_driver(cls, dialect: str, is_async: bool = False) -> str:
        """Get the best available driver for a dialect."""
        cls.initialize()

        available_drivers = cls.get_available_drivers(dialect, is_async)
        if not available_drivers:
            dialect_info = cls._dialects.get(dialect)
            if dialect_info:
                # Return default driver even if not available (will raise error later)
                target_drivers = (
                    dialect_info.async_drivers
                    if is_async
                    else dialect_info.sync_drivers
                )
                if target_drivers:
                    return target_drivers[0]

            raise DriverNotFoundError(
                f"No {'async' if is_async else 'sync'} driver available for {dialect}",
                dialect=dialect,
            )

        # Return the first available driver (they're ordered by preference)
        return available_drivers[0]

    @classmethod
    def validate_driver(cls, dialect: str, driver: str, is_async: bool = False) -> bool:
        """Validate that a driver is supported for a dialect."""
        cls.initialize()

        dialect_info = cls._dialects.get(dialect)
        if not dialect_info:
            return False

        target_drivers = (
            dialect_info.async_drivers if is_async else dialect_info.sync_drivers
        )
        return driver in target_drivers

    @classmethod
    def get_install_command(cls, dialect: str, driver: str) -> Optional[str]:
        """Get installation command for a driver."""
        cls.initialize()

        dialect_info = cls._dialects.get(dialect)
        if not dialect_info:
            return None

        return dialect_info.install_commands.get(driver)

    @classmethod
    def register_dialect(cls, dialect_info: DialectInfo) -> None:
        """Register a custom dialect."""
        cls.initialize()
        cls._dialects[dialect_info.name] = dialect_info

    @classmethod
    def check_driver_requirements(
        cls, dialect: str, driver: str
    ) -> Tuple[bool, List[str]]:
        """Check if driver requirements are met.

        Returns:
            Tuple of (requirements_met, missing_packages)
        """
        cls.initialize()

        dialect_info = cls._dialects.get(dialect)
        if not dialect_info:
            return False, [f"Unknown dialect: {dialect}"]

        required_packages = dialect_info.required_packages.get(driver, [])
        missing_packages = []

        for package in required_packages:
            try:
                importlib.import_module(package.replace("-", "_"))
            except ImportError:
                missing_packages.append(package)

        return len(missing_packages) == 0, missing_packages

    @classmethod
    def get_driver_info(cls, dialect: str, driver: str) -> Dict[str, Any]:
        """Get detailed information about a specific driver."""
        cls.initialize()

        dialect_info = cls._dialects.get(dialect)
        if not dialect_info:
            return {}

        is_async = driver in dialect_info.async_drivers
        is_sync = driver in dialect_info.sync_drivers
        is_available = cls.is_driver_available(driver)
        requirements_met, missing_packages = cls.check_driver_requirements(
            dialect, driver
        )

        return {
            "dialect": dialect,
            "driver": driver,
            "is_async": is_async,
            "is_sync": is_sync,
            "is_available": is_available,
            "requirements_met": requirements_met,
            "missing_packages": missing_packages,
            "required_packages": dialect_info.required_packages.get(driver, []),
            "install_command": dialect_info.install_commands.get(driver, ""),
            "default_port": dialect_info.default_port,
        }
