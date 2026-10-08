"""
Build ShieldChat_Mini_Project_Report.docx on top of report_template.docx.

Keeps the template's page setup, theme fonts, styles (Title, Heading 1/2, Normal)
and footer; replaces the body with the report content. The Table of Contents is
a real Word TOC field generated from the headings (update_toc.ps1 fills page numbers).
"""

import os

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEMPLATE = os.path.join(ROOT, "report_template.docx")
OUT = os.path.join(ROOT, "ShieldChat_Mini_Project_Report.docx")
DIAGRAM = os.path.join(HERE, "architecture.png")

TITLE = ("SHIELDCHAT: AI-POWERED SECURE ENTERPRISE CHAT APPLICATION WITH DATA LOSS "
         "PREVENTION USING PYTHON FLASK AND GOOGLE GEMINI API")

doc = Document(TEMPLATE)
body = doc.element.body

# ---- Clear the template body but keep the final section properties (page size, margins, footer).
sect_pr = body.find(qn("w:sectPr"))
for child in list(body):
    if child is not sect_pr:
        body.remove(child)


# ------------------------------------------------------------------ helpers

def para(text="", style="Normal", bold=False, italic=False, align=None, size=None, space_after=None):
    """Add a paragraph; **bold** segments are not parsed, keep it simple."""
    p = doc.add_paragraph(style=style)
    if text:
        r = p.add_run(text)
        r.bold = bold
        r.italic = italic
        if size:
            r.font.size = Pt(size)
    if align:
        p.alignment = align
    if space_after is not None:
        p.paragraph_format.space_after = Pt(space_after)
    return p


def rich(parts, style="Normal"):
    """Paragraph from [(text, bold)] pieces."""
    p = doc.add_paragraph(style=style)
    for text, bold in parts:
        p.add_run(text).bold = bold
    return p


def bullets(items, numbered=False):
    """Simple bullet/numbered list using the template's List Paragraph style."""
    for i, item in enumerate(items, 1):
        p = doc.add_paragraph(style="List Paragraph")
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.first_line_indent = Inches(-0.25)
        p.paragraph_format.left_indent = Inches(0.5)
        marker = f"{i}.\t" if numbered else "•\t"
        if isinstance(item, tuple):
            p.add_run(marker + item[0]).bold = True
            p.add_run(item[1])
        else:
            p.add_run(marker + item)


def heading(text, level=1):
    return doc.add_heading(text, level=level)


def page_break():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def shade(element, fill):
    """Give a paragraph or table cell a background colour."""
    pr = element.get_or_add_pPr() if hasattr(element, "get_or_add_pPr") else element.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    pr.append(shd)


def code(snippet, caption):
    """Monospace code block (Consolas 9 pt, light grey background) with a caption."""
    lines = snippet.strip("\n").split("\n")
    for i, line in enumerate(lines):
        p = doc.add_paragraph(style="Normal")
        pf = p.paragraph_format
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)
        pf.line_spacing = 1.0
        pf.left_indent = Inches(0.15)
        pf.keep_with_next = True   # do not split a snippet across pages
        r = p.add_run(line if line else " ")
        r.font.name = "Consolas"
        r._element.rPr.rFonts.set(qn("w:hAnsi"), "Consolas")
        r._element.rPr.rFonts.set(qn("w:cs"), "Consolas")
        r.font.size = Pt(8.5)
        shade(p._p, "F2F4F5")
    cap = para(caption, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=9)
    cap.paragraph_format.space_before = Pt(4)


def set_borders(table):
    """Thin grey borders on every cell (the template has no 'Table Grid' style)."""
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:color"), "A6A6A6")
        borders.append(el)
    tbl_pr.append(borders)


