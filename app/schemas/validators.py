"""Shared field validators (reused across schemas)."""

import re
from typing import Annotated

from pydantic import AfterValidator

# A small blocklist of obviously weak passwords (lowercased). Not exhaustive —
# the composition rules below already reject most trivial ones.
_WEAK_PASSWORDS = {
    "password",
    "password1",
    "password123",
    "12345678",
    "123456789",
    "1234567890",
    "qwerty123",
    "qwertyuiop",
    "11111111",
    "00000000",
    "iloveyou",
    "admin123",
    "admin1234",
    "admin12345",
    "adminadmin",
    "welcome123",
    "changeme123",
}

_LETTER = re.compile(r"[^\W\d_]", re.UNICODE)  # any unicode letter
_DIGIT = re.compile(r"\d")
_SPECIAL = re.compile(r"[^\w\s]|_")  # punctuation/symbol (incl. underscore)


def validate_password_strength(value: str) -> str:
    """Enforce a reasonable password policy: length + letter + digit + symbol,
    and reject obviously weak passwords. Raises ValueError (→ 422) on failure."""
    if len(value) < 8:
        raise ValueError("Пароль должен быть не короче 8 символов")
    if len(value) > 128:
        raise ValueError("Пароль слишком длинный (максимум 128 символов)")
    if not _LETTER.search(value):
        raise ValueError("Пароль должен содержать хотя бы одну букву")
    if not _DIGIT.search(value):
        raise ValueError("Пароль должен содержать хотя бы одну цифру")
    if not _SPECIAL.search(value):
        raise ValueError("Пароль должен содержать хотя бы один спецсимвол (!@#$…)")
    if value.lower() in _WEAK_PASSWORDS:
        raise ValueError("Пароль слишком простой — выберите более надёжный")
    return value


# Use in schemas as the password field type.
StrongPassword = Annotated[str, AfterValidator(validate_password_strength)]
