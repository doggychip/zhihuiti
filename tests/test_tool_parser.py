"""Tests for improved tool request parser."""

from zhihuiti.agents import _parse_tool_request


class TestToolParser:
    def test_proper_json(self):
        resp = '{"action": "tool", "command": "curl -s https://api.com/prices"}'
        assert _parse_tool_request(resp) == "curl -s https://api.com/prices"

    def test_json_in_code_fence(self):
        resp = '```json\n{"action": "tool", "command": "gh pr list"}\n```'
        assert _parse_tool_request(resp) == "gh pr list"

    def test_bare_curl_on_own_line(self):
        resp = "I'll check the prices:\n\ncurl -s https://alphaarena.zeabur.app/api/prices\n\nThis will show us the market data."
        result = _parse_tool_request(resp)
        assert result == "curl -s https://alphaarena.zeabur.app/api/prices"

    def test_bare_curl_in_code_block(self):
        resp = "Run this:\n```bash\ncurl -s -X POST https://alphaarena.zeabur.app/api/trades -H \"X-API-Key: key\" -d '{\"pair\":\"BTC/USD\"}'\n```"
        result = _parse_tool_request(resp)
        assert result is not None
        assert "curl" in result
        assert "/api/trades" in result

    def test_curl_with_dollar_prefix(self):
        resp = "Execute:\n$ curl -s https://api.com/data\nThat should work."
        result = _parse_tool_request(resp)
        assert result == "curl -s https://api.com/data"

    def test_gh_command_bare(self):
        resp = "Let me check:\ngh pr list --repo doggychip/heartai --state open"
        result = _parse_tool_request(resp)
        assert result == "gh pr list --repo doggychip/heartai --state open"

    def test_no_tool_plain_text(self):
        resp = "The analysis shows that BTC is trending up by 2.5%."
        assert _parse_tool_request(resp) is None

    def test_no_tool_curl_in_explanation(self):
        resp = "curl is a command-line tool for transferring data."
        assert _parse_tool_request(resp) is None

    def test_json_embedded_in_text(self):
        resp = 'I will use this tool:\n{"action": "tool", "command": "curl -s https://api.com"}\nto get data.'
        result = _parse_tool_request(resp)
        assert result == "curl -s https://api.com"

    def test_not_a_tool_json(self):
        resp = '{"action": "delegate", "subtasks": []}'
        assert _parse_tool_request(resp) is None

    def test_empty_response(self):
        assert _parse_tool_request("") is None

    def test_run_prefix(self):
        resp = "Run: curl -s https://api.com/health"
        result = _parse_tool_request(resp)
        assert result == "curl -s https://api.com/health"
