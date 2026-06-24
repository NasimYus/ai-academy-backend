"""Locale resolution for translatable content (F.4).

Fallback chain for each field: requested locale → default locale → the base
column on the main row. `obj.translations` must be eager-loaded by the caller.
"""

from app.core.config import settings


def localize(obj, locale: str, default_locale: str, *fields: str) -> dict[str, str | None]:
    """Return {field: localized value} for `obj`, applying the fallback chain."""
    rows = {t.locale: t for t in obj.translations}
    out: dict[str, str | None] = {}
    for field in fields:
        value = None
        for loc in (locale, default_locale):
            row = rows.get(loc)
            if row is not None and getattr(row, field, None):
                value = getattr(row, field)
                break
        out[field] = value if value is not None else getattr(obj, field, None)
    return out


def resolve_locale(raw: str | None) -> str:
    """Normalize a requested locale (?locale= or Accept-Language) to a 2-letter
    code, falling back to the configured default."""
    if not raw:
        return settings.default_locale
    # Take the first language tag, strip region (e.g. "ru-RU,en;q=0.9" -> "ru").
    first = raw.split(",")[0].strip()
    code = first.split("-")[0].split(";")[0].strip().lower()
    return code or settings.default_locale
