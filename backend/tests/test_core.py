"""Unit tests for core auth and SQL services."""

import pytest
from fastapi import HTTPException

from app.services.auth_service import hash_password, verify_password, create_access_token, decode_access_token
from app.services.sql_service import validate_sql


def test_password_hashing():
    """Verify passwords hash and verify correctly using bcrypt."""
    password = "super-secret-password-123"
    hashed = hash_password(password)
    
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_jwt_operations():
    """Verify access tokens can be created and correctly decoded."""
    payload = {"sub": "user-uuid-12345", "role": "admin"}
    token = create_access_token(payload)
    
    assert isinstance(token, str)
    
    decoded = decode_access_token(token)
    assert decoded["sub"] == "user-uuid-12345"
    assert decoded["role"] == "admin"
    assert "exp" in decoded


def test_jwt_invalid_token():
    """Verify invalid/expired tokens raise an unauthorized HTTP Exception."""
    with pytest.raises(HTTPException) as excinfo:
        decode_access_token("completely-invalid-token-string")
    assert excinfo.value.status_code == 401


def test_sql_validation_safe_queries():
    """Verify standard read-only SELECT and WITH statements pass validation."""
    safe_queries = [
        "SELECT * FROM sales;",
        "SELECT id, name FROM customers WHERE lifetime_value > 1000",
        "SELECT COUNT(*) FROM employees GROUP BY department",
        "WITH sales_summary AS (SELECT region, SUM(amount) as total FROM sales GROUP BY region) SELECT * FROM sales_summary ORDER BY total DESC;"
    ]
    
    for q in safe_queries:
        is_safe, reason = validate_sql(q)
        assert is_safe is True, f"Query failed validation but should be safe: {q}. Reason: {reason}"


def test_sql_validation_unsafe_queries():
    """Verify DML, DDL, and multi-statement injection patterns are blocked."""
    unsafe_queries = [
        "INSERT INTO sales (product, region, amount) VALUES ('New Product', 'East', 100.00)",
        "UPDATE employees SET salary = 999999 WHERE id = 1",
        "DELETE FROM customers WHERE id = 5",
        "DROP TABLE sales",
        "ALTER TABLE employees ADD COLUMN test VARCHAR(10)",
        "TRUNCATE TABLE sales",
        "CREATE TABLE hack (id SERIAL)",
        "GRANT ALL PRIVILEGES ON DATABASE nexus TO public",
        "SELECT * FROM sales; DROP TABLE employees;",
        "SELECT * FROM customers; --",  # wait, double dash is fine or we can ignore it, but let's test blocked keywords
        "UPDATE customers SET lifetime_value = 0"
    ]
    
    for q in unsafe_queries:
        is_safe, reason = validate_sql(q)
        assert is_safe is False, f"Query passed validation but should be unsafe: {q}"
        assert len(reason) > 0
