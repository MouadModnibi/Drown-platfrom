#!/bin/bash
# Usage: this script is invoked via authorized_keys' command= directive,
# with the drown user_id passed as $1.
# It receives the real git command via $SSH_ORIGINAL_COMMAND.

USER_ID="$1"

if [ -z "$SSH_ORIGINAL_COMMAND" ]; then
    echo "Only git operations are allowed."
    exit 1
fi

# Extract the repo path from something like: git-receive-pack '/home/ubuntu/git-hook-test/env-test.git'
REPO_PATH=$(echo "$SSH_ORIGINAL_COMMAND" | sed -n "s/.*'\(.*\)'.*/\1/p")

if [ -z "$REPO_PATH" ]; then
    echo "Could not parse repository path."
    exit 1
fi

APP_NAME=$(basename "$REPO_PATH" .git)

# Check ownership via Python (reuses your existing database.py)
OWNER_ID=$(python3 -c "
import sys
sys.path.insert(0, '/home/ubuntu/mini-heroku/control-plane')
from core.database import get_app_owner
owner = get_app_owner('$APP_NAME')
print(owner if owner is not None else '')
")

if [ "$OWNER_ID" != "$USER_ID" ]; then
    echo "Permission denied: you do not own '$APP_NAME'."
    exit 1
fi

# Ownership confirmed — execute the real git command
eval "$SSH_ORIGINAL_COMMAND"
