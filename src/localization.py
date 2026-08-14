import re
from pathlib import Path
from typing import Tuple, Optional, Union, Set, List

from PIL import Image

from config import Config
from building_graph import load_graph, get_all_room_ids, find_node_by_alias
from embedding_index import CLIPEmbeddingIndex

ROOM_REGEX = re.compile(r"([567]\d{2}[A-Za-z]?)", re.IGNORECASE)

DEPT_KEYWORDS = {
    "cse": "CSE",
    "computer science": "CSE",
    "dept of cs": "CSE",
    "department of computer science": "CSE",
    "ece": "ECE",
    "electronics": "ECE",
    "eee": "EEE",
    "electrical": "EEE",
    "mech": "MECH",
    "mechanical": "MECH",
    "civil": "CIVIL",
    "mathematics": "MATH",
    "maths": "MATH",
    "dept of math": "MATH",
    "physics": "PHYSICS",
    "physics lab": "Physics_Lab",
    "chemistry": "CHEMISTRY",
    "commerce": "Dept_of_Commerce",
    "dept of commerce": "Dept_of_Commerce",
    "seminar": "Seminar_Hall",
    "seminar hall": "Seminar_Hall",
    "assembly": "Assembly_Hall",
    "assembly hall": "Assembly_Hall",
    "prayer": "Prayer_Hall",
    "prayer hall": "Prayer_Hall",
    "education": "School_of_Education",
    "psychology": "Dept_of_Psychology",
    "quantum": "Quantum_Computing",
    "energy science": "Energy_Science_Lab",
    "panel room": "Panel_Room",
    "xerox": "Xerox_5",
    "library": "Library",
    "canteen": "Canteen",
    "principal": "Principal",
    "office": "Office",
}


def normalize_ocr_text(raw_text: str) -> str:
    if not raw_text:
        return ""
    text = raw_text.strip()
    text = re.sub(r"([567])\s+([0-9oO])\s+([0-9a-zA-Z])", r"\1\2\3", text)
    text = re.sub(r"([567]\d)\s+([0-9a-zA-Z])", r"\1\2", text)
    text = re.sub(r"\b([567])[oO](\d)", r"\g<1>0\2", text)
    text = re.sub(r"([567]\d)[oO]\b", r"\g<1>0", text)
    text = re.sub(r"\b([567])[oO][oO]\b", r"\g<1>00", text)
    text = re.sub(r"([567]\d)[lI|]", r"\g<1>1", text)
    text = re.sub(r"([567])[lI|](\d)", r"\g<1>1\2", text)
    text = re.sub(r"\b[sS](0\d[A-Za-z]?)\b", r"5\1", text)
    return text


_easyocr_reader = None


def get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None:
        import easyocr
        _easyocr_reader = easyocr.Reader(
            ["en"],
            gpu=False,
            verbose=False,
            model_storage_directory=str(Config.OCR_MODELS_DIR),
        )
    return _easyocr_reader


_clip_index_instance: Optional[CLIPEmbeddingIndex] = None


def get_clip_index() -> CLIPEmbeddingIndex:
    global _clip_index_instance
    if _clip_index_instance is None:
        _clip_index_instance = CLIPEmbeddingIndex()
        if Config.CLIP_INDEX_PATH.exists():
            _clip_index_instance.load_index()
    return _clip_index_instance


def extract_text_from_image(img: Image.Image) -> List[dict]:
    import numpy as np

    max_dim = 1280
    w, h = img.size
    if max(w, h) > max_dim:
        scale = max_dim / float(max(w, h))
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

    reader = get_easyocr_reader()
    img_array = np.array(img.convert("RGB"))
    results = reader.readtext(img_array, detail=1)

    detections = []
    for bbox, text, conf in results:
        text = text.strip()
        if text:
            detections.append({
                "text": text,
                "confidence": float(conf),
                "bbox": bbox,
            })
    return detections


