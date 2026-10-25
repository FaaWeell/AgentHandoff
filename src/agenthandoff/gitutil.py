"""Git snapshot helpers.

Git is called through ``subprocess`` (decision T4 in ``plan.md``): no
dependency, and the behaviour is exactly what the user already knows from their
own terminal. Every call is defensive — a missing ``git`` binary, a folder that
is not a repository or a hanging command must never crash a capture.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

#: How many recent commits are recorded (PRD §11).
RECENT_COMMITS = 10
#: Upper bound for the changed-files list so session.json stays small.
MAX_CHANGED_FILES = 200
#: Seconds before a git call is considered hung.
GIT_TIMEOUT = 10


def _run_git(args: Sequence[str], cwd: Path) -> tuple[bool, str]:
    """Run a git command and return ``(ok, stdout)`` without ever raising."""
    env = dict(os.environ)
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    env.setdefault("GIT_PAGER", "cat")
    env.setdefault("GIT_OPTIONAL_LOCKS", "0")
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            timeout=GIT_TIMEOUT,
            env=env,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False, ""
    if completed.returncode != 0:
        return False, ""
    return True, completed.stdout.decode("utf-8", errors="replace")


def is_git_repo(root: Path) -> bool:
    """Return ``True`` when *root* is inside a git work tree."""
    ok, out = _run_git(["rev-parse", "--is-inside-work-tree"], root)
    return ok and out.strip() == "true"


def _first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def _branch(root: Path) -> str:
    ok, out = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], root)
    if ok:
        branch = _first_line(out)
        if branch and branch != "HEAD":
            return branch
    # Detached HEAD (or a repository without commits yet).
    ok, out = _run_git(["rev-parse", "--short", "HEAD"], root)
    if ok and _first_line(out):
        return f"(detached: {_first_line(out)})"
    return ""


def _last_commit(root: Path) -> str:
    ok, out = _run_git(["log", "-1", "--pretty=format:%h %s"], root)
    return _first_line(out) if ok else ""


def _recent_commits(root: Path) -> list[str]:
    ok, out = _run_git(
        ["log", f"-{RECENT_COMMITS}", "--pretty=format:%h %s"], root
    )
    if not ok:
        return []
    return [line.rstrip() for line in out.splitlines() if line.strip()]


def _changed_files(root: Path) -> list[str]:
    ok, out = _run_git(["-c", "core.quotepath=false", "status", "--porcelain"], root)
    if not ok:
        return []
    files: list[str] = []
    for line in out.splitlines():
        if len(line) < 4:
            continue
        entry = line[3:].strip()
        if " -> " in entry:  # rename: keep the destination path
            entry = entry.split(" -> ", 1)[1]
        entry = entry.strip().strip('"')
        if entry:
            files.append(entry)
    return files


def _diff_stat(root: Path) -> str:
    ok, out = _run_git(["--no-pager", "diff", "HEAD", "--stat"], root)
    if not ok:
        ok, out = _run_git(["--no-pager", "diff", "--stat"], root)
    return out.rstrip() if ok else ""


def git_snapshot(root: Path | str) -> dict[str, Any]:
    """Return a JSON-serialisable snapshot of the repository at *root*.

    In a non-git folder (or when git is not installed) the result is
    ``{"is_repo": False}`` and capture keeps working (FR-03).
    """
    path = Path(root)
    try:
        if not path.is_dir() or not is_git_repo(path):
            return {"is_repo": False}
    except OSError:  # pragma: no cover - defensive
        return {"is_repo": False}

    changed = _changed_files(path)
    return {
        "is_repo": True,
        "branch": _branch(path),
        "last_commit": _last_commit(path),
        "changed_files": changed[:MAX_CHANGED_FILES],
        "changed_count": len(changed),
        "recent_commits": _recent_commits(path),
        "diff_stat": _diff_stat(path),
    }
