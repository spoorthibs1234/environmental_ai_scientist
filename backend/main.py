import json
import os
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .models import AnalyzeRequest, ChatRequest
from .rag import KnowledgeRetriever
from .reasoning import (
    build_explanation, extract_environment, generate_recommendations,
    missing_fields, normalize_environment
)

load_dotenv()
app = FastAPI(title="Environmental AI Scientist", version="1.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

retriever = KnowledgeRetriever()
SESSIONS: Dict[str, Dict[str, Any]] = {}

def get_session(session_id):
    return SESSIONS.setdefault(
        session_id, {"environment": normalize_environment({}), "messages": []}
    )

def evidence_for_response(retrieved):
    return [
        {
            "id": x["id"], "title": x["title"], "source": x["source"],
            "year": x.get("year"), "url": x.get("url"),
            "topic": x.get("topic"), "similarity": x.get("similarity")
        }
        for x in retrieved
    ]

def optional_llm_rewrite(payload):
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5.6"),
            input=(
                "You are an environmental science assistant. Rewrite the supplied "
                "structured result into a concise scientifically cautious answer. "
                "Do not invent effect sizes or citations. Preserve recommendations, "
                "metrics, time horizons and source names. Distinguish evidence from inference.\n\n"
                + json.dumps(payload, indent=2)
            )
        )
        return response.output_text
    except Exception:
        return None

@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "rag": "TF-IDF + cosine similarity",
        "knowledge_documents": len(retriever.documents),
        "llm_enabled": bool(os.getenv("OPENAI_API_KEY", "").strip())
    }

@app.get("/api/knowledge")
def knowledge():
    return {"documents": retriever.all_documents()}

@app.post("/api/analyze")
def analyze(request: AnalyzeRequest):
    session = get_session(request.session_id)

    if request.environment:
        session["environment"] = normalize_environment(request.environment.model_dump())
    elif request.message:
        session["environment"] = extract_environment(
            request.message, session.get("environment")
        )

    env = session["environment"]
    if request.message:
        session["messages"].append({"role": "user", "content": request.message})

    missing = missing_fields(env)
    query = " ".join([
        request.message or "", json.dumps(env),
        "biodiversity soil climate land use water habitat"
    ])
    retrieved = retriever.search(query, request.top_k)

    if missing:
        answer = (
            "I can analyze the biodiversity risk, but a few important inputs are missing. "
            "Please provide: " + ", ".join(missing) + "."
        )
        session["messages"].append({"role": "assistant", "content": answer})
        return {
            "status": "needs_clarification", "answer": answer,
            "environment": env, "missing": missing,
            "retrieved_evidence": evidence_for_response(retrieved),
            "recommendations": [], "reasoning": [],
            "conversation_turns": len(session["messages"])
        }

    recommendations, analysis = generate_recommendations(env, retrieved)
    reasoning = build_explanation(env, analysis)
    payload = {
        "environment": env, "signals": analysis["signals"],
        "reasoning": reasoning, "recommendations": recommendations,
        "retrieved_evidence": evidence_for_response(retrieved)
    }

    llm_answer = optional_llm_rewrite(payload)
    if llm_answer:
        answer = llm_answer
    else:
        lines = [
            "### Environmental assessment",
            "The available variables indicate these interacting signals: "
            + (", ".join(analysis["signals"]) or "no strong predefined risk signal"),
            ""
        ]
        for i, rec in enumerate(recommendations, 1):
            lines += [
                f"### {i}. {rec['action']}",
                f"**Why it works:** {rec['why']}",
                f"**Impacted metrics:** {', '.join(rec['metrics'])}",
                f"**Time horizon:** {rec['time_horizon']}",
                f"**Confidence:** {rec['confidence']}",
                f"**Evidence:** {rec['evidence_summary']}",
                ""
            ]
        answer = "\n".join(lines)

    session["messages"].append({"role": "assistant", "content": answer})
    return {
        "status": "ok", "answer": answer, "environment": env,
        "signals": analysis["signals"], "reasoning": reasoning,
        "recommendations": recommendations,
        "retrieved_evidence": evidence_for_response(retrieved),
        "conversation_turns": len(session["messages"]),
        "llm_used": bool(llm_answer)
    }

@app.post("/api/chat")
def chat(request: ChatRequest):
    session = get_session(request.session_id)
    session["environment"] = extract_environment(
        request.message, session.get("environment")
    )
    return analyze(AnalyzeRequest(
        session_id=request.session_id,
        message=request.message,
        environment=None,
        top_k=request.top_k
    ))

@app.post("/api/reset/{session_id}")
def reset(session_id):
    SESSIONS.pop(session_id, None)
    return {"status": "reset", "session_id": session_id}
 