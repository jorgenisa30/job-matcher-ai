"""
Capa de acceso a datos (SQLite). Funciones simples, sin ORM, para que el
flujo de datos sea fácil de seguir en un proyecto de portfolio.
"""
import sqlite3
import json
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "job_matcher.db")


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def save_cv_profile(cv_data: dict, raw_text: str) -> int:
    """Guarda un CV parseado y devuelve su id."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO cv_profiles (full_name, email, phone, summary, skills,
                                      experience, education, languages, raw_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cv_data.get("full_name"),
                cv_data.get("email"),
                cv_data.get("phone"),
                cv_data.get("summary"),
                json.dumps(cv_data.get("skills", [])),
                json.dumps(cv_data.get("experience", [])),
                json.dumps(cv_data.get("education", [])),
                json.dumps(cv_data.get("languages", [])),
                raw_text,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def save_job_posting(job: dict) -> int:
    """Guarda una oferta de empleo (o devuelve el id si ya existía)."""
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM job_postings WHERE external_id = ?",
            (job.get("external_id"),),
        ).fetchone()
        if existing:
            return existing["id"]

        cursor = conn.execute(
            """
            INSERT INTO job_postings (external_id, title, company, location,
                                       description, salary_min, salary_max, url, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.get("external_id"),
                job.get("title"),
                job.get("company"),
                job.get("location"),
                job.get("description"),
                job.get("salary_min"),
                job.get("salary_max"),
                job.get("url"),
                job.get("source", "adzuna"),
            ),
        )
        conn.commit()
        return cursor.lastrowid


def save_match(cv_id: int, job_id: int, score: float, cover_letter: str = None) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO matches (cv_id, job_id, match_score, cover_letter)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(cv_id, job_id) DO UPDATE SET
                match_score = excluded.match_score,
                cover_letter = COALESCE(excluded.cover_letter, matches.cover_letter)
            """,
            (cv_id, job_id, score, cover_letter),
        )
        conn.commit()
        return cursor.lastrowid


def update_match_status(match_id: int, status: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE matches SET status = ? WHERE id = ?", (status, match_id)
        )
        conn.commit()


def get_matches_for_cv(cv_id: int) -> list:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT m.id as match_id, m.match_score, m.cover_letter, m.status,
                   j.title, j.company, j.location, j.url, j.salary_min, j.salary_max
            FROM matches m
            JOIN job_postings j ON j.id = m.job_id
            WHERE m.cv_id = ?
            ORDER BY m.match_score DESC
            """,
            (cv_id,),
        ).fetchall()
        return [dict(r) for r in rows]
