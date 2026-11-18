"""
MOTEUR DE MATCHING
------------------
Source principale : la fiche extraite par le LLM (src/extract.py) -> vraie famille de poste
et compétences demandées.
Secours, pour les offres pas encore analysées : règles par mots-clés sur le titre et
recherche des compétences dans la description.
"""
import re

import pandas as pd

# L'ordre compte : la première famille qui correspond gagne.
# "Data Product Manager" -> Product ; "Data Analyst" -> Data.
ROLE_FAMILIES = {
    "Product": r"\bproduct\b|\bproduit\b|product owner|\bPM\b",
    "Data": r"\bdata\b|analyst|analytics|données|business intelligence|\bBI\b|machine learning|\bML\b|\bAI\b|\bIA\b",
    "Strategy & Ops": r"strateg|operations|opérations|\bops\b|bizops|revops|chief of staff|project|projet|program|consult",
    "Marketing & Growth": r"marketing|growth|brand|communication|content|\bSEO\b|\bCRM\b|acquisition|partnership",
    "Sales & Business Dev": r"\bsales\b|business develop|account|commercial|customer success|\bSDR\b|\bBDR\b|vente",
    "Finance & Legal": r"financ|accounting|comptab|legal|juridique|audit|\btax\b|FP&A|treasury|trésorerie|controlling|contrôle de gestion",
    "Engineering": r"engineer|ingénieur|developer|développeur|software|backend|frontend|full[- ]?stack|devops|\bSRE\b|security|sécurité",
    "Design": r"design|\bUX\b|\bUI\b",
    "People & HR": r"\bHR\b|\bRH\b|people|talent|recruit|recrut|ressources humaines",
}
ROLE_PATTERNS = {name: re.compile(p, re.IGNORECASE) for name, p in ROLE_FAMILIES.items()}
ROLE_FAMILY_NAMES = list(ROLE_FAMILIES) + ["Other"]

# Outils et compétences qu'on sait repérer dans les descriptions (sert aussi aux analytics).
SKILLS_CATALOG = [
    "SQL", "Python", "R", "Excel", "Google Sheets", "PowerPoint", "Figma", "Notion", "Jira",
    "Tableau", "Power BI", "Looker", "Metabase", "dbt", "BigQuery", "Snowflake",
    "Amplitude", "Mixpanel", "Google Analytics", "A/B testing", "Salesforce", "HubSpot",
    "Zapier", "Make", "Airtable", "Agile", "Scrum", "Machine Learning", "LLM",
]


def skill_in_text(skill, text):
    """
    Vérifie si une compétence apparaît comme MOT ENTIER dans un texte.
    (?<!\\w) = pas de lettre/chiffre juste avant, (?!\\w) = pas juste après.
    "r" n'est donc pas trouvé dans "drive", ni "excel" dans "excellent".
    """
    pattern = r"(?<!\w)" + re.escape(skill) + r"(?!\w)"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def classify_role(title, department=""):
    """Famille de poste : d'abord d'après le titre, sinon d'après le département."""
    for text in (title or "", department or ""):
        for name, pattern in ROLE_PATTERNS.items():
            if pattern.search(text):
                return name
    return "Other"


# Compétences "proches" : avoir la compétence de gauche couvre celles de droite.
# Table explicite plutôt que magie : on peut l'expliquer et la corriger facilement.
SKILL_IMPLIES = {
    "sql":        ["data analysis", "databases", "data extraction", "analytics", "data querying", "bigquery"],
    "python":     ["coding", "programming", "scripting", "automation", "data analysis", "pandas", "software development"],
    "excel":      ["spreadsheets", "google sheets", "data analysis", "reporting", "financial modeling", "kpi tracking"],
    "google sheets": ["spreadsheets", "excel", "reporting"],
    "figma":      ["prototyping", "wireframing", "ui design", "mockups", "design tools"],
    "notion":     ["documentation", "knowledge management"],
    "tableau":    ["data visualization", "dashboards", "reporting", "bi tools"],
    "power bi":   ["data visualization", "dashboards", "reporting", "bi tools"],
    "looker":     ["data visualization", "dashboards", "bi tools"],
    "jira":       ["agile", "scrum", "backlog management", "project management tools"],
    "make":       ["automation", "no-code", "workflow automation"],
    "zapier":     ["automation", "no-code", "workflow automation"],
    "chatgpt":    ["ai tools", "generative ai", "prompt engineering"],
    "llm":        ["ai tools", "generative ai", "prompt engineering"],
}


def skills_match(user_skill, required_skill):
    """
    Vrai si la compétence de l'utilisateur couvre la compétence demandée :
    - même mot ('Python' / 'Python (pandas)'), dans un sens ou dans l'autre
    - ou compétence proche via SKILL_IMPLIES ('SQL' couvre 'Data analysis')
    """
    if skill_in_text(user_skill, required_skill) or skill_in_text(required_skill, user_skill):
        return True
    return any(skill_in_text(implied, required_skill)
               for implied in SKILL_IMPLIES.get(user_skill.lower().strip(), []))


def score_offer(row, target_families, user_skills):
    """
    Score sur 100 :
    - 50 pts si la famille principale fait partie des cibles, 25 pts si c'est la famille secondaire
      (postes hybrides, ex. "Product & Operations")
    - jusqu'à 50 pts selon la PART des compétences demandées que l'utilisateur couvre
    Si l'offre n'a pas encore été analysée par le LLM, on retombe sur l'ancienne méthode.
    Renvoie (score, compétences couvertes, compétences manquantes).
    """
    if row["role_family"] in target_families:
        score = 50
    elif row.get("secondary_family") in target_families:
        score = 25
    else:
        score = 0
    required = row["required_skills"]

    if required:
        matched = [r for r in required if any(skills_match(u, r) for u in user_skills)]
        missing = [r for r in required if r not in matched]
        score += round(50 * len(matched) / len(required))
    else:
        text = f"{row['title']}\n{row['description']}"
        matched = [u for u in user_skills if skill_in_text(u, text)]
        missing = []
        score += min(len(matched) * 10, 50)
    return score, matched, missing


def calculate_score(df, target_families, target_location, contract_type, remote, user_skills):
    df_match = df.copy()

    # --- 1. FILTRES STRICTS ---
    if target_location != "All Locations":
        df_match = df_match[df_match["city"] == target_location]
    if contract_type != "Any":
        df_match = df_match[df_match["contract_type"] == contract_type]
    if remote != "Any":
        df_match = df_match[df_match["remote"] == remote]

    if df_match.empty:
        for col in ("score", "matched_skills", "missing_skills"):
            df_match[col] = []
        return df_match

    # --- 2. SCORE ---
    skills = [s.strip() for s in user_skills if s.strip()]
    results = df_match.apply(lambda row: score_offer(row, target_families, skills), axis=1)
    df_match["score"] = [r[0] for r in results]
    df_match["matched_skills"] = [r[1] for r in results]
    df_match["missing_skills"] = [r[2] for r in results]

    return df_match.sort_values(by=["score", "first_seen"], ascending=[False, False])
