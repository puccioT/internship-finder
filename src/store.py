"""
STOCKAGE DES OFFRES (SQLite)
----------------------------
Une ligne par offre, identifiée par `source_id` (ex : "ashby:doctolib:abc123").

À chaque collecte :
- une offre jamais vue est INSÉRÉE (first_seen = maintenant)
- une offre déjà connue est MISE À JOUR (last_seen = maintenant)
- une offre qui a disparu du site est marquée is_active = 0 (on garde l'historique :
  utile plus tard pour mesurer combien de temps une offre reste en ligne)
"""
import json
import sqlite3
from datetime import datetime, timezone

import pandas as pd

DB_PATH = "data/offers.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS offers (
    source_id     TEXT PRIMARY KEY,
    ats           TEXT,
    company       TEXT,
    title         TEXT,
    location      TEXT,
    city          TEXT,
    contract_type TEXT,
    department    TEXT,
    url           TEXT,
    description   TEXT,
    posted_at     TEXT,
    first_seen    TEXT,
    last_seen     TEXT,
    is_active     INTEGER DEFAULT 1
);
"""

UPSERT = """
INSERT INTO offers (source_id, ats, company, title, location, city, contract_type,
                    department, url, description, posted_at, first_seen, last_seen, is_active)
VALUES (:source_id, :ats, :company, :title, :location, :city, :contract_type,
        :department, :url, :description, :posted_at, :now, :now, 1)
ON CONFLICT(source_id) DO UPDATE SET
    title = excluded.title, location = excluded.location, city = excluded.city,
    contract_type = excluded.contract_type, department = excluded.department,
    url = excluded.url, description = excluded.description,
    last_seen = excluded.last_seen, is_active = 1;
"""


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# Colonnes remplies par le LLM (phase 3). Ajoutées à la volée si la base est ancienne.
EXTRACTED_COLUMNS = {
    "ai_role_family":    "TEXT",
    "ai_skills":         "TEXT",     # liste JSON, ex. ["SQL", "Excel", "Stakeholder management"]
    "ai_summary":        "TEXT",
    "ai_start_date":     "TEXT",
    "ai_duration_months": "INTEGER",
    "ai_languages":      "TEXT",     # liste JSON, ex. ["French (fluent)", "English (professional)"]
    "ai_remote":         "TEXT",     # On-site / Hybrid / Full remote / Unknown
    "extracted_at":      "TEXT",
}


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(SCHEMA)
    # "Migration" simple : si une colonne n'existe pas encore, on l'ajoute.
    existing = {row[1] for row in conn.execute("PRAGMA table_info(offers)")}
    for col, col_type in EXTRACTED_COLUMNS.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE offers ADD COLUMN {col} {col_type}")
    conn.commit()
    return conn


def get_offers_to_extract(conn):
    """Offres actives que le LLM n'a pas encore lues."""
    return conn.execute(
        "SELECT source_id, title, company, description FROM offers "
        "WHERE is_active = 1 AND extracted_at IS NULL ORDER BY first_seen DESC"
    ).fetchall()


def save_extraction(conn, source_id, info):
    conn.execute(
        """UPDATE offers SET ai_role_family = ?, ai_skills = ?, ai_summary = ?, ai_start_date = ?,
           ai_duration_months = ?, ai_languages = ?, ai_remote = ?, extracted_at = ?
           WHERE source_id = ?""",
        (info["role_family"], json.dumps(info["skills"], ensure_ascii=False), info["summary"],
         info["start_date"], info["duration_months"], json.dumps(info["languages"], ensure_ascii=False),
         info["remote"], now_iso(), source_id),
    )
    conn.commit()


def save_company_offers(conn, company, offers, run_time):
    """
    Enregistre les offres d'UNE entreprise et désactive celles qui ont disparu.
    Renvoie le nombre de nouvelles offres.
    On ne désactive que pour les entreprises collectées avec succès : si le site
    d'une boîte est en panne, on ne veut pas croire que toutes ses offres ont disparu.
    """
    existing = {row[0] for row in conn.execute(
        "SELECT source_id FROM offers WHERE company = ?", (company,))}
    new_count = sum(1 for o in offers if o["source_id"] not in existing)

    conn.executemany(UPSERT, [{**o, "now": run_time} for o in offers])
    conn.execute(
        "UPDATE offers SET is_active = 0 WHERE company = ? AND last_seen < ? AND is_active = 1",
        (company, run_time),
    )
    conn.commit()
    return new_count


def get_active_offers():
    """Toutes les offres encore en ligne, les plus récentes d'abord."""
    with connect() as conn:
        return pd.read_sql_query(
            "SELECT * FROM offers WHERE is_active = 1 ORDER BY first_seen DESC, posted_at DESC", conn
        )
