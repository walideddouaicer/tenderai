#!/bin/bash
COMMAND=$(echo "$CLAUDE_TOOL_INPUT" | jq -r '.command // empty')

if echo "$COMMAND" | grep -q 'git commit'; then
  STAGED=$(git diff --cached --name-only 2>/dev/null)
  for file in $STAGED; do
    if [ -f "$file" ]; then
      if grep -qE '(AKIA[0-9A-Z]{16}|sk-[a-zA-Z0-9]{48}|ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82}|sk_live_|-----BEGIN (RSA |EC )?PRIVATE KEY-----)' "$file"; then
        echo "BLOCKED: Possible secret detected in $file" >&2
        echo "Move it to .env and reference via os.environ / process.env" >&2
        exit 2
      fi
    fi
  done
fi

exit 0
