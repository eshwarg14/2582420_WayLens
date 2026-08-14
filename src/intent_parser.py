import re
from typing import Optional, Tuple, Set

from building_graph import load_graph, get_all_room_ids, find_node_by_alias


WORD_TO_DIGIT = {
    "zero": "0", "oh": "0", "one": "1", "won": "1",
    "two": "2", "to": "2", "too": "2", "three": "3", "tree": "3",
    "four": "4", "for": "4", "fore": "4", "five": "5",
    "six": "6", "sex": "6", "seven": "7", "eight": "8", "ate": "8",
    "nine": "9", "ten": "10",
    "eleven": "11", "twelve": "12", "thirteen": "13", "fourteen": "14",
    "fifteen": "15", "sixteen": "16", "seventeen": "17", "eighteen": "18",
    "nineteen": "19", "twenty": "20", "twenty-one": "21", "twenty-two": "22",
    "twenty-three": "23", "twenty-four": "24", "twenty-five": "25",
    "twenty-six": "26", "twenty-seven": "27", "forty-one": "41",
    "forty-two": "42", "forty-three": "43", "forty-four": "44",
    "forty-six": "46", "forty-seven": "47", "fifty-one": "51",
    "fifty-two": "52", "fifty-three": "53", "fifty-four": "54",
    "fifty-five": "55"
}

ROOM_PATTERN = re.compile(r"\b([567]\d{2}[A-Za-z]?)\b", re.IGNORECASE)


def normalize_transcript(text: str) -> str:
    text = text.lower().strip()
    return re.sub(r"[^\w\s-]", "", text)


def parse_spoken_number(text: str) -> Optional[str]:
    tokens = text.split()
    converted_tokens = [WORD_TO_DIGIT.get(tok, tok) for tok in tokens]
    joined = " ".join(converted_tokens)

    m = re.search(r"\b([567])\s+0?\s*(\d{1,2})\s*([a-zA-Z])?\b", joined)
    if m:
        floor, num, suffix = m.groups()
        num_str = f"{int(num):02d}"
        suf_str = suffix.upper() if suffix else ""
        return f"{floor}{num_str}{suf_str}"

    m_digits = re.search(r"\b([567])\s+(\d)\s+(\d)\s*([a-zA-Z])?\b", joined)
    if m_digits:
        f, d1, d2, suf = m_digits.groups()
        suf_str = suf.upper() if suf else ""
        return f"{f}{d1}{d2}{suf_str}"

    return None


def parse_destination(
    text: str,
    valid_rooms: Optional[Set[str]] = None,
    graph=None,
) -> Tuple[Optional[str], float, str]:
    if not text or not text.strip():
        return None, 0.0, "I didn't hear a destination. Please speak the room number or location name."

    if graph is None and valid_rooms is None:
        graph = load_graph()
        valid_rooms = get_all_room_ids(graph)
    elif valid_rooms is None and graph is not None:
        valid_rooms = get_all_room_ids(graph)

    norm_text = normalize_transcript(text)

    m_direct = ROOM_PATTERN.search(norm_text)
    if m_direct:
        candidate = m_direct.group(1).upper()
        if candidate in valid_rooms:
            return candidate, 1.0, f"Destination set to room {candidate}."

    spoken_candidate = parse_spoken_number(norm_text)
    if spoken_candidate and spoken_candidate.upper() in valid_rooms:
        cand = spoken_candidate.upper()
        return cand, 0.95, f"Destination set to room {cand}."

    if graph is not None:
        alias_node = find_node_by_alias(graph, norm_text)
        if alias_node and alias_node in valid_rooms:
            label = graph.nodes[alias_node].get("label", alias_node)
            return alias_node, 0.9, f"Destination set to {label}."

        for node_id in valid_rooms:
            node_data = graph.nodes[node_id]
            for alias in node_data.get("aliases", []):
                if alias.lower() in norm_text:
                    label = node_data.get("label", node_id)
                    return node_id, 0.85, f"Destination set to {label}."

    return None, 0.0, f"I couldn't find '{text.strip()}' in the building map. Please repeat your destination clearly."
