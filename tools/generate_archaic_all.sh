#!/usr/bin/env bash
# Generate narration for all archaic English translations, sequentially.
# Run from the Hexapla repo root.
set -e

cd "$(dirname "$0")/.."

for lang in wbt gnv tyn wyc; do
    echo "========================================"
    echo "Starting $lang at $(date)"
    echo "========================================"
    python -u tools/narrate.py --lang "$lang" 2>&1
    echo "$lang finished at $(date)"
    echo ""
done

echo "All archaic translations done at $(date)"
