"""
Build ShieldChat_Presentation.pptx (16:9) with python-pptx.
Screenshots in ppt_assets/ are real captures of the running app.
Every slide has speaker notes so either presenter can explain it.
"""

import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "ppt_assets")
OUT = os.path.join(os.path.dirname(HERE), "ShieldChat_Presentation.pptx")

TEAL_DARK = RGBColor(0x07, 0x5E, 0x54)
TEAL = RGBColor(0x12, 0x8C, 0x7E)
MINT = RGBColor(0xE7, 0xF6, 0xF3)
GREEN_BUBBLE = RGBColor(0xD9, 0xFD, 0xD3)
RED = RGBColor(0xD9, 0x30, 0x25)
RED_BG = RGBColor(0xFD, 0xEC, 0xEA)
AMBER = RGBColor(0x8A, 0x61, 0x00)
AMBER_BG = RGBColor(0xFF, 0xF8, 0xDB)
BLUE = RGBColor(0x1A, 0x56, 0xC4)
BLUE_BG = RGBColor(0xE8, 0xF0, 0xFE)
INK = RGBColor(0x11, 0x1B, 0x21)
MUTED = RGBColor(0x5B, 0x6B, 0x75)
GREY_BG = RGBColor(0xF0, 0xF2, 0xF5)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT = "Segoe UI"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]
TOTAL = 18
_count = 0


# ------------------------------------------------------------------ helpers

def text(slide, x, y, w, h, content, size=16, color=INK, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, font=FONT, spacing=1.1):
    """Text box. content may be a string or a list of strings / (text, dict) runs-per-line."""
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    lines = content if isinstance(content, list) else [content]
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        runs = line if isinstance(line, list) else [line]
        for run_spec in runs:
            t, opts = (run_spec, {}) if isinstance(run_spec, str) else run_spec
            r = p.add_run()
            r.text = t
            r.font.name = opts.get("font", font)
            r.font.size = Pt(opts.get("size", size))
            r.font.bold = opts.get("bold", bold)
            r.font.color.rgb = opts.get("color", color)
    return tb


def box(slide, x, y, w, h, fill, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08):
    s = slide.shapes.add_shape(shape, x, y, w, h)
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(1.25)
    s.shadow.inherit = False
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = radius
    return s


def card(slide, x, y, w, h, title, body, fill=WHITE, accent=TEAL, icon=None, title_size=17, body_size=13):
    """A rounded card with a coloured top stripe, title and body text."""
    box(slide, x, y, w, h, fill, line=RGBColor(0xD5, 0xDD, 0xE0))
    box(slide, x, y, w, Inches(0.09), accent, shape=MSO_SHAPE.RECTANGLE)
    top = y + Inches(0.22)
    if icon:
        text(slide, x + Inches(0.2), top, w - Inches(0.4), Inches(0.5), icon, size=24)
        top += Inches(0.55)
    text(slide, x + Inches(0.2), top, w - Inches(0.4), Inches(0.5), title, size=title_size, bold=True, color=accent)
    text(slide, x + Inches(0.2), top + Inches(0.48), w - Inches(0.4), h - (top - y) - Inches(0.55), body,
         size=body_size, color=INK, spacing=1.15)


def picture(slide, name, x, y, w=None, h=None, border=True):
    pic = slide.shapes.add_picture(os.path.join(ASSETS if not name.endswith("architecture.png") else HERE, name),
                                   x, y, width=w, height=h)
    if border:
        pic.line.color.rgb = RGBColor(0xC9, 0xD1, 0xD6)
        pic.line.width = Pt(1)
    return pic


def new_slide(title, kicker=None, notes=""):
    """Standard content slide: left accent bar, title, slide number, footer."""
    global _count
    _count += 1
    s = prs.slides.add_slide(BLANK)
    box(s, 0, 0, Inches(0.18), prs.slide_height, TEAL_DARK, shape=MSO_SHAPE.RECTANGLE)
    if kicker:
        text(s, Inches(0.6), Inches(0.32), Inches(10), Inches(0.35), kicker.upper(), size=12, bold=True, color=TEAL)
    text(s, Inches(0.6), Inches(0.58), Inches(12), Inches(0.8), title, size=30, bold=True, color=TEAL_DARK)
    text(s, Inches(0.6), Inches(7.05), Inches(8), Inches(0.3), "🛡 ShieldChat · Secure Enterprise Chat with DLP",
         size=10, color=MUTED)
    text(s, Inches(11.9), Inches(7.05), Inches(1.0), Inches(0.3), f"{_count} / {TOTAL}", size=10, color=MUTED,
         align=PP_ALIGN.RIGHT)
    if notes:
        s.notes_slide.notes_text_frame.text = notes
    return s


def bullets(slide, x, y, w, h, items, size=16, color=INK, bullet="•", gap=8):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        p.line_spacing = 1.1
        head, rest = item if isinstance(item, tuple) else ("", item)
        r = p.add_run()
        r.text = f"{bullet}  " if bullet else ""
        r.font.size = Pt(size); r.font.name = FONT; r.font.color.rgb = TEAL; r.font.bold = True
        if head:
            r = p.add_run(); r.text = head
            r.font.size = Pt(size); r.font.name = FONT; r.font.bold = True; r.font.color.rgb = color
        r = p.add_run(); r.text = rest
        r.font.size = Pt(size); r.font.name = FONT; r.font.color.rgb = color
    return tb


