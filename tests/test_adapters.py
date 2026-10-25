"""Tests for the export adapters — the "never destroy user content" gate."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from agenthandoff.adapters import (
    ALIASES,
    BEGIN_MARKER,
    END_MARKER,
    TARGET_NAMES,
    TARGETS,
    Adapter,
    AdapterError,
    export,
    export_target,
    find_block,
    merge_block,
    render_block,
    resolve_target,
    resolve_targets,
)
from agenthandoff.core import (
    Session,
    capture,
    handoff_path,
    load_session,
    render_handoff,
    save_session,
)

AGENT_FILES = sorted({adapter.path for adapter in TARGETS.values()})


def _target_path(root: Path, name: str) -> Path:
    return root / TARGETS[name].path


def _count_blocks(text: str) -> int:
    return text.count(BEGIN_MARKER)


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #
class TestRegistry:
    def test_all_documented_targets_exist(self) -> None:
        assert set(TARGET_NAMES) == {
            "claude",
            "codex",
            "gemini",
            "cursor",
            "copilot",
            "windsurf",
            "markdown",
        }

    @pytest.mark.parametrize(
        "name,expected",
        [
            ("claude", "CLAUDE.md"),
            ("codex", "AGENTS.md"),
            ("agents", "AGENTS.md"),
            ("gemini", "GEMINI.md"),
            ("cursor", ".cursor/rules/agent-handoff.mdc"),
            ("copilot", ".github/copilot-instructions.md"),
            ("windsurf", ".windsurf/rules/agent-handoff.md"),
            ("markdown", ".agent-handoff/HANDOFF.md"),
        ],
    )
    def test_paths(self, name: str, expected: str) -> None:
        assert resolve_target(name).path == expected

    def test_aliases_resolve(self) -> None:
        assert resolve_target("AGENTS").name == "codex"
        assert resolve_target("md").name == "markdown"
        assert resolve_target("github-copilot").name == "copilot"
        assert resolve_target("claude-code").name == "claude"

    def test_alias_table_is_lowercase(self) -> None:
        assert all(key == key.casefold() for key in ALIASES)

    def test_unknown_target_lists_valid_ones(self) -> None:
        with pytest.raises(AdapterError) as excinfo:
            resolve_target("zed")
        message = str(excinfo.value)
        assert "zed" in message
        for name in TARGET_NAMES:
            assert name in message

    def test_empty_target_lists_valid_ones(self) -> None:
        with pytest.raises(AdapterError):
            resolve_targets("")

    def test_resolve_all(self) -> None:
        assert [a.name for a in resolve_targets("all")] == list(TARGET_NAMES)

    def test_resolve_multiple_and_comma_separated(self) -> None:
        names = [a.name for a in resolve_targets(["claude,codex", "claude"])]
        assert names == ["claude", "codex"]

    def test_adapter_is_frozen(self) -> None:
        with pytest.raises(dataclasses.FrozenInstanceError):
            TARGETS["claude"].path = "X.md"  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# Block rendering & merging
# --------------------------------------------------------------------------- #
class TestRenderBlock:
    def test_markers_wrap_content(self, session) -> None:
        block = render_block(session)
        assert block.startswith(BEGIN_MARKER)
        assert block.rstrip().endswith(END_MARKER)
        assert "Add login" in block
        assert "- [ ] Add refresh token" in block
        assert "- [x] Endpoint /login selesai" in block
        assert "Pakai JWT" in block

    def test_empty_session_still_valid(self, project: Path) -> None:
        empty = capture(project)
        block = render_block(empty)
        assert "_Nothing recorded yet._" in block
        assert _count_blocks(block) == 1


class TestMergeBlock:
    def test_insert_into_empty(self) -> None:
        block = f"{BEGIN_MARKER}\nhi\n{END_MARKER}\n"
        result = merge_block("", block, TARGETS["claude"])
        assert result == block

    def test_insert_preserves_user_content(self) -> None:
        block = f"{BEGIN_MARKER}\nhi\n{END_MARKER}\n"
        existing = "# My rules\n\nUse tabs.\n"
        result = merge_block(existing, block, TARGETS["claude"])
        assert "# My rules" in result
        assert "Use tabs." in result
        assert _count_blocks(result) == 1

    def test_repeated_merge_is_idempotent(self) -> None:
        block = f"{BEGIN_MARKER}\nhi\n{END_MARKER}\n"
        once = merge_block("# User\n", block, TARGETS["claude"])
        twice = merge_block(once, block, TARGETS["claude"])
        assert once == twice
        assert _count_blocks(twice) == 1

    def test_merge_replaces_old_content(self) -> None:
        old = f"{BEGIN_MARKER}\nold\n{END_MARKER}\n"
        new = f"{BEGIN_MARKER}\nnew\n{END_MARKER}\n"
        existing = f"# Top\n{old}\n# Bottom\n"
        result = merge_block(existing, new, TARGETS["claude"])
        assert "old" not in result
        assert "new" in result
        assert "# Top" in result and "# Bottom" in result

    def test_duplicate_blocks_are_collapsed(self) -> None:
        block = f"{BEGIN_MARKER}\nhi\n{END_MARKER}\n"
        existing = f"{block}\n{block}\n"
        result = merge_block(existing, block, TARGETS["claude"])
        assert _count_blocks(result) == 1

    def test_broken_markers_raise_and_do_not_guess(self) -> None:
        with pytest.raises(AdapterError) as excinfo:
            merge_block(f"{BEGIN_MARKER}\nno end\n", "x", TARGETS["claude"])
        assert "agent-handoff:end" in str(excinfo.value)

    def test_leading_blank_lines_are_preserved_exactly(self) -> None:
        adapter = Adapter(name="t", path="t.md", description="", placement="top")
        block = f"{BEGIN_MARKER}\nhi\n{END_MARKER}\n"
        existing = "\n\n# Title\nbody\n"
        result = merge_block(existing, block, adapter)
        assert result.endswith(existing)  # user content is byte-identical

    def test_crlf_input_keeps_crlf(self) -> None:
        block = f"{BEGIN_MARKER}\nhi\n{END_MARKER}\n"
        result = merge_block("line1\r\nline2\r\n", block, TARGETS["claude"])
        assert "\r\n" in result
        assert "\n" not in result.replace("\r\n", "")

    def test_frontmatter_file_gets_block_after_frontmatter(self) -> None:
        frontmatter = "---\ndescription: x\n---\n"
        block = f"{BEGIN_MARKER}\nhi\n{END_MARKER}\n"
        adapter = Adapter(name="t", path="t.md", description="", placement="top")
        result = merge_block(frontmatter + "# Body\n", block, adapter)
        assert result.startswith(frontmatter)
        assert "# Body" in result
        assert _count_blocks(result) == 1

    def test_end_placement_appends(self) -> None:
        adapter = Adapter(name="t", path="t.md", description="", placement="end")
        block = f"{BEGIN_MARKER}\nhi\n{END_MARKER}\n"
        result = merge_block("# Top\n", block, adapter)
        assert result.index("# Top") < result.index(BEGIN_MARKER)
        assert result.endswith("\n")

    def test_find_block_reports_span(self) -> None:
        text = f"a\n{BEGIN_MARKER}\nb\n{END_MARKER}\nc\n"
        block = find_block(text)
        assert block is not None
        assert text[block.start : block.start + len(BEGIN_MARKER)] == BEGIN_MARKER
        assert block.count == 1
        assert find_block("no block here") is None


# --------------------------------------------------------------------------- #
# export_target / export
# --------------------------------------------------------------------------- #
class TestExportTargets:
    @pytest.mark.parametrize("name", TARGET_NAMES)
    def test_each_target_creates_its_file(self, project: Path, session, name: str) -> None:
        result = export_target(project, session, TARGETS[name])
        path = _target_path(project, name)
        assert path.is_file()
        # The session fixture already wrote HANDOFF.md, so the markdown target
        # is up to date from the start.
        expected = {"created", "unchanged"} if name == "markdown" else {"created"}
        assert result.status in expected
        text = path.read_text(encoding="utf-8")
        if name == "markdown":
            assert text == render_handoff(session)
        else:
            assert _count_blocks(text) == 1
            assert "Add login" in text

    def test_export_all_creates_every_file(self, project: Path, session) -> None:
        results = export(project, session, resolve_targets("all"))
        assert len(results) == len(TARGET_NAMES)
        for path in AGENT_FILES:
            assert (project / path).is_file()

    @pytest.mark.parametrize("name", [n for n in TARGET_NAMES if n != "markdown"])
    def test_export_is_idempotent(self, project: Path, session, name: str) -> None:
        export_target(project, session, TARGETS[name])
        path = _target_path(project, name)
        first = path.read_bytes()
        second_result = export_target(project, session, TARGETS[name])
        assert path.read_bytes() == first
        assert second_result.status == "unchanged"
        assert _count_blocks(path.read_text(encoding="utf-8")) == 1

    def test_markdown_export_is_idempotent(self, project: Path, session) -> None:
        export_target(project, session, TARGETS["markdown"])
        path = _target_path(project, "markdown")
        first = path.read_bytes()
        assert export_target(project, session, TARGETS["markdown"]).status == "unchanged"
        assert path.read_bytes() == first

    @pytest.mark.parametrize("name", [n for n in TARGET_NAMES if n != "markdown"])
    def test_user_content_survives_repeated_exports(
        self, project: Path, session, name: str
    ) -> None:
        path = _target_path(project, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        top = "# Keep me at the top\n\nuser rule one\n"
        bottom = "\n## Keep me at the bottom\nuser rule two\n"
        path.write_text(top + bottom, encoding="utf-8")

        for _ in range(3):
            export_target(project, session, TARGETS[name])

        text = path.read_text(encoding="utf-8")
        assert "# Keep me at the top" in text
        assert "user rule one" in text
        assert "## Keep me at the bottom" in text
        assert "user rule two" in text
        assert _count_blocks(text) == 1

    def test_export_updates_block_when_session_changes(
        self, project: Path, session
    ) -> None:
        path = _target_path(project, "codex")
        export_target(project, session, TARGETS["codex"])
        session.goal = "Add login and SSO"
        result = export_target(project, session, TARGETS["codex"])
        text = path.read_text(encoding="utf-8")
        assert result.status == "updated"
        assert "Add login and SSO" in text
        assert _count_blocks(text) == 1

    def test_cursor_file_has_frontmatter(self, project: Path, session) -> None:
        export_target(project, session, TARGETS["cursor"])
        text = _target_path(project, "cursor").read_text(encoding="utf-8")
        assert text.startswith("---\n")
        assert "alwaysApply: true" in text
        assert _count_blocks(text) == 1

    def test_cursor_frontmatter_not_duplicated_on_re_export(
        self, project: Path, session
    ) -> None:
        export_target(project, session, TARGETS["cursor"])
        export_target(project, session, TARGETS["cursor"])
        text = _target_path(project, "cursor").read_text(encoding="utf-8")
        assert text.count("alwaysApply") == 1

    def test_existing_cursor_frontmatter_is_preserved(
        self, project: Path, session
    ) -> None:
        path = _target_path(project, "cursor")
        path.parent.mkdir(parents=True, exist_ok=True)
        original = '---\ndescription: mine\nglobs: ["src/**"]\n---\n\nMy rule.\n'
        path.write_text(original, encoding="utf-8")

        export_target(project, session, TARGETS["cursor"])
        text = path.read_text(encoding="utf-8")

        assert "description: mine" in text
        assert "My rule." in text
        assert text.count("alwaysApply") == 0  # we never inject a second frontmatter
        assert _count_blocks(text) == 1

    def test_broken_marker_file_is_left_untouched(self, project: Path, session) -> None:
        path = _target_path(project, "claude")
        original = f"# User\n{BEGIN_MARKER}\nhalf written\n"
        path.write_text(original, encoding="utf-8")
        with pytest.raises(AdapterError):
            export_target(project, session, TARGETS["claude"])
        assert path.read_text(encoding="utf-8") == original

    def test_non_utf8_file_is_not_mangled(self, project: Path, session) -> None:
        path = _target_path(project, "claude")
        original = "# Règles\n".encode("latin-1")
        path.write_bytes(original)

        with pytest.raises(AdapterError) as excinfo:
            export_target(project, session, TARGETS["claude"])

        assert "UTF-8" in str(excinfo.value)
        assert path.read_bytes() == original  # untouched, not "repaired"

    def test_target_path_is_a_directory_raises(self, project: Path, session) -> None:
        path = _target_path(project, "gemini")
        path.mkdir(parents=True)
        with pytest.raises(AdapterError) as excinfo:
            export_target(project, session, TARGETS["gemini"])
        assert "is not a file" in str(excinfo.value)

    def test_crlf_file_stays_crlf(self, project: Path, session) -> None:
        path = _target_path(project, "windsurf")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"# Windows rules\r\n\r\nkeep\r\n")

        export_target(project, session, TARGETS["windsurf"])
        raw = path.read_bytes().decode("utf-8")

        assert "# Windows rules" in raw
        assert "keep" in raw
        assert "\r\n" in raw
        assert "\n" not in raw.replace("\r\n", "")

    def test_utf8_content_written_correctly(self, project: Path, session) -> None:
        session.goal = "Selesaikan login 🔐 dengan emoji"
        path = _target_path(project, "codex")
        export_target(project, session, TARGETS["codex"])
        assert "🔐" in path.read_text(encoding="utf-8")

    def test_no_temp_files_left_behind(self, project: Path, session) -> None:
        export_target(project, session, TARGETS["claude"])
        assert not list(project.glob(".*.tmp"))


# --------------------------------------------------------------------------- #
# End-to-end through the session file
# --------------------------------------------------------------------------- #
def test_capture_then_export_reads_source_of_truth(project: Path) -> None:
    capture(project, goal="First goal", todos=["old todo"])
    session = load_session(project)
    assert session is not None
    export(project, session, resolve_targets("all"))

    capture(project, goal="Second goal", done=["old todo"])
    updated = load_session(project)
    assert updated is not None

    for adapter in resolve_targets("all"):
        result = export_target(project, updated, adapter)
        text = tool_text = result.path.read_text(encoding="utf-8")
        assert tool_text  # keep flake-friendly
        assert "Second goal" in text
        if adapter.name != "markdown":
            assert "- [ ] old todo" not in text
            assert _count_blocks(text) == 1


def test_handoff_file_matches_session(project: Path) -> None:
    session = capture(project, goal="Match me")
    export_target(project, session, TARGETS["markdown"])
    assert handoff_path(project).read_text(encoding="utf-8") == render_handoff(
        load_session(project)
    )


def test_empty_session_export_still_safe(project: Path) -> None:
    empty = Session(project="p")
    save_session(project, empty)
    results = export(project, empty, resolve_targets("all"))
    assert all(result.status == "created" for result in results)
    for adapter in resolve_targets("all"):
        assert (project / adapter.path).is_file()
