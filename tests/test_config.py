"""
Tests for configuration classes.
"""

from uniconndbbridge.config import (
    BasicAuthPlugin,
    ConnectionInfo,
    DBConfig,
    SSLAuthPlugin,
)


class TestDBConfig:
    """Test DBConfig class."""

    def test_basic_config(self):
        """Test basic configuration creation."""
        config = DBConfig(
            dialect="postgresql",
            user="testuser",
            password="testpass",
            host="localhost",
            database="testdb",
        )

        assert config.dialect == "postgresql"
        assert config.user == "testuser"
        assert config.password == "testpass"
        assert config.host == "localhost"
        assert config.database == "testdb"
        assert config.port is None

    def test_to_url_postgresql(self):
        """Test URL generation for PostgreSQL."""
        config = DBConfig(
            dialect="postgresql",
            user="testuser",
            password="testpass",
            host="localhost",
            port=5432,
            database="testdb",
        )

        url = config.to_url()
        assert "postgresql+psycopg2://" in url
        assert "testuser:testpass@localhost:5432/testdb" in url

    def test_to_url_mysql(self):
        """Test URL generation for MySQL."""
        config = DBConfig(
            dialect="mysql",
            user="testuser",
            password="testpass",
            host="localhost",
            database="testdb",
        )

        url = config.to_url()
        assert "mysql+mysqlconnector://" in url
        assert "testuser:testpass@localhost" in url

    def test_to_url_sqlite(self):
        """Test URL generation for SQLite."""
        config = DBConfig(
            dialect="sqlite", user="", password="", database="/path/to/db.sqlite"
        )

        url = config.to_url()
        assert url == "sqlite:////path/to/db.sqlite"

    def test_to_url_sqlite_memory(self):
        """Test URL generation for SQLite in-memory."""
        config = DBConfig(dialect="sqlite", user="", password="")

        url = config.to_url()
        assert url == "sqlite:///:memory:"

    def test_get_engine_options(self):
        """Test engine options generation."""
        config = DBConfig(
            dialect="postgresql",
            user="testuser",
            password="testpass",
            pool_size=20,
            max_overflow=30,
            echo=True,
        )

        options = config.get_engine_options()
        assert options["pool_size"] == 20
        assert options["max_overflow"] == 30
        assert options["echo"] is True

    def test_default_driver_setting(self):
        """Test that default driver is set when not specified."""
        config = DBConfig(
            dialect="postgresql",
            user="testuser",
            password="testpass",
        )

        # Driver should be set to default for PostgreSQL
        assert config.driver == "psycopg2"

    def test_explicit_driver_preserved(self):
        """Test that explicitly set driver is preserved."""
        config = DBConfig(
            dialect="postgresql",
            user="testuser",
            password="testpass",
            driver="pg8000",
        )

        # Explicitly set driver should be preserved
        assert config.driver == "pg8000"

    def test_set_driver_method(self):
        """Test set_driver method."""
        config = DBConfig(
            dialect="postgresql",
            user="testuser",
            password="testpass",
            driver="pg8000",
        )

        # Set to default driver
        config.set_driver(None)
        assert config.driver == "psycopg2"

        # Set to specific driver
        config.set_driver("pg8000")
        assert config.driver == "pg8000"

    def test_set_driver_validation(self):
        """Test driver validation in set_driver method."""
        config = DBConfig(
            dialect="postgresql",
            user="testuser",
            password="testpass",
        )

        # Try to set invalid driver
        try:
            config.set_driver("invalid_driver")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "invalid_driver" in str(e)
            assert "postgresql" in str(e)

    def test_get_default_driver(self):
        """Test get_default_driver method."""
        config = DBConfig(
            dialect="mysql",
            user="testuser",
            password="testpass",
        )

        default_driver = config.get_default_driver()
        assert default_driver == "mysqlconnector"

    def test_unsupported_dialect_error(self):
        """Test error handling for unsupported dialect."""
        try:
            config = DBConfig(
                dialect="unsupported_db",
                user="testuser",
                password="testpass",
            )
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Unsupported dialect" in str(e)
            assert "unsupported_db" in str(e)


class TestConnectionInfo:
    """Test ConnectionInfo class."""

    def test_connection_info_creation(self):
        """Test ConnectionInfo creation."""
        info = ConnectionInfo(
            dialect="postgresql",
            driver="psycopg2",
            host="localhost",
            port=5432,
            database="testdb",
            user="testuser",
        )

        assert info.dialect == "postgresql"
        assert info.driver == "psycopg2"
        assert info.host == "localhost"
        assert info.port == 5432
        assert info.database == "testdb"
        assert info.user == "testuser"
        assert info.is_async is False


class TestAuthPlugins:
    """Test authentication plugins."""

    def test_basic_auth_plugin(self):
        """Test BasicAuthPlugin."""
        plugin = BasicAuthPlugin()

        config = DBConfig(dialect="postgresql", user="testuser", password="testpass")

        # Basic auth shouldn't modify config
        result_config = plugin.authenticate(config)
        assert result_config == config

        # Should return URL as-is
        url = "postgresql://user:pass@localhost/db"
        result_url = plugin.get_connection_url(url)
        assert result_url == url

        # Should return empty engine args
        args = plugin.configure_engine_args()
        assert args == {}

    def test_ssl_auth_plugin(self):
        """Test SSLAuthPlugin."""
        plugin = SSLAuthPlugin(
            ssl_cert="/path/to/cert.pem",
            ssl_key="/path/to/key.pem",
            ssl_ca="/path/to/ca.pem",
            ssl_mode="require",
        )

        config = DBConfig(dialect="postgresql", user="testuser", password="testpass")

        # SSL auth should add options to config
        result_config = plugin.authenticate(config)
        assert "sslmode" in result_config.auth_options
        assert result_config.auth_options["sslmode"] == "require"

        # Should modify URL to include SSL parameters
        url = "postgresql://user:pass@localhost/db"
        result_url = plugin.get_connection_url(url)
        assert "sslmode=require" in result_url
        assert "sslcert" in result_url

        # Should return SSL engine args
        args = plugin.configure_engine_args()
        assert "connect_args" in args
        assert args["connect_args"]["sslmode"] == "require"
