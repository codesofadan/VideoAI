#!/usr/bin/env bash
# Render social clips from the Aug 23 meeting: blur Shayan's tile, 1920x1080, loudness-normalised.
set -euo pipefail
SRC="../../Impromptu Google Meet Meeting - Aug 23 2026 (2).mp4"
MASK="tilemask.png"
OUT="../../shayan"
mkdir -p "$OUT"

FC='[0:v]split=2[base][pre];[pre]crop=417:549:434:113,scale=14:18,scale=417:549:flags=neighbor,gblur=sigma=16[blr];[1:v]format=gray[mk];[blr][mk]alphamerge[bla];[base][bla]overlay=434:113[bd];[bd]crop=837:549:13:113,scale=1646:1080:flags=lanczos,pad=1920:1080:137:0:color=0x131314,fps=30,format=yuv420p[v]'

# clips.tsv: name <TAB> start <TAB> duration
while IFS=$'\t' read -r name start dur; do
  [ -z "${name:-}" ] && continue
  case "$name" in \#*) continue;; esac
  echo ">>> $name  start=$start dur=$dur"
  ffmpeg -y -v error -nostats \
    -ss "$start" -t "$dur" -i "$SRC" \
    -i "$MASK" \
    -filter_complex "$FC" -map "[v]" -map 0:a \
    -af "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000" \
    -c:v libx264 -preset medium -crf 19 -pix_fmt yuv420p -profile:v high -level 4.2 \
    -c:a aac -b:a 192k -ar 48000 -ac 2 \
    -movflags +faststart \
    "$OUT/$name.mp4"
done < clips.tsv
echo "ALL DONE -> $OUT"
