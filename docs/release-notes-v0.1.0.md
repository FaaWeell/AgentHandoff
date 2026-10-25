# AgentHandoff v0.1.0 — move context between AI coding agents in 10 seconds

**Every time you switch AI coding agents, your new agent starts from zero.**
Quota ran out on Claude Code mid-task? Moved to Codex to finish the refactor?
You spend 5–30 minutes re-explaining the goal, what is done and *why* you chose
that approach — then you do it again tomorrow, in the other direction.

AgentHandoff makes that a two-command, ten-second job.

```bash
pip install agenthandoff

handoff capture --goal "Add login" --from claude \
  --decision "Use JWT :: stateless, fits our API" \
  --todo "Add refresh token" \
  --done "Login endpoint finished"

handoff export --to codex      # writes AGENTS.md — or --to all
```

Open Codex in the same project. It already knows the goal, the decisions and the
reasoning, and what to build next.

## What's in 0.1.0

- **Capture once, in seconds.** Goal, source agent, decisions (with reasons),
  done, todos, notes — plus an automatic git snapshot (branch, last commit,
  changed files, 10 recent commits, diff stat). Gracefully does nothing outside
  a git repo.
- **Seven export targets, one source of truth.**
  `CLAUDE.md` · `AGENTS.md` · `GEMINI.md` ·
  `.cursor/rules/agent-handoff.mdc` · `.github/copilot-instructions.md` ·
  `.windsurf/rules/agent-handoff.md` · `.agent-handoff/HANDOFF.md`
- **Never destructive.** The generated block is marker-delimited and replaced
  in place: re-exporting never duplicates it and never touches what you wrote
  outside the markers. CRLF preserved, atomic writes, malformed markers abort
  loudly instead of guessing. (This is a release gate with dedicated tests.)
- **Merge, not overwrite.** Capture as often as you like; a `--done` item leaves
  the todo list automatically and nothing recorded earlier disappears.
- **Bring your old notes.** `handoff import-log notes.txt` understands
  `Decision:` / `TODO:` / `Done:` and the Indonesian
  `Keputusan:` / `Selanjutnya:` / `Selesai:`.
- **`handoff status`** for a five-line catch-up, **`handoff scan-todos`** to pull
  `TODO`/`FIXME` comments out of your source, **`handoff init`** to set up a repo.
- **Zero dependencies, 100% local, offline, no telemetry**, Python 3.11+ on
  Windows, macOS and Linux. MIT.

## Quality

- 200+ tests, ~94% coverage on the core (`capture`, `merge`, `export`).
- CI matrix: Ubuntu/macOS/Windows × Python 3.11/3.12/3.13.
- Nine explicit tests assert that user content outside the block survives
  repeated exports.

## Roadmap next

v0.2 polish → native Claude Code session parsing (v0.3) → Codex/Gemini parsers
and optional BYO-key summarisation (v0.4) → handoff history (v0.5) → open format
spec, plugins, `watch`/`diff` (v1.0). See [ROADMAP.md](ROADMAP.md).

**If this saves you one re-briefing, a ⭐ helps other developers find it.**
