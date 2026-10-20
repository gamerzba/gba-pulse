# G.ba Pulse v0.1.2 test report

## Automated checks

- **35/35 unit tests passed** using Python `unittest` in the build environment.
- Covers RSS/Atom parsing, Gamerz.ba URL rules, explicit API mapping (`balance`, `unread`, `notifications`), online-count parsing, JavaScript-result decoding as JSON string/list/dict/double-encoded JSON, progressive response snapshots and batch tokens, malformed-result handling, redirect safety, and 403/unknown schema states.
- Python source files passed compile checks.
- Generated fetch JavaScript passed `node --check`.

## Reliability fixes in v0.1.2

1. Normalize Qt WebEngine callback values instead of assuming they are always Python strings.
2. Store progressive JS results as a per-endpoint object, then serialize a stable snapshot for Python.
3. Publish RSS/home results as each endpoint finishes; a stalled personalized API can no longer hold the whole dashboard.
4. Add a token to each poll batch and ignore stale callbacks after a timeout/retry.
5. Add an 18-second homepage load watchdog, 12-second request abort, 14.5-second per-endpoint watchdog, and 20-second batch watchdog.
6. On page-load, response-decode, and request-timeout failures, publish an explicit unavailable dashboard model so the UI cannot remain forever at “Čeka podatke” / “RSS se još učitava…”.
7. Surface a value-free result-type/parser-class diagnostic in Settings.
8. Use a larger bounded body limit for RSS than for API/HTML payloads to reduce valid-feed truncation.

## Not covered here

- Qt WebEngine GUI runtime and visual layout;
- live login/session behavior on a Windows machine;
- live Gamerz.ba API responses in the user's session;
- building or launching the Windows executable.

PySide6/QtWebEngine is not installed in this build environment, so these items are not claimed as passed. Tests use mock payloads and validate parser/state logic; they do not guarantee live-site availability.
