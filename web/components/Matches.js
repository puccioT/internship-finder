"use client";
/**
 * ÉCRAN « MES MATCHS »
 * Les scores sont calculés ici, dans le navigateur, à partir du profil enregistré.
 */
import Link from "next/link";
import { useMemo } from "react";
import { rankOffers, topGaps, verdict } from "@/lib/matching";
import { useProfile, useTracker } from "@/lib/store";
import { isNew } from "@/lib/data";
import { ScoreRing, Segments, Bar } from "@/components/Gauges";
import TrackButton from "@/components/TrackButton";

const COUNTRIES = ["France", "Toutes"];
const CONTRACTS = ["Tous", "Stage", "Alternance"];

/** Une phrase courte et factuelle sous chaque offre du top 3 (le verdict IA viendra plus tard). */
function whyLine(o) {
  const have = o.matched.map((m) => m.skill).slice(0, 2).join(" et ");
  if (!o.missing.length) return `Tu couvres toutes les compétences demandées${have ? `, dont ${have}` : ""}.`;
  return `${have ? `Tu as déjà ${have}. ` : ""}À travailler : ${o.missing.slice(0, 2).join(", ")}.`;
}

export default function Matches({ offers, skillImplies, roleFamilies, generatedAt }) {
  const [profile, setProfile] = useProfile();
  const [tracker] = useTracker();

  const ranked = useMemo(() => rankOffers(offers, profile, skillImplies), [offers, profile, skillImplies]);
  const inTargets = ranked.filter((o) => profile.roles.includes(o.family) || profile.roles.includes(o.secondaryFamily));
  const top = inTargets.slice(0, 3);
  const rest = inTargets.slice(3, 15);
  const gaps = topGaps(ranked, profile);
  const strong = inTargets.filter((o) => o.score >= 75).length;
  const newCount = inTargets.filter(isNew).length;

  const tracked = Object.values(tracker);
  const countStatus = (s) => tracked.filter((t) => t.status === s).length;

  const toggleRole = (role) =>
    setProfile((p) => ({ ...p, roles: p.roles.includes(role) ? p.roles.filter((r) => r !== role) : [...p.roles, role] }));

  const updated = new Date(generatedAt).toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" });

  return (
    <>
      <header className="split" style={{ alignItems: "flex-end", gap: 40, paddingTop: 12 }}>
        <div className="split-main" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <span className="eyebrow">Mis à jour {updated}</span>
          <h1 className="h1">
            {profile.name ? `Salut ${profile.name}.` : "Salut."}<br />
            {newCount > 0 ? `${newCount} nouvelle${newCount > 1 ? "s" : ""} offre${newCount > 1 ? "s" : ""} t'attend${newCount > 1 ? "ent" : ""}.` : `Tes ${top.length} meilleurs matchs du jour.`}
          </h1>
        </div>
        <dl className="stats" style={{ flex: "0 1 460px", minWidth: 300 }}>
          <div><dt>offres analysées</dt><dd>{ranked.length}</dd></div>
          <div><dt>bons matchs (75+)</dt><dd style={{ color: "var(--accent)" }}>{strong}</dd></div>
          <div><dt>à apprendre en n°1</dt><dd style={{ fontSize: gaps[0]?.skill.length > 8 ? 24 : 40 }}>{gaps[0]?.skill ?? "—"}</dd></div>
        </dl>
      </header>

      <section aria-label="Filtres" className="filters">
        {roleFamilies.filter((r) => r !== "Other").map((role) => (
          <button key={role} className="chip" aria-pressed={profile.roles.includes(role)} onClick={() => toggleRole(role)}>{role}</button>
        ))}
        <span style={{ width: 8 }} />
        <label className="sr-only" htmlFor="country">Pays</label>
        <select id="country" className="select" value={profile.country} onChange={(e) => setProfile((p) => ({ ...p, country: e.target.value }))}>
          {COUNTRIES.map((c) => <option key={c} value={c}>{c === "Toutes" ? "Tous pays" : c}</option>)}
        </select>
        <label className="sr-only" htmlFor="contract">Contrat</label>
        <select id="contract" className="select" value={profile.contract} onChange={(e) => setProfile((p) => ({ ...p, contract: e.target.value }))}>
          {CONTRACTS.map((c) => <option key={c} value={c}>{c === "Tous" ? "Stage + Alternance" : c}</option>)}
        </select>
      </section>

      {profile.roles.length === 0 ? (
        <div className="empty">Choisis au moins un rôle visé pour voir tes matchs.</div>
      ) : (
        <>
          <section aria-labelledby="top3" style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            <h2 id="top3" className="h2">Ton top 3</h2>
            {top.length === 0 && <div className="empty">Aucune offre pour ces filtres. Essaie « Tous pays » ou un autre rôle.</div>}
            <div className="cards">
              {top.map((o) => (
                <article key={o.id} className="card">
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
                    <div style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 0 }}>
                      <span style={{ fontWeight: 600 }}>{o.company}</span>
                      <span className="muted" style={{ fontSize: 13 }}>{o.cities.join(" · ")} · {o.contract}{o.durationMonths ? ` · ${o.durationMonths} mois` : ""}</span>
                    </div>
                    <ScoreRing score={o.score} />
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
                      {isNew(o) && <span className="new-badge">● Nouveau</span>}
                      <span className="muted" style={{ fontSize: 13 }}>{verdict(o.score)} · {o.family}{o.secondaryFamily ? ` + ${o.secondaryFamily}` : ""}</span>
                    </div>
                    <h3 className="card-title"><Link href={`/offre/${o.slug}`}>{o.title}</Link></h3>
                    <p className="muted" style={{ margin: 0 }}>{whyLine(o)}</p>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                      <span className="muted">Compétences couvertes</span>
                      <span style={{ fontWeight: 700 }}>{o.matched.length}/{o.skills.length}</span>
                    </div>
                    <Segments have={o.matched.length} total={o.skills.length} />
                  </div>
                  <div style={{ display: "flex", gap: 8, marginTop: "auto" }}>
                    <Link href={`/offre/${o.slug}`} className="btn btn-primary" style={{ flex: 1 }}>Voir le match</Link>
                    <TrackButton offerId={o.id} />
                  </div>
                </article>
              ))}
            </div>
          </section>

          <div className="split" style={{ paddingTop: 8 }}>
            <section className="split-main" aria-labelledby="others" style={{ display: "flex", flexDirection: "column" }}>
              <h2 id="others" className="h2" style={{ paddingBottom: 14 }}>Autres bons matchs</h2>
              {rest.map((o) => (
                <Link key={o.id} href={`/offre/${o.slug}`} className="row">
                  <span className="row-score">{o.score}</span>
                  <span style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 3 }}>
                    <span className="row-title">{o.title}</span>
                    <span className="muted" style={{ fontSize: 14 }}>{o.company} · {o.cities.join(" · ")} · {o.contract}{o.durationMonths ? ` ${o.durationMonths} mois` : ""}</span>
                  </span>
                  {isNew(o) && <span className="new-badge">● Nouveau</span>}
                </Link>
              ))}
              {rest.length === 0 && <p className="muted">Pas d'autres offres dans tes rôles visés pour l'instant.</p>}
            </section>

            <aside className="split-side" style={{ display: "flex", flexDirection: "column", gap: 40 }}>
              <section style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                <h2 className="h2">À apprendre en priorité</h2>
                {gaps.map((g) => (
                  <div key={g.skill} style={{ display: "flex", flexDirection: "column", gap: 7 }}>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ fontWeight: 600 }}>{g.skill}</span>
                      <span className="muted">{g.n} offre{g.n > 1 ? "s" : ""}</span>
                    </div>
                    <Bar value={g.n} max={gaps[0].n} />
                  </div>
                ))}
              </section>
              <section style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                <h2 className="h2"><Link href="/suivi" style={{ textDecoration: "none" }}>Mon suivi →</Link></h2>
                <dl className="stats" style={{ borderTop: "1px solid var(--line)", paddingTop: 14 }}>
                  <div><dt>à postuler</dt><dd style={{ fontSize: 32 }}>{countStatus("todo")}</dd></div>
                  <div><dt>postulé</dt><dd style={{ fontSize: 32 }}>{countStatus("applied")}</dd></div>
                  <div><dt>entretien</dt><dd style={{ fontSize: 32, color: "var(--accent)" }}>{countStatus("interview")}</dd></div>
                </dl>
              </section>
            </aside>
          </div>
        </>
      )}
    </>
  );
}
