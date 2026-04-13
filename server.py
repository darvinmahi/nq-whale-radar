#!/usr/bin/env python3
"""
server.py — NQ Whale Radar Local Server
Sirve archivos estáticos Y proxea Yahoo Finance para evitar CORS.
Uso: python server.py
     Abre: http://127.0.0.1:5501/daily_dashboard.html
"""
import http.server, socketserver, urllib.request, urllib.error, json, os, sys

PORT = 5501
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

YAHOO_ENDPOINTS = {
    '/api/nq5m': 'https://query1.finance.yahoo.com/v8/finance/chart/NQ=F?interval=5m&range=2d&includePrePost=true',
    '/api/nq1m': 'https://query1.finance.yahoo.com/v8/finance/chart/NQ=F?interval=1m&range=1d&includePrePost=true',
    '/api/nq15m': 'https://query1.finance.yahoo.com/v8/finance/chart/NQ=F?interval=15m&range=5d',
}

HEADERS_OUT = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Content-Type': 'application/json',
    'Cache-Control': 'no-cache',
}

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        path = self.path.split('?')[0]

        # ── Proxy requests ────────────────────────────────────────
        if path in YAHOO_ENDPOINTS:
            url = YAHOO_ENDPOINTS[path]
            try:
                req = urllib.request.Request(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json',
                })
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = resp.read()
                self.send_response(200)
                for k, v in HEADERS_OUT.items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self.send_response(502)
                for k, v in HEADERS_OUT.items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
            return

        # ── Static files ──────────────────────────────────────────
        return super().do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        for k, v in HEADERS_OUT.items():
            self.send_header(k, v)
        self.end_headers()

    def log_message(self, fmt, *args):
        # Suppress static file noise, only log API calls
        if '/api/' in (args[0] if args else ''):
            print(f"[API] {args[0]} → {args[1]}")

if __name__ == '__main__':
    os.chdir(BASE_DIR)
    with socketserver.TCPServer(('127.0.0.1', PORT), Handler) as httpd:
        httpd.allow_reuse_address = True
        print(f"\n🐋 NQ Whale Radar Server")
        print(f"   http://127.0.0.1:{PORT}/daily_dashboard.html")
        print(f"   Proxy: /api/nq5m  /api/nq1m  /api/nq15m")
        print(f"   Ctrl+C para detener\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\nServidor detenido.")
