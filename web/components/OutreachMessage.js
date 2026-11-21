"use client";
/**
 * BLOC « MESSAGE LINKEDIN » de la fiche offre.
 * Le seul endroit de l'app qui appelle l'IA, et seulement quand on clique.
 */
import { useState } from "react";

const REASONS = {
  user_limit: "Tu as utilisé tes messages IA du jour : voici un modèle à personnaliser. Reviens demain pour une version IA.",
  global_limit: "L'IA a atteint sa limite du jour pour toute l'app : voici un modèle à personnaliser.",
  no_key: "L'IA n'est pas configurée sur ce serveur : voici un modèle à personnaliser.",
  unavailable: "L'IA ne répond pas pour le moment : voici un modèle à personnaliser.",
};

export default function OutreachMessage({ offer, profile }) {
  const [state, setState] = useState({ status: "idle" });
  const [text, setText] = useState("");
  const [copied, setCopied] = useState(false);

  async function generate(fresh = false) {
    setState({ status: "loading" });
    try {
      const res = await fetch("/api/message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ offerId: offer.id, name: profile.name, roles: profile.roles, skills: profile.skills, fresh }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Erreur");
      setText(data.message);
      setState({ status: "done", source: data.source, reason: data.reason, remaining: data.remaining });
    } catch {
      setState({ status: "error" });
    }
  }

  async function copy() {
    try { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch {}
  }

  return (
    <section style={{ display: "flex", flexDirection: "column", gap: 12, borderTop: "1px solid var(--line)", paddingTop: 24 }}>
      <h2 className="h2" style={{ fontSize: 19 }}>Message LinkedIn</h2>
      {state.status === "idle" && (
        <>
          <p className="muted" style={{ margin: 0, fontSize: 14 }}>
            Un message court pour contacter quelqu'un de l'équipe, basé sur les compétences que tu as vraiment.
          </p>
          <button className="btn btn-ghost" onClick={() => generate()}>✦ Rédiger mon message</button>
        </>
      )}
      {state.status === "loading" && <p className="muted" style={{ margin: 0 }} aria-live="polite">Rédaction en cours…</p>}
      {state.status === "error" && (
        <>
          <p className="muted" style={{ margin: 0 }}>Impossible de joindre le serveur.</p>
          <button className="btn btn-ghost" onClick={() => generate()}>Réessayer</button>
        </>
      )}
      {state.status === "done" && (
        <>
          {state.source === "template" && (
            <p style={{ margin: 0, fontSize: 13, color: "var(--accent-2)" }}>{REASONS[state.reason] || REASONS.unavailable}</p>
          )}
          <label htmlFor="outreach" className="sr-only">Message à envoyer</label>
          <textarea id="outreach" className="input" rows={9} value={text} onChange={(e) => setText(e.target.value)}
            style={{ resize: "vertical", lineHeight: 1.5, fontFamily: "inherit" }} />
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-primary" style={{ flex: 1 }} onClick={copy}>{copied ? "Copié ✓" : "Copier"}</button>
            {state.source === "ai" && state.remaining > 0 && <button className="btn btn-ghost" onClick={() => generate(true)} title="Une autre version" aria-label="Une autre version">↻</button>}
          </div>
          <span className="muted" style={{ fontSize: 12 }}>
            {state.source === "ai" ? `Rédigé par l'IA · relis-le avant d'envoyer · ${state.remaining} restant${state.remaining > 1 ? "s" : ""} aujourd'hui` : "Modèle sans IA · complète-le avant d'envoyer"}
          </span>
        </>
      )}
    </section>
  );
}
