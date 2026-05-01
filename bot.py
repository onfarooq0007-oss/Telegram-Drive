# telegram_drive_bot_pro_ultra.py
# FIXED + nest_asyncio support for OpenClaw/Ubuntu/Any platform

import os
import sqlite3
import mimetypes
import asyncio
import threading
from datetime import datetime

import requests
import nest_asyncio   # ← NEW: Fixes "event loop already running"

from flask import (
    Flask,
    request,
    redirect,
    url_for,
    render_template_string,
    jsonify,
    abort,
)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Apply nest_asyncio immediately (fixes OpenClaw / any pre-existing loop)
nest_asyncio.apply()

# =====================================================
# CONFIG
# =====================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", -1001234567890))
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000")
DB_NAME = "drive_pro.db"

if not BOT_TOKEN:
    raise SystemExit("❌ Error: Set BOT_TOKEN environment variable!")

# =====================================================
# DATABASE (same as before)
# =====================================================

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER UNIQUE,
    username TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS files(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER,
    tg_msg_id INTEGER,
    file_id TEXT,
    name TEXT,
    category TEXT,
    mime TEXT,
    size INTEGER,
    favorite INTEGER DEFAULT 0,
    created_at TEXT
);
"""

def db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

with db() as conn:
    conn.executescript(CREATE_TABLES)

# Migration for old DBs
with db() as conn:
    try:
        conn.execute("ALTER TABLE files ADD COLUMN file_id TEXT")
        print("✅ Added file_id column (migration done)")
    except sqlite3.OperationalError:
        pass

# =====================================================
# FLASK WEB UI (unchanged)
# =====================================================

app = Flask(__name__)

HTML = """<!doctype html>
<html>
<head>
<title>Drive PRO ULTRA</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{font-family:Arial;background:#f1f3f4;margin:0;}
.top{background:white;padding:15px;box-shadow:0 1px 5px rgba(0,0,0,.08);}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:15px;padding:20px;}
.card{background:white;border-radius:16px;padding:15px;box-shadow:0 1px 4px rgba(0,0,0,.08);}
a{text-decoration:none;color:#1a73e8;}
small{color:#777;}
</style>
</head>
<body>
<div class="top">
<h2>My Drive</h2>
<a href="/">All</a> |
<a href="/?cat=video">Videos</a> |
<a href="/?cat=audio">Audio</a> |
<a href="/?cat=document">Documents</a> |
<a href="/?cat=other">Other</a>
</div>
<div class="grid">
{% for f in files %}
<div class="card">
<b>{{f['name']}}</b><br>
<small>{{f['category']}} | {{f['size']}} bytes</small><br><br>
{% if f['category'] == 'video' %}
<video controls width="100%"><source src="/stream/{{f['id']}}"></video>
{% elif f['category'] == 'audio' %}
<audio controls style="width:100%"><source src="/stream/{{f['id']}}"></audio>
{% endif %}
<br><br>
<a href="/download/{{f['id']}}">Download</a> |
<a href="/favorite/{{f['id']}}">Favorite</a>
</div>
{% endfor %}
</div>
</body>
</html>
"""

@app.route("/")
def index():
    cat = request.args.get("cat")
    with db() as conn:
        if cat:
            files = conn.execute("SELECT * FROM files WHERE category=? ORDER BY id DESC", (cat,)).fetchall()
        else:
            files = conn.execute("SELECT * FROM files ORDER BY id DESC").fetchall()
    return render_template_string(HTML, files=files)

@app.route("/favorite/<int:file_id>")
def favorite(file_id):
    with db() as conn:
        conn.execute("UPDATE files SET favorite=1 WHERE id=?", (file_id,))
    return redirect("/")

def get_telegram_file_url(tg_file_id: str):
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
            params={"file_id": tg_file_id}, timeout=10
        )
        r.raise_for_status()
        data = r.json()
        if data.get("ok"):
            return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{data['result']['file_path']}"
    except Exception as e:
        print(f"Error getting file URL: {e}")
    return None

@app.route("/telegram_file/<int:file_id>")
@app.route("/download/<int:file_id>")
@app.route("/stream/<int:file_id>")
def telegram_file(file_id):
    with db() as conn:
        row = conn.execute("SELECT file_id FROM files WHERE id=?", (file_id,)).fetchone()
    if not row or not row["file_id"]:
        abort(404, "File not found")
    url = get_telegram_file_url(row["file_id"])
    if url:
        return redirect(url)
    abort(503, "Could not generate Telegram file URL")

# =====================================================
# TELEGRAM BOT (same robust logic)
# =====================================================

async def register_user(user):
    with db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users(tg_id, username, created_at) VALUES(?,?,?)",
            (user.id, user.username, datetime.utcnow().isoformat()),
        )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await register_user(update.effective_user)
    kb = [[InlineKeyboardButton("Open Drive", url=BASE_URL)]]
    await update.message.reply_text(
        "Welcome to PRO ULTRA Drive Bot!\nSend any video, audio or document.",
        reply_markup=InlineKeyboardMarkup(kb),
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - Start bot\n/help - This menu\n/stats - Show stats\n/search name - Search files\n\nSend any file to upload."
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    await update.message.reply_text(f"Total files stored: {total}")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use: /search filename")
        return
    query = " ".join(context.args)
    with db() as conn:
        rows = conn.execute("SELECT name FROM files WHERE name LIKE ? LIMIT 10", (f"%{query}%",)).fetchall()
    if not rows:
        await update.message.reply_text("No files found.")
        return
    await update.message.reply_text("\n".join(row["name"] for row in rows))

def detect_category(msg):
    if msg.video: return "video", msg.video
    if msg.audio: return "audio", msg.audio
    if msg.document: return "document", msg.document
    return "other", None

async def save_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user = update.effective_user
    await register_user(user)

    category, media = detect_category(msg)
    if media is None:
        await msg.reply_text("Send video/audio/document file only.")
        return

    name = getattr(media, "file_name", "file")
    size = getattr(media, "file_size", 0)
    mime = getattr(media, "mime_type", None) or mimetypes.guess_type(name)[0] or "application/octet-stream"
    file_id = getattr(media, "file_id", None)

    try:
        sent = await context.bot.copy_message(
            chat_id=CHANNEL_ID,
            from_chat_id=msg.chat_id,
            message_id=msg.message_id,
        )

        with db() as conn:
            owner = conn.execute("SELECT id FROM users WHERE tg_id=?", (user.id,)).fetchone()
            owner_id = owner["id"] if owner else 0

            conn.execute(
                """
                INSERT INTO files(owner_id, tg_msg_id, file_id, name, category, mime, size, created_at)
                VALUES(?,?,?,?,?,?,?,?)
                """,
                (owner_id, sent.message_id, file_id, name, category, mime, size, datetime.utcnow().isoformat()),
            )

        await msg.reply_text(f"✅ Uploaded successfully: {name}")
    except Exception as e:
        await msg.reply_text(f"❌ Upload failed: {str(e)}")

# =====================================================
# RUNNERS
# =====================================================

async def run_bot():
    app_bot = Application.builder().token(BOT_TOKEN).build()

    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("help", help_cmd))
    app_bot.add_handler(CommandHandler("stats", stats))
    app_bot.add_handler(CommandHandler("search", search))

    app_bot.add_handler(
        MessageHandler(
            filters.Document.ALL | filters.VIDEO | filters.AUDIO,
            save_file,
        )
    )

    await app_bot.run_polling()

def run_web():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    print("🚀 Starting PRO ULTRA Drive Bot...")
    threading.Thread(target=run_web, daemon=True).start()
    asyncio.run(run_bot())
