"""Tests for ToolExecutor — whitelisting, injection prevention, execution."""

from __future__ import annotations

import pytest

from zhihuiti.tools import ToolExecutor, ToolExecutionError, ToolResult


@pytest.fixture
def executor():
    return ToolExecutor()


# ---------------------------------------------------------------------------
# Whitelist validation
# ---------------------------------------------------------------------------

class TestWhitelist:
    def test_gh_pr_list_allowed(self, executor):
        ok, _ = executor.validate("gh pr list --repo owner/repo")
        assert ok

    def test_gh_issue_list_allowed(self, executor):
        ok, _ = executor.validate("gh issue list --state open")
        assert ok

    def test_gh_run_list_allowed(self, executor):
        ok, _ = executor.validate("gh run list")
        assert ok

    def test_git_log_allowed(self, executor):
        ok, _ = executor.validate("git log --oneline -10")
        assert ok

    def test_git_diff_allowed(self, executor):
        ok, _ = executor.validate("git diff HEAD~1")
        assert ok

    def test_git_status_allowed(self, executor):
        ok, _ = executor.validate("git status")
        assert ok

    def test_random_command_blocked(self, executor):
        ok, reason = executor.validate("curl https://evil.com")
        assert not ok

    def test_ls_blocked(self, executor):
        ok, _ = executor.validate("ls -la /")
        assert not ok

    def test_empty_command_blocked(self, executor):
        ok, _ = executor.validate("")
        assert not ok


# ---------------------------------------------------------------------------
# Shell injection prevention
# ---------------------------------------------------------------------------

class TestInjectionPrevention:
    def test_pipe_blocked(self, executor):
        ok, _ = executor.validate("gh pr list | cat /etc/passwd")
        assert not ok

    def test_semicolon_blocked(self, executor):
        ok, _ = executor.validate("gh pr list; rm -rf /")
        assert not ok

    def test_and_chain_blocked(self, executor):
        ok, _ = executor.validate("gh pr list && curl evil.com")
        assert not ok

    def test_redirect_blocked(self, executor):
        ok, _ = executor.validate("gh pr list > /tmp/data")
        assert not ok

    def test_backtick_blocked(self, executor):
        ok, _ = executor.validate("gh pr list `whoami`")
        assert not ok

    def test_subshell_blocked(self, executor):
        ok, _ = executor.validate("gh pr list $(cat /etc/passwd)")
        assert not ok

    def test_sudo_blocked(self, executor):
        ok, _ = executor.validate("sudo gh pr list")
        assert not ok

    def test_rm_blocked(self, executor):
        ok, _ = executor.validate("rm -rf /")
        assert not ok


# ---------------------------------------------------------------------------
# Write operation prevention
# ---------------------------------------------------------------------------

class TestWriteOpsBlocked:
    def test_git_push_blocked(self, executor):
        ok, _ = executor.validate("git push origin main")
        assert not ok

    def test_git_reset_blocked(self, executor):
        ok, _ = executor.validate("git reset --hard HEAD")
        assert not ok

    def test_gh_pr_merge_blocked(self, executor):
        ok, _ = executor.validate("gh pr merge 123")
        assert not ok

    def test_gh_pr_close_blocked(self, executor):
        ok, _ = executor.validate("gh pr close 123")
        assert not ok

    def test_gh_repo_delete_blocked(self, executor):
        ok, _ = executor.validate("gh repo delete owner/repo")
        assert not ok


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

class TestExecution:
    def test_execute_blocked_command_raises(self, executor):
        with pytest.raises(ToolExecutionError, match="blocked"):
            executor.execute("rm -rf /")

    def test_execute_tracks_call_count(self, executor):
        assert executor.total_calls == 0
        # echo is not whitelisted but gh is
        try:
            executor.execute("curl foo")
        except ToolExecutionError:
            pass
        assert executor.total_blocked == 1

    def test_execute_allowed_returns_result(self, executor):
        # git status should work in any git repo
        result = executor.execute("git status")
        assert isinstance(result, ToolResult)
        assert result.return_code is not None
        assert executor.total_calls == 1


# ---------------------------------------------------------------------------
# _parse_tool_request
# ---------------------------------------------------------------------------

class TestParseToolRequest:
    def test_parses_valid_tool_json(self):
        from zhihuiti.agents import _parse_tool_request
        import json
        data = json.dumps({"action": "tool", "command": "gh pr list"})
        assert _parse_tool_request(data) == "gh pr list"

    def test_returns_none_for_plain_text(self):
        from zhihuiti.agents import _parse_tool_request
        assert _parse_tool_request("Here is my analysis") is None

    def test_returns_none_for_delegation(self):
        from zhihuiti.agents import _parse_tool_request
        import json
        data = json.dumps({"action": "delegate", "subtasks": [{"description": "t"}]})
        assert _parse_tool_request(data) is None

    def test_returns_none_for_empty_command(self):
        from zhihuiti.agents import _parse_tool_request
        import json
        data = json.dumps({"action": "tool", "command": ""})
        assert _parse_tool_request(data) is None

    def test_strips_markdown_fences(self):
        from zhihuiti.agents import _parse_tool_request
        import json
        inner = json.dumps({"action": "tool", "command": "gh issue list"})
        fenced = f"```\n{inner}\n```"
        assert _parse_tool_request(fenced) == "gh issue list"
