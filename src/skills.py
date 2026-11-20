"""
NORMALISATION DES COMPÉTENCES
-----------------------------
L'IA n'écrit pas toujours une compétence de la même façon : "G-Sheets" et
"Google Sheets", "Javascript" et "JavaScript", "LLMs" et "LLM"...
Sans normalisation, le matching les traite comme deux compétences différentes
(un candidat qui a "Google Sheets" se voit dire "à travailler : G-Sheets").

On ramène donc chaque compétence à un NOM CANONIQUE, au moment de l'export.
La même table est envoyée à l'app web pour normaliser aussi ce que tape l'utilisateur.
"""
from collections import Counter

# nom canonique -> variantes rencontrées (comparaison insensible à la casse)
SKILL_ALIASES = {
    "Google Sheets": ["G-Sheets", "GSheets", "Google Spreadsheets"],
    "Google Workspace": ["G Suite", "GSuite", "Google Suite"],
    "Microsoft Office": ["MS Office", "Microsoft 365", "Office 365", "Microsoft Office Suite"],
    "Excel": ["Microsoft Excel", "MS Excel"],
    "PowerPoint": ["Microsoft PowerPoint", "MS PowerPoint"],
    "JavaScript": ["JS"],
    "TypeScript": ["TS"],
    "React": ["React.js", "ReactJS"],
    "Node.js": ["NodeJS", "Node"],
    "PostgreSQL": ["Postgres"],
    "LLM": ["LLMs", "Large language models", "Large Language Models (LLMs)"],
    "AI tools": ["AI tooling", "Generative AI tools", "GenAI tools"],
    "AI": ["Artificial intelligence"],
    "Machine learning": ["ML", "Machine learning concepts"],
    "APIs": ["API"],
    "REST APIs": ["REST API"],
    "CRM": ["Customer relationship management", "CRM tools"],
    "ATS": ["Applicant Tracking System", "Applicant Tracking Systems"],
    "Adobe Photoshop": ["Photoshop"],
    "No-code": ["No-code/Low-code tools", "Low-code", "No-code tools"],
    "KPI tracking": ["KPIs", "KPI monitoring"],
    "Competitive benchmarking": ["Competitor benchmarking"],
    "IP law": ["Intellectual property law"],
    "Supply chain": ["Supply Chain Management"],
    "Data structures and algorithms": ["DSA"],
}

_LOOKUP = {v.lower(): canon for canon, variants in SKILL_ALIASES.items() for v in [canon, *variants]}


def canonical_skill(skill):
    """'g-sheets' -> 'Google Sheets'. Une compétence inconnue est renvoyée telle quelle (espaces retirés)."""
    s = (skill or "").strip()
    return _LOOKUP.get(s.lower(), s)


def normalize_skill_lists(lists):
    """
    Normalise toutes les listes de compétences d'un coup :
    1. applique la table d'alias ;
    2. unifie la casse ("Machine Learning" / "Machine learning") en gardant
       l'écriture la plus fréquente ;
    3. retire les doublons dans chaque liste.
    """
    lists = [[canonical_skill(s) for s in (lst or []) if s and s.strip()] for lst in lists]
    spellings = Counter(s for lst in lists for s in lst)
    best = {}
    for s, n in spellings.most_common():
        best.setdefault(s.lower(), s)  # la plus fréquente arrive en premier
    out = []
    for lst in lists:
        seen, clean = set(), []
        for s in lst:
            c = best[s.lower()]
            if c.lower() not in seen:
                seen.add(c.lower())
                clean.append(c)
        out.append(clean)
    return out
