"use client";
/**
 * BLOC « MESSAGE LINKEDIN » de la fiche offre.
 * Le seul endroit de l'app qui appelle l'IA, et seulement quand on clique.
 */
import { useState } from "react";

const REASONS = {
  user_limit: "You've used today's AI messages: here's a template to personalise. Come back tomorrow for an AI version.",
  global_limit: "The AI has reached today's limit for the whole app: here's a template to personalise.",
  no_key: "AI isn't configured on this server: here's a template to personalise.",
  unavailable: "The AI isn't responding right now: here's a template to personalise.",
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
      <h2 className="h2" style={{ fontSize: 19 }}>LinkedIn message</h2>
      {state.status === "idle" && (
        <>
          <p className="muted" style={{ margin: 0, fontSize: 14 }}>
            A short message to reach someone on the team, based on the skills you really have.
          </p>
          <button className="btn btn-ghost" onClick={() => generate()}>✦ Write my message</button>
        </>
      )}
      {state.status === "loading" && <p className="muted" style={{ margin: 0 }} aria-live="polite">Writing…</p>}
      {state.status === "error" && (
        <>
          <p className="muted" style={{ margin: 0 }}>Couldn't reach the server.</p>
          <button className="btn btn-ghost" onClick={() => generate()}>Try again</button>
        </>
      )}
      {state.status === "done" && (
        <>
          {state.source === "template" && (
            <p style={{ margin: 0, fontSize: 13, color: "var(--accent-2)" }}>{REASONS[state.reason] || REASONS.unavailable}</p>
          )}
          <label htmlFor="outreach" className="sr-only">Message to send</label>
          <textarea id="outreach" className="input" rows={9} value={text} onChange={(e) => setText(e.target.value)}
            style={{ resize: "vertical", lineHeight: 1.5, fontFamily: "inherit" }} />
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-primary" style={{ flex: 1 }} onClick={copy}>{copied ? "Copied ✓" : "Copy"}</button>
            {state.source === "ai" && state.remaining > 0 && <button className="btn btn-ghost" onClick={() => generate(true)} title="Another version" aria-label="Another version">↻</button>}
          </div>
          <span className="muted" style={{ fontSize: 12 }}>
            {state.source === "ai" ? `Written by AI · proofread before sending · ${state.remaining} left today` : "Template (no AI) · complete it before sending"}
          </span>
        </>
      )}
    </section>
  );
}
