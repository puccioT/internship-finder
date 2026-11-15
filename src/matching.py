"""
MOTEUR DE MATCHING (version "vraies offres")
--------------------------------------------
Les vraies offres n'ont pas de champ "domaine" ni de liste de compétences structurée :
juste un titre, un département et une description en texte libre.

En attendant la phase 3 (extraction par LLM), on utilise des règles simples :
- la FAMILLE de poste est déduite du titre (puis du département) par mots-clés
- les COMPÉTENCES sont cherchées comme mots entiers dans le titre + la description
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


def calculate_score(df, target_family, target_location, contract_type, user_skills):
    df_match = df.copy()

    # --- 1. FILTRES STRICTS ---
    if target_location != "All Locations":
        df_match = df_match[df_match["city"] == target_location]
    if contract_type != "Any":
        df_match = df_match[df_match["contract_type"] == contract_type]

    if df_match.empty:
        df_match["score"] = []
        df_match["matched_skills"] = []
        return df_match

    # --- 2. SCORE ---
    # +50 si la famille de poste correspond
    df_match["score"] = (df_match["role_family"] == target_family) * 50

    # +10 par compétence de l'utilisateur trouvée dans le titre ou la description
    skills = [s.strip() for s in user_skills if s.strip()]

    def find_skills(row):
        text = f"{row['title']}\n{row['description']}"
        return [s for s in skills if skill_in_text(s, text)]

    df_match["matched_skills"] = df_match.apply(find_skills, axis=1)
    df_match["score"] += df_match["matched_skills"].apply(len) * 10

    return df_match.sort_values(by=["score", "first_seen"], ascending=[False, False])
