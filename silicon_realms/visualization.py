from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker


def plot_simulation(history: dict, output_path: str = "simulation_results.png"):
    """Generate a multi-panel chart from simulation history data."""
    ticks = history["ticks"]
    if len(ticks) < 2:
        return

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Silicon Realms - Simulation Results", fontsize=16, fontweight="bold")

    # --- Panel 1: Token Supply ---
    ax = axes[0, 0]
    ax.plot(ticks, history["total_supply"], label="Total Supply", linewidth=2, color="#2196F3")
    ax.plot(ticks, history["circulating"], label="Circulating", linewidth=2, color="#4CAF50")
    ax.plot(ticks, history["staked"], label="Staked", linewidth=2, color="#FF9800")
    ax.set_title("Token Economics")
    ax.set_xlabel("Tick")
    ax.set_ylabel("SiCoin")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    # --- Panel 2: Gini Coefficient ---
    ax = axes[0, 1]
    ax.plot(ticks, history["gini"], linewidth=2, color="#E91E63")
    ax.set_title("Wealth Inequality (Gini Coefficient)")
    ax.set_xlabel("Tick")
    ax.set_ylabel("Gini")
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0.4, color="gray", linestyle="--", alpha=0.5, label="High inequality threshold")
    ax.legend(loc="upper right", fontsize=8)

    # --- Panel 3: Realm Populations ---
    ax = axes[1, 0]
    realm_names = sorted(history["realm_population"][0].keys())
    for realm in realm_names:
        pops = [rp.get(realm, 0) for rp in history["realm_population"]]
        ax.plot(ticks, pops, label=realm.capitalize(), linewidth=2)
    ax.set_title("Realm Populations")
    ax.set_xlabel("Tick")
    ax.set_ylabel("Agents")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)

    # --- Panel 4: Strategy Performance (avg wealth over time) ---
    ax = axes[1, 1]
    strategies = sorted(history["strategy_wealth"][0].keys())
    colors = {"balanced": "#2196F3", "greedy": "#F44336", "nomad": "#9C27B0", "staker": "#FF9800"}
    for strat in strategies:
        avgs = [sw.get(strat, 0) for sw in history["strategy_wealth"]]
        ax.plot(ticks, avgs, label=strat.capitalize(), linewidth=2,
                color=colors.get(strat, None))
    ax.set_title("Strategy Performance (Avg Wealth)")
    ax.set_xlabel("Tick")
    ax.set_ylabel("Avg SiCoin per Agent")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"\n  Chart saved to {output_path}")
    plt.close(fig)
