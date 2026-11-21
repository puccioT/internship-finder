"use client";
/**
 * PROFIL ET SUIVI — stockés dans le navigateur (localStorage).
 * Pas de compte, pas de serveur : chaque visiteur garde ses données chez lui.
 */
import { useEffect, useState, useCallback, useRef } from "react";

// Profil vierge : un nouveau visiteur passe d'abord par l'onboarding (/profil).
export const DEFAULT_PROFILE = {
  name: "",
  roles: [],
  skills: [],
  countries: [],                      // [] = tous les pays
  languages: [],                      // langues parlées (codes anglais) ; [] = pas de filtre
  hideLanguageMismatch: true,         // masquer les offres qui exigent une autre langue
  onboarded: false,                   // l'utilisateur a-t-il terminé l'onboarding ?
  contract: "Tous",
};

function read(key, fallback) {
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? { ...fallback, ...JSON.parse(raw) } : fallback;
  } catch {
    return fallback;
  }
}

function write(key, value) {
  try { window.localStorage.setItem(key, JSON.stringify(value)); } catch { /* stockage indisponible : on continue sans */ }
}

/** Petit "hook" réutilisable : une valeur gardée dans le navigateur, synchronisée entre composants. */
function useStored(key, fallback) {
  const [value, setValue] = useState(fallback);
  const [loaded, setLoaded] = useState(false);
  // On garde aussi la valeur dans une "ref" : on peut la lire sans passer par une fonction
  // de mise à jour de React (que React exécute DEUX FOIS en développement pour détecter les bugs).
  const current = useRef(fallback);

  useEffect(() => {
    current.current = read(key, fallback);
    setValue(current.current);
    setLoaded(true);
    const sync = (e) => {
      if (e.detail === key) { current.current = read(key, fallback); setValue(current.current); }
    };
    window.addEventListener("if-store", sync);
    return () => window.removeEventListener("if-store", sync);
  }, [key]); // eslint-disable-line react-hooks/exhaustive-deps

  const update = useCallback((next) => {
    // On calcule la nouvelle valeur UNE seule fois, puis on l'enregistre et on prévient
    // les autres composants. (Avant, ce calcul se faisait dans une fonction exécutée 2 fois :
    // un clic pouvait ajouter puis retirer un rôle aussitôt.)
    const v = typeof next === "function" ? next(current.current) : next;
    current.current = v;
    setValue(v);
    write(key, v);
    window.dispatchEvent(new CustomEvent("if-store", { detail: key }));
  }, [key]);

  return [value, update, loaded];
}

export const useProfile = () => useStored("if-profile", DEFAULT_PROFILE);

/** Lecture directe (pas d'état React) : utile pour décider d'une redirection sans valeur périmée. */
export const isOnboarded = () => read("if-profile", DEFAULT_PROFILE).onboarded === true;

/**
 * Suivi : { [offerId]: { status, addedAt, updatedAt, title, company, city, slug } }
 * On garde le titre et l'entreprise : si l'offre disparaît des données, la ligne reste lisible.
 */
export const TRACK_STATUSES = [
  { id: "todo", label: "À postuler" },
  { id: "applied", label: "Postulé" },
  { id: "interview", label: "Entretien" },
  { id: "closed", label: "Clôturé" },   // refusé, abandonné ou offre fermée
];
export const useTracker = () => useStored("if-tracker", {});
