"""
Async DatabaseManager implementation for asynchronous database operations.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional, Sequence, Union
from urllib.parse import urlparse

try:
    from sqlalchemy import MetaData, text
    from sqlalchemy.ext.asyncio import (
        AsyncEngine,
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )
    from sqlalchemy.sql import Executable

    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False

from .config import AuthPlugin, ConnectionInfo, DBConfig, create_auth_plugin
from .exceptions import (
    ConfigurationError,
    DriverNotFoundError,
    wrap_sqlalchemy_error,
)
from .registry import DriverRegistry

logger = logging.getLogger(__name__)


class AsyncDatabaseManager:
    """Asynchronous database connection manager."""

    def __init__(
        self,
        url: Optional[str] = None,
        *,
        config: Optional[Union[DBConfig, Dict[str, Any]]] = None,
        **kwargs: Any,
    ):
        """Initialize AsyncDatabaseManager.

        Args:
            url: SQLAlchemy database URL
            config: Database configuration (DBConfig or dict)
            **kwargs: Additional engine options
        """
        if not ASYNC_AVAILABLE:
            raise ConfigurationError(
                "Async functionality not available. Install SQLAlchemy with async support: "
                "pip install sqlalchemy[asyncio]"
            )

        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None
        self._url: Optional[str] = None
        self._config: Optional[DBConfig] = None
        self._auth_plugin: Optional[AuthPlugin] = None

        if url and config:
            raise ConfigurationError("Cannot specify both url and config")

        if not url and not config:
            raise ConfigurationError("Must specify either url or config")

        if url:
            self._url = self._ensure_async_url(url)
        else:
            # Convert dict to DBConfig if needed
            if isinstance(config, dict):
                config = DBConfig(**config)
            self._config = config

            # Create auth plugin if specified
            if config.auth_plugin:
                self._auth_plugin = create_auth_plugin(
                    config.auth_plugin, **config.auth_options
                )
                # Apply authentication
                self._config = self._auth_plugin.authenticate(config)

            # Generate URL from config and ensure it's async
            base_url = config.to_url()
            self._url = self._ensure_async_url(base_url)

        # Store additional engine options
        self._engine_kwargs = kwargs

        logger.info(
            f"Initialized AsyncDatabaseManager with URL: {self._mask_url(self._url)}"
        )

    def _ensure_async_url(self, url: str) -> str:
        """Ensure URL is properly formatted for async use."""
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()

        # Map sync schemes to async schemes
        async_mapping = {
            "postgresql": "postgresql+asyncpg",
            "mysql": "mysql+aiomysql",
            "sqlite": "sqlite+aiosqlite",
            "oracle": "oracle+oracledb",  # oracledb supports async
            "mssql": "mssql+aioodbc",
        }

        # If already has a driver specified, check if it's async
        if "+" in scheme:
            dialect, driver = scheme.split("+", 1)
            dialect_info = DriverRegistry.get_dialect_info(dialect)

            if dialect_info and driver in dialect_info.async_drivers:
                # Already async
                return url
            elif dialect_info:
                # Use best async driver for this dialect
                try:
                    best_async_driver = DriverRegistry.get_best_driver(
                        dialect, is_async=True
                    )
                    new_scheme = f"{dialect}+{best_async_driver}"
                    return url.replace(scheme, new_scheme, 1)
                except DriverNotFoundError:
                    raise ConfigurationError(f"No async driver available for {dialect}")
        else:
            # No driver specified, use default async mapping
            if scheme in async_mapping:
                return url.replace(scheme, async_mapping[scheme], 1)

        # If we can't convert, try to use as-is and let SQLAlchemy handle it
        return url

    def _mask_url(self, url: str) -> str:
        """Mask password in URL for logging."""
        try:
            parsed = urlparse(url)
            if parsed.password:
                masked_netloc = parsed.netloc.replace(f":{parsed.password}@", ":***@")
                return url.replace(parsed.netloc, masked_netloc)
        except Exception:
            pass
        return url

    @property
    def engine(self) -> AsyncEngine:
        """Get or create the async SQLAlchemy engine."""
        if self._engine is None:
            raise RuntimeError(
                "Engine not created. Call create_engine() first or use async context manager."
            )
        return self._engine

    async def create_engine(self) -> None:
        """Create the async SQLAlchemy engine."""
        try:
            # Prepare engine options
            engine_options = {}

            # Add config-based options
            if self._config:
                engine_options.update(self._config.get_engine_options())

            # Add auth plugin options
            if self._auth_plugin:
                auth_options = await self._auth_plugin.configure_engine_args_async()
                engine_options.update(auth_options)

            # Add additional options
            engine_options.update(self._engine_kwargs)

            # Get final URL from auth plugin if available
            final_url = self._url
            if self._auth_plugin:
                final_url = self._auth_plugin.get_connection_url(self._url)

            logger.debug(f"Creating async engine with options: {engine_options}")
            self._engine = create_async_engine(final_url, **engine_options)

            # Create session factory
            self._session_factory = async_sessionmaker(bind=self._engine)

            logger.info("Async database engine created successfully")

        except Exception as e:
            logger.error(f"Failed to create async database engine: {e}")
            raise wrap_sqlalchemy_error(e, "async engine creation")

    async def connect_info_async(self) -> ConnectionInfo:
        """Get connection information from the current engine."""
        if self._engine is None:
            await self.create_engine()

        try:
            url = self._engine.url

            return ConnectionInfo(
                dialect=url.drivername.split("+")[0]
                if "+" in url.drivername
                else url.drivername,
                driver=url.drivername.split("+")[1]
                if "+" in url.drivername
                else "default",
                host=url.host or "localhost",
                port=url.port or 0,
                database=url.database or "",
                user=url.username or "",
                is_async=True,
                pool_size=getattr(self._engine.pool, "size", lambda: 0)(),
                max_overflow=getattr(self._engine.pool, "max_overflow", 0),
                pool_timeout=getattr(self._engine.pool, "timeout", 30),
                engine_options={},
            )
        except Exception as e:
            logger.error(f"Failed to get async connection info: {e}")
            raise wrap_sqlalchemy_error(e, "async connection info retrieval")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session with automatic transaction management."""
        if self._session_factory is None:
            await self.create_engine()

        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Async session error, rolling back: {e}")
            raise wrap_sqlalchemy_error(e, "async session operation")
        finally:
            await session.close()

    @asynccontextmanager
    async def connection(self):
        """Get a raw async database connection."""
        if self._engine is None:
            await self.create_engine()

        conn = await self._engine.connect()
        try:
            yield conn
        except Exception as e:
            logger.error(f"Async connection error: {e}")
            raise wrap_sqlalchemy_error(e, "async connection operation")
        finally:
            await conn.close()

    async def execute(
        self,
        statement: Union[str, Executable],
        parameters: Optional[Dict[str, Any]] = None,
    ):
        """Execute a SQL statement asynchronously."""
        try:
            async with self.connection() as conn:
                if isinstance(statement, str):
                    statement = text(statement)

                if parameters:
                    result = await conn.execute(statement, parameters)
                else:
                    result = await conn.execute(statement)

                await conn.commit()
                return result

        except Exception as e:
            logger.error(f"Failed to execute async statement: {e}")
            raise wrap_sqlalchemy_error(e, "async statement execution")

    async def fetch_one(
        self,
        statement: Union[str, Executable],
        parameters: Optional[Dict[str, Any]] = None,
    ):
        """Execute a statement and fetch one result asynchronously."""
        result = await self.execute(statement, parameters)
        return result.fetchone()

    async def fetch_many(
        self,
        statement: Union[str, Executable],
        size: Optional[int] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        """Execute a statement and fetch multiple results asynchronously."""
        result = await self.execute(statement, parameters)
        if size is not None:
            return result.fetchmany(size)
        return result.fetchall()

    async def get_table_names(self, schema: Optional[str] = None) -> List[str]:
        """Get list of table names in the database asynchronously."""
        try:
            async with self.connection() as conn:
                # Use database-specific queries for better async support
                if self._engine.dialect.name == "postgresql":
                    query = text("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = COALESCE(:schema, 'public')
                        AND table_type = 'BASE TABLE'
                    """)
                    result = await conn.execute(query, {"schema": schema})
                elif self._engine.dialect.name == "mysql":
                    query = text("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = COALESCE(:schema, DATABASE())
                        AND table_type = 'BASE TABLE'
                    """)
                    result = await conn.execute(query, {"schema": schema})
                elif self._engine.dialect.name == "sqlite":
                    query = text("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    """)
                    result = await conn.execute(query)
                else:
                    # Fallback to reflection (may not work well with async)
                    metadata = MetaData()
                    await conn.run_sync(metadata.reflect, schema=schema)
                    return list(metadata.tables.keys())

                return [row[0] for row in result.fetchall()]

        except Exception as e:
            logger.error(f"Failed to get table names async: {e}")
            raise wrap_sqlalchemy_error(e, "async table name retrieval")

    async def get_column_names(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[str]:
        """Get column names for a table asynchronously."""
        try:
            async with self.connection() as conn:
                # Use database-specific queries for better async support
                if self._engine.dialect.name == "postgresql":
                    query = text("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = :table_name 
                        AND table_schema = COALESCE(:schema, 'public')
                        ORDER BY ordinal_position
                    """)
                    result = await conn.execute(
                        query, {"table_name": table_name, "schema": schema}
                    )
                elif self._engine.dialect.name == "mysql":
                    query = text("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = :table_name 
                        AND table_schema = COALESCE(:schema, DATABASE())
                        ORDER BY ordinal_position
                    """)
                    result = await conn.execute(
                        query, {"table_name": table_name, "schema": schema}
                    )
                elif self._engine.dialect.name == "sqlite":
                    query = text(f"PRAGMA table_info({table_name})")
                    result = await conn.execute(query)
                    return [
                        row[1] for row in result.fetchall()
                    ]  # Column name is index 1
                else:
                    # Fallback to reflection
                    metadata = MetaData()
                    await conn.run_sync(
                        metadata.reflect, schema=schema, only=[table_name]
                    )
                    full_table_name = f"{schema}.{table_name}" if schema else table_name
                    if full_table_name in metadata.tables:
                        table = metadata.tables[full_table_name]
                        return [col.name for col in table.columns]
                    else:
                        return []

                return [row[0] for row in result.fetchall()]

        except Exception as e:
            logger.error(f"Failed to get column names for {table_name} async: {e}")
            raise wrap_sqlalchemy_error(e, "async column name retrieval")

    async def test_connection(self) -> bool:
        """Test the database connection asynchronously."""
        try:
            async with self.connection() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Async connection test successful")
            return True
        except Exception as e:
            logger.warning(f"Async connection test failed: {e}")
            return False

    async def close(self) -> None:
        """Close the database engine and all connections."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Async database engine closed")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.create_engine()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    @classmethod
    async def from_discovery(cls, **kwargs) -> "AsyncDatabaseManager":
        """Create AsyncDatabaseManager using async connection discovery.

        Args:
            **kwargs: Arguments for discover_connection_async()

        Returns:
            AsyncDatabaseManager instance
        """
        from .discovery import ConnectionDiscovery

        url = await ConnectionDiscovery.discover_connection_async(**kwargs)
        return cls(url=url)

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
        """Discover and return a working async connection URL.

        Args:
            user: Username
            password: Password
            host: Database host
            port: Database port (optional)
            database: Database name (optional)
            dialects: List of dialects to try (optional)
            timeout: Connection timeout

        Returns:
            Working async connection URL
        """
        from .discovery import ConnectionDiscovery

        return await ConnectionDiscovery.discover_connection_async(
            user=user,
            password=password,
            host=host,
            port=port,
            database=database,
            dialects=dialects,
            timeout=timeout,
        )
