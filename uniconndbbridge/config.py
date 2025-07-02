"""
Configuration classes for UniConnDBBridge.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from urllib.parse import quote_plus


@dataclass
class ConnectionInfo:
    """Database connection information."""

    dialect: str
    driver: str
    host: str
    port: int
    database: str
    user: str
    is_async: bool = False
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    engine_options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DBConfig:
    """Database configuration class."""

    dialect: str
    user: str
    password: str
    host: str = "localhost"
    port: Optional[int] = None
    database: Optional[str] = None
    driver: Optional[str] = None
    auth_plugin: Optional[str] = None
    auth_options: Dict[str, Any] = field(default_factory=dict)
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    pool_pre_ping: bool = True
    echo: bool = False
    engine_options: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Post-initialization to set default driver if not specified."""
        if self.driver is None:
            self.driver = self.get_default_driver()

    def get_default_driver(self) -> str:
        """Get the default driver for the dialect."""
        from .registry import DriverRegistry

        dialect_info = DriverRegistry.get_dialect_info(self.dialect)
        if not dialect_info:
            raise ValueError(f"Unsupported dialect: {self.dialect}")
        
        return dialect_info.default_driver

    def set_driver(self, driver: Optional[str] = None) -> None:
        """Set the driver, using default if None is provided."""
        if driver is None:
            self.driver = self.get_default_driver()
        else:
            # Validate the driver
            from .registry import DriverRegistry
            if not DriverRegistry.validate_driver(self.dialect, driver):
                raise ValueError(f"Driver '{driver}' is not supported for dialect '{self.dialect}'")
            self.driver = driver

    def to_url(self, driver_override: Optional[str] = None) -> str:
        """Convert configuration to SQLAlchemy URL."""
        from .registry import DriverRegistry

        # Get dialect info for default port
        dialect_info = DriverRegistry.get_dialect_info(self.dialect)
        if not dialect_info:
            raise ValueError(f"Unsupported dialect: {self.dialect}")

        # Determine driver
        effective_driver = driver_override or self.driver or dialect_info.default_driver

        # Determine port
        effective_port = self.port or dialect_info.default_port

        # URL encode credentials
        encoded_user = quote_plus(self.user)
        encoded_password = quote_plus(self.password)

        # Build URL
        if self.dialect == "sqlite":
            if self.database:
                return f"sqlite:///{self.database}"
            else:
                return "sqlite:///:memory:"

        # For other databases
        url_parts = [f"{self.dialect}"]
        if effective_driver:
            url_parts.append(f"+{effective_driver}")

        url_parts.extend(["://", f"{encoded_user}:{encoded_password}@{self.host}"])

        if effective_port:
            url_parts.append(f":{effective_port}")

        if self.database:
            url_parts.append(f"/{self.database}")

        return "".join(url_parts)

    def get_engine_options(self) -> Dict[str, Any]:
        """Get engine options for SQLAlchemy."""
        options = {
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_timeout": self.pool_timeout,
            "pool_recycle": self.pool_recycle,
            "pool_pre_ping": self.pool_pre_ping,
            "echo": self.echo,
        }

        # Add custom engine options
        options.update(self.engine_options)

        return options


class AuthPlugin(ABC):
    """Base class for authentication plugins."""

    @abstractmethod
    def authenticate(self, config: DBConfig) -> DBConfig:
        """Authenticate and return updated config."""
        pass

    @abstractmethod
    def get_connection_url(self, base_url: str) -> str:
        """Get modified connection URL with authentication."""
        pass

    @abstractmethod
    def configure_engine_args(self) -> Dict[str, Any]:
        """Get additional engine configuration."""
        pass

    async def configure_engine_args_async(self) -> Dict[str, Any]:
        """Get additional engine configuration for async engines."""
        return self.configure_engine_args()


class BasicAuthPlugin(AuthPlugin):
    """Basic username/password authentication."""

    def authenticate(self, config: DBConfig) -> DBConfig:
        """No additional authentication needed for basic auth."""
        return config

    def get_connection_url(self, base_url: str) -> str:
        """Return URL as-is for basic auth."""
        return base_url

    def configure_engine_args(self) -> Dict[str, Any]:
        """No additional engine args for basic auth."""
        return {}


class SSLAuthPlugin(AuthPlugin):
    """SSL certificate-based authentication."""

    def __init__(
        self,
        ssl_cert: Optional[str] = None,
        ssl_key: Optional[str] = None,
        ssl_ca: Optional[str] = None,
        ssl_mode: str = "require",
    ):
        self.ssl_cert = ssl_cert
        self.ssl_key = ssl_key
        self.ssl_ca = ssl_ca
        self.ssl_mode = ssl_mode

    def authenticate(self, config: DBConfig) -> DBConfig:
        """Add SSL configuration to auth options."""
        ssl_options = {
            "sslmode": self.ssl_mode,
        }

        if self.ssl_cert:
            ssl_options["sslcert"] = self.ssl_cert
        if self.ssl_key:
            ssl_options["sslkey"] = self.ssl_key
        if self.ssl_ca:
            ssl_options["sslrootcert"] = self.ssl_ca

        config.auth_options.update(ssl_options)
        return config

    def get_connection_url(self, base_url: str) -> str:
        """Add SSL parameters to URL."""
        from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

        parsed = urlparse(base_url)
        query_params = parse_qs(parsed.query)

        # Add SSL parameters
        if self.ssl_mode:
            query_params["sslmode"] = [self.ssl_mode]
        if self.ssl_cert:
            query_params["sslcert"] = [self.ssl_cert]
        if self.ssl_key:
            query_params["sslkey"] = [self.ssl_key]
        if self.ssl_ca:
            query_params["sslrootcert"] = [self.ssl_ca]

        # Rebuild query string
        new_query = urlencode(query_params, doseq=True)
        new_parsed = parsed._replace(query=new_query)

        return urlunparse(new_parsed)

    def configure_engine_args(self) -> Dict[str, Any]:
        """Configure SSL-specific engine options."""
        return {
            "connect_args": {
                "sslmode": self.ssl_mode,
                "sslcert": self.ssl_cert,
                "sslkey": self.ssl_key,
                "sslrootcert": self.ssl_ca,
            }
        }


def create_auth_plugin(plugin_type: str, **options: Any) -> AuthPlugin:
    """Create authentication plugin by type."""
    plugin_map = {
        "basic": BasicAuthPlugin,
        "ssl": SSLAuthPlugin,
    }

    plugin_class = plugin_map.get(plugin_type)
    if not plugin_class:
        raise ValueError(f"Unknown auth plugin type: {plugin_type}")

    return plugin_class(**options)
