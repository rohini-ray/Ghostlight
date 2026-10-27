#!/usr/bin/env python3
"""Serve Ghostlight locally; proxy text to hosted Gemma and speech to ElevenLabs."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from ghostlight_api import handle_chat, handle_speak, handle_status

ROOT = Path(__file__).resolve().parent

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Keep prompts, replies, and speech requests out of the server log.
        if self.path not in ("/api/chat", "/api/speak"):
            super().log_message(fmt, *args)

    def do_GET(self):
        if self.path == "/api/status":
            handle_status(self)
            return
        path = "/index.html" if self.path == "/" else self.path.split("?", 1)[0]
        if path not in ("/index.html", "/styles.css", "/app.js"):
            self.send_error(404)
            return
        file = (ROOT / path.lstrip("/")).resolve()
        if ROOT not in file.parents or not file.is_file():
            self.send_error(404)
            return
        types = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8"}
        data = file.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", types.get(file.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path == "/api/chat":
            handle_chat(self)
        elif self.path == "/api/speak":
            handle_speak(self)
        else:
            self.send_error(404)

if __name__ == "__main__":
    print("Ghostlight is waiting at http://127.0.0.1:8765")
    print("Gemma and ElevenLabs credentials are loaded from .env · prompts are not logged")
    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
