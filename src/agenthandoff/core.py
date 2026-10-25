"""Session model, merge semantics, storage and Markdown rendering.

``.agent-handoff/session.json`` is the single source of truth (decision T2).
Every other artifact — ``HANDOFF.md`` and each agent-native file — is rendered
from it, so the formats can never drift apart.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from . import __version__

#: Folder that holds all AgentHandoff state, inside the user's project.
SESSION_DIR = ".agent-handoff"
SESSION_FILE = "session.json"
HANDOFF_FILE = "HANDOFF.md"
#: Bumped only for breaking changes to the on-disk format (additive is free).
SCHEMA_VERSION = 1


class SessionError(Exception):
    """A user-facing problem with the session file (never a raw traceback)."""


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def now_iso() -> str:
    """Current local time as an ISO-8601 string with timezone offset."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def normalize(text: object) -> str:
    """Normalise a line so ``Done`` can match an equivalent ``TODO``.

    Case, surrounding whitespace, inner whitespace runs and trailing punctuation
    are ignored; everything else (including non-ASCII text) is preserved.
    """
    value = " ".join(str(text).split()).strip().casefold()
    return value.rstrip(" .;:,!?")


def _dedupe(items: Iterable[Any], key=normalize) -> list[Any]:
    """Stable de-duplication that keeps the first occurrence order."""
    seen: set[str] = set()
    result: list[Any] = []
    for item in items:
        marker = key(item)
        if not marker or marker in seen:
            continue
        seen.add(marker)
        result.append(item)
    return result


def _clean_str(value: object, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _clean_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple)):
        return []
    return _dedupe(_clean_str(item) for item in value if _clean_str(item))


def _clean_decisions(value: object) -> list[dict[str, str]]:
    """Accept both ``{"text": ..., "reason": ...}`` and bare strings."""
    if value is None:
        return []
    if isinstance(value, (str, Mapping)):
        value = [value]
    if not isinstance(value, (list, tuple)):
        return []

    decisions: list[dict[str, str]] = []
    for raw in value:
        if isinstance(raw, Mapping):
            text = _clean_str(raw.get("text"))
            reason = _clean_str(raw.get("reason"))
        else:
            text, reason = split_decision(_clean_str(raw))
        if text:
            decisions.append({"text": text, "reason": reason})
    return dedupe_decisions(decisions)


def split_decision(value: str) -> tuple[str, str]:
    """Split ``"text :: reason"`` (or ``"text -- reason"``) into its parts."""
    text = _clean_str(value)
    for separator in ("::", " -- "):
        if separator in text:
            head, tail = text.split(separator, 1)
            if _clean_str(head):
                return _clean_str(head), _clean_str(tail)
    return text, ""


