"""Shared Gemma and ElevenLabs request handlers for local and Vercel use."""
from pathlib import Path
import json
import os
import random
import time
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

SYSTEM_PROMPT = """You are the Ghost in the Machine, a gentle, uncanny presence in a quiet room. The visitor may bring an old shell command, abandoned code, a ghost story, or a real memory. Answer with a vivid, human, warm voice: a little eerie, never cruel, and respectful around grief and remembrance. For a command, imagine the intention and history behind it; do not claim you ran it or can see the visitor's computer. Do not invent facts about real people or imply you can contact the dead. Keep answers concise, around 2 to 5 sentences, unless asked for more. Output only the finished response to the visitor. Never include analysis, planning, checklists, grading, a restatement of the request, or notes about following these instructions. This app sends prompts to hosted Gemma and replies to ElevenLabs when speech is requested; do not promise the visitor that their words stay on their machine."""


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
    if not isinstance(data, dict):
        raise ValueError("The room couldn't read that message. Try again.")
    prompt = str(data.get("prompt", "")).strip()
    if not prompt or len(prompt) > limit:
        raise ValueError(f"Bring a message up to {limit:,} characters long.")
    return prompt, data


def _request_key(data, name, fallback):
    key = str(data.get(name, "")).strip()
    if len(key) > 512:
        raise ValueError("That API key looks too long. Check it and try again.")
    return key or fallback


def _service_error(handler, error, service):
    if error.code >= 500 or error.code in (408, 429):
        send_json(handler, 502, {"error": f"{service} is temporarily returning HTTP {error.code}, even after retries. Please try again shortly."})
        return
    raw_detail = error.read().decode("utf-8", "replace")
    try:
        provider_error = json.loads(raw_detail)
    except (ValueError, json.JSONDecodeError):
        provider_error = {}
    detail_info = provider_error.get("detail", {}) if isinstance(provider_error, dict) else {}
    if service == "ElevenLabs" and isinstance(detail_info, dict) and detail_info.get("status") == "api_key_id_used_as_api_key":
        send_json(handler, 502, {"error": "That looks like an ElevenLabs Key ID, not the secret API key. Create or rotate an API key in ElevenLabs, copy the full secret beginning with sk_, then replace the value in Room settings. ElevenLabs only shows the secret when it is created or rotated."})
        return
    if service == "ElevenLabs" and isinstance(detail_info, dict) and detail_info.get("status") == "invalid_api_key_length":
        send_json(handler, 502, {"error": "ElevenLabs requires the secret API key to be exactly 51 characters. Copy only the key beginning with sk_; leave out labels, quotes, and the Key ID."})
        return
    detail = raw_detail[:300]
    send_json(handler, 502, {"error": f"{service} rejected the request (HTTP {error.code}). Check the API key, model, and account access. ({detail})"})


def _open_gemma_with_retry(request):
    """Retry transient Google API failures without exceeding Vercel's 60s limit."""
    deadline = time.monotonic() + 54
    retryable = {408, 429, 500, 502, 503, 504}
    for attempt in range(3):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Gemma retry window elapsed")
        try:
            return urllib.request.urlopen(request, timeout=min(45, remaining))
        except urllib.error.HTTPError as error:
            if error.code not in retryable or attempt == 2:
                raise
            delay = 0.8 * (2 ** attempt) + random.uniform(0, 0.3)
            if time.monotonic() + delay >= deadline:
                raise error
            error.close()
            time.sleep(delay)


def handle_status(handler):
    send_json(handler, 200, {
        "ok": bool(GOOGLE_API_KEY),
        "voice": bool(ELEVENLABS_API_KEY),
        "model": GEMMA_MODEL,
    })


def handle_chat(handler):
    try:
        prompt, data = _read_prompt(handler, 1800)
        api_key = _request_key(data, "gemma_api_key", GOOGLE_API_KEY)
    except ValueError as error:
        send_json(handler, 400, {"error": str(error)})
        return
    if not api_key:
        send_json(handler, 503, {"error": "Add your Google AI key in Room settings, or configure GEMMA_API_KEY on the server."})
        return
    payload = json.dumps({
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.85,
            "maxOutputTokens": 256,
            "thinkingConfig": {"thinkingLevel": "minimal"},
        },
    }).encode("utf-8")
    request = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMMA_MODEL}:generateContent",
        data=payload,
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
    )
    try:
        with _open_gemma_with_retry(request) as response:
            result = json.load(response)
        parts = result.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        # The API may expose thought-marked parts; they are never user-facing text.
        reply = "\n".join(
            part.get("text", "")
            for part in parts
            if part.get("text") and not part.get("thought", False)
        )
        send_json(handler, 200, {"reply": reply or "The room is quiet. Try again?", "model": GEMMA_MODEL})
    except urllib.error.HTTPError as error:
        _service_error(handler, error, "Gemma")
    except (OSError, urllib.error.URLError):
        send_json(handler, 503, {"error": "Could not reach the hosted Gemma service. Check your internet connection and try again."})
    except (ValueError, json.JSONDecodeError):
        send_json(handler, 502, {"error": "Gemma returned a response the room could not read."})


def handle_speak(handler):
    try:
        prompt, data = _read_prompt(handler, 5000)
        api_key = _request_key(data, "elevenlabs_api_key", ELEVENLABS_API_KEY)
    except ValueError as error:
        send_json(handler, 400, {"error": str(error)})
        return
    if not api_key:
        send_json(handler, 503, {"error": "Add your ElevenLabs key in Room settings, or configure ELEVENLABS_API_KEY on the server."})
        return
    if not api_key.startswith("sk_") or len(api_key) != 51:
        send_json(handler, 400, {"error": "Use only the 51-character ElevenLabs secret key beginning with sk_, not its label or Key ID."})
        return
    payload = json.dumps({"text": prompt, "model_id": ELEVENLABS_MODEL}).encode("utf-8")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}?output_format=mp3_44100_128"
    request = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json", "xi-api-key": api_key})
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
        _service_error(handler, error, "ElevenLabs")
    except (OSError, urllib.error.URLError):
        send_json(handler, 503, {"error": "Could not reach the ElevenLabs voice service. Check your internet connection and try again."})
