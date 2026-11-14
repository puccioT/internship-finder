import re
import streamlit as st

def inject_css():
    st.markdown("""
    <style>
    /* Import Inter font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --bg-color: #F7F7F5;
        --surface-color: #FFFFFF;
        --text-primary: #14171F;
        --text-secondary: #6B7280;
        --accent-color: #2F5BFF;
        --border-color: #E7E5E0;
        --success-bg: #E6F6EF;
        --success-text: #0F9D6B;
        --warning-bg: #FDF3E1;
        --warning-text: #B7791F;
        --danger-bg: #FDECE4;
        --danger-text: #C2410C;
        --radius-card: 12px;
        --radius-sm: 8px;
        --shadow-soft: 0 1px 2px rgba(16,24,40,.04);
    }

    /* Global Typography */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, sans-serif !important;
        color: var(--text-primary);
    }

    /* Hide Streamlit Cruft & Adjust Layout */
    #MainMenu {visibility: hidden;}
    header {background-color: transparent;} 
    footer {background-color: transparent;}
    .stDeployButton {display: none;}
    
    .block-container {
        max-width: 1200px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        border-right: 1px solid var(--border-color);
    }
    .sidebar-section-title {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--text-secondary);
        margin-bottom: 16px;
        margin-top: 8px;
    }

    /* Override Native Streamlit Cards (st.container(border=True)) */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: var(--surface-color) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: var(--radius-card) !important;
        box-shadow: var(--shadow-soft) !important;
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: #D1D5DB !important;
        box-shadow: 0 4px 6px rgba(16,24,40,.06) !important;
    }

    /* Button System */
    button[kind="primary"] {
        background-color: var(--accent-color) !important;
        color: white !important;
        border-radius: var(--radius-sm) !important;
        font-weight: 500 !important;
        border: none !important;
        transition: all 0.2s ease !important;
    }
    button[kind="primary"]:hover {
        background-color: #2548CC !important;
        box-shadow: 0 4px 12px rgba(47, 91, 255, 0.2) !important;
    }
    button[kind="secondary"] {
        background-color: transparent !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: var(--radius-sm) !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    button[kind="secondary"]:hover {
        border-color: var(--text-secondary) !important;
        background-color: #F9FAFB !important;
    }

    /* Hero Section */
    .hero-title {
        font-size: 34px;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin-bottom: 8px;
        color: var(--text-primary);
    }
    .hero-subtitle {
        font-size: 16px;
        color: var(--text-secondary);
        margin-bottom: 24px;
    }
    .hero-pill {
        display: inline-block;
        padding: 4px 12px;
        background-color: var(--surface-color);
        border: 1px solid var(--border-color);
        border-radius: 99px;
        font-size: 13px;
        font-weight: 500;
        color: var(--text-secondary);
        box-shadow: var(--shadow-soft);
        margin-bottom: 32px;
    }

    /* KPI Cards */
    .kpi-card {
        background: var(--surface-color);
        border: 1px solid var(--border-color);
        border-radius: var(--radius-card);
        padding: 24px;
        box-shadow: var(--shadow-soft);
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    .kpi-label {
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-secondary);
        font-weight: 600;
    }
    .kpi-value {
        font-size: 32px;
        font-weight: 700;
        color: var(--text-primary);
        line-height: 1;
    }

    /* Offer Header & Meta */
    .offer-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 16px;
    }
    .offer-title-group {
        display: flex;
        gap: 16px;
        align-items: center;
    }
    .company-avatar {
        width: 48px;
        height: 48px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        font-size: 20px;
        color: var(--text-secondary);
        border: 1px solid var(--border-color);
    }
    .offer-title {
        font-size: 17px;
        font-weight: 600;
        margin: 0 0 4px 0;
        color: var(--text-primary);
    }
    .offer-meta {
        font-size: 13px;
        color: var(--text-secondary);
        display: flex;
        gap: 8px;
        align-items: center;
    }
    .meta-dot {
        width: 4px;
        height: 4px;
        border-radius: 50%;
        background-color: #D1D5DB;
    }

    /* Score Badge */
    .score-badge {
        padding: 4px 12px;
        border-radius: 99px;
        font-size: 13px;
        font-weight: 600;
        border: 1px solid transparent;
    }
    .score-green { background: var(--success-bg); color: var(--success-text); border-color: #A7F3D0;}
    .score-amber { background: var(--warning-bg); color: var(--warning-text); border-color: #FDE68A;}
    .score-grey { background: #F3F4F6; color: var(--text-secondary); border-color: #E5E7EB;}

    /* Skills Chips */
    .chip-group {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 16px;
        margin-bottom: 24px;
    }
    .chip {
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 500;
    }
    .chip-matched {
        background: var(--success-bg);
        color: var(--success-text);
        border: 1px solid rgba(15, 157, 107, 0.2);
    }
    .chip-missing {
        background: #F9FAFB;
        color: var(--text-secondary);
        border: 1px dashed #D1D5DB;
    }

    /* AI Insight Block */
    .ai-block {
        border-left: 3px solid var(--accent-color);
        background-color: rgba(47, 91, 255, 0.03);
        padding: 16px 20px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 20px;
    }
    .ai-label {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--accent-color);
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .ai-text {
        font-size: 14px;
        line-height: 1.5;
        color: var(--text-primary);
        margin: 0;
    }
    </style>
    """, unsafe_allow_html=True)