def pill(slide, x, y, w, label, fill, color, size=12):
    s = box(slide, x, y, w, Inches(0.38), fill, radius=0.5)
    tf = s.text_frame
    tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = label
    r.font.size = Pt(size); r.font.bold = True; r.font.name = FONT; r.font.color.rgb = color
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    return s


def code_box(slide, x, y, w, h, lines, size=12):
    box(slide, x, y, w, h, RGBColor(0x1E, 0x29, 0x2E))
    text(slide, x + Inches(0.2), y + Inches(0.15), w - Inches(0.4), h - Inches(0.3), lines, size=size,
         color=RGBColor(0xD7, 0xF5, 0xEE), font="Consolas", spacing=1.05)


# ================================================================== 1. TITLE

_count += 1
s = prs.slides.add_slide(BLANK)
box(s, 0, 0, prs.slide_width, prs.slide_height, TEAL_DARK, shape=MSO_SHAPE.RECTANGLE)
box(s, Inches(8.6), Inches(-1.2), Inches(6.5), Inches(6.5), TEAL, shape=MSO_SHAPE.OVAL)
box(s, Inches(10.4), Inches(4.2), Inches(4.0), Inches(4.0), RGBColor(0x0B, 0x6F, 0x63), shape=MSO_SHAPE.OVAL)
text(s, Inches(0.8), Inches(0.9), Inches(3), Inches(1), "🛡", size=54, color=WHITE)
text(s, Inches(0.8), Inches(1.95), Inches(10), Inches(1.1), "ShieldChat", size=60, bold=True, color=WHITE)
text(s, Inches(0.8), Inches(3.05), Inches(10.5), Inches(1.2),
     "AI-Powered Secure Enterprise Chat Application with Data Loss Prevention",
     size=24, color=RGBColor(0xC8, 0xF4, 0xEA))
text(s, Inches(0.8), Inches(4.2), Inches(10), Inches(0.5),
     "Python Flask · Flask-SocketIO · SQLite · Google Gemini API", size=16, color=RGBColor(0x9F, 0xE0, 0xD2))
text(s, Inches(0.8), Inches(5.0), Inches(8), Inches(1.6), [
    [("Piyush Tiwatne (TH3313)  ·  Kedar Bhaskar (TH3314)", {"bold": True})],
    "Guide: Mrs Rajashree Khadke",
    "Department: CDS  ·  MIT ACSC  ·  Academic Year 2026-27",
], size=16, color=WHITE, spacing=1.3)
s.notes_slide.notes_text_frame.text = (
    "Good morning. We are Piyush and Kedar. Our project is ShieldChat: an internal company chat app, like "
    "WhatsApp for employees, that stops sensitive data such as card numbers, Aadhaar, PAN and bank details from "
    "being shared, discourages copying data outside the organisation, and uses Google Gemini AI to suggest more "
    "professional wording.")

# ================================================================== 2. PROBLEM

s = new_slide("Chat is where company data leaks", "The problem", notes=(
    "Companies moved from email to chat because it is fast. But speed means people paste things without "
    "thinking. Example: a support employee pastes a customer's card number to a colleague. Now it sits on "
    "chat servers, visible to everyone, easy to forward. That can breach the DPDP Act 2023, RBI rules and PCI-DSS. "
    "Data also leaves by copy-paste, printing and screenshots, and rude messages create HR problems."))
cards = [
    ("💳", "Sensitive data in chat", "Employees paste card numbers, Aadhaar, PAN and bank details to colleagues, "
     "often without thinking.", RED),
    ("📋", "Data walks out the door", "Copy-paste into personal email, printing, screen-sharing and "
     "screenshots move data outside the organisation.", AMBER),
    ("😠", "Unprofessional tone", "Rude or aggressive messages damage teamwork and can become HR and "
     "harassment issues.", BLUE),
]
for i, (icon, title, body, accent) in enumerate(cards):
    card(s, Inches(0.6 + i * 4.15), Inches(1.75), Inches(3.9), Inches(3.4), title, body, accent=accent, icon=icon,
         body_size=15)
box(s, Inches(0.6), Inches(5.55), Inches(12.2), Inches(1.15), MINT)
text(s, Inches(0.9), Inches(5.62), Inches(11.7), Inches(1.0), [
    [("Why it matters:  ", {"bold": True, "color": TEAL_DARK}),
     "India's DPDP Act 2023, RBI card-data rules and PCI-DSS all require organisations to protect personal "
     "and financial data, including inside internal tools."]], size=15, anchor=MSO_ANCHOR.MIDDLE)

# ================================================================== 3. SOLUTION

s = new_slide("ShieldChat: WhatsApp for employees, with a security guard", "Our solution", notes=(
    "Our answer has four pillars. Secure login so only employees get in. A two-layer DLP engine that checks every "
    "message: Layer 1 runs locally with patterns and checksums; Layer 2 uses Gemini AI for things patterns "
    "cannot see, and also suggests polite wording. Anti-exfiltration controls discourage copying and make leaks "
    "traceable. And a live dashboard for the security team."))
text(s, Inches(0.6), Inches(1.45), Inches(12.2), Inches(0.9),
     "A real-time internal chat app that blocks sensitive data before it is sent, discourages copying, "
     "and uses Google Gemini AI to keep communication professional.", size=17, color=MUTED)
