"""Tests for import-log parsing (EN + ID) and the TODO scanner."""

from __future__ import annotations

from pathlib import Path

import pytest

from agenthandoff.importer import (
    LABELS,
    MAX_TODO_ITEMS,
    import_file,
    parse_log,
    scan_todos,
)


class TestParseLogEnglish:
    def test_basic_labels(self) -> None:
        parsed = parse_log(
            """
            Decision: Use JWT for auth
            TODO: Add refresh token
            Done: Login endpoint finished
            """
        )
        assert parsed.decisions == ["Use JWT for auth"]
        assert parsed.todos == ["Add refresh token"]
        assert parsed.done == ["Login endpoint finished"]

    def test_notes(self) -> None:
        parsed = parse_log("Note: meeting tomorrow at 9")
        assert parsed.notes == ["meeting tomorrow at 9"]

    def test_decision_with_reason(self) -> None:
        parsed = parse_log("Decision: Use JWT :: stateless, fits the API")
        assert parsed.decisions == ["Use JWT :: stateless, fits the API"]

    def test_case_insensitive(self) -> None:
        parsed = parse_log("todo: ship it\ndEcIsIoN: keep it simple")
        assert parsed.todos == ["ship it"]
        assert parsed.decisions == ["keep it simple"]

    def test_bullets_quotes_and_numbering(self) -> None:
        parsed = parse_log(
            """
            - TODO: bullet item
            * Done: star item
            > Decision: quote item
            1. TODO: numbered item
            2) SELESAI: numbered done
            """
        )
        assert parsed.todos == ["bullet item", "numbered item"]
        assert parsed.done == ["star item", "numbered done"]
        assert parsed.decisions == ["quote item"]

    def test_bold_markers(self) -> None:
        parsed = parse_log("**TODO:** bold item\n**Decision**: other item")
        assert parsed.todos == ["bold item"]
        assert parsed.decisions == ["other item"]

    def test_dash_separator(self) -> None:
        parsed = parse_log("TODO - dashed separator")
        assert parsed.todos == ["dashed separator"]

    def test_ignores_prose(self) -> None:
        parsed = parse_log(
            """
            We talked about the login page.
            I decided to use JWT because it is stateless.
            This line has a TODO in the middle: not imported.
            """
        )
        assert parsed.total == 0

    def test_ignores_empty_labels(self) -> None:
        parsed = parse_log("TODO:\nDone:   \nDecision: --")
        assert parsed.total == 0

    def test_duplicates_collapse(self) -> None:
        parsed = parse_log("TODO: same thing\nTODO: same thing\nTODO: Same thing.")
        assert parsed.todos == ["same thing"]

    def test_trailing_whitespace_trimmed(self) -> None:
        parsed = parse_log("TODO:    spaced out   ")
        assert parsed.todos == ["spaced out"]

    def test_total(self) -> None:
        parsed = parse_log("TODO: a\nTODO: b\nDone: c")
        assert parsed.total == 3


class TestParseLogIndonesian:
    def test_indonesian_labels(self) -> None:
        parsed = parse_log(
            """
            Keputusan: Pakai JWT :: stateless, cocok untuk API
            Selanjutnya: Tambahkan refresh token
            Selesai: Endpoint /login selesai
            Catatan: rapat besok jam 9
            """
        )
        assert parsed.decisions == ["Pakai JWT :: stateless, cocok untuk API"]
        assert parsed.todos == ["Tambahkan refresh token"]
        assert parsed.done == ["Endpoint /login selesai"]
        assert parsed.notes == ["rapat besok jam 9"]

    def test_more_aliases(self) -> None:
        parsed = parse_log("Berikutnya: deploy\nRencana: tulis docs\nSudah: setup repo")
        assert parsed.todos == ["deploy", "tulis docs"]
        assert parsed.done == ["setup repo"]

    def test_emoji_preserved(self) -> None:
        parsed = parse_log("Selanjutnya: perbaiki UI 🎨\nKeputusan: pakai Tailwind ✨")
        assert parsed.todos == ["perbaiki UI 🎨"]
        assert parsed.decisions == ["pakai Tailwind ✨"]

    def test_label_table_covers_both_languages(self) -> None:
        buckets = {bucket for bucket, _ in LABELS.values()}
        assert buckets == {"decision", "todo", "done", "note"}


