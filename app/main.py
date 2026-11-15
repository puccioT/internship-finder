import json
import os
import sys

import pandas as pd
import streamlit as st

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.llm import generate_outreach_message, get_match_explanation
from src.matching import ROLE_FAMILY_NAMES, calculate_score, classify_role
from src.store import get_active_offers
from src.style import inject_css, render_kpi_card, render_offer_block

st.set_page_config(page_title="Internship Finder", layout="wide", initial_sidebar_state="expanded")
inject_css()

DESCRIPTION_PREVIEW = 350     # caractères de description affichés sur une carte
DESCRIPTION_FOR_LLM = 3000    # caractères envoyés à Gemini (les descriptions réelles sont longues)


# --- CACHE ---
def parse_list(value):
    """Les listes sont stockées en JSON dans SQLite : '["SQL", "Excel"]' -> ['SQL', 'Excel']."""
    return json.loads(value) if isinstance(value, str) and value else []


@st.cache_data(ttl=600)
def load_offers():
    """
    Lit les offres actives et prépare les colonnes utilisées par l'app.
    Si le LLM a analysé l'offre (src/extract.py), on utilise sa fiche ;
    sinon on retombe sur les règles par mots-clés.
    """
    df = get_active_offers()
    if df.empty:
        return df
    keyword_family = df.apply(lambda r: classify_role(r["title"], r["department"]), axis=1)
    df["role_family"] = df["ai_role_family"].fillna(keyword_family)
    df["required_skills"] = df["ai_skills"].apply(parse_list)
    df["languages"] = df["ai_languages"].apply(parse_list)
    df["remote"] = df["ai_remote"].fillna("Unknown")
    df["summary"] = df["ai_summary"].fillna("")
    return df


@st.cache_data(show_spinner=False, ttl=3600)
def cached_explanation(target, skills, title, company, family, summary, required, matched, missing):
    return get_match_explanation(target, list(skills), title, company, family, summary,
                                 list(required), list(matched), list(missing))


def offer_details(row):
    """Ligne d'infos pratiques : 'Stage · 6 months · Start: January 2027 · Hybrid'."""
    parts = [row["contract_type"]]
    if pd.notna(row["ai_duration_months"]):
        parts.append(f"{int(row['ai_duration_months'])} months")
    if row["ai_start_date"] and row["ai_start_date"] != "Unknown" and pd.notna(row["ai_start_date"]):
        parts.append(f"Start: {row['ai_start_date']}")
    if row["remote"] != "Unknown":
        parts.append(row["remote"])
    return " · ".join(parts)


df_offers = load_offers()

if df_offers.empty:
    st.warning("Aucune offre en base. Lance d'abord `python -m src.collect` dans le terminal.")
    st.stop()

not_analysed = df_offers["extracted_at"].isna().sum()
if not_analysed:
    st.info(f"{not_analysed} offres pas encore analysées par l'IA (matching approximatif). "
            "Lance `python -m src.extract` dans le terminal.")

# --- SESSION STATE ---
if "results" not in st.session_state:
    st.session_state.results = None
    st.session_state.profile = None
    st.session_state.pitches = {}

# --- HERO ---
st.markdown('<div class="hero-title">Internship Finder</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Real internship & work-study offers from top French tech companies, ranked against your profile.</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="hero-pill">{len(df_offers)} live offers · {df_offers["company"].nunique()} companies</div>',
    unsafe_allow_html=True,
)

# --- SIDEBAR ---
st.sidebar.markdown('<div class="sidebar-section-title">Your Profile</div>', unsafe_allow_html=True)
selected_family = st.sidebar.selectbox("Target Role", ROLE_FAMILY_NAMES)
entered_skills = st.sidebar.text_input("Skills (comma-separated)", "SQL, Python, Figma, Excel, Notion")

st.sidebar.markdown('<div class="sidebar-section-title" style="margin-top: 24px;">Filters</div>', unsafe_allow_html=True)
# Villes triées par nombre d'offres (Paris en premier)
cities = df_offers["city"].value_counts().index.tolist()
selected_location = st.sidebar.selectbox("Location", ["All Locations"] + cities)
selected_contract = st.sidebar.selectbox("Contract Type", ["Any", "Stage", "Alternance"])
selected_remote = st.sidebar.selectbox("Remote", ["Any", "On-site", "Hybrid", "Full remote"])