pillars = [
    ("🔐", "Secure Login", "Hashed passwords\nCompany-domain only\nLockout after 5 failures", TEAL),
    ("🛡", "2-Layer DLP", "Layer 1: local regex + checksums\nLayer 2: Gemini AI context check", RED),
    ("🚫", "Anti-Exfiltration", "Copy & print blocked\nUser watermark\nPrivacy blur", AMBER),
    ("📊", "Admin Monitoring", "Live incident dashboard\nMasked values only\nRole-protected", BLUE),
]
for i, (icon, title, body, accent) in enumerate(pillars):
    card(s, Inches(0.6 + i * 3.1), Inches(2.45), Inches(2.9), Inches(3.3), title, body, accent=accent, icon=icon,
         body_size=14)
text(s, Inches(0.6), Inches(6.05), Inches(12.2), Inches(0.6),
     [[("Plus: ", {"bold": True, "color": TEAL_DARK}),
       "an AI tone assistant that suggests a polite rewrite (it never blocks)."]], size=15)

# ================================================================== 4. TECH STACK

s = new_slide("Technology stack", "How it is built", notes=(
    "We kept the stack simple so it runs on any Windows laptop. No React, no build step: plain HTML, CSS and "
    "JavaScript. Flask is the Python web framework; Flask-SocketIO gives real-time two-way messaging, in threading "
    "mode so it works on Windows without extra servers. SQLite is a single-file database. The AI is Google Gemini "
    "through the official google-genai SDK, model gemini-3.5-flash-lite: stable, free tier, and fast."))
stack = [
    ("Frontend", "HTML · CSS · Vanilla JavaScript", "No framework, no build step", TEAL),
    ("Backend", "Python Flask + Flask-SocketIO", "Real-time messaging (threading mode)", TEAL_DARK),
    ("Database", "SQLite", "Users, messages, incidents in one file", MUTED),
    ("AI", "Google Gemini API (google-genai)", "Model: gemini-3.5-flash-lite (from .env)", BLUE),
    ("Security", "Werkzeug scrypt · python-dotenv", "Password hashing, secrets in .env", RED),
    ("Testing", "pytest", "28 automated tests, all passing", AMBER),
]
for i, (layer, tech, note, accent) in enumerate(stack):
    col, row = i % 2, i // 2
    x, y = Inches(0.6 + col * 6.2), Inches(1.6 + row * 1.7)
    box(s, x, y, Inches(5.95), Inches(1.45), GREY_BG)
    box(s, x, y, Inches(0.12), Inches(1.45), accent, shape=MSO_SHAPE.RECTANGLE)
    text(s, x + Inches(0.35), y + Inches(0.14), Inches(5.4), Inches(0.35), layer.upper(), size=12, bold=True,
         color=accent)
    text(s, x + Inches(0.35), y + Inches(0.45), Inches(5.4), Inches(0.5), tech, size=19, bold=True)
    text(s, x + Inches(0.35), y + Inches(0.92), Inches(5.4), Inches(0.4), note, size=13, color=MUTED)

# ================================================================== 5. ARCHITECTURE

s = new_slide("System architecture", "Design", notes=(
    "Browsers talk to one Flask server over Socket.IO. Every message goes to the DLP engine first; it runs on our "
    "own server. Only if the message is clean do we call Gemini. The result is either delivered, blocked with a "
    "popup, or returned with a tone suggestion. Everything is stored in SQLite, and incidents are pushed live to "
    "the admin dashboard. The key point: raw sensitive data never reaches Gemini."))
picture(s, os.path.join(HERE, "architecture.png"), Inches(0.6), Inches(1.45), h=Inches(5.45), border=False)
box(s, Inches(10.15), Inches(1.7), Inches(2.75), Inches(4.9), MINT)
text(s, Inches(10.35), Inches(1.85), Inches(2.4), Inches(4.6), [
    [("Key design rule", {"bold": True, "color": TEAL_DARK, "size": 17})],
    "",
    "Raw sensitive data never leaves our server.",
    "",
    "Layer 1 DLP blocks it locally before any AI call.",
    "",
    "Only clean messages are sent to Gemini.",
], size=14, spacing=1.15)

# ================================================================== 6. MESSAGE FLOW

s = new_slide("What happens when you press Send", "Message flow", notes=(
    "Step by step: the browser sends the text over Socket.IO. The server takes the sender's identity from the "
    "signed session, never from the browser. Layer 1 scans locally. If it finds something, block and log a masked "
    "incident. If clean, one Gemini call returns JSON. Then there are three outcomes: send, block, or suggest. "
    "If Gemini is down, we still send. Layer 1 has already protected us."))
