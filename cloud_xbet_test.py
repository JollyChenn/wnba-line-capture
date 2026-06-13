# ============================================================================
# cloud_xbet_test.py — one-off probe: does an international 1xbet mirror serve the
# WNBA feed from a GitHub (datacenter) IP? Tries plain requests + curl_cffi against
# 1x-bet.com (international) and malay.1xbet.com (the user's). Posts the verdict to
# Discord so we know whether the 1xbet capture can move to the cloud (laptop-off).
# ============================================================================
import os, json, urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
DOMAINS = ["https://1x-bet.com", "https://malay.1xbet.com"]
PATH = ("/service-api/LineFeed/Get1x2_VZip?sports=3&champs=2874802&count=10&lng=en"
        "&mode=4&country=115&getEmpty=true&virtualSports=true")

lines, win = [], False
for dom in DOMAINS:
    url = dom + PATH
    # method 1: plain requests
    try:
        import requests
        r = requests.get(url, headers={"User-Agent": UA}, timeout=25)
        wnba = "wnba" in r.text.lower()
        win = win or (r.status_code == 200 and wnba)
        lines.append(f"{dom} · requests → HTTP {r.status_code}, {len(r.text)}B, wnba={wnba}")
    except Exception as e:
        lines.append(f"{dom} · requests → ERR {str(e)[:55]}")
    # method 2: curl_cffi (chrome TLS impersonation)
    try:
        from curl_cffi import requests as creq
        r = creq.get(url, impersonate="chrome", timeout=25)
        wnba = "wnba" in r.text.lower()
        win = win or (r.status_code == 200 and wnba)
        lines.append(f"{dom} · curl_cffi → HTTP {r.status_code}, {len(r.text)}B, wnba={wnba}")
    except Exception as e:
        lines.append(f"{dom} · curl_cffi → ERR {str(e)[:55]}")

verdict = "✅ CLOUD CAPTURE POSSIBLE" if win else "❌ blocked from datacenter — stay laptop-side"
summary = f"🧪 **Cloud 1xbet test (GitHub datacenter IP)**\n{verdict}\n" + "\n".join(lines)
print(summary)
wh = os.environ.get("DISCORD_WEBHOOK", "")
if wh:
    try:
        urllib.request.urlopen(urllib.request.Request(
            wh, data=json.dumps({"content": summary[:1900]}).encode(),
            headers={"Content-Type": "application/json", "User-Agent": UA}), timeout=15)
        print("discord: posted")
    except Exception as e:
        print("discord:", e)
