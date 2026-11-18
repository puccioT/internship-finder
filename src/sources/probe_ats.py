"""
DÉTECTEUR D'ATS
---------------
Pour chaque entreprise de la liste, on cherche quelle plateforme de recrutement (ATS)
elle utilise parmi Greenhouse, Lever, Ashby, Workable, SmartRecruiters et Personio, en testant leurs endpoints JSON publics.

Résultat : data/companies.csv, qui servira au collecteur (étape 2).

Lancer depuis la racine du projet :
    python -m src.sources.probe_ats
"""
import csv
import re
from concurrent.futures import ThreadPoolExecutor

import httpx

# Entreprises tech françaises (ou très présentes en France) qui recrutent des stagiaires
# en product / data / ops. Ajoute ou retire des noms librement.
COMPANIES = [
    # --- Cibles prioritaires de Titouan ---
    "Linear", "Notion", "Figma", "Miro", "Folk", "Slite", "Cycle", "Mistral AI", "Dust", "Lovable",
    "n8n", "Hugging Face", "Photoroom", "ElevenLabs", "Dataiku", "Stripe", "Qonto", "Pennylane",
    "Alan", "Adyen", "PayFit", "Spendesk", "Revolut", "Contentsquare", "Pigment", "Celonis",
    "Personio", "Aircall",
    # --- Liste de départ ---
    "Doctolib", "Back Market", "BlaBlaCar", "Swile", "Ledger", "Malt", "Algolia", "Ankorstore",
    "Agicap", "Mirakl", "ManoMano", "Criteo", "Datadog", "Deezer", "Shift Technology", "Swan",
    "Yousign", "Lucca", "Brevo", "Sorare", "Ornikar", "Lemlist", "Welcome to the Jungle", "Libeo",
    "Sumeria", "Ivalua", "Vestiaire Collective", "Getaround", "Comet", "Side", "Upway", "H Company",
    "Hiflow", "Indy", "Partoo", "Qover",
]

# Une offre est un "stage / alternance" si son titre contient un de ces mots.
INTERN_PATTERN = re.compile(
    r"\b(intern|internship|stage|stagiaire|alternance|alternant|apprenti|apprentice|"
    r"apprenticeship|work[- ]study|working student|trainee|césure|gap year)\b",
    re.IGNORECASE,
)

TIMEOUT = 10


def slug_candidates(name):
    """Devine les identifiants possibles : 'Back Market' -> backmarket, back-market."""
    base = name.lower().strip()
    return list(dict.fromkeys([
        base.replace(" ", ""),
        base.replace(" ", "-"),
        base.replace(" ", "").replace("-", ""),
    ]))


# Chaque fonction renvoie la liste des TITRES d'offres, ou None si le slug n'existe pas.

def try_greenhouse(client, slug):
    r = client.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
    if r.status_code != 200:
        return None
    return [job["title"] for job in r.json().get("jobs", [])]


def _lever(client, slug, host):
    r = client.get(f"https://{host}/v0/postings/{slug}?mode=json")
    if r.status_code == 200 and isinstance(r.json(), list):
        return [job["text"] for job in r.json()]
    return None


def try_lever(client, slug):
    return _lever(client, slug, "api.lever.co")


def try_lever_eu(client, slug):
    # Lever a un serveur européen séparé : beaucoup de boîtes françaises y sont.
    return _lever(client, slug, "api.eu.lever.co")


def try_ashby(client, slug):
    r = client.get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    if r.status_code != 200:
        return None
    return [job["title"] for job in r.json().get("jobs", [])]


def try_workable(client, slug):
    r = client.get(f"https://apply.workable.com/api/v1/widget/accounts/{slug}")
    if r.status_code != 200:
        return None
    return [job["title"] for job in r.json().get("jobs", [])]