def table(rows, widths=None, header=True):
    """Bordered table; first row shaded as a header."""
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_borders(t)
    for r_i, row in enumerate(rows):
        for c_i, value in enumerate(row):
            cell = t.cell(r_i, c_i)
            cell.text = ""
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(1)
            run = p.add_run(value)
            run.font.size = Pt(9.5)
            if header and r_i == 0:
                run.bold = True
                shade(cell._tc, "DCEFEA")
            if widths:
                cell.width = widths[c_i]
            if r_i < len(rows) - 1:
                p.paragraph_format.keep_with_next = True   # keep the table on one page
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def caption(text):
    para(text, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=9)


def screenshot_placeholder(label, cap):
    """A bordered empty box with a bracketed label, to be replaced by a real screenshot."""
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_borders(t)
    cell = t.cell(0, 0)
    cell.width = Inches(5.6)
    tr_pr = t.rows[0]._tr.get_or_add_trPr()
    h = OxmlElement("w:trHeight")
    h.set(qn("w:val"), str(int(1.55 * 1440)))
    h.set(qn("w:hRule"), "atLeast")
    tr_pr.append(h)
    shade(cell._tc, "F7F9FA")
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(42)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(label)
    r.bold = True
    r.font.color.rgb = RGBColor(0x59, 0x63, 0x6B)
    caption(cap)


def toc_field():
    """Insert a Word TOC field built from Heading 1-2 (page numbers filled by Word)."""
    p = doc.add_paragraph()
    run = p.add_run()
    for tag, text in (("begin", None), (None, ' TOC \\o "1-2" \\h \\z \\u '), ("separate", None)):
        if tag:
            fc = OxmlElement("w:fldChar")
            fc.set(qn("w:fldCharType"), tag)
            run._r.append(fc)
        else:
            instr = OxmlElement("w:instrText")
            instr.set(qn("xml:space"), "preserve")
            instr.text = text
            run._r.append(instr)
    p.add_run("Right-click here and choose 'Update Field' to build the table of contents.").italic = True
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    p.add_run()._r.append(end)


# ================================================================== TITLE PAGE

for _ in range(3):
    para()
t = para(TITLE, style="Title", align=WD_ALIGN_PARAGRAPH.CENTER)
for r in t.runs:
    r.font.size = Pt(22)
para()
para("Mini Project Report", align=WD_ALIGN_PARAGRAPH.CENTER, size=14, bold=True)
para()
for label, value in [
    ("Student Names", "Piyush Tiwatne, Kedar Bhaskar"),
    ("Roll Nos", "TH3313, TH3314"),
    ("Guide", "Mrs Rajashree Khadke"),
    ("Department", "CDS"),
    ("College", "MIT ACSC"),
    ("Academic Year", "2026-27"),
]:
    p = rich([(f"{label}: ", True), (value, False)])
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(4)
page_break()

# ================================================================== TOC

para("Table of Contents", style="Title", align=WD_ALIGN_PARAGRAPH.LEFT)
toc_field()
page_break()

# ================================================================== 1. INTRODUCTION

heading("1. Introduction", 1)
heading("1.1 Enterprise Chat Applications", 2)
para("An enterprise chat application is an instant-messaging system used only inside an organisation, "
     "like WhatsApp but for employees. Tools such as Microsoft Teams and Slack have replaced much internal "
     "email because they are fast and informal. That speed is also the risk: employees paste information "
     "into chat without thinking about where it ends up.")
heading("1.2 The Data-Leak Problem", 2)
para("Data Loss Prevention (DLP) means stopping sensitive information from being shared with the wrong people. "
     "In a typical incident an employee pastes a customer's credit-card number, Aadhaar number, PAN or bank "
     "details into a chat. The data is now stored on chat servers, visible to everyone in the conversation and "
     "easy to copy outside the company. In India this can breach the Digital Personal Data Protection (DPDP) "
     "Act 2023, RBI card-data rules and the PCI-DSS standard. Leaks also happen through copy-paste, printing, "
     "screen-sharing and screenshots.")
