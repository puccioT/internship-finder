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
"""
import time

from google.genai import errors

from src.llm import extract_offer_info
from src.store import connect, get_offers_to_extract, save_extraction

PAUSE_S = 4          # pause entre deux offres : le quota gratuit limite le nombre d'appels / minute
QUOTA_WAIT_S = 30    # attente si Google répond 429 (quota dépassé)
MAX_ATTEMPTS = 3


def main():
    conn = connect()
    todo = get_offers_to_extract(conn)
    if not todo:
        print("✅ Toutes les offres actives sont déjà analysées.")
        return

    print(f"Analyse de {len(todo)} offres par Gemini (~{len(todo) * PAUSE_S // 60 + 1} min)...\n")
    done, failed = 0, []

    for i, (source_id, title, company, description) in enumerate(todo, 1):
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                info = extract_offer_info(title, company, description)
                save_extraction(conn, source_id, info)
                done += 1
                print(f"[{i}/{len(todo)}] {company} · {title[:50]:<50} -> {info['role_family']}, "
                      f"{len(info['skills'])} skills, {info['duration_months'] or '?'} mois, {info['remote']}")
                break
            except errors.APIError as e:
                if e.code == 429 and attempt < MAX_ATTEMPTS:
                    print(f"   Quota atteint, pause de {QUOTA_WAIT_S}s...")
                    time.sleep(QUOTA_WAIT_S)
                    continue
                failed.append(f"{company} · {title} ({e.code})")
                break
            except Exception as e:
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
