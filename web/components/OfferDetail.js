"use client";
/** ÉCRAN « DÉTAIL D'UNE OFFRE » — score détaillé, compétences, écart à combler. */
import Link from "next/link";
import { useMemo } from "react";
import { scoreOffer, rankOffers, verdict, missingLanguages, LANGUAGES, contractLabel } from "@/lib/matching";
import { useProfile } from "@/lib/store";
import { isNew } from "@/lib/data";
import { ScoreRing, Bar } from "@/components/Gauges";
import TrackButton from "@/components/TrackButton";
import OutreachMessage from "@/components/OutreachMessage";

const REMOTE_LABELS = { "On-site": "On-site", Hybrid: "Hybrid", "Full remote": "Fully remote" };

function verdictSentence(r, offer, profile) {
  const inRole = r.roleScore === 50 ? "matches your target" : r.roleScore === 25 ? "partly matches your target" : "is outside your target roles";
  const skills = offer.skills.length ? `You cover ${r.matched.length} of ${offer.skills.length} skill${offer.skills.length > 1 ? "s" : ""}` : "The skills aren't specified";
  const gap = r.missing.length ? `; the main gap is ${r.missing[0]}.` : ", with no gap identified.";
  return `The role (${offer.family}) ${inRole}. ${skills}${gap}`;
}

