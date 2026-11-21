/**
 * ROUTE SERVEUR : POST /api/message
 * Rédige un message LinkedIn avec Gemini. Ce code tourne sur le SERVEUR :
 * la clé GEMINI_API_KEY (dans web/.env.local) n'est jamais envoyée au navigateur.
 *
 * Garde-fous pour ne pas épuiser le quota gratuit :
 *   1. cache    : même offre + même profil -> on renvoie le message déjà rédigé ;
 *   2. limite   : MAX_PER_USER messages IA par jour et par personne (adresse IP) ;
 *   3. plafond  : MAX_PER_DAY messages IA par jour pour toute l'app ;
 *   4. plan B   : au-delà, ou si Gemini ne répond pas, un modèle de message sans IA.
 *
 * Limite connue : ces compteurs vivent en mémoire. Ils repartent à zéro si le serveur
 * redémarre (sur Vercel, ça arrive souvent). Suffisant pour une V1 ; plus tard -> une base.
 */
import { offers, skillImplies } from "@/lib/data";
import { scoreOffer } from "@/lib/matching";
import { buildPrompt, templateMessage } from "@/lib/outreach";

const MODELS = [process.env.GEMINI_MODEL || "gemini-3.5-flash-lite", "gemini-3.6-flash"];
const MAX_PER_USER = Number(process.env.MAX_PER_USER || 5);
const MAX_PER_DAY = Number(process.env.MAX_PER_DAY || 200);
const TIMEOUT_MS = 12_000;
const API_BASE = process.env.GEMINI_API_BASE || "https://generativelanguage.googleapis.com";  // modifiable pour les tests

const cache = new Map();       // clé offre+profil -> message
const perUser = new Map();     // ip -> nombre de messages IA aujourd'hui
let day = "", totalToday = 0;

function resetIfNewDay() {
  const today = new Date().toISOString().slice(0, 10);
  if (today !== day) { day = today; totalToday = 0; perUser.clear(); }
}

async function askGemini(prompt) {
  const key = process.env.GEMINI_API_KEY;
  if (!key) throw new Error("no_key");
  for (const model of MODELS) {
    try {
      const res = await fetch(`${API_BASE}/v1beta/models/${model}:generateContent`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "x-goog-api-key": key },
        body: JSON.stringify({
          contents: [{ parts: [{ text: prompt }] }],
          generationConfig: { temperature: 0.7, maxOutputTokens: 400 },
        }),
        signal: AbortSignal.timeout(TIMEOUT_MS),
      });
      if (!res.ok) { console.warn(`[message] ${model} -> HTTP ${res.status}`); continue; }  // 429/503 : modèle suivant
      const data = await res.json();
      const text = data?.candidates?.[0]?.content?.parts?.map((p) => p.text).join("").trim();
      if (text) return text;
    } catch (e) {
      console.warn(`[message] ${model} -> ${e.name}`);
    }
  }
  throw new Error("unavailable");
}

const clean = (v, max) => String(v || "").trim().slice(0, max);

export async function POST(request) {
  let body;
  try { body = await request.json(); } catch { return Response.json({ error: "Requête invalide" }, { status: 400 }); }

  const offer = offers.find((o) => o.id === body?.offerId);
  if (!offer) return Response.json({ error: "Offre introuvable" }, { status: 404 });

  // On ne fait confiance à rien de ce qui vient du navigateur : tailles bornées.
  const name = clean(body.name, 40);
  const roles = (Array.isArray(body.roles) ? body.roles : []).slice(0, 10).map((r) => clean(r, 40));
  const skills = (Array.isArray(body.skills) ? body.skills : []).slice(0, 40).map((s) => clean(s, 60)).filter(Boolean);
  // Compétences de l'étudiant qui couvrent l'offre (le "via" : ce qu'il a vraiment, pas ce que l'offre demande)
  const matched = [...new Set(scoreOffer(offer, { roles, skills }, skillImplies).matched.map((m) => m.via))];
  const ctx = { offer, name, roles, matched };

  resetIfNewDay();
  const ip = (request.headers.get("x-forwarded-for") || "local").split(",")[0].trim();
  const used = perUser.get(ip) || 0;
  const remaining = () => Math.max(0, MAX_PER_USER - (perUser.get(ip) || 0));

  const cacheKey = JSON.stringify([offer.id, name, [...matched].sort(), [...roles].sort()]);
  // "Une autre version" (fresh) ignore le cache, mais compte dans la limite
  if (!body.fresh && cache.has(cacheKey)) return Response.json({ message: cache.get(cacheKey), source: "ai", remaining: remaining() });

  if (used >= MAX_PER_USER) return Response.json({ message: templateMessage(ctx), source: "template", reason: "user_limit", remaining: 0 });
  if (totalToday >= MAX_PER_DAY) return Response.json({ message: templateMessage(ctx), source: "template", reason: "global_limit", remaining: remaining() });

  try {
    const message = await askGemini(buildPrompt(ctx));
    perUser.set(ip, used + 1);
    totalToday += 1;
    if (cache.size > 2000) cache.clear();
    cache.set(cacheKey, message);
    return Response.json({ message, source: "ai", remaining: remaining() });
  } catch (e) {
    return Response.json({ message: templateMessage(ctx), source: "template", reason: e.message, remaining: remaining() });
  }
}
