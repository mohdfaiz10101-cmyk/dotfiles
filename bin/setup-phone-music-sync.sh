#!/bin/bash
# Phone Music Sync Setup — run when phone ADB is available
# Requires: ADB connection, Syncthing on phone, Musicolet

set -e

echo "=== Phone Music Sync Setup ==="

# Step 1: Check ADB
adb devices | grep -q "device$" || { echo "[FAIL] No ADB device. Connect phone first."; exit 1; }
echo "[ok] ADB device connected"

# Step 2: Install Syncthing APK if not already on phone
SYNCTHING_APK="https://github.com/syncthing/syncthing-android/releases/latest/download/app-release.apk"
if ! adb shell pm list packages | grep -q "com.nutomic.syncthingandroid"; then
    echo "Downloading Syncthing APK..."
    curl -L "$SYNCTHING_APK" -o /tmp/syncthing.apk
    adb install /tmp/syncthing.apk && echo "[ok] Syncthing installed"
else
    echo "[ok] Syncthing already installed"
fi

# Step 3: Install Musicolet (folder-based offline player)
if ! adb shell pm list packages | grep -q "com.kappdevelop.musicolet"; then
    echo "Installing Musicolet..."
    # Try from Aurora Store or direct APK
    MUSICOLET_APK=$(curl -s "https://api.github.com/repos/ImKKingshuk/Musicolet-APK/releases/latest" | python3 -c "import sys,json; print(json.load(sys.stdin)['assets'][0]['browser_download_url'])" 2>/dev/null)
    if [ -n "$MUSICOLET_APK" ]; then
        curl -L "$MUSICOLET_APK" -o /tmp/musicolet.apk
        adb install /tmp/musicolet.apk && echo "[ok] Musicolet installed"
    else
        echo "[skip] Musicolet: install from Play Store or F-Droid manually"
    fi
else
    echo "[ok] Musicolet already installed"
fi

# Step 4: Create Music directory on phone
adb shell mkdir -p /sdcard/Music 2>/dev/null
echo "[ok] /sdcard/Music created on phone"

# Step 5: Get NixOS Syncthing device ID for pairing
SYNCTHING_ID=$(curl -s -H "X-API-Key: tRL7uuKKiatCjtrsAh99ZKbnxssnXDYr" http://localhost:8384/rest/config | python3 -c "import sys,json; print(json.load(sys.stdin)['devices'][0]['deviceID'])")
echo ""
echo "=== Manual Steps Required ==="
echo "1. Open Syncthing on phone"
echo "2. Add Device: $SYNCTHING_ID"
echo "3. Accept pairing on NixOS (check http://localhost:8384)"
echo "4. Add folder 'music-library' on phone, path: /sdcard/Music"
echo "5. Open Musicolet → Settings → Folders → Add /sdcard/Music"
echo ""
echo "Syncthing will auto-sync all music over LAN/WiFi (no internet needed)"
echo "NixOS Syncthing ID: $SYNCTHING_ID"
