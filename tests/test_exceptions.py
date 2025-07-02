"""
Tests for custom exceptions.
"""

from uniconndbbridge.exceptions import (
    AuthenticationError,
    ConfigurationError,
    ConnectionError,
    DriverNotFoundError,
    PoolError,
    TransactionError,
    UniConnDBError,
    wrap_sqlalchemy_error,
)


class TestCustomExceptions:
    """Test custom exception classes."""

    def test_base_exception(self):
        """Test base UniConnDBError."""
        details = {"key": "value"}
        error = UniConnDBError("Test error", details=details)

        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.details == details

    def test_connection_error(self):
        """Test ConnectionError."""
        original_error = Exception("Original error")
        error = ConnectionError(
            "Connection failed",
            dialect="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            original_error=original_error,
        )

        assert str(error) == "Connection failed"
        assert error.dialect == "postgresql"
        assert error.host == "localhost"
        assert error.port == 5432
        assert error.database == "testdb"
        assert error.original_error == original_error

        # Check details
        assert error.details["dialect"] == "postgresql"
        assert error.details["host"] == "localhost"
        assert error.details["original_error"] == "Original error"

    def test_authentication_error(self):
        """Test AuthenticationError."""
        error = AuthenticationError(
            "Auth failed", auth_method="password", user="testuser"
        )

        assert str(error) == "Auth failed"
        assert error.auth_method == "password"
        assert error.user == "testuser"
        assert error.details["auth_method"] == "password"
        assert error.details["user"] == "testuser"


    def test_configuration_error(self):
        """Test ConfigurationError."""
        error = ConfigurationError(
            "Invalid config", config_field="dialect", config_value="unknown"
        )

        assert str(error) == "Invalid config"
        assert error.config_field == "dialect"
        assert error.config_value == "unknown"
        assert error.details["config_field"] == "dialect"
        assert error.details["config_value"] == "unknown"

    def test_driver_not_found_error(self):
        """Test DriverNotFoundError."""
        error = DriverNotFoundError(
            "Driver not found",
            dialect="postgresql",
            driver="psycopg2",
            install_command="pip install psycopg2-binary",
        )

        assert str(error) == "Driver not found"
        assert error.dialect == "postgresql"
        assert error.driver == "psycopg2"
        assert error.install_command == "pip install psycopg2-binary"
        assert error.details["install_command"] == "pip install psycopg2-binary"

    def test_pool_error(self):
        """Test PoolError."""
        error = PoolError("Pool exhausted", pool_size=10, checked_out=10)

        assert str(error) == "Pool exhausted"
        assert error.pool_size == 10
        assert error.checked_out == 10
        assert error.details["pool_size"] == 10
        assert error.details["checked_out"] == 10

    def test_transaction_error(self):
        """Test TransactionError."""
        error = TransactionError(
            "Transaction failed", operation="commit", in_transaction=True
        )

        assert str(error) == "Transaction failed"
        assert error.operation == "commit"
        assert error.in_transaction is True
        assert error.details["operation"] == "commit"
        assert error.details["in_transaction"] is True


class TestSQLAlchemyErrorWrapping:
    """Test SQLAlchemy error wrapping."""

    def test_wrap_generic_error(self):
        """Test wrapping generic exceptions."""
        original = Exception("Generic error")
        wrapped = wrap_sqlalchemy_error(original, "test operation")

        assert isinstance(wrapped, UniConnDBError)
        assert "test operation" in str(wrapped)
        assert "Generic error" in str(wrapped)

    def test_wrap_without_sqlalchemy(self):
        """Test wrapping when SQLAlchemy is not available."""
        # This simulates the case where SQLAlchemy import fails
        original = Exception("Some error")
        wrapped = wrap_sqlalchemy_error(original)

        assert isinstance(wrapped, UniConnDBError)
        assert "Database error" in str(wrapped)
