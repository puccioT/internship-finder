"use client";
import { useTracker } from "@/lib/store";

/** Bouton signet : ajoute l'offre à "À postuler" dans le suivi, ou l'en retire. */
export default function TrackButton({ offerId, offer, variant = "icon" }) {
  const [tracker, setTracker] = useTracker();
  const tracked = Boolean(tracker[offerId]);
  const toggle = () =>
    setTracker((t) => {
      const next = { ...t };
      if (next[offerId]) delete next[offerId];
      else {
        const now = new Date().toISOString();
        next[offerId] = { status: "todo", addedAt: now, updatedAt: now,
          ...(offer && { title: offer.title, company: offer.company, city: offer.city, slug: offer.slug }) };
      }
      return next;
    });

  if (variant === "full") {
    return (
      <button className="btn btn-ghost" onClick={toggle} aria-pressed={tracked}>
        {tracked ? "✓ Dans mon suivi" : "Ajouter à mon suivi"}
      </button>
    );
  }
  return (
    <button className="btn btn-ghost btn-icon" onClick={toggle} aria-pressed={tracked}
      aria-label={tracked ? "Retirer de mon suivi" : "Ajouter à mon suivi"}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill={tracked ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" /></svg>
    </button>
  );
}
