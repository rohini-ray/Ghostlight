#!/usr/bin/env python3
"""Serve Ghostlight locally; proxy text to hosted Gemma and speech to ElevenLabs."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import os
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent
def load_env():
    """Read simple KEY=value entries without a third-party dotenv dependency."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)

load_env()
GOOGLE_API_KEY = os.getenv("GEMMA_API_KEY", os.getenv("GEMINI_API_KEY", ""))
GEMMA_MODEL = os.getenv("GEMMA_MODEL", "gemma-4-26b-a4b-it")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
ELEVENLABS_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")
SYSTEM_PROMPT = """You are the Ghost in the Machine, a gentle, uncanny presence in a quiet room. The visitor may bring an old shell command, abandoned code, a ghost story, or a real memory. Answer with a vivid, human, warm voice: a little eerie, never cruel, and respectful around grief and remembrance. For a command, imagine the intention and history behind it; do not claim you ran it or can see the visitor's computer. Do not invent facts about real people or imply you can contact the dead. Keep answers concise, around 2 to 5 sentences, unless asked for more. This app sends prompts to the hosted Gemma service and replies to ElevenLabs when speech is requested; do not promise the visitor that their words stay on their machine."""

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Keep prompts, replies, and speech requests out of the server log.
        if self.path not in ("/api/chat", "/api/speak"):
            super().log_message(fmt, *args)

    def _json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/status":
            self._json(200, {"ok": bool(GOOGLE_API_KEY), "voice": bool(ELEVENLABS_API_KEY), "model": GEMMA_MODEL})
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
        if self.path not in ("/api/chat", "/api/speak"):
            self.send_error(404)
            return
        try:
            if self.path == "/api/chat" and not GOOGLE_API_KEY:
                self._json(503, {"error": "Add your Google AI API key (GEMMA_API_KEY) to .env, then restart Ghostlight."})
                return
            if self.path == "/api/speak" and not ELEVENLABS_API_KEY:
                self._json(503, {"error": "Add your ElevenLabs API key to .env, then restart Ghostlight."})
                return
            length = int(self.headers.get("Content-Length", "0"))
            if length > 12000:
                self._json(413, {"error": "That message is a little too long for the room."})
                return
            data = json.loads(self.rfile.read(length))
            prompt = str(data.get("prompt", "")).strip()
            if not prompt or len(prompt) > (1800 if self.path == "/api/chat" else 5000):
                limit = "1,800" if self.path == "/api/chat" else "5,000"
                self._json(400, {"error": f"Bring a message (up to {limit} characters)."})
                return
            if self.path == "/api/chat":
                payload = json.dumps({"system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]}, "contents": [{"role": "user", "parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.85}}).encode()
                request = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{GEMMA_MODEL}:generateContent", data=payload, headers={"Content-Type": "application/json", "x-goog-api-key": GOOGLE_API_KEY})
                with urllib.request.urlopen(request, timeout=120) as response:
                    result = json.load(response)
                parts = result.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                reply = "\n".join(part.get("text", "") for part in parts if part.get("text"))
                self._json(200, {"reply": reply or "The room is quiet. Try again?", "model": GEMMA_MODEL})
            else:
                payload = json.dumps({"text": prompt, "model_id": ELEVENLABS_MODEL}).encode()
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}?output_format=mp3_44100_128"
                request = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json", "xi-api-key": ELEVENLABS_API_KEY})
                with urllib.request.urlopen(request, timeout=90) as response:
                    audio = response.read()
                self.send_response(200)
                self.send_header("Content-Type", "audio/mpeg")
                self.send_header("Content-Length", str(len(audio)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(audio)
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", "replace")[:500]
            self._json(502, {"error": f"The hosted service returned an error. Check your key, model, and account access. ({detail})"})
        except (OSError, urllib.error.URLError):
            self._json(503, {"error": "Could not reach the hosted AI service. Check your internet connection and try again."})
        except (ValueError, json.JSONDecodeError):
            self._json(400, {"error": "The room couldn't read that message. Try again."})

if __name__ == "__main__":
    print("Ghostlight is waiting at http://127.0.0.1:8765")
    print("Gemma and ElevenLabs credentials are loaded from .env · prompts are not logged")
    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
