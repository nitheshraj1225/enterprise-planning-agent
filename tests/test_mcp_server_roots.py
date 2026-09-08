"""
Tests for the MCP Roots boundary check in epic_sizing_prompt (app/mcp/server.py).

epic_id feeds directly into a file path, so without the Roots check a
crafted epic_id (e.g. "../../../etc/passwd") could read files outside
the synthetic corpus. These tests exercise that check directly by
stubbing the ctx.request_context.session.list_roots() call — no real
MCP client/transport needed, since @mcp.prompt() leaves the underlying
function directly callable.
"""

import asyncio
from pathlib import Path

from mcp.types import ListRootsResult, Root
from pydantic import FileUrl

from app.mcp.server import epic_sizing_prompt

PROJECT_ROOT = Path.cwd().resolve()
CORPUS_DIR = PROJECT_ROOT / "app" / "data" / "synthetic_corpus" / "epics"


class _FakeSession:
    def __init__(self, root_paths):
        self._root_paths = root_paths

    async def list_roots(self):
        return ListRootsResult(
            roots=[Root(uri=FileUrl(f"file://{p}")) for p in self._root_paths]
        )


class _FakeRequestContext:
    def __init__(self, root_paths):
        self.session = _FakeSession(root_paths)


class _FakeContext:
    """Minimal stand-in for mcp.server.fastmcp.Context — duck-types only
    the .request_context.session.list_roots() path epic_sizing_prompt uses."""

    def __init__(self, root_paths):
        self.request_context = _FakeRequestContext(root_paths)


def _run(coro):
    return asyncio.run(coro)


def test_denies_when_epic_outside_declared_roots(tmp_path):
    # Declared root is unrelated to the corpus dir -> any epic_id must be denied.
    ctx = _FakeContext(root_paths=[str(tmp_path)])

    result = _run(epic_sizing_prompt(epic_id="EPIC-0001", ctx=ctx))

    assert result == "Access denied: 'EPIC-0001' resolves outside the client's declared Roots."


def test_denies_path_traversal_outside_narrow_root():
    # Root is scoped to the corpus dir itself; a traversal epic_id must
    # still be refused even though "EPIC-0001" alone would be allowed.
    ctx = _FakeContext(root_paths=[str(CORPUS_DIR)])

    result = _run(epic_sizing_prompt(epic_id="../../../../../../etc/passwd", ctx=ctx))

    assert result.startswith("Access denied:")


def test_traversal_denied_before_existence_is_checked(tmp_path):
    # The denial must not leak whether the traversal target exists —
    # same message shape regardless.
    ctx = _FakeContext(root_paths=[str(tmp_path)])

    result = _run(epic_sizing_prompt(epic_id="../../../../../../etc/passwd", ctx=ctx))

    assert result.startswith("Access denied:")
    assert "No Epic found" not in result


def test_allows_epic_within_declared_root():
    # Project root is declared -> the corpus dir is in-bounds, and an
    # existing Epic file should size normally rather than being denied.
    ctx = _FakeContext(root_paths=[str(PROJECT_ROOT)])

    result = _run(epic_sizing_prompt(epic_id="EPIC-0001", ctx=ctx))

    assert not result.startswith("Access denied:")
    assert "<epic_context>" in result


def test_allowed_root_but_missing_epic_falls_through_to_not_found():
    # Boundary check passes independently of file existence — a missing
    # (but in-bounds) epic_id should reach the "not found" branch, not denial.
    ctx = _FakeContext(root_paths=[str(PROJECT_ROOT)])

    result = _run(epic_sizing_prompt(epic_id="EPIC-9999-DOES-NOT-EXIST", ctx=ctx))

    assert result == "No Epic found with ID EPIC-9999-DOES-NOT-EXIST."
