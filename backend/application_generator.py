"""
Genera una carta de presentación personalizada para una oferta concreta,
a partir de los datos del CV. Es el paso final del pipeline: prepara la
candidatura, pero el envío queda en manos de la persona (ver README,
sección "Por qué está diseñado así").
"""
import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

COVER_LETTER_PROMPT = """Eres un asistente que escribe cartas de presentación breves y \
honestas, sin frases hechas ni exageraciones. Usa SOLO la información del perfil que se \
te da; no inventes experiencia ni habilidades que no aparezcan.

Perfil del candidato:
- Nombre: {full_name}
- Resumen: {summary}
- Habilidades: {skills}
- Experiencia relevante: {experience}

Oferta de empleo:
- Puesto: {job_title}
- Empresa: {company}
- Descripción: {job_description}

Escribe una carta de presentación en español, de máximo 150 palabras, que:
1. Mencione el puesto concreto y la empresa
2. Conecte 2-3 elementos reales del perfil con los requisitos de la oferta
3. Tenga un tono profesional pero natural, no genérico
4. No incluya placeholders como "[Nombre]" — usa los datos reales proporcionados

Devuelve solo el texto de la carta, sin explicaciones adicionales.
"""


def generate_cover_letter(cv_data: dict, job: dict) -> str:
    skills_text = ", ".join(cv_data.get("skills", []))
    experience_text = "; ".join(
        f"{e.get('role', '')} en {e.get('company', '')}"
        for e in cv_data.get("experience", [])
    )

    prompt = COVER_LETTER_PROMPT.format(
        full_name=cv_data.get("full_name", ""),
        summary=cv_data.get("summary", ""),
        skills=skills_text,
        experience=experience_text,
        job_title=job.get("title", ""),
        company=job.get("company", ""),
        job_description=(job.get("description") or "")[:1000],
    )

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()
