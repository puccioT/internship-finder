import streamlit as st
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.database import init_db, get_internships_sql
from src.matching import calculate_score
from src.llm import get_match_explanation, generate_outreach_message
from src.style import inject_css, render_kpi_card, render_offer_block

st.set_page_config(page_title="Internship Finder", layout="wide", initial_sidebar_state="expanded")
inject_css()


# --- CACHE ---
# Streamlit relance tout le script à chaque clic.
# @st.cache_data garde le résultat en mémoire : la fonction n'est exécutée
# qu'une fois par combinaison d'arguments, puis le résultat est réutilisé.

@st.cache_data
def load_internships():
    """Construit la base SQLite depuis le CSV et la lit — une seule fois."""
    init_db()
    return get_internships_sql()


@st.cache_data(show_spinner=False, ttl=3600)
def cached_explanation(domain, skills, title, company, job_skills, description):
    """Même offre + même profil = pas de nouvel appel à Gemini (pendant 1h)."""
    return get_match_explanation(domain, list(skills), title, company, job_skills, description)


df_internships = load_internships()

# --- SESSION STATE ---
# st.session_state est un dictionnaire qui SURVIT aux relances du script.
# On y stocke les résultats du matching et les pitchs générés,
# sinon ils disparaissent dès qu'on clique sur un autre bouton.
if "results" not in st.session_state:
    st.session_state.results = None   # DataFrame des résultats
    st.session_state.profile = None   # (domaine, compétences) utilisés pour ce matching
    st.session_state.pitches = {}     # id de l'offre -> message LinkedIn généré

# --- HERO SECTION ---
st.markdown('<div class="hero-title">Internship Finder</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Evaluate tech & business roles against your exact skill profile.</div>', unsafe_allow_html=True)
st.markdown(f'<div class="hero-pill">{len(df_internships)} active offers across Europe</div>', unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.markdown('<div class="sidebar-section-title">Your Profile</div>', unsafe_allow_html=True)
selected_domain = st.sidebar.selectbox("Target Domain", df_internships['domain'].unique().tolist())
entered_skills = st.sidebar.text_input("Skills (comma-separated)", "Python, SQL, Figma")

st.sidebar.markdown('<div class="sidebar-section-title" style="margin-top: 24px;">Filters</div>', unsafe_allow_html=True)
locations_list = ["All Locations"] + sorted(df_internships['location'].unique().tolist())
selected_location = st.sidebar.selectbox("Location", locations_list)
contract_list = ["Any"] + sorted(df_internships['contract_type'].unique().tolist())
selected_contract = st.sidebar.selectbox("Contract Type", contract_list)
english_list = ["Any"] + sorted(df_internships['english_level'].unique().tolist())
selected_english = st.sidebar.selectbox("English Level", english_list)

st.sidebar.write("")
run_engine = st.sidebar.button("Run matching engine", type="primary", width="stretch")

# Le bouton ne sert plus qu'à CALCULER et STOCKER les résultats.
# L'affichage, lui, se fait plus bas à partir de session_state.
if run_engine:
    skills_list = [c.strip() for c in entered_skills.split(',') if c.strip()]
    st.session_state.results = calculate_score(
        df_internships, selected_domain, selected_location, selected_contract, selected_english, skills_list
    )
    st.session_state.profile = (selected_domain, skills_list)
    st.session_state.pitches = {}  # nouveau matching = on repart de zéro

# --- RESULTS ---
df_results = st.session_state.results

if df_results is None:
    st.markdown("""
    <div style="text-align: center; padding: 64px 24px; color: var(--text-secondary);">
        <h3 style="font-size: 16px; font-weight: 500; margin: 0;">Ready to find your next role</h3>
        <p style="font-size: 14px; margin-top: 4px;">Configure your profile in the sidebar and run the matching engine.</p>
    </div>
    """, unsafe_allow_html=True)

elif df_results.empty:
    st.markdown("""
    <div style="text-align: center; padding: 64px 24px; color: var(--text-secondary);">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom: 16px; opacity: 0.5;">
            <circle cx="11" cy="11" r="8"></circle>
            <path d="m21 21-4.3-4.3"></path>
        </svg>
        <h3 style="font-size: 16px; font-weight: 500; margin: 0;">No internships found</h3>
        <p style="font-size: 14px; margin-top: 4px;">Try adjusting your strict filters (Location, Contract, English) to 'Any'.</p>
    </div>
    """, unsafe_allow_html=True)

else:
    # On utilise le profil du DERNIER matching lancé, pas ce qui est
    # actuellement tapé dans la sidebar (sinon pitch et résultats divergent).
    profile_domain, profile_skills = st.session_state.profile

    col1, col2, col3 = st.columns(3)
    col1.markdown(render_kpi_card("Offers Found", len(df_results)), unsafe_allow_html=True)
    col2.markdown(render_kpi_card("Top Match Score", f"{df_results['score'].max()} pts"), unsafe_allow_html=True)
    strong_matches = len(df_results[df_results['score'] >= 50])
    col3.markdown(render_kpi_card("Strong Matches", f"{strong_matches} roles"), unsafe_allow_html=True)

    st.write("")
    st.write("")
    st.markdown('<div style="font-size: 18px; font-weight: 600; margin-bottom: 16px;">Top Recommendations</div>', unsafe_allow_html=True)

    top_3 = df_results.head(3)
    user_skills_lower = [s.lower() for s in profile_skills]

    for index, row in top_3.iterrows():
        req_skills = [s.strip() for s in str(row['skills']).split(';') if s.strip()]
        matched = [s for s in req_skills if s.lower() in user_skills_lower]
        missing = [s for s in req_skills if s.lower() not in user_skills_lower]

        with st.container(border=True):
            with st.spinner(f"AI analyzing match for {row['company']}..."):
                explanation = cached_explanation(
                    profile_domain, tuple(profile_skills),
                    row['title'], row['company'], row['skills'], row['description']
                )

            st.markdown(render_offer_block(row, matched, missing, explanation), unsafe_allow_html=True)

            if st.button("Generate LinkedIn Pitch", key=f"pitch_{row['id']}", type="secondary"):
                with st.spinner("Drafting message..."):
                    st.session_state.pitches[row['id']] = generate_outreach_message(
                        profile_domain, profile_skills, row['title'], row['company'], row['description']
                    )

            # Affiché à chaque relance tant qu'il est dans session_state
            if row['id'] in st.session_state.pitches:
                st.text_area("Draft:", st.session_state.pitches[row['id']], height=120, key=f"draft_{row['id']}")

    st.write("")
    st.markdown('<div style="font-size: 18px; font-weight: 600; margin-bottom: 16px;">Full Database Ranking</div>', unsafe_allow_html=True)
    st.dataframe(df_results[['score', 'title', 'company', 'location', 'domain', 'contract_type', 'english_level', 'skills']], width="stretch")