heading("1.3 How AI Is Used", 2)
para("ShieldChat uses two layers. Layer 1 is a local rule engine (regular expressions plus the Luhn and Verhoeff "
     "checksums) that blocks well-structured identifiers on the server, so the raw value never leaves the "
     "organisation. Only messages that pass Layer 1 are sent to the Google Gemini API, which acts as Layer 2. "
     "In a single call Gemini checks for sensitive data that patterns cannot see (numbers written in words, "
     "passwords, salary details) and judges the tone, suggesting a polite rewrite for rude or aggressive messages.")
heading("1.4 Objective", 2)
para("To build a secure, real-time internal chat application that blocks sensitive financial and identity data "
     "before it is shared, deters copying of chat content, and uses Google Gemini AI to detect hidden sensitive "
     "data and improve the professionalism of messages.")

# ================================================================== 2. SYSTEM REQUIREMENTS

heading("2. System Requirements", 1)
heading("2.1 Hardware Requirements", 2)
bullets(["Processor: any dual-core CPU (Intel Core i3 / AMD Ryzen 3 or better)",
         "RAM: 4 GB minimum",
         "Storage: about 500 MB free (Python, libraries and the SQLite database)",
         "Internet connection: needed only for the Gemini AI features"])
heading("2.2 Software Requirements", 2)
bullets(["Operating system: Windows 10 / 11",
         "Python 3.10 or later",
         "Code editor: Visual Studio Code",
         "Web browser: Google Chrome (plus a second browser such as Microsoft Edge for the admin view)"])
heading("2.3 Libraries and Frameworks", 2)
table([
    ["Library / Technology", "Purpose"],
    ["HTML, CSS, JavaScript", "Front-end user interface (no framework, no build step)"],
    ["Flask", "Python web framework: pages, login, JSON APIs"],
    ["Flask-SocketIO (threading mode)", "Real-time two-way messaging over WebSockets"],
    ["Socket.IO JavaScript client", "Browser side of the real-time connection"],
    ["SQLite (sqlite3)", "Lightweight database for users, messages and incidents"],
    ["Werkzeug security", "Salted scrypt password hashing"],
    ["python-dotenv", "Loads secrets (API key, SECRET_KEY) from the .env file"],
    ["google-genai", "Official Google Gemini Python SDK"],
    ["pytest", "Automated testing of the DLP engine and server"],
], widths=[Inches(2.3), Inches(4.0)])
heading("2.4 AI API", 2)
para("Google Gemini API, accessed with the official google-genai SDK. The model name is read from the .env file "
     "(GEMINI_MODEL). The default is gemini-3.5-flash-lite: a stable model with a free tier, designed for fast, "
     "high-volume tasks, which suits a short per-message check with a 5-second timeout.")

# ================================================================== 3. SYSTEM DESIGN

heading("3. System Design", 1)
heading("3.1 Architecture", 2)
para("The system follows a client-server design. Browsers connect to a single Flask server, which runs every "
     "message through the local DLP engine before optionally consulting Gemini, then stores the result in "
     "SQLite and notifies the Security Admin dashboard in real time.")
doc.add_picture(DIAGRAM, width=Inches(6.3))
doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
caption("Figure 1: ShieldChat system architecture")
heading("3.2 Message Flow", 2)
bullets([
    "The user types a message and presses Send; the browser emits it to the server over Socket.IO.",
    "The server identifies the sender from the signed session (never from the browser's data).",
    "Layer 1 DLP (dlp.py) scans the text locally. If a card, Aadhaar, PAN, IFSC or bank account is found, "
    "the message is blocked, a masked incident is logged and the user sees a red policy popup with the "
    "options Edit message or Send masked version. The raw text is never sent to Gemini.",
    "If Layer 1 is clean, Gemini is called once and returns JSON. If sensitive data is detected, the message "
    "is blocked (Layer 2). If the tone is unprofessional, a yellow hint with a polite suggestion is shown.",
    "If the message is clean and professional, it is saved in SQLite and delivered instantly to the receiver.",
    "If Gemini fails, times out (5 s) or has no key, the message is still sent and the user sees "
    "\"AI assistant unavailable\"; Layer 1 has already been enforced.",
    "Every incident is pushed live to the admin dashboard.",
], numbered=True)
heading("3.3 Database Design", 2)
table([
    ["Table", "Main columns", "Purpose"],
    ["users", "id, email, name, password_hash, role, failed_attempts, locked_until",
     "Employee accounts, roles and lockout state"],
    ["messages", "id, sender_id, receiver_id, text, created_at", "Chat history"],
    ["dlp_incidents", "id, user_email, type, details, created_at",
     "Security incidents with masked values only"],
], widths=[Inches(1.2), Inches(3.0), Inches(2.1)])

