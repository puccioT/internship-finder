"use client";
/**
 * ÉCRAN « MES MATCHS »
 * Les scores sont calculés ici, dans le navigateur, à partir du profil enregistré.
 */
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useMemo } from "react";
import { rankOffers, topGaps, verdict, countriesOf, missingLanguages, LANGUAGES, contractLabel } from "@/lib/matching";
import { isOnboarded, useProfile, useTracker } from "@/lib/store";
import { isNew } from "@/lib/data";
import { ScoreRing, Segments, Bar } from "@/components/Gauges";
import TrackButton from "@/components/TrackButton";

// Pays proposés en filtre (valeur extraite par l'IA, libellé affiché)
const COUNTRIES = [
  ["France", "France"], ["Germany", "Germany"], ["Netherlands", "Netherlands"],
  ["Ireland", "Ireland"], ["United Kingdom", "UK"], ["Switzerland", "Switzerland"],
];
const CONTRACTS = ["Tous", "Stage", "Alternance", "Working student"];

/** Une phrase courte et factuelle sous chaque offre du top 3 (le verdict IA viendra plus tard). */
function whyLine(o) {
  const have = o.matched.map((m) => m.skill).slice(0, 2).join(" and ");
  if (!o.missing.length) return `You cover every required skill${have ? `, including ${have}` : ""}.`;
  return `${have ? `You already have ${have}. ` : ""}To work on: ${o.missing.slice(0, 2).join(", ")}.`;
}

