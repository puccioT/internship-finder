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
  if (score >= 75) return "Bon match";
  if (score >= 50) return "Match partiel";
  return "Match faible";
}

/**
 * Score de toutes les offres + regroupement des doublons multi-villes
 * (le même stage publié à Paris, Nantes, Berlin... devient UNE ligne avec 3 villes).
 */
export function rankOffers(offers, profile, skillImplies) {
  const groups = new Map();
  for (const offer of offers) {
    if (profile.country !== "Toutes" && offer.country !== profile.country) continue;
    if (profile.contract !== "Tous" && offer.contract !== profile.contract) continue;
    const key = `${offer.company}|${offer.title.replace(/\s*[-–(].*$/, "").trim().toLowerCase()}|${offer.contract}`;
    const result = { ...offer, ...scoreOffer(offer, profile, skillImplies) };
    const existing = groups.get(key);
    if (!existing) groups.set(key, { ...result, cities: [offer.city] });
    else if (!existing.cities.includes(offer.city)) existing.cities.push(offer.city);
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
