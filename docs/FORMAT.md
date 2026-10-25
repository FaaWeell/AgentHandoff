# AgentHandoff data format — `session.json` v1

This document is the contract between AgentHandoff and anything that wants to
read or write the same data. It is intentionally small: one JSON file is the
single source of truth, and every other output (`.agent-handoff/HANDOFF.md`,
`CLAUDE.md`, `AGENTS.md`, …) is generated from it.

- **Location:** `<project>/.agent-handoff/session.json`
- **Encoding:** UTF-8, no BOM, LF newlines, 2-space indent (diff-friendly)
- **MIME:** `application/json`
- **Stability:** v1. Additive changes are allowed without a version bump;
  removing or renaming a field, or changing a field's type, requires a schema
  version bump.

## Example

```json
{
  "schema_version": 1,
  "project": "my-app",
  "goal": "Menyelesaikan fitur login",
  "source_agent": "claude",
  "created_at": "2026-10-25T10:00:00+07:00",
  "updated_at": "2026-10-25T12:30:00+07:00",
  "decisions": [
    { "text": "Pakai JWT", "reason": "stateless, cocok untuk API" }
  ],
  "todos": ["Tambahkan refresh token", "Tulis test untuk /login"],
  "done": ["Endpoint /login selesai"],
  "notes": "Catatan bebas…",
  "git": {
    "is_repo": true,
    "branch": "feat/login",
    "last_commit": "a1b2c3d feat: login endpoint",
    "changed_files": ["src/auth.py"],
    "changed_count": 1,
    "recent_commits": ["a1b2c3d feat: login endpoint"],
    "diff_stat": " src/auth.py | 40 ++++"
  }
}
```

## Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `schema_version` | integer | recommended | Format version. Absent is treated as `1`. |
| `project` | string | yes | Project name, normally the root directory name. |
| `goal` | string | yes | What the project/session is trying to achieve. Empty string allowed. |
| `source_agent` | string | yes | Agent the session was captured from (`claude`, `codex`, `gemini`, …). Free-form. |
| `created_at` | string | yes | ISO-8601 with timezone offset. Set once, never changes. |
| `updated_at` | string | yes | ISO-8601 with timezone offset. Refreshed on every capture. |
| `decisions` | array of object | yes | `{ "text": string, "reason": string }`. `reason` may be `""`. |
| `todos` | array of string | yes | Next steps, in the order they were recorded. |
| `done` | array of string | yes | Completed items. Never overlaps with `todos`. |
| `notes` | string | yes | Free-form Markdown-ish text; appended on merge. |
| `git` | object | yes | Snapshot; `{"is_repo": false}` when not in a git repository. |

### `git` object

| Field | Type | Description |
| --- | --- | --- |
| `is_repo` | boolean | `false` → all other fields may be absent. |
| `branch` | string | Current branch, or `(detached: <sha>)`. Empty for a repo without commits. |
| `last_commit` | string | `"<short-sha> <subject>"` of `HEAD`, or `""`. |
| `changed_files` | array of string | Paths relative to the project root, POSIX separators, capped at 200. |
| `changed_count` | integer | Number of changed entries *before* the cap (may exceed `len(changed_files)`). |
| `recent_commits` | array of string | Up to 10 `"<short-sha> <subject>"` entries, newest first. |
| `diff_stat` | string | Output of `git diff HEAD --stat` (falls back to `git diff --stat`). |

## Merge semantics (normative)

A capture with an existing session merges (`Session.merge`):

1. `goal` and `source_agent` are replaced **only** when the new value is
   non-empty — a flag-less capture never erases the goal.
2. `decisions` merge by normalised `text`. If a previously empty `reason` gets a
   value, the richer reason wins. Order = first occurrence.
3. `done` is the stable, de-duplicated union of old and new `done`.
   Any `done` item removes a `todo` with the same normalised text.
4. `todos` is the stable, de-duplicated union of old and new `todos`, excluding
   anything present in `done`.
5. `notes` are appended (`old + "\n\n" + new`); an identical note is not
   duplicated, and a note already contained in the other is not repeated.
6. `git` is fully replaced by the newest snapshot.
7. `created_at` never changes; `updated_at` is always now.

**Normalisation** for comparison (used by 3 and 4): collapse whitespace, strip,
casefold, and drop trailing `. ; : , ! ?`. Nothing else — non-ASCII text and
emoji are preserved exactly.

## Export block format

Files other than `session.json` and `HANDOFF.md` receive exactly one block:

```markdown
<!-- agent-handoff:begin -->
## 🤝 AgentHandoff context — <project>
…goal, git state, done, decisions, next steps, notes…
<!-- agent-handoff:end -->
```

Rules:

- Re-export **replaces** the existing block; it never appends a second one.
- Duplicated blocks (e.g. from a bad merge in git) are collapsed to one.
- Content outside the markers is preserved byte-for-byte, including CRLF line
  endings and trailing whitespace.
- `<!-- agent-handoff:begin -->` without a matching `end` marker is an error:
  the export aborts and leaves the file untouched.
- When a file is created for Cursor, YAML frontmatter is written first
  (`description`, `globs`, `alwaysApply: true`); existing frontmatter is never
  modified or duplicated.
- `.agent-handoff/HANDOFF.md` is fully generated (no markers required) because
  it is documented as a generated file.

## Reading the format from another tool

Minimal consumer:

```python
import json, pathlib

data = json.loads(pathlib.Path(".agent-handoff/session.json").read_text("utf-8"))
goal, todos, done = data["goal"], data["todos"], data["done"]
```

Minimum viable producer (this already makes `handoff show` and
`handoff export --to all` work):

```python
{
  "schema_version": 1,
  "project": "x",
  "goal": "…",
  "source_agent": "my-tool",
  "created_at": "2026-10-25T10:00:00+00:00",
  "updated_at": "2026-10-25T10:00:00+00:00",
  "decisions": [],
  "todos": [],
  "done": [],
  "notes": "",
  "git": {"is_repo": false}
}
```

Tolerated on read for forward/backward compatibility: unknown fields (ignored),
bare strings in `decisions` (split on `" :: "` or `" -- "`), a missing
`schema_version`, and non-object `git` (treated as `{}`).
