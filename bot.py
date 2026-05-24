"""
╔══════════════════════════════════════════════════════════════════╗
║         SUPER AI BOT  —  ULTIMATE EDITION  v3.0                 ║
║                                                                  ║
║  ✅ Ko'p AI model       (Gemini, ChatGPT, Groq)                  ║
║  ✅ Auto model fallback (model ishlamasa keyingisi)              ║
║  ✅ Multimodal Vision   (Gemini & GPT-4o)                        ║
║  ✅ Voice-to-Text       (Whisper-large-v3, bepul)                ║
║  ✅ Web Search          (Gemini google_search)                   ║
║  ✅ Rasm generatsiya    (DALL-E 3 + stil + tarjima)              ║
║  ✅ Ovoz javob          (gTTS)                                   ║
║  ✅ SQLite + thread     (parallel suhbatlar)                     ║
║  ✅ RAG                 (PDF/TXT/DOCX/MD/CSV)                    ║
║  ✅ Til tanlash         (uz / ru / en)                           ║
║  ✅ Inline rejim        (guruhda @bot)                           ║
║  ✅ Telegram Mini App   (webapp/index.html)                      ║
║  ✅ Anti-spam           (rate limiting, flood himoya)            ║
║  ✅ Premium tizimi      (Telegram Stars, kunlik limitlar)        ║
║  ✅ Scheduled xabarlar  (cron, eslatmalar)                       ║
║  ✅ Admin analytics     (grafik, hisobot)                        ║
║  ✅ Webhook rejim       (Render uchun, polling o'rniga)          ║
║  ✅ AI Admin Panel      (Gemini function calling)                ║
╚══════════════════════════════════════════════════════════════════╝

Render.com uchun muhit o'zgaruvchilari (.env yoki Render Dashboard):
    TELEGRAM_TOKEN, GEMINI_API_KEY, ADMIN_GEMINI_KEY,
    OPENAI_API_KEY, GROQ_API_KEY, ADMIN_IDS,
    WEBHOOK_URL (https://your-app.onrender.com),
    BOT_WEBAPP_URL (ixtiyoriy),
    PORT (8443, Render avtomatik qo'yadi)

Render start command:
    python bot.py
"""

# ══════════════════════════════════════════════════════════════════
#  IMPORTLAR
# ══════════════════════════════════════════════════════════════════
import io
import os
import re
import time
import math
import hmac
import json
import base64
import hashlib
import logging
import sqlite3
import textwrap
import threading
import requests
from datetime import datetime, timedelta
from collections import defaultdict

from dotenv import load_dotenv
import google.generativeai as genai
from openai import OpenAI
from groq import Groq
from gtts import gTTS
from telebot import TeleBot
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineQueryResultArticle, InputTextMessageContent,
    WebAppInfo, MenuButtonWebApp,
    LabeledPrice, ShippingAddress,
)
from flask import Flask, request, abort

# ══════════════════════════════════════════════════════════════════
#  LOGGING
# ══════════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════
#  .ENV — MAXFIY KALITLAR
# ══════════════════════════════════════════════════════════════════
load_dotenv()

def _req(key: str) -> str:
    val = os.getenv(key, "").strip()
    if not val:
        log.warning("Muhit o'zgaruvchisi topilmadi: %s", key)
    return val

TELEGRAM_TOKEN   = _req("TELEGRAM_TOKEN")
GEMINI_API_KEY   = _req("GEMINI_API_KEY")
ADMIN_GEMINI_KEY = _req("ADMIN_GEMINI_KEY")
OPENAI_API_KEY   = _req("OPENAI_API_KEY")
GROQ_API_KEY     = _req("GROQ_API_KEY")
WEBHOOK_URL      = os.getenv("WEBHOOK_URL", "").rstrip("/")   # https://app.onrender.com
BOT_WEBAPP_URL   = os.getenv("BOT_WEBAPP_URL", "")
PORT             = int(os.getenv("PORT", "8443"))
SECRET_TOKEN     = hashlib.sha256(TELEGRAM_TOKEN.encode()).hexdigest()[:32]

_admin_env = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: list[int] = (
    [int(x.strip()) for x in _admin_env.split(",") if x.strip().isdigit()]
    if _admin_env else []
)

# ── Konstantalar ───────────────────────────────────────────────────
DB_PATH          = os.getenv("DB_PATH", "bot_history.db")
MAX_HISTORY      = 20
CHUNK_SIZE       = 800
CHUNK_OVERLAP    = 100
RAG_TOP_K        = 4
MAX_THREADS      = 10

# Anti-spam
RATE_MSG_LIMIT   = 10    # N xabar
RATE_WINDOW      = 60    # M soniyada
RATE_BLOCK_SEC   = 30    # Bloklash muddati

# Premium
FREE_DAILY_MSG   = 30
FREE_DAILY_IMG   = 5
PREM_DAILY_MSG   = 99999
PREM_DAILY_IMG   = 99999
PREMIUM_STARS    = 100   # 1 oylik narx (Telegram Stars)

# ══════════════════════════════════════════════════════════════════
#  TIL KONFIGURATSIYASI
# ══════════════════════════════════════════════════════════════════
LANGUAGES = {
    "uz": {
        "label": "🇺🇿 O'zbekcha",
        "system": "Foydalanuvchi bilan faqat o'zbek tilida muloqot qil. Javoblarni aniq va tushunarli o'zbek tilida yoz.",
        "rate_limited": "⏳ Juda tez xabar yuboryapsiz. {sec} soniya kuting.",
        "daily_limit":  "📊 Kunlik limitingiz tugadi. Premium uchun /premium yozing.",
        "img_limit":    "🖼 Kunlik rasm limitingiz tugadi. Premium uchun /premium yozing.",
        "banned":       "🚫 Siz bloklangansiz.",
        "premium_msg":  "⭐ Premium (1 oy) — {stars} Telegram Stars\nCheksiz xabarlar va rasmlar.",
    },
    "ru": {
        "label": "🇷🇺 Русский",
        "system": "Общайся с пользователем только на русском языке. Пиши ответы чётко и понятно.",
        "rate_limited": "⏳ Слишком быстро. Подождите {sec} секунд.",
        "daily_limit":  "📊 Дневной лимит исчерпан. Напишите /premium.",
        "img_limit":    "🖼 Лимит изображений исчерпан. Напишите /premium.",
        "banned":       "🚫 Вы заблокированы.",
        "premium_msg":  "⭐ Premium (1 месяц) — {stars} Telegram Stars\nНеограниченные сообщения и изображения.",
    },
    "en": {
        "label": "🇬🇧 English",
        "system": "Communicate with the user only in English. Write clear and concise answers.",
        "rate_limited": "⏳ Too fast. Wait {sec} seconds.",
        "daily_limit":  "📊 Daily limit reached. Type /premium.",
        "img_limit":    "🖼 Image limit reached. Type /premium.",
        "banned":       "🚫 You are banned.",
        "premium_msg":  "⭐ Premium (1 month) — {stars} Telegram Stars\nUnlimited messages and images.",
    },
}
DEFAULT_LANG = "uz"

BASE_SYSTEM = (
    "You are a helpful, smart AI assistant. "
    "Format answers with Markdown when it improves readability. "
    "Be concise but thorough."
)

def get_system_prompt(lang: str) -> str:
    inst = LANGUAGES.get(lang, LANGUAGES[DEFAULT_LANG])["system"]
    return f"{BASE_SYSTEM}\n\n{inst}"

def t(lang: str, key: str, **kwargs) -> str:
    tmpl = LANGUAGES.get(lang, LANGUAGES[DEFAULT_LANG]).get(key, key)
    return tmpl.format(**kwargs) if kwargs else tmpl

# ══════════════════════════════════════════════════════════════════
#  CLIENTLAR
# ══════════════════════════════════════════════════════════════════
genai.configure(api_key=GEMINI_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)
groq_client   = Groq(api_key=GROQ_API_KEY)
bot           = TeleBot(TELEGRAM_TOKEN, threaded=False)
app           = Flask(__name__)

# ══════════════════════════════════════════════════════════════════
#  MODEL REGISTRY
# ══════════════════════════════════════════════════════════════════
MODELS = {
    "gemini":      {"label": "🟣 Gemini 1.5 Flash",     "provider": "gemini"},
    "chatgpt":     {"label": "🟢 ChatGPT-4o Mini",       "provider": "openai"},
    "groq_llama3": {"label": "🟠 Groq · LLaMA 3.3 70B", "provider": "groq", "id": "llama-3.3-70b-versatile"},
    "groq_llama4": {"label": "🔵 Groq · LLaMA 4 Scout", "provider": "groq", "id": "meta-llama/llama-4-scout-17b-16e-instruct"},
    "groq_fast":   {"label": "⚡ Groq · LLaMA 3.1 8B",  "provider": "groq", "id": "llama-3.1-8b-instant"},
}
DEFAULT_MODEL    = "groq_llama3"
GEMINI_FALLBACK  = ["gemini-1.5-flash", "gemini-1.5-flash-8b", "gemini-1.0-pro"]
GROQ_FALLBACK    = ["llama-3.3-70b-versatile", "meta-llama/llama-4-scout-17b-16e-instruct", "llama-3.1-8b-instant"]
VISION_PROVIDERS = {"gemini", "openai"}

# Auto-fallback zanjiri: model ishlamasa keyingisiga o'tadi
MODEL_FALLBACK_CHAIN = ["groq_llama3", "groq_llama4", "groq_fast", "gemini", "chatgpt"]

# Rasm stillari
IMAGE_STYLES = {
    "":            "",
    "realistic":   ", ultra realistic photograph, 8k, photorealistic, DSLR",
    "digital_art": ", digital art, trending on artstation, vibrant colors, concept art",
    "sketch":      ", pencil sketch, hand drawn, black and white, detailed linework",
    "anime":       ", anime style, Studio Ghibli, vibrant, manga art",
    "3d":          ", 3D render, octane render, cinema4d, ray tracing, high detail",
    "cinematic":   ", cinematic lighting, movie still, epic composition, anamorphic lens",
}

# ══════════════════════════════════════════════════════════════════
#  SQLITE — MA'LUMOTLAR BAZASI
# ══════════════════════════════════════════════════════════════════
_db_lock = threading.Lock()

