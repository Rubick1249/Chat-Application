# ShieldChat: AI-Powered Secure Enterprise Chat with DLP

ShieldChat is an internal company chat app, like WhatsApp for employees. It stops sensitive data
such as card numbers, Aadhaar, PAN and bank details from being shared, discourages copying data
outside the organisation, and uses Google Gemini AI to suggest more professional wording.

**Stack:** HTML/CSS/vanilla JS · Python Flask + Flask-SocketIO (threading mode) · SQLite · Google Gemini API (`google-genai`)

## Setup on Windows

Open **Command Prompt** or **PowerShell** in this `shieldchat` folder.

```bat
:: 1. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate

:: 2. Install the libraries
pip install -r requirements.txt

:: 3. Create your settings file
copy .env.example .env
```

Then edit `.env`:

| Setting | What to put |
|---|---|
| `SECRET_KEY` | A long random string. Generate one with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `GEMINI_API_KEY` | Your key from Google AI Studio (https://aistudio.google.com/apikey). Leave it empty to run without AI. |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` (default: stable, free tier, fast). `gemini-3.8-flash` also works. |

```bat
:: 4. Start the server (creates shieldchat.db and the demo users on first run)
python app.py
```

You should see `ShieldChat running on http://localhost:5000`.

## Opening the two chat instances

Each browser session gets its own login cookie, so use one normal window and one private window:

1. **Normal Chrome window** → http://localhost:5000 → `alice@shieldcorp.com` / `Alice@123`
2. **Incognito window** (Ctrl+Shift+N) → http://localhost:5000 → `bob@shieldcorp.com` / `Bob@123`
3. *(Optional)* **A different browser such as Edge** → http://localhost:5000 → `admin@shieldcorp.com` / `Admin@123`. This opens the Security Dashboard.

> All incognito windows share one session, so the admin needs a *different browser* (or a second Chrome profile).

Click a contact on the left and start chatting.

> **Privacy blur:** the chat blurs whenever its window loses focus. With Alice and Bob side by side,
> the window you are *not* typing in will be blurred; click it to view. To keep both visible
> during a demo, set `BLUR_ON_FOCUS_LOSS = false` at the top of `static/chat.js`.
> Switching tabs or minimising still blurs.

## Running the tests

```bat
python -m pytest -v
```

- `tests/test_dlp.py` covers the DLP engine: Luhn, Verhoeff, cards, Aadhaar, PAN, IFSC, bank accounts, and a phone number that must not be flagged.
- `tests/test_app.py` covers login security, blocking, the AI flow (using a fake Gemini, so no key is needed), incidents and admin access.

Try the DLP engine alone with `python dlp.py`. Try Gemini alone, after setting the key, with `python ai_assistant.py`.

## Project structure

```
app.py            Flask routes, login security, Socket.IO events, admin dashboard API
dlp.py            Layer 1 DLP: regex patterns, Luhn, Verhoeff, masking
ai_assistant.py   Layer 2: one Gemini call (JSON output), 5 s timeout, safe fallback
database.py       SQLite tables + demo users (hashed passwords)
templates/        login.html, chat.html, admin.html
static/           style.css, chat.js, socket.io.min.js (stored locally so the app works offline)
tests/            pytest tests
```

## Reset the demo data

Stop the server and delete `shieldchat.db`. It is recreated, with the three demo users, the next time the server starts.

## Security notes (honest)

- Layer 1 DLP runs locally on the server and works with no internet connection. Raw sensitive values are never sent to Gemini or written to the database.
- Copy blocking, the watermark, the blur and print blocking are **deterrents and traceability controls**. A phone camera or an OS screenshot cannot be stopped by a web page.
- This is a local demo. A real deployment needs HTTPS (with `SESSION_COOKIE_SECURE=True`), a production server, and CSRF tokens.
