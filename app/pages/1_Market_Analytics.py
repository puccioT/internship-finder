import streamlit as st
import pandas as pd
import altair as alt
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.database import get_internships_sql
from src.style import inject_css, render_kpi_card

st.set_page_config(page_title="Market Analytics", layout="wide")
inject_css()

df = get_internships_sql()

st.markdown('<div class="hero-title">Market Analytics</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Macro overview of the European tech internship market.</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
col1.markdown(render_kpi_card("Tracked Offers", len(df)), unsafe_allow_html=True)
col2.markdown(render_kpi_card("Top Hiring City", df['location'].mode()[0]), unsafe_allow_html=True)
col3.markdown(render_kpi_card("Top Domain", df['domain'].mode()[0]), unsafe_allow_html=True)

st.write("")
st.write("")

# Configure Altair strictly for SaaS minimalism
def get_chart_theme():
    return {
        "config": {
            "view": {"stroke": "transparent"},
            "axis": {
                "domainColor": "#E7E5E0",
                "gridColor": "#F3F4F6",
                "gridDash": [2, 2],
                "labelColor": "#6B7280",
                "labelFont": "Inter",
                "titleFont": "Inter",
                "titleColor": "#14171F",
                "titleFontSize": 12,
                "titleFontWeight": 600,
            }
        }
    }
alt.themes.register("saas_theme", get_chart_theme)
alt.themes.enable("saas_theme")

col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    with st.container(border=True):
        st.markdown('<div style="font-size: 16px; font-weight: 600; margin-bottom: 16px;">Offers by Location</div>', unsafe_allow_html=True)
        loc_df = df['location'].value_counts().reset_index()
        loc_df.columns = ['Location', 'Count']
        
        loc_chart = alt.Chart(loc_df).mark_bar(cornerRadiusEnd=4, color="#2F5BFF").encode(
            x=alt.X('Count:Q', title="Number of Offers", axis=alt.Axis(grid=True)),
            y=alt.Y('Location:N', sort='-x', title=None, axis=alt.Axis(grid=False)),
            tooltip=['Location', 'Count']
        ).properties(height=300)
        
        st.altair_chart(loc_chart, width="stretch")
        st.markdown('<div style="font-size: 13px; color: var(--text-secondary); margin-top: 8px;">Distribution of available roles across European tech hubs.</div>', unsafe_allow_html=True)

with col_chart2:
    with st.container(border=True):
        st.markdown('<div style="font-size: 16px; font-weight: 600; margin-bottom: 16px;">Offers by Domain</div>', unsafe_allow_html=True)
        dom_df = df['domain'].value_counts().reset_index()
        dom_df.columns = ['Domain', 'Count']
        
        dom_chart = alt.Chart(dom_df).mark_bar(cornerRadiusEnd=4, color="#2F5BFF").encode(
            x=alt.X('Count:Q', title="Number of Offers", axis=alt.Axis(grid=True)),
            y=alt.Y('Domain:N', sort='-x', title=None, axis=alt.Axis(grid=False)),
            tooltip=['Domain', 'Count']
        ).properties(height=300)
        
        st.altair_chart(dom_chart, width="stretch")
        st.markdown('<div style="font-size: 13px; color: var(--text-secondary); margin-top: 8px;">Breakdown of roles by primary business function.</div>', unsafe_allow_html=True)

st.write("")
with st.container(border=True):
    st.markdown('<div style="font-size: 16px; font-weight: 600; margin-bottom: 16px;">Top 10 Most Demanded Skills</div>', unsafe_allow_html=True)
    all_skills = []
    for skills_str in df['skills'].dropna():
        skills_list = [s.strip() for s in skills_str.split(';')]
        all_skills.extend(skills_list)
    
    top_skills = pd.Series(all_skills).value_counts().head(10).reset_index()
    top_skills.columns = ['Skill', 'Frequency']

    # Highlights top bar in primary blue, rest in muted grey
    top_skill_name = top_skills['Skill'].iloc[0]
    color_condition = alt.condition(
        alt.datum.Skill == top_skill_name,
        alt.value("#2F5BFF"),
        alt.value("#9CA3AF")
    )

    skill_chart = alt.Chart(top_skills).mark_bar(cornerRadiusEnd=4).encode(
        x=alt.X('Frequency:Q', title="Appearance in job descriptions", axis=alt.Axis(grid=True)),
        y=alt.Y('Skill:N', sort='-x', title=None, axis=alt.Axis(grid=False)),
        color=color_condition,
        tooltip=['Skill', 'Frequency']
    ).properties(height=350)
    
    st.altair_chart(skill_chart, width="stretch")
    st.markdown('<div style="font-size: 13px; color: var(--text-secondary); margin-top: 8px;">Macro tech stack trends across all collected internship offers.</div>', unsafe_allow_html=True)