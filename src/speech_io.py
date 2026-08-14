import io
import subprocess
import wave
import struct
from pathlib import Path
from typing import Union

from config import Config

_whisper_model_instance = None


def get_whisper_model():
    global _whisper_model_instance
    if _whisper_model_instance is None:
        try:
            from faster_whisper import WhisperModel
            _whisper_model_instance = WhisperModel(
                Config.WHISPER_MODEL_SIZE,
                device=Config.WHISPER_DEVICE,
                compute_type=Config.WHISPER_COMPUTE_TYPE,
            )
        except Exception:
            _whisper_model_instance = None
    return _whisper_model_instance


def transcribe_audio(audio_input: Union[str, Path, bytes]) -> str:
    model = get_whisper_model()
    if model is None:
        return ""

    temp_path = None
    if isinstance(audio_input, bytes):
        Config.AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        temp_path = Config.AUDIO_CACHE_DIR / "temp_input.wav"
        with open(temp_path, "wb") as f:
            f.write(audio_input)
        file_to_process = str(temp_path)
    else:
        file_to_process = str(audio_input)

    try:
        segments, _ = model.transcribe(
            file_to_process,
            beam_size=5,
            language="en",
            task="transcribe",
        )
        return " ".join([seg.text.strip() for seg in segments]).strip()
    except Exception:
        return ""
    finally:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass


def generate_fallback_beeps_wav(duration_sec: float = 0.5, freq: float = 440.0) -> bytes:
    sample_rate = 16000
    num_samples = int(sample_rate * duration_sec)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)

        import math
        samples = [int(16000 * math.sin(2 * math.pi * freq * (i / sample_rate))) for i in range(num_samples)]
        wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))

    return buf.getvalue()


def synthesize_speech(text: str) -> bytes:
    if not text or not text.strip():
        return generate_fallback_beeps_wav()

    Config.AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out_wav_path = Config.AUDIO_CACHE_DIR / "temp_output.wav"

    piper_exe = Config.PIPER_EXE_PATH
    piper_model = Config.PIPER_MODEL_PATH
    if piper_exe.exists() and piper_model.exists():
        try:
            cmd = [
                str(piper_exe),
                "--model", str(piper_model),
                "--output_file", str(out_wav_path),
            ]
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            proc.communicate(input=text, timeout=10)
            if out_wav_path.exists():
                with open(out_wav_path, "rb") as f:
                    wav_bytes = f.read()
                out_wav_path.unlink(missing_ok=True)
                return wav_bytes
        except Exception:
            pass

    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 165)
        engine.save_to_file(text, str(out_wav_path))
        engine.runAndWait()
        if out_wav_path.exists():
            with open(out_wav_path, "rb") as f:
                wav_bytes = f.read()
            out_wav_path.unlink(missing_ok=True)
            return wav_bytes
    except Exception:
        pass

    return generate_fallback_beeps_wav()
