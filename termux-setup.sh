#!/data/data/com.termux/files/usr/bin/bash
# Setup AI Remote - Termux to VPS

VPS_IP="152.55.176.178"
MODEL="qwen2.5-coder:1.5b"

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
    return 1
  fi
  curl -s http://152.55.176.178:11434/api/generate \
    -d "{\"model\":\"qwen2.5-coder:1.5b\",\"prompt\":\"$*\",\"stream\":false}" \
    | jq -r '.response'
}

# 🤖 AI Coding (lebih detail)
aic() {
  if [ -z "$1" ]; then
    echo "Gunakan: aic \"bikin kode ...\""
    return 1
  fi
  curl -s http://152.55.176.178:11434/api/generate \
    -d "{\"model\":\"qwen2.5-coder:1.5b\",\"prompt\":\"Kamu adalah programmer expert. $*\",\"stream\":false}" \
    | jq -r '.response'
}

# 📝 AI Chat biasa
aichat() {
  if [ -z "$1" ]; then
    echo "Gunakan: aichat \"pesan\""
    return 1
  fi
  curl -s http://152.55.176.178:11434/api/chat \
    -d "{\"model\":\"qwen2.5-coder:1.5b\",\"messages\":[{\"role\":\"user\",\"content\":\"$*\"}],\"stream\":false}" \
    | jq -r '.message.content'
}
EOF

source ~/.bashrc

echo ""
echo "✅ SETUP SELESAI!"
echo "================================"
echo ""
echo "Perintah yang tersedia:"
echo "  ai \"pesan\"       → AI general"
echo "  aic \"bikin app\"  → AI coding"
echo "  aichat \"halo\"    → AI chat biasa"
echo ""
echo "Contoh:"
echo "  ai \"bikin fungsi python reverse string\""
echo "  aic \"buat REST API Flask dengan SQLite\""
echo "  aichat \"siapa presiden Indonesia?\""
echo ""
echo "📌 Catatan: Butuh koneksi internet!"
