
import os
import time
import uuid
from collections import defaultdict

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

API_KEY = os.getenv("ANALYTICS_API_KEY", "")
STUDENT_EMAIL = os.getenv("STUDENT_EMAIL", "")


@app.middleware("http")
async def request_headers(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start = time.perf_counter()

    response = await call_next(request)

    elapsed = max(0.0, time.perf_counter() - start)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{elapsed:.6f}"
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Event(BaseModel):
    user: str
    amount: float
    ts: int


class AnalyticsRequest(BaseModel):
    events: list[Event]


@app.post("/analytics")
def analytics(
    body: AnalyticsRequest,
    x_api_key: str = Header(default=None, alias="X-API-Key"),
):
    if not API_KEY or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    events = body.events
    user_totals = defaultdict(float)

    for event in events:
        if event.amount > 0:
            user_totals[event.user] += event.amount

    top_user = (
        max(user_totals, key=user_totals.get)
        if user_totals
        else ""
    )

    return {
        "email": STUDENT_EMAIL,
        "total_events": len(events),
        "unique_users": len({event.user for event in events}),
        "revenue": round(
            sum(e.amount for e in events if e.amount > 0), 2
        ),
        "top_user": top_user,
    }
