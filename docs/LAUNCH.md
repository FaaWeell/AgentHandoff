# Launch plan — v0.1.0

Purpose: launch on three or four channels, not one, and never on the same day.
Goal is not stars for their own sake — it is real users and contributors.

## 0. Pre-flight checklist

- [x] `pytest` green locally, 3 OS × Python 3.11/3.12/3.13 in CI
- [x] Coverage ≥ 80% on core (actual: ~94%)
- [x] 0 known "user content destroyed" bugs; export proven idempotent
- [x] README follows the required structure: tagline → problem → demo → quick
      start → supported agents → example output → differentiation → roadmap →
      contributing → license
- [x] `LICENSE`, `CONTRIBUTING.md`, `CHANGELOG.md`, `docs/FORMAT.md`,
      `docs/ROADMAP.md`
- [x] Dogfooding: this repo carries its own `.agent-handoff/` + exported files
- [ ] `pip install agenthandoff` works from PyPI (TestPyPI dry run first)
- [ ] GitHub Release `v0.1.0` + tag
- [ ] ≥ 5 `good first issue` issues open
- [ ] Demo GIF recorded (see below)
- [ ] Repo description + topics set

## 1. Release steps

```bash
# 1. final checks
pytest -q
python -m build            # requires `pip install build`
python -m twine check dist/*

# 2. publish (TestPyPI first, then PyPI)
python -m twine upload --repository testpypi dist/*
python -m twine upload dist/*

# 3. tag & release
git tag -a v0.1.0 -m "AgentHandoff v0.1.0"
git push origin v0.1.0
gh release create v0.1.0 --title "v0.1.0 — move context between agents in 10s" \
  --notes-file docs/release-notes-v0.1.0.md
```

Repo metadata:

- **Description:** `Never lose context when switching AI coding agents — capture a session, export it to CLAUDE.md / AGENTS.md / GEMINI.md and more.`
- **Topics:** `ai-coding-agent`, `claude-code`, `codex`, `gemini-cli`, `cursor`,
  `copilot`, `context`, `handoff`, `developer-tools`, `cli`, `python`,
  `open-source`, `productivity`

## 2. Demo assets

Record a ≤15 s terminal GIF showing the whole promise:

```bash
bash examples/demo.sh          # prints the full flow, ready to record
asciinema rec demo.cast        # or: vhs docs/demo.tape
```

Storyboard (exact beats):

1. `handoff capture --goal "Add login" --from claude --todo "Add refresh token"` → success.
2. `handoff export --to codex` → `AGENTS.md` written.
3. Show the top of `AGENTS.md`: goal, done, next steps.
4. Cursor rests on `## ⏭️ Next steps` — caption: *"the next agent already knows."*

## 3. Channel schedule

| Day | Channel | Material |
| --- | --- | --- |
| 12 | X/Twitter + Indonesian dev communities (Telegram/Discord) | "Building in public" thread: problem → GIF → link → ask for feedback |
| 13 | dev.to / Medium | Tutorial: *"How I Switch Between Claude Code and Codex Without Losing Context"* |
| 13 | Reddit r/ClaudeAI, r/ChatGPTCoding, r/commandline | Personal story, not an ad. Answer every comment. |
| 14 | Hacker News (Show HN) | `Show HN: AgentHandoff – move context between AI coding agents in 10 seconds` |
| 14 | Product Hunt | Schedule; banner + GIF ready |
| ongoing | Awesome lists | PR to awesome-claude-code, awesome-ai-coding, awesome-cli-apps, awesome-python-cli |

## 4. Copy (ready to paste)

### X/Twitter thread (EN)

1. I switch between Claude Code, Codex and Cursor every day. Every switch costs
   me 10+ minutes of re-explaining the project. So I built AgentHandoff. 🧵
2. `handoff capture --goal "Add login" --from claude --todo "Add refresh token"`
   One command records goal, decisions (with reasons), done, todos + the git
   state. Local, offline, plain text.
3. `handoff export --to codex` → writes `AGENTS.md` with a clean, delimited
   block. Already using `CLAUDE.md`? Your own text outside the block is never
   touched — proven by tests.
4. 7 targets: Claude Code, Codex/AGENTS.md, Gemini CLI, Cursor, Copilot,
   Windsurf, plain Markdown. One JSON source of truth, zero dependencies.
5. Not an AI agent, not a SaaS: 100% local, `pip install agenthandoff`, MIT.
   If this saves you one re-briefing, a ⭐ helps others find it →
   https://github.com/FaaWeell/AgentHandoff

### Show HN

> **Show HN: AgentHandoff – move context between AI coding agents in 10 seconds**
>
> I keep switching between Claude Code, Codex and Gemini CLI (quota, task fit,
> curiosity). Every switch meant 5–30 minutes of re-briefing, and decisions I'd
> already explained were gone.
>
> AgentHandoff is a small, dependency-free Python CLI: `handoff capture` records
> goal / decisions (+ why) / done / next steps / git state into
> `.agent-handoff/session.json`; `handoff export --to codex` (or `all`) writes
> agent-native files — `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`,
> `.cursor/rules/agent-handoff.mdc`, `.github/copilot-instructions.md`,
> `.windsurf/rules/…`, `.agent-handoff/HANDOFF.md`.
>
> The part I cared most about: it must never damage an existing rules file. The
> generated block is marker-delimited, re-exports replace it (idempotent), and
> everything outside the markers is preserved byte-for-byte — CRLF included.
> Malformed markers abort instead of guessing.
>
> Local-first, no telemetry, no LLM calls, MIT. Happy to hear what agent/format
> you'd want supported next.

### Reddit (short, story-first)

> **I got tired of re-briefing every new AI agent, so I wrote a 2-command CLI**
>
> Body: the personal story (quota ran out mid-refactor, then a 20-minute
> catch-up), what I built, the safety design (markers, idempotency, tests),
> two-command example, and an explicit ask: *what would make you actually use
> this?* No hard sell.

## 5. First two weeks after launch

- Reply to **every** comment/issue within 24 hours.
- Convert every piece of feedback into a public issue (the repo looks alive).
- Ship v0.1.1 within a week with the top three fixes.
- Keep ≥ 5 `good first issue`s open; personally mentor the first external PR.

## 6. What success looks like

| Window | Target |
| --- | --- |
| 2 weeks | 100 ⭐, first external issue/PR, PyPI downloads happening |
| 1 month | 500 ⭐, ≥ 5 external contributors, ≥ 10 organic issues |
| 3 months | 2,000 ⭐, format discussed or adopted by another project |

Signals that matter more than stars: a stranger opens a PR unasked, someone asks
for agent X support, someone mentions it without being asked.
