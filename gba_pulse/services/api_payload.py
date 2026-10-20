"""Safe helpers for extracting numeric counters from forum JSON payloads.

Field paths are configured explicitly by the response processor/settings. The
module does not infer semantic meaning from arbitrary keys and never returns
payload values in schema diagnostics.
"""
from __future__ import annotations

import json
import re
from typing import Any

_NUMERIC_TEXT = re.compile(r"^[+-]?\d+(?:\.\d+)?$")


def parse_json_body(body: str) -> Any | None:
    try:
        return json.loads(body)
    except (json.JSONDecodeError, TypeError):
        stripped = (body or "").strip()
        if stripped and _NUMERIC_TEXT.fullmatch(stripped):
            try:
                number = float(stripped)
                return int(number) if number.is_integer() else number
            except ValueError:
                return None
        return None


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    return type(value).__name__


def summarize_shape(value: Any, depth: int = 0, max_depth: int = 4) -> str:
    """Describe keys and types only; never include payload values."""
    if depth >= max_depth:
        return _type_name(value)
    if isinstance(value, dict):
        if not value:
            return "object {}"
        parts = []
        for index, (key, member) in enumerate(value.items()):
            if index >= 24:
                parts.append("…")
                break
            safe_key = re.sub(r"[^\w .:-]", "?", str(key))[:60]
            parts.append(f"{safe_key}: {summarize_shape(member, depth + 1, max_depth)}")
        return "object {" + ", ".join(parts) + "}"
    if isinstance(value, list):
        if not value:
            return "array []"
        return "array[" + summarize_shape(value[0], depth + 1, max_depth) + "]"
    return _type_name(value)


def value_at_path(value: Any, path: str) -> Any:
    """Resolve a deliberately simple path: key.nested_key[0].field.

    Empty path means root. Array indexes are supported. No expression evaluation
    or arbitrary code is permitted.
    """
    if not path.strip():
        return value
    tokens = re.findall(r"([^.[\]]+)|\[(\d+)\]", path.strip())
    if not tokens:
        raise ValueError("Neispravna putanja.")
    current = value
    for key, index in tokens:
        if index:
            if not isinstance(current, list):
                raise ValueError("Putanja očekuje listu.")
            i = int(index)
            if i >= len(current):
                raise ValueError("Indeks je izvan liste.")
            current = current[i]
        else:
            if not isinstance(current, dict) or key not in current:
                raise ValueError("Polje nije pronađeno u odgovoru.")
            current = current[key]
    return current


def extract_numeric_value(body: str, path: str = "") -> tuple[int | float | None, str]:
    """Return a numeric value only if root/path explicitly resolves to a number.

    The second return value is a value-free structural summary suitable for UI
    diagnostics. Booleans and numeric-looking arbitrary strings are rejected.
    """
    value = parse_json_body(body)
    if value is None:
        stripped = (body or "").strip()
        if stripped and _NUMERIC_TEXT.fullmatch(stripped):
            raw: Any = float(stripped)
            value = int(raw) if raw.is_integer() else raw
        else:
            return None, "Odgovor nije prepoznat kao JSON/broj; vrijednosti nisu prikazane."
    shape = summarize_shape(value)
    try:
        resolved = value_at_path(value, path)
    except ValueError as exc:
        return None, f"{shape}\nPutanja nije riješena: {exc}"
    if isinstance(resolved, bool) or not isinstance(resolved, (int, float)):
        return None, f"{shape}\nOdabrano polje nije broj."
    if isinstance(resolved, float) and not resolved.is_integer():
        return resolved, shape
    return int(resolved), shape
