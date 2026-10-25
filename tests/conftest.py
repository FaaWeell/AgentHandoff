"""Shared pytest fixtures for the AgentHandoff test suite."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

# Allow running the tests without installing the package (e.g. `pytest` from a
# bare checkout): prefer the source tree, fall back to the installed package.
SRC = Path(__file__).resolve().parents[1] / "src"
if SRC.is_dir() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agenthandoff.core import capture  # noqa: E402


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        },
    )


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """An empty, non-git project directory."""
    root = tmp_path / "demo project"
    root.mkdir()
    return root


@pytest.fixture()
def git_project(tmp_path: Path) -> Path:
    """A git repository with one commit and one modified file."""
    root = tmp_path / "git project"
    root.mkdir()
    _git(root, "init", "-q")
    (root / "app.py").write_text("print('hi')\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "feat: initial app")
    (root / "app.py").write_text("print('hi there')\n", encoding="utf-8")
    return root


@pytest.fixture()
def session(project: Path):
    """A populated session in the *project* directory."""
    return capture(
        project,
        goal="Add login",
        source_agent="claude",
        decisions=["Pakai JWT :: stateless, cocok untuk API"],
        todos=["Add refresh token", "Write tests for /login"],
        done=["Endpoint /login selesai"],
        notes="Catatan bebas 🚀",
    )
