# Ghostlight — a séance for the machine

A spooky writing companion for old commands, ghost stories, and memories worth keeping. Hosted Gemma gives the ghost its words; ElevenLabs can read its reply aloud.

## Set up your keys

1. Install Python 3.
2. Open the `.env` file beside `server.py` and add your keys:

   ```env
   GEMMA_API_KEY=your_google_ai_api_key
   ELEVENLABS_API_KEY=your_elevenlabs_api_key
   ```

   Get a Google AI API key from [Google AI Studio](https://aistudio.google.com/apikey) for hosted Gemma, and an ElevenLabs key from [ElevenLabs API keys](https://elevenlabs.io/app/settings/api-keys). The `.env` file is excluded from Git.

3. Optional settings in `.env` let you pick the Gemma model, ElevenLabs voice ID, and speech model. The default model is `gemma-4-26b-a4b-it`; the default voice ID is `JBFqnCBsd6RMkjVDRZzb`.
4. Start the server:

   ```sh
   python server.py
   ```

5. Visit [http://127.0.0.1:8765](http://127.0.0.1:8765), send a prompt, then press **Listen** on a reply to generate speech.

Restart the server after changing `.env`. The keys stay on the local Python server and are never sent to the browser. Prompts are sent to hosted Gemma through Google's API to generate replies; reply text is sent to ElevenLabs only when **Listen** is selected. Both are hosted services and may retain or process data under their own terms. API usage may incur charges. Ghostlight does not log prompt or response text, but use only stories you are comfortable sharing with those providers.

## The séance

The terminal is theatrical: it does not monitor, inspect, or execute real shell commands. Ghostlight is a creative writing companion, not a way to contact the dead. The model can make things up.

## Why this version uses hosted AI

The visitor asked for Gemma and ElevenLabs so Ghostlight can use an open-weight Gemma model through Google's hosted API and a natural voice. This trades offline operation and local-only story processing for those services. Keys stay local, can be replaced without changing the interface, and the prompt and model settings are inspectable in `server.py` and `.env`. Google documents hosted Gemma access and the current model IDs [here](https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api).
