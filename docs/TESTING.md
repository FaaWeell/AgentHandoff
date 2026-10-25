# Testing AgentHandoff end to end

This is a manual checklist you can run on your own machine in about five
minutes. It installs the package from source, exercises every command, and
proves the two things that matter most: exports are idempotent, and content you
wrote is never touched.

Everything below runs in a throwaway folder, so your real projects are safe.

## 0. Prerequisites

```bash
python3 --version    # must be 3.11 or newer
git --version        # optional, only needed for git snapshots
```

## 1. Install from the repository

```bash
git clone https://github.com/FaaWeell/AgentHandoff
cd AgentHandoff

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -e ".[dev]"
```

Check that the entry point works:

```bash
handoff --version      # AgentHandoff 0.1.0
handoff --help         # lists capture, export, show, status, import-log,
                       # scan-todos, init
```

## 2. Run the automated tests

```bash
pytest -q                             # expect: all tests pass, no failures
pytest --cov=agenthandoff             # expect: total coverage around 94%
ruff check src tests examples         # expect: All checks passed!
```

If these are green, the library itself is fine. The next steps check the
behaviour you actually feel as a user.

## 3. Create a scratch project

```bash
mkdir -p /tmp/handoff-test && cd /tmp/handoff-test
git init -q .
git config user.email you@example.com
git config user.name "You"

mkdir src
printf 'def login():\n    return True\n' > src/auth.py
printf 'flask\n' > requirements.txt
git add -A && git commit -qm "feat: project scaffold"

# Work in progress: leave one changed file and a TODO comment behind.
printf 'def login():\n    # TODO: hash the password\n    return True\n' > src/auth.py
```

## 4. Capture a session

```bash
handoff capture \
  --goal "Finish the login feature" \
  --from claude \
  --decision "Use JWT :: stateless, fits our API" \
  --todo "Add refresh token" \
  --done "Login endpoint finished" \
  --notes "Deploy target is Railway"
```

Expected output (wording may differ slightly):

```
Handoff updated in /tmp/handoff-test
  .agent-handoff/session.json  -> 1 done, 1 decision, 1 todo
  .agent-handoff/HANDOFF.md    -> regenerated
  git: master · 1 changed file(s)
  Next: handoff export --to codex   (or --to all)
```

Check the files:

```bash
cat .agent-handoff/HANDOFF.md     # goal, git state, done, decisions, next steps
cat .agent-handoff/session.json   # same data as JSON, this is the source of truth
```

## 5. Export to every agent

```bash
handoff export --to all
```

Expected: seven files reported as `created`:

```bash
ls AGENTS.md CLAUDE.md GEMINI.md
ls .cursor/rules/agent-handoff.mdc
ls .github/copilot-instructions.md
ls .windsurf/rules/agent-handoff.md
ls .agent-handoff/HANDOFF.md
```

Look inside `AGENTS.md`:

```bash
cat AGENTS.md
```

You should see a block starting with `<!-- agent-handoff:begin -->`, the goal,
the git branch, the done item, the decision with its reason, and the todo item,
then `<!-- agent-handoff:end -->`.

## 6. Prove the export is idempotent

```bash
handoff export --to all --quiet
grep -c "agent-handoff:begin" AGENTS.md      # expect: 1

# byte-for-byte check: two runs must produce identical files
md5sum AGENTS.md > /tmp/before.txt
handoff export --to all --quiet
md5sum AGENTS.md > /tmp/after.txt
diff /tmp/before.txt /tmp/after.txt && echo "idempotent: OK"
```

On macOS use `md5` instead of `md5sum`, or just run `git diff --stat` and expect
no changes.

## 7. Prove that your own text is never touched

This is the check that matters most.

```bash
printf '\n\n## My own rules\nAlways run the tests before committing.\n' >> AGENTS.md

handoff export --to all --quiet
handoff export --to all --quiet

grep -c "Always run the tests before committing" AGENTS.md   # expect: 1
grep -c "agent-handoff:begin" AGENTS.md                      # expect: 1
tail -4 AGENTS.md                                            # your lines, unchanged
```

