# Gamerz.ba endpoint integration state

## v0.1.2 fetch reliability

Each endpoint now publishes independently, so a slow messages/points endpoint cannot prevent RSS or online status from appearing. Qt WebEngine callback results are normalized; batch and page-load watchdogs ensure the UI leaves the loading state after a failure. Diagnostics show only safe error classes and JSON key/type structure.

The following URLs are used exactly as supplied:

- `https://www.gamerz.ba/api/poruke/broj/`
- `https://www.gamerz.ba/api/bodovi/promjena/`
- `https://www.gamerz.ba/rss`
- Homepage: `https://www.gamerz.ba/`
- Logo: `https://www.gamerz.ba/assets/v5/images/logo-mark-mRsiQoL.svg`

## What is implemented

- All three page/API resources are requested on the Gamerz.ba origin with browser-profile credentials.
- HTTP status, content type, redirect state and timeouts are handled.
- RSS XML parsing and public-homepage online-anchor parsing are implemented.
- Points map to `balance`; unread messages map to `unread`; `notifications` is shown as a secondary detail (messages endpoint first, points endpoint as fallback).
- Raw numeric endpoint responses remain supported, while configurable JSON paths can override the confirmed defaults.
- 401, 403, login redirects, malformed responses and unknown response schemas do not produce fake counts.

## What still needs a real authenticated response

The confirmed response shapes used by the app are:

- Points: `{"balance": <number>, "last": <unknown>, "gained": <number>, "lost": <number>, "notifications": <number>}`
- Messages: `{"unread": <number>, "notifications": <number>}`

The app maps `balance`, `unread`, and `notifications` accordingly. It deliberately does not assign meaning to `last`, `gained`, or `lost` in the compact dashboard beyond not displaying them. Unit tests use synthetic values, not a live account snapshot. The window/UI still requires a Windows runtime test using a logged-in session to verify these representative schemas match current live responses. The homepage/online number is scraped from the visible link label rather than a guessed API endpoint. No separate notification endpoint was supplied, so only the known message-count endpoint is represented.
