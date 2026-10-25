# AgentHandoff

**Never lose context when switching AI coding agents.**

[![CI](https://github.com/FaaWeell/AgentHandoff/actions/workflows/ci.yml/badge.svg)](https://github.com/FaaWeell/AgentHandoff/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/agenthandoff.svg)](https://pypi.org/project/agenthandoff/)
[![Python versions](https://img.shields.io/pypi/pyversions/agenthandoff.svg)](https://pypi.org/project/agenthandoff/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/FaaWeell/AgentHandoff.svg?style=social)](https://github.com/FaaWeell/AgentHandoff/stargazers)

> 🇮🇩 Baca versi Bahasa Indonesia: [README.id.md](README.id.md)

**Switching from Claude Code to Codex mid-task? Your new agent knows nothing.**
AgentHandoff captures your session (goal, decisions, what's done, next steps, git
state) and writes it into the file your next agent reads at startup — in two
commands, in about ten seconds, entirely offline.

```console
$ handoff capture --goal "Add login" --from claude --todo "Add refresh token"
✔ Handoff diperbarui di /home/you/app
  .agent-handoff/session.json  → 1 done · 1 decisions · 2 todo
  .agent-handoff/HANDOFF.md    → regenerated
  git: feat/login · 1 changed file(s)

$ handoff export --to codex
✔ Export selesai (1 target)
  AGENTS.md                                     created

# open Codex in the same project — it already knows the goal,
# the decisions you made and what to build next.
```

> 📹 A ≤15 second GIF demo lives in [docs/LAUNCH.md](docs/LAUNCH.md#demo-assets) —
> run [`examples/demo.sh`](examples/demo.sh) to record it yourself.

---

## Why this exists

Developers in 2026 don't use one AI coding agent. Limits run out, one agent is
better at planning, another at refactoring, and a third is free this week.
Every switch costs 5–30 minutes of re-briefing, and whatever you explained to
the previous agent is gone — including *why* you made the choices you made.

AgentHandoff turns that lost context into one local, git-friendly file
(`.agent-handoff/session.json`) and renders it into every agent's native format,
so the handoff takes seconds instead of a meeting.

## Quick start

```bash
pip install agenthandoff

handoff capture --goal "Add login" --from claude --todo "Add refresh token"
handoff export --to codex
```

That's the whole loop:

1. **capture** — record the session (git snapshot is automatic).
2. **export** — write it where the next agent looks.
3. **switch** — open the other agent in the same folder and keep working.

### Then what?

| Command | What it does |
| --- | --- |
| `handoff capture` | Capture or update the session. Repeated captures **merge** — nothing recorded earlier is lost. |
| `handoff export --to <agent>` | Write the handoff block into that agent's native file. `--to all` does every target. |
| `handoff show` | Print the current handoff (`.agent-handoff/HANDOFF.md`), or `--json` for the raw data. |
| `handoff status` | Five-line summary: goal, progress, remaining todos, last agent, last update. |
| `handoff import-log <file>` | Extract `Decision:` / `TODO:` / `Done:` lines (`Keputusan:` / `Selanjutnya:` / `Selesai:`) from an old chat log. |
| `handoff scan-todos` | Preview the `TODO`/`FIXME` comments `capture --scan-todos` would collect. |
| `handoff init` | Create `.agent-handoff/`, optionally gitignore it, and show next steps. |

Every command accepts `--path DIR` to operate on another project root and
`--quiet` for script-friendly output. Every command has `--help`.

## Supported agents

| Target (`--to`) | File written | Read by |
| --- | --- | --- |
| `claude` | `CLAUDE.md` | Claude Code |
| `codex`, `agents` | `AGENTS.md` | Codex, OpenCode and every AGENTS.md-compatible agent |
| `gemini` | `GEMINI.md` | Gemini CLI |
| `cursor` | `.cursor/rules/agent-handoff.mdc` | Cursor (rule frontmatter included) |
| `copilot` | `.github/copilot-instructions.md` | GitHub Copilot |
| `windsurf` | `.windsurf/rules/agent-handoff.md` | Windsurf |
| `markdown` | `.agent-handoff/HANDOFF.md` | Anything / humans |
| `all` | all of the above | — |

Aliases work too: `--to agents`, `--to md`, `--to github-copilot`, …
Adding a new agent is literally one line in
[`src/agenthandoff/adapters.py`](src/agenthandoff/adapters.py).

## What gets written

`handoff show` renders `.agent-handoff/HANDOFF.md` (also exported into every
target file, inside a delimited block):

```markdown
# 🤝 AgentHandoff — my-app

| Field | Value |
| --- | --- |
| Project | `my-app` |
| Last agent | claude |
| Updated | 2026-10-25T12:30:00+07:00 |

## 🎯 Goal
Add login

## 🌿 Git state
- **Branch:** `feat/login`
- **Last commit:** `a1b2c3d feat: login endpoint`
- **Changed files:** 1
  - `src/auth.py`

## ✅ Done
- [x] Endpoint /login selesai

## 🧭 Decisions (and why)
- **Pakai JWT** — stateless, cocok untuk API

## ⏭️ Next steps
- [ ] Add refresh token
- [ ] Write tests for /login
```

### Safe by design

Every exported file gets exactly one block:

```markdown
<!-- agent-handoff:begin -->
…generated context…
<!-- agent-handoff:end -->
```

- Re-exporting **replaces** that block — idempotent, never duplicated.
- Everything you wrote **outside** the markers is preserved byte-for-byte
  (including CRLF files and non-ASCII paths).
- A half-written marker pair stops the export instead of guessing — zero
  incidents of "the tool ate my rules file" is a release blocker for us.
- Writes are atomic (`write temp → fsync → replace`) and keep file permissions.

## What it is not

| | AgentHandoff | Plain copy-paste | Built-in agent memory |
| --- | --- | --- | --- |
| Time per switch | ~10 seconds | 5–30 minutes | n/a |
| Works across vendors | ✅ any agent | ✅ manual | ❌ locked to one vendor |
| Records decisions *and why* | ✅ | ❌ | ❌ |
| Format | one JSON source → native files | inconsistent | vendor-specific |
| Privacy | 100% local, no network, no telemetry | local | varies |
| Versioned with git | ✅ | ❌ | ❌ |

AgentHandoff is **not** an AI agent, not a cloud service, not a git replacement
and not a project manager. It is a small, boring, reliable handoff tool.

## Install

```bash
pip install agenthandoff      # requires Python 3.11+
```

From source:

```bash
git clone https://github.com/FaaWeell/AgentHandoff
cd AgentHandoff
pip install -e ".[dev]"
pytest
```

**Zero runtime dependencies** — standard library only, so it installs anywhere
Python runs (Windows, macOS, Linux) and works fully offline.

## Design principles

1. **Local-first** — your context never leaves your machine.
2. **Agent-agnostic** — no vendor gets special treatment.
3. **Zero-config** — the first command works without setup.
4. **Plain text, git-friendly** — readable by humans, diffable by review tools.
5. **Never destructive** — user content outside the handoff block is sacred.
6. **Simple over complete** — few features, very reliable.

## Roadmap

- ✅ **v0.1 (now)** — capture, export to 7 targets, show, import-log, TODO scan, merge semantics.
- ⏳ **v0.2** — `init` wizard polish, richer `status`, launch bug fixes.
- ⏳ **v0.3** — parse native Claude Code session history (`~/.claude/projects/**.jsonl`).
- ⏳ **v0.4** — Codex/Gemini history parsers, optional `--summarize` (bring your own key / Ollama).
- ⏳ **v0.5** — handoff history (`history/`) + `handoff log`, stack detection.
- 🔭 **v1.0** — open `HANDOFF-SPEC.md`, community adapter plugins, `handoff watch` / `diff`.

Details in [docs/ROADMAP.md](docs/ROADMAP.md); format spec in
[docs/FORMAT.md](docs/FORMAT.md).

## Contributing

Contributions are welcome — especially new agent adapters.

- **Add an agent = one line.** Add an entry to `TARGETS` in
  [`src/agenthandoff/adapters.py`](src/agenthandoff/adapters.py) plus a test.
  That's a perfect first PR.
- Found a bug that touched your files? Open an issue immediately, that's a P0.
- Read [CONTRIBUTING.md](CONTRIBUTING.md) and grab a
  [`good first issue`](https://github.com/FaaWeell/AgentHandoff/labels/good%20first%20issue).

```bash
pip install -e ".[dev]"
pytest -q                      # 200+ tests, no network needed
pytest --cov=agenthandoff      # coverage (CI gate: 80%)
```

This repository practices what it preaches: it carries its own real
[`.agent-handoff/`](.agent-handoff/session.json) session and exported
`CLAUDE.md` / `AGENTS.md` / `GEMINI.md` files.

## License

[MIT](LICENSE) © 2026 FaaWeell and AgentHandoff contributors.

---

**If this saves you one re-briefing, a ⭐ helps other developers find it.**