steps = [
    ("1", "Type & Send", "Browser emits the text over Socket.IO", TEAL),
    ("2", "Who sent it?", "Identity from the signed session, not the browser", TEAL_DARK),
    ("3", "Layer 1 DLP", "Local regex + Luhn / Verhoeff scan", RED),
    ("4", "Layer 2 AI", "One Gemini call, strict JSON (only if clean)", BLUE),
    ("5", "Decision", "Send · Block · Suggest", AMBER),
]
for i, (num, title, body, accent) in enumerate(steps):
    x = Inches(0.6 + i * 2.5)
    shp = box(s, x, Inches(1.75), Inches(2.3), Inches(2.4), WHITE, line=accent)
    c = box(s, x + Inches(0.85), Inches(1.5), Inches(0.6), Inches(0.6), accent, shape=MSO_SHAPE.OVAL)
    c.text_frame.text = num
    c.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
    r = c.text_frame.paragraphs[0].runs[0]; r.font.bold = True; r.font.size = Pt(18); r.font.color.rgb = WHITE
    text(s, x + Inches(0.12), Inches(2.3), Inches(2.06), Inches(0.5), title, size=17, bold=True, color=accent,
         align=PP_ALIGN.CENTER)
    text(s, x + Inches(0.12), Inches(2.85), Inches(2.06), Inches(1.2), body, size=13, align=PP_ALIGN.CENTER,
         color=MUTED)
    if i < len(steps) - 1:
        a = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, x + Inches(2.32), Inches(2.8), Inches(0.16), Inches(0.3))
        a.fill.solid(); a.fill.fore_color.rgb = MUTED; a.line.fill.background()
outcomes = [
    ("✅ Clean & professional", "Saved to SQLite and delivered instantly to the receiver.", TEAL, MINT),
    ("⛔ Sensitive data found", "Blocked. Red popup, masked incident logged, admin alerted live.", RED, RED_BG),
    ("💡 Unprofessional tone", "Not blocked. Yellow hint with a polite rewrite to choose from.", AMBER, AMBER_BG),
]
for i, (title, body, accent, fill) in enumerate(outcomes):
    x = Inches(0.6 + i * 4.15)
    box(s, x, Inches(4.55), Inches(3.95), Inches(1.5), fill)
    text(s, x + Inches(0.25), Inches(4.68), Inches(3.5), Inches(0.4), title, size=16, bold=True, color=accent)
    text(s, x + Inches(0.25), Inches(5.12), Inches(3.5), Inches(0.9), body, size=13)
text(s, Inches(0.6), Inches(6.3), Inches(12.2), Inches(0.5),
     [[("If Gemini is down, slow (> 5 s) or has no key: ", {"bold": True, "color": TEAL_DARK}),
       "Layer 1 has already run, the message is sent, and the user sees \"AI assistant unavailable\"."]], size=14)

# ================================================================== 7. LOGIN SECURITY

s = new_slide("Only employees get in", "Feature 1 · Authentication security", notes=(
    "Passwords are hashed with scrypt and a random salt: a one-way blender, so even if the database is stolen the "
    "passwords are not exposed. Only shieldcorp.com emails can sign in, checked on the server. Five wrong passwords "
    "lock the account for two minutes, which stops brute force; every failure is logged for the admin. Sessions "
    "use a signed cookie that JavaScript cannot read."))
bullets(s, Inches(0.6), Inches(1.6), Inches(6.2), Inches(5.2), [
    ("Password hashing: ", "salted scrypt via Werkzeug. A one-way blender: we can check a password but never "
     "recover it."),
    ("Domain restriction: ", "only @shieldcorp.com emails, checked on the server."),
    ("Account lockout: ", "5 wrong passwords → locked for 2 minutes. Stops brute-force guessing."),
    ("Every failure logged: ", "FAILED_LOGIN and LOCKOUT incidents appear on the admin dashboard."),
    ("Secure session cookie: ", "signed with a secret key from .env, HttpOnly and SameSite."),
], size=16, gap=12)
picture(s, "s1_login.png", Inches(7.2), Inches(1.7), w=Inches(5.6))
text(s, Inches(7.2), Inches(5.0), Inches(5.6), Inches(0.4), "ShieldChat login page", size=12, color=MUTED,
     align=PP_ALIGN.CENTER)
pill(s, Inches(7.2), Inches(5.55), Inches(5.6),
     "gmail.com → \"Access denied\" (employees only)", RED_BG, RED, size=12)
pill(s, Inches(7.2), Inches(6.05), Inches(5.6),
     "5th wrong password → \"Account locked for 2 minutes\"", RED_BG, RED, size=12)

# ================================================================== 8. DLP LAYER 1

s = new_slide("DLP Layer 1: pattern + checksum detection", "Feature 2 · The star feature", notes=(
    "Think of it as an airport X-ray for messages. Regular expressions find the shape of the data, and checksums "
    "confirm it is real, so random numbers are not flagged. Bank accounts are the tricky one: 9 to 18 digits also "
    "matches phone numbers and order IDs, so we only flag them when words like 'account' or an IFSC code are nearby. "
    "Every finding is masked to the last four characters, and only the masked value is stored."))
rows = [
    ("Data type", "How we detect it", "Masked as"),
    ("Credit / debit card", "13–19 digits + Luhn checksum + network from prefix + expiry date", "XXXX XXXX XXXX 7352"),
    ("Aadhaar", "12 digits, first digit 2–9 + Verhoeff checksum", "XXXX XXXX 0124"),
    ("PAN", "5 letters · 4 digits · 1 letter (any case)", "XXXXX1234X"),
    ("IFSC", "4 letters · 0 · 6 letters/digits", "XXXXXXX3456"),
    ("Bank account", "9–18 digits only near 'account', 'bank', 'a/c' or an IFSC", "XXXXXXXX9012"),
]
tbl = s.shapes.add_table(len(rows), 3, Inches(0.6), Inches(1.6), Inches(12.2), Inches(3.6)).table
for c_i, wdt in enumerate((2.6, 6.6, 3.0)):
    tbl.columns[c_i].width = Inches(wdt)
