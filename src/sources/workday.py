"""
CONNECTEUR WORKDAY (grands groupes)
-----------------------------------
Les grandes entreprises (Salesforce, Visa, Philips, ING, Deutsche Bank...) n'utilisent
pas les ATS "startup" (Greenhouse, Lever, Ashby...) mais Workday.

Chaque page carrière Workday a une adresse du type :
    https://{tenant}.{wdN}.myworkdayjobs.com/{site}
    ex. https://salesforce.wd12.myworkdayjobs.com/External_Career_Site

Derrière, une API JSON publique (celle qu'utilise la page elle-même) :
    POST /wday/cxs/{tenant}/{site}/jobs            -> liste paginée (20 par page), avec recherche
    GET  /wday/cxs/{tenant}/{site}{externalPath}   -> détail d'une offre (description)

Différence avec les autres connecteurs : un grand groupe a des MILLIERS d'offres dans le
monde. On ne télécharge donc pas tout : on cherche par mots-clés ("intern", "praktikum"...),
puis on ne garde que les stages situés dans les pays visés AVANT de demander les descriptions.

L'identifiant ne se devine pas à partir du nom (tenant, numéro de serveur wdN, nom du site) :
les entreprises sont donc listées à la main dans WORKDAY_COMPANIES, avec des adresses vérifiées.
"""
import re
import time

from src.sources.ats import INTERN_PATTERN, html_to_text, make_offer

# (entreprise, tenant, serveur, [sites]) — adresses relevées sur leurs pages carrières
WORKDAY_COMPANIES = [
    ("Salesforce", "salesforce", "wd12", ["External_Career_Site"]),
    ("Workday", "workday", "wd5", ["Workday", "Workday_Early_Career"]),
    ("Visa", "visa", "wd5", ["Visa", "Visa_Early_Careers"]),
    ("Philips", "philips", "wd3", ["jobs-and-careers"]),
    ("ING", "ing", "wd3", ["ICSGBLCOR"]),
    ("Deutsche Bank", "db", "wd3", ["DBWebsite"]),
    ("Shell", "shell", "wd3", ["ShellCareers"]),
    ("Intel", "intel", "wd1", ["External"]),
    ("Airbus", "ag", "wd3", ["Airbus"]),
    ("Autodesk", "autodesk", "wd1", ["uni"]),
    ("Red Hat", "redhat", "wd5", ["jobs"]),
    ("CrowdStrike", "crowdstrike", "wd5", ["crowdstrikecareers"]),
    ("Pernod Ricard", "pernodricard", "wd3", ["pernod-ricard"]),
    ("Motorola Solutions", "motorolasolutions", "wd5", ["Careers"]),
    ("Puma", "puma", "wd502", ["Jobs_at_Puma"]),
    ("Novartis", "novartis", "wd3", ["Novartis_Careers"]),
]

# Moins de mots-clés = moins de requêtes ("intern" ramène déjà la plupart des "internship")
SEARCH_TERMS = ["intern", "internship", "praktikum", "werkstudent", "stage"]
PAUSE_S = 3.0        # pause entre deux requêtes : plus rapide, Workday bloque (429)
MAX_PER_TERM = 200   # garde-fou : au-delà, la recherche ramène surtout du bruit
PAGE_SIZE = 20       # maximum accepté par Workday

# Pays visés (France + étranger). Workday écrit les lieux de façons variées :
# "Germany - Munich", "DEU - Munich", "Amsterdam", "London, United Kingdom"...
TARGET_LOCATION = re.compile(
    r"\b(france|paris|lyon|germany|deutschland|deu|berlin|munich|münchen|muenchen|hamburg|frankfurt|"
    r"netherlands|nederland|nld|amsterdam|rotterdam|eindhoven|utrecht|the hague|den haag|"
    r"ireland|irl|dublin|united kingdom|uk|gbr|england|london|"
    r"switzerland|schweiz|suisse|che|zurich|zürich|geneva|genève|lausanne|basel)\b",
    re.IGNORECASE,
)
MULTI_LOCATION = re.compile(r"^\d+\s+locations?$", re.IGNORECASE)   # "3 Locations" : il faut ouvrir le détail


# Workday met souvent le pays AVANT la ville : "Germany - Munich", "DEU - Munich", "Ireland, Dublin"
COUNTRY_FIRST = re.compile(
    r"^(germany|deu|netherlands|nld|ireland|irl|united kingdom|gbr|uk|switzerland|che|france|fra|"
    r"usa|united states|canada|spain|esp|italy|ita|poland|pol|india|ind|belgium|austria|aut)\s*[-,]\s*(.+)$",
    re.IGNORECASE,
)


def tidy_location(raw):
    """'Germany - Munich' -> 'Munich, Germany' (la ville d'abord, comme les autres plateformes)."""
    raw = re.sub(r"^(headquarters?|hq|siège)\s*[-,:]\s*", "", (raw or "").strip(), flags=re.IGNORECASE)
    m = COUNTRY_FIRST.match(raw)
    return f"{m.group(2).strip()}, {m.group(1).strip()}" if m else raw


