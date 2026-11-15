import os
import sys

import altair as alt
import pandas as pd
import streamlit as st

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.matching import SKILLS_CATALOG, classify_role, skill_in_text
from src.store import get_active_offers
from src.style import inject_css, render_kpi_card

st.set_page_config(page_title="Market Analytics", layout="wide")
inject_css()

BLUE, GREY = "#2F5BFF", "#9CA3AF"


@st.cache_data(ttl=600)
def load_data():
    df = get_active_offers()
    if df.empty:
        return df, pd.DataFrame()
    df["role_family"] = df.apply(lambda r: classify_role(r["title"], r["department"]), axis=1)
    # Pour chaque outil du catalogue : dans quelle part des offres est-il cité ?
    texts = (df["title"] + "\n" + df["description"].fillna("")).tolist()
    rows = []
    for skill in SKILLS_CATALOG:
        count = sum(skill_in_text(skill, t) for t in texts)
        if count:
            rows.append({"Skill": skill, "Offers": count, "Share": count / len(df)})
    skills = pd.DataFrame(rows).sort_values("Offers", ascending=False).head(12)
    return df, skills


def bar_chart(data, y, x, x_title, height=300, highlight_top=False):
    """Bar chart horizontal au style minimaliste de l'app."""
    color = (
        alt.condition(alt.datum[y] == data[y].iloc[0], alt.value(BLUE), alt.value(GREY))
        if highlight_top else alt.value(BLUE)
    )
    return (
        alt.Chart(data)
        .mark_bar(cornerRadiusEnd=4)
        .encode(
            x=alt.X(f"{x}:Q", title=x_title, axis=alt.Axis(grid=True, tickMinStep=1)),
            y=alt.Y(f"{y}:N", sort="-x", title=None, axis=alt.Axis(grid=False)),
            color=color,
            tooltip=list(data.columns),
        )
        .properties(height=height)
        .configure_view(stroke=None)
        .configure_axis(domainColor="#E7E5E0", gridColor="#F3F4F6", gridDash=[2, 2],
                        labelColor="#6B7280", titleColor="#14171F", titleFontSize=12)
    )


def section(title, chart, caption):
    with st.container(border=True):
        st.markdown(f'<div style="font-size: 16px; font-weight: 600; margin-bottom: 16px;">{title}</div>', unsafe_allow_html=True)
        st.altair_chart(chart, width="stretch")
        st.markdown(f'<div style="font-size: 13px; color: var(--text-secondary); margin-top: 8px;">{caption}</div>', unsafe_allow_html=True)


df, skills = load_data()

st.markdown('<div class="hero-title">Market Analytics</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">What French tech companies are actually looking for in interns, based on live offers.</div>', unsafe_allow_html=True)

if df.empty:
    st.warning("Aucune offre en base. Lance d'abord `python -m src.collect` dans le terminal.")
    st.stop()

col1, col2, col3 = st.columns(3)
col1.markdown(render_kpi_card("Live Offers", len(df)), unsafe_allow_html=True)
col2.markdown(render_kpi_card("Companies Hiring", df["company"].nunique()), unsafe_allow_html=True)
paris_share = (df["city"] == "Paris").mean()
col3.markdown(render_kpi_card("Based in Paris", f"{paris_share:.0%}"), unsafe_allow_html=True)

st.write("")
st.write("")

c1, c2 = st.columns(2)
with c1:
    by_company = df["company"].value_counts().head(10).rename_axis("Company").reset_index(name="Offers")
    section("Top Hiring Companies", bar_chart(by_company, "Company", "Offers", "Number of offers"),
            "Companies with the most open internship & work-study offers.")
with c2:
    by_role = df["role_family"].value_counts().rename_axis("Role").reset_index(name="Offers")
    section("Offers by Role", bar_chart(by_role, "Role", "Offers", "Number of offers"),
            "Role families detected from offer titles (keyword rules — refined by AI in a next version).")

st.write("")
c3, c4 = st.columns(2)
with c3:
    by_city = df["city"].value_counts().head(10).rename_axis("City").reset_index(name="Offers")
    section("Offers by City", bar_chart(by_city, "City", "Offers", "Number of offers"),
            "Where the offers are located.")
with c4:
    if not skills.empty:
        section("Most Cited Tools & Skills", bar_chart(skills, "Skill", "Offers", "Offers mentioning it", height=350, highlight_top=True),
                "Share of live offers whose description mentions each tool (whole-word match).")