st.sidebar.write("")
run_engine = st.sidebar.button("Run matching engine", type="primary", width="stretch")

if run_engine:
    skills_list = [c.strip() for c in entered_skills.split(',') if c.strip()]
    st.session_state.results = calculate_score(
        df_offers, selected_family, selected_location, selected_contract, selected_remote, skills_list
    )
    st.session_state.profile = (selected_family, skills_list)
    st.session_state.pitches = {}

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
        <h3 style="font-size: 16px; font-weight: 500; margin: 0;">No offers found</h3>
        <p style="font-size: 14px; margin-top: 4px;">Try setting Location or Contract Type to 'Any'.</p>
    </div>
    """, unsafe_allow_html=True)

else:
    profile_family, profile_skills = st.session_state.profile

    col1, col2, col3 = st.columns(3)
    col1.markdown(render_kpi_card("Offers Found", len(df_results)), unsafe_allow_html=True)
    col2.markdown(render_kpi_card("In Your Target Role", f"{(df_results['role_family'] == profile_family).sum()} offers"), unsafe_allow_html=True)
    strong = (df_results["score"] >= 75).sum()   # bonne famille + au moins la moitié des compétences
    col3.markdown(render_kpi_card("Strong Matches (75+)", f"{strong} offers"), unsafe_allow_html=True)

    st.write("")
    st.write("")
    st.markdown('<div style="font-size: 18px; font-weight: 600; margin-bottom: 16px;">Top Recommendations</div>', unsafe_allow_html=True)

    for _, row in df_results.head(3).iterrows():
        offer_id = row["source_id"]
        matched, missing = row["matched_skills"], row["missing_skills"]
        desc = str(row["description"])

        # Carte : résumé des missions (LLM) plutôt que le début de la description
        card = row.copy()
        card["contract_type"] = offer_details(row)
        card["location"] = row["city"]
        if row["summary"]:
            card["description"] = row["summary"]
        else:
            card["description"] = desc[:DESCRIPTION_PREVIEW] + ("…" if len(desc) > DESCRIPTION_PREVIEW else "")
        if row["languages"]:
            card["description"] += " — Languages: " + ", ".join(row["languages"])

        with st.container(border=True):
            with st.spinner(f"AI analyzing match for {row['company']}..."):
                explanation = cached_explanation(
                    profile_family, tuple(profile_skills), row["title"], row["company"],
                    row["role_family"], row["summary"] or desc[:DESCRIPTION_FOR_LLM],
                    tuple(row["required_skills"]), tuple(matched), tuple(missing),
                )
            st.markdown(render_offer_block(card, matched, missing, explanation), unsafe_allow_html=True)

            b1, b2 = st.columns([1, 1])
            b1.link_button("View offer ↗", row["url"], width="stretch")
            if b2.button("Generate LinkedIn Pitch", key=f"pitch_{offer_id}", type="secondary", width="stretch"):
                with st.spinner("Drafting message..."):
                    st.session_state.pitches[offer_id] = generate_outreach_message(
                        profile_family, profile_skills, row["title"], row["company"],
                        row["summary"] or desc[:DESCRIPTION_FOR_LLM],
                    )
            if offer_id in st.session_state.pitches:
                st.text_area("Draft:", st.session_state.pitches[offer_id], height=140, key=f"draft_{offer_id}")

    st.write("")
    st.markdown('<div style="font-size: 18px; font-weight: 600; margin-bottom: 16px;">All Matching Offers</div>', unsafe_allow_html=True)
    table = df_results[["score", "title", "company", "city", "role_family", "contract_type",
                        "ai_duration_months", "ai_start_date", "remote", "matched_skills", "missing_skills", "url"]].copy()
    table["matched_skills"] = table["matched_skills"].apply(", ".join)
    table["missing_skills"] = table["missing_skills"].apply(", ".join)
    st.dataframe(
        table,
        width="stretch",
        hide_index=True,
        column_config={
            "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d"),
            "url": st.column_config.LinkColumn("Link", display_text="Open ↗"),
            "role_family": "Role",
            "contract_type": "Contract",
            "ai_duration_months": st.column_config.NumberColumn("Months", format="%d"),
            "ai_start_date": "Start",
            "remote": "Remote",
            "matched_skills": "Skills you have",
            "missing_skills": "Skills to develop",
        },
    )
