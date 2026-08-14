import base64
import io
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

from config import Config
from navigation_session import NavigationOrchestrator
from speech_io import transcribe_audio, synthesize_speech

app = FastAPI(
    title="WayLens: Indoor Navigation API",
    description="Indoor Navigation Assistant for Visually Impaired Users",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if Config.STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(Config.STATIC_DIR)), name="static")

orchestrator = NavigationOrchestrator()
active_session = None


@app.get("/")
def serve_index():
    index_path = Config.STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse(content={"status": "running", "message": "WayLens API is active"})


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "graph_nodes": len(orchestrator.graph.nodes) if orchestrator.graph else 0,
        "active_session": active_session is not None,
    }


@app.post("/api/start-session")
async def start_session(
    destination_text: Optional[str] = Form(None),
    audio_file: Optional[UploadFile] = File(None),
):
    global active_session

    dest_input = ""
    if audio_file:
        audio_bytes = await audio_file.read()
        dest_input = transcribe_audio(audio_bytes)
        if not dest_input:
            error_msg = "Could not transcribe spoken destination. Please try speaking again."
            tts_audio = synthesize_speech(error_msg)
            return JSONResponse(
                content={
                    "status": "error",
                    "message": error_msg,
                    "audio_b64": base64.b64encode(tts_audio).decode("utf-8"),
                },
                status_code=400,
            )
    elif destination_text:
        dest_input = destination_text.strip()
    else:
        raise HTTPException(status_code=400, detail="Provide either destination_text or audio_file.")

    session, response = orchestrator.start_session(dest_input)

    if response.get("status") == "active":
        active_session = session

    tts_audio = synthesize_speech(response["message"])
    response["audio_b64"] = base64.b64encode(tts_audio).decode("utf-8")

    return JSONResponse(content=response)


@app.post("/api/navigate")
async def navigate_step(
    image_file: UploadFile = File(...),
):
    global active_session

    image_bytes = await image_file.read()
    try:
        pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image format: {e}")

    if not active_session:
        from localization import localize
        from building_graph import get_node_info
        curr_node, loc_conf, loc_method, loc_msg = localize(pil_image, valid_rooms=orchestrator.valid_rooms, graph=orchestrator.graph)
        
        if curr_node != "rescan":
            node_info = get_node_info(orchestrator.graph, curr_node) or {}
            label = node_info.get("label", curr_node)
            floor_name = node_info.get("floor_name", "")
            info_msg = f"You are at {label} on {floor_name}. Please enter your destination to begin navigation."
            tts_audio = synthesize_speech(info_msg)
            return JSONResponse(
                content={
                    "status": "located_standby",
                    "current_node": curr_node,
                    "current_label": label,
                    "floor_name": floor_name,
                    "instruction": info_msg,
                    "audio_b64": base64.b64encode(tts_audio).decode("utf-8"),
                }
            )
        else:
            error_msg = "Could not detect room number. Please point your camera at a room sign or door number."
            tts_audio = synthesize_speech(error_msg)
            return JSONResponse(
                content={
                    "status": "rescan_needed",
                    "instruction": error_msg,
                    "audio_b64": base64.b64encode(tts_audio).decode("utf-8"),
                }
            )

    result = orchestrator.process_scan(active_session, pil_image)

    instruction_text = result.get("instruction", "")
    tts_audio = synthesize_speech(instruction_text)
    result["audio_b64"] = base64.b64encode(tts_audio).decode("utf-8")

    return JSONResponse(content=result)


@app.post("/api/generate-visual")
def generate_visual_endpoint(
    node_id: Optional[str] = Form(None),
    prompt: Optional[str] = Form(None),
):
    from sd_augmentation import generate_landmark_visual
    from building_graph import get_node_info

    visual_prompt = prompt or ""
    if node_id:
        info = get_node_info(orchestrator.graph, node_id) or {}
        label = info.get("label", node_id)
        floor = info.get("floor_name", "")
        visual_prompt = f"doorway and signage for {label} on {floor} of university department corridor"

    if not visual_prompt:
        visual_prompt = "university campus classroom corridor entrance"

    img = generate_landmark_visual(visual_prompt)
    if img:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
        return JSONResponse(
            content={
                "status": "success",
                "prompt": visual_prompt,
                "image_b64": b64_str,
            }
        )
    return JSONResponse(
        content={
            "status": "offline",
            "message": "Local Stable Diffusion model is offline or busy.",
        }
    )


@app.post("/api/end-session")
def end_session():
    global active_session
    active_session = None
    msg = "Navigation session ended."
    tts_audio = synthesize_speech(msg)
    return JSONResponse(
        content={
            "status": "ended",
            "message": msg,
            "audio_b64": base64.b64encode(tts_audio).decode("utf-8"),
        }
    )
