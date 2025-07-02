import pytest

from uniconndbbridge.config import DBConfig
from uniconndbbridge.core import DatabaseManager


@pytest.fixture(scope="module")
def mysql_config():
    return DBConfig(
        dialect="mysql",
        driver="mysqlconnector",
        host="127.0.0.1",
        port=3307,
        user="testuser",
        password="testpassword",
        database="testdb",
    )


@pytest.fixture(scope="module")
def postgres_config():
    return DBConfig(
        dialect="postgresql",
        host="127.0.0.1",
        port=5432,
        user="testuser",
        password="testpassword",
        database="testdb",
    )


def test_mysql_connection(mysql_config):
    """Tests connection to the MySQL test database and fetches data."""
    try:
        with DatabaseManager(config=mysql_config) as bridge:
            rows = bridge.fetch_many("SELECT * FROM sample_table;")
            assert len(rows) == 2
            assert rows[0][1] == "test1"
    except Exception as e:
        pytest.fail(f"MySQL connection test failed: {e}")


def test_postgres_connection(postgres_config):
    """Tests connection to the PostgreSQL test database and fetches data."""
    try:
        with DatabaseManager(config=postgres_config) as bridge:
            rows = bridge.fetch_many("SELECT * FROM sample_table;")
            assert len(rows) == 2
            assert rows[0][1] == "test1"
    except Exception as e:
        pytest.fail(f"PostgreSQL connection test failed: {e}")


def test_connection_discovery():
    """Tests auto-discovery of database connections using DatabaseManager.from_discovery."""
    try:
        # Test discovering MySQL connection
        mysql_manager = DatabaseManager.from_discovery(
            user="testuser",
            password="testpassword",
            host="127.0.0.1",
            port=3307,
            database="testdb",
            dialects=["mysql"],
            timeout=10.0,
        )

        # Test the connection works
        with mysql_manager as bridge:
            rows = bridge.fetch_many("SELECT * FROM sample_table;")
            assert len(rows) == 2
            assert rows[0][1] == "test1"

    except Exception as e:
        pytest.fail(f"MySQL discovery test failed: {e}")

    try:
        # Test discovering PostgreSQL connection
        postgres_manager = DatabaseManager.from_discovery(
            user="testuser",
            password="testpassword",
            host="127.0.0.1",
            database="testdb",
            dialects=["postgresql"],
            timeout=10.0,
        )

        # Test the connection works
        with postgres_manager as bridge:
            rows = bridge.fetch_many("SELECT * FROM sample_table;")
            assert len(rows) == 2
            assert rows[0][1] == "test1"

    except Exception as e:
        pytest.fail(f"PostgreSQL discovery test failed: {e}")


def test_connection_discovery_multiple_dialects():
    """Tests auto-discovery with multiple dialects."""
    try:
        # Test discovering connection from both MySQL and PostgreSQL
        manager = DatabaseManager.from_discovery(
            user="testuser",
            password="testpassword",
            host="127.0.0.1",
            database="testdb",
            dialects=["mysql", "postgresql"],
            timeout=10.0,
        )

        # Test the discovered connection works
        with manager as bridge:
            rows = bridge.fetch_many("SELECT * FROM sample_table;")
            assert len(rows) == 2
            assert rows[0][1] == "test1"

    except Exception as e:
        pytest.fail(f"Multiple dialects discovery test failed: {e}")


def test_connection_discovery_invalid_config():
    """Tests auto-discovery with invalid configurations."""
    with pytest.raises(Exception):
        # Test with invalid host - should raise an exception
        DatabaseManager.from_discovery(
            user="invalid",
            password="invalid",
            host="invalid-host",
            database="invalid",
            dialects=["mysql", "postgresql"],
            timeout=5.0,
        )
