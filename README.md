# Internship Finder

Outil de recherche de stages et d'alternances dans la tech française : il collecte les **vraies offres** publiées sur les pages carrières d'une trentaine de startups et scale-ups (Doctolib, Back Market, Alan, Qonto, Contentsquare…), les classe selon ton profil, explique chaque correspondance avec l'IA et rédige un message d'approche LinkedIn.

## Fonctionnalités

- **Collecte** : les offres sont récupérées via les API publiques des plateformes de recrutement (Greenhouse, Lever, Ashby), normalisées et stockées dans SQLite (dédoublonnage, historique des offres retirées).
- **Analyse IA des offres** : Gemini lit chaque offre une fois et en extrait une fiche structurée (vraie famille de poste, compétences demandées, résumé des missions, date de début, durée, langues, télétravail), avec sortie JSON imposée par un schéma.
- **Matching sur 100** : 50 pts si la famille de poste correspond à ta cible + jusqu'à 50 pts selon la part des compétences demandées que tu as. Les compétences manquantes sont affichées.
- **AI Insight** : verdict honnête (Strong / Partial / Weak match), la raison et un conseil concret.
- **LinkedIn Pitch** : message d'approche personnalisé, généré à la demande.
- **Market Analytics** : entreprises qui recrutent le plus, répartition par famille de poste et par ville, outils les plus cités dans les offres.

## Stack

Python · Streamlit · pandas · SQLite · httpx · API Gemini (`google-genai`)

## Installation

```bash
python -m venv venv
venv\Scripts\activate          # Windows (macOS/Linux : source venv/bin/activate)
pip install -r requirements.txt
```

Crée un fichier `.env` à la racine :

```
GEMINI_API_KEY=ta_cle_api
# Optionnel : modèle principal (par défaut gemini-3.5-flash-lite)
# GEMINI_MODEL=gemini-3.5-flash-lite
```

Sans clé, l'app fonctionne quand même et affiche des explications génériques à la place de l'IA.

## Lancer l'app

```bash
python -m src.sources.probe_ats   # 1 fois : détecte l'ATS de chaque entreprise -> data/companies.csv
python -m src.collect             # récupère les offres -> data/offers.db (à relancer pour rafraîchir)
python -m src.extract             # Gemini analyse les nouvelles offres (une seule fois par offre)
streamlit run app/main.py
```

## Structure

```
app/
  main.py                    # Page principale : profil, matching, recommandations
  pages/1_Market_Analytics.py
src/
  sources/
    probe_ats.py             # Détecte la plateforme de recrutement de chaque entreprise
    ats.py                   # Connecteurs Greenhouse / Lever / Ashby + normalisation
  collect.py                 # Collecte des offres de stage / alternance
  extract.py                 # Analyse des offres par LLM (fiche structurée)
  store.py                   # Stockage SQLite (upsert, offres inactives)
  matching.py                # Famille de poste + scoring
  llm.py                     # Appels Gemini (timeout, modèle de secours, logs)
  style.py                   # CSS et composants HTML
data/
  companies.csv              # Entreprises suivies et leur ATS
```

## Roadmap

- [x] Phase 1 : stabiliser le prototype (état des boutons, cache, gestion des erreurs Gemini, matching par mot entier)
- [x] Phase 2 : vraies offres via Greenhouse / Lever / Ashby, stockage et dédoublonnage en base
- [ ] Plus de sources : API France Travail (alternance), autres ATS
- [x] Phase 3 : extraction des compétences par LLM, score sur 100, verdict honnête
- [ ] Phase 4 : mise en ligne, premiers utilisateurs, suivi des candidatures
