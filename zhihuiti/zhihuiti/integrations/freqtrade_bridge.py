"""Freqtrade Bridge — backtesting engine and risk management.

Wraps freqtrade for strategy backtesting and hyperparameter optimization.
Gives agents the ability to evaluate trading strategies with historical data
and compute risk-adjusted performance metrics.

Integration points:
  - Strategy evaluation: backtest a strategy class over historical data
  - Hyperopt: optimize strategy parameters via freqtrade's hyperopt engine
  - Risk metrics: compute drawdown, Sharpe, Sortino, win rate from trade lists
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class FreqtradeBridge:
    """Bridge to freqtrade for backtesting and risk management."""

    def __init__(self, config_path: str | None = None):
        self._config_path = config_path
        self._available: bool | None = None
        self._ft_config: dict[str, Any] | None = None

    def is_available(self) -> bool:
        """Check if freqtrade is installed."""
        if self._available is not None:
            return self._available
        try:
            import freqtrade  # noqa: F401
            self._available = True
            return True
        except ImportError:
            self._available = False
            return False

    def _load_config(self) -> dict[str, Any]:
        """Lazily load freqtrade configuration."""
        if self._ft_config is not None:
            return self._ft_config
        if not self.is_available():
            return {}
        try:
            from freqtrade.configuration import Configuration  # type: ignore

            args: dict[str, Any] = {}
            if self._config_path:
                args["config"] = [self._config_path]
            self._ft_config = Configuration(args).get_config()
            return self._ft_config
        except Exception as e:
            logger.warning("freqtrade config load failed: %s", e)
            self._ft_config = {}
            return {}

    def backtest(
        self,
        strategy_class: str,
        timerange: str,
        pairs: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run a backtest for the given strategy.

        Args:
            strategy_class: Name of the strategy class to backtest.
            timerange: Date range string, e.g. "20230101-20231231".
            pairs: Optional list of trading pairs; uses config default if None.

        Returns:
            Dict with keys: profit, trades, drawdown, sharpe.
        """
        if not self.is_available():
            return {"error": "freqtrade not installed"}
        try:
            from freqtrade.commands.optimize_commands import start_backtesting  # type: ignore

            config = dict(self._load_config())
            config["strategy"] = strategy_class
            config["timerange"] = timerange
            if pairs:
                config["pairs"] = pairs
            config["dry_run"] = True

            result = start_backtesting(config)
            stats = result if isinstance(result, dict) else {}
            return {
                "profit": stats.get("profit_total", 0.0),
                "trades": stats.get("total_trades", 0),
                "drawdown": stats.get("max_drawdown", 0.0),
                "sharpe": stats.get("sharpe", 0.0),
            }
        except Exception as e:
            logger.warning("freqtrade backtest failed: %s", e)
            return {"error": str(e)}

    def optimize(
        self,
        strategy_class: str,
        param_space: dict[str, Any] | None = None,
        epochs: int = 100,
    ) -> dict[str, Any]:
        """Run hyperparameter optimization for a strategy.

        Args:
            strategy_class: Name of the strategy class.
            param_space: Optional parameter space overrides.
            epochs: Number of hyperopt epochs.

        Returns:
            Dict with best parameters and optimization metrics.
        """
        if not self.is_available():
            return {"error": "freqtrade not installed"}
        try:
            from freqtrade.commands.optimize_commands import start_hyperopt  # type: ignore

            config = dict(self._load_config())
            config["strategy"] = strategy_class
            config["epochs"] = epochs
            if param_space:
                config["hyperopt_params"] = param_space

            result = start_hyperopt(config)
            return result if isinstance(result, dict) else {"raw": str(result)}
        except Exception as e:
            logger.warning("freqtrade hyperopt failed: %s", e)
            return {"error": str(e)}

    def get_risk_metrics(self, trades: list[dict[str, Any]]) -> dict[str, float]:
        """Compute risk metrics from a list of trade results.

        Pure computation -- does not require freqtrade installation.

        Args:
            trades: List of trade dicts, each with at least 'profit_ratio' key.

        Returns:
            Dict with max_drawdown, sharpe, sortino, win_rate.
        """
        if not trades:
            return {"max_drawdown": 0.0, "sharpe": 0.0, "sortino": 0.0, "win_rate": 0.0}

        profits = [t.get("profit_ratio", 0.0) for t in trades]
        wins = sum(1 for p in profits if p > 0)
        win_rate = wins / len(profits) if profits else 0.0

        # Max drawdown from cumulative returns
        cumulative = 0.0
        peak = 0.0
        max_dd = 0.0
        for p in profits:
            cumulative += p
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_dd:
                max_dd = dd

        # Sharpe ratio (simplified: mean / std)
        mean_p = sum(profits) / len(profits)
        variance = sum((p - mean_p) ** 2 for p in profits) / len(profits)
        std_p = variance ** 0.5
        sharpe = mean_p / std_p if std_p > 0 else 0.0

        # Sortino ratio (downside deviation only)
        downside = [p for p in profits if p < 0]
        if downside:
            down_var = sum(p ** 2 for p in downside) / len(downside)
            down_std = down_var ** 0.5
            sortino = mean_p / down_std if down_std > 0 else 0.0
        else:
            sortino = float("inf") if mean_p > 0 else 0.0

        return {
            "max_drawdown": round(max_dd, 6),
            "sharpe": round(sharpe, 4),
            "sortino": round(sortino, 4),
            "win_rate": round(win_rate, 4),
        }


# Singleton for lazy initialization
_bridge: FreqtradeBridge | None = None


def get_bridge(config_path: str | None = None) -> FreqtradeBridge:
    """Get or create the global Freqtrade bridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = FreqtradeBridge(config_path=config_path)
    return _bridge
