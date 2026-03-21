"""Custom tools that let CrewAI agents interact with the token economy."""

from __future__ import annotations

from crewai.tools import tool

# Shared ledger — a simple in-memory store that tracks balances and transactions.
# In production you'd swap this for a database.
_economy = {
    "balances": {},
    "staked": {},
    "transactions": [],
    "total_supply": 0.0,
}


def get_economy() -> dict:
    return _economy


def reset_economy(initial_budgets: dict[str, float] | None = None):
    """Reset the economy, optionally seeding agent budgets."""
    _economy["balances"] = {}
    _economy["staked"] = {}
    _economy["transactions"] = []
    _economy["total_supply"] = 0.0
    if initial_budgets:
        for agent_name, amount in initial_budgets.items():
            _economy["balances"][agent_name] = amount
            _economy["total_supply"] += amount


# ---- Tools exposed to CrewAI agents ----

@tool("Check Balance")
def check_balance(agent_name: str) -> str:
    """Check the SiCoin balance and staked amount for an agent."""
    bal = _economy["balances"].get(agent_name, 0.0)
    stk = _economy["staked"].get(agent_name, 0.0)
    return f"{agent_name}: {bal:.1f} SiCoin available, {stk:.1f} staked, {bal + stk:.1f} total"


@tool("Transfer Tokens")
def transfer_tokens(sender: str, receiver: str, amount: float) -> str:
    """Transfer SiCoin from one agent to another. A 1% fee is burned."""
    fee = amount * 0.01
    total_cost = amount + fee
    bal = _economy["balances"].get(sender, 0.0)
    if bal < total_cost:
        return f"Transfer failed: {sender} has {bal:.1f} but needs {total_cost:.1f}"
    _economy["balances"][sender] = bal - total_cost
    _economy["balances"][receiver] = _economy["balances"].get(receiver, 0.0) + amount
    _economy["total_supply"] -= fee
    _economy["transactions"].append({
        "type": "transfer", "from": sender, "to": receiver,
        "amount": amount, "fee": fee,
    })
    return f"Transferred {amount:.1f} SiCoin from {sender} to {receiver} (fee: {fee:.2f} burned)"


@tool("Stake Tokens")
def stake_tokens(agent_name: str, amount: float) -> str:
    """Stake SiCoin to earn rewards. Minimum stake is 10 SiCoin."""
    if amount < 10:
        return f"Stake failed: minimum is 10 SiCoin, got {amount:.1f}"
    bal = _economy["balances"].get(agent_name, 0.0)
    if bal < amount:
        return f"Stake failed: {agent_name} has {bal:.1f} but wants to stake {amount:.1f}"
    _economy["balances"][agent_name] = bal - amount
    _economy["staked"][agent_name] = _economy["staked"].get(agent_name, 0.0) + amount
    _economy["transactions"].append({
        "type": "stake", "agent": agent_name, "amount": amount,
    })
    return f"{agent_name} staked {amount:.1f} SiCoin"


@tool("View Economy Summary")
def view_economy_summary() -> str:
    """Get a summary of the current token economy state."""
    balances = _economy["balances"]
    staked = _economy["staked"]
    all_agents = set(list(balances.keys()) + list(staked.keys()))
    if not all_agents:
        return "Economy is empty — no agents registered."

    lines = ["=== Economy Summary ==="]
    lines.append(f"Total supply: {_economy['total_supply']:.1f} SiCoin")
    lines.append(f"Transactions: {len(_economy['transactions'])}")
    lines.append("")
    lines.append("Agent balances:")
    for name in sorted(all_agents):
        b = balances.get(name, 0.0)
        s = staked.get(name, 0.0)
        lines.append(f"  {name}: {b:.1f} available, {s:.1f} staked")
    return "\n".join(lines)


@tool("Award Tokens")
def award_tokens(agent_name: str, amount: float, reason: str) -> str:
    """Award SiCoin to an agent for completing work. Used by the management realm."""
    _economy["balances"][agent_name] = _economy["balances"].get(agent_name, 0.0) + amount
    _economy["total_supply"] += amount
    _economy["transactions"].append({
        "type": "award", "agent": agent_name, "amount": amount, "reason": reason,
    })
    return f"Awarded {amount:.1f} SiCoin to {agent_name} for: {reason}"