def try_smartrecruiters(client, slug):
    r = client.get(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings", params={"limit": 100})
    if r.status_code != 200:
        return None
    return [job["name"] for job in r.json().get("content", [])]


def try_personio(client, slug):
    import xml.etree.ElementTree as ET
    for domain in ("jobs.personio.de", "jobs.personio.com"):
        r = client.get(f"https://{slug}.{domain}/xml")
        if r.status_code == 200 and r.text.lstrip().startswith("<"):
            try:
                root = ET.fromstring(r.content)
            except ET.ParseError:
                continue
            return [p.findtext("name", "") for p in root.iter("position")]
    return None


ATS_TESTERS = {
    "greenhouse": try_greenhouse,
    "lever": try_lever,
    "lever-eu": try_lever_eu,
    "ashby": try_ashby,
    "workable": try_workable,
    "smartrecruiters": try_smartrecruiters,
    "personio": try_personio,
}


def probe_company(name):
    """Teste toutes les combinaisons (ATS x slug) et garde celle qui a le plus d'offres."""
    best = None
    with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
        for slug in slug_candidates(name):
            for ats, tester in ATS_TESTERS.items():
                try:
                    titles = tester(client, slug)
                except (httpx.HTTPError, ValueError):
                    continue  # erreur réseau ou réponse non-JSON : on passe
                if not titles:   # None = slug inconnu ; [] = rien de probant
                    continue
                nb_intern = sum(1 for t in titles if INTERN_PATTERN.search(t))
                if best is None or len(titles) > best["nb_jobs"]:
                    best = {"company": name, "ats": ats, "slug": slug,
                            "nb_jobs": len(titles), "nb_intern": nb_intern}
    return best or {"company": name, "ats": "", "slug": "", "nb_jobs": 0, "nb_intern": 0}


def load_previous():
    """Entreprises trouvées lors d'une détection précédente (data/companies.csv)."""
    try:
        with open("data/companies.csv", encoding="utf-8") as f:
            return {row["company"]: row for row in csv.DictReader(f) if row.get("ats")}
    except FileNotFoundError:
        return {}


def main():
    print(f"Test de {len(COMPANIES)} entreprises sur Greenhouse, Lever, Ashby, Workable, SmartRecruiters et Personio...\n")
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(probe_company, COMPANIES))

    found = sorted([r for r in results if r["ats"]], key=lambda r: -r["nb_intern"])
    missing = [r["company"] for r in results if not r["ats"]]

    # Une entreprise trouvée la dernière fois mais pas cette fois : souvent une erreur réseau
    # passagère. On la GARDE (sinon elle sortirait de la collecte et ses offres resteraient
    # "actives" en base pour toujours), et on prévient.
    previous = load_previous()
    kept = [previous[name] for name in missing if name in previous]
    missing = [name for name in missing if name not in previous]

    print(f"{'Entreprise':<24}{'ATS':<16}{'Slug':<22}{'Offres':>7}{'Stages':>8}")
    print("-" * 77)
    for r in found:
        print(f"{r['company']:<24}{r['ats']:<16}{r['slug']:<22}{r['nb_jobs']:>7}{r['nb_intern']:>8}")

    print(f"\nTrouvées : {len(found)}/{len(COMPANIES)}  |  "
          f"Total offres : {sum(r['nb_jobs'] for r in found)}  |  "
          f"Total stages/alternances : {sum(r['nb_intern'] for r in found)}")
    if kept:
        print(f"⚠️  Non retrouvées cette fois mais conservées (détectées avant) : "
              f"{', '.join(r['company'] for r in kept)}")
    print(f"Non trouvées (autre ATS ou slug différent) : {', '.join(missing) or 'aucune'}")

    with open("data/companies.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["company", "ats", "slug", "nb_jobs", "nb_intern"])
        writer.writeheader()
        writer.writerows(found + kept)
    print(f"\n✅ {len(found) + len(kept)} entreprises enregistrées dans data/companies.csv")


if __name__ == "__main__":
    main()
