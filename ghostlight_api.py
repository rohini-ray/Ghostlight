"""Shared Gemma and ElevenLabs request handlers for local and Vercel use."""
from pathlib import Path
import json
import os
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent


def _load_env():
    """Load the local .env file when present; Vercel supplies real env vars."""
    env_file = ROOT / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env()
GOOGLE_API_KEY = os.getenv("GEMMA_API_KEY", os.getenv("GEMINI_API_KEY", ""))
GEMMA_MODEL = os.getenv("GEMMA_MODEL", "gemma-4-26b-a4b-it")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
ELEVENLABS_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")

SYSTEM_PROMPT = """You are the Ghost in the Machine, a gentle, uncanny presence in a quiet room. The visitor may bring an old shell command, abandoned code, a ghost story, or a real memory. Answer with a vivid, human, warm voice: a little eerie, never cruel, and respectful around grief and remembrance. For a command, imagine the intention and history behind it; do not claim you ran it or can see the visitor's computer. Do not invent facts about real people or imply you can contact the dead. Keep answers concise, around 2 to 5 sentences, unless asked for more. This app sends prompts to hosted Gemma and replies to ElevenLabs when speech is requested; do not promise the visitor that their words stay on their machine."""


def send_json(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def _read_prompt(handler, limit):
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except ValueError:
        raise ValueError("The room couldn't read that message. Try again.")
    if length <= 0 or length > 12000:
        raise ValueError("That message is empty or too long for the room.")
    try:
        data = json.loads(handler.rfile.read(length))
    except (ValueError, json.JSONDecodeError):
        raise ValueError("The room couldn't read that message. Try again.")
    prompt = str(data.get("prompt", "")).strip()
    if not prompt or len(prompt) > limit:
        raise ValueError(f"Bring a message up to {limit:,} characters long.")
    return prompt


def _service_error(handler, error):
    detail = error.read().decode("utf-8", "replace")[:300]
    send_json(handler, 502, {"error": f"The hosted service returned an error. Check your key, model, and account access. ({detail})"})


def handle_status(handler):
    send_json(handler, 200, {
        "ok": bool(GOOGLE_API_KEY),
        "voice": bool(ELEVENLABS_API_KEY),
        "model": GEMMA_MODEL,
    })


def handle_chat(handler):
    if not GOOGLE_API_KEY:
        send_json(handler, 503, {"error": "Configure GEMMA_API_KEY in .env or your Vercel environment variables, then restart or redeploy Ghostlight."})
        return
    try:
        prompt = _read_prompt(handler, 1800)
    except ValueError as error:
        send_json(handler, 400, {"error": str(error)})
        return
    payload = json.dumps({
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.85, "maxOutputTokens": 256},
    }).encode("utf-8")
    request = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMMA_MODEL}:generateContent",
        data=payload,
        headers={"Content-Type": "application/json", "x-goog-api-key": GOOGLE_API_KEY},
    )
    try:
        with urllib.request.urlopen(request, timeout=55) as response:
            result = json.load(response)
        parts = result.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        reply = "\n".join(part.get("text", "") for part in parts if part.get("text"))
        send_json(handler, 200, {"reply": reply or "The room is quiet. Try again?", "model": GEMMA_MODEL})
    except urllib.error.HTTPError as error:
        _service_error(handler, error)
    except (OSError, urllib.error.URLError):
        send_json(handler, 503, {"error": "Could not reach the hosted Gemma service. Check your internet connection and try again."})
    except (ValueError, json.JSONDecodeError):
        send_json(handler, 502, {"error": "Gemma returned a response the room could not read."})


def handle_speak(handler):
    if not ELEVENLABS_API_KEY:
        send_json(handler, 503, {"error": "Configure ELEVENLABS_API_KEY in .env or your Vercel environment variables, then restart or redeploy Ghostlight."})
        return
    try:
        prompt = _read_prompt(handler, 5000)
    except ValueError as error:
        send_json(handler, 400, {"error": str(error)})
        return
    payload = json.dumps({"text": prompt, "model_id": ELEVENLABS_MODEL}).encode("utf-8")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}?output_format=mp3_44100_128"
    request = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json", "xi-api-key": ELEVENLABS_API_KEY})
    try:
        with urllib.request.urlopen(request, timeout=55) as response:
            audio = response.read()
        handler.send_response(200)
        handler.send_header("Content-Type", "audio/mpeg")
        handler.send_header("Content-Length", str(len(audio)))
        handler.send_header("Cache-Control", "no-store")
        handler.end_headers()
        handler.wfile.write(audio)
    except urllib.error.HTTPError as error:
        _service_error(handler, error)
    except (OSError, urllib.error.URLError):
        send_json(handler, 503, {"error": "Could not reach the ElevenLabs voice service. Check your internet connection and try again."})
