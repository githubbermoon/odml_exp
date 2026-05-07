# Phase 3: Full Native Android Deployment

The native Android app is preserved in `phase3_android_native/`.

It is not the primary meetup MVP. The fastest demo path is now the browser/PWA experience served from the Mac over Tailscale. The native code remains buildable later as the full offline phone deployment track.

## Future Native Architecture

```text
Samsung S21 FE
├── CameraX camera pipeline
├── MediaPipe Android perception
├── gesture + attention semantic events
├── LiteRT / MediaPipe LLM Inference API
├── Gemma E2B local reasoning
├── optional GPU/NPU acceleration
└── fully offline execution with no Mac required
```

## Current Native Code

The preserved project contains:

- Kotlin + Gradle Android application setup
- Jetpack Compose shell
- Camera permission flow
- CameraX front-camera preview
- MediaPipe Tasks Vision dependency
- semantic event data model
- gesture heuristic module
- WebSocket event router

## Migration Path

1. Replace the CameraX analyzer heartbeat with real MediaPipe frame processing.
2. Use MediaPipe `GestureRecognizer`, `HandLandmarker`, and face tasks to generate semantic events.
3. Add LiteRT Android model loading for Gemma E2B.
4. Add a local reasoning mode that bypasses the Mac backend.
5. Keep Tailscale/WebSocket as an optional hybrid distributed mode.
6. Add performance profiling on Samsung S21 FE for camera, MediaPipe, and LiteRT inference.

## Android Edge AI Notes

- Prefer Gemma E2B for the phone-only path.
- Use compact prompts and structured JSON outputs.
- Keep video frames on-device; send only semantic events when hybrid mode is enabled.
- Explore GPU delegate support first; NPU paths depend on device/runtime availability.
- MediaPipe LLM Inference API and LiteRT Android should be evaluated as the native runtime matures.
