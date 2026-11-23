"""
EXPORT JSON POUR L'APP WEB
--------------------------
Écrit web/public/data/offers.json : toutes les offres actives, déjà préparées
(fiche IA, famille de poste, compétences, pays...), plus la table des compétences
proches utilisée par le matching. L'app web lit ce fichier, rien d'autre.

À lancer après la collecte et l'extraction :
    python -m src.collect
    python -m src.extract
    python -m src.export
"""
import json
import os
from collections import Counter
from datetime import datetime, timezone

from src.matching import ROLE_FAMILY_NAMES, SKILL_IMPLIES
from src.offers import load_prepared_offers
from src.skills import SKILL_ALIASES, normalize_skill_lists

OUT_PATH = os.path.join("web", "public", "data", "offers.json")

# Pays couverts par l'app (ceux proposés dans les filtres). Les offres ailleurs
# (Delivery Hero à Milan, Stripe à San Francisco...) sont écartées : hors cible, elles brouillent les stats.
SUPPORTED_COUNTRIES = {"France", "Germany", "Netherlands", "Ireland", "United Kingdom", "Switzerland"}


def clean(value):
    """NaN / None de pandas -> null en JSON."""
    if value is None:
        return None
    try:
        if value != value:  # NaN n'est jamais égal à lui-même
            return None
    except (TypeError, ValueError):
        pass
    return value


def main():
    df = load_prepared_offers()
    # "G-Sheets" -> "Google Sheets", "Javascript" -> "JavaScript"... (voir src/skills.py)
    skill_lists = normalize_skill_lists(df["required_skills"].tolist())
    offers = []
    for i, (_, r) in enumerate(df.iterrows()):
        duration = clean(r["ai_duration_months"])
        offers.append({
            "id": r["source_id"],
            "company": r["company"],
            "title": r["title"],
            "city": r["city"],
            "location": r["location"],
            "country": r["country"],
            "contract": r["contract_type"],
            "family": r["role_family"],
            "secondaryFamily": clean(r["secondary_family"]),
            "skills": skill_lists[i],
            "summary": r["summary"],
            "startDate": clean(r["ai_start_date"]),
            "durationMonths": int(duration) if duration is not None else None,
            "languages": r["languages"],
            "remote": r["remote"],
            "url": r["url"],
            "firstSeen": r["first_seen"],
            "postedAt": clean(r["posted_at"]),
        })

    kept = [o for o in offers if o["country"] in SUPPORTED_COUNTRIES]
    dropped = Counter(o["country"] or "Unknown" for o in offers if o["country"] not in SUPPORTED_COUNTRIES)
    offers = kept

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "roleFamilies": ROLE_FAMILY_NAMES,
        "skillImplies": SKILL_IMPLIES,
        "skillAliases": SKILL_ALIASES,
        "offers": offers,
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"✅ {len(offers)} offres exportées dans {OUT_PATH}")
    if dropped:
        print("   Écartées (hors pays couverts) : " + ", ".join(f"{c} {n}" for c, n in dropped.most_common()))


if __name__ == "__main__":
    main()
