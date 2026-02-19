#!/bin/bash
# Accept all new visual regression screenshots as the new baselines.
# This replaces each baseline with the corresponding new_* screenshot.

PRIMARY_SCREENSHOTS_DIR="tests/core/e2e/screenshots"
LEGACY_SCREENSHOTS_DIR="tests/e2e/screenshots"

cd "$(dirname "$0")/.." || exit 1

if [ -d "$PRIMARY_SCREENSHOTS_DIR" ]; then
    SCREENSHOTS_DIR="$PRIMARY_SCREENSHOTS_DIR"
elif [ -d "$LEGACY_SCREENSHOTS_DIR" ]; then
    SCREENSHOTS_DIR="$LEGACY_SCREENSHOTS_DIR"
else
    echo "No screenshots directory found."
    exit 1
fi

count=0
for new_file in "$SCREENSHOTS_DIR"/new_*.png; do
    if [ -f "$new_file" ]; then
        baseline=$(echo "$new_file" | sed 's|/new_|/|')
        mv "$new_file" "$baseline"
        echo "Accepted: $(basename "$baseline")"
        ((count++))
    fi
done

if [ $count -eq 0 ]; then
    echo "No new screenshots to accept."
else
    echo ""
    echo "Accepted $count screenshot(s)."
fi
