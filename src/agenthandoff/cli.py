"""Command line interface: ``handoff <command>``.

Uses only ``argparse`` from the standard library (decision T6). Every command
returns a process exit code instead of raising, and every failure message says
what went wrong and how to fix it (PRD §10).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .adapters import (
    TARGET_NAMES,
    AdapterError,
    resolve_targets,
)
from .adapters import (
    export as export_targets,
)
from .core import (
    SESSION_DIR,
    Session,
    SessionError,
    handoff_path,
    load_session,
    project_root,
    render_handoff,
)
from .core import (
    capture as capture_session,
)
from .importer import import_file, scan_todos

PROG = "handoff"
OK = "✔"
WARN = "!"
FAIL = "✘"
ARROW = "→"

EXIT_OK = 0
EXIT_USER_ERROR = 1

#: Files agents read at startup — used by ``init`` to show what will be created.
AGENT_FILE_HINTS = {
    "claude": "CLAUDE.md",
    "codex": "AGENTS.md",
    "gemini": "GEMINI.md",
    "cursor": ".cursor/rules/agent-handoff.mdc",
    "copilot": ".github/copilot-instructions.md",
    "windsurf": ".windsurf/rules/agent-handoff.md",
}

_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def _paint(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOR else text


def ok(text: str) -> str:
    return _paint(OK, "32") + " " + text


def warn(text: str) -> str:
    return _paint(WARN, "33") + " " + text


def fail(text: str) -> str:
    return _paint(FAIL, "31") + " " + text


def echo(message: str = "", *, err: bool = False) -> None:
    """Print *message*, degrading gracefully on legacy consoles/encodings."""
    stream = sys.stderr if err else sys.stdout
    try:
        print(message, file=stream)
    except UnicodeEncodeError:  # pragma: no cover - Windows cp1252 consoles
        encoding = getattr(stream, "encoding", None) or "ascii"
        print(message.encode(encoding, "replace").decode(encoding), file=stream)
    except BrokenPipeError:  # pragma: no cover - piped into `head`
        sys.exit(EXIT_OK)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _plural(count: int, word: str, suffix: str = "s") -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}{suffix}"


def _fmt_counts(session: Session) -> str:
    counts = session.counts()
    return (
        f"{counts['done']} done · {_plural(counts['decisions'], 'decision')} · "
        f"{_plural(counts['todos'], 'todo')}"
    )


def _resolve_root(args: argparse.Namespace) -> Path:
    return project_root(getattr(args, "path", None))


def _require_session(root: Path) -> Session:
    session = load_session(root)
    if session is None:
        raise SessionError(
            "No handoff found for this project.\n"
            f"  Start with: {PROG} capture --goal \"what you are working on\" --from claude"
        )
    return session


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def cmd_capture(args: argparse.Namespace) -> int:
    root = _resolve_root(args)
    session = capture_session(
        root,
        goal=args.goal,
        source_agent=args.source_agent,
        decisions=args.decision,
        todos=args.todo,
        done=args.done,
        notes=args.notes,
        scan_todos=args.scan_todos,
    )

    if not args.quiet:
        echo(ok(f"Handoff updated in {root}"))
        echo(f"  {SESSION_DIR}/session.json  {ARROW} {_fmt_counts(session)}")
        echo(f"  {SESSION_DIR}/HANDOFF.md    {ARROW} regenerated")
        git = session.git or {}
        if git.get("is_repo"):
            branch = git.get("branch") or "(no commits yet)"
            changed = git.get("changed_count") or 0
            echo(f"  git: {branch} · {changed} changed file(s)")
        else:
            echo(warn("Not a git repository - git snapshot skipped."))
        if not session.goal and not session.todos:
            echo(
                warn(
                    "The session is still empty. Add context with "
                    "--goal/--todo/--decision, or run " + f"{PROG} import-log <file>."
                )
            )
        echo(f"  Next: {PROG} export --to codex   (or --to all)")
    return EXIT_OK


def cmd_export(args: argparse.Namespace) -> int:
    root = _resolve_root(args)
    adapters = resolve_targets(args.to)
    session = _require_session(root)
    results = export_targets(root, session, adapters)

    if not args.quiet:
        echo(ok(f"Export finished ({len(results)} target(s))"))
        for result in results:
            try:
                shown = result.path.relative_to(root).as_posix()
            except ValueError:  # pragma: no cover - defensive
                shown = result.path.as_posix()
            echo(f"  {shown:<45} {result.status}")
        echo(f"  Source of truth: {SESSION_DIR}/session.json")
        echo("  Open the target agent in the same project; it reads these files"
             " on startup.")
    return EXIT_OK


def cmd_show(args: argparse.Namespace) -> int:
    root = _resolve_root(args)
    session = load_session(root)
    if session is None:
        echo(
            warn("No handoff found for this project.") + "\n"
            f"  Create one: {PROG} capture --goal \"...\" --from claude\n"
            f"  Or import old notes: {PROG} import-log notes.txt"
        )
        return EXIT_OK

    if args.json:
        echo(json.dumps(session.to_dict(), indent=2, ensure_ascii=False))
        return EXIT_OK

    path = handoff_path(root)
    if path.exists():
        echo(path.read_text(encoding="utf-8").rstrip())
    else:
        echo(render_handoff(session).rstrip())
    return EXIT_OK


def cmd_status(args: argparse.Namespace) -> int:
    """Five-line summary: goal, progress, remaining todos, last update."""
    root = _resolve_root(args)
    session = load_session(root)
    if session is None:
        echo(
            warn("No handoff found for this project.") + "\n"
            f"  Start: {PROG} capture --goal \"...\" --from claude"
        )
        return EXIT_OK

    counts = session.counts()
    goal = session.goal or "(not set)"
    progress = (
        f"{counts['done']} done · {_plural(counts['decisions'], 'decision')}"
    )
    todos = session.todos
    if todos:
        next_todo = todos[0]
        remaining = f"{_plural(len(todos), 'todo')} - next: {next_todo}"
    else:
        remaining = "no next steps recorded"
    echo(ok(f"goal         : {goal}"))
    echo(f"progress     : {progress}")
    echo(f"next steps   : {remaining}")
    echo(f"last agent   : {session.source_agent or '—'}")
    echo(f"last updated : {session.updated_at or '—'}")
    if not args.quiet:
        echo(f"details      : {PROG} show")
    return EXIT_OK


def cmd_import_log(args: argparse.Namespace) -> int:
    root = _resolve_root(args)
    source = Path(args.file).expanduser()
    try:
        parsed = import_file(source)
    except FileNotFoundError:
        raise SessionError(
            f"File not found: {source}\n"
            "  Check the path and try again (e.g. handoff import-log notes.txt)."
        ) from None
    except IsADirectoryError:
        raise SessionError(
            f"'{source}' is a folder, not a file.\n"
            "  Point it at a log/chat file (e.g. notes.txt)."
        ) from None
    except OSError as exc:
        raise SessionError(f"Could not read {source}: {exc}") from None

    if parsed.total == 0:
        raise SessionError(
            f"No recognised lines in {source}.\n"
            "  Supported format (start the line with a label):\n"
            "    Decision: Use JWT for auth\n"
            "    TODO: Add refresh token\n"
            "    Done: Login endpoint finished\n"
            "  Indonesian labels work too: Keputusan:, Selanjutnya:, Selesai:"
        )

    session = capture_session(
        root,
        decisions=parsed.decisions,
        todos=parsed.todos,
        done=parsed.done,
        notes="\n".join(parsed.notes),
    )
    if not args.quiet:
        echo(ok(f"Imported from {source}"))
        summary = (
            f"  +{_plural(len(parsed.decisions), 'decision')} · "
            f"+{_plural(len(parsed.todos), 'todo')} · "
            f"+{_plural(len(parsed.done), 'done', suffix='')}"
        )
        if parsed.notes:
            summary += f" · +{_plural(len(parsed.notes), 'note')}"
        echo(summary)
        echo(f"  Session now: {_fmt_counts(session)}")
        echo(f"  Review: {PROG} show    ·    Share: {PROG} export --to all")
    return EXIT_OK


def cmd_init(args: argparse.Namespace) -> int:
    root = _resolve_root(args)
    if root.exists() and not root.is_dir():
        raise SessionError(f"'{root}' is not a folder.")
    root.mkdir(parents=True, exist_ok=True)
    directory = root / SESSION_DIR
    directory.mkdir(parents=True, exist_ok=True)

    created: list[str] = []
    for name in ("session.json", "HANDOFF.md"):
        path = directory / name
        if not path.exists():
            created.append(name)

    gitignore_added = False
    if args.gitignore:
        gitignore = root / ".gitignore"
        entry = f"{SESSION_DIR}/"
        existing = ""
        if gitignore.exists():
            existing = gitignore.read_text(encoding="utf-8", errors="replace")
        if entry not in existing.splitlines():
            prefix = "" if (not existing or existing.endswith("\n")) else "\n"
            extra = f"{prefix}# AgentHandoff local state (opt-out of git)\n{entry}\n"
            with open(gitignore, "a", encoding="utf-8", newline="") as handle:
                handle.write(extra)
            gitignore_added = True

    if not args.quiet:
        echo(ok(f"Ready in {root}"))
        detail = f" ({', '.join(created)})" if created else " (already exists)"
        echo(f"  folder: {SESSION_DIR}/" + detail)
        if args.gitignore:
            echo(
                f"  .gitignore: {SESSION_DIR}/ "
                + ("added" if gitignore_added else "already present")
            )
        existing_agents = [
            name for name, path in AGENT_FILE_HINTS.items() if (root / path).exists()
        ]
        if existing_agents:
            echo(f"  detected agents: {', '.join(existing_agents)}")
        echo("")
        echo("Next steps:")
        echo(f"  1. {PROG} capture --goal \"what this project is building\" --from claude")
        echo(f"  2. {PROG} export --to all")
        echo("  3. Open another agent in this folder; it reads its own context file")
        echo("")
        echo("Note: by default every generated file is commit-friendly (teams share context).")
        echo(f"      Run '{PROG} init --gitignore' to keep the session local instead.")
    return EXIT_OK


def cmd_scan_todos(args: argparse.Namespace) -> int:
    root = _resolve_root(args)
    todos = scan_todos(root, limit=args.limit)
    if not todos:
        echo(warn("No TODO/FIXME comments found in the source code."))
        return EXIT_OK
    echo(f"{len(todos)} TODO/FIXME comment(s) found:")
    for item in todos:
        echo(f"  - {item}")
    if not args.quiet:
        echo(f"  Add them to the session: {PROG} capture --scan-todos")
    return EXIT_OK


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description=(
            "AgentHandoff — never lose context when switching AI coding agents. "
            "Capture a session once, export it to every agent's native file."
        ),
        epilog=(
            "Examples:\n"
            f"  {PROG} capture --goal \"Add login\" --from claude --todo \"Add refresh token\"\n"
            f"  {PROG} export --to codex\n"
            f"  {PROG} export --to all\n"
            f"  {PROG} show\n"
            f"  {PROG} import-log notes.txt\n"
            f"  {PROG} status\n"
            f"  {PROG} init\n"
            "\nDocs: https://github.com/FaaWeell/AgentHandoff"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version=f"AgentHandoff {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    def add_path(sub: argparse.ArgumentParser) -> None:
        sub.add_argument(
            "-p",
            "--path",
            metavar="DIR",
            default=".",
            help="project root to operate on (default: current directory)",
        )
        sub.add_argument(
            "-q", "--quiet", action="store_true", help="only print the essentials"
        )

    # capture ------------------------------------------------------------- #
    p_capture = subparsers.add_parser(
        "capture",
        help="capture or update the session (goal, decisions, todo, done, git)",
        description=(
            "Capture the current state of the project. Repeated captures MERGE into "
            "the existing session; nothing recorded earlier is lost."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_capture.add_argument("--goal", "-g", help="what the project/session is trying to achieve")
    p_capture.add_argument(
        "--from",
        "-f",
        dest="source_agent",
        metavar="AGENT",
        help="agent you are leaving (claude, codex, gemini, cursor, copilot, windsurf, …)",
    )
    p_capture.add_argument(
        "--decision",
        "-d",
        action="append",
        default=[],
        metavar="TEXT",
        help="technical decision; repeatable. Use \"text :: reason\" to record why",
    )
    p_capture.add_argument(
        "--todo", "-t", action="append", default=[], metavar="TEXT", help="next step; repeatable"
    )
    p_capture.add_argument(
        "--done",
        "-D",
        action="append",
        default=[],
        metavar="TEXT",
        help="completed work; repeatable. Also removes the matching todo",
    )
    p_capture.add_argument("--notes", "-n", metavar="TEXT", help="free-form notes (appended)")
    p_capture.add_argument(
        "--scan-todos",
        action="store_true",
        help="also collect TODO/FIXME comments from source code",
    )
    add_path(p_capture)
    p_capture.set_defaults(func=cmd_capture)

    # export -------------------------------------------------------------- #
    p_export = subparsers.add_parser(
        "export",
        help="write the session into agent-native context files",
        description=(
            "Write the handoff block into each target file. The block is delimited by "
            "'<!-- agent-handoff:begin/end -->' markers: re-exporting replaces it, so "
            "content you wrote outside the markers is never touched."
        ),
        epilog=(
            "Targets:\n  " + "\n  ".join(TARGET_NAMES) + "\n\n"
            f"Example: {PROG} export --to codex   ·   {PROG} export --to all"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_export.add_argument(
        "--to",
        "-T",
        action="append",
        required=True,
        metavar="AGENT",
        help="target agent (repeatable, comma separated, or 'all'). "
        f"Choices: {', '.join(TARGET_NAMES)}, all",
    )
    add_path(p_export)
    p_export.set_defaults(func=cmd_export)

    # show ---------------------------------------------------------------- #
    p_show = subparsers.add_parser(
        "show",
        help="print the current handoff",
        description="Print .agent-handoff/HANDOFF.md (or the raw JSON with --json).",
    )
    p_show.add_argument("--json", action="store_true", help="print session.json instead")
    add_path(p_show)
    p_show.set_defaults(func=cmd_show)

    # status -------------------------------------------------------------- #
    p_status = subparsers.add_parser(
        "status",
        help="five-line summary of the session",
        description="Quick summary: goal, progress, remaining todos, last agent, last update.",
    )
    add_path(p_status)
    p_status.set_defaults(func=cmd_status)

    # import-log ---------------------------------------------------------- #
    p_import = subparsers.add_parser(
        "import-log",
        help="extract decisions/todos/done from a log or chat file",
        description=(
            "Parse lines starting with Decision:/TODO:/Done: (English) or "
            "Keputusan:/Selanjutnya:/Selesai:/Catatan: (Bahasa Indonesia) and merge "
            "them into the session."
        ),
    )
    p_import.add_argument("file", metavar="FILE", help="log/chat file to import (UTF-8)")
    add_path(p_import)
    p_import.set_defaults(func=cmd_import_log)

    # scan-todos ---------------------------------------------------------- #
    p_scan = subparsers.add_parser(
        "scan-todos",
        help="list TODO/FIXME comments found in source code",
        description="Preview what 'capture --scan-todos' would collect.",
    )
    p_scan.add_argument(
        "--limit", type=int, default=50, metavar="N", help="max items to list (default: 50)"
    )
    add_path(p_scan)
    p_scan.set_defaults(func=cmd_scan_todos)

    # init ---------------------------------------------------------------- #
    p_init = subparsers.add_parser(
        "init",
        help="create .agent-handoff/ and show the next steps",
        description=(
            "Prepare the project folder. Use --gitignore to keep the session local "
            "instead of committing it (default: commit-friendly)."
        ),
    )
    p_init.add_argument(
        "--gitignore",
        action="store_true",
        help=f"add '{SESSION_DIR}/' to .gitignore (opt out of sharing via git)",
    )
    add_path(p_init)
    p_init.set_defaults(func=cmd_init)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``handoff`` console script."""
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if not getattr(args, "command", None):
        parser.print_help()
        return EXIT_OK

    try:
        return int(args.func(args))
    except (SessionError, AdapterError) as exc:
        echo(fail("Failed."), err=True)
        for line in str(exc).splitlines():
            echo(f"  {line}" if not line.startswith("  ") else line, err=True)
        return EXIT_USER_ERROR
    except KeyboardInterrupt:  # pragma: no cover
        echo("", err=True)
        echo(fail("Cancelled."), err=True)
        return 130
    except BrokenPipeError:  # pragma: no cover
        return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
