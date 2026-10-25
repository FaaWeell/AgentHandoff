"""Import free-form log/chat notes (F6) and scan source code for TODOs (F7)."""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from .core import normalize

#: Label keywords → bucket. Both English and Bahasa Indonesia are supported
#: (FR-11), plus a few common aliases people actually type in chat logs.
LABELS: dict[str, tuple[str, str]] = {
    "decision": ("decision", "en"),
    "decisions": ("decision", "en"),
    "keputusan": ("decision", "id"),
    "todo": ("todo", "en"),
    "todos": ("todo", "en"),
    "to-do": ("todo", "en"),
    "next": ("todo", "en"),
    "next steps": ("todo", "en"),
    "selanjutnya": ("todo", "id"),
    "berikutnya": ("todo", "id"),
    "rencana": ("todo", "id"),
    "done": ("done", "en"),
    "completed": ("done", "en"),
    "selesai": ("done", "id"),
    "sudah": ("done", "id"),
    "note": ("note", "en"),
    "notes": ("note", "en"),
    "catatan": ("note", "id"),
}

_LABEL_ALT = "|".join(
    re.escape(label) for label in sorted(LABELS, key=len, reverse=True)
)

# Optional bullet (`-`, `*`, `+`, `>`, `1.`), optional bold/italic wrappers,
# one of the labels, then `:` or an en/em dash.
LINE_RE = re.compile(
    rf"""
    ^\s*
    (?:[-*+>]\s*|\d+[.)]\s*)?
    (?:[*_]{{1,3}}\s*)?
    (?P<label>{_LABEL_ALT})
    \s*(?:[*_]{{1,3}})?
    \s*(?::|：|\-{{1,2}}|–|—)\s*
    (?:(?:[*_]{{1,2}})\s*)?
    (?P<text>.+?)
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)

#: Anything that looks like a TODO/FIXME marker in source code.
SOURCE_TODO_RE = re.compile(r"\b(?P<label>TODO|FIXME|HACK|XXX)\b\s*[:\-]?\s*(?P<text>.{0,200})")

SCAN_EXTENSIONS = {
    ".py", ".pyi", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".vue",
    ".svelte", ".go", ".rs", ".java", ".kt", ".kts", ".scala", ".rb", ".php",
    ".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".cs", ".swift", ".m", ".mm",
    ".sh", ".bash", ".zsh", ".fish", ".ps1", ".sql", ".lua", ".dart", ".ex",
    ".exs", ".erl", ".hs", ".clj", ".elm", ".zig", ".nim", ".r", ".jl",
    ".toml", ".yaml", ".yml", ".ini", ".cfg", ".dockerfile", ".tf",
}

SKIP_DIRS = {
    ".git", ".hg", ".svn", ".agent-handoff", ".venv", "venv", "env", "node_modules",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", ".nox",
    "dist", "build", "out", "target", "vendor", ".next", ".nuxt", ".cache",
    "coverage", ".coverage", ".idea", ".vscode", ".gradle", ".terraform",
}

MAX_SCAN_BYTES = 512 * 1024
MAX_TODO_ITEMS = 50
MAX_TEXT_LEN = 160


@dataclass
class ParsedLog:
    """Result of parsing a free-form log file."""

    decisions: list[str] = field(default_factory=list)
    todos: list[str] = field(default_factory=list)
    done: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.decisions) + len(self.todos) + len(self.done) + len(self.notes)


def _add_unique(target: list[str], value: str) -> None:
    key = normalize(value)
    if key and all(normalize(existing) != key for existing in target):
        target.append(value)


def parse_log(text: str) -> ParsedLog:
    """Extract decisions / todos / done / notes from free-form text.

    Only lines that start with a recognised label are imported, so arbitrary
    prose never pollutes the session.
    """
    parsed = ParsedLog()
    # Excel/Notepad exports often start with a BOM.
    text = text.lstrip("\ufeff")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = LINE_RE.match(line)
        if not match:
            continue
        bucket = LABELS[match.group("label").lower()][0]
        value = " ".join(match.group("text").split()).strip()
        value = value.strip("*_` ")
        # "TODO:" / "Decision: --" carry no information.
        if not value.strip("-–—:;*_` "):
            continue
        if bucket == "decision":
            _add_unique(parsed.decisions, value)
        elif bucket == "todo":
            _add_unique(parsed.todos, value)
        elif bucket == "done":
            _add_unique(parsed.done, value)
        else:
            _add_unique(parsed.notes, value)
    return parsed


def import_file(path: str | Path) -> ParsedLog:
    """Read *path* as UTF-8 (replacing bad bytes) and parse it."""
    file_path = Path(path).expanduser()
    if not file_path.exists():
        raise FileNotFoundError(str(file_path))
    if file_path.is_dir():
        raise IsADirectoryError(str(file_path))
    text = file_path.read_text(encoding="utf-8", errors="replace")
    return parse_log(text)


# --------------------------------------------------------------------------- #
# TODO scanning
# --------------------------------------------------------------------------- #
def _iter_source_files(root: Path) -> Iterator[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            name for name in dirnames if name.lower() not in SKIP_DIRS
        )
        for filename in sorted(filenames):
            path = Path(dirpath) / filename
            suffix = path.suffix.lower()
            if suffix in SCAN_EXTENSIONS or filename.lower() == "dockerfile":
                yield path


def scan_todos(
    root: Path | str,
    *,
    limit: int = MAX_TODO_ITEMS,
) -> list[str]:
    """Collect ``TODO``/``FIXME`` comments from source code as next steps.

    Output format: ``path/to/file.py:12 — TODO: text``. The list is capped so a
    large repository can never flood the session (plan.md §3.3).
    """
    base = Path(root)
    if not base.is_dir():
        return []
    found: list[str] = []
    seen: set[str] = set()
    for path in _iter_source_files(base):
        try:
            if path.stat().st_size > MAX_SCAN_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            match = SOURCE_TODO_RE.search(line)
            if not match:
                continue
            message = " ".join(match.group("text").split()).rstrip("*/-#> ")
            message = message[:MAX_TEXT_LEN]
            label = match.group("label")
            relative = path.relative_to(base).as_posix()
            body = f"{label}: {message}" if message else label
            entry = f"{relative}:{lineno} — {body}"
            key = normalize(entry)
            if key in seen:
                continue
            seen.add(key)
            found.append(entry)
            if len(found) >= limit:
                return found
    return found
