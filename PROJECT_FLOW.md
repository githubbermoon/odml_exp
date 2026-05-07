# EdgePulse Project Flow

This document explains how the current EdgePulse MVP is wired, which scripts matter, what the Python virtual environment contains, and how the native Android code fits into the roadmap.

## Current Running Status

The main app is the browser/PWA MVP.

Main runtime:

```bash
./scripts/run_pwa.sh
```

This starts FastAPI/Uvicorn on localhost:

```text
http://127.0.0.1:8501
```

Current Mac Tailscale IP detected by the backend:

```text
100.89.1.45
```

Plain Tailscale IP:

```text
100.89.1.45
```

Do not open the IP with port `8501` for the Android camera demo. Tailscale Serve exposes the app through the DNS HTTPS URL below.

Current Tailscale HTTPS Serve URL:

```text
https://pranjals-macbook-air.tail32e467.ts.net/
```

Important Android camera note:

Android Chrome/Samsung Internet usually require HTTPS for camera access unless the page is localhost. For phone camera access, use Tailscale Serve HTTPS once it is enabled on the tailnet.

The attempted command was:

```bash
./scripts/tailscale_serve_https.sh
```

It reported:

```text
Serve is not enabled on your tailnet.
```

Tailscale gave this enablement URL:

```text
https://login.tailscale.com/f/serve?node=ni32J2ToBj11CNTRL
```

After enabling Serve, rerun:

```bash
./scripts/tailscale_serve_https.sh
```

The helper now uses:

```bash
tailscale serve --bg http://127.0.0.1:8501
```

Do not use `https://100.89.1.45:8501` or `http://100.89.1.45:8501` for Android camera perception. Use the `*.ts.net` HTTPS URL.

## Virtual Environment

A Python virtual environment exists at:

```text
.venv/
```

It was created by:

```bash
./scripts/setup_macos.sh
```

The script uses Python 3.11 and installs dependencies from:

```text
requirements.txt
```

Key installed packages:

- `fastapi`
- `uvicorn`
- `websockets`
- `httpx`
- `streamlit`
- `opencv-python`
- `mediapipe`
- `pytest`

Activate manually with:

```bash
source .venv/bin/activate
```

Run tests with:

```bash
pytest -q
```

Current verification result:

```text
5 passed
```

## Main Scripts

Use this for the actual MVP:

```bash
./scripts/run_pwa.sh
```

This starts:

- the browser PWA
- the FastAPI backend
- the WebSocket endpoint
- the Gemma/LiteRT reasoning adapter
- the speculative interaction stream

Use this only after Tailscale Serve is enabled:

```bash
./scripts/tailscale_serve_https.sh
```

This exposes the local app through Tailscale HTTPS so Android browser camera permissions work reliably.

Useful helper:

```bash
./scripts/tailscale_status.sh
```

This prints the Mac Tailscale IP and tailnet peers.

First-time setup only:

```bash
./scripts/setup_macos.sh
```

Legacy or optional scripts:

```bash
./scripts/run_dashboard.sh
./scripts/run_mac_perception.sh
./scripts/run_runtime.sh
```

`run_dashboard.sh` is the older Streamlit dashboard path.

`run_mac_perception.sh` is the optional Mac webcam MediaPipe path.

`run_runtime.sh` now points to the same FastAPI runtime on port `8501`, but `run_pwa.sh` is the clearer main command.

## Main Architecture

```text
Samsung S21 FE Browser
├── opens EdgePulse PWA
├── requests camera permission
├── runs MediaPipe JS in browser
├── detects gestures / face direction / attention
├── creates semantic events
└── streams events over WebSocket
        ↓
Tailscale private mesh
        ↓
Mac M4 Backend
├── FastAPI app
├── WebSocket event handler
├── speculative interaction engine
├── LiteRT-LM / Gemma adapter
├── token streaming
├── state store
└── debug dashboard UI
```

## Code Flow

### 1. Browser loads the PWA

Entry point:

```text
edgepulse/web/index.html
```

Styling:

```text
edgepulse/web/styles.css
```

Frontend logic:

```text
edgepulse/web/app.js
```

The browser UI:

- shows the phone camera feed
- draws landmark overlays
- displays current gesture, attention, and head pose
- shows instant speculative text
- displays streamed Gemma reasoning
- shows token chunks and debug traces
- includes demo buttons for raised hand, pointing, and confused states

### 2. Browser asks for camera access

Code:

```text
edgepulse/web/app.js
```

Main browser API:

```js
navigator.mediaDevices.getUserMedia(...)
```

This is why HTTPS matters on Android phones.

### 3. MediaPipe JS runs perception

Code:

```text
edgepulse/web/app.js
```

It dynamically imports:

```text
@mediapipe/tasks-vision
```

It uses:

- `GestureRecognizer`
- `FaceLandmarker`

