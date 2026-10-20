# G.ba Pulse

**Source update: v0.1.2 — result-decoding and request-timeout fix**

A small Windows desktop companion for Gamerz.ba, built with Python and PySide6. The visual direction uses the requested near-black background (`#060911`), orange accent (`#fb9524`), and restrained lime detail (`#8cbf2b`).

## Current implementation status

- Frameless, fixed-size panel that can be dragged by its header.
- Eye-style hide control switches to a small clickable logo window. The logo is **not** configured to stay above other applications, so other windows can cover it.
- The panel reads the official logo-mark SVG from the supplied Gamerz.ba URL at runtime; the app has a local fallback mark if the download fails.
- The RSS parser supports RSS 2.0, RDF/RSS and Atom. Feed items are limited to Gamerz.ba links so a feed item cannot launch an arbitrary external host.
- The current online-member count is read from visible `Online (N)`/`Online N` anchor text on the public homepage. If the site's markup changes, it safely falls back to unavailable.
- The two user-provided API endpoints are called asynchronously in a persistent embedded Gamerz.ba session. No cookie is read from Chrome/Edge, copied into a config file, or written to logs.
- Confirmed API field mappings use `balance` for the points balance and `unread` for unread private messages. The `notifications` field is shown as a small secondary detail under the messages count. Explicit JSON paths remain configurable in Settings. Unknown fields such as `last` are not treated as counters because their semantics have not been confirmed.
- Settings include 30/60/300-second polling, opt-in Windows logon startup (default off), API JSON-path mapping, and clearing the app's own login cookies.
- Offline requests show unavailable states rather than pretending stale data is current.

## Requirements

- Windows 10/11
- Python 3.11+ recommended
- Internet access to install packages and access Gamerz.ba

Install and run from PowerShell in this folder:

```powershell
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py
```

Use `build_windows.bat` to make a PyInstaller one-folder build. The output is expected at `dist\GbaPulse\GbaPulse.exe`.

## First launch

1. Open G.ba Pulse.
2. Click **PRIJAVA** and sign into Gamerz.ba in the built-in session window.
3. Click **Gotovo — provjeri sesiju**, then refresh the panel.
4. On refresh, points should read from `balance`, unread messages from `unread`, and the secondary message detail from `notifications`.
5. If your account's API payload differs, open **Settings → API Diagnostics** to inspect HTTP status and a value-free JSON shape, then adjust the paths if needed.

## Known API integration limitation

The site endpoints supplied for messages and points returned HTTP 403 through the external inspection environment used during development. The user subsequently supplied representative JSON payloads, so the app maps `balance` to points, `unread` to unread messages, and `notifications` to the secondary notifications detail. The live endpoint behavior still needs a Windows runtime test from the user's logged-in session. The provided message endpoint is `/api/poruke/broj/`; no distinct notifications-count endpoint was supplied, so a separate notification counter is not fabricated.

The RSS response is expected to be XML and is parsed at runtime; an external browsing tool could not render its XML content directly. The browser login/session and live RSS also require a Windows runtime test.

## Local files and privacy

Settings use Qt `QSettings`; the WebEngine profile (including its session cookie store) is held under the current user's application-data directory. The app never imports a cookie from another browser. Use **Settings → Odjavi / očisti sesiju** to remove cookies for the app's own profile. Do not share application-data/profile directories if you intend to keep the account session private.

Raw API bodies are not saved to files and are not included in schema diagnostics. RSS titles and summaries are shown from the public feed. The public homepage's visible online label is parsed but not persisted.

## v0.1.2 reliability fix

- Reads JS callback output robustly across Qt result representations (JSON string, Python list/dict, Qt JSON wrappers).
- Adds per-endpoint watchdogs and a 20-second batch timeout.
- On page-load, decode, or request timeout failures, refreshes all tiles into an explicit unavailable state and replaces the infinite `RSS se još učitava…` placeholder.
- The global JS result is stored as structured data and stringified by the callback expression, which keeps the return type stable for Qt WebEngine.
- RSS responses are allowed a larger bounded body than the HTML/API endpoints to avoid truncating ordinary feeds.

## Tests

Run the pure parser/response-processing tests (these do not require Qt):

```powershell
python -m unittest discover -s tests -v
```

The suite uses mock RSS/HTML/JSON responses, including the example Gamerz.ba payload fields provided by the user. It does not prove that the live API endpoints, login flow, Qt WebEngine behavior, or Windows executable work; those require testing on Windows with an actual forum account.
