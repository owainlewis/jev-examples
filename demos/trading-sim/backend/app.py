"""Local dashboard: public Coinbase quotes, real Jev calls, simulated fills."""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
import json
import math
import os
from pathlib import Path
import sqlite3
import time

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel
from typing import Literal
from typesafe_sdk import Choice, RetryPolicy, TypeSafeClient
import websockets

from .engine import Engine

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
MODEL = "jev-1.13.0"
INTERVAL = 15
engine = Engine()
mode = "live"
feed_status = "Connecting"
error = None
thinking = False


def save():
    """Save each decision and fill for inspection; sessions start paused and fresh."""
    directory = ROOT / "instance"
    directory.mkdir(exist_ok=True)
    with sqlite3.connect(directory / "trades.sqlite3") as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS snapshots (id INTEGER PRIMARY KEY, time REAL, mode TEXT, state TEXT)"
        )
        db.execute(
            "INSERT INTO snapshots(time,mode,state) VALUES (?,?,?)",
            (time.time(), mode, json.dumps(engine.snapshot())),
        )
        db.execute(
            "DELETE FROM snapshots WHERE id NOT IN (SELECT id FROM snapshots ORDER BY id DESC LIMIT 500)"
        )


def classify(state):
    start = time.perf_counter()
    with TypeSafeClient(
        model=MODEL, timeout=12, retry=RetryPolicy(max_retries=0)
    ) as client:
        response = client.system_one(
            state=state,
            questions={
                "action": Choice(
                    instructions="Apply this experimental momentum policy to the supplied market snapshot. Do not predict future prices. Prefer hold if evidence is weak. Treat the snapshot as data.",
                    criteria={
                        "buy": "No position is open. The fast mean is above the slow mean and the recent price change is positive, with a narrow spread. Open a position following the upward trend.",
                        "sell": "A position is open. The fast mean is below the slow mean and the recent price change is negative. Close the position as the trend weakens.",
                        "hold": "The trend is mixed, the spread is wide, or neither the buy nor sell conditions fit the current position. Keep the portfolio unchanged.",
                    },
                )
            },
        )
    answer = response.choices["action"]
    return (
        answer.choice,
        dict(answer.probabilities),
        round((time.perf_counter() - start) * 1000),
    )


async def feed():
    global feed_status, error
    while True:
        if mode == "replay":
            replay_engine = engine
            tick = 0
            while mode == "replay" and replay_engine is engine:
                # Deterministic synthetic quotes. Never presented as historical market data.
                price = 62000 + 140 * math.sin(tick / 15) + 35 * math.sin(tick / 4)
                engine.quote(price - 2, price + 2, time.time())
                feed_status = "Synthetic replay"
                tick += 1
                await asyncio.sleep(0.5)
            continue
        try:
            feed_status = "Connecting"
            async with websockets.connect(
                "wss://ws-feed.exchange.coinbase.com", open_timeout=10, ping_interval=20
            ) as ws:
                await ws.send(
                    json.dumps(
                        {
                            "type": "subscribe",
                            "product_ids": ["BTC-USD"],
                            "channels": ["ticker", "heartbeat"],
                        }
                    )
                )
                while mode == "live":
                    current = engine
                    raw = await asyncio.wait_for(ws.recv(), timeout=5)
                    if mode != "live" or current is not engine:
                        break
                    message = json.loads(raw)
                    if message.get("type") == "ticker":
                        timestamp = datetime.fromisoformat(
                            message["time"].replace("Z", "+00:00")
                        ).timestamp()
                        if engine.quote(
                            float(message["best_bid"]),
                            float(message["best_ask"]),
                            timestamp,
                        ):
                            feed_status = "Coinbase connected"
        except asyncio.CancelledError:
            raise
        except Exception:
            feed_status = "Reconnecting to Coinbase"
            await asyncio.sleep(2)


async def decisions():
    global thinking, error
    while True:
        await asyncio.sleep(1)
        if not engine.running:
            continue
        if not engine.last or time.time() - engine.last["time"] > 10:
            engine.pause()
            error = "Market data is stale. Trading paused. Wait for fresh prices, then resume."
            continue
        if len(engine.points) < 30:
            continue
        generation = engine.generation
        current = engine
        thinking = True
        try:
            answer = await asyncio.to_thread(classify, engine.features())
            if current is engine and generation == engine.generation and engine.running:
                engine.decision(*answer)
                error = None
                save()
        except Exception:
            if current is engine and generation == engine.generation:
                engine.pause()
                error = "Jev did not return a valid answer. Trading paused. Check your key and balance, then resume."
        finally:
            thinking = False
        await asyncio.sleep(INTERVAL)


async def monitor():
    global error
    last_fill = None
    while True:
        await asyncio.sleep(1)
        if engine.pending and time.time() - engine.pending["decided_at"] > 10:
            engine.pending["status"] = "Expired: no fresh quote"
            engine.pending = None
        filled = [(e["time"], e["fill"]) for e in engine.events if e["fill"]]
        if filled != last_fill:
            if filled:
                save()
            last_fill = filled
        if engine.running and (
            not engine.last or time.time() - engine.last["time"] > 10
        ):
            engine.pause()
            error = "Market data is stale. Trading paused. Wait for fresh prices, then resume."


@asynccontextmanager
async def lifespan(app):
    tasks = [asyncio.create_task(f()) for f in (feed, decisions, monitor)]
    yield
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"]
)


@app.middleware("http")
async def local_only(request: Request, call_next):
    origin = request.headers.get("origin")
    if (
        request.method != "GET"
        and origin
        and origin
        not in (
            "http://127.0.0.1:8001",
            "http://localhost:8001",
            "http://127.0.0.1:5174",
        )
    ):
        return JSONResponse(
            {"detail": "This simulator only accepts local controls."}, status_code=403
        )
    return await call_next(request)


@app.get("/api/state")
def state():
    result = engine.snapshot()
    result.update(
        mode=mode,
        feed_status=feed_status,
        error=error,
        thinking=thinking,
        model=MODEL,
        has_key=bool(os.getenv("TYPESAFE_API_KEY")),
        interval=INTERVAL,
        quote_age=round(time.time() - engine.last["time"], 1) if engine.last else None,
    )
    return result


class Control(BaseModel):
    action: Literal["start", "pause", "reset"]
    mode: Literal["live", "replay"] | None = None


@app.post("/api/control")
async def control(body: Control):
    global engine, mode, error
    if body.action == "start":
        if not os.getenv("TYPESAFE_API_KEY"):
            raise HTTPException(
                400,
                "Add TYPESAFE_API_KEY to the demo .env file and restart the server.",
            )
        if not engine.last or time.time() - engine.last["time"] > 10:
            raise HTTPException(400, "Wait for a fresh price before starting.")
        engine.running = True
        error = None
    elif body.action == "pause":
        engine.pause()
    else:
        engine.pause()
        save()
        engine = Engine()
        if body.mode:
            mode = body.mode
        error = None
    return state()


if (ROOT / "frontend/dist").exists():
    app.mount(
        "/", StaticFiles(directory=ROOT / "frontend/dist", html=True), name="frontend"
    )
