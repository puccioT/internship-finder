"""
DATE DE DÉBUT : texte libre -> période (mois au plus tôt, mois au plus tard)
-------------------------------------------------------------------------
L'IA recopie la date telle qu'écrite dans l'offre : "January 2027", "Janvier 2027",
"ASAP", "Q1/27", "February, March, April, May, or June 2027", "Summer 2027"...
Pour filtrer ("je peux commencer à partir de juillet 2027"), on la convertit en
deux mois "AAAA-MM" : le plus tôt et le plus tard possibles.

Règle de filtrage côté app : une offre est gardée si son mois "au plus tard"
est >= au mois de disponibilité de l'étudiant. Date inconnue -> offre gardée.
"""
import re
from datetime import date

MONTHS = {
    1: ["january", "janvier", "januar", "jan"], 2: ["february", "février", "fevrier", "februar", "feb", "fév"],
    3: ["march", "mars", "märz", "maerz", "mar"], 4: ["april", "avril", "apr", "avr"],
    5: ["may", "mai"], 6: ["june", "juin", "juni", "jun"], 7: ["july", "juillet", "juli", "jul"],
    8: ["august", "août", "aout", "aug"], 9: ["september", "septembre", "sept", "sep"],
    10: ["october", "octobre", "oktober", "oct", "okt"], 11: ["november", "novembre", "nov"],
    12: ["december", "décembre", "decembre", "dezember", "dec", "déc", "dez"],
}
SEASONS = {"spring": (3, 5), "printemps": (3, 5), "summer": (6, 8), "été": (6, 8), "sommer": (6, 8),
           "autumn": (9, 11), "fall": (9, 11), "automne": (9, 11), "herbst": (9, 11), "winter": (1, 2), "hiver": (1, 2)}
QUARTERS = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}
ASAP = re.compile(r"asap|as soon as possible|immediate|dès que possible|des que possible|ab sofort|sofort|now\b", re.I)

_WORD_TO_MONTH = {w: m for m, words in MONTHS.items() for w in words}
_MONTH_RE = re.compile(r"\b(" + "|".join(sorted(map(re.escape, _WORD_TO_MONTH), key=len, reverse=True)) + r")\b\.?", re.I)


def _ym(y, m):
    return f"{y:04d}-{m:02d}"


def parse_start(text, ref=None):
    """
    Renvoie (au_plus_tot, au_plus_tard) en "AAAA-MM", ou (None, None) si inconnu.
    ref = date de référence (date de collecte) pour deviner l'année quand elle manque.
    """
    ref = ref or date.today()
    t = (text or "").strip().lower()
    if not t or t in {"unknown", "n/a", "none", "flexible"}:
        return None, None
    if ASAP.search(t):
        now = _ym(ref.year, ref.month)
        return now, now

    years = [int(y) for y in re.findall(r"\b(20\d\d)\b", t)]
    years += [2000 + int(y) for y in re.findall(r"q[1-4]\s*/\s*(\d\d)\b", t)]   # "Q1/27"
    months = []
    for m in _MONTH_RE.findall(t):
        months.append((_WORD_TO_MONTH[m.lower().rstrip(".")],) * 2)
    for word, rng in SEASONS.items():
        if re.search(rf"\b{word}\b", t):
            months.append(rng)
    for q in re.findall(r"\bq([1-4])\b", t):
        months.append(QUARTERS[int(q)])

    if not months and not years:
        return None, None
    if not months:                      # "2027" seul -> toute l'année
        return _ym(min(years), 1), _ym(max(years), 12)

    lo, hi = min(a for a, _ in months), max(b for _, b in months)
    if not years:
        # Pas d'année : la prochaine période de ce nom qui n'est pas déjà passée
        y = ref.year if hi >= ref.month else ref.year + 1
        y_hi = y if hi >= lo else y + 1
        return _ym(y, lo), _ym(y_hi, hi)
    if len(set(years)) > 1:
        # "December / January 2026/2027" : la période enjambe le changement d'année
        y1, y2 = min(years), max(years)
        return _ym(y1, hi if hi >= lo else lo), _ym(y2, lo)
    y = years[0]
    return _ym(y, lo), _ym(y, hi)
