# ShieldChat: Live Demo Script (7–8 minutes)

**Presenters:** Piyush Tiwatne (TH3313) and Kedar Bhaskar (TH3314)
**Speaker A** drives the keyboard. **Speaker B** explains. Swap halfway if you like.

---

## Before the viva (10 minutes earlier)

1. Delete `shieldchat.db` to start with a clean demo, then run `python app.py`.
2. Check that `.env` has `GEMINI_API_KEY`. Run `python ai_assistant.py` once to confirm the AI answers.
3. Open three windows and arrange them side by side. Leave them on the login page.
   - **Window A:** normal Chrome
   - **Window B:** Chrome incognito
   - **Window C:** Microsoft Edge (a different browser, so it gets its own session)
4. Optional: if the side-by-side blur would get in the way, set `BLUR_ON_FOCUS_LOSS = false` in `static/chat.js`. Tab-switch blur keeps working either way.
5. Keep this file open on a phone so you can copy the exact texts.

**Fake test values (never real data):**

| What | Value to type |
|---|---|
| Visa card (test number) | `4485 3647 3952 7352` |
| Aadhaar (generated to pass Verhoeff, fake) | `2345 6789 0124` |
| PAN (dummy format example) | `ABCDE1234F` |
| IFSC (fake) | `ABCD0123456` |
| Bank account (fake) | `123456789012` |

---

## Step 1: Real-time chat (≈1 min)

**Do:**
- Window A: log in as `alice@shieldcorp.com` / `Alice@123`.
- Window B: log in as `bob@shieldcorp.com` / `Bob@123`.
- Alice clicks **Bob**. Bob clicks **Alice**. Both show a green online dot.
- Alice types `Hi Bob, can you join the 3 pm project call?` → **Enter**.
- Bob replies `Sure Alice, see you then.`

**Say:**
> "This is ShieldChat, an internal chat app for ShieldCorp employees. It works like WhatsApp: contacts on the left, conversation on the right, and messages arrive instantly through Socket.IO. Everything is stored in SQLite. Notice the small grey 'Checking message…' while it sends. Every message passes through our two-layer DLP before delivery."

---

## Step 2: Login security (≈1 min)

**Do (in Window C, Edge):**
1. Type `piyush@gmail.com` / `anything` → **Sign in**. You get "Access denied: only ShieldCorp employees…".
2. Type `bob@shieldcorp.com` with a wrong password `wrong1` five times. On the 5th you see "Too many failed attempts. Account locked for 2 minutes."
3. Now type the correct password `Bob@123`. It is still locked and shows a countdown.

**Say:**
> "Only company email addresses can sign in. That check happens on the server, not just in the browser. After 5 wrong passwords the account is locked for 2 minutes, which stops password-guessing attacks. Every failed attempt is logged. Passwords are stored as one-way scrypt hashes, never as plain text."

