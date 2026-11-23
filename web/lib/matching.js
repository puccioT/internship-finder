/**
 * MOTEUR DE MATCHING — version JavaScript
 * Même logique que src/matching.py (Python), pour calculer les scores dans le navigateur :
 *  - 50 pts si la famille principale de l'offre fait partie des rôles visés,
 *    25 pts si c'est sa famille secondaire (postes hybrides)
 *  - jusqu'à 50 pts selon la PART des compétences demandées que l'utilisateur couvre
 */

/** Échappe les caractères spéciaux d'une regex : "C++" -> "C\+\+". */
const escapeRegex = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** La compétence apparaît-elle comme MOT ENTIER ? ("r" n'est pas trouvé dans "drive") */
export function skillInText(skill, text) {
  const pattern = new RegExp(`(?<![\\p{L}\\p{N}_])${escapeRegex(skill)}(?![\\p{L}\\p{N}_])`, "iu");
  return pattern.test(text);
}

/**
 * Quelle compétence de l'utilisateur couvre une compétence demandée ?
 * Renvoie le nom de la compétence utilisateur, ou null.
 * Ex. : demandé "Data analysis", l'utilisateur a "Python" -> "Python" (via la table des compétences proches).
 */
export function coveringSkill(required, userSkills, skillImplies) {
  for (const u of userSkills) {
    if (skillInText(u, required) || skillInText(required, u)) return u;
  }
  for (const u of userSkills) {
    const implied = skillImplies[u.toLowerCase().trim()] || [];
    if (implied.some((imp) => skillInText(imp, required))) return u;
  }
  return null;
}

/** Score détaillé d'une offre pour un profil. */
export function scoreOffer(offer, profile, skillImplies) {
  const roleScore = profile.roles.includes(offer.family) ? 50 : profile.roles.includes(offer.secondaryFamily) ? 25 : 0;

  const matched = [];   // [{ skill, via }]
  const missing = [];   // ["SQL", ...]
  for (const req of offer.skills) {
    const via = coveringSkill(req, profile.skills, skillImplies);
    if (via) matched.push({ skill: req, via });
    else missing.push(req);
  }
  const skillScore = offer.skills.length ? Math.round((50 * matched.length) / offer.skills.length) : 0;

  return { score: roleScore + skillScore, roleScore, skillScore, matched, missing };
}

/** Verdict déterministe : il découle du score (l'IA ne fera que l'expliquer). */
export function verdict(score) {
  if (score >= 75) return "Strong match";
  if (score >= 50) return "Partial match";
  return "Weak match";
}

/** Langues que l'utilisateur peut proposer (codes anglais, comme dans les offres). */
export const LANGUAGES = [
  ["english", "English"], ["french", "French"], ["german", "German"], ["dutch", "Dutch"],
  ["spanish", "Spanish"], ["italian", "Italian"], ["portuguese", "Portuguese"],
];

/**
 * Langues EXIGÉES par une offre. L'IA écrit par ex. "German (fluent)", "French (plus)".
 * Une langue marquée "plus", "nice to have", "helpful", "bonus"... n'est pas exigée.
 */
export function requiredLanguages(offer) {
  return (offer.languages || [])
    .filter((l) => !/plus|nice|helpful|bonus|advantage|preferred|asset|optional|atout/i.test(l))
    .map((l) => l.trim().split(/[\s(]/)[0].toLowerCase())
    .filter((l) => LANGUAGES.some(([code]) => code === l));
}

/** Langues exigées par l'offre que l'utilisateur ne parle pas (liste vide = OK). */
export function missingLanguages(offer, profile) {
  if (!Array.isArray(profile.languages) || profile.languages.length === 0) return [];
  return requiredLanguages(offer).filter((l) => !profile.languages.includes(l));
}

/** Pays choisis par l'utilisateur ([] = tous). Gère aussi les anciens profils à un seul pays. */
export function countriesOf(profile) {
  if (Array.isArray(profile.countries)) return profile.countries;
  return profile.country && profile.country !== "Toutes" ? [profile.country] : [];
}

/**
 * Clé de regroupement des doublons multi-villes : le titre SANS les mentions de ville
 * ni les "(x/f/m)", "(H/F)"...
 * "AI Engineer Intern (x/f/m) - Paris" et "AI Engineer intern (x/f/m) - Berlin" -> "ai engineer intern".
 * (Avant, on coupait au premier tiret : "Stage - Product Manager" devenait "Stage",
 * et tous les "Stage - ..." d'une même boîte étaient fusionnés. Bug corrigé.)
 */
function groupKey(offer, cityNames) {
  let t = offer.title.toLowerCase()
    .replace(/\((?:[a-z]\/[a-z](?:\/[a-z])?|h\/f|f\/h)\)/g, " ")   // (x/f/m), (h/f)...
    .replace(/[–—]/g, "-");
  for (const city of cityNames) {
    t = t.replace(new RegExp(`(^|[\\s\\-,(])${escapeRegex(city)}(?=$|[\\s\\-,)])`, "g"), " ");
  }
  t = t.replace(/[^\p{L}\p{N}]+/gu, " ").trim();
  return `${offer.company}|${t}|${offer.contract}`;
}

/**
 * Score de toutes les offres + regroupement des doublons multi-villes
 * (le même stage publié à Paris, Nantes, Berlin... devient UNE ligne avec 3 villes).
 */
/**
 * L'offre commence-t-elle trop tôt pour l'étudiant ?
 * startTo = mois de début "au plus tard" (calculé à l'export). Date inconnue -> on garde l'offre.
 */
export function startsTooEarly(offer, profile) {
  return Boolean(profile.availableFrom && offer.startTo && offer.startTo < profile.availableFrom);
}

/** Choix du filtre "Je peux commencer à partir de" : le mois en cours + 18 mois. */
export function startOptions(now = new Date()) {
  const opts = [["", "Any time"]];
  for (let i = 0; i <= 18; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() + i, 1);
    const value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    opts.push([value, d.toLocaleDateString("en-GB", { month: "long", year: "numeric" })]);
  }
  return opts;
}

export function rankOffers(offers, profile, skillImplies) {
  const countries = countriesOf(profile);
  const cityNames = [...new Set(offers.map((o) => (o.city || "").toLowerCase()).filter((c) => c.length > 2))];
  const groups = new Map();
  for (const offer of offers) {
    if (countries.length && !countries.includes(offer.country)) continue;
    if (profile.contract !== "Tous" && offer.contract !== profile.contract) continue;
    if (profile.hideLanguageMismatch !== false && missingLanguages(offer, profile).length) continue;
    if (startsTooEarly(offer, profile)) continue;
    const key = groupKey(offer, cityNames);
    const result = { ...offer, ...scoreOffer(offer, profile, skillImplies) };
    const existing = groups.get(key);
    if (!existing) {
      groups.set(key, { ...result, cities: [offer.city] });
    } else {
      const cities = existing.cities.includes(offer.city) ? existing.cities : [...existing.cities, offer.city];
      // On garde la version la mieux notée comme représentante du groupe
      groups.set(key, result.score > existing.score ? { ...result, cities } : { ...existing, cities });
    }
  }
  return [...groups.values()].sort((a, b) => b.score - a.score || (b.firstSeen || "").localeCompare(a.firstSeen || ""));
}

/** Compétences manquantes les plus fréquentes parmi les offres des rôles visés. */
export function topGaps(ranked, profile, limit = 4) {
  const counts = new Map();
  for (const o of ranked) {
    if (!profile.roles.includes(o.family) && !profile.roles.includes(o.secondaryFamily)) continue;
    for (const m of o.missing) counts.set(m, (counts.get(m) || 0) + 1);
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, limit).map(([skill, n]) => ({ skill, n }));
}

/** Libellés anglais des types de contrat (les valeurs en base restent "Stage", "Alternance"...). */
export const CONTRACT_LABELS = { Stage: "Internship", Alternance: "Apprenticeship", "Working student": "Working student", Tous: "All contracts" };
export const contractLabel = (c) => CONTRACT_LABELS[c] || c;
