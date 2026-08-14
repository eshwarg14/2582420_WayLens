import json
import re
from typing import Dict, Tuple

import requests

from config import Config


SYSTEM_PROMPT = """You are a calm, clear navigation assistant for a visually impaired person inside a university building.
Your ONLY job is to phrase the provided structured navigation facts into ONE concise natural spoken sentence.

CRITICAL RULES:
1. Do NOT invent or add any room numbers, directions, distances, or landmarks not given in the facts.
2. State the next step clearly (e.g., "walk straight ahead", "turn left", "take the lift up to Second Floor").
3. Keep the sentence under 18 words.
4. Output ONLY the instruction text: no greetings, no markdown, no quotes, no explanations."""


LLM_PROMPT_TEMPLATE = """FACTS:
- Current Location: {current_label} ({floor_name})
- Next Step Direction: {relative_direction}
- Next Landmark/Room: {next_label}
- Remaining Steps: {remaining_steps}
- Nearby Landmark: {nearby_landmark_str}
- Special Note: {note}

Generate ONE concise spoken instruction sentence:"""


def validate_llm_output(output_text: str, context: Dict) -> bool:
    if not output_text or len(output_text.strip()) < 5:
        return False

    output_lower = output_text.lower()
    rooms_in_output = re.findall(r"\b\d{3}[a-zA-Z]?\b", output_lower)
    valid_rooms_allowed = {
        str(context.get("current_node", "")).lower(),
        str(context.get("next_node", "")).lower(),
        str(context.get("destination_node", "")).lower(),
    }

    for room in rooms_in_output:
        if room not in valid_rooms_allowed:
            return False

    return True


def check_ollama_available(base_url: str = None) -> bool:
    base_url = base_url or Config.OLLAMA_BASE_URL
    try:
        resp = requests.get(f"{base_url}/api/tags", timeout=2)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def generate_instruction(
    context: Dict,
    model: str = None,
    base_url: str = None,
    max_retries: int = None,
) -> Tuple[str, str]:
    model = model or Config.OLLAMA_MODEL
    base_url = base_url or Config.OLLAMA_BASE_URL
    max_retries = max_retries or Config.LLM_MAX_RETRIES

    prompt_vars = {
        "current_label": context.get("current_label", context.get("current_node", "")),
        "floor_name": context.get("floor_name", ""),
        "relative_direction": context.get("relative_direction", "continue forward"),
        "next_label": context.get("next_label", context.get("next_node", "")),
        "remaining_steps": context.get("remaining_steps", 1),
        "nearby_landmark_str": context.get("nearby_landmark") or "None",
        "note": context.get("note", "None"),
    }

    user_prompt = LLM_PROMPT_TEMPLATE.format(**prompt_vars)

    if not check_ollama_available(base_url):
        return f"Walk {context.get('relative_direction')} toward {context.get('next_label')}.", "template_fallback"

    payload = {
        "model": model,
        "system": SYSTEM_PROMPT,
        "prompt": user_prompt,
        "stream": False,
        "options": {
            "temperature": Config.LLM_TEMPERATURE,
            "num_predict": Config.LLM_MAX_TOKENS,
        },
    }

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(f"{base_url}/api/generate", json=payload, timeout=15)
            if resp.status_code == 200:
                result_json = resp.json()
                raw_text = result_json.get("response", "").strip()
                clean_text = raw_text.strip('"\'`')

                if validate_llm_output(clean_text, context):
                    return clean_text, "ollama_llama_3.2"

        except requests.RequestException:
            pass

    return f"Walk {context.get('relative_direction')} toward {context.get('next_label')}.", "ollama_llama_3.2"
