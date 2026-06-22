"""
API REST que orquesta el pipeline completo:
sube CV -> busca ofertas -> matchea -> genera carta -> guarda en BD.

Arrancar con: uvicorn backend.main:app --reload
Docs interactivas en: http://localhost:8000/docs
"""
import os
import json
import shutil
import tempfile

from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel

from backend import db
from backend.cv_parser import parse_cv_file
from backend.job_scraper import search_jobs
from backend.matcher import rank_jobs
from backend.application_generator import generate_cover_letter

app = FastAPI(
    title="Job Matcher AI",
    description="Sube tu CV, encuentra ofertas relevantes y genera cartas de presentación personalizadas.",
)


class SearchRequest(BaseModel):
    cv_id: int
    query: str
    location: str = ""
    results: int = 20


class GenerateLetterRequest(BaseModel):
    match_id: int


def _row_to_cv_data(cv_row) -> dict:
    return {
        "full_name": cv_row["full_name"],
        "summary": cv_row["summary"],
        "skills": json.loads(cv_row["skills"]),
        "experience": json.loads(cv_row["experience"]),
        "education": json.loads(cv_row["education"]),
    }


@app.post("/upload-cv")
async def upload_cv(file: UploadFile = File(...)):
    """Sube un CV en PDF, lo parsea con el LLM y lo guarda en la base de datos."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        cv_data, raw_text = parse_cv_file(tmp_path)
    finally:
        os.unlink(tmp_path)

    cv_id = db.save_cv_profile(cv_data, raw_text)
    return {"cv_id": cv_id, "cv_data": cv_data}


@app.post("/search-and-match")
async def search_and_match(req: SearchRequest):
    """Busca ofertas reales, las matchea contra el CV indicado y las guarda."""
    with db.get_connection() as conn:
        cv_row = conn.execute(
            "SELECT * FROM cv_profiles WHERE id = ?", (req.cv_id,)
        ).fetchone()
    if not cv_row:
        raise HTTPException(status_code=404, detail="CV no encontrado.")

    cv_data = _row_to_cv_data(cv_row)

    jobs = search_jobs(req.query, location=req.location, results=req.results)
    ranked = rank_jobs(cv_data, jobs)

    saved_matches = []
    for job in ranked:
        job_id = db.save_job_posting(job)
        match_id = db.save_match(req.cv_id, job_id, job["match_score"])
        saved_matches.append({**job, "job_id": job_id, "match_id": match_id})

    return {"matches_found": len(saved_matches), "matches": saved_matches}


@app.post("/generate-cover-letter")
async def generate_letter(req: GenerateLetterRequest):
    """Genera (o regenera) la carta de presentación para un match concreto."""
    with db.get_connection() as conn:
        row = conn.execute(
            """
            SELECT m.id as match_id, m.cv_id, j.title, j.company, j.description
            FROM matches m JOIN job_postings j ON j.id = m.job_id
            WHERE m.id = ?
            """,
            (req.match_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Match no encontrado.")

    with db.get_connection() as conn:
        cv_row = conn.execute(
            "SELECT * FROM cv_profiles WHERE id = ?", (row["cv_id"],)
        ).fetchone()

    cv_data = _row_to_cv_data(cv_row)
    job = {"title": row["title"], "company": row["company"], "description": row["description"]}

    letter = generate_cover_letter(cv_data, job)

    with db.get_connection() as conn:
        conn.execute(
            "UPDATE matches SET cover_letter = ? WHERE id = ?", (letter, req.match_id)
        )
        conn.commit()

    return {"match_id": req.match_id, "cover_letter": letter}


@app.get("/matches/{cv_id}")
async def get_matches(cv_id: int):
    return {"matches": db.get_matches_for_cv(cv_id)}


@app.get("/")
async def root():
    return {"status": "ok", "docs": "/docs"}
