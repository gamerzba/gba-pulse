"""Progressive same-origin endpoint requests inside the embedded forum session."""
import json
from gba_pulse.config import FORUM_URL, MESSAGES_URL, POINTS_URL, RSS_URL, MAX_RESPONSE_BYTES


def build_fetch_script() -> str:
    endpoints = {
        "messages": MESSAGES_URL,
        "points": POINTS_URL,
        "rss": RSS_URL,
        "home": FORUM_URL,
    }
    endpoints_json = json.dumps(endpoints, ensure_ascii=False)
    max_chars = MAX_RESPONSE_BYTES
    # Entire code runs inside an IIFE to avoid leaking lexical const/let names
    # into the page's global scope after repeated manual refreshes.
    return f"""(() => {{
      const endpoints = {endpoints_json};
      const maxChars = {max_chars};
      const batchId = String(Date.now()) + '-' + Math.random().toString(36).slice(2);
      window.__gbaPulseBatchId = batchId;
      window.__gbaPulseResponse = {{}};
      window.__gbaPulseDone = false;

      const getOne = async ([key, url]) => {{
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 12000);
        try {{
          const response = await fetch(url, {{
            credentials: 'include',
            cache: 'no-store',
            redirect: 'follow',
            signal: controller.signal,
            headers: {{ 'Accept': key === 'rss' ? 'application/rss+xml, application/atom+xml, application/xml, text/xml, */*' : 'application/json, text/plain, */*' }}
          }});
          const text = await response.text();
          const bodyLimit = key === 'rss' ? Math.max(maxChars, 500000) : maxChars;
          return {{ key, requestedUrl: url, status: response.status, ok: response.ok,
            url: response.url, redirected: response.redirected,
            contentType: response.headers.get('content-type') || '',
            body: text.slice(0, bodyLimit), truncated: text.length > bodyLimit }};
        }} catch (error) {{
          return {{ key, requestedUrl: url, status: 0, ok: false, url, redirected: false,
            contentType: '', body: '',
            error: String(error && error.name === 'AbortError' ? 'timeout' : 'network'), truncated: false }};
        }} finally {{ clearTimeout(timer); }}
      }};

      // A single endpoint that stalls cannot block RSS or the online counter.
      const safeGetOne = async pair => {{
        const key = pair[0], url = pair[1];
        let watchdog = null;
        const timeoutResult = () => ({{ key, requestedUrl: url, status: 0, ok: false, url,
          redirected: false, contentType: '', body: '', error: 'timeout', truncated: false }});
        try {{
          const result = await Promise.race([
            getOne(pair),
            new Promise(resolve => {{ watchdog = setTimeout(() => resolve(timeoutResult()), 14500); }})
          ]);
          if (window.__gbaPulseBatchId === batchId) {{
            window.__gbaPulseResponse[result.key] = result;
          }}
          return result;
        }} finally {{ if (watchdog !== null) clearTimeout(watchdog); }}
      }};

      Promise.all(Object.entries(endpoints).map(safeGetOne)).then(() => {{
        if (window.__gbaPulseBatchId === batchId) window.__gbaPulseDone = true;
      }}).catch(() => {{
        if (window.__gbaPulseBatchId === batchId) window.__gbaPulseDone = true;
      }});
      return batchId;
    }})();"""
