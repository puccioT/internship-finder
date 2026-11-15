"""
DÉTECTEUR D'ATS
---------------
Pour chaque entreprise de la liste, on cherche quelle plateforme de recrutement (ATS)
elle utilise parmi Greenhouse, Lever et Ashby, en testant leurs endpoints JSON publics.

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
    "Qonto", "Alan", "Doctolib", "Back Market", "BlaBlaCar", "Contentsquare", "Dataiku",
    "Mistral AI", "Swile", "Pennylane", "PayFit", "Ledger", "Spendesk", "Malt", "Algolia",
    "Ankorstore", "Aircall", "Agicap", "Pigment", "Mirakl", "ManoMano", "Criteo", "Datadog",
    "Deezer", "Shift Technology", "Swan", "Yousign", "Lucca", "Brevo", "Hugging Face",
    "Photoroom", "Sorare", "Ornikar", "Lemlist", "Welcome to the Jungle", "Libeo",
    "Sumeria", "Ivalua", "Vestiaire Collective", "Getaround", "Comet", "Side",
    "Upway", "Dust", "H Company", "Hiflow", "Indy", "Partoo", "Qover", "Revolut",
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


def try_lever(client, slug):
    # Lever a deux serveurs : global et européen (beaucoup de boîtes françaises sont sur l'EU).
    for host in ("api.lever.co", "api.eu.lever.co"):
        r = client.get(f"https://{host}/v0/postings/{slug}?mode=json")
        if r.status_code == 200 and isinstance(r.json(), list):
            return [job["text"] for job in r.json()]
    return None


def try_ashby(client, slug):
    r = client.get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    if r.status_code != 200:
        return None
    return [job["title"] for job in r.json().get("jobs", [])]


ATS_TESTERS = {"greenhouse": try_greenhouse, "lever": try_lever, "ashby": try_ashby}


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
                if titles is None:
                    continue
                nb_intern = sum(1 for t in titles if INTERN_PATTERN.search(t))
                if best is None or len(titles) > best["nb_jobs"]:
                    best = {"company": name, "ats": ats, "slug": slug,
                            "nb_jobs": len(titles), "nb_intern": nb_intern}
    return best or {"company": name, "ats": "", "slug": "", "nb_jobs": 0, "nb_intern": 0}


def main():
    print(f"Test de {len(COMPANIES)} entreprises sur Greenhouse, Lever et Ashby...\n")
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(probe_company, COMPANIES))

    found = sorted([r for r in results if r["ats"]], key=lambda r: -r["nb_intern"])
    missing = [r["company"] for r in results if not r["ats"]]

    print(f"{'Entreprise':<24}{'ATS':<12}{'Slug':<22}{'Offres':>7}{'Stages':>8}")
    print("-" * 73)
    for r in found:
        print(f"{r['company']:<24}{r['ats']:<12}{r['slug']:<22}{r['nb_jobs']:>7}{r['nb_intern']:>8}")

    print(f"\nTrouvées : {len(found)}/{len(COMPANIES)}  |  "
          f"Total offres : {sum(r['nb_jobs'] for r in found)}  |  "
          f"Total stages/alternances : {sum(r['nb_intern'] for r in found)}")
    print(f"Non trouvées (autre ATS ou slug différent) : {', '.join(missing) or 'aucune'}")

    with open("data/companies.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["company", "ats", "slug", "nb_jobs", "nb_intern"])
        writer.writeheader()
        writer.writerows(found)
    print("\n✅ Résultats enregistrés dans data/companies.csv")


if __name__ == "__main__":
    main()
