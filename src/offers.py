"""
PRÉPARATION DES OFFRES (partagée par toutes les pages de l'app)
--------------------------------------------------------------
Lit les offres actives en base et ajoute les colonnes "prêtes à l'emploi" :
famille de poste, compétences, pays, télétravail...
Si le LLM a analysé l'offre, on prend sa fiche ; sinon, les règles par mots-clés.
"""
import json
import re
from collections import Counter

from src.matching import classify_role
from src.store import get_active_offers


def parse_list(value):
    """Les listes sont stockées en JSON dans SQLite : '["SQL", "Excel"]' -> ['SQL', 'Excel']."""
    return json.loads(value) if isinstance(value, str) and value else []


def load_prepared_offers():
    df = get_active_offers()
    if df.empty:
        return df
    keyword_family = df.apply(lambda r: classify_role(r["title"], r["department"]), axis=1)
    df["role_family"] = df["ai_role_family"].fillna(keyword_family)
    df["secondary_family"] = df["ai_secondary_family"]
    df["required_skills"] = df["ai_skills"].apply(parse_list)
    df["languages"] = df["ai_languages"].apply(parse_list)
    df["remote"] = df["ai_remote"].fillna("Unknown")
    df["country"] = df["ai_country"].fillna("Unknown")
    df["summary"] = df["ai_summary"].fillna("")
    return df


def skill_key(skill):
    """Clé de regroupement : 'A/B testing', 'AB Testing' et 'a/b-testing' -> 'abtesting'."""
    return re.sub(r"[^a-z0-9+#]", "", skill.lower())


def count_skills(skill_lists):
    """
    Compte dans combien d'offres chaque compétence apparaît (une fois max par offre).
    Renvoie [(nom affiché, nombre d'offres)], le nom affiché étant l'orthographe la plus fréquente.
    """
    counts, spellings = Counter(), {}
    for skills in skill_lists:
        for key in {skill_key(s) for s in skills if s.strip()}:
            counts[key] += 1
        for s in skills:
            spellings.setdefault(skill_key(s), Counter())[s.strip()] += 1
    return [(spellings[k].most_common(1)[0][0], n) for k, n in counts.most_common()]
