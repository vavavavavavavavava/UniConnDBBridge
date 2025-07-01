"""
Tests for driver registry system.
"""

from uniconndbbridge.registry import DialectInfo, DriverRegistry


class TestDriverRegistry:
    """Test DriverRegistry class."""

    def test_initialization(self):
        """Test registry initialization."""
        DriverRegistry.initialize()

        dialects = DriverRegistry.get_supported_dialects()
        assert "postgresql" in dialects
        assert "mysql" in dialects
        assert "sqlite" in dialects
        assert "oracle" in dialects
        assert "mssql" in dialects

    def test_get_dialect_info(self):
        """Test getting dialect information."""
        DriverRegistry.initialize()

        # Test PostgreSQL
        pg_info = DriverRegistry.get_dialect_info("postgresql")
        assert pg_info is not None
        assert pg_info.name == "postgresql"
        assert pg_info.default_driver == "psycopg2"
        assert pg_info.default_port == 5432
        assert "psycopg2" in pg_info.sync_drivers
        assert "asyncpg" in pg_info.async_drivers

        # Test MySQL
        mysql_info = DriverRegistry.get_dialect_info("mysql")
        assert mysql_info is not None
        assert mysql_info.name == "mysql"
        assert mysql_info.default_port == 3306

        # Test SQLite
        sqlite_info = DriverRegistry.get_dialect_info("sqlite")
        assert sqlite_info is not None
        assert sqlite_info.name == "sqlite"
        assert sqlite_info.default_port == 0

        # Test unknown dialect
        unknown_info = DriverRegistry.get_dialect_info("unknown")
        assert unknown_info is None

    def test_validate_driver(self):
        """Test driver validation."""
        DriverRegistry.initialize()

        # Test valid sync drivers
        assert DriverRegistry.validate_driver("postgresql", "psycopg2", is_async=False)
        assert DriverRegistry.validate_driver("mysql", "mysqlclient", is_async=False)

        # Test valid async drivers
        assert DriverRegistry.validate_driver("postgresql", "asyncpg", is_async=True)
        assert DriverRegistry.validate_driver("mysql", "aiomysql", is_async=True)

        # Test invalid combinations
        assert not DriverRegistry.validate_driver(
            "postgresql", "asyncpg", is_async=False
        )
        assert not DriverRegistry.validate_driver(
            "postgresql", "psycopg2", is_async=True
        )
        assert not DriverRegistry.validate_driver(
            "postgresql", "unknown_driver", is_async=False
        )
        assert not DriverRegistry.validate_driver(
            "unknown_dialect", "psycopg2", is_async=False
        )

    def test_get_install_command(self):
        """Test getting installation commands."""
        DriverRegistry.initialize()

        cmd = DriverRegistry.get_install_command("postgresql", "psycopg2")
        assert cmd == "pip install psycopg2-binary"

        cmd = DriverRegistry.get_install_command("postgresql", "asyncpg")
        assert cmd == "pip install asyncpg"

        cmd = DriverRegistry.get_install_command("unknown", "unknown")
        assert cmd is None

    def test_register_custom_dialect(self):
        """Test registering custom dialect."""
        DriverRegistry.initialize()

        custom_info = DialectInfo(
            name="custom",
            default_driver="custom_driver",
            default_port=1234,
            async_drivers=["async_custom"],
            sync_drivers=["custom_driver"],
            required_packages={"custom_driver": ["custom_package"]},
            install_commands={"custom_driver": "pip install custom_package"},
        )

        DriverRegistry.register_dialect(custom_info)

        # Test that custom dialect is registered
        retrieved_info = DriverRegistry.get_dialect_info("custom")
        assert retrieved_info is not None
        assert retrieved_info.name == "custom"
        assert retrieved_info.default_port == 1234

        # Test it's in supported dialects
        dialects = DriverRegistry.get_supported_dialects()
        assert "custom" in dialects

    def test_check_driver_requirements(self):
        """Test checking driver requirements."""
        DriverRegistry.initialize()

        # Test built-in SQLite (should always be available)
        requirements_met, missing = DriverRegistry.check_driver_requirements(
            "sqlite", "pysqlite"
        )
        assert requirements_met is True
        assert len(missing) == 0

        # Test unknown dialect
        requirements_met, missing = DriverRegistry.check_driver_requirements(
            "unknown", "unknown"
        )
        assert requirements_met is False
        assert "Unknown dialect: unknown" in missing

    def test_get_driver_info(self):
        """Test getting detailed driver information."""
        DriverRegistry.initialize()

        info = DriverRegistry.get_driver_info("postgresql", "psycopg2")
        assert info["dialect"] == "postgresql"
        assert info["driver"] == "psycopg2"
        assert info["is_sync"] is True
        assert info["is_async"] is False
        assert info["default_port"] == 5432
        assert "psycopg2-binary" in info["required_packages"]

        info = DriverRegistry.get_driver_info("postgresql", "asyncpg")
        assert info["is_sync"] is False
        assert info["is_async"] is True

        # Test unknown driver
        info = DriverRegistry.get_driver_info("unknown", "unknown")
        assert info == {}
