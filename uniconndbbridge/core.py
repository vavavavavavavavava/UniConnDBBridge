"""
Core DatabaseManager implementation for synchronous database operations.
"""

import logging
from contextlib import contextmanager
from typing import Union, Optional, Dict, Any, Generator, List, Sequence
from urllib.parse import urlparse

from sqlalchemy import create_engine, Engine, text, MetaData
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import Executable

from .config import DBConfig, ConnectionInfo, AuthPlugin, create_auth_plugin
from .registry import DriverRegistry
from .exceptions import (
    ConnectionError,
    ConfigurationError,
    DriverNotFoundError,
    wrap_sqlalchemy_error,
)


logger = logging.getLogger(__name__)


class DatabaseManager:
    """Synchronous database connection manager."""
    
    def __init__(self, 
                 url: Optional[str] = None,
                 *,
                 config: Optional[Union[DBConfig, Dict[str, Any]]] = None,
                 **kwargs: Any):
        """Initialize DatabaseManager.
        
        Args:
            url: SQLAlchemy database URL
            config: Database configuration (DBConfig or dict)
            **kwargs: Additional engine options
        """
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._url: Optional[str] = None
        self._config: Optional[DBConfig] = None
        self._auth_plugin: Optional[AuthPlugin] = None
        
        if url and config:
            raise ConfigurationError("Cannot specify both url and config")
        
        if not url and not config:
            raise ConfigurationError("Must specify either url or config")
        
        if url:
            self._url = url
        else:
            # Convert dict to DBConfig if needed
            if isinstance(config, dict):
                config = DBConfig(**config)
            self._config = config
            
            # Create auth plugin if specified
            if config.auth_plugin:
                self._auth_plugin = create_auth_plugin(
                    config.auth_plugin,
                    **config.auth_options
                )
                # Apply authentication
                self._config = self._auth_plugin.authenticate(config)
            
            # Generate URL from config
            self._url = config.to_url()
        
        # Store additional engine options
        self._engine_kwargs = kwargs
        
        logger.info(f"Initialized DatabaseManager with URL: {self._mask_url(self._url)}")
    
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
    def engine(self) -> Engine:
        """Get or create the SQLAlchemy engine."""
        if self._engine is None:
            self._create_engine()
        return self._engine
    
    def _create_engine(self) -> None:
        """Create the SQLAlchemy engine."""
        try:
            # Prepare engine options
            engine_options = {}
            
            # Add config-based options
            if self._config:
                engine_options.update(self._config.get_engine_options())
            
            # Add auth plugin options
            if self._auth_plugin:
                auth_options = self._auth_plugin.configure_engine_args()
                engine_options.update(auth_options)
            
            # Add additional options
            engine_options.update(self._engine_kwargs)
            
            # Get final URL from auth plugin if available
            final_url = self._url
            if self._auth_plugin:
                final_url = self._auth_plugin.get_connection_url(self._url)
            
            logger.debug(f"Creating engine with options: {engine_options}")
            self._engine = create_engine(final_url, **engine_options)
            
            # Create session factory
            self._session_factory = sessionmaker(bind=self._engine)
            
            logger.info("Database engine created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create database engine: {e}")
            raise wrap_sqlalchemy_error(e, "engine creation")
    
    def connect_info(self) -> ConnectionInfo:
        """Get connection information from the current engine."""
        engine = self.engine  # This will create engine if needed
        
        try:
            url = engine.url
            
            return ConnectionInfo(
                dialect=url.drivername.split('+')[0] if '+' in url.drivername else url.drivername,
                driver=url.drivername.split('+')[1] if '+' in url.drivername else 'default',
                host=url.host or 'localhost',
                port=url.port or 0,
                database=url.database or '',
                user=url.username or '',
                is_async=False,
                pool_size=getattr(engine.pool, 'size', lambda: 0)(),
                max_overflow=getattr(engine.pool, 'max_overflow', 0),
                pool_timeout=getattr(engine.pool, 'timeout', 30),
                engine_options=dict(engine.pool.get_pool().params) if hasattr(engine.pool, 'get_pool') else {}
            )
        except Exception as e:
            logger.error(f"Failed to get connection info: {e}")
            raise wrap_sqlalchemy_error(e, "connection info retrieval")
    
    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Get a database session with automatic transaction management."""
        if self._session_factory is None:
            # Trigger engine creation
            _ = self.engine
        
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Session error, rolling back: {e}")
            raise wrap_sqlalchemy_error(e, "session operation")
        finally:
            session.close()
    
    @contextmanager
    def connection(self):
        """Get a raw database connection."""
        conn = self.engine.connect()
        try:
            yield conn
        except Exception as e:
            logger.error(f"Connection error: {e}")
            raise wrap_sqlalchemy_error(e, "connection operation")
        finally:
            conn.close()
    
    def execute(self, statement: Union[str, Executable], parameters: Optional[Dict[str, Any]] = None):
        """Execute a SQL statement."""
        try:
            with self.connection() as conn:
                if isinstance(statement, str):
                    statement = text(statement)
                
                if parameters:
                    result = conn.execute(statement, parameters)
                else:
                    result = conn.execute(statement)
                
                conn.commit()
                return result
                
        except Exception as e:
            logger.error(f"Failed to execute statement: {e}")
            raise wrap_sqlalchemy_error(e, "statement execution")
    
    def fetch_one(self, statement: Union[str, Executable], parameters: Optional[Dict[str, Any]] = None):
        """Execute a statement and fetch one result."""
        result = self.execute(statement, parameters)
        return result.fetchone()
    
    def fetch_many(self, statement: Union[str, Executable], 
                   size: Optional[int] = None,
                   parameters: Optional[Dict[str, Any]] = None):
        """Execute a statement and fetch multiple results."""
        result = self.execute(statement, parameters)
        if size is not None:
            return result.fetchmany(size)
        return result.fetchall()
    
    def get_table_names(self, schema: Optional[str] = None) -> List[str]:
        """Get list of table names in the database."""
        try:
            with self.connection() as conn:
                metadata = MetaData()
                metadata.reflect(bind=conn, schema=schema)
                return list(metadata.tables.keys())
        except Exception as e:
            logger.error(f"Failed to get table names: {e}")
            raise wrap_sqlalchemy_error(e, "table name retrieval")
    
    def get_column_names(self, table_name: str, schema: Optional[str] = None) -> List[str]:
        """Get column names for a table."""
        try:
            with self.connection() as conn:
                metadata = MetaData()
                metadata.reflect(bind=conn, schema=schema, only=[table_name])
                
                full_table_name = f"{schema}.{table_name}" if schema else table_name
                if full_table_name in metadata.tables:
                    table = metadata.tables[full_table_name]
                    return [col.name for col in table.columns]
                else:
                    return []
        except Exception as e:
            logger.error(f"Failed to get column names for {table_name}: {e}")
            raise wrap_sqlalchemy_error(e, "column name retrieval")
    
    def test_connection(self) -> bool:
        """Test the database connection."""
        try:
            with self.connection() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Connection test successful")
            return True
        except Exception as e:
            logger.warning(f"Connection test failed: {e}")
            return False
    
    def close(self) -> None:
        """Close the database engine and all connections."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Database engine closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    @classmethod
    def from_discovery(cls, **kwargs) -> "DatabaseManager":
        """Create DatabaseManager using connection discovery.
        
        Args:
            **kwargs: Arguments for discover_connection()
        
        Returns:
            DatabaseManager instance
        """
        from .discovery import ConnectionDiscovery
        
        url = ConnectionDiscovery.discover_connection(**kwargs)
        return cls(url=url)
    
    @classmethod
    def discover_connection(cls, *,
                           user: str,
                           password: str,
                           host: str = "localhost",
                           port: Optional[int] = None,
                           database: Optional[str] = None,
                           dialects: Optional[Sequence[str]] = None,
                           timeout: float = 5.0) -> str:
        """Discover and return a working connection URL.
        
        Args:
            user: Username
            password: Password  
            host: Database host
            port: Database port (optional)
            database: Database name (optional)
            dialects: List of dialects to try (optional)
            timeout: Connection timeout
            
        Returns:
            Working connection URL
        """
        from .discovery import ConnectionDiscovery
        
        return ConnectionDiscovery.discover_connection(
            user=user,
            password=password,
            host=host,
            port=port,
            database=database,
            dialects=dialects,
            timeout=timeout
        )