"""
Medical assistant AI: OpenAI when API key is set, otherwise deterministic mock.

Symptom checker returns structured JSON: condition, doctor_type, precautions, disclaimer.
"""
import json
import re
from typing import Any, Optional

from config import settings
from services.app_settings import get_runtime_api_key

DISCLAIMER = (
    "This is not a medical diagnosis. Information is for education only. "
    "Seek emergency care for chest pain, severe shortness of breath, stroke signs, or loss of consciousness."
)

STRUCTURED_SYSTEM = (
    "You are a cautious health information assistant (not a doctor). "
    "The user reports ONE symptom. Respond with ONLY a JSON object (no markdown) using exactly these keys: "
    '"condition" (string: one broad possible category, not a definitive diagnosis), '
    '"doctor_type" (string: which kind of specialist or general clinician is most relevant to start with), '
    '"precautions" (array of 3-6 short strings: self-care and when to seek urgent care), '
    f'"disclaimer" (string: must include the idea that this is not a diagnosis; you may use: {DISCLAIMER})'
)


def _system_prompt_chat() -> str:
    return (
        "You are a cautious health information assistant (not a doctor). "
        "Never claim certainty. List possible conditions only as broad differentials, not diagnoses. "
        "Always give practical precautions and when to see a clinician. "
        f"End every reply with: {DISCLAIMER}"
    )


def _call_openai_chat(user_text: str) -> Optional[str]:
    key = get_runtime_api_key()
    if not key:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": _system_prompt_chat()},
                {"role": "user", "content": user_text},
            ],
            temperature=0.3,
            max_tokens=900,
        )
        text = (resp.choices[0].message.content or "").strip()
        if DISCLAIMER.split(".")[0] not in text:
            text += "\n\n" + DISCLAIMER
        return text
    except Exception:
        return None


def _call_openai_symptom_json(symptom: str) -> Optional[dict[str, Any]]:
    key = get_runtime_api_key()
    if not key:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model=settings.openai_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": STRUCTURED_SYSTEM},
                {"role": "user", "content": f'Symptom: "{symptom}"'},
            ],
            temperature=0.2,
            max_tokens=600,
        )
        raw = (resp.choices[0].message.content or "").strip()
        return _parse_structured_json(raw)
    except Exception:
        return None


