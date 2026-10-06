"""Voice-agent decision backend: fans each caller turn out to an LLM, Jev and CLM.

All three lanes answer the same four judgments about the conversation, and every
number the UI shows is a measured round trip from this server.

Run:  uvicorn app:app --port 8000
"""
import asyncio
import json
import os
import statistics
import time

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from catalog import MAX_TOOLS, build_tools, reply_for

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
TYPESAFE_API_KEY = os.getenv("TYPESAFE_API_KEY", "")
TYPESAFE_BASE_URL = os.getenv("TYPESAFE_BASE_URL", "https://api.typesafe.ai").rstrip("/")
JEV_MODEL = os.getenv("JEV_MODEL", "jev-latest")
CLM_BASE_URL = os.getenv("CLM_BASE_URL", "").rstrip("/")
CLM_API_KEY = os.getenv("CLM_API_KEY", "")
CLM_MODEL = os.getenv("CLM_MODEL", "clm-latest")
TIMEOUT = float(os.getenv("LANE_TIMEOUT_S", "30"))

FRUSTRATION_LEVELS = ["Calm and cooperative", "Mildly impatient", "Clearly frustrated", "Angry or distressed"]
AGENT_ROLE = "Phone receptionist voice agent for Maple Street Clinic"

app = FastAPI(title="CLM Voice Showcase")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
http = httpx.AsyncClient(timeout=TIMEOUT, limits=httpx.Limits(max_keepalive_connections=20))


class Turn(BaseModel):
    role: str  # "caller" | "agent"
    text: str


class TurnRequest(BaseModel):
    transcript: list[Turn]
    n_tools: int = Field(8, ge=8, le=MAX_TOOLS)
    lanes: list[str] = ["llm", "jev", "clm"]


class BenchRequest(BaseModel):
    utterance: str = "Hi, I need to move my appointment on Thursday to next week if possible."
    sizes: list[int] = [8, 32, 64, 128, 250]
    reps: int = Field(3, ge=1, le=10)
    lanes: list[str] = ["llm", "jev", "clm"]


def make_state(transcript: list[Turn]) -> dict:
    return {"agent": AGENT_ROLE, "transcript": [t.model_dump() for t in transcript[-8:]]}


def make_questions(tools: dict[str, str]) -> dict:
    return {
        "end_of_turn": {"type": "noul", "instructions":
            "Has the caller finished their thought in the last caller message of `transcript`, "
            "so the agent should respond now instead of waiting for them to keep talking?"},
        "tool": {"type": "choice", "instructions":
            "Which tool should the voice agent use to handle the caller's latest message in `transcript`?",
            "criteria": tools},
        "frustration": {"type": "score", "instructions":
            "How frustrated is the caller right now, based on `transcript`?",
            "criteria": FRUSTRATION_LEVELS},
        "escalate": {"type": "noul", "instructions":
            "Should the call be handed to a human staff member now? Yes only for a medical emergency, "
            "an explicit request for a person, or the agent repeatedly failing the caller."},
    }


# ---------------------------------------------------------------- lanes

async def system_one(base_url: str, key: str, model: str, state: dict, questions: dict) -> dict:
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    r = await http.post(f"{base_url}/v1/systemone", headers=headers,
                        json={"model": model, "state": state, "questions": questions})
    r.raise_for_status()
    body = r.json()
    a = body["answers"]
    server_ms = r.headers.get("X-CLM-Latency-Ms")
    return {
        "model": body.get("model", model),
        "server_ms": float(server_ms) if server_ms else None,
        "end_of_turn": a["end_of_turn"]["noul"],
        "tool": a["tool"]["choice"],
        "tool_prob": a["tool"]["probabilities"].get(a["tool"]["choice"]),
        "tool_top3": sorted(a["tool"]["probabilities"].items(), key=lambda kv: -kv[1])[:3],
        "frustration": a["frustration"]["score"],
        "escalate": a["escalate"]["noul"],
        "usage": body.get("usage"),
    }