# ================================================================== 4. IMPLEMENTATION

heading("4. Implementation", 1)
heading("4.1 Frontend", 2)
para("The interface has three pages: login, chat and admin dashboard. They are built with plain HTML, CSS and "
     "JavaScript in a WhatsApp-like green and teal theme. The chat page shows contacts with online indicators "
     "on the left and message bubbles with timestamps on the right. chat.js handles the Socket.IO connection, "
     "the DLP popup, the tone hint and the anti-exfiltration controls. All user text is inserted with "
     "textContent rather than innerHTML, which prevents cross-site scripting (XSS).")
heading("4.2 Backend", 2)
para("app.py contains the Flask routes and Socket.IO event handlers. Login security includes salted scrypt "
     "password hashing, an @shieldcorp.com domain restriction, lockout for 2 minutes after 5 failed attempts, "
     "and HttpOnly, SameSite session cookies signed with a secret key from .env. Every SQL statement uses "
     "parameterised queries to prevent SQL injection. The /admin route checks the role on the server and "
     "returns HTTP 403 for non-admins.")
heading("4.3 DLP Engine", 2)
para("dlp.py detects card numbers (13-19 digits that pass the Luhn checksum, with the network identified "
     "from the prefix and a nearby expiry date included), Aadhaar numbers (12 digits starting 2-9 that pass "
     "the Verhoeff checksum), PAN, IFSC, and bank account numbers. Bank account numbers are flagged only when "
     "banking keywords or an IFSC are nearby, so phone numbers and order IDs are not blocked. Each finding is "
     "returned with a masked value that keeps only the last 4 digits; only masked values are ever stored.")
heading("4.4 AI Integration", 2)
para("ai_assistant.py makes one call to client.models.generate_content() per clean message. The prompt "
     "places the message between markers and asks for strict JSON. The SDK's structured-output mode "
     "(response_mime_type=\"application/json\" plus a JSON schema) guarantees the shape: is_unprofessional, "
     "tone, suggestion, sensitive_detected and sensitive_reason. A safety parser strips code fences and "
     "fills defaults. The call has a hard 5-second timeout. If there is an error, a timeout or no API key, "
     "the function returns None and the server fails open for tone, while Layer 1 DLP has already failed "
     "closed. The model is told never to repeat sensitive values in its reason.")
heading("4.5 Anti-Exfiltration and Monitoring", 2)
para("Text selection, copy, cut, right-click and drag are disabled in the message area; each attempt shows a "
     "toast and is logged as COPY_ATTEMPT. Pastes longer than 200 characters are allowed but logged as "
     "BULK_PASTE (size only). A faint diagonal watermark shows the user's email and the current time, the chat "
     "blurs when the window loses focus, and printing produces a blank page. These are deterrents and "
     "traceability controls: a phone camera or an operating-system screenshot cannot be fully prevented by a "
     "web application.")
