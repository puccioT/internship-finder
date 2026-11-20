/**
 * Données des offres, produites chaque jour par le moteur Python (python -m src.export).
 * Importées au moment du build : l'app n'a besoin d'aucune base de données.
 */
import data from "@/public/data/offers.json";

/** "ashby:doctolib:abc-123" -> "ashby-doctolib-abc-123" (utilisable dans une URL) */
export const slugOf = (id) => id.replace(/[^a-zA-Z0-9_-]/g, "-");

export const offers = data.offers.map((o) => ({ ...o, slug: slugOf(o.id) }));
export const skillImplies = data.skillImplies;
export const roleFamilies = data.roleFamilies;
export const skillAliases = data.skillAliases || {};
export const generatedAt = data.generatedAt;

/** Une offre est "Nouvelle" si elle est apparue dans les 3 jours avant la dernière collecte. */
export const isNew = (offer) =>
  offer.firstSeen && new Date(generatedAt) - new Date(offer.firstSeen) < 3 * 24 * 3600 * 1000;
