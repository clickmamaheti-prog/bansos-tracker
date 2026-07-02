#!/bin/bash
# Build APK manual — BansosApp
# Jalankan dari folder android/BansosApp

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

echo "=== 1. Bersihkan build dir ==="
rm -rf build
mkdir -p build/out build/obj build/gen build/dex-out

echo "=== 2. Compile resources (AAPT) ==="
$AAPT package -f -m -J build/gen \
  -M app/src/main/AndroidManifest.xml \
  -S app/src/main/res \
  -I $PLATFORM

echo "=== 3. Compile Java (javac) ==="
javac -source 8 -target 8 -cp $PLATFORM \
  -d build/obj \
  -s build/gen \
  app/src/main/java/com/kemensos/bansos/*.java

echo "=== 4. Convert to DEX (d8) ==="
$D8 --output build/dex-out --min-api 21 \
  --lib $PLATFORM \
  $(find build/obj -name "*.class")

echo "=== 5. Package APK (AAPT) ==="
$AAPT package -f -M app/src/main/AndroidManifest.xml \
  -S app/src/main/res \
  -I $PLATFORM \
  -F build/out/unsigned.apk \
  build/obj

echo "=== 6. Inject classes.dex ==="
cd build/dex-out && zip -r ../out/unsigned.apk classes.dex && cd ../..

echo "=== 7. Zipalign ==="
$ZIPALIGN -f 4 build/out/unsigned.apk build/out/aligned.apk

echo "=== 8. Sign APK ==="
$APKSIGNER sign \
  --ks $KS --ks-pass pass:$KSPASS \
  --key-pass pass:$KSPASS \
  --ks-key-alias $ALIAS \
  --out build/out/bantuan-sosial.apk \
  build/out/aligned.apk

echo "=== 9. Verify ==="
$APKSIGNER verify build/out/bantuan-sosial.apk

echo ""
echo "✅ APK siap: build/out/bantuan-sosial.apk"
ls -lh build/out/bantuan-sosial.apk
