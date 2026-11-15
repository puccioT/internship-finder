"""
COLLECTEUR
----------
Lit data/companies.csv (produit par probe_ats), récupère les offres de chaque
entreprise, garde les stages / alternances et les enregistre dans data/offers.db.

Lancer depuis la racine du projet (à relancer quand tu veux rafraîchir les offres) :
    python -m src.collect
"""
import csv
from concurrent.futures import ThreadPoolExecutor

from src.sources.ats import fetch_company, is_internship
from src.store import connect, now_iso, save_company_offers

COMPANIES_CSV = "data/companies.csv"


def load_companies():
    with open(COMPANIES_CSV, encoding="utf-8") as f:
        return [row for row in csv.DictReader(f) if row["ats"]]


def collect_one(company_row):
    """Renvoie (entreprise, offres de stage) ou (entreprise, erreur)."""
    name = company_row["company"]
    try:
        offers = fetch_company(company_row["ats"], company_row["slug"], name)
        return name, [o for o in offers if is_internship(o)], None
    except Exception as e:
        return name, [], f"{type(e).__name__}: {e}"


def main():
    companies = load_companies()
    run_time = now_iso()
    print(f"Collecte de {len(companies)} entreprises...\n")

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(collect_one, companies))

    conn = connect()
    total, total_new, errors = 0, 0, []
    for name, offers, error in results:
        if error:
            errors.append(f"  ❌ {name} : {error}")
            continue
        new = save_company_offers(conn, name, offers, run_time)
        total += len(offers)
        total_new += new
        if offers:
            print(f"  {name:<24}{len(offers):>4} offres  ({new} nouvelles)")

    active = conn.execute("SELECT COUNT(*) FROM offers WHERE is_active = 1").fetchone()[0]
    by_contract = conn.execute(
        "SELECT contract_type, COUNT(*) FROM offers WHERE is_active = 1 GROUP BY contract_type"
    ).fetchall()
    top_cities = conn.execute(
        "SELECT city, COUNT(*) c FROM offers WHERE is_active = 1 GROUP BY city ORDER BY c DESC LIMIT 8"
    ).fetchall()
    conn.close()

    print(f"\n✅ {total} stages/alternances collectés, dont {total_new} nouveaux.")
    print(f"   Offres actives en base : {active}  |  " + ", ".join(f"{c} : {n}" for c, n in by_contract))
    print("   Villes : " + ", ".join(f"{c} ({n})" for c, n in top_cities))
    if errors:
        print("\nErreurs :\n" + "\n".join(errors))


if __name__ == "__main__":
    main()
