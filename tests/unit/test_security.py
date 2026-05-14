"""
Security module unit tests — v6 completos.
Valida que todas las funciones JWT estén disponibles (fix v6 crítico).
"""
import pytest
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token_type,
    sanitize_input,
)
from app.core.exceptions import AuthenticationException


# ── Password ──────────────────────────────────────────────────────────────

def test_password_hash_and_verify():
    hashed = hash_password("MySecret123!")
    assert verify_password("MySecret123!", hashed)
    assert not verify_password("WrongPassword", hashed)


def test_empty_password_raises():
    with pytest.raises(ValueError):
        hash_password("")


def test_password_over_72_bytes_raises():
    with pytest.raises(ValueError):
        hash_password("x" * 73)


# ── Access Token ──────────────────────────────────────────────────────────

def test_access_token_roundtrip():
    token = create_access_token("user-123", {"role": "admin"})
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"


def test_access_token_without_extra_claims():
    token = create_access_token("user-abc")
    payload = decode_token(token)
    assert payload["sub"] == "user-abc"
    assert payload["type"] == "access"


# ── Refresh Token ─────────────────────────────────────────────────────────

def test_refresh_token_roundtrip():
    token = create_refresh_token("user-456")
    payload = decode_token(token)
    assert payload["sub"] == "user-456"
    assert payload["type"] == "refresh"


def test_verify_token_type_refresh():
    token = create_refresh_token("user-456")
    payload = verify_token_type(token, "refresh")
    assert payload["sub"] == "user-456"


def test_wrong_token_type_raises():
    access_token = create_access_token("user-789")
    with pytest.raises(AuthenticationException) as exc_info:
        verify_token_type(access_token, "refresh")
    assert "refresh" in str(exc_info.value.message)


def test_invalid_token_raises():
    with pytest.raises(AuthenticationException):
        decode_token("not.a.valid.token")


def test_tampered_token_raises():
    token = create_access_token("user-999")
    tampered = token[:-4] + "XXXX"
    with pytest.raises(AuthenticationException):
        decode_token(tampered)


# ── Sanitize ──────────────────────────────────────────────────────────────

def test_sanitize_input_strips_control_chars():
    result = sanitize_input("hello\x00world\x01")
    assert "\x00" not in result
    assert "hello" in result


def test_sanitize_input_enforces_length():
    long_str = "a" * 1000
    result = sanitize_input(long_str, max_length=100)
    assert len(result) == 100