def db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def db_init():
    with _db_lock, db_connect() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                uid           INTEGER PRIMARY KEY,
                username      TEXT    DEFAULT '',
                first_name    TEXT    DEFAULT '',
                model         TEXT    DEFAULT 'groq_llama3',
                voice_on      INTEGER DEFAULT 0,
                banned        INTEGER DEFAULT 0,
                lang          TEXT    DEFAULT 'uz',
                active_thread INTEGER DEFAULT 0,
                premium       INTEGER DEFAULT 0,
                premium_until TEXT    DEFAULT '',
                daily_msgs    INTEGER DEFAULT 0,
                daily_images  INTEGER DEFAULT 0,
                last_reset    TEXT    DEFAULT '',
                notify_on     INTEGER DEFAULT 1,
                joined_at     TEXT    DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                uid        INTEGER NOT NULL,
                thread_id  INTEGER NOT NULL DEFAULT 1,
                role       TEXT    NOT NULL,
                content    TEXT    NOT NULL,
                model      TEXT    DEFAULT '',
                created_at TEXT    DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS threads (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                uid        INTEGER NOT NULL,
                name       TEXT    NOT NULL DEFAULT 'Yangi suhbat',
                created_at TEXT    DEFAULT (datetime('now')),
                updated_at TEXT    DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS images (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                uid        INTEGER NOT NULL,
                prompt     TEXT    NOT NULL,
                url        TEXT    NOT NULL,
                created_at TEXT    DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS broadcasts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                text       TEXT    NOT NULL,
                sent_count INTEGER DEFAULT 0,
                created_at TEXT    DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS rag_docs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                uid        INTEGER NOT NULL,
                filename   TEXT    NOT NULL,
                file_hash  TEXT    NOT NULL,
                created_at TEXT    DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS rag_chunks (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id    INTEGER NOT NULL,
                uid       INTEGER NOT NULL,
                chunk_idx INTEGER NOT NULL,
                content   TEXT    NOT NULL,
                FOREIGN KEY (doc_id) REFERENCES rag_docs(id)
            );
            CREATE TABLE IF NOT EXISTS spam_log (
                uid INTEGER NOT NULL,
                ts  REAL    NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rate_blocked (
                uid   INTEGER PRIMARY KEY,
                until REAL    NOT NULL
            );
            CREATE TABLE IF NOT EXISTS scheduled_msgs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                uid        INTEGER NOT NULL,
                text       TEXT    NOT NULL,
                send_at    TEXT    NOT NULL,
                repeat     TEXT    DEFAULT 'none',
                sent       INTEGER DEFAULT 0,
                created_at TEXT    DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS payments (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                uid        INTEGER NOT NULL,
                stars      INTEGER NOT NULL,
                months     INTEGER DEFAULT 1,
                created_at TEXT    DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_messages_uid_thread ON messages(uid, thread_id);
            CREATE INDEX IF NOT EXISTS idx_spam_log_uid ON spam_log(uid);
            CREATE INDEX IF NOT EXISTS idx_scheduled_send ON scheduled_msgs(send_at, sent);
        """)
        # Safe migration for existing databases
        safe_cols = [
            ("users", "premium",       "INTEGER DEFAULT 0"),
            ("users", "premium_until", "TEXT    DEFAULT ''"),
            ("users", "daily_msgs",    "INTEGER DEFAULT 0"),
            ("users", "daily_images",  "INTEGER DEFAULT 0"),
            ("users", "last_reset",    "TEXT    DEFAULT ''"),
            ("users", "notify_on",     "INTEGER DEFAULT 1"),
            ("users", "lang",          "TEXT    DEFAULT 'uz'"),
            ("users", "active_thread", "INTEGER DEFAULT 0"),
        ]
        for table, col, defn in safe_cols:
            try:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {defn}")
            except Exception:
                pass

# ── Helpers ────────────────────────────────────────────────────────
def _exec(sql: str, params: tuple = ()):
    with _db_lock, db_connect() as c:
        c.execute(sql, params)

def _fetch(sql: str, params: tuple = (), one: bool = False):
    with _db_lock, db_connect() as c:
        cur = c.execute(sql, params)
        return cur.fetchone() if one else cur.fetchall()

# ── Users ──────────────────────────────────────────────────────────
def db_ensure_user(uid: int, username: str = "", first_name: str = ""):
    with _db_lock, db_connect() as c:
        c.execute("""
            INSERT INTO users (uid, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(uid) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name
        """, (uid, username[:64] if username else "", first_name[:64] if first_name else ""))
    _ensure_default_thread(uid)

def db_get_user(uid: int):
    return _fetch("SELECT * FROM users WHERE uid=?", (uid,), one=True)

def db_set(uid: int, **fields):
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields)
    vals = list(fields.values()) + [uid]
    _exec(f"UPDATE users SET {sets} WHERE uid=?", tuple(vals))

def db_all_users():
    return _fetch("SELECT * FROM users")

def db_recent_users(limit: int = 5):
    return _fetch("SELECT uid,username,first_name,joined_at FROM users ORDER BY rowid DESC LIMIT ?", (limit,))

def db_stats() -> dict:
    with _db_lock, db_connect() as c:
        r = lambda q, p=(): c.execute(q, p).fetchone()[0]
        return {
            "users":      r("SELECT COUNT(*) FROM users"),
            "premium":    r("SELECT COUNT(*) FROM users WHERE premium=1"),
            "active":     r("SELECT COUNT(DISTINCT uid) FROM messages WHERE created_at>datetime('now','-1 day')"),
            "messages":   r("SELECT COUNT(*) FROM messages"),
            "images":     r("SELECT COUNT(*) FROM images"),
            "docs":       r("SELECT COUNT(*) FROM rag_docs"),
            "threads":    r("SELECT COUNT(*) FROM threads"),
            "scheduled":  r("SELECT COUNT(*) FROM scheduled_msgs WHERE sent=0"),
            "top_model":  (c.execute("SELECT model FROM messages WHERE role='user' GROUP BY model ORDER BY COUNT(*) DESC LIMIT 1").fetchone() or ["—"])[0],
        }

# ── Premium ────────────────────────────────────────────────────────
def _reset_daily_if_needed(user) -> dict:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    if user["last_reset"] != today:
        _exec("UPDATE users SET daily_msgs=0, daily_images=0, last_reset=? WHERE uid=?",
              (today, user["uid"]))
        return {**dict(user), "daily_msgs": 0, "daily_images": 0, "last_reset": today}
    return dict(user)

def is_premium(user) -> bool:
    if not user["premium"]:
        return False
    if user["premium_until"]:
        try:
            exp = datetime.fromisoformat(user["premium_until"])
            if datetime.utcnow() > exp:
                _exec("UPDATE users SET premium=0 WHERE uid=?", (user["uid"],))
                return False
        except Exception:
            pass
    return True

def check_msg_limit(uid: int) -> bool:
    """True = ruxsat, False = limit tugagan."""
    user = db_get_user(uid)
    if not user:
        return True
    user = _reset_daily_if_needed(user)
    limit = PREM_DAILY_MSG if is_premium(user) else FREE_DAILY_MSG
    if user["daily_msgs"] >= limit:
        return False
    _exec("UPDATE users SET daily_msgs=daily_msgs+1 WHERE uid=?", (uid,))
    return True

def check_img_limit(uid: int) -> bool:
    user = db_get_user(uid)
    if not user:
        return True
    user = _reset_daily_if_needed(user)
    limit = PREM_DAILY_IMG if is_premium(user) else FREE_DAILY_IMG
    if user["daily_images"] >= limit:
        return False
    _exec("UPDATE users SET daily_images=daily_images+1 WHERE uid=?", (uid,))
    return True

def grant_premium(uid: int, months: int = 1):
    user = db_get_user(uid)
    if user and user["premium_until"]:
        try:
            base = datetime.fromisoformat(user["premium_until"])
            if base > datetime.utcnow():
                exp = base + timedelta(days=30 * months)
            else:
                exp = datetime.utcnow() + timedelta(days=30 * months)
        except Exception:
            exp = datetime.utcnow() + timedelta(days=30 * months)
    else:
        exp = datetime.utcnow() + timedelta(days=30 * months)
    _exec("UPDATE users SET premium=1, premium_until=? WHERE uid=?",
          (exp.isoformat(), uid))
    _exec("INSERT INTO payments (uid, stars, months) VALUES (?,?,?)",
          (uid, PREMIUM_STARS * months, months))

# ── Anti-spam ──────────────────────────────────────────────────────
def is_rate_blocked(uid: int) -> float:
    """0 = ruxsat, >0 = qolgan soniya."""
    row = _fetch("SELECT until FROM rate_blocked WHERE uid=?", (uid,), one=True)
    if row:
        remaining = row["until"] - time.time()
        if remaining > 0:
            return remaining
        _exec("DELETE FROM rate_blocked WHERE uid=?", (uid,))
    return 0.0

def record_message(uid: int) -> float:
    """Xabarni qayd etadi. 0 = OK, >0 = bloklandi (soniya)."""
    now = time.time()
    # Eski yozuvlarni tozalash
    _exec("DELETE FROM spam_log WHERE uid=? AND ts<?", (uid, now - RATE_WINDOW))
    # Songi N xabarni sanash
    count = _fetch("SELECT COUNT(*) FROM spam_log WHERE uid=?", (uid,), one=True)[0]
    _exec("INSERT INTO spam_log (uid, ts) VALUES (?,?)", (uid, now))
    if count >= RATE_MSG_LIMIT:
        until = now + RATE_BLOCK_SEC
        _exec("INSERT INTO rate_blocked (uid, until) VALUES (?,?) ON CONFLICT(uid) DO UPDATE SET until=?",
              (uid, until, until))
        return float(RATE_BLOCK_SEC)
    return 0.0

# ── Threads ────────────────────────────────────────────────────────
def _ensure_default_thread(uid: int) -> int:
    row = _fetch("SELECT id FROM threads WHERE uid=? ORDER BY id LIMIT 1", (uid,), one=True)
    if row:
        tid = row["id"]
    else:
        with _db_lock, db_connect() as c:
            cur = c.execute("INSERT INTO threads (uid, name) VALUES (?,?)",
                            (uid, "💬 Asosiy suhbat"))
            tid = cur.lastrowid
    _exec("UPDATE users SET active_thread=? WHERE uid=? AND (active_thread=0 OR active_thread IS NULL)",
          (tid, uid))
    return tid

def db_create_thread(uid: int, name: str) -> int | None:
    count = _fetch("SELECT COUNT(*) FROM threads WHERE uid=?", (uid,), one=True)[0]
    if count >= MAX_THREADS:
        return None
    with _db_lock, db_connect() as c:
        cur = c.execute("INSERT INTO threads (uid, name) VALUES (?,?)",
                        (uid, name[:50]))
        tid = cur.lastrowid
        c.execute("UPDATE users SET active_thread=? WHERE uid=?", (tid, uid))
    return tid

def db_get_threads(uid: int) -> list:
    return _fetch(
        "SELECT t.id, t.name, t.updated_at, COUNT(m.id) as msg_count "
        "FROM threads t LEFT JOIN messages m ON m.thread_id=t.id AND m.uid=t.uid "
        "WHERE t.uid=? GROUP BY t.id ORDER BY t.updated_at DESC",
        (uid,),
    )

def db_get_thread(uid: int, tid: int):
    return _fetch("SELECT * FROM threads WHERE id=? AND uid=?", (tid, uid), one=True)

def db_rename_thread(uid: int, tid: int, name: str) -> bool:
    r = _fetch("SELECT id FROM threads WHERE id=? AND uid=?", (tid, uid), one=True)
    if not r:
        return False
    _exec("UPDATE threads SET name=? WHERE id=?", (name[:50], tid))
    return True

def db_delete_thread(uid: int, tid: int) -> bool:
    r = _fetch("SELECT id FROM threads WHERE id=? AND uid=?", (tid, uid), one=True)
    if not r:
        return False
    count = _fetch("SELECT COUNT(*) FROM threads WHERE uid=?", (uid,), one=True)[0]
    if count <= 1:
        return False
    _exec("DELETE FROM messages WHERE thread_id=? AND uid=?", (tid, uid))
    _exec("DELETE FROM threads WHERE id=?", (tid,))
    first = _fetch("SELECT id FROM threads WHERE uid=? ORDER BY id LIMIT 1", (uid,), one=True)
    if first:
        _exec("UPDATE users SET active_thread=? WHERE uid=?", (first["id"], uid))
    return True

def db_get_active_thread(uid: int) -> int:
    user = db_get_user(uid)
    if user and user["active_thread"]:
        r = _fetch("SELECT id FROM threads WHERE id=? AND uid=?",
                   (user["active_thread"], uid), one=True)
        if r:
            return r["id"]
    return _ensure_default_thread(uid)

def db_update_thread_time(tid: int):
    _exec("UPDATE threads SET updated_at=datetime('now') WHERE id=?", (tid,))

# ── Messages ───────────────────────────────────────────────────────
def db_save_message(uid: int, role: str, content: str,
                    model: str = "", thread_id: int | None = None):
    if thread_id is None:
        thread_id = db_get_active_thread(uid)
    # Uzun xabarlarni qisqartirish (DB himoyasi)
    content = content[:8000] if content else ""
    _exec("INSERT INTO messages (uid,thread_id,role,content,model) VALUES (?,?,?,?,?)",
          (uid, thread_id, role, content, model))
    db_update_thread_time(thread_id)

def db_get_history(uid: int, limit: int = MAX_HISTORY,
                   thread_id: int | None = None) -> list[dict]:
    if thread_id is None:
        thread_id = db_get_active_thread(uid)
    rows = _fetch(
        "SELECT role,content FROM messages WHERE uid=? AND thread_id=? ORDER BY id DESC LIMIT ?",
        (uid, thread_id, limit),
    )
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

def db_clear_thread(uid: int, thread_id: int | None = None):
    if thread_id is None:
        thread_id = db_get_active_thread(uid)
    _exec("DELETE FROM messages WHERE uid=? AND thread_id=?", (uid, thread_id))

def pop_last_user_msg(uid: int, thread_id: int | None = None):
    if thread_id is None:
        thread_id = db_get_active_thread(uid)
    _exec(
        "DELETE FROM messages WHERE uid=? AND thread_id=? AND id=("
        "SELECT MAX(id) FROM messages WHERE uid=? AND thread_id=? AND role='user')",
        (uid, thread_id, uid, thread_id),
    )

# ── Images / Broadcasts ────────────────────────────────────────────
def db_save_image(uid: int, prompt: str, note: str = ""):
    _exec("INSERT INTO images (uid,prompt,url) VALUES (?,?,?)", (uid, prompt[:500], note))

def db_save_broadcast(text: str, sent: int):
    _exec("INSERT INTO broadcasts (text,sent_count) VALUES (?,?)", (text, sent))

# ── Scheduled ─────────────────────────────────────────────────────
def db_add_schedule(uid: int, text: str, send_at: str, repeat: str = "none") -> int:
    with _db_lock, db_connect() as c:
        cur = c.execute(
            "INSERT INTO scheduled_msgs (uid,text,send_at,repeat) VALUES (?,?,?,?)",
            (uid, text[:2000], send_at, repeat),
        )
        return cur.lastrowid

def db_get_due_schedules() -> list:
    return _fetch(
        "SELECT * FROM scheduled_msgs WHERE sent=0 AND send_at<=datetime('now')"
    )

def db_mark_schedule_sent(sid: int, repeat: str):
    if repeat == "daily":
        _exec("UPDATE scheduled_msgs SET send_at=datetime(send_at,'+1 day') WHERE id=?", (sid,))
    elif repeat == "weekly":
        _exec("UPDATE scheduled_msgs SET send_at=datetime(send_at,'+7 days') WHERE id=?", (sid,))
    elif repeat == "monthly":
        _exec("UPDATE scheduled_msgs SET send_at=datetime(send_at,'+30 days') WHERE id=?", (sid,))
    else:
        _exec("UPDATE scheduled_msgs SET sent=1 WHERE id=?", (sid,))

def db_list_schedules(uid: int) -> list:
    return _fetch(
        "SELECT id,text,send_at,repeat FROM scheduled_msgs WHERE uid=? AND sent=0 ORDER BY send_at",
        (uid,),
    )

def db_delete_schedule(uid: int, sid: int) -> bool:
    r = _fetch("SELECT id FROM scheduled_msgs WHERE id=? AND uid=?", (sid, uid), one=True)
    if not r:
        return False
    _exec("DELETE FROM scheduled_msgs WHERE id=?", (sid,))
    return True

# ── Analytics ──────────────────────────────────────────────────────
def db_analytics(days: int = 7) -> dict:
    with _db_lock, db_connect() as c:
        daily = c.execute("""
            SELECT date(created_at) as day, COUNT(*) as cnt
            FROM messages WHERE role='user'
              AND created_at >= datetime('now', ?)
            GROUP BY day ORDER BY day
        """, (f"-{days} days",)).fetchall()

        models = c.execute("""
            SELECT model, COUNT(*) as cnt FROM messages
            WHERE role='user' AND model!=''
            GROUP BY model ORDER BY cnt DESC
        """).fetchall()

        top_users = c.execute("""
            SELECT u.first_name, u.username, COUNT(m.id) as cnt
            FROM messages m JOIN users u ON m.uid=u.uid
            WHERE m.role='user'
            GROUP BY m.uid ORDER BY cnt DESC LIMIT 5
        """).fetchall()

        new_users = c.execute("""
            SELECT date(joined_at) as day, COUNT(*) as cnt
            FROM users WHERE joined_at >= datetime('now', ?)
            GROUP BY day ORDER BY day
        """, (f"-{days} days",)).fetchall()

    return {
        "daily_msgs":  [(r["day"], r["cnt"]) for r in daily],
        "models":      [(r["model"], r["cnt"]) for r in models],
        "top_users":   [(r["first_name"], r["username"] or "—", r["cnt"]) for r in top_users],
        "new_users":   [(r["day"], r["cnt"]) for r in new_users],
    }

# ══════════════════════════════════════════════════════════════════
#  RAG — RETRIEVAL AUGMENTED GENERATION
# ══════════════════════════════════════════════════════════════════
def _extract_text_pdf(data: bytes) -> str:
    try:
        import fitz
        doc  = fitz.open(stream=data, filetype="pdf")
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return text
    except ImportError:
        return "[PyMuPDF kerak: pip install PyMuPDF]"

def _extract_text_docx(data: bytes) -> str:
    try:
        from docx import Document
        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except ImportError:
        return "[python-docx kerak: pip install python-docx]"

def _extract_text(data: bytes, filename: str) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):  return _extract_text_pdf(data)
    if name.endswith(".docx"): return _extract_text_docx(data)
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode("utf-8", errors="replace")

def _chunk_text(text: str) -> list[str]:
    text   = re.sub(r"\s+", " ", text).strip()
    chunks, start = [], 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks

def _tfidf_score(query: str, chunk: str) -> float:
    q_words = set(re.findall(r"\w+", query.lower()))
    c_words = re.findall(r"\w+", chunk.lower())
    if not q_words or not c_words:
        return 0.0
    freq = {}
    for w in c_words:
        freq[w] = freq.get(w, 0) + 1
    return sum(
        (freq[w] / len(c_words)) * math.log(1 + 1 / (freq[w] + 1))
        for w in q_words if w in freq
    )

def rag_save(uid: int, data: bytes, filename: str) -> tuple[int, int]:
    file_hash = hashlib.md5(data).hexdigest()
    ex = _fetch("SELECT id FROM rag_docs WHERE uid=? AND file_hash=?", (uid, file_hash), one=True)
    if ex:
        return ex["id"], 0
    with _db_lock, db_connect() as c:
        cur    = c.execute("INSERT INTO rag_docs (uid,filename,file_hash) VALUES (?,?,?)",
                           (uid, filename[:200], file_hash))
        doc_id = cur.lastrowid
        chunks = _chunk_text(_extract_text(data, filename))
        c.executemany("INSERT INTO rag_chunks (doc_id,uid,chunk_idx,content) VALUES (?,?,?,?)",
                      [(doc_id, uid, i, ch) for i, ch in enumerate(chunks)])
    return doc_id, len(chunks)

def rag_search(uid: int, query: str) -> str:
    rows = _fetch("SELECT content FROM rag_chunks WHERE uid=?", (uid,))
    if not rows:
        return ""
    scored = sorted(
        [(_tfidf_score(query, r["content"]), r["content"]) for r in rows],
        reverse=True,
    )
    top = [ch for sc, ch in scored[:RAG_TOP_K] if sc > 0]
    if not top:
        return ""
    return "📄 *Hujjatdan:*\n\n" + "\n\n---\n\n".join(top) + "\n\n---\n"

def rag_list(uid: int) -> list:
    return _fetch("SELECT id,filename,created_at FROM rag_docs WHERE uid=? ORDER BY id DESC", (uid,))

def rag_delete(uid: int, doc_id: int) -> bool:
    r = _fetch("SELECT id FROM rag_docs WHERE id=? AND uid=?", (doc_id, uid), one=True)
    if not r:
        return False
    _exec("DELETE FROM rag_chunks WHERE doc_id=?", (doc_id,))
    _exec("DELETE FROM rag_docs WHERE id=?", (doc_id,))
    return True

def rag_delete_all(uid: int):
    _exec("DELETE FROM rag_chunks WHERE uid=?", (uid,))
    _exec("DELETE FROM rag_docs WHERE uid=?", (uid,))

# ══════════════════════════════════════════════════════════════════
#  YORDAMCHI
# ══════════════════════════════════════════════════════════════════
def get_file_bytes(file_id: str) -> bytes:
    info = bot.get_file(file_id)
    url  = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{info.file_path}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.content

def safe_send(uid: int, text: str, **kwargs):
    try:
        bot.send_message(uid, text, parse_mode="Markdown", **kwargs)
    except Exception:
        try:
            bot.send_message(uid, re.sub(r"[*_`\[\]]", "", text), **kwargs)
        except Exception as e:
            log.error("safe_send uid=%s: %s", uid, e)

def error_msg(err: str) -> str:
    e = err.lower()
    if "429" in e or "quota" in e:
        return "⚠️ *Rate limit!* /model orqali boshqa modelni tanlang."
    if "decommissioned" in e or "model_not_found" in e:
        return "❌ Bu model eskirgan. /model orqali boshqasini tanlang."
    if "content_policy" in e or "safety" in e:
        return "🚫 Kontent siyosatiga zid. Boshqa so'rov yozing."
    if "insufficient_quota" in e or "billing" in e:
        return "💳 *API balansi tugagan.*"
    return f"❌ Xatolik:\n`{err[:200]}`"

def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS

def get_ctx(uid: int) -> tuple[str, str, str, bool, int]:
    """(model_key, lang, system_prompt, voice_on, thread_id)"""
    user      = db_get_user(uid)
    model_key = user["model"] if user else DEFAULT_MODEL
    lang      = user["lang"]  if user and user["lang"] else DEFAULT_LANG
    voice_on  = bool(user["voice_on"]) if user else False
    thread_id = db_get_active_thread(uid)
    return model_key, lang, get_system_prompt(lang), voice_on, thread_id

def _ascii_bar(val: int, max_val: int, width: int = 12) -> str:
    if max_val == 0:
        return "░" * width
    filled = int(round(val / max_val * width))
    return "█" * filled + "░" * (width - filled)

def build_analytics_text(days: int = 7) -> str:
    data = db_analytics(days)
    lines = [f"📊 *Analytics — oxirgi {days} kun*\n"]

    # Kunlik xabarlar
    if data["daily_msgs"]:
        lines.append("*📅 Kunlik xabarlar:*")
        max_m = max(c for _, c in data["daily_msgs"])
        for day, cnt in data["daily_msgs"]:
            bar = _ascii_bar(cnt, max_m)
            lines.append(f"  `{day[5:]}` {bar} {cnt}")
        lines.append("")

    # Modellar
    if data["models"]:
        lines.append("*🤖 Modellar:*")
        max_m = max(c for _, c in data["models"])
        for model, cnt in data["models"]:
            label = MODELS.get(model, {}).get("label", model)
            bar   = _ascii_bar(cnt, max_m, 8)
            lines.append(f"  {bar} {label}: {cnt}")
        lines.append("")

    # Top users
    if data["top_users"]:
        lines.append("*👑 Top foydalanuvchilar:*")
        for name, uname, cnt in data["top_users"]:
            lines.append(f"  • {name} (@{uname}): {cnt} xabar")
        lines.append("")

    # Yangi users
    if data["new_users"]:
        total_new = sum(c for _, c in data["new_users"])
        lines.append(f"*🆕 Yangi foydalanuvchilar:* {total_new} ta")

    return "\n".join(lines)

# ══════════════════════════════════════════════════════════════════
#  AI — AUTO FALLBACK TEXT
# ══════════════════════════════════════════════════════════════════
def ask_gemini(history: list[dict], sys_p: str) -> str:
    gemini_hist = [
        {"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]}
        for m in history[:-1]
    ]
    last     = history[-1]["content"]
    last_exc = None
    for name in GEMINI_FALLBACK:
        try:
            mdl  = genai.GenerativeModel(name, system_instruction=sys_p, tools="google_search")
            chat = mdl.start_chat(history=gemini_hist)
            resp = chat.send_message(last)
            parts = resp.candidates[0].content.parts
            return "".join(p.text for p in parts if hasattr(p, "text") and p.text).strip()
        except Exception as e:
            last_exc = e
            err = str(e)
            if "429" in err or "quota" in err.lower():
                d = 15
                m = re.search(r"seconds:\s*(\d+)", err)
                if m:
                    d = min(int(m.group(1)), 30)
                log.warning("[GEMINI] %s rate limit — %ss", name, d)
                time.sleep(d)
                continue
            raise
    raise last_exc

def ask_chatgpt(history: list[dict], sys_p: str) -> str:
    msgs = [{"role": "system", "content": sys_p}] + history
    r = openai_client.chat.completions.create(
        model="gpt-4o-mini", messages=msgs, max_tokens=1500, temperature=0.7
    )
    return r.choices[0].message.content

def ask_groq_raw(model_id: str, history: list[dict], sys_p: str) -> str:
    msgs = [{"role": "system", "content": sys_p}] + history
    r = groq_client.chat.completions.create(
        model=model_id, messages=msgs, max_tokens=1500, temperature=0.7
    )
    return r.choices[0].message.content

def ask_groq(primary_id: str, history: list[dict], sys_p: str) -> str:
    chain    = [primary_id] + [m for m in GROQ_FALLBACK if m != primary_id]
    last_exc = None
    for mid in chain:
        try:
            return ask_groq_raw(mid, history, sys_p)
        except Exception as e:
            err = str(e)
            last_exc = e
            if "decommissioned" in err or "404" in err or "not found" in err.lower():
                log.warning("[GROQ] %s ishlamaydi → keyingisi", mid)
                continue
            raise
    raise last_exc

def get_answer_single(model_key: str, history: list[dict], sys_p: str) -> str:
    cfg = MODELS.get(model_key, MODELS[DEFAULT_MODEL])
    p   = cfg["provider"]
    if p == "gemini": return ask_gemini(history, sys_p)
    if p == "openai": return ask_chatgpt(history, sys_p)
    if p == "groq":   return ask_groq(cfg["id"], history, sys_p)
    return "Noma'lum model."

def get_answer(model_key: str, history: list[dict], sys_p: str) -> str:
    """
    Auto-fallback: model ishlamasa, zanjir bo'yicha keyingisiga o'tadi.
    """
    chain = [model_key] + [k for k in MODEL_FALLBACK_CHAIN if k != model_key]
    last_exc = None
    for key in chain:
        try:
            ans = get_answer_single(key, history, sys_p)
            if key != model_key:
                ans = f"ℹ️ _{MODELS[model_key]['label']} ishlamadi → {MODELS[key]['label']}_\n\n" + ans
            return ans
        except Exception as e:
            last_exc = e
            err = str(e)
            if any(x in err.lower() for x in ["429", "quota", "decommissioned",
                                               "not found", "overloaded", "503"]):
                log.warning("[FALLBACK] %s xato → keyingi model", key)
                continue
            break
    raise last_exc

# ══════════════════════════════════════════════════════════════════
#  AI — VISION
# ══════════════════════════════════════════════════════════════════
def analyze_image_gemini(image_bytes: bytes, caption: str, sys_p: str) -> str:
    prompt   = caption.strip() or "Iltimos, bu rasmni batafsil tahlil qilib ber."
    b64      = base64.b64encode(image_bytes).decode("utf-8")
    last_exc = None
    for name in GEMINI_FALLBACK:
        try:
            mdl  = genai.GenerativeModel(name, system_instruction=sys_p, tools="google_search")
            resp = mdl.generate_content([{"inline_data": {"mime_type": "image/jpeg", "data": b64}}, prompt])
            parts = resp.candidates[0].content.parts
            return "".join(p.text for p in parts if hasattr(p, "text") and p.text).strip()
        except Exception as e:
            last_exc = e
            if "429" in str(e) or "quota" in str(e).lower():
                time.sleep(15)
                continue
            raise
    raise last_exc

def analyze_image_chatgpt(image_bytes: bytes, caption: str, sys_p: str) -> str:
    prompt  = caption.strip() or "Please analyze this image in detail."
    b64_img = base64.b64encode(image_bytes).decode("utf-8")
    resp = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": sys_p},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}},
                {"type": "text", "text": prompt},
            ]},
        ],
        max_tokens=1500,
    )
    return resp.choices[0].message.content

def analyze_image(model_key: str, image_bytes: bytes, caption: str, sys_p: str) -> str:
    cfg = MODELS.get(model_key, MODELS[DEFAULT_MODEL])
    if cfg["provider"] == "gemini":
        return analyze_image_gemini(image_bytes, caption, sys_p)
    elif cfg["provider"] == "openai":
        return analyze_image_chatgpt(image_bytes, caption, sys_p)
    else:
        note = f"ℹ️ _{cfg['label']}_ vision qo'llab-quvvatlamaydi → Gemini:\n\n"
        return note + analyze_image_gemini(image_bytes, caption, sys_p)

# ══════════════════════════════════════════════════════════════════
#  AI — VOICE-TO-TEXT
# ══════════════════════════════════════════════════════════════════
def transcribe_voice(audio_bytes: bytes) -> str:
    buf      = io.BytesIO(audio_bytes)
    buf.name = "voice.ogg"
    r = groq_client.audio.transcriptions.create(
        file=buf, model="whisper-large-v3",
        language="uz", response_format="text",
    )
    return str(r).strip()

# ══════════════════════════════════════════════════════════════════
#  AI — RASM GENERATSIYA (DALL-E 3)
# ══════════════════════════════════════════════════════════════════
def _translate_prompt(prompt: str) -> str:
    if re.search(r"[a-zA-Z]{4,}", prompt):
        return prompt
    try:
        mdl  = genai.GenerativeModel("gemini-1.5-flash")
        resp = mdl.generate_content(
            f"Translate this image prompt to English for DALL-E 3. "
            f"Return ONLY the English prompt, nothing else:\n{prompt}"
        )
        tr = resp.text.strip()
        log.info("[IMG] Prompt tarjima: %s → %s", prompt[:40], tr[:40])
        return tr or prompt
    except Exception:
        return prompt

def generate_image(prompt: str, style: str = "") -> bytes:
    eng_prompt = _translate_prompt(prompt)
    full       = (eng_prompt + IMAGE_STYLES.get(style, ""))[:4000]
    try:
        r = openai_client.images.generate(
            model="dall-e-3", prompt=full,
            n=1, size="1024x1024", quality="standard",
            response_format="b64_json",
        )
        return base64.b64decode(r.data[0].b64_json)
    except Exception as e:
        err = str(e)
        if "content_policy" in err.lower() or "safety" in err.lower():
            raise ValueError("🚫 Kontent siyosatiga zid. Boshqa tavsif yozing.")
        if "billing" in err.lower() or "quota" in err.lower():
            raise ValueError("💳 OpenAI balansi tugagan.")
        raise

# ══════════════════════════════════════════════════════════════════
#  OVOZ JAVOB (gTTS)
# ══════════════════════════════════════════════════════════════════
def text_to_voice(text: str, lang: str = "uz") -> io.BytesIO:
    clean    = re.sub(r"[*_`#~>|\\]", "", text)
    clean    = re.sub(r"\n{2,}", "\n", clean).strip()
    gtts_map = {"uz": "uz", "ru": "ru", "en": "en"}
    buf      = io.BytesIO()
    gTTS(text=clean[:3000], lang=gtts_map.get(lang, "uz"), slow=False).write_to_fp(buf)
    buf.seek(0)
    buf.name = "voice.mp3"
    return buf

# ══════════════════════════════════════════════════════════════════
#  SCHEDULER (background thread)
# ══════════════════════════════════════════════════════════════════
def _scheduler_loop():
    log.info("[SCHEDULER] Ishga tushdi")
    while True:
        try:
            due = db_get_due_schedules()
            for row in due:
                uid = row["uid"]
                try:
                    user = db_get_user(uid)
                    if user and not user["banned"] and user["notify_on"]:
                        safe_send(uid, f"🔔 *Eslatma:*\n\n{row['text']}")
                except Exception as e:
                    log.error("[SCHEDULER] uid=%s xato: %s", uid, e)
                db_mark_schedule_sent(row["id"], row["repeat"])
        except Exception as e:
            log.error("[SCHEDULER] loop xato: %s", e)
        time.sleep(30)  # 30 soniyada bir tekshirish

# ══════════════════════════════════════════════════════════════════
#  AI ADMIN PANEL — Gemini Function Calling
# ══════════════════════════════════════════════════════════════════
ADMIN_TOOLS = [
    {"name": "get_stats",
     "description": "Bot statistikasini ko'rish"},
    {"name": "get_analytics",
     "description": "Kunlik analytics grafik (oxirgi N kun)",
     "parameters": {"type": "object", "properties": {
         "days": {"type": "integer", "description": "Kun soni (default 7)"}}}},
    {"name": "list_users",
     "description": "Oxirgi foydalanuvchilar",
     "parameters": {"type": "object", "properties": {
         "limit": {"type": "integer", "description": "Soni (default 5)"}}}},
    {"name": "broadcast",
     "description": "Barcha foydalanuvchilarga xabar yuborish",
     "parameters": {"type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"]}},
    {"name": "ban_user",
     "description": "Bloklash yoki blokdan chiqarish",
     "parameters": {"type": "object",
                    "properties": {
                        "uid":    {"type": "integer"},
                        "action": {"type": "string", "description": "'ban' yoki 'unban'"}},
                    "required": ["uid", "action"]}},
    {"name": "grant_premium",
     "description": "Foydalanuvchiga premium berish",
     "parameters": {"type": "object",
                    "properties": {
                        "uid":    {"type": "integer"},
                        "months": {"type": "integer", "description": "Oy soni (default 1)"}},
                    "required": ["uid"]}},
    {"name": "find_user",
     "description": "Foydalanuvchini topish (@username yoki ID)",
     "parameters": {"type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"]}},
    {"name": "set_global_model",
     "description": "Barcha uchun default model",
     "parameters": {"type": "object",
                    "properties": {"model": {"type": "string",
                                             "description": f"Key: {', '.join(MODELS.keys())}"}},
                    "required": ["model"]}},
]

def admin_exec_tool(name: str, args: dict, admin_uid: int) -> str:
    if name == "get_stats":
        s = db_stats()
        return (f"📊 Statistika:\n👥 {s['users']} user ({s['premium']} premium)\n"
                f"🟢 Bugun faol: {s['active']}\n💬 {s['messages']} xabar\n"
                f"🖼 {s['images']} rasm\n📄 {s['docs']} hujjat\n"
                f"🧵 {s['threads']} thread\n🔔 {s['scheduled']} rejalashtirilgan\n"
                f"🏆 Top model: {s['top_model']}")

    elif name == "get_analytics":
        days = int(args.get("days", 7))
        return build_analytics_text(days)

    elif name == "list_users":
        limit = int(args.get("limit", 5))
        rows  = db_recent_users(limit)
        if not rows:
            return "Foydalanuvchilar topilmadi."
        return "👥 Foydalanuvchilar:\n" + "\n".join(
            f"• {r['first_name']} (@{r['username'] or '—'}) | {r['uid']} | {r['joined_at'][:10]}"
            for r in rows)

    elif name == "broadcast":
        text  = args.get("text", "").strip()
        if not text:
            return "❌ Matn bo'sh."
        users = db_all_users()
        sent  = 0
        for u in users:
            if u["banned"]:
                continue
            try:
                safe_send(u["uid"], f"📢 *Admin xabari:*\n\n{text}")
                sent += 1
                time.sleep(0.05)
            except Exception:
                pass
        db_save_broadcast(text, sent)
        return f"✅ {sent} ta foydalanuvchiga yuborildi."

    elif name == "ban_user":
        uid    = int(args.get("uid", 0))
        action = args.get("action", "ban")
        db_set(uid, banned=1 if action == "ban" else 0)
        return f"✅ {uid} {'bloklandi' if action == 'ban' else 'blokdan chiqarildi'}."

    elif name == "grant_premium":
        uid    = int(args.get("uid", 0))
        months = int(args.get("months", 1))
        grant_premium(uid, months)
        return f"✅ {uid} ga {months} oylik premium berildi."

    elif name == "find_user":
        query = args.get("query", "").strip().lstrip("@")
        if query.isdigit():
            row = _fetch("SELECT * FROM users WHERE uid=?", (int(query),), one=True)
        else:
            row = _fetch("SELECT * FROM users WHERE username=?", (query,), one=True)
        if not row:
            return f"❌ '{query}' topilmadi."
        prem  = f"⭐ {row['premium_until'][:10]}" if row["premium"] else "—"
        return (f"👤 {row['first_name']} (@{row['username'] or '—'}) | ID:{row['uid']}\n"
                f"Model: {MODELS.get(row['model'],{}).get('label',row['model'])}\n"
                f"Til: {row['lang']} | Ovoz: {'✅' if row['voice_on'] else '❌'}\n"
                f"Holat: {'🚫 Ban' if row['banned'] else '✅ Faol'}\n"
                f"Premium: {prem}\n"
                f"Bugun: {row['daily_msgs']} msg / {row['daily_images']} img\n"
                f"Ro'yxatdan: {row['joined_at'][:10]}")

    elif name == "set_global_model":
        model = args.get("model", "")
        if model not in MODELS:
            return f"❌ Noto'g'ri. Mavjudlari: {', '.join(MODELS.keys())}"
        with _db_lock, db_connect() as c:
            c.execute("UPDATE users SET model=?", (model,))
        return f"✅ Barcha uchun '{MODELS[model]['label']}' tanlandi."

    return f"❓ Noma'lum: {name}"

admin_sessions: dict[int, list] = {}

def admin_ai_chat(uid: int, user_message: str) -> str:
    genai.configure(api_key=ADMIN_GEMINI_KEY)
    if uid not in admin_sessions:
        admin_sessions[uid] = []
    admin_sessions[uid].append({"role": "user", "parts": [user_message]})

    tools_spec = [genai.protos.Tool(function_declarations=[
        genai.protos.FunctionDeclaration(
            name=t["name"], description=t["description"],
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    k: genai.protos.Schema(
                        type={"integer": genai.protos.Type.INTEGER,
                              "string":  genai.protos.Type.STRING}.get(v["type"], genai.protos.Type.STRING),
                        description=v.get("description", ""),
                    ) for k, v in t.get("parameters", {}).get("properties", {}).items()
                },
                required=t.get("parameters", {}).get("required", []),
            ) if t.get("parameters") else None,
        ) for t in ADMIN_TOOLS
    ])]

    try:
        model = genai.GenerativeModel(
            "gemini-1.5-flash",
            system_instruction=(
                f"Sen Telegram bot admin yordamchisisisan. O'zbek tilida javob ber. "
                f"Model keylar: {', '.join(MODELS.keys())}. "
                f"Vaqt: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC."
            ),
            generation_config={"temperature": 0.1},
        )
        chat = model.start_chat(history=admin_sessions[uid][:-1])
        resp = chat.send_message(user_message, tools=tools_spec)
        part = resp.candidates[0].content.parts[0]

        if hasattr(part, "function_call") and part.function_call.name:
            fc     = part.function_call
            result = admin_exec_tool(fc.name, dict(fc.args), uid)
            admin_sessions[uid].append({"role": "model", "parts": [resp.candidates[0].content]})
            fn_resp = chat.send_message(genai.protos.Content(parts=[
                genai.protos.Part(function_response=genai.protos.FunctionResponse(
                    name=fc.name, response={"result": result}))
            ]))
            final = fn_resp.text.strip()
            admin_sessions[uid].append({"role": "model", "parts": [final]})
            return f"{final}\n\n📋 *Natija:*\n{result}"
        else:
            txt = part.text.strip()
            admin_sessions[uid].append({"role": "model", "parts": [txt]})
            return txt
    except Exception as e:
        return f"❌ Admin AI xatolik: {str(e)[:200]}"
    finally:
        genai.configure(api_key=GEMINI_API_KEY)

# ══════════════════════════════════════════════════════════════════
#  KLAVIATURALAR
# ══════════════════════════════════════════════════════════════════
def main_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    kb.add(KeyboardButton("🤖 Model"), KeyboardButton("🖼 Rasm"),  KeyboardButton("🔊 Ovoz"))
    kb.add(KeyboardButton("🧵 Thread"), KeyboardButton("🌍 Til"),   KeyboardButton("📄 Hujjatlar"))
    kb.add(KeyboardButton("🔔 Eslatma"), KeyboardButton("📊 Status"), KeyboardButton("❓ Yordam"))
    return kb

def admin_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("📊 Statistika"), KeyboardButton("📈 Analytics"))
    kb.add(KeyboardButton("👥 Foydalanuvchilar"), KeyboardButton("📢 Broadcast"))
    kb.add(KeyboardButton("🔍 User topish"), KeyboardButton("🚪 Chiqish"))
    return kb

def model_kb(current: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    for key, cfg in MODELS.items():
        v    = " 👁" if cfg["provider"] in VISION_PROVIDERS else ""
        tick = "✅ " if key == current else ""
        kb.add(InlineKeyboardButton(f"{tick}{cfg['label']}{v}", callback_data=f"model:{key}"))
    return kb

def lang_kb(current: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    for code, info in LANGUAGES.items():
        tick = "✅ " if code == current else ""
        kb.add(InlineKeyboardButton(f"{tick}{info['label']}", callback_data=f"lang:{code}"))
    return kb

def threads_kb(uid: int, active_id: int) -> InlineKeyboardMarkup:
    kb      = InlineKeyboardMarkup(row_width=1)
    threads = db_get_threads(uid)
    for th in threads:
        tick  = "✅ " if th["id"] == active_id else ""
        count = f" ({th['msg_count']}💬)" if th["msg_count"] else ""
        name  = textwrap.shorten(th["name"], 28)
        kb.add(InlineKeyboardButton(f"{tick}{name}{count}", callback_data=f"th_sw:{th['id']}"))
    kb.add(
        InlineKeyboardButton("➕ Yangi", callback_data="th_new"),
        InlineKeyboardButton("🗑 O'chir", callback_data=f"th_del:{active_id}"),
    )
    kb.add(InlineKeyboardButton("✏️ Nomlash", callback_data=f"th_ren:{active_id}"))
    return kb

def rag_kb(uid: int) -> InlineKeyboardMarkup:
    kb   = InlineKeyboardMarkup(row_width=1)
    docs = rag_list(uid)
    for doc in docs[:8]:
        name = textwrap.shorten(doc["filename"], 35)
        kb.add(InlineKeyboardButton(f"🗑 {name}", callback_data=f"rag_del:{doc['id']}"))
    if docs:
        kb.add(InlineKeyboardButton("🗑 Barchasini o'chirish", callback_data="rag_del_all"))
    kb.add(InlineKeyboardButton("✖️ Yopish", callback_data="rag_close"))
    return kb

def schedule_kb(uid: int) -> InlineKeyboardMarkup:
    kb    = InlineKeyboardMarkup(row_width=1)
    items = db_list_schedules(uid)
    for item in items[:8]:
        name = textwrap.shorten(item["text"], 25)
        kb.add(InlineKeyboardButton(
            f"🗑 {item['send_at'][5:16]} — {name}",
            callback_data=f"sch_del:{item['id']}"
        ))
    kb.add(InlineKeyboardButton("✖️ Yopish", callback_data="sch_close"))
    return kb

def premium_kb(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(
        f"⭐ {PREMIUM_STARS} Stars — 1 oy Premium",
        callback_data="buy_premium_1"
    ))
    kb.add(InlineKeyboardButton(
        f"⭐ {PREMIUM_STARS * 3} Stars — 3 oy Premium (-10%)",
        callback_data="buy_premium_3"
    ))
    return kb

def webapp_kb() -> InlineKeyboardMarkup:
    if not BOT_WEBAPP_URL:
        return InlineKeyboardMarkup()
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📱 Mini App", web_app=WebAppInfo(url=BOT_WEBAPP_URL)))
    return kb

# ══════════════════════════════════════════════════════════════════
#  GLOBAL STATE (in-memory)
# ══════════════════════════════════════════════════════════════════
image_mode:        dict[int, bool] = {}
image_style_sel:   dict[int, str]  = {}
admin_mode:        dict[int, bool] = {}
broadcast_state:   dict[int, bool] = {}
find_user_state:   dict[int, bool] = {}
thread_name_state: dict[int, bool] = {}
thread_ren_state:  dict[int, int]  = {}
schedule_state:    dict[int, dict] = {}  # uid → {step, text, send_at, repeat}

# ══════════════════════════════════════════════════════════════════
#  MIDDLEWARE — Anti-spam + ban check
# ══════════════════════════════════════════════════════════════════
def check_user(uid: int, lang: str = DEFAULT_LANG) -> bool:
    """True = davom etish mumkin. False = bloklangan."""
    user = db_get_user(uid)
    if user and user["banned"]:
        safe_send(uid, t(lang, "banned"))
        return False
    remaining = is_rate_blocked(uid)
    if remaining > 0:
        safe_send(uid, t(lang, "rate_limited", sec=int(remaining)))
        return False
    secs = record_message(uid)
    if secs > 0:
        safe_send(uid, t(lang, "rate_limited", sec=int(secs)))
        return False
    return True

# ══════════════════════════════════════════════════════════════════
#  HANDLERS — COMMANDS
# ══════════════════════════════════════════════════════════════════
@bot.message_handler(commands=["start"])
def cmd_start(msg):
    uid  = msg.chat.id
    user = msg.from_user
    db_ensure_user(uid, user.username or "", user.first_name or "")
    name = user.first_name or "Foydalanuvchi"
    adm  = "\n👑 /admin — Admin panel" if is_admin(uid) else ""
    app_btn = "\n📱 /app — Mini App" if BOT_WEBAPP_URL else ""
    bot.send_message(
        uid,
        f"👋 Salom, *{name}!*\n\n"
        "Men kuchli AI botman:\n\n"
        "💬 *Suhbat* — har qanday savolingizga javob\n"
        "🔄 *Auto fallback* — model ishlamasa keyingisi\n"
        "🧵 *Thread* — parallel suhbatlar\n"
        "👁 *Vision* — rasm tahlili\n"
        "🎤 *Voice* — ovozli xabar\n"
        "🖼 *Rasm* — DALL-E 3\n"
        "📄 *RAG* — hujjat asosida javob\n"
        "🌐 *Web Search* — internet qidiruvi\n"
        "🔔 *Eslatmalar* — scheduled xabarlar\n"
        "⭐ *Premium* — cheksiz limitlar"
        f"{adm}{app_btn}",
        parse_mode="Markdown",
        reply_markup=main_kb(),
    )

@bot.message_handler(commands=["myid"])
def cmd_myid(msg):
    bot.reply_to(msg, f"🪪 ID: `{msg.chat.id}`", parse_mode="Markdown")

@bot.message_handler(commands=["premium"])
def cmd_premium(msg):
    uid  = msg.chat.id
    user = db_get_user(uid)
    lang = user["lang"] if user and user["lang"] else DEFAULT_LANG
    db_ensure_user(uid, msg.from_user.username or "", msg.from_user.first_name or "")

    if user and is_premium(user):
        exp = user["premium_until"][:10] if user["premium_until"] else "—"
        safe_send(uid, f"⭐ *Premium faol!*\n\nMuddati: `{exp}`\n\n"
                       f"Kunlik limit: ♾ xabar, ♾ rasm.")
        return

    free_left = max(0, FREE_DAILY_MSG - (user["daily_msgs"] if user else 0))
    img_left  = max(0, FREE_DAILY_IMG - (user["daily_images"] if user else 0))

    safe_send(
        uid,
        f"⭐ *Premium*\n\n"
        f"*Bepul:* {FREE_DAILY_MSG} xabar/kun, {FREE_DAILY_IMG} rasm/kun\n"
        f"*Bugun qoldi:* {free_left} xabar, {img_left} rasm\n\n"
        f"*Premium:* Cheksiz xabar va rasm\n\n"
        f"{t(lang, 'premium_msg', stars=PREMIUM_STARS)}",
        reply_markup=premium_kb(lang),
    )

@bot.message_handler(commands=["schedule", "remind"])
def cmd_schedule(msg):
    uid  = msg.chat.id
    db_ensure_user(uid, msg.from_user.username or "", msg.from_user.first_name or "")
    items = db_list_schedules(uid)
    text  = (
        "🔔 *Eslatmalar*\n\n"
        f"Rejalashtirilgan: *{len(items)}* ta\n\n"
        "Yangi eslatma qo'shish uchun quyidagi formatda yozing:\n\n"
        "`/remind 2025-12-31 09:00 Yillik hisobot`\n"
        "`/remind 2025-12-31 09:00 daily Har kuni xabar`\n"
        "`/remind 2025-12-31 09:00 weekly Haftalik`\n\n"
        "Takrorlash: `none` (bir marta), `daily`, `weekly`, `monthly`"
    )
    safe_send(uid, text, reply_markup=schedule_kb(uid))

@bot.message_handler(commands=["schedules"])
def cmd_schedules(msg):
    cmd_schedule(msg)

@bot.message_handler(commands=["analytics"])
def cmd_analytics(msg):
    uid = msg.chat.id
    if not is_admin(uid):
        bot.send_message(uid, "❌ Faqat adminlar uchun.")
        return
    bot.send_message(uid, build_analytics_text(7), parse_mode="Markdown")

@bot.message_handler(commands=["admin"])
def cmd_admin(msg):
    uid = msg.chat.id
    if not is_admin(uid):
        if not ADMIN_IDS:
            bot.send_message(
                uid,
                f"⚠️ *Admin sozlanmagan!*\n\nID: `{uid}`\n\n"
                f"`.env` ga qo'shing:\n`ADMIN_IDS={uid}`",
                parse_mode="Markdown",
            )
        else:
            bot.send_message(uid, "❌ Siz admin emassiz.")
        return
    admin_mode[uid] = True
    image_mode[uid] = False
    admin_sessions.pop(uid, None)
    bot.send_message(
        uid,
        "👑 *Admin panelga xush kelibsiz!*\n\n"
        "O'zbek tilida buyruq bering:\n"
        "• `statistika ko'rsat`\n"
        "• `oxirgi 10 ta foydalanuvchi`\n"
        "• `barcha userlarga salom de`\n"
        "• `@username ni blokla`\n"
        "• `@username ga 1 oylik premium ber`\n"
        "• `analytics 14 kun`\n"
        "• `barchaga modelni groq_fast qil`",
        parse_mode="Markdown",
        reply_markup=admin_kb(),
    )

@bot.message_handler(commands=["app"])
def cmd_app(msg):
    uid = msg.chat.id
    if not BOT_WEBAPP_URL:
        bot.send_message(uid, "⚠️ Mini App URL sozlanmagan.")
        return
    bot.send_message(uid, "📱 *Mini App:*", parse_mode="Markdown", reply_markup=webapp_kb())

@bot.message_handler(commands=["help"])
def cmd_help(msg):
    lines = "\n".join(
        f"  {cfg['label']}" + (" 👁" if cfg["provider"] in VISION_PROVIDERS else "")
        for cfg in MODELS.values()
    )
    safe_send(
        msg.chat.id,
        "ℹ️ *Yordam*\n\n"
        "*/model* — AI modelni tanlash\n"
        "*/lang* — Til (uz/ru/en)\n"
        "*/thread* — Thread boshqaruvi\n"
        "*/docs* — Hujjatlar (RAG)\n"
        "*/image* — Rasm yaratish rejimi\n"
        "*/chat* — Suhbat rejimine qaytish\n"
        "*/voice* — Ovoz javob yoq/o'chir\n"
        "*/clear* — Thread tarixini tozalash\n"
        "*/remind* — Eslatma qo'shish\n"
        "*/schedules* — Eslatmalar ro'yxati\n"
        "*/premium* — Premium obuna\n"
        "*/status* — Joriy holat\n"
        "*/myid* — Telegram ID\n\n"
        f"*Modellar (👁=vision):*\n{lines}\n\n"
        "🔄 *Auto fallback:* model ishlamasa keyingisi\n"
        "📸 Rasm yuboring → vision tahlil\n"
        "🎤 Ovoz yuboring → matnga o'girish\n"
        "📄 Fayl yuboring → RAG aktivlashadi\n"
        "⚡ Guruhda: `@bot savol`",
    )

@bot.message_handler(commands=["model"])
def cmd_model(msg):
    uid  = msg.chat.id
    user = db_get_user(uid)
    curr = user["model"] if user else DEFAULT_MODEL
    bot.send_message(
        uid,
        f"⚙️ Hozirgi: *{MODELS.get(curr, MODELS[DEFAULT_MODEL])['label']}*\n\n"
        "👁 = vision | 🔄 = auto fallback yoqiq. Tanlang:",
        parse_mode="Markdown",
        reply_markup=model_kb(curr),
    )

@bot.message_handler(commands=["lang"])
def cmd_lang(msg):
    uid  = msg.chat.id
    user = db_get_user(uid)
    curr = user["lang"] if user and user["lang"] else DEFAULT_LANG
    bot.send_message(uid, f"🌍 Hozirgi: *{LANGUAGES.get(curr, LANGUAGES[DEFAULT_LANG])['label']}*\n\nTanlang:",
                     parse_mode="Markdown", reply_markup=lang_kb(curr))

@bot.message_handler(commands=["thread", "threads"])
def cmd_thread(msg):
    uid   = msg.chat.id
    tid   = db_get_active_thread(uid)
    ths   = db_get_threads(uid)
    cur   = next((th for th in ths if th["id"] == tid), None)
    aname = cur["name"] if cur else "—"
    bot.send_message(
        uid,
        f"🧵 *Thread boshqaruvi*\n\nFaol: *{aname}*\nJami: *{len(ths)}/{MAX_THREADS}*\n\nTanlang:",
        parse_mode="Markdown",
        reply_markup=threads_kb(uid, tid),
    )

@bot.message_handler(commands=["docs"])
def cmd_docs(msg):
    uid  = msg.chat.id
    docs = rag_list(uid)
    if not docs:
        bot.send_message(uid, "📄 *Hujjatlar bo'sh.*\n\nPDF, TXT, DOCX, MD yuboring!",
                         parse_mode="Markdown")
        return
    lines = [f"📄 `{d['id']}` — {d['filename']} ({d['created_at'][:10]})" for d in docs]
    bot.send_message(uid, f"📚 *Hujjatlar ({len(docs)} ta):*\n\n" + "\n".join(lines),
                     parse_mode="Markdown", reply_markup=rag_kb(uid))

@bot.message_handler(commands=["image"])
def cmd_image(msg):
    uid = msg.chat.id
    image_mode[uid] = True
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(
        InlineKeyboardButton("🎲 Auto",       callback_data="ist:"),
        InlineKeyboardButton("📷 Realistic",  callback_data="ist:realistic"),
        InlineKeyboardButton("🖼 Digital Art", callback_data="ist:digital_art"),
        InlineKeyboardButton("✏️ Sketch",     callback_data="ist:sketch"),
        InlineKeyboardButton("🌈 Anime",      callback_data="ist:anime"),
        InlineKeyboardButton("🎬 Cinematic",  callback_data="ist:cinematic"),
    )
    bot.send_message(
        uid,
        "🖼 *Rasm yaratish rejimi!*\n\nStiil tanlang (yoki o'tkazib yuboring):\n\n"
        "Keyin tavsif yozing — o'zbek tilida ham bo'ladi!\n\n/chat — orqaga",
        parse_mode="Markdown",
        reply_markup=kb,
    )

@bot.message_handler(commands=["chat"])
def cmd_chat(msg):
    uid = msg.chat.id
    image_mode[uid] = False
    admin_mode[uid] = False
    bot.send_message(uid, "💬 Suhbat rejimine qaytildi.", reply_markup=main_kb())

@bot.message_handler(commands=["voice"])
def cmd_voice(msg):
    uid  = msg.chat.id
    user = db_get_user(uid)
    new  = not bool(user["voice_on"]) if user else True
    db_set(uid, voice_on=int(new))
    bot.send_message(uid, f"🔊 Ovoz javob {'✅ yoqildi' if new else '❌ ochirildi'}.")

@bot.message_handler(commands=["clear"])
def cmd_clear(msg):
    uid = msg.chat.id
    tid = db_get_active_thread(uid)
    db_clear_thread(uid, tid)
    th  = db_get_thread(uid, tid)
    bot.send_message(uid, f"🗑 *{th['name'] if th else 'Thread'}* tarixi tozalandi!",
                     parse_mode="Markdown")

@bot.message_handler(commands=["status"])
def cmd_status(msg):
    uid  = msg.chat.id
    user = db_get_user(uid)
    if not user:
        bot.send_message(uid, "Avval /start bosing.")
        return
    model_key, lang, _, voice_on, tid = get_ctx(uid)
    label    = MODELS.get(model_key, MODELS[DEFAULT_MODEL])["label"]
    lang_lbl = LANGUAGES.get(lang, LANGUAGES[DEFAULT_LANG])["label"]
    n_msg    = len(db_get_history(uid, limit=9999, thread_id=tid))
    ths      = db_get_threads(uid)
    cur_th   = next((th for th in ths if th["id"] == tid), None)
    prem     = is_premium(user)
    prem_str = f"⭐ {user['premium_until'][:10]}" if prem else f"❌ ({user['daily_msgs']}/{FREE_DAILY_MSG} msg)"
    safe_send(
        uid,
        f"📊 *Joriy holat*\n\n"
        f"🤖 Model: *{label}*\n"
        f"🌍 Til: {lang_lbl}\n"
        f"🔊 Ovoz: {'✅' if voice_on else '❌'}\n"
        f"📍 Rejim: {'🖼 Rasm' if image_mode.get(uid) else '💬 Suhbat'}\n"
        f"⭐ Premium: {prem_str}\n"
        f"🧵 Thread: *{cur_th['name'] if cur_th else '—'}* ({n_msg} xabar)\n"
        f"🗂 Threadlar: {len(ths)}/{MAX_THREADS}\n"
        f"📄 Hujjatlar: {len(rag_list(uid))} ta\n"
        f"🔔 Eslatmalar: {len(db_list_schedules(uid))} ta\n"
        f"📅 Ro'yxatdan: {user['joined_at'][:10]}",
    )

# ══════════════════════════════════════════════════════════════════
#  HANDLERS — CALLBACKS
# ══════════════════════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda c: c.data.startswith("model:"))
def cb_model(call):
    uid = call.message.chat.id
    key = call.data.split(":", 1)[1]
    if key not in MODELS:
        bot.answer_callback_query(call.id, "Noma'lum model!")
        return
    db_set(uid, model=key)
    label = MODELS[key]["label"]
    v     = " (👁 Vision)" if MODELS[key]["provider"] in VISION_PROVIDERS else ""
    bot.answer_callback_query(call.id, f"✅ {label}")
    bot.edit_message_text(f"✅ *{label}* tanlandi.{v}",
                          chat_id=uid, message_id=call.message.message_id,
                          parse_mode="Markdown", reply_markup=model_kb(key))

@bot.callback_query_handler(func=lambda c: c.data.startswith("lang:"))
def cb_lang(call):
    uid  = call.message.chat.id
    lang = call.data.split(":", 1)[1]
    if lang not in LANGUAGES:
        bot.answer_callback_query(call.id, "Noma'lum til!")
        return
    db_set(uid, lang=lang)
    label = LANGUAGES[lang]["label"]
    bot.answer_callback_query(call.id, f"✅ {label}")
    bot.edit_message_text(f"✅ Til: *{label}*",
                          chat_id=uid, message_id=call.message.message_id,
                          parse_mode="Markdown", reply_markup=lang_kb(lang))

@bot.callback_query_handler(func=lambda c: c.data.startswith("th_sw:"))
def cb_th_switch(call):
    uid = call.message.chat.id
    tid = int(call.data.split(":", 1)[1])
    th  = db_get_thread(uid, tid)
    if not th:
        bot.answer_callback_query(call.id, "Topilmadi!")
        return
    db_set(uid, active_thread=tid)
    bot.answer_callback_query(call.id, f"✅ '{th['name']}'")
    try:
        bot.edit_message_text(
            f"🧵 Faol: *{th['name']}*\n\nTanlang:",
            chat_id=uid, message_id=call.message.message_id,
            parse_mode="Markdown", reply_markup=threads_kb(uid, tid))
    except Exception:
        pass

@bot.callback_query_handler(func=lambda c: c.data == "th_new")
def cb_th_new(call):
    uid = call.message.chat.id
    ths = db_get_threads(uid)
    if len(ths) >= MAX_THREADS:
        bot.answer_callback_query(call.id, f"❌ Max {MAX_THREADS} ta!")
        return
    bot.answer_callback_query(call.id)
    thread_name_state[uid] = True
    bot.send_message(uid, "✏️ Yangi thread nomi:")

@bot.callback_query_handler(func=lambda c: c.data.startswith("th_del:"))
def cb_th_del(call):
    uid = call.message.chat.id
    tid = int(call.data.split(":", 1)[1])
    ok  = db_delete_thread(uid, tid)
    if not ok:
        bot.answer_callback_query(call.id, "❌ O'chirib bo'lmaydi.")
        return
    bot.answer_callback_query(call.id, "✅ O'chirildi!")
    new_tid = db_get_active_thread(uid)
    try:
        bot.edit_message_text(
            "🧵 Thread o'chirildi. Tanlang:",
            chat_id=uid, message_id=call.message.message_id,
            parse_mode="Markdown", reply_markup=threads_kb(uid, new_tid))
    except Exception:
        pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("th_ren:"))
def cb_th_ren(call):
    uid = call.message.chat.id
    tid = int(call.data.split(":", 1)[1])
    bot.answer_callback_query(call.id)
    thread_ren_state[uid] = tid
    bot.send_message(uid, "✏️ Yangi nom:")

@bot.callback_query_handler(func=lambda c: c.data.startswith("rag_del:"))
def cb_rag_del(call):
    uid    = call.message.chat.id
    doc_id = int(call.data.split(":", 1)[1])
    ok     = rag_delete(uid, doc_id)
    bot.answer_callback_query(call.id, "✅ O'chirildi!" if ok else "❌ Topilmadi.")
    if ok:
        try:
            bot.edit_message_reply_markup(uid, call.message.message_id, reply_markup=rag_kb(uid))
        except Exception:
            pass

@bot.callback_query_handler(func=lambda c: c.data == "rag_del_all")
def cb_rag_del_all(call):
    uid = call.message.chat.id
    rag_delete_all(uid)
    bot.answer_callback_query(call.id, "✅ Barchasi o'chirildi!")
    try:
        bot.edit_message_text("🗑 Barcha hujjatlar o'chirildi.",
                              chat_id=uid, message_id=call.message.message_id)
    except Exception:
        pass

@bot.callback_query_handler(func=lambda c: c.data == "rag_close")
def cb_rag_close(call):
    bot.answer_callback_query(call.id)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("ist:"))
def cb_image_style(call):
    uid   = call.message.chat.id
    style = call.data.split(":", 1)[1]
    image_style_sel[uid] = style
    labels = {"": "🎲 Auto", "realistic": "📷 Realistic", "digital_art": "🖼 Digital Art",
              "sketch": "✏️ Sketch", "anime": "🌈 Anime", "cinematic": "🎬 Cinematic"}
    label = labels.get(style, style)
    bot.answer_callback_query(call.id, f"✅ {label}")
    try:
        bot.edit_message_text(
            f"✅ Stil: *{label}*\n\nEndi tavsif yozing:\n`kechasi shahar, neon chiroqlar`",
            chat_id=uid, message_id=call.message.message_id, parse_mode="Markdown")
    except Exception:
        pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("sch_del:"))
def cb_sch_del(call):
    uid = call.message.chat.id
    sid = int(call.data.split(":", 1)[1])
    ok  = db_delete_schedule(uid, sid)
    bot.answer_callback_query(call.id, "✅ O'chirildi!" if ok else "❌ Topilmadi.")
    if ok:
        try:
            bot.edit_message_reply_markup(uid, call.message.message_id,
                                          reply_markup=schedule_kb(uid))
        except Exception:
            pass

@bot.callback_query_handler(func=lambda c: c.data == "sch_close")
def cb_sch_close(call):
    bot.answer_callback_query(call.id)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_premium_"))
def cb_buy_premium(call):
    uid    = call.message.chat.id
    months = int(call.data.split("_")[-1])
    stars  = PREMIUM_STARS * months
    bot.answer_callback_query(call.id)
    try:
        bot.send_invoice(
            uid,
            title=f"⭐ Premium — {months} oy",
            description=f"Cheksiz xabarlar va rasmlar. {months} oylik obuna.",
            payload=f"premium_{uid}_{months}",
            provider_token="",           # Telegram Stars uchun bo'sh
            currency="XTR",              # Telegram Stars
            prices=[LabeledPrice(label=f"Premium {months} oy", amount=stars)],
        )
    except Exception as e:
        safe_send(uid, f"❌ To'lov tizimida xatolik: {str(e)[:100]}")

# ══════════════════════════════════════════════════════════════════
#  HANDLER — PRE-CHECKOUT (Telegram Stars)
# ══════════════════════════════════════════════════════════════════
@bot.pre_checkout_query_handler(func=lambda q: True)
def pre_checkout(query):
    bot.answer_pre_checkout_query(query.id, ok=True)

@bot.message_handler(content_types=["successful_payment"])
def successful_payment(msg):
    uid     = msg.chat.id
    payload = msg.successful_payment.invoice_payload
    parts   = payload.split("_")
    months  = int(parts[-1]) if parts[-1].isdigit() else 1
    grant_premium(uid, months)
    user = db_get_user(uid)
    lang = user["lang"] if user else DEFAULT_LANG
    exp  = user["premium_until"][:10] if user and user["premium_until"] else "—"
    safe_send(uid, f"⭐ *Premium faollashtirildi!*\n\nMuddati: `{exp}`\n\nRahmat!")
    log.info("[PREMIUM] uid=%s %s oy premium oldi", uid, months)

# ══════════════════════════════════════════════════════════════════
#  HANDLER — INLINE
# ══════════════════════════════════════════════════════════════════
@bot.inline_handler(func=lambda q: len(q.query.strip()) >= 3)
def handle_inline(query):
    uid  = query.from_user.id
    text = query.query.strip()
    _, lang, sys_p, _, _ = get_ctx(uid)
    try:
        ans   = ask_groq_raw("llama-3.1-8b-instant", [{"role": "user", "content": text}], sys_p)
        short = textwrap.shorten(ans, 800, placeholder="...")
    except Exception as e:
        short = f"Xatolik: {str(e)[:100]}"
    try:
        bot.answer_inline_query(query.id, [
            InlineQueryResultArticle(
                id="1", title="🤖 AI Javob",
                description=textwrap.shorten(short, 100),
                input_message_content=InputTextMessageContent(
                    message_text=f"❓ *{textwrap.shorten(text, 100)}*\n\n{short}",
                    parse_mode="Markdown",
                ),
            )
        ], cache_time=30)
    except Exception as e:
        log.error("[INLINE] %s", e)

@bot.inline_handler(func=lambda q: len(q.query.strip()) < 3)
def handle_inline_short(query):
    bot.answer_inline_query(query.id, [
        InlineQueryResultArticle(
            id="hint", title="✏️ Kamida 3 belgi...",
            description="Ko'proq yozing",
            input_message_content=InputTextMessageContent(message_text="..."),
        )
    ], cache_time=1)

# ══════════════════════════════════════════════════════════════════
#  HANDLER — DOCUMENT (RAG)
# ══════════════════════════════════════════════════════════════════
@bot.message_handler(content_types=["document"])
def handle_document(msg):
    uid  = msg.chat.id
    db_ensure_user(uid, msg.from_user.username or "", msg.from_user.first_name or "")
    user = db_get_user(uid)
    lang = user["lang"] if user else DEFAULT_LANG
    if not check_user(uid, lang):
        return

    doc      = msg.document
    filename = doc.file_name or "document"
    ext      = filename.lower().rsplit(".", 1)[-1]

    if ext not in ("pdf", "txt", "docx", "md", "csv"):
        bot.send_message(uid, "⚠️ Faqat *PDF, TXT, DOCX, MD, CSV* qabul qilinadi.",
                         parse_mode="Markdown")
        return
    if doc.file_size and doc.file_size > 20 * 1024 * 1024:
        bot.send_message(uid, "⚠️ Fayl 20 MB dan oshmasin.")
        return

    wait = bot.send_message(uid, f"📄 *{filename}* o'qilmoqda...", parse_mode="Markdown")
    try:
        data      = get_file_bytes(doc.file_id)
        doc_id, n = rag_save(uid, data, filename)
        bot.delete_message(uid, wait.message_id)
        if n == 0:
            safe_send(uid, f"ℹ️ *{filename}* avval yuklangan.")
        else:
            safe_send(uid, f"✅ *{filename}* yuklandi!\n📊 {n} ta bo'lak. Savol bering!")
    except Exception as e:
        bot.delete_message(uid, wait.message_id)
        safe_send(uid, f"❌ Fayl xatolik:\n`{str(e)[:200]}`")

# ══════════════════════════════════════════════════════════════════
#  HANDLER — PHOTO (Vision)
# ══════════════════════════════════════════════════════════════════
@bot.message_handler(content_types=["photo"])
def handle_photo(msg):
    uid  = msg.chat.id
    db_ensure_user(uid, msg.from_user.username or "", msg.from_user.first_name or "")
    user = db_get_user(uid)
    lang = user["lang"] if user else DEFAULT_LANG
    if not check_user(uid, lang):
        return
    if image_mode.get(uid):
        bot.send_message(uid, "ℹ️ Rasm yaratish rejimidasisiz. Vision uchun /chat bosing.")
        return

    photo                              = msg.photo[-1]
    caption                            = msg.caption or ""
    model_key, lang, sys_p, voice_on, tid = get_ctx(uid)
    label                              = MODELS.get(model_key, MODELS[DEFAULT_MODEL])["label"]

    wait = bot.send_message(uid, f"👁 *{label}* tahlil qilmoqda...", parse_mode="Markdown")
    try:
        img_bytes = get_file_bytes(photo.file_id)
        answer    = analyze_image(model_key, img_bytes, caption, sys_p)
        db_save_message(uid, "user", f"[Rasm{': '+caption if caption else ''}]", model_key, tid)
        db_save_message(uid, "assistant", answer, model_key, tid)
    except Exception as e:
        answer = error_msg(str(e))
    bot.delete_message(uid, wait.message_id)
    safe_send(uid, answer)
    if voice_on and answer and not answer.startswith(("❌", "⚠️", "💳", "ℹ️")):
        try:
            bot.send_voice(uid, text_to_voice(answer, lang), caption="🔊")
        except Exception as e:
            log.error("[VOICE] %s", e)

# ══════════════════════════════════════════════════════════════════
#  HANDLER — VOICE (STT)
# ══════════════════════════════════════════════════════════════════
@bot.message_handler(content_types=["voice"])
def handle_voice(msg):
    uid  = msg.chat.id
    db_ensure_user(uid, msg.from_user.username or "", msg.from_user.first_name or "")
    user = db_get_user(uid)
    lang = user["lang"] if user else DEFAULT_LANG
    if not check_user(uid, lang):
        return

    model_key, lang, sys_p, voice_on, tid = get_ctx(uid)
    label = MODELS.get(model_key, MODELS[DEFAULT_MODEL])["label"]

    wait = bot.send_message(uid, "🎤 Whisper matnga o'girmoqda...")
    try:
        audio_bytes = get_file_bytes(msg.voice.file_id)
        transcribed = transcribe_voice(audio_bytes)
    except Exception as e:
        bot.delete_message(uid, wait.message_id)
        safe_send(uid, f"❌ STT xatolik:\n`{str(e)[:200]}`")
        return

    bot.delete_message(uid, wait.message_id)
    if not transcribed:
        safe_send(uid, "⚠️ Matn aniqlanmadi.")
        return
    safe_send(uid, f"🎤 *Siz aytdingiz:*\n_{transcribed}_")

    if admin_mode.get(uid):
        r = admin_ai_chat(uid, transcribed)
        safe_send(uid, r)
        return

    if image_mode.get(uid):
        if not check_img_limit(uid):
            safe_send(uid, t(lang, "img_limit"))
            return
        wait2 = bot.send_message(uid, "🎨 Rasm yaratilmoqda... (20-40s)")
        try:
            style     = image_style_sel.get(uid, "")
            img_bytes = generate_image(transcribed, style)
            db_save_image(uid, transcribed)
            bot.delete_message(uid, wait2.message_id)
            buf = io.BytesIO(img_bytes); buf.name = "image.png"
            bot.send_photo(uid, buf,
                caption=f"🖼 _{textwrap.shorten(transcribed, 80)}_",
                parse_mode="Markdown")
        except ValueError as e:
            bot.delete_message(uid, wait2.message_id); safe_send(uid, str(e))
        except Exception as e:
            bot.delete_message(uid, wait2.message_id); safe_send(uid, error_msg(str(e)))
        return

    if not check_msg_limit(uid):
        safe_send(uid, t(lang, "daily_limit"))
        return

    rag_ctx = rag_search(uid, transcribed)
    db_save_message(uid, "user", transcribed, model_key, tid)
    history = db_get_history(uid, thread_id=tid)
    if rag_ctx:
        history = history[:-1] + [{"role": "user",
                                    "content": rag_ctx + "\n\nSavol: " + transcribed}]

    wait3 = bot.send_message(uid, f"⏳ *{label}* javob...", parse_mode="Markdown")
    try:
        answer = get_answer(model_key, history, sys_p)
        db_save_message(uid, "assistant", answer, model_key, tid)
    except Exception as e:
        answer = error_msg(str(e))
        pop_last_user_msg(uid, tid)
    bot.delete_message(uid, wait3.message_id)
    safe_send(uid, answer)
    if voice_on and answer and not answer.startswith(("❌", "⚠️", "💳")):
        try:
            bot.send_voice(uid, text_to_voice(answer, lang), caption="🔊")
        except Exception as e:
            log.error("[VOICE] %s", e)

# ══════════════════════════════════════════════════════════════════
#  HANDLER — WEBAPP DATA
# ══════════════════════════════════════════════════════════════════
@bot.message_handler(content_types=["web_app_data"])
def handle_webapp(msg):
    uid = msg.chat.id
    db_ensure_user(uid, msg.from_user.username or "", msg.from_user.first_name or "")
    try:
        data = json.loads(msg.web_app_data.data)
    except Exception:
        return

    action = data.get("action", "")

    if action == "chat":
        text      = data.get("text", "").strip()[:4000]
        model_key = data.get("model", DEFAULT_MODEL)
        if model_key not in MODELS:
            model_key = DEFAULT_MODEL
        lang = data.get("lang", DEFAULT_LANG)
        if lang not in LANGUAGES:
            lang = DEFAULT_LANG
        if not text:
            return
        db_set(uid, model=model_key, lang=lang)
        if not check_msg_limit(uid):
            safe_send(uid, t(lang, "daily_limit"))
            return
        sys_p     = get_system_prompt(lang)
        tid       = db_get_active_thread(uid)
        label     = MODELS.get(model_key, MODELS[DEFAULT_MODEL])["label"]
        rag_ctx   = rag_search(uid, text)
        db_save_message(uid, "user", text, model_key, tid)
        history   = db_get_history(uid, thread_id=tid)
        if rag_ctx:
            history = history[:-1] + [{"role": "user",
                                        "content": rag_ctx + "\n\nSavol: " + text}]
        wait = bot.send_message(uid, f"📱 ⏳ *{label}*...", parse_mode="Markdown")
        try:
            answer = get_answer(model_key, history, sys_p)
            db_save_message(uid, "assistant", answer, model_key, tid)
        except Exception as e:
            answer = error_msg(str(e))
            pop_last_user_msg(uid, tid)
        bot.delete_message(uid, wait.message_id)
        safe_send(uid, f"📱 *Siz:* {text}\n\n{answer}")

    elif action == "generate_image":
        prompt = data.get("prompt", "").strip()[:500]
        style  = data.get("style", "")
        if not prompt or not check_img_limit(uid):
            if not prompt:
                return
            user = db_get_user(uid)
            lang = user["lang"] if user else DEFAULT_LANG
            safe_send(uid, t(lang, "img_limit"))
            return
        wait = bot.send_message(uid, f"📱 🎨 Rasm yaratilmoqda...")
        try:
            img_bytes = generate_image(prompt, style)
            db_save_image(uid, prompt)
            bot.delete_message(uid, wait.message_id)
            buf = io.BytesIO(img_bytes); buf.name = "image.png"
            bot.send_photo(uid, buf,
                caption=f"🖼 _{textwrap.shorten(prompt, 80)}_",
                parse_mode="Markdown")
        except ValueError as e:
            bot.delete_message(uid, wait.message_id); safe_send(uid, str(e))
        except Exception as e:
            bot.delete_message(uid, wait.message_id); safe_send(uid, error_msg(str(e)))

# ══════════════════════════════════════════════════════════════════
#  HANDLER — REPLY KEYBOARD
# ══════════════════════════════════════════════════════════════════
BUTTON_MAP = {
    "🤖 Model":     cmd_model,
    "📊 Status":    cmd_status,
    "🔔 Eslatma":   cmd_schedule,
    "❓ Yordam":    cmd_help,
    "🖼 Rasm":      cmd_image,
    "🔊 Ovoz":      cmd_voice,
    "🌍 Til":       cmd_lang,
    "📄 Hujjatlar": cmd_docs,
    "🧵 Thread":    cmd_thread,
}

ADMIN_BUTTON_MAP = {
    "📊 Statistika":    "statistika ko'rsat",
    "📈 Analytics":     "analytics 7 kun",
    "👥 Foydalanuvchilar": "oxirgi 10 ta foydalanuvchi",
    "📢 Broadcast":     None,
    "🔍 User topish":   None,
    "🚪 Chiqish":       "__exit__",
}

@bot.message_handler(func=lambda m: m.text in BUTTON_MAP or m.text in ADMIN_BUTTON_MAP)
def handle_buttons(msg):
    uid  = msg.chat.id
    text = msg.text

    if text in ADMIN_BUTTON_MAP and admin_mode.get(uid):
        val = ADMIN_BUTTON_MAP[text]
        if val == "__exit__":
            admin_mode[uid] = False
            admin_sessions.pop(uid, None)
            bot.send_message(uid, "✅ Admin paneldan chiqdingiz.", reply_markup=main_kb())
        elif val is None:
            if text == "📢 Broadcast":
                broadcast_state[uid] = True
                bot.send_message(uid, "✏️ Barcha userlarga yuboriladigan xabar:")
            elif text == "🔍 User topish":
                find_user_state[uid] = True
                bot.send_message(uid, "🔍 @username yoki ID:")
        else:
            result = admin_ai_chat(uid, val)
            safe_send(uid, result)
        return

    if text in BUTTON_MAP:
        BUTTON_MAP[text](msg)

# ══════════════════════════════════════════════════════════════════
#  HANDLER — MATN (asosiy mantiq)
# ══════════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: True)
def handle_text(msg):
    uid  = msg.chat.id
    text = (msg.text or "").strip()
    if not text:
        return

    db_ensure_user(uid, msg.from_user.username or "", msg.from_user.first_name or "")
    user = db_get_user(uid)
    lang = user["lang"] if user and user["lang"] else DEFAULT_LANG

    # Xavfsizlik
    if not check_user(uid, lang):
        return

    model_key, lang, sys_p, voice_on, tid = get_ctx(uid)
    label = MODELS.get(model_key, MODELS[DEFAULT_MODEL])["label"]

    # ── /remind shortcut: /remind 2025-12-31 09:00 [repeat] matn ──
    remind_match = re.match(
        r"^/remind\s+(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})(?:\s+(daily|weekly|monthly))?\s+(.+)$",
        text, re.DOTALL
    )
    if remind_match:
        date_str, time_str, repeat, rtext = remind_match.groups()
        repeat   = repeat or "none"
        send_at  = f"{date_str} {time_str}:00"
        try:
            datetime.strptime(send_at, "%Y-%m-%d %H:%M:%S")
            sid = db_add_schedule(uid, rtext.strip(), send_at, repeat)
            safe_send(uid,
                f"✅ Eslatma qo'shildi!\n\n"
                f"📅 Vaqt: `{send_at[:16]}`\n"
                f"🔁 Takrorlash: `{repeat}`\n"
                f"📝 Matn: {rtext[:100]}"
            )
        except ValueError:
            safe_send(uid, "❌ Sana formati noto'g'ri. Misol: `2025-12-31 09:00`")
        return

    # ── Admin states ────────────────────────────────────────────────
    if broadcast_state.get(uid):
        broadcast_state[uid] = False
        result = admin_ai_chat(uid, f"Barcha foydalanuvchilarga shu xabarni yubor: {text}")
        safe_send(uid, result)
        return

    if find_user_state.get(uid):
        find_user_state[uid] = False
        result = admin_ai_chat(uid, f"Ushbu foydalanuvchini top: {text}")
        safe_send(uid, result)
        return

    # ── Thread state ────────────────────────────────────────────────
    if thread_name_state.get(uid):
        thread_name_state[uid] = False
        tid2 = db_create_thread(uid, text)
        if tid2 is None:
            safe_send(uid, f"❌ Max {MAX_THREADS} ta thread.")
        else:
            safe_send(uid, f"✅ Thread *{text}* yaratildi!", reply_markup=main_kb())
        return

    if uid in thread_ren_state:
        old_tid = thread_ren_state.pop(uid)
        ok = db_rename_thread(uid, old_tid, text)
        safe_send(uid, f"✅ Thread *{text}* deb nomlandi!" if ok else "❌ Topilmadi.")
        return

    # ── Admin panel ────────────────────────────────────────────────
    if admin_mode.get(uid):
        wait   = bot.send_message(uid, "👑 Admin AI...")
        result = admin_ai_chat(uid, text)
        bot.delete_message(uid, wait.message_id)
        safe_send(uid, result)
        return

    # ── Rasm yaratish ──────────────────────────────────────────────
    if image_mode.get(uid):
        if not check_img_limit(uid):
            safe_send(uid, t(lang, "img_limit"))
            return
        style = image_style_sel.get(uid, "")
        wait  = bot.send_message(uid, "🎨 Rasm yaratilmoqda... (20-40s)")
        try:
            img_bytes = generate_image(text, style)
            db_save_image(uid, text)
            bot.delete_message(uid, wait.message_id)
            buf = io.BytesIO(img_bytes); buf.name = "image.png"
            bot.send_photo(uid, buf,
                caption=f"🖼 _{textwrap.shorten(text, 80)}_",
                parse_mode="Markdown")
        except ValueError as e:
            bot.delete_message(uid, wait.message_id); safe_send(uid, str(e))
        except Exception as e:
            bot.delete_message(uid, wait.message_id); safe_send(uid, error_msg(str(e)))
        return

    # ── Kunlik limit tekshirish ────────────────────────────────────
    if not check_msg_limit(uid):
        safe_send(uid, t(lang, "daily_limit"))
        return

    # ── Suhbat + RAG ───────────────────────────────────────────────
    rag_ctx   = rag_search(uid, text)
    rag_badge = " 📄" if rag_ctx else ""

    db_save_message(uid, "user", text, model_key, tid)
    history = db_get_history(uid, thread_id=tid)
    if rag_ctx:
        history = history[:-1] + [{"role": "user",
                                    "content": rag_ctx + "\n\nFoydalanuvchi savoli: " + text}]

    wait = bot.send_message(uid,
        f"⏳ *{label}*{rag_badge} javob tayyorlamoqda...",
        parse_mode="Markdown")

    try:
        answer = get_answer(model_key, history, sys_p)
        db_save_message(uid, "assistant", answer, model_key, tid)
    except Exception as e:
        answer = error_msg(str(e))
        pop_last_user_msg(uid, tid)

    bot.delete_message(uid, wait.message_id)
    safe_send(uid, answer)

    if voice_on and answer and not answer.startswith(("❌", "⚠️", "💳")):
        try:
            bot.send_voice(uid, text_to_voice(answer, lang), caption="🔊")
        except Exception as e:
            log.error("[VOICE] %s", e)

# ══════════════════════════════════════════════════════════════════
#  WEBHOOK — Flask (Render.com uchun)
# ══════════════════════════════════════════════════════════════════
@app.route(f"/{SECRET_TOKEN}", methods=["POST"])
def webhook():
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != SECRET_TOKEN:
        abort(403)
    try:
        import telebot
        update = telebot.types.Update.de_json(request.get_data(as_text=True))
        bot.process_new_updates([update])
    except Exception as e:
        log.error("[WEBHOOK] %s", e)
    return "OK", 200

@app.route("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}, 200

@app.route("/")
def index():
    return "🤖 Super AI Bot — Running", 200

def setup_webhook():
    if not WEBHOOK_URL:
        log.info("WEBHOOK_URL yo'q — polling rejimida ishlatiladi")
        return False
    url = f"{WEBHOOK_URL}/{SECRET_TOKEN}"
    try:
        bot.remove_webhook()
        time.sleep(0.5)
        bot.set_webhook(
            url=url,
            secret_token=SECRET_TOKEN,
            allowed_updates=["message", "callback_query", "inline_query",
                             "pre_checkout_query", "chosen_inline_result"],
        )
        log.info("[WEBHOOK] O'rnatildi: %s", url)
        return True
    except Exception as e:
        log.error("[WEBHOOK] O'rnatilmadi: %s", e)
        return False

def setup_mini_app():
    if not BOT_WEBAPP_URL:
        return
    try:
        bot.set_chat_menu_button(menu_button=MenuButtonWebApp(
            text="📱 App", web_app=WebAppInfo(url=BOT_WEBAPP_URL)
        ))
        log.info("[WEBAPP] %s", BOT_WEBAPP_URL)
    except Exception as e:
        log.warning("[WEBAPP] %s", e)

# ══════════════════════════════════════════════════════════════════
#  ISHGA TUSHIRISH
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    db_init()
    setup_mini_app()

    # Scheduler thread
    sch_thread = threading.Thread(target=_scheduler_loop, daemon=True)
    sch_thread.start()

    print("=" * 65)
    print("🤖  SUPER AI BOT  —  ULTIMATE EDITION  v3.0")
    print(f"🗄   Database    : {DB_PATH}")
    print(f"📋  Modellar    : {', '.join(MODELS.keys())}")
    print(f"🔄  Auto fallback: {' → '.join(MODEL_FALLBACK_CHAIN[:3])}...")
    print(f"🔒  Anti-spam   : {RATE_MSG_LIMIT} msg/{RATE_WINDOW}s")
    print(f"⭐  Premium     : {PREMIUM_STARS} Stars/oy | Free: {FREE_DAILY_MSG} msg/kun")
    print(f"🔔  Scheduler   : aktiv (30s interval)")
    print(f"🎤  STT          : Groq Whisper-large-v3")
    print(f"🌐  Web Search   : Gemini google_search")
    print(f"📱  Mini App     : {BOT_WEBAPP_URL or 'sozlanmagan'}")
    print(f"👑  Admin IDs   : {ADMIN_IDS or 'sozlanmagan — /myid yozing'}")

    if WEBHOOK_URL:
        ok = setup_webhook()
        if ok:
            print(f"🌐  Webhook     : {WEBHOOK_URL}/{SECRET_TOKEN[:8]}...")
            print(f"🚀  Port         : {PORT}")
            print("=" * 65)
            app.run(host="0.0.0.0", port=PORT, debug=False)
        else:
            print("⚠️  Webhook xato — polling rejimiga o'tildi")
            print("=" * 65)
            bot.remove_webhook()
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
    else:
        print("⚡  Rejim        : Long Polling")
        print("=" * 65)
        bot.remove_webhook()
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
