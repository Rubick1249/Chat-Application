// chat.js - front-end logic for the ShieldChat chat screen.
//
// SECURITY NOTE (XSS): every piece of user-written text is put on the page with
// element.textContent, NEVER innerHTML. textContent treats the text as plain
// characters, so a message like <script>...</script> is shown, not executed.
//
// IMPORTANT: the real DLP decision is made on the SERVER (app.py + dlp.py).
// This file only shows the results. Anything enforced only in the browser
// could be bypassed by a user with developer tools.

const socket = io();                 // live connection to the Flask-SocketIO server
let activePeer = null;               // the contact we are chatting with
const contacts = {};                 // id -> contact object
let pending = null;                  // message waiting for a decision (DLP popup / tone hint)

// Blur the chat when this window loses focus (shoulder-surfing / screen-share protection).
// Tip: set to false if you want to watch two windows side by side during the demo.
const BLUR_ON_FOCUS_LOSS = true;
const BULK_PASTE_LIMIT = 200;        // pastes longer than this are logged

const $ = (id) => document.getElementById(id);
const $contacts = $("contacts");
const $messages = $("messages");
const $input = $("msgInput");
const $send = $("sendBtn");
const $composer = $("composer");

/** Turn "2026-10-05T14:30:00" into "14:30". */
function shortTime(iso) {
  return iso ? iso.slice(11, 16) : "";
}

/** Show a short dark pop-up message at the bottom of the screen. */
let toastTimer = null;
function toast(text) {
  const t = $("toast");
  t.textContent = text;
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.hidden = true; }, 2600);
}

/** Show (or hide, with null) the small grey status line above the input. */
function setStatus(text, checking = false) {
  const s = $("statusLine");
  s.hidden = !text;
  s.textContent = text || "";
  s.classList.toggle("checking", checking);
}

// =====================================================================
// Phase 1: contacts, history, real-time messages
// =====================================================================

/** Build the left-hand contact list from the server. */
async function loadContacts() {
  const res = await fetch("/api/contacts");
  const list = await res.json();
  $contacts.replaceChildren();
  list.forEach((c) => {
    contacts[c.id] = c;
    const li = document.createElement("li");
    li.className = "contact";
    li.dataset.id = c.id;

    const av = document.createElement("div");
    av.className = "avatar";
    av.textContent = c.name[0];
    const dot = document.createElement("span");
    dot.className = "dot" + (c.online ? " on" : "");
    av.appendChild(dot);

    const info = document.createElement("div");
    const nm = document.createElement("div");
    nm.className = "contact-name";
    nm.textContent = c.name;
    const em = document.createElement("div");
    em.className = "contact-email";
    em.textContent = c.email;
    info.append(nm, em);

    li.append(av, info);
    li.addEventListener("click", () => openChat(c.id));
    $contacts.appendChild(li);
  });
}

/** Show "online"/"offline" under the open contact's name. */
function renderPeerStatus() {
  if (!activePeer) return;
  $("peerStatus").textContent = contacts[activePeer].online ? "online" : "offline";
}

/** Open a conversation: highlight the contact and load the history. */
async function openChat(peerId) {
  activePeer = peerId;
  hideToneHint();
  document.querySelectorAll(".contact").forEach((li) => {
    li.classList.toggle("active", Number(li.dataset.id) === peerId);
  });
  $("peerName").textContent = contacts[peerId].name;
  $("peerAvatar").textContent = contacts[peerId].name[0];
  renderPeerStatus();
  $input.disabled = false;
  $send.disabled = false;
  $input.focus();

  const res = await fetch(`/api/messages/${peerId}`);
  const history = await res.json();
  $messages.replaceChildren();
  history.forEach(addBubble);
}

/** Draw one message bubble (right side if I sent it, left if received). */
function addBubble(msg) {
  const div = document.createElement("div");
  div.className = "bubble " + (msg.sender_id === ME.id ? "out" : "in");
  const body = document.createElement("span");
  body.textContent = msg.text;               // textContent = XSS-safe
  const time = document.createElement("span");
  time.className = "time";
  time.textContent = shortTime(msg.created_at);
  div.append(body, time);
  $messages.appendChild(div);
  $messages.scrollTop = $messages.scrollHeight;
}

