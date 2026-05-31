import json
import math
from pathlib import Path
from statistics import mean

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

DATA_PATH = Path(__file__).resolve().parent.parent / "q-vercel-latency.json"
DATA = json.loads(DATA_PATH.read_text(encoding="utf-8"))
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "*",
}

app = FastAPI(title="eShopCo Latency API")


class MetricsRequest(BaseModel):
    regions: list[str]
    threshold_ms: float


def percentile_95(values: list[float]) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = 0.95 * (len(ordered) - 1)
    lower_index = math.floor(rank)
    upper_index = math.ceil(rank)
    lower_value = ordered[lower_index]
    upper_value = ordered[upper_index]
    if lower_index == upper_index:
        return lower_value
    fraction = rank - lower_index
    return lower_value + (upper_value - lower_value) * fraction


def build_response(payload: MetricsRequest) -> dict:
    response = {}
    for region in payload.regions:
        rows = [row for row in DATA if row.get("region") == region]
        latencies = [float(row["latency_ms"]) for row in rows]
        uptimes = [float(row["uptime_pct"]) for row in rows]
        response[region] = {
            "avg_latency": round(mean(latencies), 2) if latencies else 0.0,
            "p95_latency": round(percentile_95(latencies), 2) if latencies else 0.0,
            "avg_uptime": round(mean(uptimes), 3) if uptimes else 0.0,
            "breaches": sum(1 for latency in latencies if latency > payload.threshold_ms),
        }
    return response


@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    if request.method == "OPTIONS":
        return Response(status_code=204, headers=CORS_HEADERS)
    response = await call_next(request)
    response.headers.update(CORS_HEADERS)
    return response


@app.post("/")
@app.post("/api")
def latency_metrics(payload: MetricsRequest):
    return JSONResponse(content=build_response(payload))
