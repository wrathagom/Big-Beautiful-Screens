#!/bin/bash
# Copy e2e test screenshots to docs for mkdocs build.
# Screenshots are stored in tests/e2e/screenshots/ but mkdocs needs them in docs/.

set -e

cd "$(dirname "$0")/.." || exit 1

SRC_DIR="tests/e2e/screenshots"
DEST_DIR="docs/images/screenshots"

# Create destination directory
mkdir -p "$DEST_DIR"

# Copy all png files (excluding new_* which are uncommitted test artifacts)
count=0
for file in "$SRC_DIR"/*.png; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        # Skip new_* files (visual regression test artifacts)
        if [[ ! "$filename" == new_* ]]; then
            cp "$file" "$DEST_DIR/"
            count=$((count + 1))
        fi
    fi
done

echo "Copied $count screenshot(s) to $DEST_DIR"
