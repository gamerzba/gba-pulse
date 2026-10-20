"""Normalize Qt WebEngine JavaScript callback values into safe Python data."""
from __future__ import annotations
import json
from typing import Any


def _to_plain(value: Any, depth: int = 0) -> Any:
    if depth > 12:
        raise ValueError("JavaScript result is nested too deeply.")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_to_plain(item, depth + 1) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_plain(item, depth + 1) for key, item in value.items()}
    if isinstance(value, (bytes, bytearray)) or type(value).__name__ == "QByteArray":
        try:
            return bytes(value).decode("utf-8")
        except (TypeError, UnicodeDecodeError) as exc:
            raise ValueError("Qt result was not UTF-8.") from exc

    # QJsonValue/QJSValue variants expose toVariant() in some PySide builds.
    to_variant = getattr(value, "toVariant", None)
    if callable(to_variant):
        converted = to_variant()
        if converted is not value:
            return _to_plain(converted, depth + 1)
    # QJsonDocument exposes toJson() on versions which don't auto-convert it.
    to_json = getattr(value, "toJson", None)
    if callable(to_json):
        converted = to_json()
        if converted is not value:
            return _to_plain(converted, depth + 1)
    raise ValueError(f"Unsupported JavaScript result type: {type(value).__name__}")


def decode_fetch_snapshot(raw_result: Any) -> dict:
    """Decode a progressive response snapshot returned from Qt WebEngine.

    Supports the intended ``{token, responses, complete}`` envelope and older
    test/adapter representations (list of responses or a double-encoded string).
    No exception message includes any endpoint response body.
    """
    value = _to_plain(raw_result)
    for _ in range(3):
        if isinstance(value, str):
            text = value.strip()
            if not text:
                raise ValueError("Empty JavaScript result.")
            try:
                value = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError("JavaScript result was not valid JSON.") from exc
            continue
        break

    if isinstance(value, dict) and isinstance(value.get("responses"), dict):
        value = {**value, "responses": list(value["responses"].values())}
    if isinstance(value, dict) and isinstance(value.get("responses"), list):
        response_items = value["responses"]
        token = value.get("token")
        complete = bool(value.get("complete", False))
    elif isinstance(value, list):
        response_items = value
        token = None
        complete = True
    else:
        raise ValueError("JavaScript result was not an endpoint response snapshot.")

    cleaned: list[dict] = []
    for item in response_items:
        item = _to_plain(item)
        if not isinstance(item, dict) or not isinstance(item.get("key"), str):
            raise ValueError("Endpoint response entry is malformed.")
        cleaned.append(item)
    return {"token": str(token) if token is not None else None, "complete": complete, "responses": cleaned}


def decode_fetch_result(raw_result: Any) -> list[dict]:
    """Compatibility helper for complete endpoint result arrays."""
    return decode_fetch_snapshot(raw_result)["responses"]
