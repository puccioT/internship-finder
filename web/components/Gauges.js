/** Anneau de score : un dégradé conique rempli à `score` %. */
export function ScoreRing({ score, size = 74, thickness = 6, background = "var(--surface)", label }) {
  return (
    <div className="ring" role="img" aria-label={`Score ${score} sur 100`}
      style={{ width: size, height: size, background: `conic-gradient(var(--accent) ${score}%, var(--surface-2) 0)` }}>
      <div className="ring-inner" style={{ width: size - 2 * thickness, height: size - 2 * thickness, background, fontSize: size * 0.32 }}>
        {score}
        {label && <span style={{ fontFamily: "var(--font-body)", fontSize: 13, fontWeight: 400, color: "var(--muted)", marginTop: 4 }}>{label}</span>}
      </div>
    </div>
  );
}

/** Jauge en segments : 3 compétences couvertes sur 5 = 3 segments allumés. */
export function Segments({ have, total }) {
  return (
    <div className="segments" role="img" aria-label={`${have} compétences sur ${total}`}>
      {Array.from({ length: total }, (_, i) => <div key={i} className={`segment${i < have ? " on" : ""}`} />)}
    </div>
  );
}

export function Bar({ value, max }) {
  return <div className="bar"><div style={{ width: `${Math.round((100 * value) / max)}%` }} /></div>;
}
