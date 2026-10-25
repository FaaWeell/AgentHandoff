"""Tests for git snapshots: real repo, non-git folder, missing git binary."""

from __future__ import annotations

import subprocess
from pathlib import Path

from agenthandoff import gitutil
from agenthandoff.gitutil import (
    MAX_CHANGED_FILES,
    RECENT_COMMITS,
    git_snapshot,
    is_git_repo,
)


class TestNonRepo:
    def test_plain_folder(self, project: Path) -> None:
        assert is_git_repo(project) is False
        assert git_snapshot(project) == {"is_repo": False}

    def test_missing_folder(self, tmp_path: Path) -> None:
        assert git_snapshot(tmp_path / "does-not-exist") == {"is_repo": False}

    def test_file_path(self, tmp_path: Path) -> None:
        path = tmp_path / "file.txt"
        path.write_text("x", encoding="utf-8")
        assert git_snapshot(path) == {"is_repo": False}

    def test_git_binary_missing(self, project: Path, monkeypatch) -> None:
        def boom(*args, **kwargs):
            raise FileNotFoundError("git not found")

        monkeypatch.setattr(subprocess, "run", boom)
        assert git_snapshot(project) == {"is_repo": False}

    def test_git_timeout(self, project: Path, monkeypatch) -> None:
        def timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="git", timeout=1)

        monkeypatch.setattr(subprocess, "run", timeout)
        assert git_snapshot(project) == {"is_repo": False}

    def test_empty_repo_without_commits(self, tmp_path: Path) -> None:
        root = tmp_path / "empty-repo"
        root.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
        snapshot = git_snapshot(root)
        assert snapshot["is_repo"] is True
        assert snapshot["last_commit"] == ""
        assert snapshot["recent_commits"] == []
        assert snapshot["changed_files"] == []


class TestRealRepo:
    def test_snapshot_fields(self, git_project: Path) -> None:
        snapshot = git_snapshot(git_project)
        assert snapshot["is_repo"] is True
        assert isinstance(snapshot["branch"], str) and snapshot["branch"]
        assert snapshot["last_commit"].endswith("feat: initial app")
        assert "app.py" in snapshot["changed_files"]
        assert snapshot["changed_count"] == len(snapshot["changed_files"])
        assert snapshot["recent_commits"][0].endswith("feat: initial app")
        assert "app.py" in snapshot["diff_stat"]

    def test_recent_commits_are_capped(self, git_project: Path) -> None:
        for index in range(RECENT_COMMITS + 3):
            (git_project / "f.txt").write_text(str(index), encoding="utf-8")
            subprocess.run(
                ["git", "add", "-A"], cwd=git_project, check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-q", "-m", f"commit {index}"],
                cwd=git_project,
                check=True,
                capture_output=True,
                env={
                    "GIT_AUTHOR_NAME": "T",
                    "GIT_AUTHOR_EMAIL": "t@example.com",
                    "GIT_COMMITTER_NAME": "T",
                    "GIT_COMMITTER_EMAIL": "t@example.com",
                    "PATH": "/usr/bin:/bin:/usr/local/bin",
                },
            )
        snapshot = git_snapshot(git_project)
        assert len(snapshot["recent_commits"]) == RECENT_COMMITS

    def test_changed_files_are_capped(self, git_project: Path) -> None:
        for index in range(MAX_CHANGED_FILES + 5):
            (git_project / f"gen_{index}.py").write_text("x = 1\n", encoding="utf-8")
        snapshot = git_snapshot(git_project)
        assert len(snapshot["changed_files"]) == MAX_CHANGED_FILES
        assert snapshot["changed_count"] > MAX_CHANGED_FILES

    def test_renamed_file_uses_destination(self, git_project: Path) -> None:
        subprocess.run(
            ["git", "mv", "app.py", "renamed.py"],
            cwd=git_project,
            check=True,
            capture_output=True,
        )
        snapshot = git_snapshot(git_project)
        assert "renamed.py" in snapshot["changed_files"]

    def test_clean_tree(self, git_project: Path) -> None:
        subprocess.run(
            ["git", "checkout", "--", "."],
            cwd=git_project,
            check=True,
            capture_output=True,
        )
        snapshot = git_snapshot(git_project)
        assert snapshot["changed_count"] == 0
        assert snapshot["changed_files"] == []

    def test_subdirectory_of_repo_is_detected(self, git_project: Path) -> None:
        sub = git_project / "src"
        sub.mkdir()
        assert is_git_repo(sub) is True

    def test_detached_head_does_not_crash(self, git_project: Path) -> None:
        subprocess.run(
            ["git", "checkout", "-q", "--detach", "HEAD"],
            cwd=git_project,
            check=True,
            capture_output=True,
        )
        snapshot = git_snapshot(git_project)
        assert snapshot["is_repo"] is True
        assert snapshot["branch"].startswith("(detached")


def test_snapshot_is_json_serialisable(git_project: Path) -> None:
    import json

    snapshot = git_snapshot(git_project)
    assert json.loads(json.dumps(snapshot)) == snapshot


def test_module_constants_are_sane() -> None:
    assert RECENT_COMMITS == 10
    assert gitutil.GIT_TIMEOUT > 0
