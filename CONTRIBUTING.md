# Contributing to AgentHandoff

Thanks for being here. AgentHandoff exists because people switch AI coding
agents all day and hate re-briefing. Every contribution — a bug report, a new
adapter, a typo fix — moves that forward.

## The 5-minute contribution: add a new agent

This is the best first PR in the repo. Two things to change:

**1. Register the adapter** in [`src/agenthandoff/adapters.py`](src/agenthandoff/adapters.py):

```python
TARGETS = {
    # …
    "myagent": Adapter(
        name="myagent",
        path="MYAGENT.md",          # the file your agent reads at startup
        description="MyAgent project context",
        aliases=("myagent-cli",),   # optional short names for --to
        placement="top",            # "top" or "end" of an existing file
    ),
}
```

**2. Add a test** in [`tests/test_adapters.py`](tests/test_adapters.py): add the
name/path to the parametrised `test_paths` table. The idempotency, user-content
and CRLF tests pick the new target up automatically.

Then:

```bash
pip install -e ".[dev]"
pytest -q
```

Rules for adapters:

- The file must be a documented startup-context file. Link its docs in the PR.
- Never special-case the writer; the marker block logic must stay generic.
- If your agent needs a frontmatter/header, use `Adapter.frontmatter` (only
  written when AgentHandoff creates the file).

## Development setup

```bash
git clone https://github.com/FaaWeell/AgentHandoff
cd AgentHandoff
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

pytest -q                      # full suite, no network, no external services
pytest --cov=agenthandoff      # coverage (CI gate: 80%)
ruff check src tests examples  # lint (CI gate)
```

Requirements: Python 3.11+ and git. The **runtime has zero dependencies** —
please keep it that way: no `requests`, no `click`, no `rich`, no
`pydantic` in `[project].dependencies`.

## Definition of a good change

1. `pytest` is green and `ruff check src tests examples` is clean on your machine
   (CI runs Linux/macOS/Windows × 3.11/3.12/3.13, plus lint).
2. New behaviour has a test that would fail without your change.
3. No new runtime dependency.
4. User-visible behaviour is documented in `README.md` **and** in `--help`.
5. Nothing destroys user content. If your change can write or delete bytes in a
   file AgentHandoff did not create, add a test proving user content survives.

## Data-safety rules (non-negotiable)

AgentHandoff writes into files users care about. Therefore:

- Generated content always lives between `<!-- agent-handoff:begin -->` and
  `<!-- agent-handoff:end -->`.
- Never delete a file, never truncate content outside the markers.
- If markers are malformed, **raise** with a clear message — do not guess.
- Writes go through `core.atomic_write_text` (temp file → fsync → `os.replace`).
- Re-exporting the same session must produce byte-identical files.

PRs that weaken any of these are rejected regardless of the feature they add.

## Commit messages

[Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add Zed adapter
fix: keep CRLF when exporting to existing file
docs: explain --to all
test: cover broken marker pair
chore: bump version to 0.1.1
```

## Project layout

```text
src/agenthandoff/
├── cli.py        # argparse commands, friendly errors, exit codes
├── core.py       # Session model, merge, save/load, HANDOFF.md renderer
├── gitutil.py    # git snapshot via subprocess (never raises)
├── adapters.py   # target registry + idempotent marker-block writer
└── importer.py   # import-log parser (EN/ID) + TODO scanner
tests/            # pytest suite (core, adapters, gitutil, importer, cli)
docs/             # FORMAT.md (data format), ROADMAP.md, LAUNCH.md
examples/         # demo.sh, sample-log.txt, sample-HANDOFF.md
```

## Reporting bugs

Use the issue templates. The most useful bug report contains:

- the command you ran (redact private paths),
- the relevant part of `.agent-handoff/session.json`,
- what you expected vs. what happened,
- OS + Python version (`handoff --version`, `python -V`).

**If AgentHandoff ever removed or changed content you did not put inside the
markers, say so in the first line of the issue** — that is a release blocker and
gets priority over everything else.

## Adding a `good first issue`

Maintainers: keep at least 5 open `good first issue`s. Good candidates are new
adapters, `--help` wording, extra import-log labels, and docs.

## Code of conduct

Be kind, assume good faith, critique code not people. Harassment of any kind is
not tolerated.

## License

By contributing you agree your work is released under the [MIT License](LICENSE).