heading("4.6 Key Code Snippets", 2)
code('''
def luhn_valid(number: str) -> bool:
    digits = [int(d) for d in number if d.isdigit()]
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:          # double every second digit from the right
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0      # valid card numbers end in 0
''', "Snippet 1: Luhn checksum (dlp.py)")
code('''
findings = dlp.scan(text)                     # Layer 1: local, always runs
if findings:
    public = dlp.public_findings(findings)
    for f in public:                          # log MASKED values only
        log_incident(email, f["type"], f"{f['label']}: {f['masked_value']}")
    masked = dlp.mask_text(text, findings)
    # raw text is NOT sent to Gemini
    return {"status": "blocked", "layer": 1, "findings": public, "masked_text": masked}
''', "Snippet 2: DLP check in the send handler (app.py)")
code('''
response = client.models.generate_content(
    model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
    contents=PROMPT_TEMPLATE.format(message=message),
    config=types.GenerateContentConfig(
        response_mime_type="application/json",   # JSON mode
        response_json_schema=RESPONSE_SCHEMA,     # exact shape we want
        temperature=0.2,
    ),
)
raw = future.result(timeout=5)   # hard 5 s limit; on failure -> None (fail-open)
''', "Snippet 3: Gemini call with structured JSON output (ai_assistant.py, simplified)")
code('''
@socketio.on("send_message")
def on_send_message(data):
    sender = session["user_id"]                 # identity from the signed session
    ...                                          # Layer 1 DLP, then Layer 2 AI
    conn.execute("INSERT INTO messages (sender_id, receiver_id, text, created_at) "
                 "VALUES (?, ?, ?, ?)", (sender, receiver, text, created))
    socketio.emit("new_message", msg, to=f"user_{receiver}")   # real-time delivery
''', "Snippet 4: Socket.IO send handler (app.py, simplified)")

# ================================================================== 5. RESULTS

heading("5. Results", 1)
para("The application was tested with two employees (Alice and Bob) chatting from two browser windows and a "
     "Security Admin watching the dashboard from a third.")
screenshot_placeholder("[Screenshot 1: Login page]", "Figure 2: ShieldCorp login page with domain restriction")
screenshot_placeholder("[Screenshot 2: Real-time chat between Alice and Bob]",
                       "Figure 3: Real-time chat with online indicators and timestamps")
screenshot_placeholder("[Screenshot 3: DLP block popup for credit card]",
                       "Figure 4: Layer 1 DLP blocks a Visa card number and offers a masked version")
screenshot_placeholder("[Screenshot 4: AI tone suggestion]",
                       "Figure 5: Gemini suggests a polite rewrite of a rude message")
screenshot_placeholder("[Screenshot 5: Watermark and copy block]",
                       "Figure 6: User watermark and the \"Copying enterprise data is restricted\" toast")
screenshot_placeholder("[Screenshot 6: Admin dashboard]",
                       "Figure 7: Security Admin dashboard with live, masked incidents")
heading("5.1 Sample Conversation", 2)
table([
    ["Sender", "Message typed", "Result"],
    ["Alice", "Hi Bob, can you join the 3 pm project call?", "Delivered"],
    ["Bob", "Sure Alice, see you then.", "Delivered"],
    ["Alice", "Hi Bob, here is the client card: Visa: 4485 3647 3952 7352 Expires: 2/2009",
     "Blocked (Layer 1: Visa card + expiry). Masked version sent: "
     "\"…Visa: XXXX XXXX XXXX 7352 Expires: XX/XX\""],
    ["Alice", "My Aadhaar is 2345 6789 0124 and PAN is abcde1234f (fake test values)",
     "Blocked (Layer 1: Aadhaar XXXX XXXX 0124, PAN XXXXX1234X)"],
    ["Alice", "The client's card is four four eight five three six four seven …",
     "Blocked (Layer 2: Gemini detected a card number written in words)"],
    ["Alice", "Send me the report now, why are you always so slow?",
     "Not blocked; tone hint shown with a polite suggestion, which was sent instead"],
], widths=[Inches(0.7), Inches(3.0), Inches(2.6)])
heading("5.2 Testing", 2)
para("28 automated pytest tests pass. They cover valid and invalid cards (Luhn), the Visa sample, a fake "
     "Aadhaar generated with the Verhoeff algorithm, PAN, IFSC, bank accounts with and without context, a "
     "phone number that must not be flagged, the raw card never reaching the AI, the Gemini timeout "
     "fallback, and HTTP 403 for non-admin users. All test data is fake.")

