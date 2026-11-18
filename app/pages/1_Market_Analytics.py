import os
import sys

import altair as alt
import pandas as pd
import streamlit as st

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.matching import ROLE_FAMILY_NAMES, score_offer
from src.offers import count_skills, load_prepared_offers
from src.style import inject_css, render_kpi_card

st.set_page_config(page_title="Market Analytics", layout="wide")
inject_css()

ACCENT, NEUTRAL = "#2F5BFF", "#C9CDD6"   # 1 couleur de mise en avant + 1 gris neutre


@st.cache_data(ttl=600)
def load_data():
    return load_prepared_offers()


def bar_chart(data, label, value, value_title, highlight=None, fmt="d", height=None):
    """
    Bar chart horizontal minimaliste : barres fines aux bouts arrondis, grille discrète,
    tooltip au survol. `highlight` = la barre à mettre en avant (les autres en gris).
    """
    color = (alt.condition(alt.datum[label] == highlight, alt.value(ACCENT), alt.value(NEUTRAL))
             if highlight is not None else alt.value(ACCENT))
    base = alt.Chart(data).encode(
        y=alt.Y(f"{label}:N", sort="-x", title=None, axis=alt.Axis(labelLimit=220, labelPadding=8, ticks=False, domain=False)),
        x=alt.X(f"{value}:Q", title=value_title, axis=alt.Axis(grid=True, tickCount=5, format=fmt, domain=False)),
    )
    bars = base.mark_bar(cornerRadiusEnd=4, height=14).encode(
        color=color, tooltip=[alt.Tooltip(f"{label}:N"), alt.Tooltip(f"{value}:Q", format=fmt)]
    )
    # Valeur affichée au bout de chaque barre (le texte reste gris, jamais de la couleur de la barre)
    labels = base.mark_text(align="left", dx=4, color="#6B7280", fontSize=11).encode(
        text=alt.Text(f"{value}:Q", format=fmt)
    )
    return (
        (bars + labels)
        .properties(height=height or max(140, 26 * len(data)))
        .configure_view(stroke=None)
        .configure_axis(gridColor="#F1F2F4", labelColor="#6B7280", titleColor="#6B7280",
                        titleFontSize=11, titleFontWeight="normal", labelFontSize=12)
    )


def section(title, caption, chart=None):
    with st.container(border=True):
        st.markdown(f'<div style="font-size: 16px; font-weight: 600;">{title}</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size: 13px; color: var(--text-secondary); margin: 4px 0 12px;">{caption}</div>', unsafe_allow_html=True)
        if chart is not None:
            st.altair_chart(chart, width="stretch")


df_all = load_data()

st.markdown('<div class="hero-title">Market Analytics</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">What tech companies actually ask from interns and apprentices, based on live offers analysed by AI.</div>', unsafe_allow_html=True)

if df_all.empty:
    st.warning("Aucune offre en base. Lance d'abord `python -m src.collect` puis `python -m src.extract`.")
    st.stop()

# --- FILTRES (une seule ligne, au-dessus des graphiques) ---
f1, f2, f3 = st.columns([1, 1, 2])
countries = df_all["country"].value_counts().index.tolist()
country = f1.selectbox("Country", ["All Countries"] + countries,
                       index=countries.index("France") + 1 if "France" in countries else 0)
contract = f2.selectbox("Contract", ["Any", "Stage", "Alternance"])
families = f3.multiselect("Role families (for skills charts)", ROLE_FAMILY_NAMES,
                          default=["Product", "Strategy & Ops", "Data"])

df = df_all if country == "All Countries" else df_all[df_all["country"] == country]
if contract != "Any":
    df = df[df["contract_type"] == contract]
if df.empty:
    st.info("Aucune offre pour ces filtres.")
    st.stop()

in_families = df[df["role_family"].isin(families) | df["secondary_family"].isin(families)] if families else df

# --- KPIs ---
product_share = (df["role_family"] == "Product").mean()
median_months = df["ai_duration_months"].dropna().median()
k1, k2, k3, k4 = st.columns(4)
k1.markdown(render_kpi_card("Live Offers", len(df)), unsafe_allow_html=True)
k2.markdown(render_kpi_card("Companies Hiring", df["company"].nunique()), unsafe_allow_html=True)
k3.markdown(render_kpi_card("Pure Product Roles", f"{product_share:.0%}"), unsafe_allow_html=True)
k4.markdown(render_kpi_card("Typical Duration", f"{median_months:.0f} months" if pd.notna(median_months) else "n/a"), unsafe_allow_html=True)

st.write("")

# --- 1. Familles de poste ---
c1, c2 = st.columns(2)
with c1:
    by_family = df["role_family"].value_counts().rename_axis("Role").reset_index(name="Offers")
    section("Offers by Role Family",
            "Main function of each offer, judged by AI from the missions (not the title). Product highlighted.",
            bar_chart(by_family, "Role", "Offers", "Number of offers", highlight="Product"))

# --- 2. Compétences demandées ---
with c2:
    skills = pd.DataFrame(count_skills(in_families["required_skills"]), columns=["Skill", "Offers"])
    if not skills.empty:
        skills["Share"] = skills["Offers"] / len(in_families)
        section("Most Requested Skills",
                f"Share of the {len(in_families)} offers in {', '.join(families) or 'all families'} requiring each skill.",
                bar_chart(skills.head(12), "Skill", "Share", "Share of offers", fmt=".0%"))

st.write("")

# --- 3. Tes manques prioritaires (si un profil a été saisi sur la page principale) ---
c3, c4 = st.columns(2)
with c3:
    profile = st.session_state.get("profile")
    if profile:
        targets, user_skills = profile
        targeted = df[df["role_family"].isin(targets) | df["secondary_family"].isin(targets)]
        missing = [score_offer(row, targets, user_skills)[2] for _, row in targeted.iterrows()]
        gaps = pd.DataFrame(count_skills(missing), columns=["Skill", "Offers"])
        if not gaps.empty:
            section("Your Skill Gaps",
                    f"Skills you don't list that are most often required in the {len(targeted)} "
                    f"{' / '.join(targets)} offers. Learn the top ones first.",
                    bar_chart(gaps.head(8), "Skill", "Offers", "Offers requiring it", highlight=gaps["Skill"].iloc[0]))
        else:
            section("Your Skill Gaps", "You cover every skill requested in your target offers. 🎯")
    else:
        section("Your Skill Gaps",
                "Run the matching engine on the main page first: your profile will be used here to rank "
                "the skills you should learn next.")

# --- 4. Entreprises ---
with c4:
    by_company = df["company"].value_counts().head(10).rename_axis("Company").reset_index(name="Offers")
    section("Top Hiring Companies", "Companies with the most open internship & work-study offers.",
            bar_chart(by_company, "Company", "Offers", "Number of offers"))