async def llm_lane(state: dict, tools: dict[str, str]) -> dict:
    schema = {
        "type": "object", "additionalProperties": False,
        "required": ["end_of_turn", "tool", "frustration", "escalate"],
        "properties": {
            "end_of_turn": {"type": "boolean"},
            "tool": {"type": "string", "enum": list(tools)},
            "frustration": {"type": "integer", "enum": [0, 1, 2, 3]},
            "escalate": {"type": "boolean"},
        },
    }
    tool_list = "\n".join(f"- {k}: {v}" for k, v in tools.items())
    system = (
        f"You are the decision module of a {AGENT_ROLE}. Given the conversation, return JSON with:\n"
        "end_of_turn: has the caller finished their thought so the agent should respond now?\n"
        "tool: which tool handles the caller's latest message. Tools:\n" + tool_list + "\n"
        "frustration: " + ", ".join(f"{i}={l}" for i, l in enumerate(FRUSTRATION_LEVELS)) + "\n"
        "escalate: hand to a human now? Only for a medical emergency, an explicit request for a person, "
        "or repeated agent failure."
    )
    r = await http.post(
        f"{OPENAI_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        json={"model": OPENAI_MODEL,
              "messages": [{"role": "system", "content": system},
                           {"role": "user", "content": json.dumps(state)}],
              "response_format": {"type": "json_schema",
                                  "json_schema": {"name": "decision", "strict": True, "schema": schema}}},
    )
    r.raise_for_status()
    body = r.json()
    d = json.loads(body["choices"][0]["message"]["content"])
    return {
        "model": body.get("model", OPENAI_MODEL),
        "server_ms": None,
        "end_of_turn": 1.0 if d["end_of_turn"] else 0.0,
        "tool": d["tool"],
        "tool_prob": None,  # an LLM gives no calibrated distribution
        "tool_top3": [[d["tool"], None]],
        "frustration": float(d["frustration"]),
        "escalate": 1.0 if d["escalate"] else 0.0,
        "usage": body.get("usage"),
    }


def configured(lane: str) -> bool:
    return bool({"llm": OPENAI_API_KEY, "jev": TYPESAFE_API_KEY, "clm": CLM_BASE_URL}[lane])


async def run_lane(lane: str, state: dict, tools: dict[str, str]) -> dict:
    if not configured(lane):
        return {"lane": lane, "ok": False, "error": f"{lane} is not configured in backend/.env"}
    t0 = time.perf_counter()
    try:
        if lane == "llm":
            out = await llm_lane(state, tools)
        elif lane == "jev":
            out = await system_one(TYPESAFE_BASE_URL, TYPESAFE_API_KEY, JEV_MODEL, state, make_questions(tools))
        else:
            out = await system_one(CLM_BASE_URL, CLM_API_KEY, CLM_MODEL, state, make_questions(tools))
    except httpx.HTTPStatusError as e:
        return {"lane": lane, "ok": False, "latency_ms": (time.perf_counter() - t0) * 1000,
                "error": f"HTTP {e.response.status_code}: {e.response.text[:300]}"}
    except Exception as e:  # noqa: BLE001 - surface any lane failure to the UI
        return {"lane": lane, "ok": False, "latency_ms": (time.perf_counter() - t0) * 1000,
                "error": f"{type(e).__name__}: {e}"}
    latency = (time.perf_counter() - t0) * 1000
    return {"lane": lane, "ok": True, "latency_ms": latency,
            "reply": reply_for(out["tool"], out["escalate"], out["end_of_turn"]), **out}


def sse(obj: dict) -> str:
    return f"data: {json.dumps(obj)}\n\n"


# ---------------------------------------------------------------- routes

@app.get("/api/health")
async def health():
    out = {}
    for lane, model in (("llm", OPENAI_MODEL), ("jev", JEV_MODEL), ("clm", CLM_MODEL)):
        out[lane] = {"configured": configured(lane), "model": model}
    if CLM_BASE_URL:
        try:
            r = await http.get(f"{CLM_BASE_URL}/health", timeout=10)
            h = r.json()
            out["clm"]["reachable"] = r.status_code == 200 and h.get("embedder", False)
            out["clm"]["mock"] = bool(h.get("mock"))
        except Exception as e:  # noqa: BLE001
            out["clm"]["reachable"] = False
            out["clm"]["error"] = str(e)
    return out


@app.post("/api/turn")
async def turn(req: TurnRequest):
    """Stream each lane's decision the moment it lands (SSE), fastest first."""
    state, tools = make_state(req.transcript), build_tools(req.n_tools)

    async def gen():
        tasks = [asyncio.create_task(run_lane(l, state, tools)) for l in req.lanes]
        for fut in asyncio.as_completed(tasks):
            yield sse(await fut)
        yield sse({"done": True})

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/api/bench")
async def bench(req: BenchRequest):
    """Real latency vs. tool count. Lanes run in parallel per rep; streams one row per size."""
    state = make_state([Turn(role="caller", text=req.utterance)])

    async def gen():
        for n in req.sizes:
            tools = build_tools(n)
            samples: dict[str, list[float]] = {l: [] for l in req.lanes}
            errors: dict[str, str] = {}
            for _ in range(req.reps):
                results = await asyncio.gather(*(run_lane(l, state, tools) for l in req.lanes))
                for res in results:
                    if res["ok"]:
                        samples[res["lane"]].append(res["latency_ms"])
                    else:
                        errors[res["lane"]] = res["error"]
            row: dict[str, float | None] = {"n_tools": len(tools)}
            for l, s in samples.items():
                row[l] = statistics.median(s) if s else None
                row[f"{l}_first"] = s[0] if s else None
            yield sse({"row": row, "errors": errors})
        yield sse({"done": True})

    return StreamingResponse(gen(), media_type="text/event-stream")
