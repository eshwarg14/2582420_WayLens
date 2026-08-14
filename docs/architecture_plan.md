# WayLens — System Architecture Document

> **Project**: WayLens — Generative AI Indoor Navigation Assistant  
> **Type**: On-Device Multimodal AI System (Zero Cloud Dependencies)  
> **Stack**: Python 3.10+ · FastAPI · PyTorch CPU · NetworkX · OpenCLIP · EasyOCR · Whisper · Ollama · Stable Diffusion  
> **Generated**: August 2026  

---

## 1. Executive Summary

WayLens is a **fully on-device indoor navigation assistant** for university campus buildings, designed for visually impaired students, faculty, and visitors. It transforms a smartphone into a spatial guidance system by fusing:

- **Computer Vision** (OCR + CLIP embeddings) for real-time location recognition  
- **Graph-Based Routing** (Dijkstra over a 116-node building topology) for deterministic pathfinding  
- **Local LLM** (Llama 3.2 3B via Ollama) for natural language instruction generation  
- **Local Image Generation** (Stable Diffusion 1.5 via AUTOMATIC1111) for visual augmentation  
- **Speech I/O** (Whisper STT + Piper/pyttsx3 TTS) for voice-first interaction  

**Zero cloud APIs are used.** All inference runs on CPU (target: Intel Core i3, 12 GB RAM).

---

## 2. High-Level System Architecture

```mermaid
graph TB
    subgraph CLIENT["Client Layer (Browser)"]
        UI["index.html<br/>Accessible Mobile SPA"]
        AppJS["app.js<br/>Client Controller"]
        FloorMap["floormap.js<br/>HD Canvas Map Engine"]
        Camera["Camera / Mic<br/>MediaStream API"]
        Speech["Web Speech API<br/>SpeechSynthesis"]
    end

    subgraph SERVER["Server Layer (FastAPI)"]
        API["server.py<br/>REST API Gateway"]
        Session["navigation_session.py<br/>Session Orchestrator"]
    end

    subgraph PERCEPTION["Perception Layer"]
        OCR["localization.py<br/>EasyOCR Engine"]
        CLIP["embedding_index.py<br/>OpenCLIP ViT-B-32"]
        Fusion["localization.py<br/>OCR + CLIP Fusion"]
    end

    subgraph REASONING["Reasoning Layer"]
        Intent["intent_parser.py<br/>Destination Parser"]
        Router["routing.py<br/>Dijkstra Router"]
        Tracker["state_tracker.py<br/>Direction Tracker"]
        LLM["llm_instructor.py<br/>Llama 3.2 3B"]
    end

    subgraph GENERATION["Generation Layer"]
        SD["sd_augmentation.py<br/>Stable Diffusion 1.5"]
        TTS["speech_io.py<br/>Piper TTS / pyttsx3"]
        STT["speech_io.py<br/>Whisper STT"]
    end

    subgraph DATA["Data Layer"]
        Graph["building_graph.py<br/>116-Node DiGraph"]
        GraphJSON["building_graph.json<br/>Topology Store"]
        Embeddings["clip_index.npz<br/>512-D Vector Index"]
        Dataset["dataset/<br/>Room Photographs"]
        LabelMap["label_map.json<br/>Node ↔ Image Map"]
    end

    subgraph INFRA["Infrastructure"]
        Config["config.py<br/>Central Configuration"]
        SSL["app.py<br/>SSL Cert Generator"]
        Eval["evaluation.py<br/>Benchmark Suite"]
        Report["evaluation_report.py<br/>Report Generator"]
    end

    Camera -->|"Video Frames"| AppJS
    AppJS -->|"JPEG Blob"| API
    AppJS -->|"Form Data"| API
    Speech -->|"Audio Output"| UI
    AppJS -->|"Node Updates"| FloorMap

    API -->|"POST /api/start-session"| Session
    API -->|"POST /api/navigate"| Session
    API -->|"POST /api/generate-visual"| SD

    Session --> Intent
    Session --> Fusion
    Session --> Router
    Session --> Tracker
    Session --> LLM

    Fusion --> OCR
    Fusion --> CLIP

    CLIP --> Embeddings
    Router --> Graph
    Tracker --> Graph
    Intent --> Graph
    Graph --> GraphJSON

    API --> STT
    API --> TTS

    Config -.->|"Paths & Settings"| API
    Config -.->|"Paths & Settings"| Graph
    Config -.->|"Paths & Settings"| CLIP
    Config -.->|"Paths & Settings"| LLM
    Config -.->|"Paths & Settings"| SD
```

---

## 3. Layer Architecture (Detailed Breakdown)

### 3.1 Client Layer — `static/`

The client is a **single-page accessible mobile web application** served as static files.

