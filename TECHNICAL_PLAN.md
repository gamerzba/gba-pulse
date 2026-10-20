# G.ba Pulse — technical plan

## Product behavior

- Windows 10/11, Python + PySide6 / Qt WebEngine.
- Fixed 392×690 frameless panel, draggable from its title bar.
- Compact 84-logical-pixel points/messages cards, with freed vertical space assigned to the RSS viewport.
- Hide action replaces the panel with a small clickable logo window. No `WindowStaysOnTopHint`: other windows may cover it.
- Theme: background `#060911`, orange `#fb9524`, secondary lime `#8cbf2b`, cool slate neutrals.
- Panel contents: points counter, private-message counter, live online-member count, RSS topics, quick links, connection status, last-refresh time.
- Polling defaults to 60 seconds, configurable to 30 or 300 seconds.
- Windows startup is optional and off by default.
- Links open in the default browser; no embedded thread reader is planned.

## Components

```text
main.py                         Qt startup / WebEngine profile
build_windows.bat               Windows PyInstaller build
gba_pulse/
  config.py                     official URLs and visual constants
  paths.py                      dev/build asset paths
  services/
    forum_session.py            async polling in Gamerz.ba origin
    fetch_script.py             JS fetch batch, browser-profile cookies
    response_processor.py       response -> safe view model
    api_payload.py              path lookup and value-free schema inspection
    feed_parser.py              RSS/RDF/Atom parsing and URL validation
    online_parser.py            visible homepage anchor parser
    autostart.py                opt-in HKCU Run registry value
  ui/
    main_window.py               panel, metrics, RSS rows, hide-logo window
    login_dialog.py              embedded session login
    settings_dialog.py           interval, startup, schema path, diagnostics
    logo_loader.py               official SVG loader + fallback
    theme.py                     QSS palette
assets/
  gba_pulse_mark.svg             vector local fallback mark
  gba_pulse_mark.ico             Windows application icon
 tests/                          pure tests using mock responses
```

## Session and request handling

1. A named `QWebEngineProfile` uses a persistent app-specific storage/cache directory under Windows application data.
2. The user signs into Gamerz.ba in a QtWebEngine view using that profile. We do not read cookies from the user's main browser.
3. Requests execute asynchronously through JavaScript `fetch(..., credentials: 'include')` on the same site origin, so the browser profile handles session cookies.
4. Each endpoint publishes into a tokenized progressive response map as soon as it finishes. RSS and the online count can appear while a personalized API endpoint is still retrying or timing out.
5. The UI is never blocked by synchronous network calls. There is a 12-second per-request abort, a 14.5-second per-endpoint watchdog, an 18-second homepage-load watchdog, and a 20-second batch watchdog. Poll batches do not overlap.
5. Only derived counters, sanitized RSS items and *field names/types* for diagnostics reach the UI. Raw API bodies are not persisted or logged.
6. A 401/403, redirect to another page, timeout, malformed XML/JSON, or missing number produces an unavailable/diagnostic state, not a fabricated value.

## Endpoint inventory

| Purpose | URL provided by user | Status |
|---|---|---|
| Homepage and visible online label | `https://www.gamerz.ba/` | HTML parser built; validate on Windows/live session |
| RSS | `https://www.gamerz.ba/rss` | Generic RSS/Atom XML parser built; validate live feed |
| Logo | `https://www.gamerz.ba/assets/v5/images/logo-mark-mRsiQoL.svg` | Runtime download with fallback |
| Messages | `https://www.gamerz.ba/api/poruke/broj/` | `unread` -> message count; `notifications` -> secondary badge, based on user-provided sample |
| Points | `https://www.gamerz.ba/api/bodovi/promjena/` | `balance` -> points balance; `notifications` is a fallback source, based on user-provided sample |

A separate notifications-count endpoint was not supplied. The app does not invent one or silently treat message counts as notification counts.

## API schema policy

The user supplied representative JSON fields, so defaults are `balance` for points, `unread` for messages, and `notifications` for the secondary notification detail. These paths remain configurable in Settings. The field `last` is not surfaced because its semantic meaning is unknown.

During development the external inspection service returned HTTP 403 for the two API URLs, so the authenticated payload was not visible from this environment. The user then provided representative sample schemas that are now mapped. A logged-in Windows runtime test is still required to verify the live responses.

## Local storage / security posture

- QSettings stores UI settings, refresh interval, startup flag and explicitly configured JSON paths.
- WebEngine keeps the app's own site cookies in its profile storage. The app doesn't expose or log cookie strings.
- Clear-session deletes the app profile's cookies and HTTP cache; it does not touch other browser profiles.
- API diagnostic summaries include field names and types only. Raw response bodies are discarded after parsing.
- The app does not save online/homepage data as an offline cache in this version; the chosen behavior is empty/unavailable states when requests fail.
- RSS links are accepted as clickable only if they resolve to `gamerz.ba` or a subdomain.

## Validation

Pure RSS/Atom parsing, visible online anchor parsing, API numeric-path extraction, unknown-schema behavior, redirect/403 handling, and mock response aggregation are unit tested. Qt runtime, account login, current server response schema, logo network loading and Windows packaging need to be tested on Windows; the development container lacks PySide6 and cannot launch that UI.