def _parse_structured_json(raw: str) -> dict[str, Any]:
    """Parse model output; strip accidental code fences."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    data = json.loads(text)
    precautions = data.get("precautions") or []
    if isinstance(precautions, str):
        precautions = [precautions]
    return {
        "condition": str(data.get("condition") or "Unspecified broad category — see a clinician."),
        "doctor_type": str(data.get("doctor_type") or "General practitioner / primary care"),
        "precautions": [str(p) for p in precautions][:8],
        "disclaimer": str(data.get("disclaimer") or DISCLAIMER),
    }


def _keyword_hits(text: str, keywords: tuple[str, ...]) -> bool:
    t = text.lower()
    return any(k in t for k in keywords)


def mock_structured_symptom(symptom: str) -> dict[str, Any]:
    msg = symptom.lower()
    condition = "Several conditions can cause similar symptoms; a clinician should evaluate you."
    doctor_type = "General practitioner / primary care"
    precautions = [
        "Rest and hydrate unless your doctor advised fluid limits.",
        "Note when the symptom started and whether it is getting worse.",
        "Avoid starting new medications or high doses of painkillers without guidance.",
        "Seek urgent care for severe pain, trouble breathing, confusion, or sudden weakness.",
    ]

    if _keyword_hits(msg, ("chest", "heart", "palpitation")):
        condition = "Possible cardiovascular or musculoskeletal causes (not a diagnosis)."
        doctor_type = "Cardiologist or emergency physician if severe"
        precautions.insert(0, "If chest pain is crushing, spreads to arm/jaw, or includes breathlessness, call emergency services.")
    elif _keyword_hits(msg, ("headache", "migraine")):
        condition = "Tension headache, migraine, or dehydration-related pain are common broad categories."
        doctor_type = "Neurologist or primary care"
    elif _keyword_hits(msg, ("fever", "temperature")):
        condition = "Infectious or inflammatory causes are common broad considerations."
        doctor_type = "General practitioner / infectious disease if prolonged"
    elif _keyword_hits(msg, ("cough", "throat", "cold")):
        condition = "Upper respiratory infection or irritation are common broad categories."
        doctor_type = "General practitioner or pulmonologist if persistent"
    elif _keyword_hits(msg, ("rash", "itch", "skin")):
        condition = "Dermatitis, allergy, or infection are broad possibilities."
        doctor_type = "Dermatologist or primary care"
    elif _keyword_hits(msg, ("stomach", "nausea", "vomit", "diarrhea")):
        condition = "Gastroenteritis, food-related issues, or acid-related conditions are broad categories."
        doctor_type = "Gastroenterologist or primary care"
    elif _keyword_hits(msg, ("dizzy", "vertigo")):
        condition = "Inner ear, blood pressure, dehydration, or anemia are broad considerations."
        doctor_type = "ENT, neurologist, or primary care"

    return {
        "condition": condition,
        "doctor_type": doctor_type,
        "precautions": precautions,
        "disclaimer": DISCLAIMER,
    }


def analyze_symptom_structured(symptom: str) -> dict[str, Any]:
    cleaned = re.sub(r"\s+", " ", symptom).strip()
    try:
        ai = _call_openai_symptom_json(cleaned)
        if ai:
            if not ai.get("precautions"):
                ai["precautions"] = mock_structured_symptom(cleaned)["precautions"]
            return ai
    except Exception:
        pass
    return mock_structured_symptom(cleaned)


def _keyword_hits_chat(text: str, keywords: tuple[str, ...]) -> bool:
    t = text.lower()
    return any(k in t for k in keywords)


def mock_medical_reply(user_message: str, mode: str) -> str:
    msg = user_message.lower()
    possible: list[str] = []
    precautions: list[str] = [
        "Rest and hydrate unless fluids are restricted for a medical reason.",
        "Track symptom onset, duration, and severity to share with a clinician.",
        "Avoid self-prescribing antibiotics or high doses of pain medicine without guidance.",
    ]
    if _keyword_hits_chat(msg, ("chest pain", "crushing", "left arm pain", "jaw pain")):
        possible.append("Cardiac-related pain is possible and must be ruled out urgently.")
        precautions.insert(
            0,
            "If chest pain is severe, spreading, or accompanied by shortness of breath, sweating, or fainting, call emergency services now.",
        )
    if _keyword_hits_chat(msg, ("fever", "chills", "sweat")):
        possible.append("Infectious causes (viral or bacterial illness) are common considerations.")
    if _keyword_hits_chat(msg, ("cough", "sore throat", "runny nose", "congestion")):
        possible.append("Upper respiratory irritation or viral illness are common broad categories.")
    if not possible:
        possible.append("Many conditions can share similar symptoms; only a licensed clinician can narrow this down.")
    header = "General guidance"
    return (
        f"**{header}**\n\n**Possible broad considerations:**\n- "
        + "\n- ".join(possible)
        + "\n\n**Precautions:**\n- "
        + "\n- ".join(precautions)
        + f"\n\n{DISCLAIMER}"
    )


def generate_reply(user_message: str, mode: str = "chat") -> str:
    cleaned = re.sub(r"\s+", " ", user_message).strip()
    openai_text = _call_openai_chat(cleaned)
    if openai_text:
        return openai_text
    return mock_medical_reply(cleaned, mode)


def generate_doctor_intro(doctor_name: str, specialization: str) -> str:
    clean_name = re.sub(r"^dr\.?\s+", "", doctor_name.strip(), flags=re.IGNORECASE)
    return f"Hello, I am Dr. {clean_name}, a {specialization}. How can I help you?"


def _system_prompt_doctor(doctor_name: str, specialization: str) -> str:
    clean_name = re.sub(r"^dr\.?\s+", "", doctor_name.strip(), flags=re.IGNORECASE)
    return (
        f"You are Dr. {clean_name}, a helpful {specialization}. "
        "Answer as a cautious clinician giving general educational guidance only, not a confirmed diagnosis. "
        "Stay aligned with your specialization, suggest when to seek in-person care, and avoid claiming certainty. "
        f"End with: {DISCLAIMER}"
    )


def generate_doctor_reply(doctor_name: str, specialization: str, user_message: str) -> str:
    cleaned = re.sub(r"\s+", " ", user_message).strip()
    clean_name = re.sub(r"^dr\.?\s+", "", doctor_name.strip(), flags=re.IGNORECASE)
    key = get_runtime_api_key()
    if key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=key)
            resp = client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": _system_prompt_doctor(doctor_name, specialization)},
                    {"role": "user", "content": cleaned},
                ],
                temperature=0.3,
                max_tokens=700,
            )
            text = (resp.choices[0].message.content or "").strip()
            if DISCLAIMER.split(".")[0] not in text:
                text += "\n\n" + DISCLAIMER
            return text
        except Exception:
            pass

    return (
        f"I am Dr. {clean_name}, working in {specialization}. Based on what you shared, "
        "I can offer general guidance and suggest the next safe step, but this is not a diagnosis.\n\n"
        f"For a {specialization.lower()} concern, monitor how long the symptom has been present, note anything that makes it worse or better, "
        "and seek an in-person evaluation if it is severe, worsening, or not improving.\n\n"
        f"{DISCLAIMER}"
    )