for r_i, row in enumerate(rows):
    for c_i, val in enumerate(row):
        cell = tbl.cell(r_i, c_i)
        cell.fill.solid()
        cell.fill.fore_color.rgb = TEAL_DARK if r_i == 0 else (WHITE if r_i % 2 else GREY_BG)
        cell.text = val
        p = cell.text_frame.paragraphs[0]
        r = p.runs[0]
        r.font.size = Pt(15 if r_i else 14)
        r.font.name = "Consolas" if (c_i == 2 and r_i) else FONT
        r.font.bold = r_i == 0 or c_i == 0
        r.font.color.rgb = WHITE if r_i == 0 else (RED if c_i == 2 else INK)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
box(s, Inches(0.6), Inches(5.5), Inches(5.95), Inches(1.3), MINT)
text(s, Inches(0.85), Inches(5.6), Inches(5.5), Inches(1.1), [
    [("Runs on our server, works offline", {"bold": True, "color": TEAL_DARK})],
    "If Layer 1 finds anything, the raw text is never sent to the AI.",
], size=14, spacing=1.2)
box(s, Inches(6.85), Inches(5.5), Inches(5.95), Inches(1.3), AMBER_BG)
text(s, Inches(7.1), Inches(5.6), Inches(5.5), Inches(1.1), [
    [("Why the bank-account context rule?", {"bold": True, "color": AMBER})],
    "Otherwise every phone number and order ID would be blocked (false positives).",
], size=14, spacing=1.2)

# ================================================================== 9. LUHN & VERHOEFF

s = new_slide("Checksums: a spelling check for numbers", "How we avoid false alarms", notes=(
    "A checksum is like a spell-check for numbers: the last digit is calculated from the others, so a random "
    "number usually fails. Luhn: from the right, double every second digit, subtract 9 if over 9, add everything; "
    "a valid card total ends in zero. Our Visa test number totals 80, so it is valid. Verhoeff is stronger: it "
    "catches every single-digit mistake and every swap of neighbouring digits. UIDAI uses it for Aadhaar."))
card(s, Inches(0.6), Inches(1.6), Inches(6.0), Inches(5.1), "Luhn: cards", "", accent=TEAL)
bullets(s, Inches(0.8), Inches(2.3), Inches(5.6), Inches(2.0), [
    "From the right, double every 2nd digit",
    "If the result > 9, subtract 9",
    "Add all digits. A valid card's total ends in 0",
], size=15, bullet="→", gap=6)
code_box(s, Inches(0.85), Inches(4.0), Inches(5.5), Inches(2.45), [
    "Test card: 4485 3647 3952 7352",
    "",
    "double: 4 8 3 4 3 5 7 5",
    "     → 8 7 6 8 6 1 5 1          = 42",
    "others: 4 5 6 7 9 2 3 2          = 38",
    "total = 42 + 38 = 80   ✓ ends in 0",
    "→ valid Visa (starts with 4) → BLOCK",
], size=13)
card(s, Inches(6.8), Inches(1.6), Inches(6.0), Inches(5.1), "Verhoeff: Aadhaar", "", accent=BLUE)
bullets(s, Inches(7.0), Inches(2.3), Inches(5.6), Inches(2.4), [
    "Uses 3 fixed tables (multiply, permute, inverse)",
    "Catches EVERY single-digit error and EVERY swap of neighbouring digits (Luhn misses some)",
    "UIDAI uses it for Aadhaar's 12th digit",
], size=15, bullet="→", gap=6)
box(s, Inches(7.05), Inches(4.75), Inches(5.5), Inches(1.7), BLUE_BG)
text(s, Inches(7.25), Inches(4.85), Inches(5.1), Inches(1.5), [
    [("Result:", {"bold": True, "color": BLUE})],
    "A random 12-digit or 16-digit number (order ID, tracking no.) is almost never flagged.",
    [("Our test Aadhaar is fake, generated with Verhoeff.", {"size": 12, "color": MUTED})],
], size=14, spacing=1.2)

# ================================================================== 10. DLP IN ACTION

s = new_slide("DLP in action: card number blocked", "Live result", notes=(
    "This is a real screenshot. Alice typed the client's Visa number with its expiry date. The message was blocked "
    "before it reached Bob. The popup names the policy, shows only the masked value and the reason. Alice can edit "
    "the message, or send the masked version, which Bob receives as XXXX XXXX XXXX 7352 with the expiry masked too. "
    "The raw message was never sent to Gemini."))
picture(s, "s3_dlp.png", Inches(0.6), Inches(1.55), h=Inches(5.25))
text(s, Inches(9.1), Inches(1.6), Inches(3.8), Inches(0.5), "Alice typed:", size=14, bold=True, color=MUTED)
box(s, Inches(9.1), Inches(2.05), Inches(3.75), Inches(1.15), GREEN_BUBBLE)
text(s, Inches(9.25), Inches(2.1), Inches(3.5), Inches(1.05),
     "Hi Bob, here is the client card: Visa: 4485 3647 3952 7352 Expires: 2/2009", size=13,
     anchor=MSO_ANCHOR.MIDDLE)
