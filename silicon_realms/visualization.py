"""
Simulation Visualization
========================
Multi-panel matplotlib charts for Silicon Realms simulation history.

Panel layout (4×2):
  Row 1: Token Supply | Gini Coefficient
  Row 2: Strategy Frequency Evolution (Replicator) | Strategy Performance (Wealth)
  Row 3: Temperature & Entropy (StatMech) | Bellman Values per Realm
  Row 4: Avalanche Distribution (SOC) | Phase Diagram (T vs H)
"""
from __future__ import annotations

import math
from pathlib import Path
from collections import Counter

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np


# Consistent color palettes
STRATEGY_COLORS = {
    "balanced": "#2196F3",
    "greedy": "#F44336",
    "nomad": "#9C27B0",
    "staker": "#FF9800",
}

REALM_COLORS = {
    "compute": "#00BCD4",
    "data": "#4CAF50",
    "governance": "#FF5722",
}

THERMO_COLORS = {
    "temperature": "#F44336",
    "entropy": "#2196F3",
}


def _get_color(name: str, palette: dict, fallback_idx: int = 0) -> str:
    if name in palette:
        return palette[name]
    fallbacks = ["#607D8B", "#795548", "#009688", "#3F51B5", "#CDDC39", "#E91E63"]
    return fallbacks[fallback_idx % len(fallbacks)]


