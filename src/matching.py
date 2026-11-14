import re
import pandas as pd


def skill_in_text(skill, text):
    """
    Vérifie si une compétence apparaît comme MOT ENTIER dans un texte.

    Avant, on testait `skill in text` (recherche de sous-chaîne) :
    "r" était trouvé dans "drive", "excel" dans "excellent"...
    Ici, la regex exige qu'il n'y ait ni lettre ni chiffre juste avant ni juste après.
    (?<!\\w) = "pas de caractère de mot avant", (?!\\w) = "pas de caractère de mot après".
    re.escape protège les caractères spéciaux comme dans "C++" ou "A/B Testing".
    """
    pattern = r"(?<!\w)" + re.escape(skill) + r"(?!\w)"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def calculate_score(df, target_domain, target_location, contract_type, english_level, user_skills):
    df_match = df.copy()

    # --- 1. STRICT FILTERS (Élimination directe) ---
    if target_location != "All Locations":
        df_match = df_match[df_match['location'].str.lower() == target_location.lower()]

    if contract_type != "Any":
        df_match = df_match[df_match['contract_type'].str.lower() == contract_type.lower()]

    if english_level != "Any":
        df_match = df_match[df_match['english_level'].str.lower() == english_level.lower()]

    # Si le filtrage strict a vidé le tableau, on retourne un tableau vide avec les bonnes colonnes
    if df_match.empty:
        df_match['score'] = []
        return df_match

    # --- 2. SCORING ENGINE ---
    # Domain Rule (+50 pts)
    df_match['score'] = df_match['domain'].apply(
        lambda x: 50 if str(x).lower() == target_domain.lower() else 0
    )

    # Skills Rule (+15 pts in required skills, +5 pts if mentioned in description)
    def match_skills(row):
        job_skills_list = [s.strip().lower() for s in str(row.get('skills', '')).split(';')]
        job_desc = str(row.get('description', ''))

        score_comp = 0
        for skill in user_skills:
            clean_skill = skill.lower().strip()
            if not clean_skill:
                continue
            if clean_skill in job_skills_list:      # liste exacte : pas de souci de sous-chaîne
                score_comp += 15
            elif skill_in_text(clean_skill, job_desc):  # texte libre : mot entier uniquement
                score_comp += 5
        return score_comp

    df_match['score'] += df_match.apply(match_skills, axis=1)

    df_match = df_match.sort_values(by='score', ascending=False)

    return df_match
