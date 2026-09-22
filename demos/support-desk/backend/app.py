"""Run from this demo folder: uvicorn backend.app:app --host 127.0.0.1."""

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .classifier import MODEL, MODES, SPECS, classify, python_example
from .store import Conflict, MissingTicket, Store

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


class TicketInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    subject: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=8000)
    customer: str = Field(default="Demo customer", min_length=1, max_length=80)


class RunInput(BaseModel):
    mode: Literal["choice", "noul", "score", "combined"]


class Correction(BaseModel):
    team: Literal["billing", "technical", "account", "other"]
    priority: Literal["standard", "urgent", "needs_review"]


def create_app(database=None, classify_fn=None):
    application = FastAPI(title="Jev Support Desk")
    application.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"]
    )
    store = Store(
        Path(
            database
            or os.environ.get("SUPPORT_DESK_DB", ROOT / "instance" / "desk.sqlite3")
        )
    )
    provider = classify_fn or classify
    application.state.store = store

    @application.middleware("http")
    async def local_mutations(request: Request, call_next):
        if request.method in {"POST", "PATCH", "DELETE", "PUT"}:
            if (
                request.headers.get("x-demo-request") != "support-desk"
                or request.headers.get("content-type", "").split(";")[0]
                != "application/json"
            ):
                return JSONResponse(
                    {"detail": "Use the support desk interface to make this request."},
                    status_code=403,
                )
        return await call_next(request)

    @application.exception_handler(Conflict)
    async def conflict_handler(request, error):
        return JSONResponse({"detail": str(error)}, status_code=409)

    @application.exception_handler(MissingTicket)
    async def missing_handler(request, error):
        return JSONResponse({"detail": str(error)}, status_code=404)

    @application.get("/api/config")
    def config():
        return {
            "model": MODEL,
            "configured": bool(os.environ.get("TYPESAFE_API_KEY")),
            "modes": {
                mode: {
                    "questions": {key: SPECS[key] for key in keys},
                    "python": python_example(mode),
                }
                for mode, keys in MODES.items()
            },
        }

    @application.get("/api/tickets")
    def tickets():
        return store.list()

    @application.post("/api/tickets", status_code=201)
    def create_ticket(data: TicketInput):
        return store.create(data.model_dump())

    @application.post("/api/tickets/{identifier}/runs")
    def run(identifier: str, data: RunInput):
        ticket = store.get(identifier)
        run_id = store.claim(identifier, data.mode)
        try:
            result = provider(ticket, data.mode)
        except Exception:
            # Provider errors can contain request details. Never return them to the browser.
            error = "Jev could not complete the request. Check the backend API key and connection, then try again. Your ticket is saved."
            store.finish(run_id, error=error)
            raise HTTPException(502, error) from None
        completed = store.finish(run_id, result=result)
        if not completed:
            raise HTTPException(
                409, "This request expired. Refresh the ticket and run it again."
            )
        return completed

    @application.patch("/api/tickets/{identifier}/correction")
    def correct(identifier: str, data: Correction):
        return store.correct(identifier, data.model_dump())

    @application.post("/api/reset")
    def reset():
        return store.reset()

    build = ROOT / "frontend" / "dist"
    if build.exists():
        application.mount("/", StaticFiles(directory=build, html=True), name="frontend")
    return application


app = create_app()
