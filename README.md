# Job Matcher AI

Sistema que analiza tu CV, lo compara semánticamente con ofertas de empleo reales (vía la API de Adzuna) y genera una carta de presentación personalizada para cada oferta relevante — lista para que la revises y envíes.

## Por qué está diseñado así (decisión deliberada)

Este proyecto **no envía candidaturas automáticamente sin supervisión**. Genera el match y la carta personalizada, y deja un paso final de revisión humana antes de aplicar. Esto es intencional:

- LinkedIn e Indeed prohíben la automatización de candidaturas en sus Términos de Servicio. Un bot que aplica sin supervisión puede acabar con la cuenta del usuario bloqueada.
- Un sistema que decide "candidaturas masivas sin revisión" es mala práctica de producto, no solo un riesgo legal: nadie quiere 50 candidaturas genéricas saliendo en su nombre.
- El diseño "human-in-the-loop" (la IA prepara, la persona decide) es el patrón que de hecho usan productos reales de HR-Tech. Mostrar que entiendes esto es más valioso en una entrevista que un bot que infringe ToS.

## Arquitectura

```
┌─────────────────┐
│  1. CV Parser    │  PDF → texto → Claude API → JSON estructurado
└────────┬─────────┘
         │
┌────────▼─────────┐
│  2. Job Search    │  Adzuna API → ofertas reales (título, descripción, ubicación, salario)
└────────┬─────────┘
         │
┌────────▼─────────┐
│  3. Matcher        │  Embeddings locales (sentence-transformers) → similitud coseno CV vs oferta
└────────┬─────────┘
         │
┌────────▼─────────┐
│  4. App Generator  │  Claude API → carta de presentación personalizada por oferta
└────────┬─────────┘
         │
┌────────▼─────────┐
│  5. SQLite          │  Guarda CV, ofertas, matches y estado de cada candidatura
└────────┬─────────┘
         │
┌────────▼─────────┐
│  6. Dashboard        │  Streamlit: sube CV, ve matches, revisa carta, marca como "enviada"
└─────────────────┘
```

## Stack

- **Backend**: FastAPI
- **LLM**: Claude API (Anthropic) — extracción de CV y generación de cartas
- **Embeddings**: `sentence-transformers` (local, sin coste, sin API key)
- **Búsqueda de empleo**: [Adzuna API](https://developer.adzuna.com/) (gratis, cubre España)
- **Base de datos**: SQLite
- **Frontend**: Streamlit

## Setup

### 1. Clona e instala dependencias

```bash
git clone <tu-repo>
cd job-matcher-ai
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Variables de entorno

```bash
cp .env.example .env
```

Rellena en `.env`:
- `ANTHROPIC_API_KEY` — desde [console.anthropic.com](https://console.anthropic.com)
- `ADZUNA_APP_ID` y `ADZUNA_APP_KEY` — gratis en [developer.adzuna.com](https://developer.adzuna.com/)

### 3. Inicializa la base de datos

```bash
python db/init_db.py
```

Esto crea `job_matcher.db` localmente (no se sube a Git, ver `.gitignore`).

### 4. Arranca el backend

```bash
uvicorn backend.main:app --reload
```

### 5. Arranca el dashboard

```bash
streamlit run frontend/app.py
```

Abre `http://localhost:8501`, sube tu CV en PDF, define qué puesto buscas y deja que el sistema encuentre y rankee ofertas.

## Estructura del repo

```
job-matcher-ai/
├── backend/
│   ├── main.py              # Endpoints FastAPI
│   ├── cv_parser.py         # Extracción de CV con Claude
│   ├── job_scraper.py       # Búsqueda de ofertas (Adzuna API)
│   ├── matcher.py           # Embeddings + similitud semántica
│   ├── application_generator.py  # Generación de carta de presentación
│   └── db.py                # Capa de acceso a SQLite
├── db/
│   ├── schema.sql           # Estructura de tablas (versionado, no el .db)
│   └── init_db.py           # Script de inicialización
├── frontend/
│   └── app.py                # Dashboard Streamlit
├── n8n_workflow/
│   └── daily_job_search.json # Workflow de ejemplo: búsqueda diaria + notificación
├── sample_data/
│   └── sample_cv_text.txt    # CV de ejemplo para probar sin subir un PDF
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Extensión a producción

Este proyecto usa SQLite porque es un MVP/portfolio. Para producción:
- Migrar `db/schema.sql` a PostgreSQL o SQL Server (el esquema es compatible casi sin cambios)
- Sustituir Adzuna por agregadores adicionales (Infojobs API, Jooble API) según cobertura geográfica
- Añadir cola de tareas (Celery/RQ) si el volumen de CVs/ofertas crece
- Añadir autenticación si hay múltiples usuarios

## Limitaciones conocidas

- Adzuna no cubre el 100% de las ofertas de LinkedIn/Indeed — es la fuente que sí ofrece una API legal y estable.
- La generación de cartas depende de la calidad de extracción del CV; revisa siempre antes de enviar.
- No hay envío automático de candidaturas (ver sección de diseño arriba).
