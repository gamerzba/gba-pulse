"""Pure response-to-dashboard transformation, separately testable with fixtures."""
from __future__ import annotations
from datetime import datetime
from urllib.parse import urlparse

from gba_pulse.config import MAX_FEED_ITEMS, RSS_URL
from gba_pulse.services.api_payload import extract_numeric_value, parse_json_body
from gba_pulse.services.feed_parser import parse_feed
from gba_pulse.services.online_parser import parse_online_count


def _trusted_gamerz_url(value: str) -> bool:
    parsed = urlparse(value or "")
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and host in {"gamerz.ba", "www.gamerz.ba"}


def _redirect_stayed_on_endpoint(response: dict) -> bool:
    if not response.get("redirected"):
        return True
    requested = urlparse(response.get("requestedUrl", ""))
    final = urlparse(response.get("url", ""))
    if not _trusted_gamerz_url(response.get("url", "")):
        return False
    # Accept slash-only canonical redirects, but not a redirect from an API to
    # another page (e.g. an unexpected login page or homepage).
    return requested.path.rstrip("/") == final.path.rstrip("/") and requested.path != ""


def endpoint_status(response: dict | None) -> str:
    if not response:
        return "Odgovor nije dostupan"
    status = response.get("status", 0)
    if status in (401, 403):
        return f"Sesija nema pristup ({status})"
    if response.get("error") == "timeout":
        return "Isteklo vrijeme zahtjeva"
    if response.get("error"):
        return "Mrežna greška"
    if status < 200 or status >= 300:
        return f"HTTP {status}"
    if response.get("redirected"):
        return "Odgovor preusmjeren"
    return "Odgovor primljen"


def _parse_count_endpoint(response: dict | None, path: str) -> dict:
    result = {
        "value": None,
        "status": endpoint_status(response),
        "schema": "Nema odgovora",
        "content_type": "",
    }
    if not response:
        return result
    result["content_type"] = response.get("contentType", "") or ""
    status = response.get("status", 0)
    if status < 200 or status >= 300 or not _trusted_gamerz_url(response.get("url", "")):
        return result
    if not _redirect_stayed_on_endpoint(response):
        result["status"] = "Preusmjeren odgovor; provjeri prijavu"
        result["schema"] = "Odgovor nije korišten jer je endpoint preusmjeren na drugu putanju."
        return result
    body = response.get("body", "")
    content_type = result["content_type"].lower()
    if "html" in content_type and "json" not in content_type:
        result["schema"] = "Odgovor izgleda kao HTML, ne kao API JSON. Provjeri sesiju ili endpoint."
        result["status"] = "HTML odgovor; provjeri sesiju"
        return result
    value, schema = extract_numeric_value(body, path)
    parsed = parse_json_body(body)
    # Keep compatibility with an endpoint that returns a raw numeric body
    # instead of an object with the confirmed default field.
    if value is None and isinstance(parsed, (int, float)) and not isinstance(parsed, bool):
        value, schema = extract_numeric_value(body, "")
    result["schema"] = schema
    result["value"] = value
    if value is not None:
        result["status"] = "Ažurirano"
    else:
        if parsed is None:
            result["status"] = "Odgovor nije prepoznat kao JSON/broj"
        elif isinstance(parsed, (dict, list)):
            result["status"] = "Format primljen; potrebno mapirati polje"
        else:
            result["status"] = "Broj nije pronađen na zadanoj putanji"
    return result


def process_responses(responses: dict[str, dict], paths: dict[str, str] | None = None, now: datetime | None = None) -> dict:
    """Process one fixture/live response batch without persisting raw body values."""
    paths = paths or {}
    # Confirmed Gamerz.ba response fields supplied by the user:
    # points => balance; messages => unread. Explicit settings still override these defaults.
    points_path = str(paths.get("points") or "balance").strip()
    messages_path = str(paths.get("messages") or "unread").strip()
    messages_response = responses.get("messages")
    points_response = responses.get("points")
    messages = _parse_count_endpoint(messages_response, messages_path)
    points = _parse_count_endpoint(points_response, points_path)

    # Both supplied payloads contain `notifications`. Prefer the messages endpoint,
    # falling back to the points response only if that response has no numeric value.
    notifications = _parse_count_endpoint(messages_response, "notifications")
    if notifications["value"] is None:
        notifications = _parse_count_endpoint(points_response, "notifications")

    rss_response = responses.get("rss") or {}
    rss_items = []
    rss_status = endpoint_status(rss_response)
    if 200 <= rss_response.get("status", 0) < 300 and _trusted_gamerz_url(rss_response.get("url", "")) and _redirect_stayed_on_endpoint(rss_response):
        rss_items = parse_feed(rss_response.get("body", ""), RSS_URL, MAX_FEED_ITEMS)
        rss_status = "Ažurirano" if rss_items else "RSS primljen, ali XML format nije prepoznat ili nema stavki"

    home_response = responses.get("home") or {}
    online_count = None
    online_status = endpoint_status(home_response)
    if 200 <= home_response.get("status", 0) < 300 and _trusted_gamerz_url(home_response.get("url", "")) and _redirect_stayed_on_endpoint(home_response):
        online_count = parse_online_count(home_response.get("body", ""))
        online_status = "Ažurirano" if online_count is not None else "Broj članova nije pronađen na stranici"

    successful = sum(
        1 for response in responses.values()
        if 200 <= response.get("status", 0) < 300 and _trusted_gamerz_url(response.get("url", "")) and _redirect_stayed_on_endpoint(response)
    )
    if messages["value"] is not None and points["value"] is not None and successful >= 3:
        connection_state = "ok"
    elif successful:
        connection_state = "warning"
    else:
        connection_state = "error"

    checked = (now or datetime.now().astimezone()).strftime("%H:%M:%S")
    return {
        "points": points,
        "messages": messages,
        "notifications": notifications,
        "rss_items": rss_items,
        "rss_status": rss_status,
        "online_count": online_count,
        "online_status": online_status,
        "endpoint_statuses": {key: endpoint_status(response) for key, response in responses.items()},
        "checked_at": checked,
        "connection_state": connection_state,
    }