class WorkdayBlocked(Exception):
    """Workday refuse nos requêtes (429 persistant) ou le temps alloué est écoulé.
    On lève une erreur plutôt que de renvoyer une liste incomplète : sinon la collecte
    croirait que les offres manquantes ont disparu et les marquerait inactives."""


_deadline = None   # heure limite pour l'ensemble des grands groupes (voir set_deadline)


def set_deadline(seconds):
    """Temps maximum accordé à Workday pendant une collecte (au-delà : on garde les offres de la veille)."""
    global _deadline
    _deadline = time.monotonic() + seconds


def _request(client, method, url, **kwargs):
    """
    Requête "polie" : une pause avant chaque appel ; si Workday répond 429 (trop de requêtes),
    on attend un peu (60 s max) et on réessaie 2 fois. Au-delà, on abandonne cette entreprise
    pour aujourd'hui (WorkdayBlocked) : ses offres de la veille sont conservées.
    """
    for attempt in range(3):
        if _deadline and time.monotonic() > _deadline:
            raise WorkdayBlocked("temps alloué à Workday écoulé")
        time.sleep(PAUSE_S)
        r = client.request(method, url, **kwargs)
        if r.status_code != 429:
            return r
        retry_after = r.headers.get("Retry-After", "")
        wait = min(int(retry_after) if retry_after.isdigit() else 30 * (attempt + 1), 60)
        print(f"    [Workday] trop de requêtes, pause de {wait} s...")
        time.sleep(wait)
    raise WorkdayBlocked("429 Too Many Requests persistant")


def search_jobs(client, base, term):
    """Toutes les offres qui correspondent à un mot-clé (pagination par 20)."""
    jobs, offset = [], 0
    while offset < MAX_PER_TERM:
        r = _request(client, "POST", f"{base}/jobs",
                     json={"appliedFacets": {}, "limit": PAGE_SIZE, "offset": offset, "searchText": term})
        r.raise_for_status()
        data = r.json()
        page = data.get("jobPostings") or []
        jobs += page
        offset += PAGE_SIZE
        if not page or offset >= (data.get("total") or 0):
            break
    return jobs


def fetch_workday(client, slug, company):
    """slug = 'tenant|wdN|site1,site2' (format utilisé dans companies.csv)."""
    tenant, server, sites = slug.split("|")
    host = f"https://{tenant}.{server}.myworkdayjobs.com"
    offers, seen = [], set()

    for site in sites.split(","):
        base = f"{host}/wday/cxs/{tenant}/{site}"
        # 1. Recherche par mots-clés, dédoublonnée
        candidates = {}
        for term in SEARCH_TERMS:
            for job in search_jobs(client, base, term):
                path = job.get("externalPath")
                if path and path not in candidates:
                    candidates[path] = job

        for path, job in candidates.items():
            title = job.get("title") or ""
            where = job.get("locationsText") or ""
            # 2. Filtre AVANT le détail : un stage, dans un pays visé (ou plusieurs lieux à vérifier)
            if not INTERN_PATTERN.search(title):
                continue
            if not (TARGET_LOCATION.search(where) or MULTI_LOCATION.match(where.strip())):
                continue

            # 3. Détail de l'offre : description + lieux exacts
            r = _request(client, "GET", f"{base}{path}")
            if r.status_code == 404:
                continue          # offre retirée entre la recherche et le détail
            r.raise_for_status()  # autre erreur : on abandonne l'entreprise (offres de la veille gardées)
            info = r.json().get("jobPostingInfo") or {}
            locations = [tidy_location(l) for l in [info.get("location") or where, *(info.get("additionalLocations") or [])] if l]
            # Les lieux dans les pays visés passent devant ("NYC / London" -> "London / NYC")
            locations.sort(key=lambda l: not TARGET_LOCATION.search(l))
            location = " / ".join(locations)
            if not TARGET_LOCATION.search(location):
                continue   # "3 Locations" qui étaient finalement hors Europe

            job_id = info.get("jobReqId") or path.rsplit("_", 1)[-1]
            if job_id in seen:   # même offre publiée sur deux sites
                continue
            seen.add(job_id)
            offers.append(make_offer(
                "workday", tenant, company, job_id, info.get("title") or title,
                location,
                info.get("externalUrl") or f"{host}/{site}{path}",
                html_to_text(info.get("jobDescription")),
                info.get("startDate"),
                "",
            ))
    return offers


def workday_rows():
    """Les entreprises Workday au même format que les lignes de companies.csv."""
    return [{"company": name, "ats": "workday", "slug": f"{tenant}|{server}|{','.join(sites)}"}
            for name, tenant, server, sites in WORKDAY_COMPANIES]
