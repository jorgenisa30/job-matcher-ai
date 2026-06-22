"""
Extrae texto de un CV en PDF y lo estructura en JSON usando Claude.
"""
import json
import os
import pdfplumber
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

EXTRACTION_PROMPT = """Eres un sistema de extracción de datos de CVs. Analiza el siguiente \
texto extraído de un CV y devuelve ÚNICAMENTE un objeto JSON (sin texto adicional, sin \
backticks de markdown) con esta estructura exacta:

{{
  "full_name": "",
  "email": "",
  "phone": "",
  "summary": "resumen de 2-3 frases del perfil profesional",
  "skills": ["lista de skills técnicas y herramientas mencionadas"],
  "experience": [
    {{"role": "", "company": "", "period": "", "description": ""}}
  ],
  "education": [
    {{"degree": "", "institution": "", "period": ""}}
  ],
  "languages": ["idioma (nivel)"]
}}

Si un campo no aparece en el CV, usa una cadena vacía o lista vacía. No inventes datos.

Texto del CV:
---
{cv_text}
---
"""


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extrae todo el texto de un PDF, página a página."""
    text_chunks = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_chunks.append(page_text)
    return "\n".join(text_chunks)


def parse_cv_with_llm(cv_text: str) -> dict:
    """Envía el texto del CV a Claude y devuelve un dict estructurado."""
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[
            {"role": "user", "content": EXTRACTION_PROMPT.format(cv_text=cv_text)}
        ],
    )

    raw_response = message.content[0].text.strip()

    # Por si el modelo envuelve la respuesta en ```json ... ```
    if raw_response.startswith("```"):
        raw_response = raw_response.strip("`")
        raw_response = raw_response.replace("json\n", "", 1)

    try:
        return json.loads(raw_response)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"No se pudo parsear la respuesta del modelo como JSON: {e}\n"
            f"Respuesta recibida: {raw_response[:500]}"
        )


def parse_cv_file(pdf_path: str) -> tuple[dict, str]:
    """Pipeline completo: PDF -> texto -> JSON estructurado.

    Devuelve (cv_data, raw_text).
    """
    raw_text = extract_text_from_pdf(pdf_path)
    if not raw_text.strip():
        raise ValueError(
            "No se pudo extraer texto del PDF. Si es un CV escaneado (imagen), "
            "necesitarás OCR antes de este paso."
        )
    cv_data = parse_cv_with_llm(raw_text)
    return cv_data, raw_text


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Uso: python cv_parser.py ruta/al/cv.pdf")
        sys.exit(1)

    data, _ = parse_cv_file(sys.argv[1])
    print(json.dumps(data, indent=2, ensure_ascii=False))
