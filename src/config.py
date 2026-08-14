import os
from pathlib import Path


class Config:
    CURRENT_DIR = Path(__file__).resolve().parent
    PROJECT_ROOT = CURRENT_DIR.parent if CURRENT_DIR.name == "src" else CURRENT_DIR

    DATA_DIR = PROJECT_ROOT / "data"
    MODELS_DIR = PROJECT_ROOT / "models"
    OUTPUTS_DIR = PROJECT_ROOT / "outputs"

    DATASET_DIR = (DATA_DIR / "dataset") if (DATA_DIR / "dataset").exists() else (PROJECT_ROOT / "dataset")
    TRAIN_DIR = DATASET_DIR / "train"
    VAL_DIR = DATASET_DIR / "val"
    TEST_DIR = DATASET_DIR / "test"
    AUGMENTED_DIR = DATASET_DIR / "augmented"

    EMBEDDINGS_DIR = (DATA_DIR / "embeddings") if (DATA_DIR / "embeddings").exists() else (PROJECT_ROOT / "embeddings")
    CLIP_INDEX_PATH = EMBEDDINGS_DIR / "clip_index.npz"

    GRAPH_JSON_PATH = (DATA_DIR / "building_graph.json") if (DATA_DIR / "building_graph.json").exists() else (PROJECT_ROOT / "building_graph.json")
    LABEL_MAP_PATH = (DATA_DIR / "label_map.json") if (DATA_DIR / "label_map.json").exists() else (PROJECT_ROOT / "label_map.json")

    LOGS_DIR = OUTPUTS_DIR / "logs"
    REPORTS_DIR = OUTPUTS_DIR / "reports"
    AUDIO_CACHE_DIR = OUTPUTS_DIR / "audio_cache"

    STATIC_DIR = PROJECT_ROOT / "static"
    OCR_MODELS_DIR = (MODELS_DIR / "ocr_models") if (MODELS_DIR / "ocr_models").exists() else (PROJECT_ROOT / "ocr_models")

    OCR_CONFIDENCE_THRESHOLD = 70
    TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    CLIP_MODEL_NAME = "ViT-B-32"
    CLIP_PRETRAINED = "openai"
    CLIP_SIMILARITY_THRESHOLD = 0.62
    CLIP_AMBIGUITY_GAP = 0.015

    OLLAMA_BASE_URL = "http://localhost:11434"
    OLLAMA_MODEL = "llama3.2:3b"
    LLM_TEMPERATURE = 0.3
    LLM_MAX_TOKENS = 100
    LLM_MAX_RETRIES = 3

    WHISPER_MODEL_SIZE = "base"
    WHISPER_DEVICE = "cpu"
    WHISPER_COMPUTE_TYPE = "int8"

    PIPER_EXE_PATH = PROJECT_ROOT.parent / "waylens-piper" / "piper" / "piper.exe"
    PIPER_MODEL_PATH = PROJECT_ROOT.parent / "waylens-piper" / "models" / "en_US-lessac-medium.onnx"

    SD_API_URL = "http://127.0.0.1:7861"
    SD_DENOISING_STRENGTH_MIN = 0.3
    SD_DENOISING_STRENGTH_MAX = 0.5
    SD_STEPS = 15
    SD_WIDTH = 512
    SD_HEIGHT = 512
    SD_VARIATIONS_PER_IMAGE = 4

    SERVER_HOST = "0.0.0.0"
    SERVER_PORT = 8000

    SCAN_INTERVAL_SECONDS = 5
    MAX_INSTRUCTION_REPEAT = 2

    @classmethod
    def ensure_dirs(cls):
        for d in [
            cls.EMBEDDINGS_DIR,
            cls.AUGMENTED_DIR,
            cls.LOGS_DIR,
            cls.REPORTS_DIR,
            cls.STATIC_DIR,
            cls.AUDIO_CACHE_DIR,
            cls.MODELS_DIR,
            cls.DATA_DIR,
        ]:
            d.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_local_ip(cls) -> str:
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
