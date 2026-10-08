"""Draw the ShieldChat architecture diagram (architecture.png) with matplotlib."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

fig, ax = plt.subplots(figsize=(11, 6.2), dpi=200)
ax.set_xlim(0, 110); ax.set_ylim(-1, 64); ax.axis("off")

TEAL, GREEN, RED, BLUE, GREY, AMBER = "#075e54", "#d9fdd3", "#fdecea", "#e8f0fe", "#f0f2f5", "#fff4d6"

def box(x, y, w, h, title, sub, fill, edge=TEAL):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.6",
                                fc=fill, ec=edge, lw=1.6))
    ax.text(x + w / 2, y + h * 0.64, title, ha="center", va="center", fontsize=10.5, weight="bold", color="#111b21")
    ax.text(x + w / 2, y + h * 0.28, sub, ha="center", va="center", fontsize=8, color="#3b4a54", linespacing=1.3)

def arrow(x1, y1, x2, y2, label="", color=TEAL, lx=0, ly=1.6, style="-|>"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=1.6, mutation_scale=14))
    if label:
        ax.text((x1 + x2) / 2 + lx, (y1 + y2) / 2 + ly, label, ha="center", va="center", fontsize=8,
                color=color, weight="bold", bbox=dict(fc="white", ec="none", pad=0.6))

# Top row: the request path
box(1, 44, 17, 12, "User Browser", "Alice / Bob / Admin\n(Chrome, Edge)", GREY)
box(23, 44, 19, 12, "Frontend", "HTML · CSS · JavaScript\nchat.js, watermark, blur", GREEN)
box(47, 44, 21, 12, "Flask Backend", "+ Flask-SocketIO\nlogin, sessions, events", GREEN)
box(75, 44, 22, 12, "DLP Engine (local)", "dlp.py · regex + Luhn\n+ Verhoeff + masking", RED, edge="#d93025")

arrow(18.6, 50, 22.4, 50)
arrow(42.6, 50, 46.4, 50)
arrow(68.6, 50, 74.4, 50)

# Middle: decisions
box(75, 24, 22, 12, "Gemini API", "Layer 2: tone + hidden\nsensitive data (JSON)", BLUE, edge="#1a56c4")
arrow(86, 43.4, 86, 36.6, "only if clean", color="#1a56c4", lx=7.5, ly=0)

box(47, 24, 21, 12, "Response / Block", "send · DLP popup ·\ntone hint · masked send", AMBER, edge="#b07d00")
arrow(80, 43.4, 64, 36.6, "sensitive → BLOCK", color="#d93025", lx=-6, ly=1.2)
arrow(74.4, 30, 68.6, 30, color="#1a56c4")
arrow(47.2, 36.6, 37, 43.4, "result shown", color="#b07d00", lx=-5, ly=0)

# Bottom: storage and monitoring
box(47, 4, 21, 12, "SQLite", "users · messages ·\ndlp_incidents (masked)", GREY)
box(75, 4, 22, 12, "Admin Dashboard", "/admin (role check)\nlive incidents", GREEN)
arrow(57.5, 23.4, 57.5, 16.6, "store", ly=0, lx=4)
arrow(68.6, 10, 74.4, 10)

ax.text(1, 62.5, "ShieldChat: System Architecture", fontsize=13, weight="bold", color=TEAL)
ax.text(1, 30, "Raw sensitive data never\nreaches Gemini: Layer 1\nblocks it locally first.\n\nIf Gemini is down/slow (5 s),\nLayer 1 still enforces and\nthe message is sent\n(\"AI assistant unavailable\").",
        fontsize=8.3, color="#3b4a54", va="center", linespacing=1.35,
        bbox=dict(boxstyle="round,pad=0.8", fc="#ffffff", ec="#c9d1d6"))
plt.savefig(__file__.replace("make_diagram.py", "architecture.png"), bbox_inches="tight", facecolor="white")
print("saved")
