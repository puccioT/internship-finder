import os
import sys

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
@st.cache_data(ttl=600)
def load_offers():
    """Lit les offres actives en base (rafraîchies par `python -m src.collect`)."""
    df = get_active_offers()
    if not df.empty:
        df["role_family"] = df.apply(lambda r: classify_role(r["title"], r["department"]), axis=1)
    return df


@st.cache_data(show_spinner=False, ttl=3600)
def cached_explanation(domain, skills, title, company, matched, description):
    return get_match_explanation(domain, list(skills), title, company, matched, description)


df_offers = load_offers()

if df_offers.empty:
    st.warning("Aucune offre en base. Lance d'abord `python -m src.collect` dans le terminal.")
    st.stop()

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

st.sidebar.write("")
run_engine = st.sidebar.button("Run matching engine", type="primary", width="stretch")

if run_engine:
    skills_list = [c.strip() for c in entered_skills.split(',') if c.strip()]
    st.session_state.results = calculate_score(
        df_offers, selected_family, selected_location, selected_contract, skills_list
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
    strong = (df_results["score"] >= 60).sum()   # bonne famille + au moins 1 compétence
    col3.markdown(render_kpi_card("Strong Matches", f"{strong} offers"), unsafe_allow_html=True)

    st.write("")
    st.write("")
    st.markdown('<div style="font-size: 18px; font-weight: 600; margin-bottom: 16px;">Top Recommendations</div>', unsafe_allow_html=True)

    for _, row in df_results.head(3).iterrows():
        offer_id = row["source_id"]
        matched = row["matched_skills"]

        # Carte : description raccourcie, ville + pays d'origine
        card = row.copy()
        desc = str(row["description"])
        card["description"] = desc[:DESCRIPTION_PREVIEW] + ("…" if len(desc) > DESCRIPTION_PREVIEW else "")

        with st.container(border=True):
            with st.spinner(f"AI analyzing match for {row['company']}..."):
                explanation = cached_explanation(
                    profile_family, tuple(profile_skills), row["title"], row["company"],
                    ";".join(matched), desc[:DESCRIPTION_FOR_LLM],
                )
            # Les compétences "manquantes" ne sont pas encore connues (phase 3 : extraction LLM)
            st.markdown(render_offer_block(card, matched, [], explanation), unsafe_allow_html=True)

            b1, b2 = st.columns([1, 1])
            b1.link_button("View offer ↗", row["url"], width="stretch")
            if b2.button("Generate LinkedIn Pitch", key=f"pitch_{offer_id}", type="secondary", width="stretch"):
                with st.spinner("Drafting message..."):
                    st.session_state.pitches[offer_id] = generate_outreach_message(
                        profile_family, profile_skills, row["title"], row["company"], desc[:DESCRIPTION_FOR_LLM]
                    )
            if offer_id in st.session_state.pitches:
                st.text_area("Draft:", st.session_state.pitches[offer_id], height=140, key=f"draft_{offer_id}")

    st.write("")
    st.markdown('<div style="font-size: 18px; font-weight: 600; margin-bottom: 16px;">All Matching Offers</div>', unsafe_allow_html=True)
    table = df_results[["score", "title", "company", "city", "role_family", "contract_type", "matched_skills", "url"]].copy()
    table["matched_skills"] = table["matched_skills"].apply(", ".join)
    st.dataframe(
        table,
        width="stretch",
        hide_index=True,
        column_config={
            "url": st.column_config.LinkColumn("Link", display_text="Open ↗"),
            "role_family": "Role",
            "contract_type": "Contract",
            "matched_skills": "Your skills found",
        },
    )
