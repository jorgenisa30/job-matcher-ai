"""
Matching semántico CV <-> ofertas de empleo usando embeddings locales
(sentence-transformers), sin necesidad de API keys de pago para esta parte.

Por qué local y no vía API: el matching se ejecuta sobre muchas ofertas a la
vez, así que tenerlo local evita coste y latencia de red por cada comparación.
"""
import numpy as np
from sentence_transformers import SentenceTransformer

_model = None


def _get_model() -> SentenceTransformer:
    """Carga el modelo de embeddings de forma perezosa (solo la primera vez)."""
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def cv_data_to_text(cv_data: dict) -> str:
    """Convierte el JSON estructurado del CV en un texto plano para embeddear."""
    parts = [cv_data.get("summary", "")]

    skills = cv_data.get("skills", [])
    if skills:
        parts.append("Habilidades: " + ", ".join(skills))

    for exp in cv_data.get("experience", []):
        parts.append(f"{exp.get('role', '')} en {exp.get('company', '')}: {exp.get('description', '')}")

    for edu in cv_data.get("education", []):
        parts.append(f"{edu.get('degree', '')} - {edu.get('institution', '')}")

    return "\n".join(p for p in parts if p)


def embed_text(text: str) -> np.ndarray:
    model = _get_model()
    return model.encode(text, normalize_embeddings=True)


def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    # Los vectores ya están normalizados, así que el producto escalar = similitud coseno
    return float(np.dot(vec_a, vec_b))


def rank_jobs(cv_data: dict, jobs: list[dict]) -> list[dict]:
    """Calcula un match_score (0-1) entre el CV y cada oferta, y las ordena.

    Devuelve la misma lista de jobs, cada uno con una clave extra 'match_score',
    ordenada de mayor a menor relevancia.
    """
    cv_text = cv_data_to_text(cv_data)
    cv_embedding = embed_text(cv_text)

    scored_jobs = []
    for job in jobs:
        job_text = f"{job.get('title', '')}\n{job.get('description', '')}"
        job_embedding = embed_text(job_text)
        score = cosine_similarity(cv_embedding, job_embedding)

        job_with_score = dict(job)
        job_with_score["match_score"] = round(score, 4)
        scored_jobs.append(job_with_score)

    return sorted(scored_jobs, key=lambda j: j["match_score"], reverse=True)


if __name__ == "__main__":
    sample_cv = {
        "summary": "Ingeniero especializado en IA, RAG y sistemas multi-agente.",
        "skills": ["Python", "LLMs", "RAG", "n8n", "SQL"],
        "experience": [{"role": "AI Engineer", "company": "AHORA", "description": "Desarrollo de sistemas RAG y agentes de IA"}],
        "education": [],
    }
    sample_jobs = [
        {"title": "Machine Learning Engineer", "description": "Buscamos experto en LLMs y RAG"},
        {"title": "Camarero de sala", "description": "Atención al cliente en restaurante"},
    ]
    ranked = rank_jobs(sample_cv, sample_jobs)
    for j in ranked:
        print(f"{j['match_score']:.3f} - {j['title']}")
