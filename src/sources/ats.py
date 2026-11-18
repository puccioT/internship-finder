"""
CONNECTEURS ATS
---------------
Récupère les offres d'une entreprise sur Greenhouse, Lever, Ashby, Workable,
SmartRecruiters ou Personio
et les convertit toutes au MÊME format (un dictionnaire par offre).

C'est le principe de la "normalisation" : chaque plateforme nomme ses champs
différemment (title / text, absolute_url / hostedUrl...), mais le reste de l'app
ne voit qu'un seul format.
"""
import html
import re
from datetime import datetime, timezone

import httpx

TIMEOUT = 20

# Une offre est gardée si son titre contient un de ces mots.
INTERN_PATTERN = re.compile(
    r"\b(intern|internship|stage|stagiaire|alternance|alternant|alternante|apprenti|apprentie|"
    r"apprentice|apprenticeship|work[- ]study|working student|trainee|césure|gap year)\b",
    re.IGNORECASE,
)
ALTERNANCE_PATTERN = re.compile(
    r"\b(alternance|alternant|alternante|apprenti|apprentie|apprentice|apprenticeship|work[- ]study)\b",
    re.IGNORECASE,
)


# ---------- Petits utilitaires ----------

def html_to_text(raw):
    """Transforme du HTML en texte lisible (retire les balises, décode &amp; etc.)."""
    if not raw:
        return ""
    text = html.unescape(raw)                      # Greenhouse encode son HTML deux fois
    text = re.sub(r"<(br|/p|/li|/h\d)\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)           # supprime toutes les balises
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def ms_to_iso(ms):
    """Lever donne les dates en millisecondes depuis 1970 -> format ISO lisible."""
    if not ms:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def contract_from_title(title):
    return "Alternance" if ALTERNANCE_PATTERN.search(title) else "Stage"


def city_from_location(location):
    """'Paris, Île-de-France, France' -> 'Paris'. Simple mais suffisant pour filtrer."""
    if not location:
        return "Unknown"
    return location.split(",")[0].split(" - ")[0].strip() or "Unknown"


def make_offer(ats, slug, company, job_id, title, location, url, description, posted_at, department):
    return {
        "source_id": f"{ats}:{slug}:{job_id}",   # identifiant unique -> sert au dédoublonnage
        "ats": ats,
        "company": company,
        "title": title.strip(),
        "location": location or "",
        "city": city_from_location(location),
        "contract_type": contract_from_title(title),
        "department": department or "",
        "url": url,
        "description": description,
        "posted_at": posted_at,
    }


# ---------- Un connecteur par plateforme ----------

def fetch_greenhouse(client, slug, company):
    r = client.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", params={"content": "true"})
    r.raise_for_status()
    offers = []
    for job in r.json().get("jobs", []):
        departments = job.get("departments") or []
        offers.append(make_offer(
            "greenhouse", slug, company, job["id"], job["title"],
            (job.get("location") or {}).get("name"),
            job.get("absolute_url"),
            html_to_text(job.get("content")),
            job.get("first_published") or job.get("updated_at"),
            departments[0]["name"] if departments else None,
        ))
    return offers


def _fetch_lever(client, slug, company, host, ats_name):
    r = client.get(f"https://{host}/v0/postings/{slug}", params={"mode": "json"})
    r.raise_for_status()
    offers = []
    for job in r.json():
        cat = job.get("categories") or {}
        # La description Lever est en plusieurs morceaux : intro + listes (missions, profil...) + fin
        parts = [job.get("descriptionPlain", "")]
        for block in job.get("lists") or []:
            parts.append(block.get("text", ""))
            parts.append(html_to_text(block.get("content")))
        parts.append(job.get("additionalPlain", ""))
        offers.append(make_offer(
            ats_name, slug, company, job["id"], job["text"],
            cat.get("location"),
            job.get("hostedUrl"),
            "\n".join(p for p in parts if p).strip(),
            ms_to_iso(job.get("createdAt")),
            cat.get("team") or cat.get("department"),
        ))
    return offers


def fetch_lever(client, slug, company):
    return _fetch_lever(client, slug, company, "api.lever.co", "lever")


def fetch_lever_eu(client, slug, company):
    return _fetch_lever(client, slug, company, "api.eu.lever.co", "lever-eu")


def fetch_ashby(client, slug, company):
    r = client.get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    r.raise_for_status()
    offers = []
    for job in r.json().get("jobs", []):
        description = job.get("descriptionPlain") or html_to_text(job.get("descriptionHtml"))
        offers.append(make_offer(
            "ashby", slug, company, job["id"], job["title"],
            job.get("location"),
            job.get("jobUrl") or job.get("applyUrl"),
            description,
            job.get("publishedAt"),
            job.get("department") or job.get("team"),
        ))
    return offers


def fetch_workable(client, slug, company):
    r = client.get(f"https://apply.workable.com/api/v1/widget/accounts/{slug}", params={"details": "true"})
    r.raise_for_status()
    offers = []
    for job in r.json().get("jobs", []):
        location = ", ".join(p for p in (job.get("city"), job.get("country")) if p)
        offers.append(make_offer(
            "workable", slug, company, job.get("shortcode") or job.get("id"), job["title"],
            location,
            job.get("url") or job.get("application_url") or job.get("shortlink"),
            html_to_text(job.get("description")),
            job.get("published_on") or job.get("created_at"),
            job.get("department"),
        ))
    return offers


def fetch_smartrecruiters(client, slug, company):
    base = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
    postings, offset = [], 0
    while True:   # la liste est paginée par 100
        r = client.get(base, params={"limit": 100, "offset": offset})
        r.raise_for_status()
        data = r.json()
        postings += data.get("content", [])
        offset += 100
        if offset >= data.get("totalFound", 0):
            break

    offers = []
    for job in postings:
        loc = job.get("location") or {}
        location = ", ".join(p for p in (loc.get("city"), (loc.get("country") or "").upper()) if p)
        description = ""
        # La description demande un appel par offre : on ne le fait que pour les stages
        if INTERN_PATTERN.search(job["name"]):
            d = client.get(f"{base}/{job['id']}")
            if d.status_code == 200:
                sections = ((d.json().get("jobAd") or {}).get("sections") or {})
                description = "\n\n".join(
                    html_to_text((sections.get(k) or {}).get("text"))
                    for k in ("jobDescription", "qualifications", "additionalInformation")
                ).strip()
        offers.append(make_offer(
            "smartrecruiters", slug, company, job["id"], job["name"],
            location,
            job.get("postingUrl") or f"https://jobs.smartrecruiters.com/{slug}/{job['id']}",
            description,
            job.get("releasedDate"),
            (job.get("department") or {}).get("label"),
        ))
    return offers


def fetch_personio(client, slug, company):
    import xml.etree.ElementTree as ET
    for domain in ("jobs.personio.de", "jobs.personio.com"):
        r = client.get(f"https://{slug}.{domain}/xml")
        if r.status_code == 200 and r.text.lstrip().startswith("<"):
            break
    else:
        r.raise_for_status()
        raise ValueError(f"Personio feed not found for {slug}")

    offers = []
    for pos in ET.fromstring(r.content).iter("position"):
        job_id = pos.findtext("id", "")
        parts = []
        for jd in pos.iter("jobDescription"):
            parts.append(jd.findtext("name", ""))
            parts.append(html_to_text(jd.findtext("value", "")))
        offers.append(make_offer(
            "personio", slug, company, job_id, pos.findtext("name", ""),
            pos.findtext("office", ""),
            f"https://{slug}.{domain}/job/{job_id}",
            "\n".join(p for p in parts if p).strip(),
            pos.findtext("createdAt"),
            pos.findtext("department"),
        ))
    return offers


FETCHERS = {
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "lever-eu": fetch_lever_eu,
    "ashby": fetch_ashby,
    "workable": fetch_workable,
    "smartrecruiters": fetch_smartrecruiters,
    "personio": fetch_personio,
}


def fetch_company(ats, slug, company):
    """Renvoie TOUTES les offres de l'entreprise (le filtre stage est fait par le collecteur)."""
    with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
        return FETCHERS[ats](client, slug, company)


def is_internship(offer):
    return bool(INTERN_PATTERN.search(offer["title"]))
