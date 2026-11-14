# Internship Finder

Outil de recherche de stages en product et data : il classe les offres selon ton profil (domaine visé, compétences), explique chaque correspondance avec l'IA et rédige un message d'approche LinkedIn.

> ⚠️ **État actuel : prototype.** Les 500 offres de `data/internships.csv` sont **générées artificiellement** (`src/generate_data.py`) pour tester l'interface. Prochaine étape : brancher de vraies sources d'offres (API France Travail, pages carrières).

## Fonctionnalités

- **Matching** : score par offre (+50 si le domaine correspond, +15 par compétence requise que tu as, +5 si elle est seulement citée dans la description).
- **AI Insight** : Gemini explique pourquoi l'offre te correspond et comment combler une compétence manquante.
- **LinkedIn Pitch** : message d'approche personnalisé, généré à la demande.
- **Market Analytics** : répartition des offres par ville et par domaine, compétences les plus demandées.

## Stack

Python · Streamlit · pandas · SQLite · API Gemini (`google-genai`)

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
streamlit run app/main.py
```

## Structure

```
app/
  main.py                    # Page principale : profil, matching, recommandations
  pages/1_Market_Analytics.py
src/
  database.py                # Chargement CSV -> SQLite
  matching.py                # Moteur de scoring
  llm.py                     # Appels Gemini (timeout, modèle de secours, logs)
  style.py                   # CSS et composants HTML
  generate_data.py           # Génération des offres fictives
data/
  internships.csv
```

## Roadmap

- [x] Phase 1 : stabiliser le prototype (état des boutons, cache, gestion des erreurs Gemini, matching par mot entier)
- [ ] Phase 2 : vraies offres (API France Travail, pages carrières), stockage et dédoublonnage en base
- [ ] Phase 3 : extraction des compétences par LLM, score sur 100
- [ ] Phase 4 : mise en ligne, premiers utilisateurs, suivi des candidatures