def parse_room_from_ocr(
    detections: List[dict],
    valid_rooms: Set[str],
    graph=None,
) -> Tuple[Optional[str], float, str, List[str]]:
    all_texts = [d["text"] for d in detections]
    combined_raw = " ".join(all_texts)
    combined_norm = normalize_ocr_text(combined_raw).lower()

    room_candidates = []
    dept_candidates = []

    for det in detections:
        raw_text = det["text"].strip()
        norm_text = normalize_ocr_text(raw_text)
        conf = det["confidence"]

        for t in (norm_text, raw_text):
            matches = ROOM_REGEX.findall(t)
            for m in matches:
                room_id = m.upper()
                if room_id in valid_rooms:
                    room_candidates.append((room_id, max(conf, 0.75), f"OCR room number '{room_id}' (conf={conf:.2f})"))

    matches_combined = ROOM_REGEX.findall(combined_norm)
    for m in matches_combined:
        room_id = m.upper()
        if room_id in valid_rooms:
            room_candidates.append((room_id, 0.80, f"OCR combined room number '{room_id}'"))

    if graph is not None:
        for keyword, mapped_node in DEPT_KEYWORDS.items():
            if keyword in combined_norm and mapped_node:
                alias_node = find_node_by_alias(graph, keyword) or mapped_node
                if alias_node and alias_node in valid_rooms:
                    dept_candidates.append((alias_node, 0.85, f"OCR department '{keyword}' -> {alias_node}"))

        alias_node = find_node_by_alias(graph, combined_norm)
        if alias_node and alias_node in valid_rooms:
            dept_candidates.append((alias_node, 0.85, f"OCR alias match -> {alias_node}"))

    if room_candidates:
        best = max(room_candidates, key=lambda x: x[1])
        return best[0], best[1], best[2], all_texts

    if dept_candidates:
        best = max(dept_candidates, key=lambda x: x[1])
        return best[0], best[1], best[2], all_texts

    return None, 0.0, "OCR: no room or department detected", all_texts


def run_ocr_localization(
    img: Image.Image,
    valid_rooms: Set[str],
    graph=None,
) -> Tuple[Optional[str], float, str, List[str]]:
    try:
        detections = extract_text_from_image(img)
        if not detections:
            return None, 0.0, "OCR: no text detected in image", []
        return parse_room_from_ocr(detections, valid_rooms, graph)
    except Exception as e:
        return None, 0.0, f"OCR error: {e}", []


def run_clip_localization(
    img: Image.Image,
    valid_rooms: Set[str],
) -> Tuple[Optional[str], float, str]:
    clip_idx = get_clip_index()
    if clip_idx.embeddings is None or len(clip_idx.embeddings) == 0:
        return None, 0.0, "CLIP index empty or unavailable"

    try:
        results = clip_idx.query(img, top_k=3)
        if not results:
            return None, 0.0, "No CLIP matches"

        top1_node, top1_score = results[0]
        top1_node = str(top1_node)

        if top1_node not in valid_rooms:
            return None, 0.0, f"Top match {top1_node} not in valid rooms"

        similarity_threshold = 0.62
        if top1_score < similarity_threshold:
            return None, top1_score, f"CLIP score {top1_score:.3f} below threshold {similarity_threshold}"

        if len(results) > 1:
            top2_node, top2_score = results[1]
            gap = top1_score - top2_score
            if gap < 0.015 and top1_node != str(top2_node):
                return None, top1_score, f"CLIP top-1 ({top1_node}:{top1_score:.3f}) ambiguous vs top-2 ({top2_node}:{top2_score:.3f})"

        return top1_node, float(top1_score), f"CLIP visual match ({top1_node}, score={top1_score:.3f})"

    except Exception as e:
        return None, 0.0, f"CLIP query error: {e}"


def localize(
    image_input: Union[Path, str, Image.Image],
    valid_rooms: Optional[Set[str]] = None,
    graph=None,
) -> Tuple[str, float, str, str]:
    if isinstance(image_input, (str, Path)):
        img = Image.open(image_input).convert("RGB")
    else:
        img = image_input.convert("RGB")

    if graph is None and valid_rooms is None:
        graph = load_graph()
        valid_rooms = get_all_room_ids(graph)
    elif valid_rooms is None and graph is not None:
        valid_rooms = get_all_room_ids(graph)

    ocr_node, ocr_conf, ocr_detail, ocr_texts = run_ocr_localization(img, valid_rooms, graph=graph)
    clip_node, clip_conf, clip_detail = run_clip_localization(img, valid_rooms)

    if ocr_node and clip_node and ocr_node == clip_node:
        fused_conf = min(1.0, (ocr_conf * 0.6 + clip_conf * 0.4) + 0.15)
        ocr_text_str = ", ".join(ocr_texts[:5]) if ocr_texts else ""
        return (
            ocr_node,
            fused_conf,
            "ocr+clip",
            f"Located at room {ocr_node}. Sign text: [{ocr_text_str}]. Visual match confirmed.",
        )

    if ocr_node and ocr_conf >= 0.20:
        ocr_text_str = ", ".join(ocr_texts[:5]) if ocr_texts else ""
        return (
            ocr_node,
            ocr_conf,
            "ocr",
            f"Located at room {ocr_node} via sign text: [{ocr_text_str}].",
        )

    if clip_node and clip_conf >= 0.62:
        return (
            clip_node,
            clip_conf,
            "clip",
            f"Located near room {clip_node} via visual matching.",
        )

    return (
        "rescan",
        0.0,
        "none",
        "Could not detect room number. Please point your camera directly at the room sign or door number and scan again.",
    )
