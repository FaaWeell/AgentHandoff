#!/usr/bin/env bash
# End-to-end demo of the AgentHandoff loop (safe: works in a temp folder).
#
#   bash examples/demo.sh            # run it
#   asciinema rec demo.cast -c "bash examples/demo.sh"   # record a GIF/video
#
set -euo pipefail

HANDOFF="${HANDOFF:-handoff}"
if ! command -v "$HANDOFF" >/dev/null 2>&1; then
  echo "handoff not found on PATH. Install it first:" >&2
  echo "  pip install agenthandoff" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT
cd "$WORKDIR"

banner() { printf '\n\033[1m== %s ==\033[0m\n' "$1"; }

banner "1. A project with some work in progress"
git init -q .
git config user.email demo@example.com
git config user.name "Demo"
mkdir -p src
printf 'flask\n' > requirements.txt
printf 'def login():\n    # TODO: hash the password\n    return True\n' > src/auth.py
git add -A && git commit -qm "feat: project scaffold"
echo "src/auth.py  requirements.txt"

banner "2. Capture the session (git snapshot is automatic)"
"$HANDOFF" capture \
  --goal "Finish the login feature" \
  --from claude \
  --decision "Use JWT :: stateless, fits our API" \
  --todo "Add refresh token" \
  --todo "Write tests for /login" \
  --done "Login endpoint finished" \
  --notes "Deploy target is Railway"

banner "3. Export to the next agent — one command"
"$HANDOFF" export --to codex

banner "4. What the new agent reads (AGENTS.md)"
sed -n '1,40p' AGENTS.md

banner "5. It is idempotent — run it again, still exactly one block"
"$HANDOFF" export --to all --quiet
grep -c "agent-handoff:begin" AGENTS.md

banner "6. Import an old chat log"
"$HANDOFF" import-log "$SCRIPT_DIR/sample-log.txt"

banner "7. Five-line status"
"$HANDOFF" status

banner "Done. Switch agents without re-briefing. github.com/FaaWeell/AgentHandoff"
