# Internship Finder — app web

Interface Next.js d'Internship Finder (thème « Prune »).
Elle lit les offres préparées par le moteur Python dans `public/data/offers.json`.

```bash
npm install      # une seule fois
npm run dev      # puis ouvre http://localhost:3000
```

Pour rafraîchir les offres : depuis la racine du projet,
`python -m src.collect`, `python -m src.extract`, puis `python -m src.export`.

- `app/` : les pages (Mes matchs, détail d'une offre, suivi, marché, profil)
- `components/` : les morceaux d'interface
- `lib/matching.js` : le moteur de score (même logique que `src/matching.py`)
- `lib/store.js` : profil et suivi, enregistrés dans le navigateur
- `app/globals.css` : le thème (toutes les couleurs en variables en haut du fichier)
