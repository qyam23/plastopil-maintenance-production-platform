#!/data/data/com.termux/files/usr/bin/bash
set -e
cd "$(dirname "$0")"
mkdir -p data uploads/images uploads/videos uploads/audio
python app.py