socket.on("new_message", (msg) => {
  // Only draw it if it belongs to the conversation that is open right now.
  const other = msg.sender_id === ME.id ? msg.receiver_id : msg.sender_id;
  if (other === activePeer) addBubble(msg);
});

socket.on("presence", ({ user_id, online }) => {
  if (!contacts[user_id]) return;
  contacts[user_id].online = online;
  const dot = document.querySelector(`.contact[data-id="${user_id}"] .dot`);
  if (dot) dot.classList.toggle("on", online);
  renderPeerStatus();
});

// =====================================================================
// Sending: server runs DLP Layer 1 + AI Layer 2 and answers with a status
// =====================================================================

/** Send text to the server and react to its verdict: sent / blocked / tone. */
function sendText(text) {
  if (!text || !activePeer) return;
  $input.disabled = true;
  $send.disabled = true;
  setStatus("Checking message…", true);

  socket.timeout(15000).emit("send_message", { to: activePeer, text }, (err, reply) => {
    $input.disabled = false;
    $send.disabled = false;
    setStatus(null);

    if (err || !reply) {
      toast("Server did not respond. Message not sent.");
      return;
    }
    if (reply.status === "sent") {
      $input.value = "";
      hideToneHint();
      if (reply.ai_unavailable) setStatus("AI assistant unavailable");  // small grey note
    } else if (reply.status === "blocked") {
      $input.value = "";   // do not leave the sensitive value on screen
      showDlpPopup(text, reply);
    } else if (reply.status === "tone") {
      showToneHint(reply);
    } else {
      toast(reply.error || "Message could not be sent.");
    }
    $input.focus();
  });
}

$composer.addEventListener("submit", (e) => {
  e.preventDefault();
  hideToneHint();
  sendText($input.value.trim());
});

// =====================================================================
// Phase 3: DLP policy-violation popup
// =====================================================================

const FINANCIAL = ["CARD", "BANK_ACCOUNT", "IFSC"];
const IDENTITY = ["AADHAAR", "PAN"];

/** Show the red popup listing what was found (masked values only). */
function showDlpPopup(originalText, reply) {
  pending = { original: originalText, masked: reply.masked_text };
  const types = reply.findings.map((f) => f.type);
  const labels = [...new Set(reply.findings.map((f) => f.label))].join(", ");

  let rule = "Sharing confidential or personal information in chat is not allowed.";
  if (types.some((t) => FINANCIAL.includes(t))) rule = "Sharing financial data in chat is not allowed.";
  else if (types.some((t) => IDENTITY.includes(t))) rule = "Sharing government ID numbers in chat is not allowed.";

  $("dlpText").textContent = `🛡 ShieldCorp DLP Policy: This message contains ${labels}. ${rule}`;

  const ul = $("dlpFindings");
  ul.replaceChildren();
  reply.findings.forEach((f) => {
    const li = document.createElement("li");
    const label = document.createElement("div");
    label.className = "f-label";
    label.textContent = f.label + ": ";
    const value = document.createElement("span");
    value.className = "f-value";
    value.textContent = f.masked_value;
    label.appendChild(value);
    const reason = document.createElement("div");
    reason.className = "f-reason";
    reason.textContent = (reply.layer === 2 ? "AI Layer 2: " : "Layer 1: ") + f.reason;
    li.append(label, reason);
    ul.appendChild(li);
  });

  // An AI (Layer 2) finding has no exact position, so we cannot offer a masked version.
  $("dlpSendMasked").hidden = !reply.masked_text;
  $("dlpModal").hidden = false;
}

function closeDlpPopup() {
  $("dlpModal").hidden = true;
}

$("dlpEdit").addEventListener("click", () => {
  closeDlpPopup();
  $input.value = pending ? pending.original : $input.value;  // back to the box to fix it
  $input.focus();
});

$("dlpSendMasked").addEventListener("click", () => {
  closeDlpPopup();
  if (pending && pending.masked) {
    $input.value = "";
    sendText(pending.masked);  // the server re-checks it, so this cannot be abused
  }
});