export default function Matches({ offers, skillImplies, roleFamilies, generatedAt }) {
  const [profile, setProfile, loaded] = useProfile();
  const [tracker] = useTracker();
  const router = useRouter();

  // Premier passage : pas encore de profil -> on envoie vers l'onboarding
  useEffect(() => {
    // On relit le navigateur : Next peut réafficher une ancienne version de cette page,
    // dont l'état dirait encore "pas d'onboarding" alors qu'il vient d'être terminé.
    if (loaded && !profile.onboarded && !isOnboarded()) router.replace("/profile");
  }, [loaded, profile.onboarded, router]);

  const ranked = useMemo(() => rankOffers(offers, profile, skillImplies), [offers, profile, skillImplies]);
  const inTargets = ranked.filter((o) => profile.roles.includes(o.family) || profile.roles.includes(o.secondaryFamily));
  const top = inTargets.slice(0, 3);
  const rest = inTargets.slice(3, 15);
  const gaps = topGaps(ranked, profile);
  const strong = inTargets.filter((o) => o.score >= 75).length;
  const newCount = inTargets.filter(isNew).length;

  // Offres masquées parce qu'elles exigent une langue que l'utilisateur ne parle pas
  const hiddenByLanguage = useMemo(() => {
    const countries = countriesOf(profile);
    const counts = new Map();
    let total = 0;
    for (const o of offers) {
      if (countries.length && !countries.includes(o.country)) continue;
      if (profile.contract !== "Tous" && o.contract !== profile.contract) continue;
      if (!profile.roles.includes(o.family) && !profile.roles.includes(o.secondaryFamily)) continue;
      const miss = missingLanguages(o, profile);
      if (!miss.length) continue;
      total++;
      for (const l of miss) counts.set(l, (counts.get(l) || 0) + 1);
    }
    const label = (code) => LANGUAGES.find(([c]) => c === code)?.[1] || code;
    return { total, langs: [...counts.keys()].map(label) };
  }, [offers, profile]);

  const tracked = Object.values(tracker);
  const countStatus = (s) => tracked.filter((t) => t.status === s).length;

  const countries = countriesOf(profile);
  const toggleCountry = (c) =>
    setProfile((p) => {
      const cur = countriesOf(p);
      return { ...p, country: undefined, countries: cur.includes(c) ? cur.filter((x) => x !== c) : [...cur, c] };
    });

  const toggleRole = (role) =>
    setProfile((p) => ({ ...p, roles: p.roles.includes(role) ? p.roles.filter((r) => r !== role) : [...p.roles, role] }));

  const updated = new Date(generatedAt).toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" });

  if (!loaded || !profile.onboarded) return <p className="muted" aria-live="polite">Loading your profile…</p>;

  return (
    <>
      {loaded && !profile.onboarded && (
        <Link href="/profile" className="row" style={{ borderTop: "none", background: "var(--surface)", padding: "16px 20px", margin: "0 0 -16px", borderRadius: 12 }}>
          <span style={{ flex: 1 }}>
            <b>Set up your profile in 1 minute</b>
            <span className="muted"> · target roles, skills and languages, for scores that fit you.</span>
          </span>
          <span style={{ color: "var(--accent)", fontWeight: 700 }}>Start →</span>
        </Link>
      )}
      <header className="split" style={{ alignItems: "flex-end", gap: 40, paddingTop: 12 }}>
        <div className="split-main" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <span className="eyebrow">Updated {updated}</span>
          <h1 className="h1">
            {profile.name ? `Hi ${profile.name}.` : "Hi there."}<br />
            {newCount > 0 ? `${newCount} new offer${newCount > 1 ? "s" : ""} for you.` : `Your top ${top.length} matches today.`}
          </h1>
        </div>
        <dl className="stats" style={{ flex: "0 1 460px", minWidth: 300 }}>
          <div><dt>offers analysed</dt><dd>{ranked.length}</dd></div>
          <div><dt>strong matches (75+)</dt><dd style={{ color: "var(--accent)" }}>{strong}</dd></div>
          <div><dt>#1 skill to learn</dt><dd style={{ fontSize: gaps[0]?.skill.length > 14 ? 20 : gaps[0]?.skill.length > 8 ? 24 : 40, overflowWrap: "break-word", lineHeight: 1.1 }}>{gaps[0]?.skill ?? "—"}</dd></div>
        </dl>
      </header>

      <section aria-label="Filters" className="filters">
        {roleFamilies.filter((r) => r !== "Other").map((role) => (
          <button key={role} className="chip" aria-pressed={profile.roles.includes(role)} onClick={() => toggleRole(role)}>{role}</button>
        ))}
      </section>

      <section aria-label="Country and contract" className="filters" style={{ marginTop: -24 }}>
        {COUNTRIES.map(([value, label]) => (
          <button key={value} className="chip" aria-pressed={countries.includes(value)} onClick={() => toggleCountry(value)}>{label}</button>
        ))}
        <button className="chip" aria-pressed={countries.length === 0} onClick={() => setProfile((p) => ({ ...p, country: undefined, countries: [] }))}>All countries</button>
        <span style={{ width: 8 }} />
        <label className="sr-only" htmlFor="contract">Contract</label>
        <select id="contract" className="select" value={profile.contract} onChange={(e) => setProfile((p) => ({ ...p, contract: e.target.value }))}>
          {CONTRACTS.map((c) => <option key={c} value={c}>{contractLabel(c)}</option>)}
        </select>
      </section>

      {hiddenByLanguage.total > 0 && profile.hideLanguageMismatch !== false && (
        <p className="muted" style={{ margin: "-20px 0 0", fontSize: 14 }}>
          {hiddenByLanguage.total} offer{hiddenByLanguage.total > 1 ? "s" : ""} hidden because {hiddenByLanguage.total > 1 ? "they require" : "it requires"} {hiddenByLanguage.langs.join(", ")}.{" "}
          <button onClick={() => setProfile((p) => ({ ...p, hideLanguageMismatch: false }))} style={{ background: "none", border: 0, padding: 0, color: "var(--accent-2)", fontWeight: 600, cursor: "pointer", textDecoration: "underline", textUnderlineOffset: 3 }}>Show them anyway</button>
        </p>
      )}
      {profile.hideLanguageMismatch === false && (
        <p className="muted" style={{ margin: "-20px 0 0", fontSize: 14 }}>
          Offers requiring a language you don't speak are shown.{" "}
          <button onClick={() => setProfile((p) => ({ ...p, hideLanguageMismatch: true }))} style={{ background: "none", border: 0, padding: 0, color: "var(--accent-2)", fontWeight: 600, cursor: "pointer", textDecoration: "underline", textUnderlineOffset: 3 }}>Hide them</button>
        </p>
      )}

      {profile.roles.length === 0 ? (
        <div className="empty">Pick at least one target role to see your matches.</div>
      ) : (
        <>
          <section aria-labelledby="top3" style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            <h2 id="top3" className="h2">Your top 3</h2>
            {top.length === 0 && <div className="empty">No offers for these filters. Try "All countries" or another role.</div>}
            <div className="cards">
              {top.map((o) => (
                <article key={o.id} className="card">
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
                    <div style={{ display: "flex", flexDirection: "column", gap: 4, minWidth: 0 }}>
                      <span style={{ fontWeight: 600 }}>{o.company}</span>
                      <span className="muted" style={{ fontSize: 13 }}>{o.cities.join(" · ")} · {contractLabel(o.contract)}{o.durationMonths ? ` · ${o.durationMonths} months` : ""}</span>
                    </div>
                    <ScoreRing score={o.score} />
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
                      {isNew(o) && <span className="new-badge">● New</span>}
                      <span className="muted" style={{ fontSize: 13 }}>{verdict(o.score)} · {o.family}{o.secondaryFamily ? ` + ${o.secondaryFamily}` : ""}</span>
                    </div>
                    <h3 className="card-title"><Link href={`/offer/${o.slug}`}>{o.title}</Link></h3>
                    <p className="muted" style={{ margin: 0 }}>{whyLine(o)}</p>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                      <span className="muted">Skills covered</span>
                      <span style={{ fontWeight: 700 }}>{o.matched.length}/{o.skills.length}</span>
                    </div>
                    <Segments have={o.matched.length} total={o.skills.length} />
                  </div>
                  <div style={{ display: "flex", gap: 8, marginTop: "auto" }}>
                    <Link href={`/offer/${o.slug}`} className="btn btn-primary" style={{ flex: 1 }}>See the match</Link>
                    <TrackButton offerId={o.id} offer={o} />
                  </div>
                </article>
              ))}
            </div>
          </section>

          <div className="split" style={{ paddingTop: 8 }}>
            <section className="split-main" aria-labelledby="others" style={{ display: "flex", flexDirection: "column" }}>
              <h2 id="others" className="h2" style={{ paddingBottom: 14 }}>Other good matches</h2>
              {rest.map((o) => (
                <Link key={o.id} href={`/offer/${o.slug}`} className="row">
                  <span className="row-score">{o.score}</span>
                  <span style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 3 }}>
                    <span className="row-title">{o.title}</span>
                    <span className="muted" style={{ fontSize: 14 }}>{o.company} · {o.cities.join(" · ")} · {contractLabel(o.contract)}{o.durationMonths ? ` · ${o.durationMonths} months` : ""}</span>
                  </span>
                  {isNew(o) && <span className="new-badge">● New</span>}
                </Link>
              ))}
              {rest.length === 0 && <p className="muted">No other offers in your target roles for now.</p>}
            </section>

            <aside className="split-side" style={{ display: "flex", flexDirection: "column", gap: 40 }}>
              <section style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                <h2 className="h2">Skills to learn first</h2>
                {gaps.map((g) => (
                  <div key={g.skill} style={{ display: "flex", flexDirection: "column", gap: 7 }}>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ fontWeight: 600 }}>{g.skill}</span>
                      <span className="muted">{g.n} offer{g.n > 1 ? "s" : ""}</span>
                    </div>
                    <Bar value={g.n} max={gaps[0].n} />
                  </div>
                ))}
              </section>
              <section style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                <h2 className="h2"><Link href="/tracker" style={{ textDecoration: "none" }}>My tracker →</Link></h2>
                <dl className="stats" style={{ borderTop: "1px solid var(--line)", paddingTop: 14 }}>
                  <div><dt>to apply</dt><dd style={{ fontSize: 32 }}>{countStatus("todo")}</dd></div>
                  <div><dt>applied</dt><dd style={{ fontSize: 32 }}>{countStatus("applied")}</dd></div>
                  <div><dt>interview</dt><dd style={{ fontSize: 32, color: "var(--accent)" }}>{countStatus("interview")}</dd></div>
                </dl>
              </section>
            </aside>
          </div>
        </>
      )}
    </>
  );
}
