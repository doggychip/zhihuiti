"""Tests for AlphaArena bridge and trading integration."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from zhihuiti.alphaarena import AlphaArenaBridge
from zhihuiti.models import AgentRole, ROLE_TO_REALM, Realm
from zhihuiti.agents import ROLE_MAP


class TestAlphaArenaRole:
    def test_role_exists(self):
        assert AgentRole.ALPHAARENA_TRADER.value == "alphaarena_trader"

    def test_role_in_execution_realm(self):
        assert ROLE_TO_REALM[AgentRole.ALPHAARENA_TRADER] == Realm.EXECUTION

    def test_role_in_role_map(self):
        assert "alphaarena_trader" in ROLE_MAP
        assert ROLE_MAP["alphaarena_trader"] == AgentRole.ALPHAARENA_TRADER


class TestAlphaArenaPrompt:
    def test_prompt_exists(self):
        from zhihuiti.prompts import get_prompt
        prompt = get_prompt("alphaarena_trader")
        assert "AlphaArena" in prompt
        assert "BTC/USD" in prompt
        assert "Sharpe" in prompt

    def test_prompt_has_workflow(self):
        from zhihuiti.prompts import get_prompt
        prompt = get_prompt("alphaarena_trader")
        assert "curl" in prompt
        assert "/api/trades" in prompt
        assert "/api/prices" in prompt


class TestToolWhitelist:
    def test_trades_endpoint_whitelisted(self):
        from zhihuiti.tools import ToolExecutor
        executor = ToolExecutor()
        assert "/api/trades" in executor.ALLOWED_POST_URLS

    def test_register_endpoint_whitelisted(self):
        from zhihuiti.tools import ToolExecutor
        executor = ToolExecutor()
        assert "/api/auth/register" in executor.ALLOWED_POST_URLS

    def test_trade_curl_allowed(self):
        from zhihuiti.tools import ToolExecutor
        executor = ToolExecutor()
        ok, reason = executor.validate(
            'curl -s -X POST https://alphaarena.app/api/trades '
            '-H "Content-Type: application/json" '
            '-d \'{"agentId":"123","pair":"BTC/USD","side":"buy","quantity":0.1}\''
        )
        assert ok, f"Trade curl should be allowed: {reason}"


class TestAlphaArenaBridge:
    def test_init_defaults(self):
        bridge = AlphaArenaBridge(base_url="https://test.com", api_key="key", agent_id="agent1")
        assert bridge.base_url == "https://test.com"
        assert bridge.api_key == "key"
        assert bridge.agent_id == "agent1"

    @patch("zhihuiti.alphaarena.httpx.Client")
    def test_get_prices(self, mock_client_class):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"prices": [{"pair": "BTC/USD", "price": 85000, "change24h": 2.5}]}
        mock_resp.raise_for_status.return_value = None
        mock_client.get.return_value = mock_resp
        mock_client_class.return_value = mock_client

        bridge = AlphaArenaBridge(base_url="https://test.com")
        prices = bridge.get_prices()
        assert len(prices) == 1
        assert prices[0]["pair"] == "BTC/USD"

    @patch("zhihuiti.alphaarena.httpx.Client")
    def test_get_portfolio(self, mock_client_class):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"cashBalance": 50000, "totalEquity": 100000, "positions": []}
        mock_resp.raise_for_status.return_value = None
        mock_client.get.return_value = mock_resp
        mock_client_class.return_value = mock_client

        bridge = AlphaArenaBridge(base_url="https://test.com", agent_id="agent1")
        portfolio = bridge.get_portfolio()
        assert portfolio["cashBalance"] == 50000

    @patch("zhihuiti.alphaarena.httpx.Client")
    def test_trade(self, mock_client_class):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": "filled", "pair": "BTC/USD"}
        mock_resp.raise_for_status.return_value = None
        mock_client.post.return_value = mock_resp
        mock_client_class.return_value = mock_client

        bridge = AlphaArenaBridge(base_url="https://test.com", api_key="key", agent_id="agent1")
        result = bridge.trade("BTC/USD", "buy", 0.1)
        assert result["status"] == "filled"

    @patch("zhihuiti.alphaarena.httpx.Client")
    def test_generate_status_report(self, mock_client_class):
        mock_client = MagicMock()

        def mock_get(url):
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            if "prices" in url:
                resp.json.return_value = {"prices": [{"pair": "BTC/USD", "price": 85000, "change24h": 2.5}]}
            elif "portfolio" in url:
                resp.json.return_value = {"cashBalance": 50000, "totalEquity": 100000, "positions": []}
            elif "leaderboard" in url:
                resp.json.return_value = [{"agentName": "Bot1", "score": 95.5, "totalReturn": 12.3}]
            return resp

        mock_client.get.side_effect = mock_get
        mock_client_class.return_value = mock_client

        bridge = AlphaArenaBridge(base_url="https://test.com", api_key="key", agent_id="agent1")
        report = bridge.generate_status_report()
        assert "BTC/USD" in report
        assert "Portfolio" in report
        assert "Leaderboard" in report

    def test_no_agent_id_portfolio(self):
        bridge = AlphaArenaBridge(base_url="https://test.com", agent_id="")
        result = bridge.get_portfolio()
        assert "error" in result
