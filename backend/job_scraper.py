"""
Búsqueda de ofertas de empleo vía Adzuna API (https://developer.adzuna.com/).

Por qué Adzuna y no scraping directo de LinkedIn/Indeed:
- Adzuna ofrece una API pública, gratuita (hasta cierto volumen) y legal,
  con buena cobertura en España y agregando muchas fuentes (incluido Indeed).
- Scrapear LinkedIn/Indeed directamente viola sus Términos de Servicio y
  puede acabar bloqueando la cuenta personal del usuario. No lo incluimos
  por diseño, no por limitación técnica.

Para extender a otras fuentes (Infojobs API, Jooble API, etc.) basta con
añadir una función `search_jobs_<fuente>()` con la misma forma de salida
que `search_jobs()` y combinarla en `job_scraper_aggregate()`.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")
ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"


def search_jobs(query: str, location: str = "", country: str = "es",
                 results: int = 20, max_days_old: int = 30) -> list[dict]:
    """Busca ofertas de empleo en Adzuna.

    Args:
        query: texto de búsqueda, p.ej. "AI engineer" o "ingeniero machine learning"
        location: ciudad o región, p.ej. "Valencia"
        country: código de país de Adzuna (es, gb, us, de, fr...)
        results: número máximo de resultados
        max_days_old: antigüedad máxima de la oferta en días

    Returns:
        Lista de dicts con: external_id, title, company, location, description,
        salary_min, salary_max, url, source
    """
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        raise EnvironmentError(
            "Faltan ADZUNA_APP_ID / ADZUNA_APP_KEY en el .env. "
            "Consigue credenciales gratuitas en https://developer.adzuna.com/"
        )

    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "what": query,
        "where": location,
        "results_per_page": results,
        "max_days_old": max_days_old,
        "content-type": "application/json",
    }

    url = ADZUNA_BASE_URL.format(country=country)
    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    jobs = []
    for item in data.get("results", []):
        jobs.append({
            "external_id": str(item.get("id")),
            "title": item.get("title", "").strip(),
            "company": item.get("company", {}).get("display_name", "Empresa no especificada"),
            "location": item.get("location", {}).get("display_name", ""),
            "description": item.get("description", ""),
            "salary_min": item.get("salary_min"),
            "salary_max": item.get("salary_max"),
            "url": item.get("redirect_url"),
            "source": "adzuna",
        })
    return jobs


if __name__ == "__main__":
    results = search_jobs("AI engineer", location="Valencia")
    for job in results[:5]:
        print(f"- {job['title']} @ {job['company']} ({job['location']})")