// =====================================================================
// Phase 4: AI tone hint (yellow card, never blocks)
// =====================================================================

/** Show the polite-rewrite suggestion above the input box. */
function showToneHint(reply) {
  pending = { original: reply.original, suggestion: reply.suggestion };
  $("toneSuggestion").textContent = reply.suggestion;   // AI text is also untrusted -> textContent
  $("toneHint").hidden = false;
}

function hideToneHint() {
  $("toneHint").hidden = true;
}

$("useSuggestion").addEventListener("click", () => {
  hideToneHint();
  $input.value = "";
  sendText(pending.suggestion);
});

$("sendOriginal").addEventListener("click", () => {
  hideToneHint();
  $input.value = "";
  sendText(pending.original);
});

$("editTone").addEventListener("click", () => {
  hideToneHint();
  $input.value = pending.original;
  $input.focus();
});

// =====================================================================
// Phase 5: anti-exfiltration controls
// HONESTY NOTE: these are DETERRENTS and TRACEABILITY controls, not a
// guarantee. A phone camera, an OS screenshot tool, or a user who opens
// developer tools can still capture what is on screen. Their value is:
// (1) stopping casual/accidental copying, (2) logging attempts for the
// security team, and (3) making any leaked screenshot traceable to a person.
// =====================================================================

/** Tell the server about a copy attempt or bulk paste so it is logged. */
function reportIncident(type, extra = {}) {
  socket.emit("client_incident", { type, ...extra });
}

/** Block copy/cut of chat content, except inside the user's own input box. */
function blockCopy(e) {
  if (e.target === $input) return;   // copying your own draft is fine
  e.preventDefault();
  toast("Copying enterprise data is restricted");
  reportIncident("COPY_ATTEMPT");
}
document.addEventListener("copy", blockCopy);
document.addEventListener("cut", blockCopy);

// No right-click menu and no dragging text out of the message area.
$messages.addEventListener("contextmenu", (e) => {
  e.preventDefault();
  toast("Copying enterprise data is restricted");
  reportIncident("COPY_ATTEMPT");
});
$messages.addEventListener("dragstart", (e) => e.preventDefault());

// Large pastes are allowed but logged: dumping a big block of text (e.g. a
// customer list) into chat is a typical way data leaks. We log only the size.
$input.addEventListener("paste", (e) => {
  const pasted = (e.clipboardData || window.clipboardData).getData("text") || "";
  if (pasted.length > BULK_PASTE_LIMIT) {
    reportIncident("BULK_PASTE", { length: pasted.length });
    toast(`Large paste (${pasted.length} characters) has been logged`);
  }
});

// Printing: CSS (@media print) prints a blank page; here we also tell the user.
window.addEventListener("beforeprint", () => toast("Printing is disabled"));
document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "p") {
    e.preventDefault();
    toast("Printing is disabled");
  }
});

/** Draw the faint diagonal watermark: my email + current date/time, repeated. */
function drawWatermark() {
  const stamp = `${ME.email} · ${new Date().toLocaleString()}`;
  // Escape characters that are special in SVG/XML before putting text inside it.
  const safe = stamp.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" width="360" height="200">` +
    `<text x="10" y="120" transform="rotate(-25 180 100)" font-family="Segoe UI, Arial" ` +
    `font-size="14" fill="#000">${safe}</text></svg>`;
  $("watermark").style.backgroundImage = `url("data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}")`;
}
drawWatermark();
setInterval(drawWatermark, 30000);  // keep the time current

/** Blur the chat when the window is hidden or loses focus; un-blur on return. */
function setPrivacy(on) {
  $("app").classList.toggle("privacy", on);
  $("privacyCover").hidden = !on;
}
document.addEventListener("visibilitychange", () => setPrivacy(document.hidden));
if (BLUR_ON_FOCUS_LOSS) {
  window.addEventListener("blur", () => setPrivacy(true));
  window.addEventListener("focus", () => setPrivacy(false));
}
$("privacyCover").addEventListener("click", () => setPrivacy(false));

loadContacts();