# ================================================================== 6. ADVANTAGES & LIMITATIONS

heading("6. Advantages and Limitations", 1)
heading("6.1 Advantages", 2)
bullets([
    ("Privacy-first, layered DLP: ", "sensitive identifiers are blocked locally and never sent to the AI; "
     "checksums keep false alarms low."),
    ("Works offline: ", "Layer 1 DLP, chat, login security and monitoring work without internet; only the AI "
     "features need it."),
    ("Accountability: ", "watermarks, masked incident logs and a live admin dashboard make leaks traceable "
     "while improving the tone of communication."),
])
heading("6.2 Limitations", 2)
bullets([
    ("Screenshots cannot be fully blocked: ", "a phone camera or OS screenshot can still capture the screen; "
     "copy blocking, blur and watermark are deterrents."),
    ("Regex can miss creative formats: ", "numbers split across messages, inside images or in other "
     "languages may escape Layer 1."),
    ("AI depends on the internet: ", "Gemini needs connectivity, may misjudge tone or context, and on the free "
     "tier Google may use inputs to improve its products."),
])

# ================================================================== 7. FUTURE ENHANCEMENTS

heading("7. Future Enhancements", 1)
bullets([
    ("OCR scanning: ", "detect sensitive data inside shared images and documents."),
    ("Enterprise integration: ", "Microsoft Active Directory / Entra ID single sign-on and Microsoft Purview DLP policies."),
    ("Mobile app and multilingual tone check: ", "Android/iOS clients and support for Hindi, Marathi and other languages."),
])

# ================================================================== 8. CONCLUSION

heading("8. Conclusion", 1)
para("ShieldChat shows that an internal chat application can be fast and secure at the same time. A local "
     "pattern-and-checksum DLP engine blocks card, Aadhaar, PAN and bank details before they are shared, "
     "while Google Gemini adds context-aware detection and professional tone suggestions without ever seeing "
     "the raw sensitive values. Combined with login security, anti-exfiltration deterrents and a live "
     "security dashboard, the project models how real enterprises protect communication.")

# ================================================================== 9. REFERENCES

heading("9. References", 1)
refs = [
    "Flask Documentation, Pallets Projects. https://flask.palletsprojects.com/",
    "Flask-SocketIO Documentation, M. Grinberg. https://flask-socketio.readthedocs.io/",
    "Google Gemini API Documentation. https://ai.google.dev/gemini-api/docs",
    "Google Gen AI Python SDK (google-genai). https://googleapis.github.io/python-genai/",
    "Gemini API Additional Terms of Service. https://ai.google.dev/gemini-api/terms",
    "Luhn algorithm. https://en.wikipedia.org/wiki/Luhn_algorithm",
    "Verhoeff algorithm. https://en.wikipedia.org/wiki/Verhoeff_algorithm",
    "Unique Identification Authority of India (UIDAI), Aadhaar. https://uidai.gov.in/",
    "Income Tax Department, Government of India (PAN). https://www.incometax.gov.in/",
    "OWASP Top Ten. https://owasp.org/www-project-top-ten/",
    "OWASP Cheat Sheet Series (XSS, SQL injection, session management). https://cheatsheetseries.owasp.org/",
    "SQLite Documentation. https://www.sqlite.org/docs.html",
]
bullets(refs, numbered=True)

doc.core_properties.title = "ShieldChat Mini Project Report"
doc.core_properties.author = "Piyush Tiwatne, Kedar Bhaskar"
doc.save(OUT)
print("Saved", OUT)
