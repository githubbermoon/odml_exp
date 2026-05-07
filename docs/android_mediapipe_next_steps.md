# Phase 3 Android MediaPipe Wiring

The preserved native Android prototype lives in `phase3_android_native/`. It includes the deployment shell and event router. To complete live phone perception in Phase 3:

1. Add a CameraX `ImageAnalysis` pipeline.
2. Convert `ImageProxy` frames into `MPImage`.
3. Run MediaPipe Tasks Vision hand/gesture detection.
4. Convert landmarks into `HandSignal`.
5. Call `GestureHeuristics.classify(...)`.
6. Send the resulting `PerceptionEvent` through `EventRouter`.

Recommended MediaPipe tasks:

- `GestureRecognizer` for common hand gestures.
- `HandLandmarker` when custom heuristics are preferred.
- Face landmarker or face detector for coarse attention/head-pose signals.

Keep the event payload semantic. Do not stream video over Tailscale for the main demo unless explicitly debugging perception.
