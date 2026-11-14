import sqlite3
import pandas as pd
import os

DB_PATH = "data/internships.db"
CSV_PATH = "data/internships.csv"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_csv(CSV_PATH)
    # On nomme la table SQL 'internships' au lieu de 'offres'
    df.to_sql('internships', conn, if_exists='replace', index=False)
    conn.close()

def get_internships_sql():
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM internships"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df