*(Bob's existing session in Window B keeps working; lockout blocks new logins only.)*

---

## Step 3: Credit card blocked → send masked version (≈1 min)

**Do (Alice, Window A):** type exactly

```
Hi Bob, here is the client card: Visa: 4485 3647 3952 7352 Expires: 2/2009
```

→ **Enter**. A red popup appears: *"🛡 ShieldCorp DLP Policy: This message contains Credit/Debit Card Number (Visa). Sharing financial data in chat is not allowed."* The masked value is `XXXX XXXX XXXX 7352 (expiry XX/XX)`.

Click **Send masked version**. Bob receives `…Visa: XXXX XXXX XXXX 7352 Expires: XX/XX`.

**Say:**
> "Layer 1 of our DLP runs locally on our server. It found a 16-digit number, confirmed it is a real card number using the Luhn checksum, identified it as Visa from the leading 4, and also caught the expiry date. The message was blocked before it reached Bob, and the raw number was never sent to Google's AI. The user can edit it or send a masked version that keeps only the last 4 digits."

---

## Step 4: Aadhaar and PAN blocked (≈40 s)

**Do (Alice):**

```
My Aadhaar is 2345 6789 0124 and PAN is abcde1234f
```

→ blocked, with two findings: `XXXX XXXX 0124` and `XXXXX1234X`. Click **Edit message** and the text comes back for correction. Clear the box.

Optional bank example:

```
Please transfer to account 123456789012, IFSC ABCD0123456
```

**Say:**
> "Aadhaar numbers end in a Verhoeff check digit, so we check that, and random 12-digit numbers don't trigger it. This Aadhaar is a fake one we generated to pass the check. PAN is matched by its 5-letters, 4-digits, 1-letter format, even in lower case. Bank account numbers are only flagged when words like 'account' or an IFSC code are nearby. Otherwise every phone number would be blocked."

---

## Step 5: AI Layer 2 catches what patterns miss (≈40 s)

**Do (Alice):**

```
Bob the client's card is four four eight five three six four seven three nine five two seven three five two
```

→ blocked with *"Sensitive information (detected by AI)"*.

Backup line if needed:

```
The production server password is Shield@2026, please don't share it
```

**Say:**
> "There are no digits here, so Layer 1 can't see it. Messages that pass Layer 1 go to Google Gemini once. Gemini returns structured JSON that says whether the message has hidden sensitive data and whether the tone is professional. Gemini spotted a card number written in words. That's our Layer 2."

---

## Step 6: Tone assistant (≈40 s)

**Do (Alice):**

```
Send me the report now, why are you always so slow?
```

→ a yellow card: *"💡 Hint: This message can be conveyed in a more polite and professional way."* with a polite rewrite. Click **Use suggestion**. Bob receives the polite version.

**Say:**
> "The tone check never blocks. It only suggests. The user can use the suggestion, send the original anyway, or edit it. This keeps workplace communication professional, which matters in HR and harassment cases."

---

## Step 7: Anti-exfiltration (≈1 min)

**Do (Window B, Bob):**
1. Try to select a message with the mouse. Nothing highlights.
2. Press **Ctrl+C** or right-click a message. A toast appears: "Copying enterprise data is restricted".
3. Point at the faint diagonal watermark: `bob@shieldcorp.com · date/time`.
4. Press **Ctrl+P**. A toast says "Printing is disabled", and the page would print blank anyway.
5. Switch to another tab, then come back. The chat was blurred with "Chat hidden for privacy".

**Say:**
> "These controls stop casual copying and make leaks traceable. If someone photographs the screen, the watermark shows whose account it was and when. We're being honest: a web page can't stop a phone camera or an OS screenshot. These are deterrents plus an audit trail, the same idea as names printed on confidential photocopies."

---

## Step 8: Security Admin dashboard (≈1 min)

**Do (Window C, Edge):** log in as `admin@shieldcorp.com` / `Admin@123` and it opens **/admin** automatically.
- Cards show total messages, DLP blocks today, copy attempts, failed logins and locked accounts. Bob may still show as locked.
- The incident table lists CARD, AADHAAR, PAN, AI_SENSITIVE, COPY_ATTEMPT, FAILED_LOGIN and LOCKOUT, all **masked**.
- **Live:** in Window A, Alice sends the card number again. The admin table updates instantly and the LIVE dot flashes.
- Optional: in Alice's window, go to `http://localhost:5000/admin`. You get **403 Forbidden**, because the server checks the role.

**Say:**
> "The security team sees every incident live through Socket.IO, with a 5-second refresh as backup. The log stores only masked values. If we stored the real card number, the incident log would itself become a data leak. The admin page is protected on the server, so a normal employee gets 403 even if they type the URL."

**Closing line:**
> "So ShieldChat combines local, offline DLP with AI where it's safe to use it, plus login security and traceability. It's a small model of how enterprise tools like Microsoft Purview protect company chat."

---

## Backup plan: internet or Gemini fails

You don't need to apologise. Turn it into a feature:

1. **Say:** "Our design expects this. DLP Layer 1 is local and fail-closed. AI is optional and fails open."
2. Messages still send, with a small grey note saying "AI assistant unavailable".
3. **Do Steps 3, 4, 7 and 8 exactly as above.** Card, Aadhaar, PAN and bank blocking all work offline, because Socket.IO and all files are served locally.
4. To show it on purpose, stop the server, clear `GEMINI_API_KEY` in `.env`, and restart. The server prints "AI features off, DLP Layer 1 still active".
5. Skip Steps 5 and 6, or show `tests/test_app.py`, which tests the AI flow with a fake Gemini. Run `python -m pytest -v` and all tests go green.

**Other emergencies**

| Problem | Fix |
|---|---|
| "Address already in use" | Close the other `python app.py` window, or restart the PC terminal |
| Bob is still locked | Wait 2 minutes, or delete `shieldchat.db` and restart |
| Both windows show the same user | Use incognito for the second user and a different browser for the admin |
| The window keeps blurring | Click it, or set `BLUR_ON_FOCUS_LOSS = false` |