def dedupe_decisions(decisions: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    """Merge decisions by their text, keeping the richest reason."""
    merged: dict[str, dict[str, str]] = {}
    for decision in decisions:
        text = _clean_str(decision.get("text"))
        if not text:
            continue
        reason = _clean_str(decision.get("reason"))
        key = normalize(text)
        if key in merged:
            if reason and not merged[key]["reason"]:
                merged[key]["reason"] = reason
        else:
            merged[key] = {"text": text, "reason": reason}
    return list(merged.values())


# --------------------------------------------------------------------------- #
# Session model
# --------------------------------------------------------------------------- #
@dataclass
class Session:
    """The handoff state of one project (PRD §11, schema v1)."""

    project: str = ""
    goal: str = ""
    source_agent: str = ""
    created_at: str = ""
    updated_at: str = ""
    decisions: list[dict[str, str]] = field(default_factory=list)
    todos: list[str] = field(default_factory=list)
    done: list[str] = field(default_factory=list)
    notes: str = ""
    git: dict[str, Any] = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION

    # -- serialisation ----------------------------------------------------- #
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project": self.project,
            "goal": self.goal,
            "source_agent": self.source_agent,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "decisions": [dict(item) for item in self.decisions],
            "todos": list(self.todos),
            "done": list(self.done),
            "notes": self.notes,
            "git": dict(self.git),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Session:
        if not isinstance(data, Mapping):
            raise SessionError("session.json must contain a JSON object.")
        schema_version = data.get("schema_version", SCHEMA_VERSION)
        try:
            schema_version = int(schema_version)
        except (TypeError, ValueError):
            schema_version = SCHEMA_VERSION
        git = data.get("git") or {}
        return cls(
            project=_clean_str(data.get("project")),
            goal=_clean_str(data.get("goal")),
            source_agent=_clean_str(data.get("source_agent")),
            created_at=_clean_str(data.get("created_at")),
            updated_at=_clean_str(data.get("updated_at")),
            decisions=_clean_decisions(data.get("decisions")),
            todos=_clean_list(data.get("todos")),
            done=_clean_list(data.get("done")),
            notes=_clean_str(data.get("notes")),
            git=dict(git) if isinstance(git, Mapping) else {},
            schema_version=schema_version,
        )

    # -- convenience ------------------------------------------------------- #
    @property
    def is_empty(self) -> bool:
        return not any(
            [
                self.goal,
                self.decisions,
                self.todos,
                self.done,
                self.notes,
                self.source_agent,
            ]
        )

    def counts(self) -> dict[str, int]:
        return {
            "decisions": len(self.decisions),
            "todos": len(self.todos),
            "done": len(self.done),
        }

    # -- merge (FR-07) ----------------------------------------------------- #
    def merge(self, incoming: Session) -> Session:
        """Merge *incoming* into ``self`` in place and return ``self``.

        Rules:
        * ``goal`` / ``source_agent`` are replaced only when the incoming value
          is non-empty (capture without flags never erases the goal).
        * ``decisions`` merge by text; a new non-empty reason wins.
        * A ``done`` item with the same text as a todo removes that todo.
        * ``todos`` and ``done`` never contain duplicates and never overlap.
        * ``notes`` are appended, never overwritten.
        """
        stamp = now_iso()
        if not self.created_at:
            self.created_at = incoming.created_at or stamp

        if incoming.project:
            self.project = incoming.project
        if incoming.goal:
            self.goal = incoming.goal
        if incoming.source_agent:
            self.source_agent = incoming.source_agent

        self.decisions = dedupe_decisions([*self.decisions, *incoming.decisions])

        done = _dedupe([*self.done, *incoming.done])
        done_keys = {normalize(item) for item in done}
        todos = [
            item
            for item in _dedupe([*self.todos, *incoming.todos])
            if normalize(item) not in done_keys
        ]

        self.done = done
        self.todos = todos
        self.notes = _merge_notes(self.notes, incoming.notes)
        if incoming.git:
            self.git = dict(incoming.git)
        self.updated_at = stamp
        return self


def _merge_notes(existing: str, incoming: str) -> str:
    if not incoming:
        return existing
    if not existing:
        return incoming
    if incoming in existing:
        return existing
    if existing in incoming:
        return incoming
    return f"{existing.rstrip()}\n\n{incoming.strip()}"


# --------------------------------------------------------------------------- #
# Paths & storage
# --------------------------------------------------------------------------- #
def project_root(path: str | Path | None = None) -> Path:
    """Resolve the project root, failing with a friendly message."""
    root = Path(path or ".").expanduser()
    try:
        root = root.resolve()
    except OSError:  # pragma: no cover - exotic filesystems
        root = Path(os.path.abspath(str(root)))
    if root.exists() and not root.is_dir():
        raise SessionError(
            f"'{root}' is a file, not a project folder.\n"
            "  Pass --path pointing at a valid project folder."
        )
    return root


def session_dir(root: Path | str) -> Path:
    return Path(root) / SESSION_DIR


def session_path(root: Path | str) -> Path:
    return session_dir(root) / SESSION_FILE


def handoff_path(root: Path | str) -> Path:
    return session_dir(root) / HANDOFF_FILE


def atomic_write_text(path: Path, text: str, newline: str = "") -> None:
    """Write *text* atomically (UTF-8, no newline translation, atomic replace).

    ``newline=""`` disables newline translation so the caller fully controls the
    bytes on disk; this keeps CRLF files CRLF and LF files LF.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline=newline) as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            try:
                shutil.copymode(path, tmp)
            except OSError:  # pragma: no cover - platform dependent
                pass
        else:
            # mkstemp creates 0600; a new project file should be world-readable
            # like any other file the user creates (respecting their umask).
            mask = os.umask(0)
            os.umask(mask)
            try:
                os.chmod(tmp, 0o666 & ~mask)
            except OSError:  # pragma: no cover - platform dependent
                pass
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def load_session(root: Path | str, required: bool = False) -> Session | None:
    """Load the session for *root*.

    Returns ``None`` when the file does not exist (unless *required*), and raises
    :class:`SessionError` with an actionable message when the JSON is broken
    (PRD §10 "Keandalan").
    """
    path = session_path(root)
    if not path.exists():
        if required:
            raise SessionError(
                "No handoff found for this project.\n"
                "  Start with: handoff capture --goal \"what you are working on\""
            )
        return None
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SessionError(f"Could not read {path}: {exc}") from exc
    if not raw.strip():
        raise SessionError(
            f"{path} is empty. Delete it and run 'handoff capture' again."
        )
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SessionError(
            f"{path} is not valid JSON (line {exc.lineno}, column {exc.colno}).\n"
            "  Fix the file, or delete it and run 'handoff capture' again."
        ) from exc
    try:
        return Session.from_dict(data)
    except SessionError as exc:
        raise SessionError(f"{path}: {exc}") from exc


def save_session(root: Path | str, session: Session) -> Path:
    """Persist the session as pretty, diff-friendly JSON and return its path."""
    path = session_path(root)
    payload = json.dumps(session.to_dict(), indent=2, ensure_ascii=False) + "\n"
    try:
        atomic_write_text(path, payload)
    except OSError as exc:
        raise SessionError(f"Could not write {path}: {exc}") from exc
    return path


# --------------------------------------------------------------------------- #
# Capture
# --------------------------------------------------------------------------- #
def capture(
    root: Path | str,
    *,
    goal: str | None = None,
    source_agent: str | None = None,
    decisions: Sequence[str] | None = None,
    todos: Sequence[str] | None = None,
    done: Sequence[str] | None = None,
    notes: str | None = None,
    scan_todos: bool = False,
) -> Session:
    """Capture (or update) the handoff session for *root*.

    A repeated capture merges into the existing session instead of overwriting
    it (F8), and always refreshes the git snapshot.
    """
    from .gitutil import git_snapshot  # local import keeps module import cheap
    from .importer import scan_todos as scan_todos_fn

    project = project_root(root)
    existing = load_session(project)

    stamp = now_iso()
    incoming = Session(
        project=project.name or "project",
        goal=_clean_str(goal),
        source_agent=_clean_str(source_agent),
        created_at=stamp,
        updated_at=stamp,
        decisions=_clean_decisions(list(decisions or [])),
        todos=_clean_list(list(todos or [])),
        done=_clean_list(list(done or [])),
        notes=_clean_str(notes),
        git=git_snapshot(project),
    )

    if scan_todos:
        scanned = scan_todos_fn(project)
        if scanned:
            incoming.todos = _dedupe([*incoming.todos, *scanned])

    if existing is None:
        session = incoming
        session.created_at = stamp
        session.updated_at = stamp
        # A first capture should still respect the --done/--todo relationship.
        session.merge(Session())
        session.created_at = stamp
    else:
        if not existing.project:
            existing.project = incoming.project
        session = existing.merge(incoming)

    session.updated_at = stamp
    save_session(project, session)
    write_handoff(project, session)
    return session


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
EMPTY_LINE = "_Nothing recorded yet._"


def _md_inline(text: str) -> str:
    """Keep Markdown output safe from accidental table/code breakage."""
    return " ".join(str(text).split())


def _render_git(git: Mapping[str, Any]) -> list[str]:
    if not git or not git.get("is_repo"):
        return [
            "Not a git repository (or git is not installed) — no git snapshot.",
        ]

    lines: list[str] = []
    if git.get("branch"):
        lines.append(f"- **Branch:** `{git['branch']}`")
    if git.get("last_commit"):
        lines.append(f"- **Last commit:** `{git['last_commit']}`")

    changed = list(git.get("changed_files") or [])
    count = int(git.get("changed_count") or len(changed))
    if count:
        lines.append(f"- **Changed files:** {count}")
        for name in changed[:15]:
            lines.append(f"  - `{name}`")
        if count > 15:
            lines.append(f"  - … and {count - 15} more")
    else:
        lines.append("- **Changed files:** none (working tree clean)")

    commits = list(git.get("recent_commits") or [])
    if commits:
        lines.append("- **Recent commits:**")
        for commit in commits:
            lines.append(f"  - `{commit}`")

    diff_stat = (git.get("diff_stat") or "").strip()
    if diff_stat:
        lines.append("- **Diff stat:**")
        lines.append("")
        lines.append("```text")
        lines.extend(diff_stat.splitlines())
        lines.append("```")
    return lines


def render_handoff(session: Session) -> str:
    """Render ``HANDOFF.md`` from *session* (PRD §12)."""
    project = session.project or "project"
    out: list[str] = [
        f"# 🤝 AgentHandoff — {project}",
        "",
        (
            "> Generated from `.agent-handoff/session.json`. "
            "Edit the JSON (via `handoff capture`), not this file."
        ),
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Project | `{project}` |",
        f"| Last agent | {session.source_agent or '—'} |",
        f"| Updated | {session.updated_at or '—'} |",
        f"| Created | {session.created_at or '—'} |",
        "",
        "## 🎯 Goal",
        "",
        _md_inline(session.goal) if session.goal else EMPTY_LINE,
        "",
        "## 🌿 Git state",
        "",
        *_render_git(session.git),
        "",
        "## ✅ Done",
        "",
    ]
    if session.done:
        out.extend(f"- [x] {_md_inline(item)}" for item in session.done)
    else:
        out.append(EMPTY_LINE)

    out.extend(["", "## 🧭 Decisions (and why)", ""])
    if session.decisions:
        for decision in session.decisions:
            text = _md_inline(decision.get("text", ""))
            reason = _md_inline(decision.get("reason", ""))
            out.append(f"- **{text}**" + (f" — {reason}" if reason else ""))
    else:
        out.append(EMPTY_LINE)

    out.extend(["", "## ⏭️ Next steps", ""])
    if session.todos:
        out.extend(f"- [ ] {_md_inline(item)}" for item in session.todos)
    else:
        out.append(EMPTY_LINE)

    out.extend(["", "## 📝 Notes", "", session.notes.strip() or EMPTY_LINE, ""])
    out.extend(
        [
            "---",
            "",
            (
                f"_Generated by AgentHandoff v{__version__} — "
                "`handoff capture` to update, `handoff export --to <agent>` to share._"
            ),
            "",
        ]
    )
    return "\n".join(out)


def write_handoff(root: Path | str, session: Session) -> Path:
    """Write ``.agent-handoff/HANDOFF.md`` from *session*."""
    path = handoff_path(root)
    try:
        atomic_write_text(path, render_handoff(session))
    except OSError as exc:  # pragma: no cover - permissions
        raise SessionError(f"Could not write {path}: {exc}") from exc
    return path
