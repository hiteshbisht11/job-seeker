"""FastAPI app — resume upload + LIVE job fetch + per-resume scoring.

Run:  uvicorn backend.main:app --reload --port 8765

Routes
------
POST /api/match  — multipart resume upload → live-fetched scored jobs
GET  /api/health — debug: returns cache stats + counts per source
GET  /           — serves the static SPA (web/)

The fetcher hits public ATS APIs (Greenhouse, Lever, Remotive, RemoteOK)
in parallel. Results are cached in-memory for 30 minutes, so the first
request takes ~5-10 s and subsequent ones return instantly until the cache
expires.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

from .live_fetcher import cache_stats, fetch_all  # noqa: E402
from .matcher import score_all                    # noqa: E402
from .parser import parse_resume                  # noqa: E402

MAX_PDF_BYTES = 5 * 1024 * 1024  # 5 MB

app = FastAPI(title="Job Seeker", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _prewarm_cache():
    """Pre-populate the live-jobs cache so the first user doesn't wait."""
    try:
        await fetch_all()
    except Exception:
        pass  # never block startup on a flaky external API


@app.get("/api/health")
async def health():
    return {"status": "ok", **cache_stats()}


@app.post("/api/match")
async def match(resume: UploadFile = File(...)):
    if (resume.content_type or "").lower() not in {"application/pdf", "application/x-pdf"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please upload a PDF.")
    pdf_bytes = await resume.read()
    if len(pdf_bytes) > MAX_PDF_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail="PDF is over 5 MB.")
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Empty file.")

    try:
        profile = parse_resume(pdf_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read PDF: {e}")

    if not profile.skills:
        raise HTTPException(
            status_code=422,
            detail="Couldn't detect any technical skills. Try a text-based PDF (not a scanned image).",
        )

    jobs = await fetch_all()
    scored = score_all(profile, jobs)

    return {
        "profile": profile.to_dict(),
        "jobs":    scored,
        "meta":    {"total_fetched": len(jobs), "cache": cache_stats()},
    }


# ---- Static SPA mount ------------------------------------------------------

WEB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web"))


@app.get("/")
def index_root():
    return FileResponse(os.path.join(WEB_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/{path:path}")
def static_fallback(path: str):
    safe = os.path.normpath(path).lstrip("/")
    if safe.startswith("..") or os.path.isabs(safe):
        raise HTTPException(status_code=404)
    full = os.path.join(WEB_DIR, safe)
    if os.path.isfile(full):
        return FileResponse(full)
    raise HTTPException(status_code=404)
