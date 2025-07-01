"""
Connection discovery functionality for automatically finding working database connections.
"""

import logging
import time
from typing import Dict, List, Optional, Sequence
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from .exceptions import DiscoveryError
from .registry import DriverRegistry

logger = logging.getLogger(__name__)

DEFAULT_DIALECTS = ["postgresql", "mysql", "sqlite", "oracle", "mssql"]


class ConnectionDiscovery:
    """Automatic database connection discovery."""

    @classmethod
    def discover_connection(
        cls,
        *,
        user: str,
        password: str,
        host: str = "localhost",
        port: Optional[int] = None,
        database: Optional[str] = None,
        dialects: Optional[Sequence[str]] = None,
        timeout: float = 5.0,
    ) -> str:
        """Discover a working database connection URL.

        Args:
            user: Database username
            password: Database password
            host: Database host
            port: Database port (if None, uses dialect defaults)
            database: Database name (optional)
            dialects: List of dialects to try (if None, uses defaults)
            timeout: Connection timeout per attempt

        Returns:
            Working connection URL

        Raises:
            DiscoveryError: If no working connection is found
        """
        if dialects is None:
            dialects = DEFAULT_DIALECTS

        logger.info(f"Starting connection discovery for {user}@{host}")
        logger.debug(f"Trying dialects: {list(dialects)}")

        failed_attempts: Dict[str, str] = {}

        for dialect in dialects:
            try:
                url = cls._try_dialect(
                    dialect=dialect,
                    user=user,
                    password=password,
                    host=host,
                    port=port,
                    database=database,
                    timeout=timeout,
                )

                if url:
                    logger.info(f"Successfully discovered connection: {dialect}")
                    return url

            except Exception as e:
                error_msg = str(e)
                failed_attempts[dialect] = error_msg
                logger.debug(f"Failed to connect with {dialect}: {error_msg}")

        # No working connection found
        logger.error(
            f"Failed to discover any working connection. Tried: {list(dialects)}"
        )
        raise DiscoveryError(
            f"No valid connection found for {user}@{host}",
            attempted_dialects=list(dialects),
            failed_attempts=failed_attempts,
        )

    @classmethod
    def _try_dialect(
        cls,
        *,
        dialect: str,
        user: str,
        password: str,
        host: str,
        port: Optional[int],
        database: Optional[str],
        timeout: float,
    ) -> Optional[str]:
        """Try to connect using a specific dialect.

        Returns:
            Connection URL if successful, None otherwise
        """
        # Get dialect info
        dialect_info = DriverRegistry.get_dialect_info(dialect)
        if not dialect_info:
            logger.debug(f"Unknown dialect: {dialect}")
            return None

        # Get available drivers for this dialect
        available_drivers = DriverRegistry.get_available_drivers(
            dialect, is_async=False
        )
        if not available_drivers:
            logger.debug(f"No available drivers for {dialect}")
            return None

        # Determine port
        effective_port = port or dialect_info.default_port

        # Try each available driver
        for driver in available_drivers:
            try:
                url = cls._build_url(
                    dialect=dialect,
                    driver=driver,
                    user=user,
                    password=password,
                    host=host,
                    port=effective_port,
                    database=database,
                )

                if cls._test_connection(url, timeout):
                    logger.debug(f"Connection successful: {dialect}+{driver}")
                    return url

            except Exception as e:
                logger.debug(f"Driver {driver} failed: {e}")
                continue

        return None

    @classmethod
    def _build_url(
        cls,
        *,
        dialect: str,
        driver: str,
        user: str,
        password: str,
        host: str,
        port: int,
        database: Optional[str],
    ) -> str:
        """Build a connection URL."""

        # URL encode credentials
        encoded_user = quote_plus(user)
        encoded_password = quote_plus(password)

        # Handle SQLite specially
        if dialect == "sqlite":
            if database:
                return f"sqlite:///{database}"
            else:
                return "sqlite:///:memory:"

        # Build URL for other databases
        url_parts = [dialect]

        # Add driver if it's not the default
        dialect_info = DriverRegistry.get_dialect_info(dialect)
        if driver != dialect_info.default_driver:
            url_parts.append(f"+{driver}")

        url_parts.extend(["://", f"{encoded_user}:{encoded_password}@{host}"])

        if port and port > 0:
            url_parts.append(f":{port}")

        if database:
            url_parts.append(f"/{database}")

        return "".join(url_parts)

    @classmethod
    def _test_connection(cls, url: str, timeout: float) -> bool:
        """Test if a connection URL works.

        Args:
            url: Database URL to test
            timeout: Connection timeout

        Returns:
            True if connection works, False otherwise
        """
        try:
            # Create engine with short timeout
            engine = create_engine(
                url,
                pool_timeout=timeout,
                pool_recycle=300,  # 5 minutes
                pool_pre_ping=True,
                echo=False,
            )

            # Test connection
            start_time = time.time()
            with engine.connect() as conn:
                # Simple test query
                conn.execute(text("SELECT 1"))

            elapsed = time.time() - start_time
            logger.debug(f"Connection test passed in {elapsed:.2f}s")

            # Clean up
            engine.dispose()

            return True

        except SQLAlchemyError as e:
            logger.debug(f"SQLAlchemy error testing {url}: {e}")
            return False
        except Exception as e:
            logger.debug(f"Unexpected error testing {url}: {e}")
            return False

    @classmethod
    def get_supported_dialects(cls) -> List[str]:
        """Get list of supported dialects for discovery."""
        return DriverRegistry.get_supported_dialects()

    @classmethod
    def check_dialect_availability(cls, dialect: str) -> Dict[str, bool]:
        """Check if drivers are available for a dialect.

        Returns:
            Dict mapping driver names to availability status
        """
        dialect_info = DriverRegistry.get_dialect_info(dialect)
        if not dialect_info:
            return {}

        availability = {}

        # Check sync drivers
        for driver in dialect_info.sync_drivers:
            availability[driver] = DriverRegistry.is_driver_available(driver)

        # Check async drivers
        for driver in dialect_info.async_drivers:
            availability[f"{driver} (async)"] = DriverRegistry.is_driver_available(
                driver
            )

        return availability

    @classmethod
    async def discover_connection_async(
        cls,
        *,
        user: str,
        password: str,
        host: str = "localhost",
        port: Optional[int] = None,
        database: Optional[str] = None,
        dialects: Optional[Sequence[str]] = None,
        timeout: float = 5.0,
    ) -> str:
        """Async version of connection discovery.

        Args:
            user: Database username
            password: Database password
            host: Database host
            port: Database port (if None, uses dialect defaults)
            database: Database name (optional)
            dialects: List of dialects to try (if None, uses defaults)
            timeout: Connection timeout per attempt

        Returns:
            Working connection URL

        Raises:
            DiscoveryError: If no working connection is found
        """

        if dialects is None:
            dialects = DEFAULT_DIALECTS

        logger.info(f"Starting async connection discovery for {user}@{host}")
        logger.debug(f"Trying dialects: {list(dialects)}")

        failed_attempts: Dict[str, str] = {}

        for dialect in dialects:
            try:
                url = await cls._try_dialect_async(
                    dialect=dialect,
                    user=user,
                    password=password,
                    host=host,
                    port=port,
                    database=database,
                    timeout=timeout,
                )

                if url:
                    logger.info(f"Successfully discovered async connection: {dialect}")
                    return url

            except Exception as e:
                error_msg = str(e)
                failed_attempts[dialect] = error_msg
                logger.debug(f"Failed to connect async with {dialect}: {error_msg}")

        # No working connection found
        logger.error(
            f"Failed to discover any working async connection. Tried: {list(dialects)}"
        )
        raise DiscoveryError(
            f"No valid async connection found for {user}@{host}",
            attempted_dialects=list(dialects),
            failed_attempts=failed_attempts,
        )

    @classmethod
    async def _try_dialect_async(
        cls,
        *,
        dialect: str,
        user: str,
        password: str,
        host: str,
        port: Optional[int],
        database: Optional[str],
        timeout: float,
    ) -> Optional[str]:
        """Try to connect using a specific dialect asynchronously."""

        # Get dialect info
        dialect_info = DriverRegistry.get_dialect_info(dialect)
        if not dialect_info:
            logger.debug(f"Unknown dialect: {dialect}")
            return None

        # Get available async drivers for this dialect
        available_drivers = DriverRegistry.get_available_drivers(dialect, is_async=True)
        if not available_drivers:
            logger.debug(f"No available async drivers for {dialect}")
            return None

        # Determine port
        effective_port = port or dialect_info.default_port

        # Try each available driver
        for driver in available_drivers:
            try:
                url = cls._build_async_url(
                    dialect=dialect,
                    driver=driver,
                    user=user,
                    password=password,
                    host=host,
                    port=effective_port,
                    database=database,
                )

                if await cls._test_connection_async(url, timeout):
                    logger.debug(f"Async connection successful: {dialect}+{driver}")
                    return url

            except Exception as e:
                logger.debug(f"Async driver {driver} failed: {e}")
                continue

        return None

    @classmethod
    def _build_async_url(
        cls,
        *,
        dialect: str,
        driver: str,
        user: str,
        password: str,
        host: str,
        port: int,
        database: Optional[str],
    ) -> str:
        """Build an async connection URL."""

        # URL encode credentials
        encoded_user = quote_plus(user)
        encoded_password = quote_plus(password)

        # Handle SQLite specially
        if dialect == "sqlite":
            if database:
                return f"sqlite+aiosqlite:///{database}"
            else:
                return "sqlite+aiosqlite:///:memory:"

        # Build URL for other databases
        url_parts = [dialect, f"+{driver}", "://"]
        url_parts.append(f"{encoded_user}:{encoded_password}@{host}")

        if port and port > 0:
            url_parts.append(f":{port}")

        if database:
            url_parts.append(f"/{database}")

        return "".join(url_parts)

    @classmethod
    async def _test_connection_async(cls, url: str, timeout: float) -> bool:
        """Test if an async connection URL works."""
        try:
            import asyncio

            from sqlalchemy.ext.asyncio import create_async_engine

            # Create async engine with short timeout
            engine = create_async_engine(
                url,
                pool_timeout=timeout,
                pool_recycle=300,  # 5 minutes
                pool_pre_ping=True,
                echo=False,
            )

            # Test connection with timeout
            start_time = time.time()

            async def test_query():
                async with engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))

            await asyncio.wait_for(test_query(), timeout=timeout)

            elapsed = time.time() - start_time
            logger.debug(f"Async connection test passed in {elapsed:.2f}s")

            # Clean up
            await engine.dispose()

            return True

        except Exception as e:
            logger.debug(f"Error testing async {url}: {e}")
            return False
