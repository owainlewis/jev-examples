"""Long-only paper ledger. No exchange order API exists in this application."""

import math
import time

STARTING_CASH = 10000.0
FEE = 0.001
SLIPPAGE = 0.0005
TRADE_BUDGET = 1000.0
THRESHOLD = 0.75


class Engine:
    def __init__(self):
        self.cash = STARTING_CASH
        self.quantity = 0.0
        self.cost_basis = 0.0
        self.realized = 0.0
        self.fees = 0.0
        self.peak = STARTING_CASH
        self.drawdown = 0.0
        self.pending = None
        self.points = []
        self.events = []
        self.last = None
        self.baseline = None
        self.running = False
        self.generation = 0
        self.calls = 0
        self.latency = None
        self.probabilities = None
        self.choice = None

    def pause(self):
        self.running = False
        self.generation += 1
        if self.pending:
            self.pending["status"] = "Cancelled on pause"
        self.pending = None

    def quote(self, bid, ask, timestamp, received=None):
        received = time.time() if received is None else received
        if not all(math.isfinite(v) for v in (bid, ask, timestamp, received)):
            return False
        if bid <= 0 or ask < bid or abs(received - timestamp) > 10:
            return False
        if self.last and timestamp <= self.last["time"]:
            return False
        self.last = {"bid": bid, "ask": ask, "time": timestamp, "received": received}
        mid = (bid + ask) / 2
        # Only quotes after the completed decision can fill an order.
        if self.running and self.pending and timestamp > self.pending["decided_at"]:
            self.fill(bid, ask, timestamp)
        if self.running and self.baseline is None:
            self.baseline = STARTING_CASH / (ask * (1 + SLIPPAGE) * (1 + FEE))
        self.points.append({"time": timestamp, "price": mid})
        self.points = self.points[-600:]
        equity = self.equity()
        if self.running:
            self.peak = max(self.peak, equity)
            self.drawdown = max(self.drawdown, (self.peak - equity) / self.peak)
        return True

    def equity(self):
        exit_price = self.last["bid"] * (1 - SLIPPAGE) if self.last else 0
        return self.cash + self.quantity * exit_price * (1 - FEE)

    def decision(self, choice, probabilities, latency, now=None):
        now = time.time() if now is None else now
        if set(probabilities) != {"buy", "hold", "sell"}:
            raise ValueError("Invalid actions")
        if any(
            type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1
            for p in probabilities.values()
        ):
            raise ValueError("Invalid probabilities")
        if not math.isclose(sum(probabilities.values()), 1, abs_tol=0.02):
            raise ValueError("Invalid distribution")
        if choice not in probabilities or probabilities[choice] < max(
            probabilities.values()
        ):
            raise ValueError("Invalid selection")
        self.calls += 1
        self.latency = latency
        self.choice = choice
        self.probabilities = probabilities
        event = {
            "time": now,
            "decided_at": now,
            "action": choice,
            "probability": probabilities[choice],
            "latency": latency,
            "status": "Hold",
            "fill": None,
        }
        if not self.running:
            event["status"] = "Paused"
        elif not self.last or now - self.last["time"] > 10:
            event["status"] = "Blocked: stale data"
        elif probabilities[choice] < THRESHOLD:
            event["status"] = "Blocked: probability below 75%"
        elif choice == "buy" and self.quantity > 0:
            event["status"] = "Blocked: position already open"
        elif choice == "sell" and self.quantity == 0:
            event["status"] = "Blocked: no position"
        elif choice in ("buy", "sell"):
            event["status"] = "Waiting for next quote"
            self.pending = event
        self.events.insert(0, event)
        self.events = self.events[:100]
        return event

    def fill(self, bid, ask, timestamp):
        event = self.pending
        self.pending = None
        if timestamp - event["decided_at"] > 10:
            event["status"] = "Expired: no fresh quote"
            return
        if event["action"] == "buy":
            price = ask * (1 + SLIPPAGE)
            budget = min(TRADE_BUDGET, self.cash)
            self.quantity = budget / (price * (1 + FEE))
            fee = self.quantity * price * FEE
            self.cash -= budget
            self.cost_basis = budget
            quantity = self.quantity
        else:
            price = bid * (1 - SLIPPAGE)
            quantity = self.quantity
            fee = quantity * price * FEE
            proceeds = quantity * price - fee
            self.realized += proceeds - self.cost_basis
            self.cash += proceeds
            self.quantity = 0
            self.cost_basis = 0
        self.fees += fee
        event.update(
            status="Filled", fill=price, quantity=quantity, fee=fee, filled_at=timestamp
        )

    def features(self):
        prices = [p["price"] for p in self.points]
        recent = prices[-30:]
        return {
            "market": "BTC-USD",
            "mid_price": prices[-1],
            "change_percent_last_30_quotes": (recent[-1] / recent[0] - 1) * 100,
            "fast_mean_5_quotes": sum(prices[-5:]) / len(prices[-5:]),
            "slow_mean_30_quotes": sum(recent) / len(recent),
            "spread_percent": (self.last["ask"] / self.last["bid"] - 1) * 100,
            "position_open": self.quantity > 0,
            "cash_usd": self.cash,
            "sample_count": len(recent),
        }

    def snapshot(self):
        equity = self.equity()
        baseline_value = (
            self.baseline * self.last["bid"] * (1 - SLIPPAGE) * (1 - FEE)
            if self.baseline and self.last
            else STARTING_CASH
        )
        return {
            "cash": self.cash,
            "quantity": self.quantity,
            "equity": equity,
            "net_profit": equity - STARTING_CASH,
            "realized": self.realized,
            "unrealized": equity - self.cash - self.cost_basis,
            "fees": self.fees,
            "return_pct": (equity / STARTING_CASH - 1) * 100,
            "drawdown_pct": self.drawdown * 100,
            "benchmark_profit": baseline_value - STARTING_CASH,
            "running": self.running,
            "points": self.points,
            "events": self.events,
            "last": self.last,
            "calls": self.calls,
            "latency": self.latency,
            "probabilities": self.probabilities,
            "choice": self.choice,
            "trade_count": sum(e["status"] == "Filled" for e in self.events),
        }