The frontend converts raw perception into semantic events like:

```json
{
  "source": "android-browser-pwa",
  "gesture": "raised_hand",
  "attention": "focused",
  "head_pose": "tilted_left",
  "duration": 4.2,
  "context": "on_device_gemma4_showcase",
  "confidence": 0.86
}
```

Current note:

MediaPipe JS assets are loaded from public static URLs. For a fully offline venue demo, vendor these assets into `edgepulse/web/` and update `app.js` paths.

### 4. WebSocket sends events to Mac

Frontend WebSocket path:

```text
/ws/events
```

Backend code:

```text
edgepulse/network/server.py
```

The same WebSocket is bidirectional:

- browser sends perception events
- backend sends speculative hints
- backend streams token chunks
- backend sends final reasoning result

### 5. Backend creates instant speculative response

Code:

```text
edgepulse/speculative/engine.py
```

Example:

```text
raised_hand
→ "Looks like you need help..."
```

This layer is intentionally lightweight and heuristic. It simulates the product feel of Gemma 4 MTP/speculative decoding without implementing real speculative decoding internals.

### 6. Backend sends event to reasoning engine

Agent loop:

```text
edgepulse/agent/loop.py
```

Reasoning adapter:

```text
edgepulse/reasoning/litert_lm.py
```

The prompt template asks the local model to infer:

1. probable user intent
2. whether intervention is useful
3. best concise assistance
4. confidence score

### 7. LiteRT-LM / Gemma integration

Configured through:

```text
.env
```

Important variables:

```bash
EDGEPULSE_MODEL=gemma-e2b-litert-lm
EDGEPULSE_LITERT_CMD=
```

If `EDGEPULSE_LITERT_CMD` is empty, the app uses a deterministic offline fallback. This keeps the demo running even without model weights installed.

Expected future runner shape:

```bash
EDGEPULSE_LITERT_CMD="/path/to/litert_runner --model /models/gemma-e2b.task --stream"
```

The command should:

- read prompt text from stdin
- stream JSON/text to stdout

### 8. Browser receives streaming response

Backend emits these WebSocket message types:

```text
snapshot
hint
token
reasoning
```

Frontend handling:

```text
edgepulse/web/app.js
```

The UI updates immediately on `hint`, appends token chips on `token`, and replaces the reasoning panel on `reasoning`.

## Backend Runtime

Main backend file:

```text
edgepulse/network/server.py
```

Important routes:

```text
GET  /
GET  /manifest.json
GET  /sw.js
GET  /health
GET  /network-info
GET  /state
POST /events
WS   /ws/events
WS   /ws/stream
```

`/network-info` detects Tailscale and helps the UI show a phone URL.

## PWA Files

```text
edgepulse/web/index.html
edgepulse/web/styles.css
edgepulse/web/app.js
edgepulse/web/manifest.json
edgepulse/web/sw.js
edgepulse/web/assets/icon.svg
```

These make the browser experience app-like:

- fullscreen mobile layout
- dark futuristic UI
- add-to-home-screen manifest
- service worker cache shell
- camera-first interface

## Phase 3 Native Android

The native Android app was preserved and moved to:

```text
phase3_android_native/
```

Documentation:

```text
PHASE3_NATIVE_ANDROID.md
phase3_android_native/README.md
```

This is not the current MVP path. It is the future fully native/offline path:

```text
Samsung S21 FE
├── CameraX
├── MediaPipe Android
├── LiteRT Android
├── Gemma E2B
└── fully offline local reasoning
```

## Recommended Demo Flow

1. Start the backend:

```bash
./scripts/run_pwa.sh
```

2. Enable and start Tailscale HTTPS Serve:

```bash
./scripts/tailscale_serve_https.sh
```

3. Open the HTTPS Tailscale URL on the Samsung phone:

```text
https://pranjals-macbook-air.tail32e467.ts.net/
```

4. Tap `Start perception`.

5. Allow camera permission.

6. Raise hand / point / tilt head.

7. Show:

- instant speculative hint
- streamed token rail
- final reasoning
- semantic event trace
- latency metrics

## Current Limitations

- Tailscale Serve must be enabled in the tailnet admin flow before HTTPS serving works.
- Android camera perception must be opened from the `*.ts.net` HTTPS URL, not the `100.x.x.x` IP URL.
- MediaPipe JS model assets are not vendored locally yet.
- Real Gemma/LiteRT-LM execution requires filling `EDGEPULSE_LITERT_CMD`.
- The native Android project is preserved for Phase 3, not the active demo path.

## What To Edit Next

Highest-impact next changes:

1. Vendor MediaPipe JS models locally for offline demo reliability.
2. Add QR code generation for the phone URL.
3. Add a real LiteRT-LM command wrapper for Gemma E2B/E4B.
4. Add richer event confidence visualizations.
5. Add coding-context cards for the meetup story.
