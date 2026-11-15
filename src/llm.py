import json
import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
import httpx
from pydantic import BaseModel

load_dotenv()

# Modèles essayés dans l'ordre : si le premier est saturé (erreur 503/429),
# on passe au suivant. Flash-Lite d'abord : plus rapide, moins demandé, et largement
# suffisant pour écrire 2-3 phrases.
# Le premier modèle peut être changé dans le .env (GEMINI_MODEL=...) sans toucher au code.
MODELS = [os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"), "gemini-3.6-flash"]
MODELS = list(dict.fromkeys(MODELS))  # retire un éventuel doublon

# Réglages réseau du client Gemini :
# - attempts=1 : on désactive les réessais automatiques du SDK. Sinon, sur une erreur 503,
#   il réessaie plusieurs fois en attendant de plus en plus longtemps (d'où les 86 s),
#   et notre modèle de secours n'a jamais le temps de prendre le relais.
# - timeout : chaque modèle a 10 s max pour répondre avant qu'on passe au suivant.
#   10 s est le MINIMUM accepté par Google (en dessous : erreur 400 INVALID_ARGUMENT).
PER_MODEL_TIMEOUT_MS = 10_000
# Budget total : 2 modèles x 10 s + une marge.
TOTAL_TIMEOUT_S = 22

HTTP_OPTIONS = types.HttpOptions(
    timeout=PER_MODEL_TIMEOUT_MS,
    retry_options=types.HttpRetryOptions(attempts=1),
)

# Un seul "pool" de threads pour toute l'app, créé une fois.
# Avant, un pool était créé dans un `with` à chaque appel : en sortant du `with`,
# Python ATTENDAIT la fin de l'appel Gemini, donc le timeout ne coupait rien.
_EXECUTOR = ThreadPoolExecutor(max_workers=4)


def _log(msg):
    """Affiche un message dans le terminal où tourne Streamlit."""
    print(f"[Gemini] {msg}", flush=True)


def _call_gemini(api_key, prompt, config=None, http_options=HTTP_OPTIONS):
    """Interroge Gemini en essayant chaque modèle de MODELS jusqu'à ce qu'un réponde."""
    client = genai.Client(api_key=api_key, http_options=http_options)
    for i, model in enumerate(MODELS):
        start = time.time()
        try:
            response = client.models.generate_content(model=model, contents=prompt, config=config)
            _log(f"OK en {time.time() - start:.1f}s (modèle : {model})")
            return response if config else response.text
        except (errors.APIError, httpx.TimeoutException) as e:
            # 503 = surchargé, 429 = quota dépassé, TimeoutException = trop lent
            if isinstance(e, httpx.TimeoutException):
                reason = f"pas de réponse en {PER_MODEL_TIMEOUT_MS // 1000}s"
                retryable = True
            else:
                reason = str(e.code)
                retryable = e.code in (429, 503)
            if retryable and i < len(MODELS) - 1:
                _log(f"{model} indisponible ({reason}), on essaie {MODELS[i + 1]}")
                continue
            raise  # autre erreur (clé, requête...) ou plus de modèle à essayer


def _ask_gemini(prompt, timeout):
    """
    Lance l'appel dans un thread et attend au maximum `timeout` secondes.
    Renvoie (texte, None) si ça marche, (None, message_erreur) sinon.
    Les erreurs ne sont plus avalées en silence : elles sont affichées dans le terminal.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        _log("GEMINI_API_KEY introuvable dans le .env")
        return None, "GEMINI_API_KEY not found in .env file."

    future = _EXECUTOR.submit(_call_gemini, api_key, prompt)
    try:
        return future.result(timeout=timeout), None
    except TimeoutError:
        # On n'attend plus : l'appel continue en arrière-plan mais l'app reprend la main.
        _log(f"TIMEOUT : pas de réponse après {timeout}s (modèles : {MODELS})")
        return None, f"Gemini did not answer within {timeout}s."
    except Exception as e:
        _log(f"ERREUR {type(e).__name__} : {e}")
        traceback.print_exc()
        return None, f"Gemini error ({type(e).__name__}): {e}"


# =====================================================================
# 1. EXTRACTION : le LLM lit une offre et en fait une fiche structurée
# =====================================================================

ROLE_FAMILIES = ["Product", "Data", "Strategy & Ops", "Marketing & Growth", "Sales & Business Dev",
                 "Finance & Legal", "Engineering", "Design", "People & HR", "Other"]
REMOTE_VALUES = ["On-site", "Hybrid", "Full remote", "Unknown"]


class OfferInfo(BaseModel):
    """Le "formulaire" que Gemini doit remplir. Le SDK l'impose en sortie (JSON garanti)."""
    role_family: str
    skills: list[str]
    summary: str
    start_date: str
    duration_months: int | None
    languages: list[str]
    remote: str


EXTRACTION_PROMPT = """You analyse internship and work-study job offers for business-school students.
Read the offer below and fill every field. Base everything ONLY on the offer text; never invent.

Fields:
- role_family: the job's REAL function, one of {families}.
  Judge the actual missions, not keywords: "Legal Intern - Product & Compliance" is "Finance & Legal";
  "Product Manager Intern" or "Product Owner apprentice" is "Product"; "Product Content Manager" is
  "Marketing & Growth" unless it is clearly product management.
- skills: the 4 to 8 most important skills or tools REQUIRED or strongly expected, short canonical
  English names (e.g. "SQL", "Excel", "Figma", "Data analysis", "Stakeholder management", "Copywriting").
- summary: 2 sentences in English describing what the intern will concretely DO (missions),
  no company marketing.
- start_date: start date as written in the offer (e.g. "January 2027", "ASAP"), or "Unknown".
- duration_months: internship duration in months as an integer, or null if not stated.
- languages: required languages with level, e.g. ["French (fluent)", "English (professional)"]; [] if not stated.
- remote: one of {remote}.

OFFER
Title: {title}
Company: {company}
Description:
{description}
"""

# L'extraction tourne dans le terminal (pas dans l'app) : on peut attendre plus longtemps.
EXTRACTION_HTTP_OPTIONS = types.HttpOptions(timeout=40_000, retry_options=types.HttpRetryOptions(attempts=1))


def extract_offer_info(title, company, description):
    """Renvoie un dict validé. Lève une exception si Gemini échoue (gérée par src/extract.py)."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not found in .env file.")

    prompt = EXTRACTION_PROMPT.format(
        families=", ".join(ROLE_FAMILIES), remote=", ".join(REMOTE_VALUES),
        title=title, company=company, description=(description or "")[:6000],
    )
    config = types.GenerateContentConfig(
        response_mime_type="application/json",   # Gemini doit répondre en JSON...
        response_schema=OfferInfo,               # ...qui respecte exactement ce schéma
        temperature=0,                           # réponses stables et factuelles
    )
    response = _call_gemini(api_key, prompt, config=config, http_options=EXTRACTION_HTTP_OPTIONS)
    info = response.parsed or OfferInfo(**json.loads(response.text))
    data = info.model_dump()

    # On ne fait pas confiance aveuglément au LLM : on vérifie les valeurs fermées.
    if data["role_family"] not in ROLE_FAMILIES:
        data["role_family"] = "Other"
    if data["remote"] not in REMOTE_VALUES:
        data["remote"] = "Unknown"
    data["skills"] = [s.strip() for s in data["skills"] if s.strip()][:8]
    return data


# =====================================================================
# 2. AI INSIGHT : verdict honnête sur le match
# =====================================================================

def get_match_explanation(target_role, user_skills, title, company, role_family, summary, required, matched, missing):
    """Verdict honnête : Strong / Partial / Weak match + raison + 1 conseil."""
    # Verdict de secours (si Gemini ne répond pas), calculé avec des règles simples
    if role_family != target_role:
        verdict = "Weak match"
    elif required and len(matched) >= len(required) / 2:
        verdict = "Strong match"
    else:
        verdict = "Partial match"
    fallback = (
        f"**{verdict}.** This {title} role at {company} is classified as {role_family}. "
        + (f"You already cover {', '.join(matched)}. " if matched else "None of your listed skills appear in the requirements. ")
        + (f"Main gap to work on: {missing[0]}." if missing else "")
    )

    prompt = f"""
    You are a blunt, honest career advisor for a business-school student. Do NOT flatter.
    Start with exactly one verdict in bold: **Strong match**, **Partial match** or **Weak match**.
    Then ONE sentence explaining why, based on the role's real function and the skills gap.
    Then ONE concrete tip (how to bridge the main gap, or why to skip this offer).
    Maximum 3 sentences in total. Address the candidate as "you".
    Only mention skills from the lists below; never claim the candidate has other skills.

    Candidate: targets {target_role} roles. Skills: {", ".join(user_skills) or "none listed"}.

    Offer: {title} at {company}
    Real function: {role_family}
    Missions: {summary}
    Required skills: {", ".join(required) or "not specified"}
    Required skills the candidate has: {", ".join(matched) or "none"}
    Required skills the candidate lacks: {", ".join(missing) or "none"}
    """
    ai_text, error = _ask_gemini(prompt, timeout=TOTAL_TIMEOUT_S)
    return fallback if error else ai_text.strip()


# =====================================================================
# 3. PITCH LINKEDIN
# =====================================================================

def generate_outreach_message(target_role, user_skills, title, company, summary):
    """Génère un message d'approche LinkedIn sur-mesure."""
    prompt = f"""
    You are an expert career coach. Write a short, engaging LinkedIn connection request message
    (under 600 characters) for a student applying to an internship.

    Student: targets {target_role} roles, skilled in {", ".join(user_skills)}.
    Target role: {title} at {company}.
    Missions: {summary}

    Rules:
    - Professional, energetic, concise.
    - Highlight one specific overlap between the student's skills and the missions. Never invent skills.
    - End with a polite call to action for a quick chat.
    - No placeholders like [Your Name]. Just the body of the message.
    """
    ai_text, error = _ask_gemini(prompt, timeout=TOTAL_TIMEOUT_S)
    return f"⚠️ {error}" if error else ai_text
