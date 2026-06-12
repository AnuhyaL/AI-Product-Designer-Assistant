"""
Lumen — FastAPI server
======================
Bridges the browser frontend (index.html) to the AI backend (groq_orchestrator.py).

Run:
    py app.py
    # or
    uvicorn app:app --reload --port 8000

Then open http://localhost:8000 in your browser.
"""

from __future__ import annotations

import os
import tempfile
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# Lifespan — optional RAG store loaded once at startup if ./chroma_lumen exists

_rag_store: Any = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _rag_store
    try:
        from groq_orchestrator import build_vector_store
        if os.path.isdir("./chroma_lumen"):
            _rag_store = build_vector_store()
            print("RAG knowledge base loaded from ./chroma_lumen")
    except Exception:
        pass  # RAG is optional — skip silently if packages not installed
    yield
    _rag_store = None


# App
app = FastAPI(
    title="Lumen AI Design API",
    description="Multi-agent UX analysis, AI design mentor, and portfolio review.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten to your domain in production
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp", "image/gif"}
DEFAULT_PALETTE = [(18, 19, 23), (205, 245, 100), (255, 106, 69), (245, 242, 234)]
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# Frontend

@app.get("/", response_class=FileResponse)
async def serve_frontend():
    """Serve the single-page frontend."""
    path = os.path.join(BASE_DIR, "index.html")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="index.html not found next to app.py")
    return FileResponse(path, media_type="text/html")


# Health check

@app.get("/health")
async def health():
    """Quick liveness check — also reports whether the API key is configured."""
    return {
        "status": "ok",
        "groq_key_configured": bool(os.environ.get("GROQ_API_KEY")),
        "rag_store_loaded": _rag_store is not None,
    }


# Helpers

def _validate_image(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file.content_type}'. Upload PNG, JPG, or WEBP.",
        )


async def _save_upload(file: UploadFile) -> str:
    """Write the uploaded file to a temp path and return that path."""
    ext = os.path.splitext(file.filename or "upload")[1] or ".png"
    tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    tmp.write(await file.read())
    tmp.close()
    return tmp.name


# POST /api/analyze  — full multi-agent UX review

@app.post("/api/analyze")
async def analyze(file: UploadFile = File(..., description="Screenshot, wireframe, or mockup")):
    """
    Upload a design image and get back:
    - Vision UI map (detected elements + device type)
    - Accessibility score (WCAG contrast check)
    - Five specialist agent reports (UX, A11y, Visual, Strategy, Design System)
    - Coordinator executive summary with ranked top actions
    """
    _validate_image(file)
    tmp_path = await _save_upload(file)
    try:
        from groq_orchestrator import run_agentic_review
        result = run_agentic_review(tmp_path, DEFAULT_PALETTE)
        return JSONResponse(content=result)
    except EnvironmentError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}")
    finally:
        os.unlink(tmp_path)


# POST /api/mentor  — RAG-grounded AI design mentor

class MentorRequest(BaseModel):
    question: str
    history: list[dict] = []

@app.post("/api/mentor")
async def mentor(req: MentorRequest):
    """
    Ask the senior UX consultant anything.
    Pass `history` as a list of prior {role, content} turns for multi-turn chat.
    If the RAG store is loaded the answer is grounded in the knowledge base.
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="'question' cannot be empty.")
    try:
        from groq_orchestrator import ask_mentor
        answer = ask_mentor(req.question, store=_rag_store, history=req.history)
        return {"answer": answer}
    except EnvironmentError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Mentor call failed: {exc}")


# POST /api/portfolio  — recruiter simulation + portfolio scoring

class PortfolioRequest(BaseModel):
    text: str

@app.post("/api/portfolio")
async def portfolio(req: PortfolioRequest):
    """
    Submit portfolio / case-study text and receive:
    - Overall portfolio score and recruiter readiness score
    - Three recruiter personas (AI Eng, Product Design, UX) with likes / concerns / missing
    - Prioritised improvement list
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="'text' cannot be empty.")
    try:
        from groq_orchestrator import portfolio_review
        return portfolio_review(req.text)
    except EnvironmentError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Portfolio review failed: {exc}")


# POST /api/requirements  — design image → product spec / PRD
@app.post("/api/requirements")
async def requirements(file: UploadFile = File(..., description="Design screenshot to convert to a spec")):
    """
    Upload a design and receive a structured product spec:
    components, functional & non-functional requirements,
    user stories, acceptance criteria, and suggested tech stack.
    """
    _validate_image(file)
    tmp_path = await _save_upload(file)
    try:
        from groq_orchestrator import design_to_requirements, map_ui
        ui_map = map_ui(tmp_path)
        return design_to_requirements(ui_map)
    except EnvironmentError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Requirements generation failed: {exc}")
    finally:
        os.unlink(tmp_path)

# Entry point
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"\nLumen server starting → http://localhost:{port}")
    print("API docs             → http://localhost:{port}/docs\n")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
