#!/bin/bash
# Link the skills into ~/.claude/skills so they run as /highlight-reel, /hr-setup, … and edits in this
# clone are live. (Alternative: install as a plugin — see README.)
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"; DEST="$HOME/.claude/skills"; mkdir -p "$DEST"
for d in "$HERE"/skills/*/; do
  n=$(basename "$d")
  if [ -e "$DEST/$n" ] && [ ! -L "$DEST/$n" ]; then echo "skip $n: $DEST/$n exists and is not a link"; continue; fi
  ln -sfn "$d" "$DEST/$n" && echo "linked $n"
done
