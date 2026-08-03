# board.py - serves the FULL dashboard on http://localhost:8899, always freshly built.
# Same page the cloud generates (build_dashboard.py) - drift gate + by-signal + real money +
# paper testing + filter lab - but rebuilt on every page load so tonight's cleared bets are current.
# Started hidden at logon by the WNBA-BetBoard scheduled task; also respawns hourly if it dies.
import os, sys, subprocess, http.server, socketserver, threading, time, datetime
D = os.path.dirname(os.path.abspath(__file__))
PORT = 8899
PAGE = os.path.join(D, "dashboard.html")
_last = [0.0]
_lock = threading.Lock()

def rebuild(max_age=90):
    """Re-run build_dashboard.py (which itself refreshes the drift gate) at most every max_age seconds."""
    with _lock:
        if time.time() - _last[0] < max_age:
            return
        try:
            subprocess.run([sys.executable, os.path.join(D, "build_dashboard.py")],
                           capture_output=True, cwd=D, timeout=300)
            _last[0] = time.time()
        except Exception as e:
            print("rebuild failed:", e)

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(s):
        rebuild()
        try:
            body = open(PAGE, encoding="utf-8").read()
            # keep the page live without a manual refresh
            body = body.replace("</head>", "<meta http-equiv=refresh content=120></head>", 1)
            body = body.encode("utf-8")
        except Exception:
            import traceback
            body = f"<pre style='background:#0d1020;color:#f85149'>{traceback.format_exc()}</pre>".encode()
        s.send_response(200)
        s.send_header("Content-Type", "text/html; charset=utf-8")
        s.send_header("Content-Length", str(len(body)))
        s.send_header("Cache-Control", "no-store")
        s.end_headers()
        s.wfile.write(body)
    def log_message(s, *a): pass

if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("127.0.0.1", PORT), H) as srv:
            print(f"[{datetime.datetime.now():%H:%M}] bet board -> http://localhost:{PORT}")
            srv.serve_forever()
    except OSError as e:
        print("port busy (already running?):", e)   # the hourly respawn task hits this harmlessly