text(s, Inches(9.1), Inches(3.4), Inches(3.8), Inches(0.5), "Bob received (masked):", size=14, bold=True,
     color=MUTED)
box(s, Inches(9.1), Inches(3.85), Inches(3.75), Inches(1.15), WHITE, line=RGBColor(0xD5, 0xDD, 0xE0))
text(s, Inches(9.25), Inches(3.9), Inches(3.5), Inches(1.05),
     "Hi Bob, here is the client card: Visa: XXXX XXXX XXXX 7352 Expires: XX/XX", size=13,
     anchor=MSO_ANCHOR.MIDDLE)
bullets(s, Inches(9.1), Inches(5.25), Inches(3.8), Inches(1.6), [
    "Visa identified from the leading 4",
    "Expiry date caught too",
    "Incident logged with masked value",
], size=13, gap=3)

# ================================================================== 11. AI LAYER 2 + TONE

s = new_slide("Gemini AI: Layer 2 DLP + tone assistant", "Feature 3 · AI integration", notes=(
    "Patterns can't read meaning. 'Four four eight five...' has no digits, and 'the password is...' has no fixed "
    "format. So clean messages go to Gemini once, and we force a strict JSON answer using the SDK's structured "
    "output. If sensitive_detected is true, we block like a DLP finding. If is_unprofessional, we show a yellow "
    "hint: the user can use the suggestion, send the original, or edit. We never block for tone. Fail-closed for "
    "security, fail-open for convenience."))
code_box(s, Inches(0.6), Inches(1.6), Inches(5.6), Inches(2.75), [
    "// One Gemini call → strict JSON",
    "{",
    '  "is_unprofessional": true,',
    '  "tone": "aggressive",',
    '  "suggestion": "Could you please share',
    '        the report when you get a chance?",',
    '  "sensitive_detected": false,',
    '  "sensitive_reason": ""',
    "}",
], size=13)
text(s, Inches(0.6), Inches(4.5), Inches(5.6), Inches(0.4), "Catches what patterns miss:", size=15, bold=True,
     color=BLUE)
bullets(s, Inches(0.6), Inches(4.95), Inches(5.6), Inches(1.9), [
    "Numbers written in words (\"four four eight five…\")",
    "Passwords, PINs, salary details",
    "Confidential project or customer information",
], size=14, gap=4)
# tone hint mock-up (drawn, mirrors the app's yellow card)
text(s, Inches(6.6), Inches(1.55), Inches(6.2), Inches(0.4), "Tone assistant (never blocks)", size=15, bold=True,
     color=AMBER)
box(s, Inches(6.6), Inches(2.0), Inches(6.2), Inches(0.75), GREEN_BUBBLE)
text(s, Inches(6.8), Inches(2.05), Inches(5.8), Inches(0.65),
     "\"Send me the report now, why are you always so slow?\"", size=14, anchor=MSO_ANCHOR.MIDDLE)
box(s, Inches(6.6), Inches(2.95), Inches(6.2), Inches(2.0), AMBER_BG, line=RGBColor(0xF1, 0xD6, 0x75))
text(s, Inches(6.8), Inches(3.05), Inches(5.8), Inches(0.5),
     "💡 Hint: This message can be conveyed in a more polite and professional way.", size=13, bold=True,
     color=AMBER)
box(s, Inches(6.8), Inches(3.6), Inches(5.8), Inches(0.6), WHITE)
text(s, Inches(6.95), Inches(3.62), Inches(5.6), Inches(0.56),
     "Could you please share the report when you get a chance?", size=13, anchor=MSO_ANCHOR.MIDDLE)
for i, (lbl, fill, col) in enumerate([("Use suggestion", TEAL, WHITE), ("Send original anyway", WHITE, INK),
                                      ("Edit", WHITE, INK)]):
    pill(s, Inches(6.8 + [0, 1.75, 4.0][i]), Inches(4.38), Inches([1.6, 2.1, 0.9][i]), lbl, fill, col, size=11)
text(s, Inches(6.6), Inches(5.0), Inches(6.2), Inches(0.3), "Illustration of the in-app hint card",
     size=10, color=MUTED, align=PP_ALIGN.RIGHT)
box(s, Inches(6.6), Inches(5.45), Inches(6.2), Inches(1.35), MINT)
text(s, Inches(6.8), Inches(5.52), Inches(5.9), Inches(1.25), [
    [("Fail-closed for security: ", {"bold": True, "color": RED}), "Layer 1 always runs, even offline."],
    [("Fail-open for convenience: ", {"bold": True, "color": TEAL_DARK}),
     "if Gemini fails or takes over 5 s, the message is still sent."],
], size=13, spacing=1.2)

# ================================================================== 12. ANTI-EXFILTRATION

s = new_slide("Stopping data from walking out", "Feature 4 · Anti-exfiltration", notes=(
    "Copy, cut, right-click and text selection are disabled in the message area; each attempt shows a toast and is "
    "logged. Large pastes over 200 characters are allowed but logged. A faint watermark with the user's email and the "
    "time covers the chat, like a name stamped on photocopies, so any photo of the screen is traceable. The chat "
    "blurs when you switch away, and printing gives a blank page. We are honest: a phone camera can't be stopped; "
    "these are deterrents plus an audit trail."))
