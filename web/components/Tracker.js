"use client";
/**
 * ÉCRAN « MON SUIVI » — les offres mises de côté et où en est chaque candidature.
 * Tout reste dans le navigateur (comme le profil).
 */
import Link from "next/link";
import { useMemo, useState } from "react";
import { scoreOffer } from "@/lib/matching";
import { useProfile, useTracker, TRACK_STATUSES } from "@/lib/store";

const DAY = 24 * 3600 * 1000;
const FOLLOW_UP_DAYS = 7;   // au-delà, on suggère une relance

function ago(iso) {
  if (!iso) return "";
  const d = Math.floor((Date.now() - new Date(iso)) / DAY);
  return d <= 0 ? "aujourd'hui" : d === 1 ? "hier" : `il y a ${d} jours`;
}

export default function Tracker({ offers, skillImplies }) {
  const [profile] = useProfile();
  const [tracker, setTracker, loaded] = useTracker();
  const [filter, setFilter] = useState("all");

  const byId = useMemo(() => new Map(offers.map((o) => [o.id, o])), [offers]);
  const items = useMemo(() =>
    Object.entries(tracker).map(([id, t]) => {
      const offer = byId.get(id);
      return {
        id, ...t, offer,
        title: offer?.title || t.title || "Offre retirée",
        company: offer?.company || t.company || "",
        city: offer?.city || t.city || "",
        score: offer && profile.roles.length ? scoreOffer(offer, profile, skillImplies).score : null,
        followUp: t.status === "applied" && Date.now() - new Date(t.updatedAt) > FOLLOW_UP_DAYS * DAY,
      };
    }).sort((a, b) => new Date(b.updatedAt || 0) - new Date(a.updatedAt || 0)),
  [tracker, byId, profile, skillImplies]);

  const setStatus = (id, status) =>
    setTracker((t) => ({ ...t, [id]: { ...t[id], status, updatedAt: new Date().toISOString() } }));
  const remove = (id) => setTracker((t) => { const n = { ...t }; delete n[id]; return n; });

  if (!loaded) return <p className="muted">Chargement…</p>;

  const count = (s) => items.filter((i) => i.status === s).length;
  const shown = filter === "all" ? items : items.filter((i) => i.status === filter);
  const followUps = items.filter((i) => i.followUp).length;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 32 }}>
      <header style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <span className="eyebrow">{items.length} offre{items.length > 1 ? "s" : ""} suivie{items.length > 1 ? "s" : ""}</span>
        <h1 className="h1" style={{ fontSize: "clamp(36px, 5vw, 56px)" }}>Mon suivi</h1>
        {followUps > 0 && (
          <p style={{ margin: 0, color: "var(--accent)", fontWeight: 600 }}>
            {followUps} candidature{followUps > 1 ? "s" : ""} sans nouvelles depuis plus de {FOLLOW_UP_DAYS} jours : c'est le bon moment pour relancer.
          </p>
        )}
      </header>

      {items.length === 0 ? (
        <div className="empty" style={{ display: "flex", flexDirection: "column", gap: 14, alignItems: "flex-start" }}>
          <span>Tu ne suis encore aucune offre. Clique sur le signet d'une offre pour la mettre ici, puis fais avancer son statut au fil de ta candidature.</span>
          <Link href="/" className="btn btn-primary">Voir mes matchs</Link>
        </div>
      ) : (
        <>
          <div className="filters" role="group" aria-label="Filtrer par statut">
            <button className="chip" aria-pressed={filter === "all"} onClick={() => setFilter("all")}>Tous · {items.length}</button>
            {TRACK_STATUSES.map((s) => (
              <button key={s.id} className="chip" aria-pressed={filter === s.id} onClick={() => setFilter(s.id)}>{s.label} · {count(s.id)}</button>
            ))}
          </div>

          <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
            {shown.map((i) => (
              <li key={i.id} className="row" style={{ cursor: "default", flexWrap: "wrap" }}>
                <span className="row-score" style={{ width: 44 }}>{i.score ?? "–"}</span>
                <span style={{ flex: "1 1 280px", minWidth: 0, display: "flex", flexDirection: "column", gap: 4 }}>
                  {i.offer
                    ? <Link href={`/offre/${i.offer.slug}`} className="row-title" style={{ textDecoration: "none" }}>{i.title}</Link>
                    : <span className="row-title" style={{ opacity: 0.6 }}>{i.title}</span>}
                  <span className="muted" style={{ fontSize: 14 }}>
                    {[i.company, i.city].filter(Boolean).join(" · ")}
                    {!i.offer && " · plus en ligne"}
                    {" · "}mis à jour {ago(i.updatedAt)}
                    {i.followUp && <b style={{ color: "var(--accent)" }}> · à relancer</b>}
                  </span>
                </span>
                <label className="sr-only" htmlFor={`st-${i.id}`}>Statut de {i.title}</label>
                <select id={`st-${i.id}`} className="select" value={i.status} onChange={(e) => setStatus(i.id, e.target.value)}>
                  {TRACK_STATUSES.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
                </select>
                <button className="btn btn-ghost btn-icon" onClick={() => remove(i.id)} aria-label={`Retirer ${i.title} du suivi`} title="Retirer">✕</button>
              </li>
            ))}
          </ul>
          {shown.length === 0 && <p className="muted">Aucune offre avec ce statut.</p>}
        </>
      )}
    </div>
  );
}
