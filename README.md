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

You can enter personal provider keys in **Room settings** instead of configuring them server-side. For ElevenLabs, use only the 51-character secret API key beginning with `sk_`, not its label or Key ID; ElevenLabs only shows the secret when it is created or rotated.

Restart the server after changing `.env`. Server-configured keys stay on the Python server. Visitors can instead enter their own keys in **Room settings**; those are held in that tab's session storage and sent to Ghostlight's backend only when needed. The backend forwards each key to its matching provider and does not log or persist it. Prompts go to hosted Gemma; replies go to ElevenLabs only when **Listen** is selected. Both providers may process data under their own terms, and API usage may incur charges. Only enter keys on a Ghostlight deployment you trust.

## Deploy to Vercel

The project includes Vercel Python functions in `api/` for `/api/status`, `/api/chat`, and `/api/speak`. The web page and its CSS/JavaScript are served as static files. The local `server.py` remains available for running Ghostlight on your computer.

1. Push this project to a GitHub, GitLab, or Bitbucket repository. Make sure `.env` is not committed; `.gitignore` excludes it.
2. Sign in to [Vercel](https://vercel.com), choose **Add New → Project**, and import the repository.
3. Set **Root Directory** to the folder containing `index.html`, `api/`, and `vercel.json` (the repository root if you pushed this folder as the repository).
4. In **Project Settings → Environment Variables**, add:

   | Name | Value |
   | --- | --- |
   | `GEMMA_API_KEY` | Your Google AI Studio API key |
   | `ELEVENLABS_API_KEY` | Your ElevenLabs API key with Text to Speech permission |

   Optionally add `GEMMA_MODEL`, `ELEVENLABS_VOICE_ID`, and `ELEVENLABS_MODEL` to override the defaults in `.env`. Apply the secrets to **Production** and, if wanted, **Preview**. Don’t add `.env` to the repository or paste secrets into source files.

5. Choose **Other** as the Framework Preset. Leave Build Command and Output Directory at their defaults/blank; Vercel detects the `api/` Python functions and serves the root HTML/CSS/JS files.
6. Click **Deploy**. When it finishes, open the deployment URL, check `/api/status`, send a prompt, and click **Listen** on a reply.
7. If you add or change environment variables later, redeploy so the new deployment receives them.

The included `vercel.json` sets a 60-second maximum for both hosted AI routes, which fits Vercel Hobby's documented function limit. If a request times out, try again or use a plan with longer function durations. [Vercel Python functions](https://vercel.com/docs/functions/runtimes/python) · [Function duration limits](https://vercel.com/docs/functions/configuring-functions/duration) · [Environment variables](https://vercel.com/docs/environment-variables)

Gemma requests retry transient Google API failures (including HTTP 500) up to two times with a short backoff. Google recommends retrying transient 5xx errors; if they continue, check Google AI Studio service/key status or try again later. [Google API troubleshooting](https://ai.google.dev/gemini-api/docs/troubleshooting)

Ghostlight asks hosted Gemma to use minimal thinking and returns only final-answer text, filtering any response parts explicitly marked as thoughts. This keeps the chat focused on the story instead of the model's planning.

**Protect your API quota:** anyone who can reach a public deployment can call its chat and speech routes, consuming your provider quota. Keep the deployment private while testing, and set appropriate usage limits in Google AI Studio and ElevenLabs before sharing it widely.

## The séance

The terminal is theatrical: it does not monitor, inspect, or execute real shell commands. Ghostlight is a creative writing companion, not a way to contact the dead. The model can make things up.

## Why this version uses hosted AI

The visitor asked for Gemma and ElevenLabs so Ghostlight can use an open-weight Gemma model through Google's hosted API and a natural voice. This trades offline operation and local-only story processing for those services. Keys stay local, can be replaced without changing the interface, and the prompt and model settings are inspectable in `server.py` and `.env`. Google documents hosted Gemma access and the current model IDs [here](https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api).