bullets(s, Inches(0.6), Inches(1.55), Inches(4.6), Inches(4.3), [
    ("Copy / cut / right-click blocked ", "in the message area → toast + COPY_ATTEMPT log"),
    ("Bulk paste (> 200 chars) ", "allowed but logged (size only)"),
    ("Dynamic watermark: ", "email + date/time on every screen"),
    ("Privacy blur ", "when the window loses focus"),
    ("Printing disabled: ", "page prints blank"),
], size=15, gap=10)
picture(s, "s5_watermark.png", Inches(5.4), Inches(1.6), w=Inches(3.65))
picture(s, "s5b_blur.png", Inches(9.2), Inches(1.6), w=Inches(3.65))
text(s, Inches(5.4), Inches(4.0), Inches(3.65), Inches(0.35), "Watermark + \"Printing is disabled\"", size=11,
     color=MUTED, align=PP_ALIGN.CENTER)
text(s, Inches(9.2), Inches(4.0), Inches(3.65), Inches(0.35), "Blurred when the window loses focus", size=11,
     color=MUTED, align=PP_ALIGN.CENTER)
box(s, Inches(5.4), Inches(4.65), Inches(7.45), Inches(1.95), AMBER_BG)
text(s, Inches(5.65), Inches(4.75), Inches(7.0), Inches(1.8), [
    [("Honest limitation", {"bold": True, "color": AMBER, "size": 16})],
    "A web app cannot stop a phone camera or an OS screenshot.",
    "These are deterrents + traceability: the watermark shows who leaked it, and when.",
], size=14, spacing=1.25)

# ================================================================== 13. ADMIN DASHBOARD

s = new_slide("Security Admin dashboard: incidents live", "Feature 5 · Monitoring", notes=(
    "The admin sees totals and every incident in real time: Socket.IO pushes each new incident, with a 5-second "
    "refresh as a backup. Notice the details column shows only masked values; storing the real card number would "
    "make the log itself a data leak. The page is protected on the server: if Alice types /admin, she gets 403."))
picture(s, "s6_admin_crop.png", Inches(0.6), Inches(1.7), w=Inches(8.2))
bullets(s, Inches(9.1), Inches(1.7), Inches(3.8), Inches(5.0), [
    ("Live: ", "pushed instantly via Socket.IO (+ 5 s refresh backup)"),
    ("Cards: ", "messages, DLP blocks today, copy attempts, failed logins, locked accounts"),
    ("Masked only: ", "the log never stores raw values"),
    ("Server-side role check: ", "employees get 403 Forbidden"),
], size=14, gap=12)

# ================================================================== 14. SECURE CODING & TESTING

s = new_slide("Built securely and tested", "Quality", notes=(
    "Beyond the features, we followed secure coding rules. Every SQL query uses parameter placeholders, which "
    "prevents SQL injection. Messages are displayed with textContent, never innerHTML, so a script tag shows as "
    "plain text; you can see that in the earlier screenshot. Every security decision is made on the server. "
    "The API key lives in .env, which is excluded from git. And 28 automated tests pass."))
