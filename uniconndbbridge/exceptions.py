"""
Custom exceptions for UniConnDBBridge.
"""

from typing import Optional, Dict, Any, List


class UniConnDBError(Exception):
    """Base exception for all UniConnDB errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConnectionError(UniConnDBError):
    """Raised when database connection fails."""
    
    def __init__(self, 
                 message: str, 
                 dialect: Optional[str] = None,
                 host: Optional[str] = None,
                 port: Optional[int] = None,
                 database: Optional[str] = None,
                 original_error: Optional[Exception] = None):
        super().__init__(message)
        self.dialect = dialect
        self.host = host
        self.port = port
        self.database = database
        self.original_error = original_error
        
        # Store connection details
        self.details.update({
            "dialect": dialect,
            "host": host,
            "port": port,
            "database": database,
            "original_error": str(original_error) if original_error else None,
        })


class AuthenticationError(UniConnDBError):
    """Raised when authentication fails."""
    
    def __init__(self, 
                 message: str,
                 auth_method: Optional[str] = None,
                 user: Optional[str] = None,
                 original_error: Optional[Exception] = None):
        super().__init__(message)
        self.auth_method = auth_method
        self.user = user
        self.original_error = original_error
        
        # Store auth details (without sensitive info)
        self.details.update({
            "auth_method": auth_method,
            "user": user,
            "original_error": str(original_error) if original_error else None,
        })


class DiscoveryError(UniConnDBError):
    """Raised when connection discovery fails."""
    
    def __init__(self, 
                 message: str,
                 attempted_dialects: Optional[List[str]] = None,
                 failed_attempts: Optional[Dict[str, str]] = None):
        super().__init__(message)
        self.attempted_dialects = attempted_dialects or []
        self.failed_attempts = failed_attempts or {}
        
        # Store discovery details
        self.details.update({
            "attempted_dialects": self.attempted_dialects,
            "failed_attempts": self.failed_attempts,
        })


class ConfigurationError(UniConnDBError):
    """Raised when configuration is invalid."""
    
    def __init__(self, 
                 message: str,
                 config_field: Optional[str] = None,
                 config_value: Optional[Any] = None):
        super().__init__(message)
        self.config_field = config_field
        self.config_value = config_value
        
        # Store config details
        self.details.update({
            "config_field": config_field,
            "config_value": str(config_value) if config_value is not None else None,
        })


class DriverNotFoundError(UniConnDBError):
    """Raised when required database driver is not installed."""
    
    def __init__(self, 
                 message: str,
                 dialect: Optional[str] = None,
                 driver: Optional[str] = None,
                 install_command: Optional[str] = None):
        super().__init__(message)
        self.dialect = dialect
        self.driver = driver
        self.install_command = install_command
        
        # Store driver details
        self.details.update({
            "dialect": dialect,
            "driver": driver,
            "install_command": install_command,
        })


class PoolError(UniConnDBError):
    """Raised when connection pool encounters an error."""
    
    def __init__(self, 
                 message: str,
                 pool_size: Optional[int] = None,
                 checked_out: Optional[int] = None):
        super().__init__(message)
        self.pool_size = pool_size
        self.checked_out = checked_out
        
        # Store pool details
        self.details.update({
            "pool_size": pool_size,
            "checked_out": checked_out,
        })


class TransactionError(UniConnDBError):
    """Raised when transaction management fails."""
    
    def __init__(self, 
                 message: str,
                 operation: Optional[str] = None,
                 in_transaction: Optional[bool] = None):
        super().__init__(message)
        self.operation = operation
        self.in_transaction = in_transaction
        
        # Store transaction details
        self.details.update({
            "operation": operation,
            "in_transaction": in_transaction,
        })


def wrap_sqlalchemy_error(original_error: Exception, 
                         operation: Optional[str] = None) -> UniConnDBError:
    """Wrap SQLAlchemy exceptions into UniConnDB exceptions."""
    
    error_message = str(original_error)
    
    # Import SQLAlchemy exceptions for checking
    try:
        from sqlalchemy.exc import (
            DisconnectionError, 
            InvalidRequestError,
            OperationalError,
            ProgrammingError,
            IntegrityError,
            DataError,
            TimeoutError as SQLTimeoutError,
        )
    except ImportError:
        # If SQLAlchemy is not available, return generic error
        return UniConnDBError(f"Database error: {error_message}")
    
    # Map SQLAlchemy exceptions to UniConnDB exceptions
    if isinstance(original_error, DisconnectionError):
        return ConnectionError(
            f"Database connection lost: {error_message}",
            original_error=original_error
        )
    
    elif isinstance(original_error, OperationalError):
        if "authentication" in error_message.lower():
            return AuthenticationError(
                f"Authentication failed: {error_message}",
                original_error=original_error
            )
        else:
            return ConnectionError(
                f"Operational error: {error_message}",
                original_error=original_error
            )
    
    elif isinstance(original_error, SQLTimeoutError):
        return PoolError(
            f"Connection timeout: {error_message}",
            original_error=original_error
        )
    
    elif isinstance(original_error, InvalidRequestError):
        if "transaction" in error_message.lower():
            return TransactionError(
                f"Transaction error: {error_message}",
                operation=operation,
                original_error=original_error
            )
        else:
            return ConfigurationError(
                f"Invalid request: {error_message}",
                original_error=original_error
            )
    
    # For other SQLAlchemy exceptions, return generic error
    return UniConnDBError(
        f"Database error during {operation or 'operation'}: {error_message}",
        details={"original_error": str(original_error)}
    )