| File | Size | Role |
|------|------|------|
| [`index.html`](file:///c:/Users/Asus/Downloads/Waylens/static/index.html) | 10.7 KB | Semantic HTML5 shell with ARIA accessibility |
| [`style.css`](file:///c:/Users/Asus/Downloads/Waylens/static/style.css) | 13.2 KB | Dark-theme design system with CSS custom properties |
| [`app.js`](file:///c:/Users/Asus/Downloads/Waylens/static/app.js) | 22.0 KB | Event controller, API client, camera/speech manager |
| [`floormap.js`](file:///c:/Users/Asus/Downloads/Waylens/static/floormap.js) | 28.8 KB | High-DPI Canvas 2D floor map renderer |

#### Client Architecture Diagram

```mermaid
graph LR
    subgraph "app.js — Client Controller"
        Init["init()"] --> Health["checkHealth()<br/>/api/health"]
        
        subgraph "Input Handlers"
            TextInput["handleSetDestination()"]
            VoiceInput["SpeechRecognition /<br/>fallbackToWhisperRecording()"]
        end

        subgraph "Navigation Loop"
            Scan["scanSurroundings()<br/>captureFrame() → JPEG"]
            AutoScan["toggleAutoScan()<br/>5s interval timer"]
            Send["sendImageFrame()<br/>POST /api/navigate"]
            Update["updateMapAndProgress()"]
        end

        subgraph "Output"
            Speak["speakInstruction()<br/>Web Speech API / Piper WAV"]
            MapUpdate["FloorMap.setCurrentNode()<br/>FloorMap.setRoute()"]
        end
    end

    TextInput -->|"POST /api/start-session"| API["Backend"]
    VoiceInput -->|"audio_file"| API
    Scan --> Send --> API
    API -->|"JSON Response"| Update
    Update --> Speak
    Update --> MapUpdate
```

#### FloorMap Canvas Engine — `floormap.js`

The `FloorMapRenderer` class renders an architectural blueprint-style map at 60 FPS using `requestAnimationFrame`:

| Render Pass | Description |
|---|---|
| `drawBackground()` | Deep slate gradient (`#090d16` → `#0e1422`) + 30px blueprint grid |
| `drawGarden()` | Central courtyard with lawn striping + tree foliage markers |
| `drawCorridors()` | Dual-pass: 14px base track + 4px inner centerline |
| `drawRoute()` | Neon sky-blue marching dashes (`dashOffset -= 0.8` per frame) |
| `drawNodes()` | Type-coded: 🔵 Room · 🟡 Lift (🛗) · 🟠 Steps (🪜) · 🟢 Gate · 🟣 Landmark |
| `drawDestinationPin()` | Bouncing diamond pin + ground ripple ellipse + `🎯` label |
| `drawUserPointer()` | Smooth easeOutCubic motion + dual expanding radar pulses + `📍 YOU ARE HERE` |
| `drawHUD()` | Floor watermark + N/S compass rose |

Hardcoded `NODE_COORDS` dictionary (116+ entries) and `EDGES` array (250+ pairs) define the topology directly in the client for instant rendering without server round-trips.

#### Design System — `style.css`

| Token Category | Values |
|---|---|
| **Backgrounds** | `--bg: #0a0f1a` · `--surface: #111827` · `--surface-2: #1a2236` |
| **Accent** | `--accent: #38bdf8` (Electric Sky Blue) |
| **Semantic** | `--green: #059669` · `--blue: #2563eb` · `--red: #dc2626` · `--orange: #d97706` · `--purple: #7c3aed` |
| **Typography** | Inter (400–900) · `--font-size-xs` to `--font-size-xxl` (12–28px) |
| **Spacing** | 4px → 48px scale (`--space-xs` to `--space-xxl`) |
| **Radii** | `--radius: 14px` · `--radius-sm: 10px` |
| **Responsive** | `@media (max-width: 380px)` compact mode |
| **A11y** | `@media (prefers-reduced-motion: reduce)` disables animations |

---

### 3.2 Server Layer — API Gateway

#### [`server.py`](file:///c:/Users/Asus/Downloads/Waylens/src/server.py) — FastAPI REST API

```mermaid
graph LR
    subgraph "REST Endpoints"
        GET1["GET /<br/>Serves index.html"]
        GET2["GET /api/health<br/>System status"]
        POST1["POST /api/start-session<br/>Initialize navigation"]
        POST2["POST /api/navigate<br/>Process camera scan"]
        POST3["POST /api/generate-visual<br/>SD landmark preview"]
        POST4["POST /api/end-session<br/>Terminate session"]
    end

    POST1 -->|"destination_text OR audio_file"| Pipeline1["speech_io.transcribe_audio()<br/>→ intent_parser.parse_destination()<br/>→ orchestrator.start_session()"]
    POST2 -->|"image_file (JPEG)"| Pipeline2["orchestrator.process_scan()<br/>→ localize() → route → LLM"]
    POST3 -->|"node_id OR prompt"| Pipeline3["sd_augmentation.generate_landmark_visual()"]
```

| Endpoint | Method | Input | Output | Latency |
|----------|--------|-------|--------|---------|
| `/` | GET | — | `index.html` | < 5ms |
| `/api/health` | GET | — | `{status, node_count, session}` | < 10ms |
| `/api/start-session` | POST | `destination_text` or `audio_file` | `{session_id, route, welcome_msg, audio_b64}` | 1–3s |
| `/api/navigate` | POST | `image_file` (JPEG/PNG) | `{node_id, instruction, progress, route, audio_b64}` | 0.5–2s |
| `/api/generate-visual` | POST | `node_id` or `prompt` | `{image_b64}` | 10–60s |
| `/api/end-session` | POST | — | `{status, audio_b64}` | < 500ms |

**Global State**: Single `active_session` variable (no multi-user concurrency). CORS enabled (`allow_origins=["*"]`).

#### [`navigation_session.py`](file:///c:/Users/Asus/Downloads/Waylens/src/navigation_session.py) — Session Orchestrator

The `NavigationOrchestrator` class is the **central coordination engine** that binds all subsystems:

```mermaid
sequenceDiagram
    participant C as Client
    participant S as server.py
    participant O as NavigationOrchestrator
    participant L as localization.py
    participant ST as state_tracker.py
    participant R as routing.py
    participant LLM as llm_instructor.py

    C->>S: POST /api/start-session (destination)
    S->>O: start_session("Room 607")
    O->>O: parse_destination() → node_id "607"
    O->>O: tracker.create_session("607")
    O-->>S: {session, route, welcome}
    S-->>C: JSON + TTS audio

    loop Every Camera Scan
        C->>S: POST /api/navigate (JPEG)
        S->>O: process_scan(session, image)
        O->>L: localize(image)
        L-->>O: (node_id="CG3", conf=0.87, method="ocr+clip")
        O->>ST: update_position(session, "CG3", route)
        ST-->>O: (session, movement_state="forward")
        O->>R: get_instruction_context("CG3", "607", heading="east")
        R-->>O: {direction, next_node, remaining_steps, ...}
        O->>LLM: generate_instruction(context)
        LLM-->>O: "Continue east past Room 505, then turn right."
        O-->>S: {instruction, progress, state}
        S-->>C: JSON + TTS audio
    end
```

**Orchestrator Methods:**

| Method | Purpose |
|--------|---------|
| `start_session(dest_text)` | Parse destination → validate against graph → create session → compute initial route |
| `process_scan(session, image)` | Localize → track state → compute route context → generate LLM instruction → deduplicate speech |

---

### 3.3 Perception Layer — Computer Vision

#### [`localization.py`](file:///c:/Users/Asus/Downloads/Waylens/src/localization.py) — Multimodal Fusion Engine

The core localization pipeline fuses **two independent perception channels** and applies confidence-gated fusion:

```mermaid
graph TB
    Input["Camera Frame<br/>(PIL Image)"]

    subgraph "Channel A: OCR"
        OCR1["extract_text_from_image()<br/>EasyOCR (en, CPU)"]
        OCR2["normalize_ocr_text()<br/>Fix: 5 0 1→501, O→0, l→1"]
        OCR3["parse_room_from_ocr()<br/>ROOM_REGEX + DEPT_KEYWORDS + alias match"]
    end

    subgraph "Channel B: CLIP"
        CLIP1["CLIPEmbeddingIndex.query()<br/>ViT-B-32 encode → 512-D vector"]
        CLIP2["Cosine Similarity<br/>vs. precomputed clip_index.npz"]
        CLIP3["Threshold Gate<br/>similarity ≥ 0.62, gap ≥ 0.015"]
    end

    subgraph "Fusion Logic"
        F1{"OCR & CLIP<br/>agree?"}
        F2{"OCR conf<br/>≥ 0.20?"}
        F3{"CLIP sim<br/>≥ 0.62?"}
        R1["🟢 ocr+clip<br/>conf = ocr×0.6 + clip×0.4 + 0.15"]
        R2["🔵 ocr<br/>OCR confidence"]
        R3["🟡 clip<br/>CLIP similarity"]
        R4["🔴 rescan<br/>conf = 0.0"]
    end

    Input --> OCR1 --> OCR2 --> OCR3
    Input --> CLIP1 --> CLIP2 --> CLIP3

    OCR3 --> F1
    CLIP3 --> F1
    F1 -->|"Yes"| R1
    F1 -->|"No"| F2
    F2 -->|"Yes"| R2
    F2 -->|"No"| F3
    F3 -->|"Yes"| R3
    F3 -->|"No"| R4
```

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `OCR_CONFIDENCE_THRESHOLD` | 0.20 | Minimum OCR confidence to accept |
| `CLIP_SIMILARITY_THRESHOLD` | 0.62 | Minimum cosine similarity to accept |
| `CLIP_AMBIGUITY_GAP` | 0.015 | Minimum margin between top-1 and top-2 CLIP results |
| `FUSION_AGREEMENT_BONUS` | 0.15 | Confidence boost when OCR and CLIP agree |
| `Image downscale` | max 1280px | Performance optimization for EasyOCR |

**OCR Error Correction** (`normalize_ocr_text`):
| Raw OCR | Corrected | Rule |
|---------|-----------|------|
| `5 0 1` | `501` | Collapse spaced digits |
| `5O1` | `501` | `O`/`o` → `0` |
| `5l1` | `511` | `l`/`I`/`\|` → `1` |
| `S01` | `501` | `S0x` → `50x` |

**Department Keywords** (`DEPT_KEYWORDS`): Maps ~20 academic keywords (`"cse"`, `"ece"`, `"physics lab"`, `"commerce"`, `"seminar hall"`, `"prayer hall"`, `"xerox"`, `"canteen"`, etc.) directly to graph node IDs.

#### [`embedding_index.py`](file:///c:/Users/Asus/Downloads/Waylens/src/embedding_index.py) — CLIP Vector Store

```mermaid
graph LR
    subgraph "Index Build (Offline)"
        Scan["Scan dataset/<br/>train + val + test + augmented"]
        Encode["model.encode_image()<br/>ViT-B-32 → 512-D float32"]
        Norm["L2 Normalize"]
        Save["Save clip_index.npz<br/>(embeddings, labels, paths)"]
    end

    subgraph "Query (Online)"
        Frame["Camera Frame"]
        QEnc["encode_image() → 512-D query"]
        Dot["np.dot(query, index.T)<br/>Cosine Similarity"]
        Agg["Aggregate max per label"]
        TopK["Return top-k (label, score)"]
    end

    Scan --> Encode --> Norm --> Save
    Frame --> QEnc --> Dot --> Agg --> TopK
```

| Attribute | Value |
|-----------|-------|
| Model | OpenCLIP ViT-B-32 (`openai` pretrained) |
| Embedding Dim | 512 float32 |
| Index Format | Compressed NumPy `.npz` |
| Query Latency | < 150ms (CPU) |
| Batch Size | 16 (during build) |

---

### 3.4 Reasoning Layer — Routing & State

#### [`building_graph.py`](file:///c:/Users/Asus/Downloads/Waylens/src/building_graph.py) — Spatial Knowledge Graph

The building topology is a **NetworkX DiGraph** with 116 nodes and 254 bidirectional edges across 3 floors.

```mermaid
graph TB
    subgraph "Floor 7 (2nd Floor) — 7xx"
        F7["~40 nodes<br/>Rooms 701-755<br/>+ C7 corridors<br/>+ Lift_7 + Steps_7"]
    end

    subgraph "Floor 6 (1st Floor) — 6xx"
        F6["~38 nodes<br/>Rooms 601-631<br/>+ C6 corridors<br/>+ Lift_6 + Steps_6"]
    end

    subgraph "Floor 5 (Ground Floor) — 5xx"
        F5["~38 nodes<br/>Rooms 501-525<br/>+ CG corridors<br/>+ Lift_5 + Steps_5<br/>+ Gates + Landmarks"]
    end

    F5 <-->|"Lifts (dist=2)<br/>Stairs (dist=3)"| F6
    F6 <-->|"Lifts (dist=2)<br/>Stairs (dist=3)"| F7
```

**Node Schema:**
```json
{
  "id": "501",
  "type": "room | landmark | lift | steps | gate | toilet",
  "floor": 5,
  "label": "Room 501",
  "aliases": ["501", "five oh one", "five zero one"],
  "corridor": "5_south",
  "x": 215, "y": 440
}
```

**Edge Schema:**
```json
{
  "from": "515",
  "to": "516",
  "direction": "north | south | east | west | up | down",
  "corridor_segment": "5_west",
  "distance": 1
}
```

**Key Functions:**

| Function | Purpose |
|----------|---------|
| `build_graph()` | Assembles complete DiGraph from hardcoded node/edge definitions |
| `save_graph(graph, path)` | Serializes to JSON (metadata + nodes + edges) |
| `load_graph(path)` | Deserializes JSON → DiGraph with fallback path search |
| `find_node_by_alias(graph, alias)` | Case-insensitive alias lookup across all nodes |
| `get_adjacent_nodes(graph, node_id)` | Returns outgoing neighbors with edge metadata |
| `validate_graph(graph)` | Integrity checks: connectivity, bidirectionality, cross-floor paths |

#### [`routing.py`](file:///c:/Users/Asus/Downloads/Waylens/src/routing.py) — Dijkstra Router

```mermaid
graph LR
    Start["Current Node<br/>(from localization)"]
    Dest["Destination Node<br/>(from intent parser)"]
    Dijkstra["nx.shortest_path()<br/>weight='distance'"]
    Steps["generate_route_steps()<br/>RouteStep[]"]
    Context["get_instruction_context()<br/>Next turn + landmark + floor change"]

    Start --> Dijkstra
    Dest --> Dijkstra
    Dijkstra --> Steps --> Context
```

**`RouteStep` Dataclass:**

| Field | Type | Example |
|-------|------|---------|
| `from_node` | str | `"CG3"` |
| `to_node` | str | `"505"` |
| `absolute_direction` | str | `"east"` |
| `relative_direction` | str | `"turn right"` |
| `is_floor_change` | bool | `false` |
| `nearby_landmark` | str | `"Library"` |

**Turn Mapping** (`TURN_MAPPING`):

| User Heading → | north | east | south | west |
|----------------|-------|------|-------|------|
| **Go north** | straight ahead | turn left | turn around | turn right |
| **Go east** | turn right | straight ahead | turn left | turn around |
| **Go south** | turn around | turn right | straight ahead | turn left |
| **Go west** | turn left | turn around | turn right | straight ahead |

#### [`state_tracker.py`](file:///c:/Users/Asus/Downloads/Waylens/src/state_tracker.py) — Directional State Tracker

The `DirectionalStateTracker` manages session state and detects 7 movement modes:

| Movement State | Trigger |
|----------------|---------|
| `starting` | First position fix (no prior history) |
| `forward` | Moving along expected route in correct direction |
| `backtracking` | Returning to position from 2 steps prior |
| `wrong_way` | Current position doesn't match expected next node |
| `reanchoring` | Reached a lift/stairs/gate transition point |
| `stationary` | Same position as last scan |
| `arrived` | Current position matches destination node |

**`NavigationSession` Dataclass:**

| Field | Purpose |
|-------|---------|
| `destination_node` | Target room/node ID |
| `current_node` | Last detected position |
| `last_node` | Previous position (for heading inference) |
| `inferred_direction` | Current cardinal heading (N/S/E/W) |
| `path_history` | Ordered list of visited nodes |
| `movement_state` | One of 7 states above |
| `last_instruction_given` | Deduplication: prevents repeating same instruction |

#### [`intent_parser.py`](file:///c:/Users/Asus/Downloads/Waylens/src/intent_parser.py) — Destination Parser

Multi-stage pipeline converting spoken/typed input to validated graph node IDs:

```mermaid
graph TB
    Input["User Input<br/>'Take me to five oh one'"]
    N["normalize_transcript()<br/>lowercase, strip"]
    P1{"Direct room<br/>pattern match?<br/>/[567]\d{2}[A-Za-z]?/"}
    P2["parse_spoken_number()<br/>WORD_TO_DIGIT lookup"]
    P3["find_node_by_alias()<br/>Graph alias search"]
    P4["Substring match<br/>across all aliases"]
    Out["(node_id='501', conf=0.95, msg='Navigating to Room 501')"]

    Input --> N --> P1
    P1 -->|"Yes"| Out
    P1 -->|"No"| P2
    P2 -->|"Match"| Out
    P2 -->|"No match"| P3
    P3 -->|"Match"| Out
    P3 -->|"No match"| P4
    P4 --> Out
```

**`WORD_TO_DIGIT` Lexicon:** Handles digit words, homophones (`"won"→"1"`, `"to"/"too"→"2"`, `"ate"→"8"`, `"tree"→"3"`), and compound numbers (`"twenty-four"→"24"`).

---

### 3.5 Generation Layer — LLM, TTS, and Diffusion

#### [`llm_instructor.py`](file:///c:/Users/Asus/Downloads/Waylens/src/llm_instructor.py) — Natural Language Instructions

```mermaid
graph TB
    Context["Navigation Context<br/>{current_label, direction, next_label, remaining_steps, landmark}"]
    Check{"Ollama<br/>available?"}
    Prompt["Build System + User Prompt<br/>LLM_PROMPT_TEMPLATE"]
    Call["POST /api/generate<br/>Llama 3.2 3B, temp=0.3, max_tokens=100"]
    Validate{"validate_llm_output()<br/>• ≥ 5 chars<br/>• No hallucinated rooms<br/>• Room numbers ∈ {current, next, dest}"}
    Retry{"Retries<br/>remaining?"}
    Fallback["Template fallback<br/>'Walk {direction} toward {next_label}.'"]
    Output["Instruction string"]

    Context --> Check
    Check -->|"Yes"| Prompt --> Call --> Validate
    Check -->|"No"| Fallback
    Validate -->|"Pass"| Output
    Validate -->|"Fail"| Retry
    Retry -->|"Yes"| Call
    Retry -->|"No"| Fallback
    Fallback --> Output
```

| Parameter | Value |
|-----------|-------|
| Model | `llama3.2:3b` via Ollama |
| Temperature | 0.3 |
| Max Tokens | 100 |
| Max Retries | 3 |
| Max Words | 18 (system prompt constraint) |
| Hallucination Check | Regex extracts 3-digit numbers from output, validates against context |

**Anti-Hallucination System:** The `validate_llm_output()` function uses regex to extract any room numbers from the LLM output and verifies each one exists in `{current_node, next_node, destination_node}`. If any unknown room is mentioned, the output is rejected and retried or replaced with a template fallback.

#### [`speech_io.py`](file:///c:/Users/Asus/Downloads/Waylens/src/speech_io.py) — Speech I/O Pipeline

```mermaid
graph TB
    subgraph "Speech-to-Text (STT)"
        AudioIn["Audio bytes / file"]
        Whisper["faster_whisper.WhisperModel<br/>model='base', device='cpu', compute='int8'"]
        Text["Transcribed text"]
    end

    subgraph "Text-to-Speech (TTS) — 3-Tier Fallback"
        TextIn["Instruction text"]
        T1["Tier 1: Piper TTS<br/>ONNX model (en_US-lessac-medium)"]
        T2["Tier 2: pyttsx3<br/>Offline engine (rate=165)"]
        T3["Tier 3: Fallback beep<br/>440 Hz sine WAV"]
        WAV["WAV audio bytes"]
    end

    AudioIn --> Whisper --> Text
    TextIn --> T1
    T1 -->|"Success"| WAV
    T1 -->|"Fail"| T2
    T2 -->|"Success"| WAV
    T2 -->|"Fail"| T3 --> WAV
```

#### [`sd_augmentation.py`](file:///c:/Users/Asus/Downloads/Waylens/src/sd_augmentation.py) — Stable Diffusion Integration

Dual purpose: **offline dataset augmentation** and **live landmark visualization**.

| Mode | API | Input | Output |
|------|-----|-------|--------|
| **Augmentation** | `/sdapi/v1/img2img` | Existing room photo + lighting prompt | Synthetic variations (3–4 per image) |
| **Landmark Preview** | `/sdapi/v1/txt2img` | Text description from node metadata | 512×512 corridor visualization |

| Parameter | Value |
|-----------|-------|
| Sampler | Euler a |
| CFG Scale | 7 |
| Steps | 15 |
| Dimensions | 512 × 512 |
| Denoising | 0.30–0.50 (randomized) |
| Negative Prompt | `"blurry, distorted, low quality, cartoon, text, watermark"` |

---

### 3.6 Data Layer

```mermaid
graph TB
    subgraph "data/"
        GraphJSON["building_graph.json<br/>116 nodes, 254 edges<br/>Topology + aliases + coordinates"]
        LabelMap["label_map.json<br/>node_id → [image_paths...]"]
        MAP["MAP.pdf<br/>Architectural floor plan blueprint"]
        subgraph "dataset/"
            Train["train/<br/>Room photographs"]
            Val["val/<br/>Validation split"]
            Test["test/<br/>Test split"]
        end
        subgraph "embeddings/"
            Index["clip_index.npz<br/>N×512 float32 vectors<br/>+ labels + paths"]
        end
    end

    subgraph "outputs/"
        Logs["logs/<br/>Session execution logs<br/>walk_test_report.json"]
        Reports["reports/<br/>augmentation_results.md"]
        Audio["audio_cache/<br/>TTS audio cache (hash-keyed)"]
        SSL["cert.pem + key.pem<br/>Self-signed SSL certs"]
    end

    subgraph "models/ & ocr_models/"
        CRAFT["craft_mlt_25k.pth<br/>83 MB — EasyOCR text detection"]
        English["english_g2.pth<br/>15 MB — EasyOCR text recognition"]
    end
```

---

### 3.7 Infrastructure & Configuration

#### [`config.py`](file:///c:/Users/Asus/Downloads/Waylens/src/config.py) — Central Configuration

Single static `Config` class — the **root dependency** imported by every module.

| Category | Key Settings |
|----------|-------------|
| **Paths** | `PROJECT_ROOT`, `DATA_DIR`, `DATASET_DIR`, `TRAIN_DIR`, `VAL_DIR`, `TEST_DIR`, `AUGMENTED_DIR`, `EMBEDDINGS_DIR`, `CLIP_INDEX_PATH`, `GRAPH_JSON_PATH`, `LABEL_MAP_PATH`, `LOGS_DIR`, `REPORTS_DIR`, `AUDIO_CACHE_DIR`, `STATIC_DIR`, `OCR_MODELS_DIR` |
| **CLIP** | `ViT-B-32`, pretrained `"openai"`, threshold `0.62`, ambiguity gap `0.015` |
| **OCR** | Confidence threshold `70`, Tesseract path (Windows) |
| **Ollama LLM** | `localhost:11434`, model `llama3.2:3b`, temp `0.3`, max tokens `100`, retries `3` |
| **Whisper** | Model `"base"`, device `"cpu"`, compute `"int8"` |
| **Piper TTS** | Binary path + ONNX model path (`en_US-lessac-medium`) |
| **Stable Diffusion** | `localhost:7861`, denoising `0.30–0.50`, 15 steps, 512×512 |
| **Server** | Host `0.0.0.0`, port `8000`, scan interval `5s` |

#### [`app.py`](file:///c:/Users/Asus/Downloads/Waylens/app.py) — Application Entry Point

Three execution modes via CLI:

| Command | Mode | Description |
|---------|------|-------------|
| `python app.py` | **Server** | Start HTTPS server on port 8000 with auto-generated SSL |
| `python app.py --eval` | **Evaluation** | Run benchmark suite across dataset |
| `python app.py --index` | **Indexing** | Rebuild CLIP embedding vector store |

**SSL Certificate Generation**: `ensure_ssl_certs()` generates self-signed X.509 certs with SAN entries for `localhost`, `127.0.0.1`, and the detected LAN IP — required for mobile browser camera/mic access.

---

## 4. Module Dependency Graph

```mermaid
graph TB
    config["config.py<br/>🔧 Configuration"]

    building_graph["building_graph.py<br/>🏗️ Knowledge Graph"]
    dataset_utils["dataset_utils.py<br/>📂 Dataset Utils"]
    embedding_index["embedding_index.py<br/>🔍 CLIP Index"]
    build_embeddings["build_embeddings.py<br/>🔨 Index Builder"]
    intent_parser["intent_parser.py<br/>🎯 Intent Parser"]
    localization["localization.py<br/>👁️ Multimodal Fusion"]
    state_tracker["state_tracker.py<br/>🧭 State Tracker"]
    routing["routing.py<br/>🛤️ Dijkstra Router"]
    llm_instructor["llm_instructor.py<br/>🤖 LLM Instructor"]
    sd_augmentation["sd_augmentation.py<br/>🎨 Stable Diffusion"]
    speech_io["speech_io.py<br/>🔊 Speech I/O"]
    navigation_session["navigation_session.py<br/>🎮 Orchestrator"]
    server["server.py<br/>🌐 API Gateway"]
    evaluation["evaluation.py<br/>📊 Evaluation"]
    evaluation_report["evaluation_report.py<br/>📝 Report Gen"]
    app["app.py<br/>🚀 Entry Point"]

    config --> building_graph
    config --> embedding_index
    config --> localization
    config --> llm_instructor
    config --> sd_augmentation
    config --> speech_io
    config --> evaluation
    config --> evaluation_report
    config --> dataset_utils

    building_graph --> intent_parser
    building_graph --> localization
    building_graph --> state_tracker
    building_graph --> routing
    building_graph --> dataset_utils
    building_graph --> navigation_session
    building_graph --> sd_augmentation

    dataset_utils --> embedding_index
    dataset_utils --> build_embeddings
    dataset_utils --> evaluation

    embedding_index --> localization
    embedding_index --> build_embeddings

    intent_parser --> navigation_session
    localization --> navigation_session
    localization --> evaluation
    state_tracker --> navigation_session
    routing --> navigation_session
    llm_instructor --> navigation_session

    navigation_session --> server
    speech_io --> server
    sd_augmentation --> server
    localization -.->|"standalone scan"| server

    server --> app
    evaluation --> app
    build_embeddings --> app

    evaluation --> evaluation_report

    style config fill:#1e3a5f,color:#fff
    style server fill:#2d5016,color:#fff
    style navigation_session fill:#5c1a5c,color:#fff
    style localization fill:#5c3a0e,color:#fff
    style building_graph fill:#0e4d4d,color:#fff
```

---

## 5. Data Flow — Complete Navigation Cycle

```mermaid
sequenceDiagram
    actor User
    participant UI as Browser (app.js)
    participant Canvas as FloorMap Canvas
    participant API as FastAPI (server.py)
    participant Orch as NavigationOrchestrator
    participant STT as Whisper STT
    participant IP as IntentParser
    participant Loc as Localizer (OCR+CLIP)
    participant ST as StateTracker
    participant RT as Router (Dijkstra)
    participant LLM as Llama 3.2 3B
    participant TTS as Piper TTS

    Note over User,TTS: Phase 1 — Session Initialization
    User->>UI: "Take me to Room 607" (voice/text)
    UI->>API: POST /api/start-session
    alt Voice input
        API->>STT: transcribe_audio(audio_bytes)
        STT-->>API: "take me to room 607"
    end
    API->>Orch: start_session("take me to room 607")
    Orch->>IP: parse_destination("take me to room 607")
    IP-->>Orch: (node_id="607", conf=0.95)
    Orch->>ST: create_session(destination="607")
    Orch->>RT: get_route(from=any_start, to="607")
    RT-->>Orch: route_steps[]
    Orch-->>API: {session, route, welcome_msg}
    API->>TTS: synthesize_speech(welcome_msg)
    TTS-->>API: WAV bytes → base64
    API-->>UI: JSON + audio_b64
    UI->>Canvas: setDestination("607"), setRoute(path)
    UI->>User: 🔊 "Navigating to Room 607, First Floor"

    Note over User,TTS: Phase 2 — Navigation Loop (repeats every scan)
    User->>UI: Points camera at door sign
    UI->>UI: scanSurroundings() → JPEG blob
    UI->>API: POST /api/navigate (image)
    API->>Orch: process_scan(session, image)
    Orch->>Loc: localize(image)

    par OCR Channel
        Loc->>Loc: EasyOCR → "505" → normalize → match graph
    and CLIP Channel
        Loc->>Loc: CLIP encode → cosine sim vs index → "505"
    end
    Loc-->>Orch: (node="505", conf=0.92, method="ocr+clip")

    Orch->>ST: update_position("505", route)
    ST-->>Orch: (movement="forward", heading="east")
    Orch->>RT: get_instruction_context("505", "607", heading="east")
    RT-->>Orch: {direction="straight ahead", next="506", remaining=4, landmark="Library"}
    Orch->>LLM: generate_instruction(context)
    LLM-->>Orch: "Continue straight past the Library toward Room 506."
    Orch-->>API: {instruction, progress, state}
    API->>TTS: synthesize_speech(instruction)
    API-->>UI: JSON + audio_b64
    UI->>Canvas: setCurrentNode("505"), update progress bar
    UI->>User: 🔊 "Continue straight past the Library toward Room 506."

    Note over User,TTS: Phase 3 — Arrival
    Orch-->>API: {status="arrived", movement="arrived"}
    API-->>UI: Arrival notification + audio
    UI->>User: 🔊 "You have arrived at Room 607." 🎉
```

---

## 6. External Service Dependencies

All services run **locally on the same machine**. No internet required at runtime.

```mermaid
graph LR
    subgraph "WayLens Python Process"
        App["app.py<br/>Uvicorn HTTPS :8000"]
    end

    subgraph "Local Services"
        Ollama["Ollama<br/>localhost:11434<br/>Llama 3.2 3B"]
        SD["AUTOMATIC1111<br/>localhost:7861<br/>Stable Diffusion 1.5"]
    end

    subgraph "System Dependencies"
        Tesseract["Tesseract OCR<br/>(optional fallback)"]
        Piper["Piper TTS Binary<br/>+ en_US ONNX model"]
    end

    App <-->|"HTTP"| Ollama
    App <-->|"HTTP"| SD
    App -.->|"subprocess"| Piper
    App -.->|"optional"| Tesseract
```

| Service | Protocol | Required? | Fallback |
|---------|----------|-----------|----------|
| **Ollama** (Llama 3.2 3B) | HTTP `:11434` | Recommended | Template-based instructions |
| **AUTOMATIC1111** (SD 1.5) | HTTP `:7861` | Optional | No visual previews |
| **Piper TTS** | Subprocess | Recommended | pyttsx3 → beep WAV |
| **Tesseract OCR** | System binary | Optional | EasyOCR only |

---

## 7. Performance Characteristics

| Component | Latency (CPU) | Memory |
|-----------|---------------|--------|
| EasyOCR inference | 300–500ms | ~200 MB |
| CLIP ViT-B-32 encode | < 150ms | ~350 MB |
| Cosine similarity query | < 5ms | ~1 MB (index) |
| Dijkstra routing | < 1ms | Negligible |
| Llama 3.2 3B (Ollama) | 1.2–2.5s | ~2 GB |
| Piper TTS synthesis | 200–500ms | ~50 MB |
| Whisper STT (base, int8) | 500ms–2s | ~150 MB |
| Stable Diffusion 1.5 | 30–60s | ~2 GB |
| **Total scan-to-instruction** | **~1.5–3.5s** | **~3 GB peak** |

Target hardware: **Intel Core i3 (Dual-Core / 4-Thread), 12 GB RAM, CPU-only.**

---

## 8. Security Model

| Feature | Implementation |
|---------|---------------|
| **HTTPS** | Auto-generated self-signed X.509 certs (RSA 2048-bit, SHA-256, 365-day validity) |
| **SAN** | `localhost` + `127.0.0.1` + detected LAN IP |
| **CORS** | `allow_origins=["*"]` (development mode) |
| **Session** | Single in-memory session, no auth |
| **Data** | All processing on-device, zero data exfiltration |

---

## 9. Evaluation & Testing Architecture

```mermaid
graph LR
    Dataset["dataset/<br/>train + val + test splits"]
    Eval["evaluation.py<br/>run_evaluation_benchmark()"]
    Loc["localization.py<br/>Full OCR+CLIP pipeline"]
    Report["walk_test_report.json"]
    MDGen["evaluation_report.py<br/>generate_markdown_report()"]
    MD["augmentation_results.md"]

    Dataset --> Eval
    Eval -->|"Per-image localization"| Loc
    Loc --> Eval
    Eval --> Report --> MDGen --> MD
```

**Reported Metrics:**
| Metric | Score |
|--------|-------|
| Intent Recognition | 100% |
| Graph Routing | 100% deterministic |
| Combined Localization (Top-1) | 96.8% |
| LLM Hallucination Rate | 0.0% |

---

## 10. File Inventory

| Path | Size | Purpose |
|------|------|---------|
| [`app.py`](file:///c:/Users/Asus/Downloads/Waylens/app.py) | 4.8 KB | CLI entry point (serve / eval / index) |
| [`requirements.txt`](file:///c:/Users/Asus/Downloads/Waylens/requirements.txt) | 328 B | Python dependencies |
| [`src/config.py`](file:///c:/Users/Asus/Downloads/Waylens/src/config.py) | 3.0 KB | Central configuration |
| [`src/building_graph.py`](file:///c:/Users/Asus/Downloads/Waylens/src/building_graph.py) | 47.4 KB | 3-floor knowledge graph (116 nodes) |
| [`src/embedding_index.py`](file:///c:/Users/Asus/Downloads/Waylens/src/embedding_index.py) | 10.5 KB | CLIP vector store manager |
| [`src/build_embeddings.py`](file:///c:/Users/Asus/Downloads/Waylens/src/build_embeddings.py) | 2.1 KB | Offline index builder |
| [`src/dataset_utils.py`](file:///c:/Users/Asus/Downloads/Waylens/src/dataset_utils.py) | 10.4 KB | Dataset scanning & validation |
| [`src/intent_parser.py`](file:///c:/Users/Asus/Downloads/Waylens/src/intent_parser.py) | 3.6 KB | Voice/text destination parser |
| [`src/localization.py`](file:///c:/Users/Asus/Downloads/Waylens/src/localization.py) | 8.9 KB | OCR + CLIP fusion engine |
| [`src/state_tracker.py`](file:///c:/Users/Asus/Downloads/Waylens/src/state_tracker.py) | 3.9 KB | Navigation state & heading tracker |
| [`src/routing.py`](file:///c:/Users/Asus/Downloads/Waylens/src/routing.py) | 6.1 KB | Dijkstra router + turn directions |
| [`src/llm_instructor.py`](file:///c:/Users/Asus/Downloads/Waylens/src/llm_instructor.py) | 3.8 KB | LLM instruction generator |
| [`src/navigation_session.py`](file:///c:/Users/Asus/Downloads/Waylens/src/navigation_session.py) | 4.7 KB | Session orchestrator |
| [`src/sd_augmentation.py`](file:///c:/Users/Asus/Downloads/Waylens/src/sd_augmentation.py) | 6.6 KB | Stable Diffusion integration |
| [`src/speech_io.py`](file:///c:/Users/Asus/Downloads/Waylens/src/speech_io.py) | 3.7 KB | Whisper STT + Piper TTS |
| [`src/evaluation.py`](file:///c:/Users/Asus/Downloads/Waylens/src/evaluation.py) | 3.5 KB | Benchmark evaluation suite |
| [`src/evaluation_report.py`](file:///c:/Users/Asus/Downloads/Waylens/src/evaluation_report.py) | 4.7 KB | Markdown report generator |
| [`src/server.py`](file:///c:/Users/Asus/Downloads/Waylens/src/server.py) | 6.4 KB | FastAPI server |
| [`static/index.html`](file:///c:/Users/Asus/Downloads/Waylens/static/index.html) | 10.7 KB | Accessible mobile SPA |
| [`static/style.css`](file:///c:/Users/Asus/Downloads/Waylens/static/style.css) | 13.2 KB | Dark-theme design system |
| [`static/app.js`](file:///c:/Users/Asus/Downloads/Waylens/static/app.js) | 22.0 KB | Client controller |
| [`static/floormap.js`](file:///c:/Users/Asus/Downloads/Waylens/static/floormap.js) | 28.8 KB | HD canvas map engine |
| [`data/building_graph.json`](file:///c:/Users/Asus/Downloads/Waylens/data/building_graph.json) | 70.1 KB | Serialized graph topology |
| [`data/label_map.json`](file:///c:/Users/Asus/Downloads/Waylens/data/label_map.json) | 8.0 KB | Node ↔ image path mapping |
| `data/MAP.pdf` | 424 KB | Architectural floor plan |
| `ocr_models/craft_mlt_25k.pth` | 83 MB | EasyOCR text detection weights |
| `ocr_models/english_g2.pth` | 15 MB | EasyOCR text recognition weights |

**Total source code**: ~200 KB across 22 files (excluding models and data).
