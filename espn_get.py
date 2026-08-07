# espn_get.py - ONE hardened way to call ESPN, after two silent outages in 3 days:
#   2026-08-06a: ESPN began 403-ing requests that send only a User-Agent  -> added browser headers.
#   2026-08-06b: ESPN also FINGERPRINTS THE TLS CLIENT - python `requests` is 403'd even with perfect
#                headers, while curl_cffi (Chrome impersonation) and urllib both pass.
# Strategy: curl_cffi impersonating Chrome first (most browser-like), urllib with full browser headers
# as fallback. Both outages would have been prevented by this. Import and use `get()` / `getj()`.
import json, urllib.request
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
     "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.9",
     "Referer": "https://www.espn.com/wnba/scoreboard", "Origin": "https://www.espn.com"}

def getj(url, params=None, timeout=20):
    """ESPN JSON with automatic client fallback. Returns {} on total failure (never raises)."""
    if params:
        url += ("&" if "?" in url else "?") + "&".join(f"{k}={v}" for k, v in params.items())
    try:                                        # 1) curl_cffi = real Chrome TLS fingerprint
        from curl_cffi import requests as creq
        r = creq.get(url, headers=H, timeout=timeout, impersonate="chrome")
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    try:                                        # 2) urllib + full browser headers
        return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=timeout))
    except Exception:
        return {}

def alive():
    """True if ESPN is reachable right now - used by the watchdog."""
    return bool(getj("https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard").get("events") is not None)
