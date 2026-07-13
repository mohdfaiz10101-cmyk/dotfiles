#!/bin/bash
# Music Auto-Decrypt Watcher
# Watches ~/Music/incoming for encrypted files and decrypts them
# Supports: .ncm (NetEase), .qmc/.mgg/.mflac (QQ), .kgm/.vpr (Kugou)

WATCH_DIR="$HOME/Music/incoming"
DECRYPT_DIR="$HOME/Music/NetEase_Decrypted"
NCMDUMP="$HOME/.local/bin/ncmdump"

mkdir -p "$WATCH_DIR"

inotifywait -m -e close_write -e moved_to --format '%f' "$WATCH_DIR" | while read FILE; do
    EXT="${FILE##*.}"
    FULLPATH="$WATCH_DIR/$FILE"
    
    case "$EXT" in
        ncm)
            echo "[$(date +%H:%M)] Decrypting NCM: $FILE"
            $NCMDUMP "$FULLPATH" -o "$DECRYPT_DIR/" 2>/dev/null && \
                rm "$FULLPATH" && \
                notify-send "音乐解密完成" "$FILE → $DECRYPT_DIR" 2>/dev/null
            ;;
        *)
            echo "[$(date +%H:%M)] Unknown format: $FILE — skipping"
            ;;
    esac
done
