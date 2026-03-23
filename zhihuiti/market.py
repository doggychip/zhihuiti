"""Trading Market (交易市场) — agents freely trade tokens and services, creating market prices.

A decentralized marketplace where agents can:
1. Post BUY orders: "I need a coder, willing to pay X tokens"
2. Post SELL orders: "I offer coding services for X tokens"
3. Orders are matched by price priority (best price first), then time priority
4. Matched trades execute automatically, transferring tokens between agents
5. Market prices emerge from supply and demand

This creates a price-discovery mechanism for agent services, complementing
the auction system (which sets prices via competitive bidding for specific tasks).
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from zhihuiti.economy import Transaction, TransactionType
from zhihuiti.relationships import RelationType

if TYPE_CHECKING:
    from zhihuiti.memory import Memory
    from zhihuiti.models import AgentState

console = Console()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_ORDER_BOOK_DEPTH = 200       # Max open orders per service role
RECENT_TRADES_WINDOW = 20        # Number of recent trades used for market price
MIN_TRADE_PRICE = 1.0            # Floor price to prevent race-to-zero
MIN_TRADE_QUANTITY = 1            # Minimum quantity per order


class OrderType(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"


@dataclass
class MarketOrder:
    """A single buy or sell order on the trading market."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    agent_id: str = ""
    order_type: OrderType = OrderType.BUY
    service_role: str = ""          # The role/service being traded (e.g. "coder", "reviewer")
    price: float = 0.0              # Price per unit in tokens
    quantity: int = 1               # Number of service units
    status: OrderStatus = OrderStatus.OPEN
    filled_by: str | None = None    # Agent ID that filled this order
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class TradeRecord:
    """A completed trade between two agents."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    buyer_id: str = ""
    seller_id: str = ""
    service_role: str = ""
    price: float = 0.0
    quantity: int = 1
    total: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TradingMarket:
    """Decentralized marketplace for agent service trading.

    Agents post buy/sell orders for service roles. The matching engine
    pairs compatible orders by best price, then earliest time. Executed
    trades transfer tokens between agents and record the relationship.
    """

    def __init__(self, memory: Memory):
        self.memory = memory
        self.orders: list[MarketOrder] = []
        self.trade_history: list[TradeRecord] = []
        # service_role -> list of trade prices (most recent last)
        self.price_history: dict[str, list[float]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Order management
    # ------------------------------------------------------------------

    def place_order(
        self,
        agent: AgentState,
        order_type: OrderType,
        service_role: str,
        price: float,
        quantity: int = 1,
    ) -> MarketOrder | None:
        """Place a buy or sell order on the market.

        Validates that:
        - Price >= MIN_TRADE_PRICE
        - Quantity >= MIN_TRADE_QUANTITY
        - For BUY orders: agent has sufficient budget to cover total cost
        - Agent is alive
        """
        if price < MIN_TRADE_PRICE:
            console.print(
                f"  [red]Order rejected:[/red] price {price:.1f} < "
                f"minimum {MIN_TRADE_PRICE:.1f}"
            )
            return None

        if quantity < MIN_TRADE_QUANTITY:
            console.print(
                f"  [red]Order rejected:[/red] quantity {quantity} < "
                f"minimum {MIN_TRADE_QUANTITY}"
            )
            return None

        if not agent.alive:
            console.print(f"  [red]Order rejected:[/red] agent {agent.id[:8]} is dead")
            return None

        total_cost = price * quantity
        if order_type == OrderType.BUY and agent.budget < total_cost:
            console.print(
                f"  [red]Order rejected:[/red] insufficient budget "
                f"({agent.budget:.1f} < {total_cost:.1f})"
            )
            return None

        # Check order book depth
        role_orders = [
            o for o in self.orders
            if o.service_role == service_role and o.status == OrderStatus.OPEN
        ]
        if len(role_orders) >= MAX_ORDER_BOOK_DEPTH:
            console.print(
                f"  [red]Order rejected:[/red] order book full for {service_role}"
            )
            return None

        order = MarketOrder(
            agent_id=agent.id,
            order_type=order_type,
            service_role=service_role,
            price=round(price, 2),
            quantity=quantity,
        )
        self.orders.append(order)

        side = "BUY" if order_type == OrderType.BUY else "SELL"
        console.print(
            f"  [cyan]📋 {side}:[/cyan] {agent.id[:8]} — "
            f"{quantity}x {service_role} @ {price:.1f} tokens"
        )

        return order

    def cancel_order(self, order_id: str, agent_id: str) -> bool:
        """Cancel an open order. Only the placing agent can cancel."""
        for order in self.orders:
            if order.id == order_id:
                if order.agent_id != agent_id:
                    console.print(f"  [red]Cannot cancel:[/red] not your order")
                    return False
                if order.status != OrderStatus.OPEN:
                    console.print(
                        f"  [red]Cannot cancel:[/red] order is {order.status.value}"
                    )
                    return False
                order.status = OrderStatus.CANCELLED
                console.print(
                    f"  [dim]Order {order_id} cancelled by {agent_id[:8]}[/dim]"
                )
                return True
        console.print(f"  [red]Order {order_id} not found[/red]")
        return False

    # ------------------------------------------------------------------
    # Matching engine
    # ------------------------------------------------------------------

    def match_orders(self, service_role: str | None = None) -> list[tuple[MarketOrder, MarketOrder]]:
        """Match buy and sell orders for a service role (or all roles).

        Matching rules:
        - Buy price >= Sell price (buyer willing to pay at least what seller asks)
        - Price priority: highest buy matched with lowest sell first
        - Time priority: among equal prices, earlier orders match first
        - Trade executes at the sell (ask) price

        Returns list of (buy_order, sell_order) matched pairs.
        """
        roles = [service_role] if service_role else list(self._get_active_roles())
        matched_pairs: list[tuple[MarketOrder, MarketOrder]] = []

        for role in roles:
            buys = sorted(
                [
                    o for o in self.orders
                    if o.service_role == role
                    and o.order_type == OrderType.BUY
                    and o.status == OrderStatus.OPEN
                ],
                key=lambda o: (-o.price, o.created_at),  # Highest price first, then earliest
            )
            sells = sorted(
                [
                    o for o in self.orders
                    if o.service_role == role
                    and o.order_type == OrderType.SELL
                    and o.status == OrderStatus.OPEN
                ],
                key=lambda o: (o.price, o.created_at),  # Lowest price first, then earliest
            )

            buy_idx = 0
            sell_idx = 0
            while buy_idx < len(buys) and sell_idx < len(sells):
                buy = buys[buy_idx]
                sell = sells[sell_idx]

                # Cannot self-trade
                if buy.agent_id == sell.agent_id:
                    sell_idx += 1
                    continue

                # Match if buy price >= sell price
                if buy.price >= sell.price:
                    matched_pairs.append((buy, sell))
                    buy_idx += 1
                    sell_idx += 1
                else:
                    # No more matches possible (buy prices only decrease,
                    # sell prices only increase from here)
                    break

        return matched_pairs

    def execute_trade(
        self,
        buy_order: MarketOrder,
        sell_order: MarketOrder,
        agents: dict[str, AgentState],
    ) -> TradeRecord | None:
        """Execute a matched trade: transfer tokens from buyer to seller.

        Trade price is the sell (ask) price. Buyer may get a better deal
        than their limit price.
        """
        buyer = agents.get(buy_order.agent_id)
        seller = agents.get(sell_order.agent_id)

        if buyer is None or seller is None:
            console.print("  [red]Trade failed:[/red] agent not found")
            return None

        if not buyer.alive or not seller.alive:
            console.print("  [red]Trade failed:[/red] agent is dead")
            return None

        # Trade executes at the sell (ask) price
        trade_price = sell_order.price
        trade_qty = min(buy_order.quantity, sell_order.quantity)
        total = round(trade_price * trade_qty, 2)

        # Verify buyer can still afford it
        if buyer.budget < total:
            console.print(
                f"  [red]Trade failed:[/red] buyer {buyer.id[:8]} "
                f"budget {buyer.budget:.1f} < {total:.1f}"
            )
            buy_order.status = OrderStatus.CANCELLED
            return None

        # Transfer tokens
        buyer.budget -= total
        seller.budget += total

        # Update order statuses
        buy_order.status = OrderStatus.FILLED
        buy_order.filled_by = seller.id
        sell_order.status = OrderStatus.FILLED
        sell_order.filled_by = buyer.id

        # Record the trade
        trade = TradeRecord(
            buyer_id=buyer.id,
            seller_id=seller.id,
            service_role=sell_order.service_role,
            price=trade_price,
            quantity=trade_qty,
            total=total,
        )
        self.trade_history.append(trade)
        self.price_history[sell_order.service_role].append(trade_price)

        # Record transaction in economy ledger
        self.memory.record_transaction(Transaction(
            tx_type=TransactionType.TRANSFER,
            from_entity=buyer.id,
            to_entity=seller.id,
            amount=total,
            memo=(
                f"Market trade {trade.id}: {trade_qty}x {sell_order.service_role} "
                f"@ {trade_price:.1f}"
            ),
        ))

        # Save economy state
        self.memory.save_economy_state("trading_market", {
            "total_trades": len(self.trade_history),
            "total_volume": sum(t.total for t in self.trade_history),
        })

        console.print(
            f"  [bold green]💱 Trade:[/bold green] {buyer.id[:8]} → {seller.id[:8]} "
            f"{trade_qty}x {sell_order.service_role} @ {trade_price:.1f} "
            f"(total {total:.1f} tokens)"
        )

        return trade

    def run_matching(self, agents: dict[str, AgentState],
                     service_role: str | None = None) -> list[TradeRecord]:
        """Full matching cycle: find matches and execute all trades.

        Returns list of completed trades.
        """
        pairs = self.match_orders(service_role)
        trades: list[TradeRecord] = []

        for buy_order, sell_order in pairs:
            trade = self.execute_trade(buy_order, sell_order, agents)
            if trade is not None:
                trades.append(trade)

        if trades:
            console.print(
                f"  [dim]Matched {len(trades)} trade(s) "
                f"across {len({t.service_role for t in trades})} role(s)[/dim]"
            )

        return trades

    # ------------------------------------------------------------------
    # Price discovery
    # ------------------------------------------------------------------

    def get_market_price(self, service_role: str) -> float | None:
        """Current market price for a service role.

        Calculated as the average price of the most recent trades.
        Returns None if no trades have occurred for this role.
        """
        history = self.price_history.get(service_role, [])
        if not history:
            return None
        recent = history[-RECENT_TRADES_WINDOW:]
        return round(sum(recent) / len(recent), 2)

    def get_best_bid(self, service_role: str) -> float | None:
        """Highest open buy price for a service role."""
        buys = [
            o.price for o in self.orders
            if o.service_role == service_role
            and o.order_type == OrderType.BUY
            and o.status == OrderStatus.OPEN
        ]
        return max(buys) if buys else None

    def get_best_ask(self, service_role: str) -> float | None:
        """Lowest open sell price for a service role."""
        sells = [
            o.price for o in self.orders
            if o.service_role == service_role
            and o.order_type == OrderType.SELL
            and o.status == OrderStatus.OPEN
        ]
        return min(sells) if sells else None

    def get_spread(self, service_role: str) -> float | None:
        """Bid-ask spread for a service role."""
        bid = self.get_best_bid(service_role)
        ask = self.get_best_ask(service_role)
        if bid is not None and ask is not None:
            return round(ask - bid, 2)
        return None

    # ------------------------------------------------------------------
    # Statistics and reporting
    # ------------------------------------------------------------------

    def _get_active_roles(self) -> set[str]:
        """Get all service roles with open orders."""
        return {
            o.service_role for o in self.orders
            if o.status == OrderStatus.OPEN
        }

    def get_stats(self) -> dict:
        """Market-wide statistics."""
        open_orders = [o for o in self.orders if o.status == OrderStatus.OPEN]
        filled_orders = [o for o in self.orders if o.status == OrderStatus.FILLED]
        total_volume = sum(t.total for t in self.trade_history)
        roles_traded = {t.service_role for t in self.trade_history}

        # Per-role market prices
        market_prices: dict[str, float | None] = {}
        for role in roles_traded | self._get_active_roles():
            market_prices[role] = self.get_market_price(role)

        return {
            "total_orders": len(self.orders),
            "open_orders": len(open_orders),
            "filled_orders": len(filled_orders),
            "cancelled_orders": len(self.orders) - len(open_orders) - len(filled_orders),
            "total_trades": len(self.trade_history),
            "total_volume": round(total_volume, 2),
            "roles_traded": len(roles_traded),
            "market_prices": market_prices,
        }

    def print_report(self) -> None:
        """Print market summary report."""
        stats = self.get_stats()

        table = Table(title="Trading Market", show_header=False,
                      box=None, padding=(0, 2))
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        table.add_row("Total Orders", str(stats["total_orders"]))
        table.add_row("  Open", f"[cyan]{stats['open_orders']}[/cyan]")
        table.add_row("  Filled", f"[green]{stats['filled_orders']}[/green]")
        table.add_row("  Cancelled", str(stats["cancelled_orders"]))
        table.add_row("", "")
        table.add_row("Total Trades", str(stats["total_trades"]))
        table.add_row("Total Volume", f"{stats['total_volume']:.1f} tokens")
        table.add_row("Roles Traded", str(stats["roles_traded"]))

        if stats["market_prices"]:
            table.add_row("", "")
            for role, price in sorted(stats["market_prices"].items()):
                price_str = f"{price:.1f}" if price is not None else "—"
                table.add_row(f"  {role}", price_str)

        console.print(Panel(table, title="💱 Trading Market"))

    def print_orderbook(self, service_role: str | None = None) -> None:
        """Print the current order book for a service role (or all roles)."""
        roles = [service_role] if service_role else sorted(self._get_active_roles())

        if not roles:
            console.print("  [dim]No open orders.[/dim]")
            return

        for role in roles:
            buys = sorted(
                [
                    o for o in self.orders
                    if o.service_role == role
                    and o.order_type == OrderType.BUY
                    and o.status == OrderStatus.OPEN
                ],
                key=lambda o: -o.price,
            )
            sells = sorted(
                [
                    o for o in self.orders
                    if o.service_role == role
                    and o.order_type == OrderType.SELL
                    and o.status == OrderStatus.OPEN
                ],
                key=lambda o: o.price,
            )

            table = Table(title=f"Order Book: {role}")
            table.add_column("Side", style="bold")
            table.add_column("Agent", style="dim")
            table.add_column("Price", justify="right")
            table.add_column("Qty", justify="center")
            table.add_column("ID", style="dim")

            # Sells first (ascending price — best ask at top)
            for o in reversed(sells):
                table.add_row(
                    "[red]SELL[/red]", o.agent_id[:8],
                    f"{o.price:.1f}", str(o.quantity), o.id,
                )

            # Separator
            spread = self.get_spread(role)
            spread_str = f"spread={spread:.1f}" if spread is not None else "—"
            market_price = self.get_market_price(role)
            mp_str = f"mkt={market_price:.1f}" if market_price is not None else ""
            table.add_row(
                f"[dim]---[/dim]", f"[dim]{spread_str}[/dim]",
                f"[dim]{mp_str}[/dim]", "", "",
            )

            # Buys (descending price — best bid at top)
            for o in buys:
                table.add_row(
                    "[green]BUY[/green]", o.agent_id[:8],
                    f"{o.price:.1f}", str(o.quantity), o.id,
                )

            console.print(table)

    def print_price_history(self, service_role: str | None = None) -> None:
        """Print price history for a service role (or all roles)."""
        roles = (
            [service_role] if service_role
            else sorted(self.price_history.keys())
        )

        if not roles:
            console.print("  [dim]No trade history yet.[/dim]")
            return

        for role in roles:
            prices = self.price_history.get(role, [])
            if not prices:
                console.print(f"  [dim]No trades for {role}.[/dim]")
                continue

            table = Table(title=f"Price History: {role}")
            table.add_column("#", style="dim", justify="right")
            table.add_column("Price", justify="right")
            table.add_column("Change", justify="right")

            prev = None
            for i, p in enumerate(prices, 1):
                if prev is not None:
                    delta = p - prev
                    sign = "+" if delta >= 0 else ""
                    color = "green" if delta >= 0 else "red"
                    change_str = f"[{color}]{sign}{delta:.1f}[/{color}]"
                else:
                    change_str = "—"
                table.add_row(str(i), f"{p:.1f}", change_str)
                prev = p

            avg_price = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices)

            console.print(table)
            console.print(
                f"  [dim]{role}: {len(prices)} trades | "
                f"avg={avg_price:.1f} | min={min_price:.1f} | max={max_price:.1f}[/dim]"
            )
