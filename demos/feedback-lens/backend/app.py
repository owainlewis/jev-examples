"""Local, stateless API and static frontend. Bind only to loopback."""

import os
from pathlib import Path
from threading import Lock

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .analyzer import EXAMPLES, IMPACT, MODEL, THEMES, analyze, questions

ROOT = Path(__file__).resolve().parents[1]


class FeedbackInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    feedback: str = Field(min_length=1, max_length=6000)


def create_app(analyze_fn=None):
    load_dotenv(os.environ.get("FEEDBACK_LENS_ENV", ROOT / ".env"))
    application = FastAPI(title="Feedback Lens", docs_url=None, redoc_url=None)
    application.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"]
    )
    provider = analyze_fn or analyze
    active = Lock()

    @application.middleware("http")
    async def local_requests(request: Request, call_next):
        if request.method == "POST":
            origin = request.headers.get("origin")
            if (
                request.headers.get("x-demo-request") != "feedback-lens"
                or request.headers.get("content-type", "").split(";")[0]
                != "application/json"
                or (origin is not None and origin != str(request.base_url).rstrip("/"))
                or request.headers.get("sec-fetch-site") == "cross-site"
            ):
                return JSONResponse(
                    {"detail": "Submit feedback from the local Feedback Lens app."},
                    status_code=403,
                )
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "connect-src 'self'; img-src 'self'; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        )
        return response

    @application.exception_handler(RequestValidationError)
    async def invalid_input(request, error):
        # FastAPI's default error body echoes submitted input.
        return JSONResponse(
            {"detail": "Enter between 1 and 6,000 characters of feedback."},
            status_code=422,
        )

    @application.get("/api/config")
    def config():
        return {
            "model": MODEL,
            "configured": bool(os.environ.get("TYPESAFE_API_KEY", "").strip()),
            "themes": THEMES,
            "impact": IMPACT,
            "examples": EXAMPLES,
            "questions": {
                key: value.model_dump() for key, value in questions().items()
            },
        }

    @application.post("/api/analyze")
    def run(data: FeedbackInput):
        if not os.environ.get("TYPESAFE_API_KEY", "").strip():
            raise HTTPException(
                503, "Add TYPESAFE_API_KEY to the demo's .env and restart the server."
            )
        if not active.acquire(blocking=False):
            raise HTTPException(
                409, "A Jev request is already running. Try again shortly."
            )
        try:
            return provider(data.feedback)
        except Exception:
            # SDK exceptions may include credentials or input. Never expose or log them.
            raise HTTPException(
                502,
                "Jev could not analyze this feedback. Check the server's API key, TypeSafe balance, and connection, then retry.",
            ) from None
        finally:
            active.release()

    application.mount("/", StaticFiles(directory=ROOT / "frontend", html=True))
    return application


app = create_app()
