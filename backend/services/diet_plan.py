"""Diet guidance as structured data; optional OpenAI enrichment."""
import json
from typing import Any, Optional

from config import settings

BASE_PLAN = {
    "recommended_foods": [
        "Vegetables (leafy greens, broccoli, carrots) for fiber and micronutrients.",
        "Whole grains (oats, brown rice, quinoa) for sustained energy.",
        "Lean proteins (beans, lentils, fish, poultry if appropriate for you).",
        "Fresh fruit in moderation; water as the primary drink.",
        "Nuts and seeds in small portions for healthy fats.",
    ],
    "foods_to_avoid": [
        "Ultra-processed snacks and sugary drinks.",
        "Excess added salt if you have hypertension (follow clinician advice).",
        "Large portions of fried foods and trans-fat–heavy items.",
        "Alcohol beyond what your clinician considers safe for you.",
    ],
    "healthy_habits": [
        "Regular meal times and mindful eating (avoid distracted snacking).",
        "Aim for consistent sleep — appetite hormones are tied to rest.",
        "Pair nutrition with physical activity appropriate to your fitness level.",
        "Discuss supplements only with a qualified professional.",
    ],
    "disclaimer": "This is general wellness information, not personalized medical nutrition therapy. Follow your clinician’s plan for conditions like diabetes, kidney disease, or allergies.",
}


def _openai_diet() -> Optional[dict[str, Any]]:
    key = (settings.openai_api_key or "").strip()
    if not key:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model=settings.openai_model,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return ONLY JSON with keys recommended_foods, foods_to_avoid, healthy_habits (each an array of strings), "
                        "and disclaimer (string mentioning not replacing a dietitian/doctor)."
                    ),
                },
                {
                    "role": "user",
                    "content": "Give concise evidence-informed diet tips for a generally healthy adult without specific diagnoses.",
                },
            ],
            temperature=0.35,
            max_tokens=700,
        )
        raw = (resp.choices[0].message.content or "").strip()
        data = json.loads(raw)
        return {
            "recommended_foods": list(data.get("recommended_foods") or [])[:12],
            "foods_to_avoid": list(data.get("foods_to_avoid") or [])[:12],
            "healthy_habits": list(data.get("healthy_habits") or [])[:12],
            "disclaimer": str(data.get("disclaimer") or BASE_PLAN["disclaimer"]),
        }
    except Exception:
        return None


def get_diet_plan() -> dict[str, Any]:
    merged = {**BASE_PLAN}
    ai = _openai_diet()
    if ai:
        for k in ("recommended_foods", "foods_to_avoid", "healthy_habits"):
            if ai.get(k):
                merged[k] = ai[k]
        if ai.get("disclaimer"):
            merged["disclaimer"] = ai["disclaimer"]
    return merged
