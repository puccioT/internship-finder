/**
 * MESSAGE D'APPROCHE LINKEDIN — fonctions partagées (serveur et navigateur).
 * - buildPrompt : la consigne envoyée à Gemini.
 * - templateMessage : le plan B sans IA (quota atteint, Gemini indisponible...).
 */

/** Français pour une offre en France, anglais ailleurs. */
export const messageLanguage = (offer) => (offer.country === "France" ? "fr" : "en");

export function buildPrompt({ offer, name, roles, matched }) {
  const lang = messageLanguage(offer) === "fr" ? "French" : "English";
  return `You are a career coach. Write a short LinkedIn message (under 600 characters) from a business-school student
to someone at ${offer.company}, about the internship "${offer.title}".

Student: ${name || "(no name given)"}, targets ${roles.join(" / ") || "internship"} roles.
Skills the student REALLY has that this offer asks for: ${matched.join(", ") || "none listed"}.
What the role is about: ${offer.summary || "not specified"}

Rules:
- Write in ${lang}. Friendly, professional, concise; no flattery, no buzzwords.
- Mention ONE concrete overlap between the student's skills and the role. Never invent skills or experience.
- End with a light call to action (a short chat, or advice about the application).
- ${name ? `Sign with the first name "${name}".` : "No signature."} No placeholders like [Name]. Output only the message.`;
}

/** "Product Intern (m/w/d)" -> "Product Intern" : les mentions de genre n'ont rien à faire dans un message. */
const shortTitle = (t) => t.replace(/\s*[([]\s*[a-z]{1,3}(\s*\/\s*[a-z]{1,3})+\s*[)\]]/gi, "").replace(/\s+-?\s*[HF]\/[HF]\b/g, "").trim();

export function templateMessage({ offer, name, matched }) {
  const skills = matched.slice(0, 2);
  const title = shortTitle(offer.title);
  if (messageLanguage(offer) === "fr") {
    return [
      `Bonjour,`,
      `Je suis étudiant en école de commerce et le stage « ${title} » chez ${offer.company} m'intéresse beaucoup.` +
        (skills.length ? ` J'ai déjà travaillé avec ${skills.join(" et ")}, ce qui me semble utile pour ce poste.` : ""),
      `Auriez-vous quelques minutes pour échanger sur l'équipe et le rôle ?`,
      name ? `Merci d'avance,\n${name}` : `Merci d'avance !`,
    ].join("\n\n");
  }
  return [
    `Hi,`,
    `I'm a business-school student and the "${title}" internship at ${offer.company} caught my attention.` +
      (skills.length ? ` I've worked with ${skills.join(" and ")}, which seems relevant to the role.` : ""),
    `Would you have a few minutes to tell me more about the team and the role?`,
    name ? `Thanks a lot,\n${name}` : `Thanks a lot!`,
  ].join("\n\n");
}