export default function OfferDetail({ offer, pool, skillImplies }) {
  const [profile] = useProfile();
  const r = useMemo(() => scoreOffer(offer, profile, skillImplies), [offer, profile, skillImplies]);

  // Dans combien d'offres du même pays la compétence manquante n°1 est-elle demandée ?
  const mainGap = r.missing[0];
  const gapCount = mainGap ? pool.filter((o) => o.skills.some((s) => s.toLowerCase() === mainGap.toLowerCase())).length : 0;

  const similar = useMemo(
    () => rankOffers(pool, { ...profile, countries: [], contract: "Tous" }, skillImplies)
      .filter((o) => o.id !== offer.id && (o.family === offer.family || o.secondaryFamily === offer.family))
      .slice(0, 3),
    [pool, profile, skillImplies, offer]
  );

  const tags = [
    `${contractLabel(offer.contract)}${offer.durationMonths ? ` · ${offer.durationMonths} months` : ""}`,
    offer.startDate && offer.startDate !== "Unknown" ? `Start: ${offer.startDate}` : null,
    `${offer.city}${REMOTE_LABELS[offer.remote] ? ` · ${REMOTE_LABELS[offer.remote]}` : ""}`,
    offer.languages.length ? offer.languages.join(", ") : null,
  ].filter(Boolean);

  return (
    <>
      <Link href="/" className="muted" style={{ fontSize: 14, textDecoration: "none", marginBottom: -16 }}>← Back to my matches</Link>

      <header className="split" style={{ alignItems: "center", gap: 40, paddingBottom: 36, borderBottom: "1px solid var(--line)" }}>
        <div className="split-main" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <span className="muted"><span style={{ color: "var(--text)", fontWeight: 600 }}>{offer.company}</span> · {offer.family}{offer.secondaryFamily ? ` + ${offer.secondaryFamily}` : ""}</span>
          <h1 className="h1">{offer.title}</h1>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
            {isNew(offer) && <span className="new-badge" style={{ marginRight: 6 }}>● New</span>}
            {tags.map((t) => (
              <span key={t} style={{ fontSize: 14, padding: "6px 12px", borderRadius: 99, background: "var(--surface-2)" }}>{t}</span>
            ))}
          </div>
        </div>
        <div style={{ flex: "1 1 auto", display: "flex", alignItems: "center", gap: 28, flexWrap: "wrap", minWidth: 0 }}>
          <ScoreRing score={r.score} size={136} thickness={10} background="var(--bg)" label="out of 100" />
          <div style={{ display: "flex", flexDirection: "column", gap: 14, flex: "1 1 180px", maxWidth: 240, minWidth: 0 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 14 }}><span className="muted">Target role</span><b>{r.roleScore}/50</b></div>
              <Bar value={r.roleScore} max={50} />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 14 }}><span className="muted">Skills</span><b>{r.skillScore}/50</b></div>
              <Bar value={r.skillScore} max={50} />
            </div>
          </div>
        </div>
      </header>

      <div className="split" style={{ gap: 64 }}>
        <main className="split-main" style={{ display: "flex", flexDirection: "column", gap: 44 }}>
          {missingLanguages(offer, profile).length > 0 && (
            <p style={{ margin: 0, padding: "14px 18px", borderRadius: 12, background: "var(--surface)", color: "var(--accent)", fontWeight: 600 }}>
              ⚠ This offer requires {missingLanguages(offer, profile).map((c) => LANGUAGES.find(([k]) => k === c)?.[1] || c).join(", ")}, which isn't in your profile.
            </p>
          )}
          <section style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <span className="eyebrow">Verdict · {verdict(r.score)}</span>
            <p style={{ margin: 0, fontFamily: "var(--font-display)", fontSize: 26, lineHeight: 1.3, fontWeight: 600, letterSpacing: "-0.02em" }}>
              {verdictSentence(r, offer, profile)}
            </p>
          </section>

          {offer.summary && (
            <section style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <h2 className="h2">What you'll do</h2>
              <p style={{ margin: 0, fontSize: 16, lineHeight: 1.6 }}>{offer.summary}</p>
              <span className="muted" style={{ fontSize: 13 }}>AI-generated summary of the offer. Read the full posting before applying.</span>
            </section>
          )}

          <section style={{ display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", paddingBottom: 12 }}>
              <h2 className="h2">Required skills</h2>
              <span className="muted">{r.matched.length} of {offer.skills.length} covered</span>
            </div>
            <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
              {r.matched.map((m) => (
                <li key={m.skill} style={{ display: "flex", justifyContent: "space-between", gap: 16, padding: "14px 0", borderTop: "1px solid var(--line)" }}>
                  <span style={{ fontWeight: 600 }}>✓ {m.skill}</span>
                  <span className="muted" style={{ fontSize: 14 }}>{m.via.toLowerCase() === m.skill.toLowerCase() ? "in your profile" : `via ${m.via}`}</span>
                </li>
              ))}
              {r.missing.map((s) => (
                <li key={s} style={{ display: "flex", justifyContent: "space-between", gap: 16, padding: "14px 0", borderTop: "1px solid var(--line)" }}>
                  <span style={{ fontWeight: 600, color: "var(--accent)" }}>{s}</span>
                  <span className="muted" style={{ fontSize: 14 }}>to learn</span>
                </li>
              ))}
            </ul>
          </section>

          {mainGap && (
            <section style={{ background: "var(--surface)", borderRadius: "var(--radius-card)", padding: 28, display: "flex", flexDirection: "column", gap: 8 }}>
              <span className="eyebrow">Closing the gap</span>
              <span style={{ fontFamily: "var(--font-display)", fontSize: 22, fontWeight: 700 }}>{mainGap}</span>
              <span className="muted">
                Asked for in {gapCount} offer{gapCount > 1 ? "s" : ""} in {["Netherlands", "United Kingdom"].includes(offer.country) ? "the " : ""}{offer.country}.
                A small, concrete project that uses it beats a line on your CV: it's something you can show in an interview.
              </span>
            </section>
          )}
        </main>

        <aside className="split-side" style={{ display: "flex", flexDirection: "column", gap: 40 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <a href={offer.url} target="_blank" rel="noopener noreferrer" className="btn btn-primary">View full posting ↗</a>
            <TrackButton offerId={offer.id} offer={offer} variant="full" />
          </div>
          <OutreachMessage key={offer.id} offer={offer} profile={profile} />
          {similar.length > 0 && (
            <section style={{ display: "flex", flexDirection: "column" }}>
              <h2 className="h2" style={{ fontSize: 19, paddingBottom: 12 }}>Similar offers</h2>
              {similar.map((o) => (
                <Link key={o.id} href={`/offer/${o.slug}`} className="row" style={{ gap: 12 }}>
                  <span style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 3 }}>
                    <span className="row-title" style={{ fontSize: 15 }}>{o.title}</span>
                    <span className="muted" style={{ fontSize: 13 }}>{o.company} · {o.cities.join(" · ")}</span>
                  </span>
                  <span className="row-score" style={{ width: "auto", fontSize: 20 }}>{o.score}</span>
                </Link>
              ))}
            </section>
          )}
        </aside>
      </div>
    </>
  );
}
