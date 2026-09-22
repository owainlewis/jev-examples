import unittest
from backend.engine import Engine, FEE, SLIPPAGE


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.e = Engine()
        self.e.running = True
        self.e.quote(99, 101, 100, 100)

    def decide(self, action, now=101):
        return self.e.decision(
            action,
            {k: 0.9 if k == action else 0.05 for k in ("buy", "hold", "sell")},
            80,
            now,
        )

    def test_buy_waits_for_quote_after_decision(self):
        self.decide("buy")
        self.assertEqual(self.e.quantity, 0)
        self.e.quote(99, 101, 100.5, 101)
        self.assertEqual(self.e.quantity, 0)
        self.e.quote(100, 102, 102, 102)
        expected = 1000 / (102 * (1 + SLIPPAGE) * (1 + FEE))
        self.assertAlmostEqual(self.e.quantity, expected)
        self.assertEqual(self.e.cash, 9000)
        self.assertEqual(self.e.events[0]["status"], "Filled")

    def test_round_trip_accounts_for_both_fees_and_slippage(self):
        self.decide("buy")
        self.e.quote(100, 102, 102, 102)
        quantity = self.e.quantity
        buy_fee = self.e.fees
        self.decide("sell", 103)
        self.e.quote(110, 112, 104, 104)
        proceeds = quantity * 110 * (1 - SLIPPAGE) * (1 - FEE)
        self.assertAlmostEqual(self.e.realized, proceeds - 1000)
        self.assertAlmostEqual(self.e.cash, 9000 + proceeds)
        self.assertAlmostEqual(
            self.e.fees, buy_fee + quantity * 110 * (1 - SLIPPAGE) * FEE
        )
        self.assertEqual(self.e.quantity, 0)
        self.assertAlmostEqual(self.e.snapshot()["unrealized"], 0)

    def test_cannot_sell_without_position_or_buy_twice(self):
        self.assertEqual(self.decide("sell")["status"], "Blocked: no position")
        self.decide("buy")
        self.e.quote(100, 102, 102, 102)
        self.assertEqual(
            self.decide("buy", 103)["status"], "Blocked: position already open"
        )

    def test_uncertain_action_does_not_trade(self):
        event = self.e.decision("buy", {"buy": 0.6, "hold": 0.3, "sell": 0.1}, 100, 101)
        self.assertIn("probability", event["status"])
        self.assertIsNone(self.e.pending)

    def test_pause_cancels_pending_trade(self):
        self.decide("buy")
        self.e.pause()
        self.e.quote(100, 102, 102, 102)
        self.assertEqual(self.e.cash, 10000)
        self.assertEqual(self.e.events[0]["status"], "Cancelled on pause")

    def test_stale_and_out_of_order_quotes_rejected(self):
        self.assertFalse(self.e.quote(100, 102, 99, 100))
        self.assertFalse(self.e.quote(100, 102, 101, 120))
        self.assertFalse(self.e.quote(float("nan"), 102, 101, 101))
        self.assertFalse(self.e.quote(103, 102, 101, 101))

    def test_expired_order_does_not_fill(self):
        self.decide("buy")
        self.e.quote(100, 102, 120, 120)
        self.assertEqual(self.e.cash, 10000)
        self.assertTrue(self.e.events[0]["status"].startswith("Expired"))

    def test_invalid_probability_rejected(self):
        for p in (
            {"buy": 1},
            {"buy": float("nan"), "hold": 0, "sell": 0},
            {"buy": 0.1, "hold": 0.8, "sell": 0.1},
        ):
            with self.assertRaises(ValueError):
                self.e.decision("buy", p, 80, 101)

    def test_unrealized_includes_exit_costs(self):
        self.decide("buy")
        self.e.quote(100, 102, 102, 102)
        self.assertLess(self.e.snapshot()["net_profit"], 0)
        self.assertAlmostEqual(
            self.e.snapshot()["unrealized"], self.e.snapshot()["net_profit"]
        )


if __name__ == "__main__":
    unittest.main()


class FreshnessTests(unittest.TestCase):
    def test_transport_delay_does_not_extend_quote_lifetime(self):
        engine = Engine()
        engine.running = True
        engine.quote(99, 101, 100, 109)
        event = engine.decision("buy", {"buy": 1.0, "hold": 0.0, "sell": 0.0}, 80, 118)
        self.assertEqual(event["status"], "Blocked: stale data")
        self.assertIsNone(engine.pending)
