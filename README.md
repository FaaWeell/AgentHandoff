# AgentHandoff

**Never lose context when switching AI coding agents.**

[![CI](https://github.com/FaaWeell/AgentHandoff/actions/workflows/ci.yml/badge.svg)](https://github.com/FaaWeell/AgentHandoff/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/agenthandoff.svg)](https://pypi.org/project/agenthandoff/)
[![Python](https://img.shields.io/pypi/pyversions/agenthandoff.svg)](https://pypi.org/project/agenthandoff/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Claude Code hits your usage limit mid-task, so you switch to Codex. The new
agent knows nothing about the project: not the goal, not what you already
finished, not why you chose that approach yesterday. You spend the next 10 to 30
minutes explaining everything again.

AgentHandoff writes that context down in one local file and copies it into the
file your next agent reads at startup. Two commands, about ten seconds, no
account and no network.

```console
$ handoff capture --goal "Add login" --from claude --todo "Add refresh token"
Handoff updated in /home/you/app
  .agent-handoff/session.json  -> 0 done, 1 decision, 1 todo
  .agent-handoff/HANDOFF.md    -> regenerated
  git: feat/login, 1 changed file
  Next: handoff export --to codex   (or --to all)

$ handoff export --to codex
Export finished (1 target)
  AGENTS.md                                     created
```

Open Codex in the same folder. It reads `AGENTS.md`, so it already knows the
goal, the decisions behind the code, and what to do next.

## Quick start

```bash
pip install agenthandoff

handoff capture --goal "What this project should do" --from claude
handoff export --to codex
```

That is the whole loop:

1. `capture` records the session. The git snapshot is automatic.
2. `export` writes it to the file the next agent reads.
3. Switch agents and keep working.

You can capture as often as you like. A second capture merges into the existing
session, so nothing you wrote earlier is lost.

A typical session with more detail:

```bash
handoff capture \
  --goal "Finish the login feature" \
  --from claude \
  --decision "Use JWT :: stateless, fits our API" \
  --done "Login endpoint finished" \
  --todo "Add refresh token" \
  --todo "Write tests for /login" \
  --notes "Deploy target is Railway"
```

## Commands

| Command | What it does |
| --- | --- |
| `handoff capture` | Record or update the session: goal, agent, decisions, done, todos, notes, plus a git snapshot. |
| `handoff export --to <agent>` | Write the handoff into that agent's native file. `--to all` does every target. |
| `handoff show` | Print the current handoff. Add `--json` for the raw data. |
| `handoff status` | Five-line summary: goal, progress, remaining todos, last agent, last update. |
| `handoff import-log <file>` | Pull `Decision:`, `TODO:`, `Done:` lines out of an old chat log. |
| `handoff scan-todos` | Preview the `TODO` / `FIXME` comments that `capture --scan-todos` collects. |
| `handoff init` | Create `.agent-handoff/`, optionally add it to `.gitignore`, show next steps. |

Useful flags: `--path DIR` to work on another project, `--quiet` for scripts,
`--scan-todos` on capture to pick up code comments. Every command has `--help`.

`import-log` understands English and Indonesian labels:

```
Decision: Use JWT        Keputusan: Pakai JWT
TODO: Add refresh token  Selanjutnya: Tambahkan refresh token
Done: Login finished     Selesai: Login selesai
Note: meet on Monday     Catatan: rapat hari Senin
```

## Supported agents

| `--to` | File written | Read by |
| --- | --- | --- |
| `claude` | `CLAUDE.md` | Claude Code |
| `codex`, `agents` | `AGENTS.md` | Codex, OpenCode, any AGENTS.md agent |
| `gemini` | `GEMINI.md` | Gemini CLI |
| `cursor` | `.cursor/rules/agent-handoff.mdc` | Cursor |
| `copilot` | `.github/copilot-instructions.md` | GitHub Copilot |
| `windsurf` | `.windsurf/rules/agent-handoff.md` | Windsurf |
| `markdown` | `.agent-handoff/HANDOFF.md` | Anything, including humans |
| `all` | all of the above | — |

Short names work too (`--to agents`, `--to md`, `--to github-copilot`).
Adding a new agent is one entry in
[`src/agenthandoff/adapters.py`](src/agenthandoff/adapters.py).

## What gets written

`handoff show` prints `.agent-handoff/HANDOFF.md`, generated from
`session.json`:

```markdown
# AgentHandoff - my-app

| Field | Value |
| --- | --- |
| Project | `my-app` |
| Last agent | claude |
| Updated | 2026-10-25T12:30:00+07:00 |

## Goal

Finish the login feature

## Git state

- **Branch:** `feat/login`
- **Last commit:** `a1b2c3d feat: login endpoint`
- **Changed files:** 1
  - `src/auth.py`

## Done

- [x] Login endpoint finished

## Decisions (and why)

- **Use JWT** - stateless, fits our API

## Next steps

- [ ] Add refresh token
- [ ] Write tests for /login
```

Agent files (`CLAUDE.md`, `AGENTS.md`, and so on) get the same content inside a
marked block, so the file stays valid wherever it ends up:

```markdown
<!-- agent-handoff:begin -->
...generated context...
<!-- agent-handoff:end -->
```

## Will it damage my existing files?

No. This is the part with the most tests, because it is the part that can cost
you work:

- Re-exporting replaces that one block. It never appends a second copy.
- Everything you wrote outside the markers is kept byte for byte, including
  Windows line endings and blank lines.
- If a file has a `begin` marker without an `end` marker, the export stops with
  an error and leaves the file untouched instead of guessing.
- A file that is not valid UTF-8 is refused instead of being rewritten.
- Writes are atomic (temp file, then rename) and keep the original permissions.

## What this is not

| | AgentHandoff | Copy and paste by hand | Built-in agent memory |
| --- | --- | --- | --- |
| Time per switch | About 10 seconds | 5 to 30 minutes | — |
| Works across vendors | Yes | Yes, manually | No, locked to one vendor |
| Records decisions and reasons | Yes | No | No |
| Data leaves your machine | Never | Never | Varies |
| Versioned with git | Yes | No | No |

It is not an AI agent, not a cloud service, not a replacement for git, and not a
project manager. There is no telemetry and no network call in the core.

## Install

```bash
pip install agenthandoff   # Python 3.11+
```

With zero runtime dependencies, so it installs anywhere Python runs: Windows,
macOS, Linux, and it works offline.

From source:

```bash
git clone https://github.com/FaaWeell/AgentHandoff
cd AgentHandoff
pip install -e ".[dev]"
pytest
```

To check your own setup end to end, follow
[docs/TESTING.md](docs/TESTING.md).

## Design principles

1. Local first. Your context never leaves your machine.
2. Agent agnostic. No vendor gets special treatment.
3. No setup. The first command works.
4. Plain text. Readable by people, diffable in git.
5. Never destructive. Content outside the block is yours.
6. Simple over complete. Fewer features, fewer surprises.

## Roadmap

- **v0.1 (current)** Capture, export to seven targets, show, status, import-log,
  TODO scan, merge on repeated capture.
- **v0.2** `init` polish, a `status` that shows per-agent sync state.
- **v0.3** Read Claude Code session history (`~/.claude/projects/**.jsonl`).
- **v0.4** Codex and Gemini history, optional `--summarize` with your own key.
- **v0.5** Handoff history and `handoff log`, project stack detection.
- **v1.0** Open format spec, community adapter plugins, `watch` and `diff`.

Details in [docs/ROADMAP.md](docs/ROADMAP.md). Data format in
[docs/FORMAT.md](docs/FORMAT.md).

## Contributing

Contributions are welcome, especially new agent adapters. Adding an agent means
one entry in `TARGETS` plus one test row, which makes it a good first PR.

```bash
pip install -e ".[dev]"
pytest -q                      # no network needed
pytest --cov=agenthandoff      # coverage, CI gate is 80%
ruff check src tests examples  # lint
```

Read [CONTRIBUTING.md](CONTRIBUTING.md) and look for
[`good first issue`](https://github.com/FaaWeell/AgentHandoff/labels/good%20first%20issue).

This repository uses AgentHandoff on itself: it ships a real
[`.agent-handoff/session.json`](.agent-handoff/session.json) and the exported
`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, Cursor, Copilot and Windsurf files.

## License

[MIT](LICENSE), 2026 FaaWeell and AgentHandoff contributors.

If this saves you a re-briefing, a star helps other developers find it.
