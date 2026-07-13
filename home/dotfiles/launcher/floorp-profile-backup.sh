#!/run/current-system/sw/bin/bash
# Full Floorp profile backup - critical files for crash recovery
# Restores: bookmarks, cookies, login state, preferences
# Keeps last 7 daily backups
set -euo pipefail

BACKUP_ROOT="/mnt/pool/home-offload/floorp-profile-backups"
KEEP_DAYS=7

# Detect active profile from profiles.ini
PROFILES_INI="$HOME/.floorp/profiles.ini"
if [ ! -f "$PROFILES_INI" ]; then
    echo "[SKIP] No Floorp profiles.ini found"
    exit 0
fi

# Find default profile path
PROFILE_PATH=$(grep -A5 '\[Profile' "$PROFILES_INI" | grep 'Path=' | head -1 | cut -d= -f2)
if [ -z "$PROFILE_PATH" ]; then
    echo "[SKIP] No profile found in profiles.ini"
    exit 0
fi

PROFILE_DIR="$HOME/.floorp/$PROFILE_PATH"
if [ ! -d "$PROFILE_DIR" ]; then
    echo "[SKIP] Profile directory not found: $PROFILE_DIR"
    exit 0
fi

TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_DIR="$BACKUP_ROOT/$TIMESTAMP"
mkdir -p "$BACKUP_DIR"

# Critical files to backup
CRITICAL_FILES=(
    places.sqlite
    cookies.sqlite
    logins.json
    logins.db
    logins-backup.json
    key4.db
    cert9.db
    pkcs11.txt
    prefs.js
    extensions.json
    containers.json
    handlers.json
    search.json.mozlz4
    xulstore.json
    webappsstore.sqlite
    formhistory.sqlite
    permissions.sqlite
)

for f in "${CRITICAL_FILES[@]}"; do
    src="$PROFILE_DIR/$f"
    if [ -f "$src" ]; then
        cp "$src" "$BACKUP_DIR/" 2>/dev/null || true
    fi
done

# Copy bookmark backups directory
if [ -d "$PROFILE_DIR/bookmarkbackups" ]; then
    cp -r "$PROFILE_DIR/bookmarkbackups" "$BACKUP_DIR/" 2>/dev/null || true
fi

# Copy session store for tab recovery
if [ -f "$PROFILE_DIR/sessionstore.jsonlz4" ]; then
    cp "$PROFILE_DIR/sessionstore.jsonlz4" "$BACKUP_DIR/" 2>/dev/null || true
fi

# Record profile info
echo "profile=$PROFILE_PATH" > "$BACKUP_DIR/backup-info.txt"
echo "date=$(date '+%Y-%m-%d %H:%M:%S')" >> "$BACKUP_DIR/backup-info.txt"
echo "hostname=$(hostname)" >> "$BACKUP_DIR/backup-info.txt"

# Cleanup old backups (keep last N days)
if [ -d "$BACKUP_ROOT" ]; then
    find "$BACKUP_ROOT" -maxdepth 1 -type d -mtime +$KEEP_DAYS -exec rm -rf {} \; 2>/dev/null || true
fi

FILE_COUNT=$(find "$BACKUP_DIR" -type f | wc -l)
echo "[OK] $(date '+%Y-%m-%d %H:%M') Floorp profile backup: $FILE_COUNT files -> $BACKUP_DIR"
