# EdgePulse

EdgePulse is a private real-time multimodal edge AI copilot prototype for a Google AI Edge / Gemma / LiteRT meetup.

The current MVP is browser-first for speed and demo reliability:

```text
Android Browser / PWA
├── camera access
├── MediaPipe JS perception
├── speculative UI hints
└── WebSocket client
        ↓ Tailscale
Mac M4 Backend
├── LiteRT-LM / Gemma 4 E2B adapter
├── event-driven reasoning loop
├── streaming token responses
├── latency metrics
└── live debug dashboard
```

The native Android app is preserved as Phase 3 in `phase3_android_native/`. See `PHASE3_NATIVE_ANDROID.md`.

## What Runs Now

- FastAPI serves the PWA and WebSocket backend on port `8501`.
- Android Chrome/Samsung Internet opens the PWA over Tailscale.
- Browser camera uses `getUserMedia()`.
- MediaPipe JS performs gesture and face/attention perception in the browser.
- Semantic events stream to the Mac over WebSocket.
- The Mac emits instant speculative hints, then streams Gemma/LiteRT-LM reasoning tokens.
- The PWA can switch between the ODML/MediaPipe fast path, ODML/MediaPipe + Gemma 4 text reasoning, and a Direct Gemma 4 Vision hook.
- The PWA shows camera overlay, semantic events, token stream, reasoning trace, latency, and Tailscale URL help.

No cloud inference is used. The MediaPipe JS demo currently loads browser assets/models from public static URLs; vendor those assets locally for a fully disconnected venue demo.

## Setup

```bash
./scripts/setup_macos.sh
```

Configure `.env` if you have a LiteRT-LM runner:

```bash
EDGEPULSE_MODEL=gemma-4-E2B-it-litert-lm
GEMMA4_E2B_MODEL_ID=gemma-4-e2b
EDGEPULSE_LITERT_SERVER_URL=http://127.0.0.1:9379
EDGEPULSE_LITERT_CMD="./scripts/run_gemma4_e2b_litert.sh"
EDGEPULSE_LITERT_VISION_CMD="./scripts/run_gemma4_e2b_vision.sh"
```

Install and warm the LiteRT-LM Gemma 4 E2B model once before the demo:

```bash
uv tool install litert-lm
./scripts/run_gemma4_e2b_litert.sh <<'EOF'
Return compact JSON only: {"intent":"test","should_intervene":false,"assistance":"ready","confidence":0.9,"actions":[]}
EOF
```

For lower latency, start the resident LiteRT-LM server before the PWA:

```bash
./scripts/start_gemma4_e2b_server.sh
```

If `EDGEPULSE_LITERT_CMD` is empty, EdgePulse uses a deterministic offline fallback so the demo still works.

Direct Gemma multimodal mode uses the separate image-capable wrapper. It receives JSON on stdin:

```bash
EDGEPULSE_LITERT_VISION_CMD="./scripts/run_gemma4_e2b_vision.sh"
```

The JSON payload is:

```json
{"prompt": "...", "frame": {"mime": "image/jpeg", "width": 640, "height": 480, "data_url": "data:image/jpeg;base64,..."}}
```

## Run

Terminal 1:

```bash
./scripts/run_pwa.sh
```

Open on the Mac:

```text
http://127.0.0.1:8501
```

## Tailscale Phone Flow

1. Install Tailscale on the Mac and Samsung S21 FE.
2. Sign both into the same tailnet.
3. Check the Mac tailnet IP:

```bash
./scripts/tailscale_status.sh
```

4. For Android camera access, use Tailscale HTTPS Serve:

```bash
./scripts/run_pwa.sh
./scripts/tailscale_serve_https.sh
```

5. Open the HTTPS Tailscale Serve URL on the phone. It should look like:

```text
https://<mac-name>.<tailnet>.ts.net/
```

Android browsers require HTTPS for camera access except on localhost. Do not use `http://100.x.x.x:8501` or `https://100.x.x.x:8501` for the camera demo; use the `*.ts.net` HTTPS URL.

## Demo Flow

1. Open EdgePulse on the Samsung phone browser.
2. Tap `Start perception`.
3. Allow camera permission.
4. Raise a hand, point, or tilt your head.
5. The UI immediately displays a speculative hint like “Looks like you need help...”.
6. Switch inference modes:
   - `MediaPipe`: browser perception and heuristic hint only.
   - `MediaPipe + Gemma`: semantic event JSON streams to Gemma 4 E2B text reasoning.
   - `Gemma Vision`: captures a compressed frame and routes it to `EDGEPULSE_LITERT_VISION_CMD`.
7. The Mac streams local Gemma/LiteRT-LM reasoning back into the UI.
8. Show the token rail, semantic events, reasoning trace, and latency metrics.

## Speculative Interaction

EdgePulse does not implement true speculative decoding, Gemma MTP internals, or DFlash internals.

It implements the product behavior that matters for the demo:

- instant heuristic drafter-style UI
- optimistic partial response
- streamed local reasoning refinement
- visible token timing
- low perceived latency

This aligns with the Gemma 4 MTP direction without making the meetup demo depend on fragile research internals.

## Important Paths

```text
edgepulse/network/server.py       FastAPI app, PWA serving, WebSocket streaming
edgepulse/web/                    mobile-first PWA frontend
edgepulse/speculative/engine.py   speculative UX layer
edgepulse/reasoning/litert_lm.py  Gemma/LiteRT-LM adapter
scripts/run_gemma4_e2b_litert.sh  Gemma 4 E2B text LiteRT-LM wrapper
scripts/run_gemma4_e2b_vision.sh  Gemma 4 E2B image attachment wrapper
scripts/start_gemma4_e2b_server.sh resident LiteRT-LM OpenAI-compatible server
edgepulse/perception/             optional Mac MediaPipe pipeline
phase3_android_native/            preserved native Android app for Phase 3
PHASE3_NATIVE_ANDROID.md          future native deployment plan
docs/dflash_mlx_feasibility.md    DFlash/MLX feasibility note
```

## Verification

```bash
source .venv/bin/activate
pytest -q
python -m compileall edgepulse -q
```

## Roadmap

- vendor MediaPipe JS model assets for no-internet venue demos
- improve LiteRT-LM performance by replacing per-request CLI startup with a resident runner/server
- add QR code display for the Tailscale Serve URL
- add richer landmark visualization and gesture confidence charts
- add event/booth task cards for ODML pipeline inspection, audience Q&A, and stack explanation
- migrate browser MediaPipe logic into `phase3_android_native/` for full phone-only execution
- evaluate official Gemma MTP drafter support before any DFlash/MLX research branch
