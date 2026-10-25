# Roadmap

Principles: ship the smallest thing that solves the problem well, release
early, grow through the community rather than through feature count.

Legend: ✅ shipped · 🚧 in progress · ⏳ planned · 🔭 exploratory

## v0.1 — MVP ✅ (2026-10-25)

| # | Feature | Status |
| --- | --- | --- |
| F1 | `handoff capture` (goal, source agent, decisions, done, todo, notes, automatic git snapshot) | ✅ |
| F2 | `handoff export --to <agent>` → claude, codex/agents, gemini, cursor, copilot, windsurf, markdown, `all` | ✅ |
| F3 | `handoff show` | ✅ |
| F4 | Structured local storage: `session.json` (source of truth) + `HANDOFF.md` (human-readable) | ✅ |
| F5 | Marker-delimited, idempotent, non-destructive export | ✅ |
| F6 | `handoff import-log` (`Decision:`/`TODO:`/`Done:` + `Keputusan:`/`Selanjutnya:`/`Selesai:`) | ✅ |
| F7 | `--scan-todos` (TODO/FIXME from source, capped, ignores vendored dirs) | ✅ |
| F8 | Session merge (a `--done` item leaves the todo list) | ✅ |

Also shipped in 0.1 beyond the original PRD list: `handoff status`,
`handoff init`, `handoff scan-todos`, `--path`/`--quiet` everywhere, `docs/FORMAT.md`.

## v0.2 — Polish after launch ⏳

- Interactive-ish `init` wizard (remember preferred agents in
  `.agent-handoff/config.json`).
- `handoff status` shows which agent files are currently in sync.
- Better Windows console output (no glyph issues on legacy code pages).
- Fixes from the first weeks of real usage.

## v0.3 — Read native Claude Code history ⏳

- Parser for `~/.claude/projects/**.jsonl` → propose goal/decisions/touched files
  automatically, then let the user confirm before writing.
- `handoff capture --from-history claude` with an interactive review step.

## v0.4 — More histories, optional summarisation ⏳

- Parsers for Codex and Gemini CLI session histories.
- `--summarize` (strictly opt-in, bring your own API key or a local Ollama
  endpoint). The core stays offline and dependency-free.

## v0.5 — History and context enrichment ⏳

- `.agent-handoff/history/` archive + `handoff log` to browse previous handoffs.
- Stack detection (package.json, pyproject.toml, go.mod, Cargo.toml …) to add a
  short "stack" section automatically.

## v1.0 — Open format and ecosystem 🔭

- `HANDOFF-SPEC.md`: a standalone, tool-agnostic specification (starts from
  [`FORMAT.md`](FORMAT.md)).
- Community adapter plugins: `handoff export --to <name>` resolved from an
  installed package/adapter file.
- `handoff watch` (periodic auto-capture) and `handoff diff` (what changed since
  the last handoff).
- VS Code extension (experimental) for people who prefer buttons.

## Non-goals

Never in core: being an AI agent, calling an LLM by default, cloud sync,
telemetry, project management, replacing git.

## How priorities are decided

1. Data-loss or corruption reports — always first.
2. Adapter breakage caused by a vendor changing its format — patched within days.
3. Requests with multiple independent 👍/comments from real users.
4. Everything else, in release order above.

Open an issue with the `feature request` template; roadmap changes are recorded
in [CHANGELOG.md](../CHANGELOG.md).
