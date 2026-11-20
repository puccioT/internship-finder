"use client";
/**
 * ONBOARDING / PROFIL — 3 étapes : rôles visés, compétences, préférences.
 * Un aperçu en direct montre ce que le profil "débloque" à chaque changement.
 */
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { rankOffers, countriesOf, LANGUAGES } from "@/lib/matching";
import { useProfile } from "@/lib/store";

const STEPS = ["Rôles visés", "Tes compétences", "Préférences"];
const COUNTRIES = [
  ["France", "France"], ["Germany", "Allemagne"], ["Netherlands", "Pays-Bas"],
  ["Ireland", "Irlande"], ["United Kingdom", "Royaume-Uni"], ["Switzerland", "Suisse"],
];
const CONTRACTS = [["Tous", "Stage + Alternance + Working student"], ["Stage", "Stage"], ["Alternance", "Alternance"], ["Working student", "Working student"]];
// Outils souvent demandés, proposés même s'ils sont rares dans les offres actuelles
const COMMON_TOOLS = ["Figma", "Notion", "Jira", "Make", "Zapier", "Amplitude", "A/B testing", "User research",
  "JavaScript", "HTML/CSS", "Git", "LLM", "Google Analytics", "Tableau", "Power BI", "Salesforce", "HubSpot"];

