import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dotenv import load_dotenv
from google import genai
from google.genai import errors

load_dotenv()

# Modèles essayés dans l'ordre : si le premier est saturé (erreur 503/429),
# on passe au suivant. Flash-Lite d'abord : plus rapide, moins demandé, et largement
# suffisant pour écrire 2-3 phrases.
# Le premier modèle peut être changé dans le .env (GEMINI_MODEL=...) sans toucher au code.
MODELS = [os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"), "gemini-3.6-flash"]
MODELS = list(dict.fromkeys(MODELS))  # retire un éventuel doublon

# Un seul "pool" de threads pour toute l'app, créé une fois.
# Avant, un pool était créé dans un `with` à chaque appel : en sortant du `with`,
# Python ATTENDAIT la fin de l'appel Gemini, donc le timeout ne coupait rien.
_EXECUTOR = ThreadPoolExecutor(max_workers=4)


def _log(msg):
    """Affiche un message dans le terminal où tourne Streamlit."""
    print(f"[Gemini] {msg}", flush=True)


def _call_gemini(api_key, prompt):
    """Interroge Gemini en essayant chaque modèle de MODELS jusqu'à ce qu'un réponde."""
    client = genai.Client(api_key=api_key)
    for i, model in enumerate(MODELS):
        start = time.time()
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            _log(f"OK en {time.time() - start:.1f}s (modèle : {model})")
            return response.text
        except errors.APIError as e:
            overloaded = e.code in (429, 503)  # 503 = surchargé, 429 = quota dépassé
            if overloaded and i < len(MODELS) - 1:
                _log(f"{model} indisponible ({e.code}), on essaie {MODELS[i + 1]}")
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


def get_match_explanation(user_domain, user_skills, job_title, job_company, job_skills, job_description):
    """Génère l'explication de l'IA sur le matching des compétences."""
    req_skills = [s.strip() for s in str(job_skills).split(';') if s.strip()]
    user_skills_lower = [s.lower() for s in user_skills]

    matched = [s for s in req_skills if s.lower() in user_skills_lower]
    missing = [s for s in req_skills if s.lower() not in user_skills_lower]

    matched_text = ", ".join(matched) if matched else "your analytical and business background"
    missing_tip = (
        f"To stand out during interviews, prepare a concrete example showing how you can quickly ramp up on **{missing[0]}**."
        if missing else
        "You cover 100% of the required technical stack—focus on highlighting your past project impact."
    )

    smart_fallback = (
        f"**AI Career Advisor:** This **{job_title}** role at **{job_company}** is a strong fit for your "
        f"target in {user_domain}, directly leveraging your skills in **{matched_text}**. "
        f"{missing_tip}"
    )

    skills_str = ", ".join(user_skills)
    prompt = f"""
    You are an expert tech career advisor.
    Write a concise, 2-sentence explanation of why this internship matches the candidate's profile based on the role description, and give 1 concrete tip on how to position themselves or bridge any missing skill. Address the candidate directly as "you".

    Candidate Profile:
    - Target Domain: {user_domain}
    - Current Skills: {skills_str}

    Internship Offer:
    - Role: {job_title} at {job_company}
    - Required Skills: {job_skills}
    - Role Description: {job_description}
    """

    ai_text, error = _ask_gemini(prompt, timeout=10)
    if error:
        return smart_fallback
    return f"**AI Career Advisor:** {ai_text}"


def generate_outreach_message(user_domain, user_skills, job_title, job_company, job_description):
    """Génère un message d'approche LinkedIn sur-mesure."""
    skills_str = ", ".join(user_skills)

    prompt = f"""
    You are an expert career coach. Write a short, highly engaging LinkedIn connection request message (under 600 characters) for a student looking for an internship.

    Student Profile: Targets {user_domain}, skilled in {skills_str}.
    Target Role: {job_title} at {job_company}.
    Role Context: {job_description}.

    Rules:
    - Keep it professional, energetic, and concise.
    - Highlight one specific overlap between the student's skills and the role.
    - End with a polite call to action for a quick chat.
    - Do not use placeholders like [Your Name]. Just write the body of the message.
    """

    ai_text, error = _ask_gemini(prompt, timeout=15)
    if error:
        # Le message d'erreur s'affiche dans la zone de texte : on sait ce qui ne va pas.
        return f"⚠️ {error}"
    return ai_text
