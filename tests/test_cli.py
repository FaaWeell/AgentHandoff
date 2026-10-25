"""End-to-end CLI tests: every command, plus friendly failure modes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agenthandoff import __version__
from agenthandoff.adapters import BEGIN_MARKER, TARGET_NAMES
from agenthandoff.cli import main
from agenthandoff.core import SESSION_DIR, handoff_path, session_path


def run(*args: str) -> int:
    return main(list(args))


class TestTopLevel:
    def test_no_command_prints_help(self, capsys) -> None:
        assert run() == 0
        out = capsys.readouterr().out
        assert "usage: handoff" in out
        assert "capture" in out
        assert "export" in out

    def test_version(self, capsys) -> None:
        with pytest.raises(SystemExit) as excinfo:
            run("--version")
        assert excinfo.value.code == 0
        assert __version__ in capsys.readouterr().out

    def test_help_lists_every_command(self, capsys) -> None:
        with pytest.raises(SystemExit):
            run("--help")
        out = capsys.readouterr().out
        for command in ("capture", "export", "show", "status", "import-log", "init"):
            assert command in out

    @pytest.mark.parametrize(
        "command", ["capture", "export", "show", "status", "import-log", "init", "scan-todos"]
    )
    def test_every_command_has_help(self, command: str, capsys) -> None:
        with pytest.raises(SystemExit) as excinfo:
            run(command, "--help")
        assert excinfo.value.code == 0
        out = capsys.readouterr().out
        assert "--path" in out
        assert "usage: handoff" in out

    def test_unknown_command_exits_nonzero(self, capsys) -> None:
        with pytest.raises(SystemExit) as excinfo:
            run("nonsense")
        assert excinfo.value.code != 0


class TestCaptureCommand:
    def test_capture_end_to_end(self, project: Path, capsys) -> None:
        code = run(
            "capture",
            "--goal",
            "Add login",
            "--from",
            "claude",
            "--decision",
            "Pakai JWT :: stateless",
            "--todo",
            "Add refresh token",
            "--done",
            "Endpoint /login selesai",
            "--notes",
            "catatan 🚀",
            "--path",
            str(project),
        )
        out = capsys.readouterr().out
        assert code == 0
        assert "Handoff diperbarui" in out
        assert session_path(project).is_file()
        assert handoff_path(project).is_file()
        data = json.loads(session_path(project).read_text(encoding="utf-8"))
        assert data["goal"] == "Add login"
        assert data["source_agent"] == "claude"

    def test_capture_merges_on_second_run(self, project: Path, capsys) -> None:
        run("capture", "--goal", "First", "--todo", "one", "--path", str(project))
        run("capture", "--todo", "two", "--done", "one", "--path", str(project))
        capsys.readouterr()
        data = json.loads(session_path(project).read_text(encoding="utf-8"))
        assert data["goal"] == "First"
        assert data["todos"] == ["two"]
        assert data["done"] == ["one"]

    def test_capture_quiet(self, project: Path, capsys) -> None:
        assert run("capture", "--goal", "g", "--path", str(project), "--quiet") == 0
        assert capsys.readouterr().out == ""

    def test_capture_warns_when_empty(self, project: Path, capsys) -> None:
        run("capture", "--path", str(project))
        assert "masih kosong" in capsys.readouterr().out

    def test_capture_warns_outside_git(self, project: Path, capsys) -> None:
        run("capture", "--goal", "g", "--path", str(project))
        assert "git repository" in capsys.readouterr().out

    def test_capture_in_git_repo_shows_branch(self, git_project: Path, capsys) -> None:
        run("capture", "--goal", "g", "--path", str(git_project))
        assert "git:" in capsys.readouterr().out

    def test_capture_scan_todos(self, project: Path, capsys) -> None:
        (project / "app.py").write_text("# TODO: write tests\n", encoding="utf-8")
        run("capture", "--scan-todos", "--path", str(project), "--quiet")
        capsys.readouterr()
        data = json.loads(session_path(project).read_text(encoding="utf-8"))
        assert data["todos"] == ["app.py:1 — TODO: write tests"]

    def test_capture_creates_missing_project_dir(self, tmp_path: Path, capsys) -> None:
        target = tmp_path / "new project"
        assert run("capture", "--goal", "g", "--path", str(target)) == 0
        assert session_path(target).is_file()
        capsys.readouterr()

    def test_capture_rejects_file_path(self, tmp_path: Path, capsys) -> None:
        file_path = tmp_path / "file.txt"
        file_path.write_text("x", encoding="utf-8")
        assert run("capture", "--goal", "g", "--path", str(file_path)) == 1
        err = capsys.readouterr().err
        assert "Gagal" in err
        assert "bukan folder project" in err

    def test_corrupt_json_is_a_friendly_error(self, project: Path, capsys) -> None:
        path = session_path(project)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not json", encoding="utf-8")
        assert run("capture", "--goal", "g", "--path", str(project)) == 1
        err = capsys.readouterr().err
        assert "bukan JSON yang valid" in err
        assert "Traceback" not in err


class TestExportCommand:
    def test_export_single_target(self, project: Path, capsys) -> None:
        run("capture", "--goal", "Add login", "--path", str(project), "--quiet")
        assert run("export", "--to", "codex", "--path", str(project)) == 0
        out = capsys.readouterr().out
        assert "AGENTS.md" in out
        assert (project / "AGENTS.md").is_file()

    def test_export_all(self, project: Path, capsys) -> None:
        run("capture", "--goal", "Add login", "--path", str(project), "--quiet")
        assert run("export", "--to", "all", "--path", str(project), "--quiet") == 0
        capsys.readouterr()
        for name in TARGET_NAMES:
            from agenthandoff.adapters import TARGETS

            assert (project / TARGETS[name].path).is_file()

    def test_export_multiple_flags(self, project: Path, capsys) -> None:
        run("capture", "--goal", "g", "--path", str(project), "--quiet")
        assert run("export", "--to", "claude", "--to", "gemini", "--path", str(project)) == 0
        capsys.readouterr()
        assert (project / "CLAUDE.md").is_file()
        assert (project / "GEMINI.md").is_file()

    def test_export_unknown_target(self, project: Path, capsys) -> None:
        run("capture", "--goal", "g", "--path", str(project), "--quiet")
        assert run("export", "--to", "zed", "--path", str(project)) == 1
        err = capsys.readouterr().err
        assert "zed" in err
        assert "claude" in err and "markdown" in err

    def test_export_requires_to(self, project: Path) -> None:
        with pytest.raises(SystemExit) as excinfo:
            run("export", "--path", str(project))
        assert excinfo.value.code != 0

    def test_export_without_session_is_friendly(self, project: Path, capsys) -> None:
        assert run("export", "--to", "all", "--path", str(project)) == 1
        err = capsys.readouterr().err
        assert "Belum ada handoff" in err
        assert "handoff capture" in err

    def test_export_is_idempotent_from_cli(self, project: Path, capsys) -> None:
        run("capture", "--goal", "g", "--path", str(project), "--quiet")
        run("export", "--to", "all", "--path", str(project), "--quiet")
        first = (project / "AGENTS.md").read_text(encoding="utf-8")
        run("export", "--to", "all", "--path", str(project), "--quiet")
        second = (project / "AGENTS.md").read_text(encoding="utf-8")
        capsys.readouterr()
        assert first == second
        assert second.count(BEGIN_MARKER) == 1

    def test_export_preserves_existing_user_file(self, project: Path, capsys) -> None:
        (project / "CLAUDE.md").write_text("# Team rules\nalways test\n", encoding="utf-8")
        run("capture", "--goal", "g", "--path", str(project), "--quiet")
        run("export", "--to", "claude", "--path", str(project), "--quiet")
        text = (project / "CLAUDE.md").read_text(encoding="utf-8")
        capsys.readouterr()
        assert "# Team rules" in text
        assert "always test" in text


class TestShowStatus:
    def test_show_without_session_is_friendly(self, project: Path, capsys) -> None:
        assert run("show", "--path", str(project)) == 0
        out = capsys.readouterr().out
        assert "Belum ada handoff" in out
        assert "handoff capture" in out

    def test_show_prints_handoff(self, project: Path, capsys) -> None:
        run(
            "capture",
            "--goal",
            "Add login",
            "--todo",
            "Add token",
            "--path",
            str(project),
            "--quiet",
        )
        capsys.readouterr()
        assert run("show", "--path", str(project)) == 0
        out = capsys.readouterr().out
        assert "# 🤝 AgentHandoff" in out
        assert "Add login" in out
        assert "Add token" in out

    def test_show_json(self, project: Path, capsys) -> None:
        run("capture", "--goal", "Add login", "--path", str(project), "--quiet")
        capsys.readouterr()
        assert run("show", "--json", "--path", str(project)) == 0
        data = json.loads(capsys.readouterr().out)
        assert data["goal"] == "Add login"

    def test_show_regenerates_missing_handoff(self, project: Path, capsys) -> None:
        run("capture", "--goal", "Add login", "--path", str(project), "--quiet")
        handoff_path(project).unlink()
        capsys.readouterr()
        assert run("show", "--path", str(project)) == 0
        assert "# 🤝 AgentHandoff" in capsys.readouterr().out

    def test_status_output_has_five_lines(self, project: Path, capsys) -> None:
        run(
            "capture",
            "--goal",
            "Add login",
            "--todo",
            "Add token",
            "--path",
            str(project),
            "--quiet",
        )
        capsys.readouterr()
        assert run("status", "--path", str(project), "--quiet") == 0
        out = capsys.readouterr().out.strip().splitlines()
        assert len(out) == 5
        assert "Add login" in out[0]
        assert "Add token" in out[2]

    def test_status_without_session(self, project: Path, capsys) -> None:
        assert run("status", "--path", str(project)) == 0
        assert "Belum ada handoff" in capsys.readouterr().out

    def test_status_without_todos(self, project: Path, capsys) -> None:
        run("capture", "--goal", "g", "--path", str(project), "--quiet")
        capsys.readouterr()
        run("status", "--path", str(project), "--quiet")
        assert "tidak ada next step" in capsys.readouterr().out


class TestImportLogCommand:
    def test_import_english(self, project: Path, tmp_path: Path, capsys) -> None:
        log = tmp_path / "log.txt"
        log.write_text("Decision: Use JWT\nTODO: Add token\nDone: Login\n", encoding="utf-8")
        assert run("import-log", str(log), "--path", str(project)) == 0
        out = capsys.readouterr().out
        assert "Import dari" in out
        data = json.loads(session_path(project).read_text(encoding="utf-8"))
        assert data["decisions"][0]["text"] == "Use JWT"
        assert data["todos"] == ["Add token"]
        assert data["done"] == ["Login"]

    def test_import_indonesian(self, project: Path, tmp_path: Path, capsys) -> None:
        log = tmp_path / "catatan.txt"
        log.write_text(
            "Keputusan: Pakai JWT :: stateless\nSelanjutnya: Tulis test\nSelesai: Setup\n",
            encoding="utf-8",
        )
        assert run("import-log", str(log), "--path", str(project)) == 0
        capsys.readouterr()
        data = json.loads(session_path(project).read_text(encoding="utf-8"))
        assert data["decisions"] == [{"text": "Pakai JWT", "reason": "stateless"}]
        assert data["todos"] == ["Tulis test"]

    def test_import_merges_into_existing(self, project: Path, tmp_path: Path, capsys) -> None:
        run("capture", "--goal", "Keep", "--todo", "old", "--path", str(project), "--quiet")
        log = tmp_path / "log.txt"
        log.write_text("TODO: new\n", encoding="utf-8")
        run("import-log", str(log), "--path", str(project), "--quiet")
        capsys.readouterr()
        data = json.loads(session_path(project).read_text(encoding="utf-8"))
        assert data["goal"] == "Keep"
        assert data["todos"] == ["old", "new"]

    def test_import_shows_up_in_show(self, project: Path, tmp_path: Path, capsys) -> None:
        log = tmp_path / "log.txt"
        log.write_text("TODO: visible item\n", encoding="utf-8")
        run("import-log", str(log), "--path", str(project), "--quiet")
        capsys.readouterr()
        run("show", "--path", str(project))
        assert "visible item" in capsys.readouterr().out

    def test_import_missing_file(self, project: Path, tmp_path: Path, capsys) -> None:
        assert run("import-log", str(tmp_path / "nope.txt"), "--path", str(project)) == 1
        err = capsys.readouterr().err
        assert "tidak ditemukan" in err.lower()

    def test_import_directory(self, project: Path, tmp_path: Path, capsys) -> None:
        assert run("import-log", str(tmp_path), "--path", str(project)) == 1
        assert "bukan file" in capsys.readouterr().err

    def test_import_unrecognised_file(self, project: Path, tmp_path: Path, capsys) -> None:
        log = tmp_path / "log.txt"
        log.write_text("just some prose\nnothing to see\n", encoding="utf-8")
        assert run("import-log", str(log), "--path", str(project)) == 1
        err = capsys.readouterr().err
        assert "Tidak ada baris yang dikenali" in err
        assert "Decision:" in err


class TestInitCommand:
    def test_init_creates_folder(self, project: Path, capsys) -> None:
        assert run("init", "--path", str(project)) == 0
        assert (project / SESSION_DIR).is_dir()
        out = capsys.readouterr().out
        assert "Siap di" in out
        assert "handoff capture" in out

    def test_init_detects_existing_agent_files(self, project: Path, capsys) -> None:
        (project / "CLAUDE.md").write_text("x", encoding="utf-8")
        run("init", "--path", str(project))
        assert "claude" in capsys.readouterr().out

    def test_init_gitignore(self, project: Path, capsys) -> None:
        assert run("init", "--path", str(project), "--gitignore") == 0
        capsys.readouterr()
        content = (project / ".gitignore").read_text(encoding="utf-8")
        assert f"{SESSION_DIR}/" in content

    def test_init_gitignore_is_idempotent(self, project: Path, capsys) -> None:
        run("init", "--path", str(project), "--gitignore", "--quiet")
        run("init", "--path", str(project), "--gitignore", "--quiet")
        capsys.readouterr()
        content = (project / ".gitignore").read_text(encoding="utf-8")
        assert content.count(f"{SESSION_DIR}/") == 1

    def test_init_appends_to_existing_gitignore(self, project: Path, capsys) -> None:
        (project / ".gitignore").write_text("*.pyc", encoding="utf-8")
        run("init", "--path", str(project), "--gitignore", "--quiet")
        capsys.readouterr()
        content = (project / ".gitignore").read_text(encoding="utf-8")
        assert "*.pyc" in content
        assert f"{SESSION_DIR}/" in content


class TestScanTodosCommand:
    def test_scan_lists_items(self, project: Path, capsys) -> None:
        (project / "a.py").write_text("# TODO: one\n# FIXME: two\n", encoding="utf-8")
        assert run("scan-todos", "--path", str(project)) == 0
        out = capsys.readouterr().out
        assert "2 TODO/FIXME" in out
        assert "one" in out and "two" in out

    def test_scan_empty(self, project: Path, capsys) -> None:
        assert run("scan-todos", "--path", str(project)) == 0
        assert "Tidak ada TODO/FIXME" in capsys.readouterr().out

    def test_scan_limit(self, project: Path, capsys) -> None:
        (project / "a.py").write_text(
            "\n".join(f"# TODO: {i}" for i in range(10)), encoding="utf-8"
        )
        run("scan-todos", "--limit", "3", "--path", str(project), "--quiet")
        out = capsys.readouterr().out
        assert "3 TODO/FIXME" in out


class TestFullFlow:
    def test_prd_main_flow(self, git_project: Path, capsys) -> None:
        """PRD §8.1: capture with claude → export to codex → agent reads AGENTS.md."""
        assert (
            run(
                "capture",
                "--goal",
                "Menyelesaikan fitur login",
                "--from",
                "claude",
                "--decision",
                "Pakai JWT :: stateless, cocok untuk API",
                "--todo",
                "Tambahkan refresh token",
                "--done",
                "Endpoint /login selesai",
                "--path",
                str(git_project),
            )
            == 0
        )
        assert run("export", "--to", "codex", "--path", str(git_project)) == 0
        capsys.readouterr()

        agents_md = (git_project / "AGENTS.md").read_text(encoding="utf-8")
        # An agent reading only this file can answer: goal, done, next steps.
        assert "Menyelesaikan fitur login" in agents_md
        assert "Endpoint /login selesai" in agents_md
        assert "Tambahkan refresh token" in agents_md
        assert "Pakai JWT" in agents_md
        # ...and it knows the git context.
        assert "Branch:" in agents_md

    def test_dogfood_round_trip(self, project: Path, tmp_path: Path, capsys) -> None:
        run("init", "--path", str(project), "--quiet")
        run("capture", "--goal", "g1", "--todo", "t1", "--path", str(project), "--quiet")
        log = tmp_path / "log.txt"
        log.write_text("Done: t1\nTODO: t2\nDecision: d :: reason\n", encoding="utf-8")
        run("import-log", str(log), "--path", str(project), "--quiet")
        run("export", "--to", "all", "--path", str(project), "--quiet")
        run("status", "--path", str(project), "--quiet")
        run("show", "--path", str(project))
        capsys.readouterr()

        data = json.loads(session_path(project).read_text(encoding="utf-8"))
        assert data["goal"] == "g1"
        assert data["todos"] == ["t2"]
        assert data["done"] == ["t1"]
        assert data["decisions"] == [{"text": "d", "reason": "reason"}]