const skillKey = (s) => s.toLowerCase().replace(/[^a-z0-9+#]/g, "");

export default function ProfileEditor({ offers, skillImplies, roleFamilies }) {
  const router = useRouter();
  const [profile, setProfile, loaded] = useProfile();
  const [step, setStep] = useState(0);
  const [search, setSearch] = useState("");

  const toggleIn = (field, value) =>
    setProfile((p) => {
      const cur = field === "countries" ? countriesOf(p) : p[field] || [];
      const next = cur.includes(value) ? cur.filter((x) => x !== value) : [...cur, value];
      return field === "countries" ? { ...p, country: undefined, countries: next } : { ...p, [field]: next };
    });
  const hasSkill = (s) => profile.skills.some((x) => skillKey(x) === skillKey(s));
  const toggleSkill = (s) =>
    setProfile((p) => ({ ...p, skills: hasSkill(s) ? p.skills.filter((x) => skillKey(x) !== skillKey(s)) : [...p.skills, s] }));

  // Compétences les plus demandées dans les offres des rôles visés (et des pays choisis)
  const suggested = useMemo(() => {
    const countries = countriesOf(profile);
    const counts = new Map();
    for (const o of offers) {
      if (countries.length && !countries.includes(o.country)) continue;
      if (profile.roles.length && !profile.roles.includes(o.family) && !profile.roles.includes(o.secondaryFamily)) continue;
      for (const s of new Set(o.skills)) counts.set(s, (counts.get(s) || 0) + 1);
    }
    return [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 18);
  }, [offers, profile]);

  // Aperçu : bons matchs (75+) avec le profil actuel, et la compétence qui en débloquerait le plus
  const preview = useMemo(() => {
    const inTargets = (list) => list.filter((o) => profile.roles.includes(o.family) || profile.roles.includes(o.secondaryFamily));
    const ranked = inTargets(rankOffers(offers, profile, skillImplies));
    const strong = ranked.filter((o) => o.score >= 75).length;
    const missingCounts = new Map();
    for (const o of ranked) for (const m of o.missing) missingCounts.set(m, (missingCounts.get(m) || 0) + 1);
    const candidates = [...missingCounts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5).map(([s]) => s);
    let best = null;
    for (const s of candidates) {
      const gain = inTargets(rankOffers(offers, { ...profile, skills: [...profile.skills, s] }, skillImplies)).filter((o) => o.score >= 75).length - strong;
      if (gain > 0 && (!best || gain > best.gain)) best = { skill: s, gain };
    }
    return { total: ranked.length, strong, best };
  }, [offers, profile, skillImplies]);

  const addCustom = (e) => {
    e.preventDefault();
    const s = search.trim();
    if (s && !hasSkill(s)) setProfile((p) => ({ ...p, skills: [...p.skills, s] }));
    setSearch("");
  };
  const finish = () => { setProfile((p) => ({ ...p, onboarded: true })); router.push("/"); };
  const canContinue = step !== 0 || profile.roles.length > 0;

  if (!loaded) return <p className="muted">Chargement du profil…</p>;

  const searchMatches = search.trim()
    ? [...new Set([...suggested.map(([s]) => s), ...COMMON_TOOLS])].filter((s) => s.toLowerCase().includes(search.trim().toLowerCase())).slice(0, 8)
    : [];

  return (
    <div className="split" style={{ gap: 56, paddingTop: 12 }}>
      <aside className="split-side" style={{ flex: "1 1 280px", maxWidth: 360, display: "flex", flexDirection: "column", gap: 36 }}>
        <ol aria-label="Étapes" style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 20 }}>
          {STEPS.map((label, i) => (
            <li key={label}>
              <button onClick={() => (i === 0 || profile.roles.length) && setStep(i)} aria-current={i === step ? "step" : undefined}
                style={{ display: "flex", gap: 14, alignItems: "center", background: "none", border: 0, padding: 0, cursor: "pointer", textAlign: "left" }}>
                <span style={{
                  width: 30, height: 30, flex: "none", borderRadius: "50%", display: "grid", placeItems: "center", fontWeight: 700, fontSize: 14,
                  background: i === step ? "var(--accent)" : i < step ? "var(--accent-2)" : "transparent",
                  color: i <= step ? "var(--on-accent)" : "var(--muted)", border: i > step ? "1px solid var(--line)" : "none",
                }}>{i < step ? "✓" : i + 1}</span>
                <span style={{ fontWeight: 600, color: i === step ? "var(--text)" : "var(--muted)" }}>{label}</span>
              </button>
            </li>
          ))}
        </ol>
        <div style={{ borderTop: "1px solid var(--line)", paddingTop: 22, display: "flex", flexDirection: "column", gap: 10 }} aria-live="polite">
          <span className="eyebrow">Aperçu en direct</span>
          <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
            <span style={{ fontFamily: "var(--font-display)", fontSize: 48, fontWeight: 700, letterSpacing: "-0.03em", color: "var(--accent)" }}>{preview.strong}</span>
            <span className="muted">bons matchs (75+) sur {preview.total} offres dans tes rôles</span>
          </div>
          {preview.best && (
            <span className="muted" style={{ fontSize: 14 }}>
              Ajouter <b style={{ color: "var(--text)" }}>{preview.best.skill}</b> en débloquerait {preview.best.gain} de plus.
            </span>
          )}
        </div>
      </aside>

      <div className="split-main" style={{ display: "flex", flexDirection: "column", gap: 28, maxWidth: 860 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <span className="eyebrow">Étape {step + 1} sur 3</span>
          <h1 className="h1" style={{ fontSize: "clamp(32px, 4vw, 48px)" }}>
            {step === 0 && "Qu'est-ce que tu cherches ?"}
            {step === 1 && "Qu'est-ce que tu sais vraiment faire ?"}
            {step === 2 && "Où et comment ?"}
          </h1>
          <p className="muted" style={{ margin: 0, fontSize: 16, maxWidth: 620 }}>
            {step === 0 && "Choisis un ou plusieurs types de poste. Les vrais stages Product sont rares : vise aussi les postes voisins."}
            {step === 1 && "Coche seulement ce que tu pourrais défendre en entretien. Le score n'a de valeur que s'il est honnête."}
            {step === 2 && "Les offres qui exigent une langue que tu ne parles pas seront masquées."}
          </p>
        </div>

        {step === 0 && (
          <>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, maxWidth: 360 }}>
              <label htmlFor="name" style={{ fontSize: 14, fontWeight: 600 }} className="muted">Ton prénom (facultatif)</label>
              <input id="name" className="input" value={profile.name} onChange={(e) => setProfile((p) => ({ ...p, name: e.target.value }))} placeholder="Ex. Titouan" />
            </div>
            <div className="filters">
              {roleFamilies.filter((r) => r !== "Other").map((r) => (
                <button key={r} className="chip chip-lg" aria-pressed={profile.roles.includes(r)} onClick={() => toggleIn("roles", r)}>{r}</button>
              ))}
            </div>
          </>
        )}

        {step === 1 && (
          <>
            <form onSubmit={addCustom} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <label htmlFor="skill-search" style={{ fontSize: 14, fontWeight: 600 }} className="muted">Chercher ou ajouter une compétence</label>
              <div style={{ display: "flex", gap: 8 }}>
                <input id="skill-search" className="input" style={{ flex: 1 }} value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Ex. Figma, SQL, A/B testing…" />
                <button type="submit" className="btn btn-ghost" disabled={!search.trim()}>Ajouter</button>
              </div>
              {searchMatches.length > 0 && (
                <div className="filters" style={{ marginTop: 6 }}>
                  {searchMatches.map((s) => <button type="button" key={s} className="chip" aria-pressed={hasSkill(s)} onClick={() => toggleSkill(s)}>{s}</button>)}
                </div>
              )}
            </form>

            <section style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "baseline" }}>
                <h2 className="h2" style={{ fontSize: 17 }}>Les plus demandées dans tes rôles</h2>
                <span className="muted" style={{ fontSize: 13 }}>nombre d'offres qui la demandent</span>
              </div>
              <div className="filters">
                {suggested.map(([s, n]) => (
                  <button key={s} className="chip" aria-pressed={hasSkill(s)} onClick={() => toggleSkill(s)}>
                    {hasSkill(s) ? "✓ " : ""}{s} <span style={{ opacity: 0.6, fontWeight: 500 }}>· {n}</span>
                  </button>
                ))}
              </div>
            </section>

            <section style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <h2 className="h2" style={{ fontSize: 17 }}>Outils courants</h2>
              <div className="filters">
                {COMMON_TOOLS.map((s) => <button key={s} className="chip" aria-pressed={hasSkill(s)} onClick={() => toggleSkill(s)}>{hasSkill(s) ? "✓ " : ""}{s}</button>)}
              </div>
            </section>

            {profile.skills.filter((s) => !COMMON_TOOLS.some((t) => skillKey(t) === skillKey(s)) && !suggested.some(([t]) => skillKey(t) === skillKey(s))).length > 0 && (
              <section style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <h2 className="h2" style={{ fontSize: 17 }}>Ajoutées par toi</h2>
                <div className="filters">
                  {profile.skills.filter((s) => !COMMON_TOOLS.some((t) => skillKey(t) === skillKey(s)) && !suggested.some(([t]) => skillKey(t) === skillKey(s))).map((s) => (
                    <button key={s} className="chip" aria-pressed="true" onClick={() => toggleSkill(s)} aria-label={`Retirer ${s}`}>✓ {s} ✕</button>
                  ))}
                </div>
              </section>
            )}
          </>
        )}

        {step === 2 && (
          <>
            <section style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <h2 className="h2" style={{ fontSize: 17 }}>Pays</h2>
              <div className="filters">
                {COUNTRIES.map(([v, l]) => <button key={v} className="chip" aria-pressed={countriesOf(profile).includes(v)} onClick={() => toggleIn("countries", v)}>{l}</button>)}
              </div>
              <span className="muted" style={{ fontSize: 13 }}>Aucun pays coché = tous les pays.</span>
            </section>
            <section style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <h2 className="h2" style={{ fontSize: 17 }}>Langues que tu parles couramment</h2>
              <div className="filters">
                {LANGUAGES.map(([v, l]) => <button key={v} className="chip" aria-pressed={(profile.languages || []).includes(v)} onClick={() => toggleIn("languages", v)}>{l}</button>)}
              </div>
            </section>
            <section style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <h2 className="h2" style={{ fontSize: 17 }}>Type de contrat</h2>
              <div className="filters">
                {CONTRACTS.map(([v, l]) => <button key={v} className="chip" aria-pressed={profile.contract === v} onClick={() => setProfile((p) => ({ ...p, contract: v }))}>{l}</button>)}
              </div>
            </section>
          </>
        )}

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, paddingTop: 20, borderTop: "1px solid var(--line)", flexWrap: "wrap" }}>
          <button className="btn btn-ghost" onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0}>Retour</button>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            {step === 1 && <span className="muted" style={{ fontSize: 14 }}>{profile.skills.length} compétence{profile.skills.length > 1 ? "s" : ""}</span>}
            {step === 0 && !profile.roles.length && <span className="muted" style={{ fontSize: 14 }}>Choisis au moins un rôle</span>}
            {step < 2
              ? <button className="btn btn-primary" onClick={() => setStep((s) => s + 1)} disabled={!canContinue}>Continuer</button>
              : <button className="btn btn-primary" onClick={finish}>Voir mes matchs</button>}
          </div>
        </div>
      </div>
    </div>
  );
}
