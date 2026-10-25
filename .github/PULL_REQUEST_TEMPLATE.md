## What does this PR do?

<!-- One or two sentences. Link the issue: "Closes #123". -->

## Type of change

- [ ] New agent adapter (`TARGETS` entry + test row)
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation
- [ ] CI / packaging / refactor

## Safety checklist (required for anything that writes files)

- [ ] The generated block still lives between `<!-- agent-handoff:begin -->` and
      `<!-- agent-handoff:end -->`.
- [ ] Re-exporting the same session produces byte-identical files (idempotency
      test added or existing one still passes).
- [ ] User content outside the markers is preserved — proven by a test.
- [ ] Writes still go through `core.atomic_write_text`.
- [ ] Malformed markers still abort with a clear error instead of guessing.

## Quality checklist

- [ ] `pytest -q` passes locally.
- [ ] New behaviour is covered by a test that fails without this change.
- [ ] No new runtime dependency in `[project].dependencies`.
- [ ] User-visible changes are documented in `README.md` **and** `--help`.
- [ ] `CHANGELOG.md` updated (for user-visible changes).
- [ ] `handoff export --to all` re-run and committed if `session.json` changed.

## How was this tested?

<!-- Commands, OS/Python version, screenshots or terminal output. -->