Also check a file that already has content **before** the block:

```bash
printf '# Team conventions\n\nUse tabs.\n' > CLAUDE.md
handoff export --to claude --quiet
cat CLAUDE.md                    # your two lines are still in the file
grep -c "agent-handoff:begin" CLAUDE.md   # expect: 1
```

`CLAUDE.md` gets the block at the top and `copilot` / `windsurf` get it at the
bottom, because that is how each vendor reads its file. Either way, your text is
only ever added to, never replaced.

And the failure path (a half-written marker must abort, not destroy):

```bash
printf '<!-- agent-handoff:begin -->\nno end marker\n' > GEMINI.md
handoff export --to gemini          # expect: error about a missing end marker
cat GEMINI.md                       # file unchanged
rm GEMINI.md                        # clean up the deliberately broken file
handoff export --to all --quiet     # everything is in sync again
```

## 8. Merge instead of overwrite

```bash
handoff capture --done "add refresh token" --path .
handoff status
```

Expected: the matching todo is gone from `next steps`, the done list has the
item, and the goal is still "Finish the login feature".

## 9. Import an old chat log

```bash
cat > /tmp/chat-log.txt <<'EOF'
Decision: Use bcrypt :: industry standard for hashing
TODO: Add rate limiting
Done: Setup project structure
Keputusan: Refresh token pakai rotating strategy
Selanjutnya: Tulis dokumentasi
EOF

handoff import-log /tmp/chat-log.txt
handoff show
```

Expected: `+2 decisions, +2 todos, +1 done` in the summary, and the new items appear
in `handoff show`. Note that both English and Indonesian labels were picked up.

## 10. Scan TODO comments from the code

```bash
handoff scan-todos                    # lists src/auth.py:2 - TODO: hash the password
handoff capture --scan-todos --quiet
handoff status                        # the TODO now appears in next steps
```

## 11. The full switch scenario

```bash
handoff capture --goal "Finish the login feature" --from claude --quiet
handoff export --to codex --quiet

# Now pretend you are the next agent: the only input is AGENTS.md.
grep -E "Goal|Finish the login|Done|Next steps|Add rate limiting" AGENTS.md
```

If those lines are present, an agent that reads `AGENTS.md` knows the goal, what
is finished, and what to do next, without any prompt from you.

## 12. Friendly errors, no tracebacks

Each of these should print a short explanation, not a Python traceback:

```bash
handoff show --path /tmp/empty-folder       # no handoff yet
handoff export --to zed                     # unknown target, lists valid ones
handoff import-log /tmp/nope.txt            # file not found

printf '{ broken json' > .agent-handoff/session.json
handoff capture --goal "x"                  # explains that the JSON is invalid

rm .agent-handoff/session.json              # start the session over
handoff capture --goal "Finish the login feature" --from claude
```

## 13. Optional: non-git folder

```bash
mkdir /tmp/no-git && cd /tmp/no-git
handoff capture --goal "Still works here"
handoff export --to claude --quiet
cat .agent-handoff/HANDOFF.md      # git section says it is not a git repository
```

## 14. Clean up

```bash
deactivate
rm -rf /tmp/handoff-test /tmp/no-git /tmp/chat-log.txt
```

## Expected results summary

| Step | Expectation |
| --- | --- |
| 2 | All tests pass, coverage about 94 percent, lint clean |
| 4 | `session.json` and `HANDOFF.md` created |
| 5 | Seven target files created |
| 6 | Exactly one block per file, byte-identical between runs |
| 7 | Your text survives, broken markers abort safely |
| 8 | Done item removes the matching todo, goal kept |
| 9 | English and Indonesian log labels imported |
| 10 | TODO comments become next steps |
| 11 | Agent file answers: goal, done, next steps |
| 12 | Human-readable errors, no tracebacks |

If a step fails, open an issue with the command you ran, the output, and your OS
and Python version. Reports where a file lost content are treated as P0.
