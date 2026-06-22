"""
Dashboard de Job Matcher AI.
Arrancar con: streamlit run frontend/app.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from backend.cv_parser import parse_cv_file
from backend.job_scraper import search_jobs
from backend.matcher import rank_jobs
from backend.application_generator import generate_cover_letter
from backend import db

st.set_page_config(page_title="Job Matcher AI", page_icon="🎯", layout="wide")

st.markdown("""
<style>
.match-card {
    border: 1px solid #2a2a2a;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
}
.score-badge {
    font-weight: 700;
    padding: 0.15rem 0.6rem;
    border-radius: 6px;
    background-color: #1e4620;
    color: #8fe89a;
    font-size: 0.85rem;
}
</style>
""", unsafe_allow_html=True)

st.title("🎯 Job Matcher AI")
st.caption("Sube tu CV, busca ofertas reales y genera cartas de presentación personalizadas. "
           "Tú decides cuáles enviar.")

if "cv_id" not in st.session_state:
    st.session_state.cv_id = None
    st.session_state.cv_data = None

# --- Paso 1: subir CV ---
st.header("1. Tu CV")

uploaded_file = st.file_uploader("Sube tu CV en PDF", type=["pdf"])

if uploaded_file is not None and st.button("Analizar CV"):
    with st.spinner("Extrayendo y estructurando tu perfil con el LLM..."):
        tmp_path = f"/tmp/{uploaded_file.name}"
        with open(tmp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        cv_data, raw_text = parse_cv_file(tmp_path)
        cv_id = db.save_cv_profile(cv_data, raw_text)
        st.session_state.cv_id = cv_id
        st.session_state.cv_data = cv_data
    st.success(f"CV analizado y guardado (id #{cv_id})")

if st.session_state.cv_data:
    with st.expander("Ver datos extraídos del CV", expanded=False):
        st.json(st.session_state.cv_data)

st.divider()

# --- Paso 2: buscar ofertas ---
st.header("2. Busca ofertas")

col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    query = st.text_input("¿Qué puesto buscas?", value="AI engineer")
with col2:
    location = st.text_input("Ubicación", value="Valencia")
with col3:
    n_results = st.number_input("Nº de ofertas", min_value=5, max_value=50, value=20)

search_disabled = st.session_state.cv_id is None
if search_disabled:
    st.info("Sube y analiza tu CV primero.")

if st.button("Buscar y matchear ofertas", disabled=search_disabled):
    with st.spinner("Buscando ofertas reales y calculando similitud semántica..."):
        jobs = search_jobs(query, location=location, results=n_results)
        ranked = rank_jobs(st.session_state.cv_data, jobs)

        for job in ranked:
            job_id = db.save_job_posting(job)
            db.save_match(st.session_state.cv_id, job_id, job["match_score"])

    st.success(f"{len(jobs)} ofertas encontradas y matcheadas.")

st.divider()

# --- Paso 3: ver matches y generar cartas ---
st.header("3. Tus mejores matches")

if st.session_state.cv_id:
    matches = db.get_matches_for_cv(st.session_state.cv_id)

    if not matches:
        st.info("Todavía no hay matches. Busca ofertas en el paso 2.")

    for m in matches:
        score_pct = round(m["match_score"] * 100)
        with st.container():
            st.markdown(f"""
            <div class="match-card">
                <span class="score-badge">{score_pct}% match</span>
                &nbsp; <strong>{m['title']}</strong> — {m['company']} ({m['location'] or 'Sin ubicación'})
            </div>
            """, unsafe_allow_html=True)

            c1, c2, c3 = st.columns([1, 1, 3])
            with c1:
                if m["url"]:
                    st.link_button("Ver oferta", m["url"])
            with c2:
                gen_key = f"gen_{m['match_id']}"
                if st.button("Generar carta", key=gen_key):
                    with st.spinner("Redactando carta de presentación..."):
                        job = {"title": m["title"], "company": m["company"], "description": ""}
                        letter = generate_cover_letter(st.session_state.cv_data, job)
                        st.session_state[f"letter_{m['match_id']}"] = letter

            letter_key = f"letter_{m['match_id']}"
            if letter_key in st.session_state or m.get("cover_letter"):
                letter_text = st.session_state.get(letter_key, m.get("cover_letter"))
                st.text_area("Carta de presentación (revísala antes de enviarla)",
                             value=letter_text, height=150, key=f"area_{m['match_id']}")

            status_key = f"status_{m['match_id']}"
            new_status = st.selectbox(
                "Estado", ["matched", "reviewed", "applied", "discarded"],
                index=["matched", "reviewed", "applied", "discarded"].index(m["status"]),
                key=status_key,
            )
            if new_status != m["status"]:
                db.update_match_status(m["match_id"], new_status)
else:
    st.info("Sube tu CV para empezar.")