items = [
    ("💉", "SQL injection", "Parameterised queries (?) everywhere. Input is data, never SQL.", TEAL),
    ("🧪", "XSS", "textContent, never innerHTML. <script> shows as plain text.", RED),
    ("🖥", "Server-side checks", "DLP, roles and identity enforced on the server, not in JavaScript.", BLUE),
    ("🔑", "Secrets", "API key and SECRET_KEY in .env, excluded by .gitignore.", AMBER),
]
for i, (icon, title, body, accent) in enumerate(items):
    card(s, Inches(0.6 + (i % 2) * 3.15), Inches(1.6 + (i // 2) * 2.6), Inches(2.95), Inches(2.4), title, body,
         accent=accent, icon=icon, body_size=13, title_size=16)
box(s, Inches(7.1), Inches(1.6), Inches(5.75), Inches(5.0), TEAL_DARK)
text(s, Inches(7.4), Inches(1.75), Inches(5.2), Inches(1.0), "28 / 28", size=54, bold=True, color=WHITE)
text(s, Inches(7.4), Inches(2.75), Inches(5.2), Inches(0.5), "automated pytest tests passing", size=17,
     color=RGBColor(0xC8, 0xF4, 0xEA))
bullets(s, Inches(7.4), Inches(3.4), Inches(5.3), Inches(3.2), [
    "Visa sample detected; Luhn valid/invalid",
    "Fake Aadhaar generated with Verhoeff",
    "PAN, IFSC, bank account with/without context",
    "Phone number NOT flagged",
    "Raw card never reaches the AI",
    "Gemini timeout falls back safely",
    "Non-admin gets 403",
], size=13, color=WHITE, gap=3)

# ================================================================== 15. ADVANTAGES & LIMITATIONS

s = new_slide("Advantages and limitations", "Evaluation", notes=(
    "Advantages: privacy-first layered DLP, works offline, and full accountability. Limitations, honestly: "
    "screenshots and phone cameras can't be fully blocked, regex can miss creative formats like numbers split "
    "across messages or inside images, and the AI needs the internet and can misjudge tone. Also, on Gemini's free "
    "tier Google may use inputs to improve its products, which is another reason sensitive data never goes to the AI."))
card(s, Inches(0.6), Inches(1.6), Inches(5.95), Inches(4.0), "✅  Advantages", "", accent=TEAL, title_size=20)
bullets(s, Inches(0.85), Inches(2.4), Inches(5.5), Inches(4.2), [
    ("Privacy-first DLP: ", "sensitive data blocked locally, never sent to the AI; checksums keep false alarms low."),
    ("Works offline: ", "chat, login security, Layer 1 DLP and monitoring need no internet."),
    ("Accountability: ", "watermarks, masked logs and a live dashboard make leaks traceable."),
], size=15, gap=14)
card(s, Inches(6.85), Inches(1.6), Inches(5.95), Inches(4.0), "⚠  Limitations", "", accent=RED, title_size=20)
bullets(s, Inches(7.1), Inches(2.4), Inches(5.5), Inches(4.2), [
    ("Screenshots: ", "a phone camera or OS screenshot can't be fully blocked."),
    ("Creative formats: ", "split numbers, images or other languages can slip past regex."),
    ("AI dependence: ", "needs the internet, may misjudge tone, and free-tier inputs may be used by Google."),
], size=15, gap=14)

# ================================================================== 16. FUTURE

s = new_slide("Future enhancements", "What's next", notes=(
    "Next steps: OCR to read sensitive data inside shared images; integration with Microsoft Active Directory for "
    "single sign-on and Microsoft Purview for central DLP policies; and a mobile app with tone checks in Hindi, "
    "Marathi and other languages."))
future = [
    ("🖼", "OCR scanning", "Detect card numbers and IDs inside shared images and documents.", TEAL),
    ("🏢", "Enterprise integration", "Active Directory / Entra ID single sign-on and Microsoft Purview DLP policies.",
     BLUE),
    ("📱", "Mobile + multilingual", "Android / iOS apps and tone checks in Hindi, Marathi and more.", AMBER),
]
for i, (icon, title, body, accent) in enumerate(future):
    card(s, Inches(0.6 + i * 4.15), Inches(1.9), Inches(3.9), Inches(3.0), title, body, accent=accent, icon=icon,
         body_size=16, title_size=19)

# ================================================================== 17. CONCLUSION

s = new_slide("Conclusion", "Summary", notes=(
    "To conclude: ShieldChat shows that internal chat can be fast and secure at the same time. Local DLP blocks "
    "sensitive data before it is shared, Gemini adds context-aware detection and polite wording without ever "
    "seeing raw sensitive values, and login security, anti-exfiltration and live monitoring complete the picture. "
    "It is a small model of how real enterprise tools like Microsoft Purview protect communication."))
box(s, Inches(0.6), Inches(1.7), Inches(12.2), Inches(2.0), MINT)
text(s, Inches(1.0), Inches(1.8), Inches(11.4), Inches(1.8),
     "ShieldChat shows that internal chat can be both fast and secure: sensitive data is stopped before it is "
     "shared, AI keeps communication professional without ever seeing raw sensitive values, and every incident is "
     "traceable.", size=20, color=TEAL_DARK, anchor=MSO_ANCHOR.MIDDLE, spacing=1.2)
points = [("🔐", "Secure login"), ("🛡", "2-layer DLP"), ("🤖", "Gemini AI"), ("🚫", "Anti-exfiltration"),
          ("📊", "Live monitoring")]
for i, (icon, label) in enumerate(points):
    x = Inches(0.6 + i * 2.48)
    box(s, x, Inches(4.2), Inches(2.25), Inches(1.8), GREY_BG)
    text(s, x, Inches(4.35), Inches(2.25), Inches(0.7), icon, size=30, align=PP_ALIGN.CENTER)
    text(s, x, Inches(5.15), Inches(2.25), Inches(0.5), label, size=16, bold=True, align=PP_ALIGN.CENTER,
         color=TEAL_DARK)

# ================================================================== 18. THANK YOU

_count += 1
s = prs.slides.add_slide(BLANK)
box(s, 0, 0, prs.slide_width, prs.slide_height, TEAL_DARK, shape=MSO_SHAPE.RECTANGLE)
box(s, Inches(-1.5), Inches(4.5), Inches(5), Inches(5), TEAL, shape=MSO_SHAPE.OVAL)
text(s, Inches(0), Inches(2.0), prs.slide_width, Inches(1.2), "Thank you", size=60, bold=True, color=WHITE,
     align=PP_ALIGN.CENTER)
text(s, Inches(0), Inches(3.25), prs.slide_width, Inches(0.8), "Questions?  ·  Live demo", size=26,
     color=RGBColor(0xC8, 0xF4, 0xEA), align=PP_ALIGN.CENTER)
text(s, Inches(0), Inches(4.6), prs.slide_width, Inches(1.2), [
    "Piyush Tiwatne (TH3313)  ·  Kedar Bhaskar (TH3314)",
    "Guide: Mrs Rajashree Khadke  ·  CDS, MIT ACSC  ·  2026-27",
], size=16, color=WHITE, align=PP_ALIGN.CENTER, spacing=1.4)
s.notes_slide.notes_text_frame.text = "Thank you. We are happy to take questions, and we can show the live demo now."

assert _count == TOTAL, _count
prs.core_properties.title = "ShieldChat"
prs.core_properties.author = "Piyush Tiwatne, Kedar Bhaskar"
prs.save(OUT)
print("Saved", OUT, "slides:", len(prs.slides))
