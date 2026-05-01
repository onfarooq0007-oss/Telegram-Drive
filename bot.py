# telegram_drive_bot_pro_ultra.py
# PRO ULTRA Telegram Drive Bot (syntax-checked starter architecture)
# Python 3.10+

import os
import sqlite3
import mimetypes
import asyncio
import threading
from datetime import datetime
from pathlib import Path

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

# =====================================================
# CONFIG
# =====================================================

BOT_TOKEN = "8617110051:AAGDG4Zdn1SOfilB6Wx3NCZRM5_KAnWrYd0"
CHANNEL_ID = -1003892816171
BASE_URL = "http://129.151.159.101:5000"
DB_NAME = "drive_pro.db"

# =====================================================
# DATABASE
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

# =====================================================
# FLASK WEB UI
# =====================================================

app = Flask(__name__)

HTML = """
<!doctype html>
<html>
<head>
<title>Drive PRO ULTRA</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{
    font-family:Arial;
    background:#f1f3f4;
    margin:0;
}
.top{
    background:white;
    padding:15px;
    box-shadow:0 1px 5px rgba(0,0,0,.08);
}
.grid{
    display:grid;
    grid-template-columns:repeat(auto-fill,minmax(250px,1fr));
    gap:15px;
    padding:20px;
}
.card{
    background:white;
    border-radius:16px;
    padding:15px;
    box-shadow:0 1px 4px rgba(0,0,0,.08);
}
a{
    text-decoration:none;
    color:#1a73e8;
}
small{
    color:#777;
}
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
<video controls width="100%">
<source src="/stream/{{f['id']}}">
</video>
{% elif f['category'] == 'audio' %}
<audio controls style="width:100%">
<source src="/stream/{{f['id']}}">
</audio>
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
            files = conn.execute(
                "SELECT * FROM files WHERE category=? ORDER BY id DESC",
                (cat,),
            ).fetchall()
        else:
            files = conn.execute(
                "SELECT * FROM files ORDER BY id DESC"
            ).fetchall()

    return render_template_string(HTML, files=files)


@app.route("/favorite/<int:file_id>")
def favorite(file_id):
    with db() as conn:
        conn.execute(
            "UPDATE files SET favorite=1 WHERE id=?",
            (file_id,),
        )
    return redirect("/")


@app.route("/download/<int:file_id>")
def download(file_id):
    return redirect(url_for("telegram_file", file_id=file_id))


@app.route("/stream/<int:file_id>")
def stream(file_id):
    return redirect(url_for("telegram_file", file_id=file_id))


@app.route("/telegram_file/<int:file_id>")
def telegram_file(file_id):
    # Real Telegram file streaming requires get_file API
    return abort(501, "Telegram CDN streaming not configured yet")


@app.route("/api/stats")
def stats_api():
    with db() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM files"
        ).fetchone()[0]

    return jsonify({"total_files": total})


# =====================================================
# TELEGRAM BOT
# =====================================================


async def register_user(user):
    with db() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO users(tg_id, username, created_at)
            VALUES(?,?,?)
            """,
            (
                user.id,
                user.username,
                datetime.utcnow().isoformat(),
            ),
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await register_user(user)

    kb = [
        [
            InlineKeyboardButton(
                "Open Drive",
                url=BASE_URL,
            )
        ]
    ]

    await update.message.reply_text(
        "Welcome to PRO ULTRA Drive Bot",
        reply_markup=InlineKeyboardMarkup(kb),
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = """
/start - Start bot
/help - Help menu
/stats - Show stats
/search name - Search files

Send any file to upload.
Video/audio/docs auto sorted.
"""
    await update.message.reply_text(txt)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with db() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM files"
        ).fetchone()[0]

    await update.message.reply_text(
        f"Total files stored: {total}"
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Use: /search filename"
        )
        return

    query = " ".join(context.args)

    with db() as conn:
        rows = conn.execute(
            """
            SELECT name FROM files
            WHERE name LIKE ?
            LIMIT 10
            """,
            (f"%{query}%",),
        ).fetchall()

    if not rows:
        await update.message.reply_text(
            "No files found."
        )
        return

    result = "\n".join(row["name"] for row in rows)
    await update.message.reply_text(result)


def detect_category(msg):
    if msg.video:
        return "video", msg.video
    if msg.audio:
        return "audio", msg.audio
    if msg.document:
        return "document", msg.document
    return "other", None


async def save_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user = update.effective_user

    await register_user(user)

    category, media = detect_category(msg)

    if media is None:
        await msg.reply_text(
            "Send video/audio/document file only."
        )
        return

    name = getattr(media, "file_name", None) or "file"
    size = getattr(media, "file_size", 0)
    mime = getattr(media, "mime_type", None)

    if not mime:
        mime = mimetypes.guess_type(name)[0]
    if not mime:
        mime = "application/octet-stream"

    sent = await context.bot.copy_message(
        chat_id=CHANNEL_ID,
        from_chat_id=msg.chat_id,
        message_id=msg.message_id,
    )

    with db() as conn:
        owner = conn.execute(
            "SELECT id FROM users WHERE tg_id=?",
            (user.id,),
        ).fetchone()

        owner_id = owner["id"]

        conn.execute(
            """
            INSERT INTO files(
                owner_id,
                tg_msg_id,
                name,
                category,
                mime,
                size,
                created_at
            )
            VALUES(?,?,?,?,?,?,?)
            """,
            (
                owner_id,
                sent.message_id,
                name,
                category,
                mime,
                size,
                datetime.utcnow().isoformat(),
            ),
        )

    await msg.reply_text(
        f"Uploaded successfully: {name}"
    )


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
            filters.Document.ALL |
            filters.VIDEO |
            filters.AUDIO,
            save_file,
        )
    )

    await app_bot.run_polling()


def run_web():
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
    )


if __name__ == "__main__":
    threading.Thread(
        target=run_web,
        daemon=True,
    ).start()

    asyncio.run(run_bot())
