"""Tests for the performance report module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from zhihuiti.performance_report import PerformanceReport, INITIAL_EQUITY


class TestPerformanceReport:
    def test_init_defaults(self):
        report = PerformanceReport(base_url="https://test.com", api_key="key")
        assert report.base_url == "https://test.com"
        assert report.api_key == "key"

    @patch("zhihuiti.performance_report.httpx.Client")
    def test_collect_all_with_registered_agents(self, mock_client_class):
        mock_client = MagicMock()

        def mock_get(url):
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            if "leaderboard" in url:
                resp.json.return_value = []
            elif "portfolio" in url:
                resp.json.return_value = {
                    "cashBalance": 80000,
                    "totalEquity": 105000,
                    "positions": [{"pair": "BTC/USD", "side": "buy", "quantity": 0.1}],
                }
            elif "trades" in url:
                resp.json.return_value = [
                    {"pair": "BTC/USD", "side": "buy", "quantity": 0.1},
                ]
            return resp

        mock_client.get.side_effect = mock_get
        mock_client_class.return_value = mock_client

        report = PerformanceReport(base_url="https://test.com")
        data = report.collect_all()

        assert len(data["agents"]) == 21
        # All agents should be registered (mock returns non-zero equity)
        registered = [a for a in data["agents"].values() if a["registered"]]
        assert len(registered) == 21
        assert registered[0]["equity"] == 105000
        assert registered[0]["pnl"] == 5000
        assert registered[0]["return_pct"] == 5.0

    @patch("zhihuiti.performance_report.httpx.Client")
    def test_generate_strategy_stats(self, mock_client_class):
        mock_client = MagicMock()

        def mock_get(url):
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            if "leaderboard" in url:
                resp.json.return_value = []
            elif "portfolio" in url:
                resp.json.return_value = {
                    "cashBalance": 90000,
                    "totalEquity": 110000,
                    "positions": [],
                }
            elif "trades" in url:
                resp.json.return_value = []
            return resp

        mock_client.get.side_effect = mock_get
        mock_client_class.return_value = mock_client

        rpt = PerformanceReport(base_url="https://test.com")
        result = rpt.generate()

        assert "strategy_stats" in result
        assert "momentum" in result["strategy_stats"]
        assert "mean_reversion" in result["strategy_stats"]
        assert "accumulate" in result["strategy_stats"]
        assert "scalp" in result["strategy_stats"]
        assert "diversify" in result["strategy_stats"]

        # 5 momentum agents
        assert result["strategy_stats"]["momentum"]["count"] == 5
        assert result["strategy_stats"]["momentum"]["avg_return"] == 10.0

        # Fleet totals
        fleet = result["fleet"]
        assert fleet["registered"] == 21
        assert fleet["total_equity"] == 21 * 110000

    @patch("zhihuiti.performance_report.httpx.Client")
    def test_generate_no_registered_agents(self, mock_client_class):
        mock_client = MagicMock()

        def mock_get(url):
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            if "leaderboard" in url:
                resp.json.return_value = []
            elif "portfolio" in url:
                resp.json.return_value = {"cashBalance": 0, "totalEquity": 0, "positions": []}
            elif "trades" in url:
                resp.json.return_value = []
            return resp

        mock_client.get.side_effect = mock_get
        mock_client_class.return_value = mock_client

        rpt = PerformanceReport(base_url="https://test.com")
        result = rpt.generate()
        assert "error" in result

    @patch("zhihuiti.performance_report.httpx.Client")
    def test_export_json(self, mock_client_class):
        mock_client = MagicMock()

        def mock_get(url):
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            if "leaderboard" in url:
                resp.json.return_value = []
            elif "portfolio" in url:
                resp.json.return_value = {
                    "cashBalance": 50000,
                    "totalEquity": 100000,
                    "positions": [],
                }
            elif "trades" in url:
                resp.json.return_value = []
            return resp

        mock_client.get.side_effect = mock_get
        mock_client_class.return_value = mock_client

        rpt = PerformanceReport(base_url="https://test.com")
        json_str = rpt.export_json()

        import json
        data = json.loads(json_str)
        assert "fleet" in data
        assert "strategy_stats" in data

    @patch("zhihuiti.performance_report.httpx.Client")
    def test_ranked_agents_sorted_by_return(self, mock_client_class):
        mock_client = MagicMock()
        call_count = {"n": 0}

        def mock_get(url):
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            if "leaderboard" in url:
                resp.json.return_value = []
            elif "portfolio" in url:
                # Alternate between profit and loss
                call_count["n"] += 1
                equity = 110000 if call_count["n"] % 2 == 0 else 90000
                resp.json.return_value = {
                    "cashBalance": 50000,
                    "totalEquity": equity,
                    "positions": [],
                }
            elif "trades" in url:
                resp.json.return_value = []
            return resp

        mock_client.get.side_effect = mock_get
        mock_client_class.return_value = mock_client

        rpt = PerformanceReport(base_url="https://test.com")
        result = rpt.generate()
        ranked = result["ranked_agents"]

        # Best should be first
        assert ranked[0]["return_pct"] >= ranked[-1]["return_pct"]
