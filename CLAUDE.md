# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

UniConnDBBridge is a universal SQLAlchemy database manager that provides a unified interface for all database types with support for various authentication methods. The library supports both synchronous and asynchronous operations with automatic driver selection.

## Development Commands

### Testing

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=uniconndbbridge --cov-report=term-missing

# Run specific test file
pytest tests/test_config.py

# Run async tests
pytest -k "async" --asyncio-mode=auto
```

### Code Quality

```bash
# Run type checking
mypy uniconndbbridge/

# Run linting and formatting
ruff check uniconndbbridge/
ruff format uniconndbbridge/
```

### Package Management

```bash
# Install dependencies
poetry install

# Install with specific database extras
poetry install -E postgres -E mysql -E oracle

# Add new dependency
poetry add <package>

# Build package
poetry build
```

### Documentation

```bash
# Build docs (if MkDocs is configured)
mkdocs build
mkdocs serve
```

## Architecture

### Core Components

1. **DatabaseManager** (`core.py`) - Synchronous database manager
   - Handles engine creation, session management, and connection pooling
   - Supports context managers for automatic resource cleanup
   - Provides utility methods for common database operations

2. **AsyncDatabaseManager** (`async_.py`) - Asynchronous database manager
   - Async version of DatabaseManager using SQLAlchemy's async engine
   - Requires SQLAlchemy with async support

3. **DBConfig** (`config.py`) - Configuration management
   - Handles database connection parameters
   - Supports URL generation from configuration
   - Manages authentication plugins

4. **DriverRegistry** (`registry.py`) - Driver management system
   - Maintains information about supported database dialects
   - Handles driver availability checking and installation commands
   - Supports custom dialect registration

5. **AuthPlugin** (`config.py`) - Authentication plugin system
   - Base class for authentication methods (basic, SSL, Kerberos, IAM, etc.)
   - Plugins modify connection URLs and engine arguments

### Key Design Patterns

- **Factory Pattern**: Used for creating auth plugins and database managers
- **Registry Pattern**: Driver registry for managing database drivers
- **Context Manager**: Automatic resource management for sessions and connections
- **Plugin Architecture**: Extensible authentication system

### Database Support

The library supports major databases through the DriverRegistry:

- PostgreSQL (psycopg2, asyncpg, pg8000)
- MySQL (mysqlclient, pymysql, aiomysql, asyncmy)
- SQLite (built-in, aiosqlite)
- Oracle (oracledb, cx_oracle)
- SQL Server (pyodbc, pymssql, aioodbc)

### Error Handling

- Custom exception hierarchy in `exceptions.py`
- SQLAlchemy errors are wrapped with context information
- Connection and configuration errors are handled separately

## Development Guidelines

### Adding New Database Dialects

1. Add dialect information to `DriverRegistry.initialize()` in `registry.py`
2. Include driver packages, install commands, and port information
3. Test driver availability and requirements checking

### Adding Authentication Plugins

1. Create new class inheriting from `AuthPlugin` in `config.py`
2. Implement required methods: `authenticate()`, `get_connection_url()`, `configure_engine_args()`
3. Register the plugin in `create_auth_plugin()` function
4. Add async support if needed with `configure_engine_args_async()`

### Testing

- Tests are organized by component in `tests/` directory
- Use pytest fixtures for database setup and teardown
- Test both sync and async functionality where applicable
- Mock external dependencies for unit tests

### Dependencies

Core dependencies are minimal:

- SQLAlchemy >= 2.0 (core requirement)
- typing-extensions (for older Python versions)
- Optional database drivers based on usage

The project uses Poetry for dependency management with optional extras for specific databases.
