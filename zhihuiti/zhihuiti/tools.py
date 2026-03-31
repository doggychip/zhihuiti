"""Tool executor — whitelisted shell command execution for agents.

Agents can request tool execution via {"action": "tool", "command": "gh pr list ..."}
Only read-only commands are allowed. Each call costs TOOL_COST budget units.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass

from rich.console import Console

console = Console()

TOOL_COST = 2.0        # Budget units per tool call
MAX_TOOL_CALLS = 5     # Max tool calls per task execution
TOOL_TIMEOUT = 30      # Seconds before command is killed
MAX_OUTPUT_LEN = 4000  # Truncate output beyond this

# Commands that are allowed (prefix match)
ALLOWED_PREFIXES = [
    # GitHub CLI (read-only)
    "gh pr ",
    "gh issue ",
    "gh run ",
    "gh repo view",
    "gh api ",
    # Git (read-only)
    "git log",
    "git diff",
    "git show",
    "git status",
    "git blame",
    "git branch --list",
    "git branch -a",
    # HTTP (read-only health checks, API queries)
    "curl -s ",
    "curl --silent ",
    "curl -sS ",
    # Node/Python project inspection (read-only)
    "npm ls",
    "npm outdated",
    "npm audit",
    "pip list",
    "pip show",
    # Process inspection
    "ps aux",
    "lsof -i",
    # Docker inspection (read-only)
    "docker ps",
    "docker logs",
    "docker inspect",
    "docker stats --no-stream",
]

# Patterns that are always blocked (shell injection, writes, destructive ops)
BLOCKED_PATTERNS = [
    "|", ";", "&&", "||",  # command chaining
    ">", "<", ">>",        # redirection
    "`", "$(",              # subshell
    "rm ", "sudo",          # destructive
    "git push", "git reset", "git checkout", "git rebase",  # write ops
    "gh pr merge", "gh pr close", "gh issue close",         # write ops
    "gh repo delete", "gh repo create",                     # write ops
    "docker rm", "docker stop", "docker kill",              # destructive docker
    "npm install", "npm run", "pip install",                # write ops
    "curl -X POST", "curl -X PUT", "curl -X DELETE",       # write HTTP
    "curl --data", "curl -d ",                              # write HTTP (except whitelisted)
]


@dataclass
class ToolResult:
    """Result of a tool execution."""
    command: str
    stdout: str
    stderr: str
    return_code: int
    truncated: bool = False


class ToolExecutionError(Exception):
    pass


class ToolExecutor:
    """Executes whitelisted shell commands for agents."""

    def __init__(self):
        self.total_calls = 0
        self.total_blocked = 0

    # Whitelisted POST endpoints (specific URLs that agents can POST to)
    ALLOWED_POST_URLS = [
        "/api/generate-activity",  # CriticAI: trigger agent activity
        "/api/trades",             # AlphaArena: submit trades
        "/api/auth/register",      # AlphaArena: register new agent
    ]

    def validate(self, command: str) -> tuple[bool, str]:
        """Check if a command is allowed.

        Returns (allowed, reason).
        """
        cmd = command.strip()

        if not cmd:
            return False, "empty command"

        # Special case: allow whitelisted POST requests to known APIs
        if "curl" in cmd and ("-X POST" in cmd or "--data" in cmd or "-d " in cmd):
            for url in self.ALLOWED_POST_URLS:
                if url in cmd:
                    return True, f"allowed POST to {url}"
            return False, "POST requests only allowed to whitelisted endpoints"

        # Check blocked patterns
        for pattern in BLOCKED_PATTERNS:
            if pattern in cmd:
                return False, f"blocked pattern: {pattern}"

        # Check allowed prefixes
        for prefix in ALLOWED_PREFIXES:
            if cmd.startswith(prefix):
                return True, "allowed"

        # Special case: bare "gh" commands not in prefix list
        if cmd.startswith("gh "):
            # Allow any gh subcommand not explicitly blocked
            return True, "allowed (gh)"

        return False, f"command not whitelisted: {cmd.split()[0] if cmd.split() else cmd}"

    def execute(self, command: str) -> ToolResult:
        """Validate and execute a command.

        Raises ToolExecutionError if command is not allowed.
        """
        allowed, reason = self.validate(command)
        if not allowed:
            self.total_blocked += 1
            raise ToolExecutionError(f"Command blocked: {reason}")

        self.total_calls += 1
        console.print(f"  [dim]🔧 Tool:[/dim] {command[:80]}")

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=TOOL_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                command=command,
                stdout="",
                stderr=f"Command timed out after {TOOL_TIMEOUT}s",
                return_code=-1,
            )
        except Exception as e:
            return ToolResult(
                command=command,
                stdout="",
                stderr=str(e),
                return_code=-1,
            )

        stdout = result.stdout
        truncated = False
        if len(stdout) > MAX_OUTPUT_LEN:
            stdout = stdout[:MAX_OUTPUT_LEN] + "\n... (truncated)"
            truncated = True

        return ToolResult(
            command=command,
            stdout=stdout,
            stderr=result.stderr[:1000] if result.stderr else "",
            return_code=result.returncode,
            truncated=truncated,
        )
