"""
EXTRACTION PAR LLM
------------------
Gemini lit chaque offre active pas encore analysée et en fait une fiche structurée
(vraie famille de poste, compétences, résumé, date de début, durée, langues, télétravail),
stockée dans data/offers.db.

Chaque offre n'est lue qu'UNE fois : relancer le script ne traite que les nouvelles.

Lancer après la collecte :
    python -m src.collect
    python -m src.extract

Pour TOUT réanalyser (ex. après avoir amélioré le prompt) :
    python -m src.extract --all
"""
import sys
import time

from google.genai import errors

from src.llm import extract_offer_info
from src.store import connect, get_offers_to_extract, save_extraction

PAUSE_S = 4          # pause entre deux offres : le quota gratuit limite le nombre d'appels / minute
WAIT_S = {429: 30, 503: 15}   # attente avant de réessayer : quota dépassé (429) ou Gemini saturé (503)
MAX_ATTEMPTS = 3


def main():
    conn = connect()
    if "--all" in sys.argv:
        # On "oublie" que les offres ont été analysées (les anciennes fiches restent utilisables
        # en attendant). Si certaines échouent, un simple `python -m src.extract` les reprendra.
        conn.execute("UPDATE offers SET extracted_at = NULL WHERE is_active = 1")
        conn.commit()
    todo = get_offers_to_extract(conn)
    if not todo:
        print("✅ Toutes les offres actives sont déjà analysées.")
        return

    print(f"Analyse de {len(todo)} offres par Gemini (~{len(todo) * PAUSE_S // 60 + 1} min)...\n")
    done, failed = 0, []

    for i, (source_id, title, company, description, location) in enumerate(todo, 1):
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                info = extract_offer_info(title, company, description, location)
                save_extraction(conn, source_id, info)
                done += 1
                print(f"[{i}/{len(todo)}] {company} · {title[:50]:<50} -> {info['role_family']}{' + ' + info['secondary_family'] if info['secondary_family'] else ''}, "
                      f"{len(info['skills'])} skills, {info['duration_months'] or '?'} mois, {info['remote']}, {info['country']}")
                break
            except errors.APIError as e:
                if e.code in WAIT_S and attempt < MAX_ATTEMPTS:
                    print(f"   Gemini indisponible ({e.code}), nouvel essai dans {WAIT_S[e.code]}s...")
                    time.sleep(WAIT_S[e.code])
                    continue
                failed.append(f"{company} · {title} ({e.code})")
                break
            except Exception as e:
                # Erreurs réseau passagères (ex. SSL EOF) : on réessaie aussi
                network_error = "ssl" in str(e).lower() or "connect" in type(e).__name__.lower()
                if network_error and attempt < MAX_ATTEMPTS:
                    print("   Erreur réseau, nouvel essai dans 10s...")
                    time.sleep(10)
                    continue
                failed.append(f"{company} · {title} ({type(e).__name__}: {e})")
                break
        time.sleep(PAUSE_S)

    conn.close()
    print(f"\n✅ {done} offres analysées.")
    if failed:
        print(f"❌ {len(failed)} échecs (relance le script pour réessayer) :")
        for f in failed:
            print("   -", f)


if __name__ == "__main__":
    main()