class TestImportFile:
    def test_imports_utf8_file(self, tmp_path: Path) -> None:
        path = tmp_path / "notes.txt"
        path.write_text("Keputusan: pakai JWT\nTODO: tulis test\n", encoding="utf-8")
        parsed = import_file(path)
        assert parsed.decisions == ["pakai JWT"]
        assert parsed.todos == ["tulis test"]

    def test_handles_bom_and_bad_bytes(self, tmp_path: Path) -> None:
        path = tmp_path / "notes.txt"
        path.write_bytes(b"\xef\xbb\xbfTODO: item\n\xff\xfe broken\n")
        parsed = import_file(path)
        assert parsed.todos == ["item"]

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            import_file(tmp_path / "nope.txt")

    def test_directory_raises(self, tmp_path: Path) -> None:
        with pytest.raises(IsADirectoryError):
            import_file(tmp_path)

    def test_empty_file(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.txt"
        path.write_text("", encoding="utf-8")
        assert import_file(path).total == 0


class TestScanTodos:
    def test_finds_todos_and_fixmes(self, tmp_path: Path) -> None:
        (tmp_path / "app.py").write_text(
            "x = 1  # TODO: validate input\n"
            "y = 2  # FIXME: handle errors\n"
            "# HACK: temporary workaround\n",
            encoding="utf-8",
        )
        found = scan_todos(tmp_path)
        assert len(found) == 3
        assert found[0] == "app.py:1 — TODO: validate input"
        assert any("FIXME: handle errors" in item for item in found)

    def test_nested_directories_use_posix_paths(self, tmp_path: Path) -> None:
        nested = tmp_path / "src" / "pkg"
        nested.mkdir(parents=True)
        (nested / "mod.ts").write_text("// TODO: add types\n", encoding="utf-8")
        found = scan_todos(tmp_path)
        assert found == ["src/pkg/mod.ts:1 — TODO: add types"]

    def test_skips_ignored_directories(self, tmp_path: Path) -> None:
        for name in ("node_modules", ".git", ".venv", "dist", "__pycache__"):
            directory = tmp_path / name
            directory.mkdir()
            (directory / "ignored.py").write_text("# TODO: hidden\n", encoding="utf-8")
        (tmp_path / "kept.py").write_text("# TODO: visible\n", encoding="utf-8")
        found = scan_todos(tmp_path)
        assert len(found) == 1
        assert "kept.py" in found[0]

    def test_skips_unknown_extensions(self, tmp_path: Path) -> None:
        (tmp_path / "image.png").write_text("# TODO: nope\n", encoding="utf-8")
        (tmp_path / "notes.txt").write_text("# TODO: nope\n", encoding="utf-8")
        assert scan_todos(tmp_path) == []

    def test_respects_limit(self, tmp_path: Path) -> None:
        (tmp_path / "many.py").write_text(
            "\n".join(f"# TODO: item {i}" for i in range(100)), encoding="utf-8"
        )
        assert len(scan_todos(tmp_path, limit=5)) == 5

    def test_default_limit(self, tmp_path: Path) -> None:
        (tmp_path / "many.py").write_text(
            "\n".join(f"# TODO: item {i}" for i in range(MAX_TODO_ITEMS + 20)),
            encoding="utf-8",
        )
        assert len(scan_todos(tmp_path)) == MAX_TODO_ITEMS

    def test_skips_large_files(self, tmp_path: Path) -> None:
        big = tmp_path / "big.py"
        big.write_text("# TODO: huge\n" + "x = 1\n" * 200_000, encoding="utf-8")
        assert scan_todos(tmp_path) == []

    def test_truncates_long_messages(self, tmp_path: Path) -> None:
        (tmp_path / "long.py").write_text(f"# TODO: {'a' * 500}\n", encoding="utf-8")
        found = scan_todos(tmp_path)
        assert len(found[0]) < 300

    def test_missing_root_returns_empty(self, tmp_path: Path) -> None:
        assert scan_todos(tmp_path / "missing") == []

    def test_message_is_cleaned(self, tmp_path: Path) -> None:
        (tmp_path / "c.py").write_text("int x; // TODO:   tidy   this  */\n", encoding="utf-8")
        assert scan_todos(tmp_path) == ["c.py:1 — TODO: tidy this"]
