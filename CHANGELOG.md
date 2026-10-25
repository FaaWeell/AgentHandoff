# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- All user-facing CLI output and error messages are now in English, so the tool
  reads the same way for every user. Log import still accepts both English and
  Indonesian labels.
- `README.md` rewritten: English only, plainer wording, fewer emoji.
  `README.id.md` removed.
- Added `docs/TESTING.md`, a step-by-step manual verification guide.
- Example content in `docs/`, `examples/` and the repository's own session file
  translated to English.

### Planned for v0.2
- `handoff init` wizard polish (interactive agent selection).
- Richer `handoff status` with per-agent export state.
- Fixes from launch feedback.

## [0.1.0] — 2026-10-25

First public release: capture a session once, export it to every agent's native
context file.

### Added
- **`handoff capture`** — snapshot the session: goal, source agent, decisions
  (with reasons), todos, done, notes, plus an automatic git snapshot (branch,
  last commit, changed files, 10 recent commits, diff stat). Works outside git.
- **`handoff export --to <agent|all>`** — write the handoff into seven targets:
  `claude` (`CLAUDE.md`), `codex`/`agents` (`AGENTS.md`), `gemini`
  (`GEMINI.md`), `cursor` (`.cursor/rules/agent-handoff.mdc`), `copilot`
  (`.github/copilot-instructions.md`), `windsurf`
  (`.windsurf/rules/agent-handoff.md`), and `markdown`
  (`.agent-handoff/HANDOFF.md`). Aliases and comma-separated targets supported.
- **`handoff show`** — print the current handoff, or `--json` for the raw schema.
- **`handoff status`** — five-line summary (goal, progress, remaining todos,
  last agent, last update).
- **`handoff import-log <file>`** — extract `Decision:` / `TODO:` / `Done:` /
  `Note:` lines, with Bahasa Indonesia labels (`Keputusan:`, `Selanjutnya:` /
  `Berikutnya:` / `Rencana:`, `Selesai:` / `Sudah:`, `Catatan:`).
- **`handoff scan-todos`** and **`capture --scan-todos`** — collect `TODO` /
  `FIXME` / `HACK` / `XXX` comments from source code (max 50, skips
  `node_modules`, `.git`, `.venv`, `dist`, `build`, …).
- **`handoff init`** — create `.agent-handoff/`, optionally add it to
  `.gitignore`, detect agents already in use, print next steps.
- **Merge semantics** — repeated captures merge instead of overwriting; a
  `--done` item removes the matching todo; no duplicate todos/done; notes are
  appended.
- **Safe, idempotent exports** — marker-delimited blocks
  (`<!-- agent-handoff:begin/end -->`) replaced in place; user content outside
  the markers preserved byte-for-byte; CRLF preserved; atomic writes; malformed
  markers abort with an actionable error instead of guessing.
- **Zero-dependency core** — Python 3.11+ standard library only, fully offline.
- **Developer ergonomics** — friendly, actionable error messages (missing
  session, corrupt JSON, unknown target, missing log file), `--path` on every
  command, `--quiet`, `--version`, complete `--help` for every subcommand.
- Docs: `README.md`, `CONTRIBUTING.md`, `docs/FORMAT.md`, `docs/TESTING.md`
  (session.json schema v1), `docs/ROADMAP.md`, `docs/LAUNCH.md`, examples.
- CI: GitHub Actions matrix — Ubuntu/macOS/Windows × Python 3.11/3.12/3.13,
  coverage gate at 80% (currently ~94%).

[Unreleased]: https://github.com/FaaWeell/AgentHandoff/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/FaaWeell/AgentHandoff/releases/tag/v0.1.0