def render_kpi_card(label, value):
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
    </div>
    """

def get_avatar_color(company_name):
    colors = ["#F3F4F6", "#E0E7FF", "#DCFCE7", "#FEF3C7", "#FEE2E2", "#F3E8FF"]
    return colors[len(company_name) % len(colors)]

def render_offer_block(row, matched_skills, missing_skills, explanation):
    score_class = "score-green" if row['score'] >= 70 else ("score-amber" if row['score'] >= 50 else "score-grey")
    avatar_bg = get_avatar_color(row['company'])
    initial = row['company'][0].upper()
    
    matched_html = "".join([f'<span class="chip chip-matched">{s}</span>' for s in matched_skills])
    missing_html = "".join([f'<span class="chip chip-missing">{s}</span>' for s in missing_skills])
    clean_ai_text = explanation.replace("**AI Career Advisor:**", "").strip()
    # Le markdown (**gras**) n'est pas interprété à l'intérieur d'un bloc HTML :
    # on le convertit nous-mêmes en balises <strong>.
    clean_ai_text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", clean_ai_text)

    html = f"""
    <div class="offer-header">
        <div class="offer-title-group">
            <div class="company-avatar" style="background-color: {avatar_bg}">{initial}</div>
            <div>
                <h3 class="offer-title">{row['title']}</h3>
                <div class="offer-meta">
                    <span>{row['company']}</span>
                    <span class="meta-dot"></span>
                    <span>{row['location']}</span>
                    <span class="meta-dot"></span>
                    <span>{row['contract_type']}</span>
                </div>
            </div>
        </div>
        <div class="score-badge {score_class}">{row['score']} pts</div>
    </div>
    
    <div style="font-size: 14px; color: var(--text-secondary); margin-bottom: 12px; line-height: 1.5;">
        {row['description']}
    </div>
    
    <div class="chip-group">
        {matched_html}
        {missing_html}
    </div>

    <div class="ai-block">
        <div class="ai-label">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/></svg>
            AI Insight
        </div>
        <p class="ai-text">{clean_ai_text}</p>
    </div>
    """
    # Streamlit passe ce HTML dans un moteur markdown, pour qui une ligne indentée
    # de 4 espaces après une ligne vide = bloc de code. Quand matched_html est vide,
    # ça arrive, et les chips s'affichent en code brut. On retire donc l'indentation
    # et les lignes vides.
    return "\n".join(line.strip() for line in html.splitlines() if line.strip())