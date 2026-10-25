"""Agent adapters: where each agent expects its context file, and how to write it.

The writer is deliberately conservative — it is the only part of AgentHandoff
that touches files the user already owns (plan.md "gerbang kualitas"):

* the generated block is delimited by ``<!-- agent-handoff:begin/end -->``;
* re-exporting replaces that block in place → idempotent, never duplicated;
* content outside the markers is preserved byte-for-byte;
* a broken marker pair raises instead of guessing, so nothing is destroyed.

Adding a new agent is a one-line entry in :data:`TARGETS` (or ``--to`` alias),
which is exactly the "perfect first PR" promised in the README.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from .core import (
    HANDOFF_FILE,
    SESSION_DIR,
    Session,
    SessionError,
    atomic_write_text,
    render_handoff,
)

BEGIN_MARKER = "<!-- agent-handoff:begin -->"
END_MARKER = "<!-- agent-handoff:end -->"
BEGIN_PREFIX = "agent-handoff:begin"
END_PREFIX = "agent-handoff:end"


class AdapterError(SessionError):
    """Raised when an export target or an existing file cannot be handled safely."""


@dataclass(frozen=True)
class Adapter:
    """Description of one export target."""

    name: str
    path: str
    description: str
    aliases: tuple[str, ...] = ()
    placement: str = "top"  # "top" or "end"
    frontmatter: str = ""
    #: ``True`` when the whole file is generated (no user content to protect).
    fully_generated: bool = False


def _cursor_frontmatter() -> str:
    return (
        "---\n"
        "description: AgentHandoff session context (goal, decisions, next steps)\n"
        'globs: ["**/*"]\n'
        "alwaysApply: true\n"
        "---\n"
    )


CURSOR = Adapter(
    name="cursor",
    path=".cursor/rules/agent-handoff.mdc",
    description="Cursor rule file (.mdc) with frontmatter",
    aliases=("cursor-rules",),
    placement="end",
    frontmatter=_cursor_frontmatter(),
)

#: Ordered registry of supported targets. Order is the order used by ``--to all``.
TARGETS: dict[str, Adapter] = {
    "claude": Adapter(
        name="claude",
        path="CLAUDE.md",
        description="Claude Code project memory",
        aliases=("claude-code", "claudecode"),
        placement="top",
    ),
    "codex": Adapter(
        name="codex",
        path="AGENTS.md",
        description="Codex / any AGENTS.md-compatible agent",
        aliases=("agents", "agents-md", "openai", "opencode"),
        placement="top",
    ),
    "gemini": Adapter(
        name="gemini",
        path="GEMINI.md",
        description="Gemini CLI context file",
        aliases=("gemini-cli",),
        placement="top",
    ),
    "cursor": CURSOR,
    "copilot": Adapter(
        name="copilot",
        path=".github/copilot-instructions.md",
        description="GitHub Copilot custom instructions",
        aliases=("github-copilot", "githubcopilot"),
        placement="end",
    ),
    "windsurf": Adapter(
        name="windsurf",
        path=".windsurf/rules/agent-handoff.md",
        description="Windsurf (Codeium) rules file",
        aliases=("codeium",),
        placement="end",
    ),
    "markdown": Adapter(
        name="markdown",
        path=f"{SESSION_DIR}/{HANDOFF_FILE}",
        description="Agent-neutral Markdown handoff",
        aliases=("md", "handoff", "neutral", "generic"),
        placement="end",
        fully_generated=True,
    ),
}

#: Resolve aliases (``codex``, ``agents``, ``md`` …) to canonical target names.
ALIASES: dict[str, str] = {
    alias.casefold(): adapter.name
    for adapter in TARGETS.values()
    for alias in (adapter.name, *adapter.aliases)
}

TARGET_NAMES: tuple[str, ...] = tuple(TARGETS)


def resolve_target(name: str) -> Adapter:
    """Return the adapter for *name* or raise a helpful :class:`AdapterError`."""
    key = (name or "").strip().casefold()
    canonical = ALIASES.get(key)
    if canonical is None:
        raise AdapterError(
            f"Target agent tidak dikenal: '{name}'.\n"
            f"  Target yang tersedia: {', '.join(TARGET_NAMES)}\n"
            "  Gunakan '--to all' untuk mengekspor ke semua target."
        )
    return TARGETS[canonical]


def resolve_targets(names: Sequence[str] | str) -> list[Adapter]:
    """Resolve one or more target names, expanding ``all`` and de-duplicating."""
    if isinstance(names, str):
        names = [names]
    resolved: list[Adapter] = []
    seen: set[str] = set()
    for raw in names:
        for part in str(raw).replace(",", " ").split():
            if part.casefold() in ("all", "*"):
                candidates = [TARGETS[name] for name in TARGET_NAMES]
            else:
                candidates = [resolve_target(part)]
            for adapter in candidates:
                if adapter.name not in seen:
                    seen.add(adapter.name)
                    resolved.append(adapter)
    if not resolved:
        raise AdapterError(
            "Tidak ada target yang dipilih.\n"
            f"  Contoh: handoff export --to {TARGET_NAMES[0]}  (atau --to all)"
        )
    return resolved


# --------------------------------------------------------------------------- #
# Block handling
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Block:
    """Location of the handoff block inside a file."""

    start: int
    end: int  # exclusive
    count: int = 1


def _marker_spans(text: str) -> list[tuple[int, int]]:
    """Return ``(begin_index, end_index_exclusive)`` for every complete block."""
    spans: list[tuple[int, int]] = []
    cursor = 0
    while True:
        begin = text.find(BEGIN_MARKER, cursor)
        if begin == -1:
            return spans
        end = text.find(END_MARKER, begin + len(BEGIN_MARKER))
        if end == -1:
            raise AdapterError(
                "File sudah berisi marker 'agent-handoff:begin' tanpa 'agent-handoff:end'.\n"
                "  Perbaiki/hapus blok tersebut secara manual, lalu jalankan export lagi.\n"
                "  (AgentHandoff tidak akan menebak dan menimpa konten Anda.)"
            )
        stop = end + len(END_MARKER)
        # Swallow a trailing newline so replacement does not accumulate blanks.
        if text[stop : stop + 2] == "\r\n":
            stop += 2
        elif text[stop : stop + 1] == "\n":
            stop += 1
        spans.append((begin, stop))
        cursor = stop


def find_block(text: str) -> Block | None:
    """Locate the (first) handoff block inside *text*."""
    spans = _marker_spans(text)
    if not spans:
        return None
    start, end = spans[0]
    return Block(start, end, count=len(spans))


def _frontmatter_end(text: str) -> int:
    """Length of a leading YAML frontmatter block, or 0 when there is none."""
    if not text.startswith("---"):
        return 0
    match = re.match(r"^---\r?\n.*?\r?\n---[ \t]*(?:\r?\n|$)", text, re.DOTALL)
    return match.end() if match else 0


def _insert(text: str, block: str, placement: str, newline: str) -> str:
    """Insert *block* into *text* without altering existing content."""
    stripped = text.strip()
    if not stripped:
        return block + newline

    if placement == "top":
        offset = _frontmatter_end(text)
        head, tail = text[:offset], text[offset:]
        if head and not head.endswith(("\n", "\r")):
            head += newline
        return head + block + newline + tail.lstrip("\r\n")

    body = text if text.endswith(("\n", "\r")) else text + newline
    return body + newline + block + newline


def merge_block(existing: str, block: str, adapter: Adapter) -> str:
    """Return *existing* with exactly one handoff block (idempotent replace)."""
    newline = "\r\n" if "\r\n" in existing else "\n"
    normalized_block = block.replace("\r\n", "\n").replace("\n", newline).rstrip(
        "\r\n"
    )

    spans = _marker_spans(existing)
    if spans:
        # Replace the first block, then drop any duplicated blocks (these are
        # always generated by us, never user prose).
        pieces: list[str] = []
        cursor = 0
        start, stop = spans[0]
        pieces.append(existing[cursor:start])
        pieces.append(normalized_block + newline)
        cursor = stop
        for start, stop in spans[1:]:
            pieces.append(existing[cursor:start])
            cursor = stop
        pieces.append(existing[cursor:])
        result = "".join(pieces)
        if len(spans) > 1:
            # Removing duplicated blocks can leave a run of blank lines behind;
            # collapse those (never touches non-empty user lines).
            result = re.sub(r"(?:[ \t]*\r?\n){3,}", newline + newline, result)
        return result

    return _insert(existing, normalized_block, adapter.placement, newline)


# --------------------------------------------------------------------------- #
# Rendering the export block
# --------------------------------------------------------------------------- #
def _section(title: str, body: Sequence[str], empty: str = "_Nothing recorded yet._") -> list[str]:
    return [f"### {title}", "", *(body or [empty]), ""]


def render_block(session: Session) -> str:
    """Render the Markdown payload that goes inside the markers."""
    project = session.project or "project"
    lines: list[str] = [
        BEGIN_MARKER,
        f"## 🤝 AgentHandoff context — {project}",
        "",
        f"**Last agent:** {session.source_agent or 'unknown'}  ",
        f"**Updated:** {session.updated_at or 'unknown'}",
        "",
        "This block is generated by [AgentHandoff](https://github.com/FaaWeell/AgentHandoff).",
        (
            "Read it first, continue from **Next steps**, "
            "and keep user content outside the markers intact."
        ),
        "",
    ]

    lines += _section("🎯 Goal", [session.goal.strip()] if session.goal.strip() else [])

    git = session.git or {}
    if git.get("is_repo"):
        git_lines = []
        if git.get("branch"):
            git_lines.append(f"- Branch: `{git['branch']}`")
        if git.get("last_commit"):
            git_lines.append(f"- Last commit: `{git['last_commit']}`")
        changed = list(git.get("changed_files") or [])
        count = int(git.get("changed_count") or len(changed))
        if count:
            shown = ", ".join(f"`{name}`" for name in changed[:10])
            more = f" (+{count - 10} more)" if count > 10 else ""
            git_lines.append(f"- Changed files ({count}): {shown}{more}")
        lines += _section("🌿 Git state", git_lines)

    lines += _section("✅ Done", [f"- [x] {item}" for item in session.done])
    lines += _section(
        "🧭 Decisions",
        [
            f"- **{d.get('text', '')}**" + (f" — {d['reason']}" if d.get("reason") else "")
            for d in session.decisions
        ],
    )
    lines += _section("⏭️ Next steps", [f"- [ ] {item}" for item in session.todos])

    if session.notes.strip():
        lines += _section("📝 Notes", session.notes.strip().splitlines())

    lines += [END_MARKER]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# Export
# --------------------------------------------------------------------------- #
@dataclass
class ExportResult:
    """Outcome of writing one target."""

    target: str
    path: Path
    status: str  # "created" | "updated" | "unchanged"

    @property
    def display_path(self) -> str:
        return self.path.as_posix()


def _read_existing(path: Path) -> str | None:
    if not path.exists():
        return None
    if not path.is_file():
        raise AdapterError(f"'{path}' ada tetapi bukan file — export dibatalkan.")
    try:
        # newline="" keeps CRLF files CRLF (no silent whole-file rewrite).
        with open(path, encoding="utf-8", errors="replace", newline="") as handle:
            return handle.read()
    except OSError as exc:
        raise AdapterError(f"Tidak bisa membaca {path}: {exc}") from exc


def export_target(
    root: Path | str,
    session: Session,
    adapter: Adapter,
) -> ExportResult:
    """Write the handoff to one agent-native file and report what happened."""
    base = Path(root)
    path = base / adapter.path

    if adapter.fully_generated:
        rendered = render_handoff(session)
        existing = _read_existing(path)
        if existing == rendered:
            return ExportResult(adapter.name, path, "unchanged")
        try:
            atomic_write_text(path, rendered)
        except OSError as exc:
            raise AdapterError(f"Tidak bisa menulis {path}: {exc}") from exc
        return ExportResult(adapter.name, path, "updated" if existing is not None else "created")

    existing = _read_existing(path)
    created = existing is None
    if created:
        text = adapter.frontmatter if adapter.frontmatter else ""
    else:
        text = existing or ""

    merged = merge_block(text, render_block(session), adapter)
    if not created and merged == text:
        return ExportResult(adapter.name, path, "unchanged")

    try:
        atomic_write_text(path, merged)
    except OSError as exc:
        raise AdapterError(f"Tidak bisa menulis {path}: {exc}") from exc
    return ExportResult(adapter.name, path, "created" if created else "updated")


def export(
    root: Path | str,
    session: Session,
    targets: Iterable[Adapter],
) -> list[ExportResult]:
    """Export *session* to every adapter in *targets*."""
    return [export_target(root, session, adapter) for adapter in targets]
