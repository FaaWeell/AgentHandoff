"""Tests for the session model: capture, merge semantics, storage, rendering."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from agenthandoff import __version__
from agenthandoff.core import (
    HANDOFF_FILE,
    SESSION_DIR,
    SESSION_FILE,
    Session,
    SessionError,
    atomic_write_text,
    capture,
    dedupe_decisions,
    handoff_path,
    load_session,
    normalize,
    now_iso,
    project_root,
    render_handoff,
    save_session,
    session_path,
    split_decision,
    write_handoff,
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
class TestNormalize:
    @pytest.mark.parametrize(
        "left,right",
        [
            ("Add refresh token", "add refresh token"),
            ("  Add   refresh   token  ", "Add refresh token"),
            ("Write tests for /login.", "Write tests for /login"),
            ("Endpoint /login selesai!", "endpoint /login selesai"),
            ("Tulis dokumentasi", "TULIS DOKUMENTASI"),
        ],
    )
    def test_equal_items_compare_equal(self, left: str, right: str) -> None:
        assert normalize(left) == normalize(right)

    def test_different_items_differ(self) -> None:
        assert normalize("Add login") != normalize("Add logout")

    def test_keeps_unicode(self) -> None:
        assert normalize("Tulis dokumentasi ✨") == "tulis dokumentasi ✨"


class TestSplitDecision:
    def test_with_reason(self) -> None:
        assert split_decision("Pakai JWT :: stateless") == ("Pakai JWT", "stateless")

    def test_with_dash_reason(self) -> None:
        assert split_decision("Pakai JWT -- stateless") == ("Pakai JWT", "stateless")

    def test_without_reason(self) -> None:
        assert split_decision("Pakai JWT") == ("Pakai JWT", "")

    def test_blank_reason_is_ignored(self) -> None:
        assert split_decision("Pakai JWT ::   ") == ("Pakai JWT", "")


def test_dedupe_decisions_keeps_first_text_and_richest_reason() -> None:
    merged = dedupe_decisions(
        [
            {"text": "Pakai JWT", "reason": ""},
            {"text": "pakai jwt", "reason": "stateless"},
            {"text": "Pakai JWT", "reason": "other"},
        ]
    )
    assert merged == [{"text": "Pakai JWT", "reason": "stateless"}]


# --------------------------------------------------------------------------- #
# Capture
# --------------------------------------------------------------------------- #
class TestCapture:
    def test_creates_session_and_handoff(self, project: Path) -> None:
        session = capture(
            project,
            goal="Add login",
            source_agent="claude",
            decisions=["Pakai JWT :: stateless"],
            todos=["Add refresh token"],
            done=["Endpoint /login selesai"],
            notes="catatan",
        )

        assert session_path(project).is_file()
        assert handoff_path(project).is_file()
        assert session.project == project.name
        assert session.goal == "Add login"
        assert session.source_agent == "claude"
        assert session.todos == ["Add refresh token"]
        assert session.done == ["Endpoint /login selesai"]

        data = json.loads(session_path(project).read_text(encoding="utf-8"))
        assert data["schema_version"] == 1
        assert data["decisions"] == [{"text": "Pakai JWT", "reason": "stateless"}]
        assert data["created_at"]
        assert data["updated_at"]

    def test_bare_capture_is_valid(self, project: Path) -> None:
        session = capture(project)
        assert session.is_empty
        assert session_path(project).is_file()
        # A bare capture must still produce a readable HANDOFF.md.
        text = handoff_path(project).read_text(encoding="utf-8")
        assert "_Nothing recorded yet._" in text
        assert __version__ in text

    def test_done_removes_matching_todo(self, project: Path) -> None:
        capture(project, todos=["Add refresh token", "Write tests for /login"])
        session = capture(project, done=["write tests for /login."])
        assert session.todos == ["Add refresh token"]
        assert session.done == ["write tests for /login."]

    def test_merge_keeps_previous_data(self, project: Path) -> None:
        capture(
            project,
            goal="Add login",
            source_agent="claude",
            decisions=["Pakai JWT :: stateless"],
            todos=["Add refresh token"],
            done=["Endpoint /login selesai"],
            notes="first note",
        )
        session = capture(
            project,
            source_agent="codex",
            decisions=["Pakai bcrypt :: standar industri"],
            todos=["Add rate limiting"],
            notes="second note",
        )

        assert session.project == project.name
        assert session.goal == "Add login"  # not erased by a flag-less capture
        assert session.source_agent == "codex"
        assert [d["text"] for d in session.decisions] == ["Pakai JWT", "Pakai bcrypt"]
        assert session.todos == ["Add refresh token", "Add rate limiting"]
        assert session.done == ["Endpoint /login selesai"]
        assert "first note" in session.notes and "second note" in session.notes

    def test_goal_can_be_updated(self, project: Path) -> None:
        capture(project, goal="Add login")
        session = capture(project, goal="Add login + SSO")
        assert session.goal == "Add login + SSO"

    def test_no_duplicate_todos(self, project: Path) -> None:
        capture(project, todos=["Add refresh token", "add refresh token "])
        session = capture(project, todos=["Add refresh token"])
        assert session.todos == ["Add refresh token"]

    def test_todo_and_done_never_overlap(self, project: Path) -> None:
        capture(project, todos=["A", "B"], done=["A"])
        session = capture(project, todos=["A"])
        assert session.todos == ["B"]
        assert session.done == ["A"]

    def test_notes_are_appended_not_overwritten(self, project: Path) -> None:
        capture(project, notes="alpha")
        session = capture(project, notes="beta")
        assert session.notes.split() == ["alpha", "beta"]

    def test_identical_note_is_not_duplicated(self, project: Path) -> None:
        capture(project, notes="alpha")
        session = capture(project, notes="alpha")
        assert session.notes == "alpha"

    def test_created_at_is_stable(self, project: Path) -> None:
        first = capture(project, goal="A")
        second = capture(project, goal="B")
        assert first.created_at == second.created_at
        assert second.updated_at >= first.updated_at

    def test_unicode_and_emoji_round_trip(self, project: Path) -> None:
        capture(
            project,
            goal="Selesaikan fitur login 🔐",
            todos=["Tulis dokumentasi Bahasa Indonesia"],
            decisions=["Pakai JWT :: stateless, cocok untuk API"],
            notes="Rapat besok jam 9 — jangan lupa",
        )
        session = load_session(project)
        assert session is not None
        assert session.goal == "Selesaikan fitur login 🔐"
        assert session.todos == ["Tulis dokumentasi Bahasa Indonesia"]
        assert "🚀" not in session.goal
        raw = session_path(project).read_text(encoding="utf-8")
        assert "🔐" in raw  # stored as real UTF-8, not \uXXXX escapes

    def test_works_outside_git(self, project: Path) -> None:
        session = capture(project, goal="No git here")
        assert session.git.get("is_repo") is False

    def test_git_snapshot_is_recorded(self, git_project: Path) -> None:
        session = capture(git_project, goal="With git")
        assert session.git["is_repo"] is True
        assert session.git["branch"]
        assert "feat: initial app" in session.git["last_commit"]
        assert "app.py" in session.git["changed_files"]
        assert session.git["changed_count"] >= 1
        assert session.git["recent_commits"]

    def test_second_capture_refreshes_git_snapshot(self, git_project: Path) -> None:
        capture(git_project)
        (git_project / "new_file.py").write_text("x = 1\n", encoding="utf-8")
        session = capture(git_project)
        assert "new_file.py" in session.git["changed_files"]

    def test_scan_todos_option(self, project: Path) -> None:
        (project / "app.py").write_text(
            "# TODO: tambahkan validasi input\nx = 1\n# FIXME: handle error\n",
            encoding="utf-8",
        )
        session = capture(project, scan_todos=True)
        assert len(session.todos) == 2
        assert any("tambahkan validasi input" in todo for todo in session.todos)
        assert any(todo.startswith("app.py:") for todo in session.todos)

    def test_path_with_spaces_and_unicode(self, tmp_path: Path) -> None:
        root = tmp_path / "project dengan spasi & ünïcode"
        root.mkdir()
        session = capture(root, goal="Halo")
        assert session.goal == "Halo"
        assert session_path(root).is_file()


# --------------------------------------------------------------------------- #
# Storage
# --------------------------------------------------------------------------- #
class TestStorage:
    def test_save_load_round_trip(self, project: Path) -> None:
        original = Session(
            project="p",
            goal="g",
            source_agent="claude",
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-02T00:00:00+00:00",
            decisions=[{"text": "d", "reason": "r"}],
            todos=["t"],
            done=["x"],
            notes="n",
            git={"is_repo": False},
        )
        save_session(project, original)
        loaded = load_session(project)
        assert loaded is not None
        assert loaded.to_dict() == original.to_dict()

    def test_load_missing_returns_none(self, project: Path) -> None:
        assert load_session(project) is None

    def test_load_missing_required_raises(self, project: Path) -> None:
        with pytest.raises(SessionError) as excinfo:
            load_session(project, required=True)
        assert "handoff capture" in str(excinfo.value)

    def test_corrupt_json_gives_actionable_error(self, project: Path) -> None:
        path = session_path(project)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"goal": "oops",}', encoding="utf-8")
        with pytest.raises(SessionError) as excinfo:
            load_session(project)
        message = str(excinfo.value)
        assert SESSION_FILE in message
        assert "is not valid JSON" in message
        assert "handoff capture" in message

    def test_empty_session_file_gives_friendly_error(self, project: Path) -> None:
        path = session_path(project)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("   \n", encoding="utf-8")
        with pytest.raises(SessionError) as excinfo:
            load_session(project)
        assert "is empty" in str(excinfo.value)

    def test_json_list_is_rejected(self, project: Path) -> None:
        path = session_path(project)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("[1, 2, 3]", encoding="utf-8")
        with pytest.raises(SessionError):
            load_session(project)

    def test_unknown_fields_are_ignored(self, project: Path) -> None:
        path = session_path(project)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"goal": "g", "future_field": {"a": 1}}), encoding="utf-8"
        )
        session = load_session(project)
        assert session is not None and session.goal == "g"

    def test_legacy_string_decisions_are_accepted(self, project: Path) -> None:
        path = session_path(project)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"decisions": ["Pakai JWT :: stateless", "Tanpa ORM"]}),
            encoding="utf-8",
        )
        session = load_session(project)
        assert session is not None
        assert session.decisions == [
            {"text": "Pakai JWT", "reason": "stateless"},
            {"text": "Tanpa ORM", "reason": ""},
        ]

    def test_save_is_atomic_and_leaves_no_temp_files(self, project: Path) -> None:
        save_session(project, Session(project="p", goal="g"))
        save_session(project, Session(project="p", goal="h"))
        directory = project / SESSION_DIR
        assert sorted(p.name for p in directory.iterdir()) == [SESSION_FILE]

    def test_project_root_rejects_file_path(self, tmp_path: Path) -> None:
        file_path = tmp_path / "a.txt"
        file_path.write_text("x", encoding="utf-8")
        with pytest.raises(SessionError) as excinfo:
            project_root(file_path)
        assert "not a project folder" in str(excinfo.value)

    def test_project_root_defaults_to_cwd(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        assert project_root() == tmp_path.resolve()

    def test_atomic_write_replaces_content(self, tmp_path: Path) -> None:
        target = tmp_path / "nested" / "file.md"
        atomic_write_text(target, "one\n")
        atomic_write_text(target, "two\n")
        assert target.read_text(encoding="utf-8") == "two\n"

    @pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
    def test_atomic_write_new_file_is_readable(self, tmp_path: Path) -> None:
        target = tmp_path / "new.md"
        atomic_write_text(target, "hello\n")
        assert stat.S_IMODE(target.stat().st_mode) & 0o444 == 0o444

    @pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
    def test_atomic_write_preserves_permissions(self, tmp_path: Path) -> None:
        target = tmp_path / "file.md"
        target.write_text("one\n", encoding="utf-8")
        target.chmod(0o640)
        atomic_write_text(target, "two\n")
        assert stat.S_IMODE(target.stat().st_mode) == 0o640


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
class TestRender:
    def test_all_sections_present(self, session) -> None:
        text = render_handoff(session)
        for heading in [
            "# 🤝 AgentHandoff",
            "## 🎯 Goal",
            "## 🌿 Git state",
            "## ✅ Done",
            "## 🧭 Decisions (and why)",
            "## ⏭️ Next steps",
            "## 📝 Notes",
        ]:
            assert heading in text

    def test_content_is_rendered(self, session) -> None:
        text = render_handoff(session)
        assert "Add login" in text
        assert "- [x] Endpoint /login selesai" in text
        assert "- [ ] Add refresh token" in text
        assert "**Pakai JWT** — stateless, cocok untuk API" in text
        assert "Catatan bebas 🚀" in text
        assert "Not a git repository" in text

    def test_git_section_in_repo(self, git_project: Path) -> None:
        session = capture(git_project, goal="g")
        text = render_handoff(session)
        assert "**Branch:**" in text
        assert "**Last commit:**" in text
        assert "**Changed files:**" in text
        assert "**Recent commits:**" in text

    def test_empty_session_renders_placeholders(self, project: Path) -> None:
        session = capture(project)
        text = render_handoff(session)
        assert text.count("_Nothing recorded yet._") >= 4

    def test_multiline_notes_are_preserved(self, project: Path) -> None:
        session = capture(project, notes="line one\nline two")
        text = render_handoff(session)
        assert "line one\nline two" in text

    def test_write_handoff_updates_file(self, project: Path) -> None:
        session = capture(project, goal="first")
        path = write_handoff(project, session)
        assert path == project / SESSION_DIR / HANDOFF_FILE
        session.goal = "second"
        write_handoff(project, session)
        assert "second" in path.read_text(encoding="utf-8")

    def test_now_iso_has_timezone(self) -> None:
        stamp = now_iso()
        assert "T" in stamp
        assert stamp[-6] in "+-" or stamp.endswith("Z")
