#!/data/data/com.termux/files/usr/bin/bash
# Setup AI Remote - Termux to VPS (via Cloudflare Tunnel)

VPS_URL="https://bansos.jokichannel.eu.org"
echo "🚀 Setup AI Remote untuk Termux..."
echo "================================"

# Install dependencies
pkg update -y
pkg install -y curl jq

# Buat fungsi AI
cat >> ~/.bashrc << 'EOF'

# 🧠 AI Remote dari VPS
ai() {
  if [ -z "$1" ]; then
    echo "Gunakan: ai \"pertanyaan kamu\""
    echo "Contoh: ai \"bikin kode python kalkulator\""
    return 1
  fi
  curl -s https://bansos.jokichannel.eu.org/api/ai/generate \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"qwen2.5-coder:1.5b\",\"prompt\":\"$*\"}" \
    | jq -r '.response // .error'
}

# 🤖 AI Coding (lebih detail)
aic() {
  if [ -z "$1" ]; then
    echo "Gunakan: aic \"bikin kode ...\""
    echo "Contoh: aic \"buat REST API Flask dengan SQLite\""
    return 1
  fi
  curl -s https://bansos.jokichannel.eu.org/api/ai/generate \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"qwen2.5-coder:1.5b\",\"prompt\":\"Kamu adalah programmer expert. $*\"}" \
    | jq -r '.response // .error'
}

# 📝 AI Chat
aichat() {
  if [ -z "$1" ]; then
    echo "Gunakan: aichat \"pesan\""
    echo "Contoh: aichat \"siapa presiden Indonesia?\""
    return 1
  fi
  curl -s https://bansos.jokichannel.eu.org/api/ai/chat \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"qwen2.5-coder:1.5b\",\"messages\":[{\"role\":\"user\",\"content\":\"$*\"}]}" \
    | jq -r '.response // .error'
}

# 🔍 Lihat model yang tersedia
aimodels() {
  curl -s https://bansos.jokichannel.eu.org/api/ai/tags | jq -r '.models[]'
}
EOF

source ~/.bashrc

echo ""
echo "✅ SETUP SELESAI!"
echo "================================"
echo ""
echo "Perintah yang tersedia:"
echo "  ai \"pesan\"       → AI general"
echo "  aic \"bikin app\"  → AI coding expert"
echo "  aichat \"halo\"    → AI chat"
echo "  aimodels         → Lihat model tersedia"
echo ""
echo "Contoh:"
echo "  ai \"bikin fungsi python reverse string\""
echo "  aic \"buat REST API Flask dengan SQLite\""
echo "  aichat \"siapa presiden Indonesia?\""
echo "  aimodels"
echo ""
echo "📌 Butuh koneksi internet!"
