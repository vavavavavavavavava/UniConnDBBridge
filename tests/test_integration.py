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