def plot_simulation(history: dict, output_path: str = "simulation_results.png"):
    """Generate an 8-panel chart from simulation history data."""
    ticks = history["ticks"]
    if len(ticks) < 2:
        return

    fig, axes = plt.subplots(4, 2, figsize=(16, 22))
    fig.suptitle(
        "Silicon Realms — Simulation Dashboard",
        fontsize=18, fontweight="bold", y=0.995,
    )
    fig.patch.set_facecolor("#fafafa")

    # ── Panel 1: Token Supply ──────────────────────────────────────────────
    ax = axes[0, 0]
    ax.plot(ticks, history["total_supply"], label="Total Supply", lw=2, color="#2196F3")
    ax.plot(ticks, history["circulating"], label="Circulating", lw=2, color="#4CAF50")
    ax.plot(ticks, history["staked"], label="Staked", lw=2, color="#FF9800")
    ax.set_title("Token Economics", fontweight="bold")
    ax.set_xlabel("Tick")
    ax.set_ylabel("SiCoin")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    # ── Panel 2: Gini Coefficient ──────────────────────────────────────────
    ax = axes[0, 1]
    ax.plot(ticks, history["gini"], lw=2, color="#E91E63")
    ax.fill_between(ticks, history["gini"], alpha=0.15, color="#E91E63")
    ax.set_title("Wealth Inequality (Gini)", fontweight="bold")
    ax.set_xlabel("Tick")
    ax.set_ylabel("Gini Coefficient")
    ax.set_ylim(0, 1)
    ax.axhline(y=0.4, color="gray", ls="--", alpha=0.5, label="High inequality")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)

    # ── Panel 3: Strategy Frequency Evolution (Replicator Dynamics) ────────
    ax = axes[1, 0]
    if history.get("strategy_freq") and history["strategy_freq"]:
        all_strats = sorted(set(
            s for sf in history["strategy_freq"] for s in sf.keys()
        ))
        freq_data = {s: [] for s in all_strats}
        for sf in history["strategy_freq"]:
            for s in all_strats:
                freq_data[s].append(sf.get(s, 0.0))

        # Stacked area plot
        bottom = [0.0] * len(ticks)
        for i, s in enumerate(all_strats):
            vals = freq_data[s]
            color = _get_color(s, STRATEGY_COLORS, i)
            ax.fill_between(ticks, bottom, [b + v for b, v in zip(bottom, vals)],
                            alpha=0.7, label=s.capitalize(), color=color)
            bottom = [b + v for b, v in zip(bottom, vals)]

        ax.set_ylim(0, 1.05)
        ax.set_title("Strategy Frequencies (Replicator Dynamics)", fontweight="bold")
        ax.set_xlabel("Tick")
        ax.set_ylabel("Frequency")
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(True, alpha=0.3)

        # Annotate: dxᵢ/dt = xᵢ(fᵢ − φ̄)
        ax.text(0.02, 0.02, r"$\dot{x}_i = x_i(f_i - \bar{\varphi})$",
                transform=ax.transAxes, fontsize=9, color="#555",
                fontstyle="italic", verticalalignment="bottom")
    else:
        ax.text(0.5, 0.5, "No strategy frequency data", ha="center", va="center",
                transform=ax.transAxes, color="#999")
        ax.set_title("Strategy Frequencies (Replicator Dynamics)", fontweight="bold")

    # ── Panel 4: Strategy Performance (Avg Wealth) ─────────────────────────
    ax = axes[1, 1]
    if history.get("strategy_wealth") and history["strategy_wealth"]:
        all_strats = sorted(set(
            s for sw in history["strategy_wealth"] for s in sw.keys()
        ))
        for i, strat in enumerate(all_strats):
            avgs = [sw.get(strat, 0) for sw in history["strategy_wealth"]]
            color = _get_color(strat, STRATEGY_COLORS, i)
            ax.plot(ticks, avgs, label=strat.capitalize(), lw=2, color=color)
        ax.set_title("Strategy Performance (Avg Wealth)", fontweight="bold")
        ax.set_xlabel("Tick")
        ax.set_ylabel("Avg SiCoin per Agent")
        ax.legend(loc="upper left", fontsize=8)
        ax.grid(True, alpha=0.3)
    else:
        ax.text(0.5, 0.5, "No strategy data", ha="center", va="center",
                transform=ax.transAxes, color="#999")
        ax.set_title("Strategy Performance", fontweight="bold")

    # ── Panel 5: Temperature & Entropy (Statistical Mechanics) ─────────────
    ax = axes[2, 0]
    if history.get("temperature") and history.get("entropy"):
        ax_t = ax
        ax_e = ax.twinx()

        ln1 = ax_t.plot(ticks, history["temperature"], lw=2,
                        color=THERMO_COLORS["temperature"], label="Temperature (T)")
        ax_t.fill_between(ticks, history["temperature"], alpha=0.1,
                          color=THERMO_COLORS["temperature"])
        ax_t.set_ylabel("Temperature T = σ/μ", color=THERMO_COLORS["temperature"])
        ax_t.tick_params(axis="y", labelcolor=THERMO_COLORS["temperature"])

        ln2 = ax_e.plot(ticks, history["entropy"], lw=2,
                        color=THERMO_COLORS["entropy"], label="Entropy (H)", ls="--")
        ax_e.set_ylabel("Entropy H = −Σ pᵢ log pᵢ", color=THERMO_COLORS["entropy"])
        ax_e.tick_params(axis="y", labelcolor=THERMO_COLORS["entropy"])

        lns = ln1 + ln2
        labs = [l.get_label() for l in lns]
        ax_t.legend(lns, labs, loc="upper right", fontsize=8)
        ax_t.set_title("Economic Thermodynamics", fontweight="bold")
        ax_t.set_xlabel("Tick")
        ax_t.grid(True, alpha=0.3)

        # Annotate equation
        ax_t.text(0.02, 0.02, r"$F = U - TS$",
                  transform=ax_t.transAxes, fontsize=9, color="#555",
                  fontstyle="italic", verticalalignment="bottom")
    else:
        ax.text(0.5, 0.5, "No thermodynamic data", ha="center", va="center",
                transform=ax.transAxes, color="#999")
        ax.set_title("Economic Thermodynamics", fontweight="bold")

    # ── Panel 6: Bellman Values per Realm ──────────────────────────────────
    ax = axes[2, 1]
    if history.get("realm_values") and history["realm_values"]:
        all_realms = sorted(set(
            r for rv in history["realm_values"] for r in rv.keys()
        ))
        for i, realm in enumerate(all_realms):
            vals = [rv.get(realm, 0.0) for rv in history["realm_values"]]
            color = _get_color(realm, REALM_COLORS, i)
            ax.plot(ticks, vals, label=f"V({realm})", lw=2, color=color)

        ax.axhline(y=0, color="gray", ls="-", alpha=0.3)
        ax.set_title("Bellman Value Function V(realm)", fontweight="bold")
        ax.set_xlabel("Tick")
        ax.set_ylabel("V(realm)")
        ax.legend(loc="best", fontsize=8)
        ax.grid(True, alpha=0.3)

        # Annotate equation
        ax.text(0.02, 0.02,
                r"$V(s) \leftarrow V(s) + \alpha[r + \gamma V(s') - V(s)]$",
                transform=ax.transAxes, fontsize=9, color="#555",
                fontstyle="italic", verticalalignment="bottom")
    else:
        ax.text(0.5, 0.5, "No Bellman value data", ha="center", va="center",
                transform=ax.transAxes, color="#999")
        ax.set_title("Bellman Values", fontweight="bold")

    # ── Panel 7: Avalanche Distribution (SOC) ──────────────────────────────
    ax = axes[3, 0]
    if history.get("avalanche"):
        avalanches = [a for a in history["avalanche"] if a > 0]
        if avalanches:
            # Time series of avalanche sizes
            ax_main = ax
            ax_main.bar(ticks, history["avalanche"], width=1.0, alpha=0.6,
                        color="#FF5722", label="Avalanche size")

            # Mark large avalanches
            mean_a = sum(avalanches) / len(avalanches)
            large_threshold = mean_a * 3
            for t, a in zip(ticks, history["avalanche"]):
                if a > large_threshold:
                    ax_main.annotate("!", (t, a), fontsize=8, color="red",
                                     ha="center", fontweight="bold")

            ax_main.set_title("Avalanche Events (SOC)", fontweight="bold")
            ax_main.set_xlabel("Tick")
            ax_main.set_ylabel("Max Wealth Drop")
            ax_main.legend(loc="upper right", fontsize=8)
            ax_main.grid(True, alpha=0.3)

            # Annotate
            ax_main.text(0.02, 0.95, f"P(s) ~ s⁻τ\n{len(avalanches)} events",
                         transform=ax_main.transAxes, fontsize=8, color="#555",
                         verticalalignment="top")
        else:
            ax.text(0.5, 0.5, "No avalanche events", ha="center", va="center",
                    transform=ax.transAxes, color="#999")
            ax.set_title("Avalanche Events (SOC)", fontweight="bold")
    else:
        ax.text(0.5, 0.5, "No avalanche data", ha="center", va="center",
                transform=ax.transAxes, color="#999")
        ax.set_title("Avalanche Events (SOC)", fontweight="bold")

    # ── Panel 8: Phase Diagram (Temperature vs Entropy) ────────────────────
    ax = axes[3, 1]
    if history.get("temperature") and history.get("entropy"):
        temps = history["temperature"]
        ents = history["entropy"]
        n = len(temps)

        # Color by time (early=blue, late=red)
        colors = plt.cm.coolwarm(np.linspace(0, 1, n))
        for i in range(n - 1):
            ax.plot(temps[i:i+2], ents[i:i+2], color=colors[i], lw=1.5, alpha=0.7)

        # Mark start and end
        ax.scatter([temps[0]], [ents[0]], color="#2196F3", s=80, zorder=5,
                   marker="o", edgecolors="white", linewidths=1.5, label="Start")
        ax.scatter([temps[-1]], [ents[-1]], color="#F44336", s=80, zorder=5,
                   marker="s", edgecolors="white", linewidths=1.5, label="End")

        ax.set_title("Phase Diagram (T vs H)", fontweight="bold")
        ax.set_xlabel("Temperature T")
        ax.set_ylabel("Entropy H")
        ax.legend(loc="best", fontsize=8)
        ax.grid(True, alpha=0.3)

        # Add colorbar for time
        sm = plt.cm.ScalarMappable(cmap=plt.cm.coolwarm,
                                   norm=plt.Normalize(vmin=0, vmax=n))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, pad=0.02)
        cbar.set_label("Tick", fontsize=8)
    else:
        ax.text(0.5, 0.5, "No phase data", ha="center", va="center",
                transform=ax.transAxes, color="#999")
        ax.set_title("Phase Diagram (T vs H)", fontweight="bold")

    plt.tight_layout(rect=[0, 0, 1, 0.98])
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"\n  Chart saved to {output_path}")
    plt.close(fig)
