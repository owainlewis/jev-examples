import asyncio
import unittest
from unittest.mock import patch
from backend import app
from backend.engine import Engine


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        app.engine = Engine()
        app.mode = "replay"
        app.error = None

    async def test_pause_keeps_replay_continuous(self):
        samples = []

        async def step(_):
            samples.append(app.engine.last["bid"])
            if len(samples) == 2:
                app.engine.pause()
            if len(samples) == 4:
                raise asyncio.CancelledError

        with patch.object(app.asyncio, "sleep", step):
            with self.assertRaises(asyncio.CancelledError):
                await app.feed()
        self.assertGreater(samples[2], samples[1])
        self.assertNotEqual(samples[2], samples[0])

    async def test_reset_restarts_replay(self):
        samples = []

        async def step(_):
            samples.append(app.engine.last["bid"])
            if len(samples) == 2:
                app.engine = Engine()
            if len(samples) == 3:
                raise asyncio.CancelledError

        with patch.object(app.asyncio, "sleep", step):
            with self.assertRaises(asyncio.CancelledError):
                await app.feed()
        self.assertEqual(samples[0], samples[2])

    async def test_monitor_explains_stale_pause(self):
        app.engine.quote(99, 101, 100, 100)
        app.engine.running = True
        calls = 0

        async def step(_):
            nonlocal calls
            calls += 1
            if calls > 1:
                raise asyncio.CancelledError

        with (
            patch.object(app.asyncio, "sleep", step),
            patch.object(app.time, "time", return_value=111),
        ):
            with self.assertRaises(asyncio.CancelledError):
                await app.monitor()
        self.assertFalse(app.engine.running)
        self.assertIn("stale", app.error)

    async def test_reset_discards_inflight_decision(self):
        app.engine.running = True
        for i in range(30):
            app.engine.quote(99, 101, 100 + i, 100 + i)
        old = app.engine

        async def classified(*args):
            app.engine = Engine()
            return "buy", {"buy": 1.0, "hold": 0.0, "sell": 0.0}, 10

        count = 0

        async def step(_):
            nonlocal count
            count += 1
            if count > 1:
                raise asyncio.CancelledError

        with (
            patch.object(app.asyncio, "sleep", step),
            patch.object(app.asyncio, "to_thread", classified),
            patch.object(app.time, "time", return_value=130),
        ):
            with self.assertRaises(asyncio.CancelledError):
                await app.decisions()
        self.assertEqual(app.engine.calls, 0)
        self.assertEqual(old.calls, 0)
        self.assertIsNone(app.engine.pending)
