const els = {
  pageTitle: document.getElementById("pageTitle"),
  pageSubtitle: document.getElementById("pageSubtitle"),
  projectDescription: document.getElementById("projectDescription"),
  projectUseCase: document.getElementById("projectUseCase"),
  video: document.getElementById("camera"),
  overlay: document.getElementById("overlay"),
  startBtn: document.getElementById("startBtn"),
  fullscreenBtn: document.getElementById("fullscreenBtn"),
  frontCameraBtn: document.getElementById("frontCameraBtn"),
  rearCameraBtn: document.getElementById("rearCameraBtn"),
  wsStatus: document.getElementById("wsStatus"),
  cameraStatus: document.getElementById("cameraStatus"),
  fps: document.getElementById("fps"),
  speculativeText: document.getElementById("speculativeText"),
  reasoningText: document.getElementById("reasoningText"),
  tokenRail: document.getElementById("tokenRail"),
  modeLabel: document.getElementById("modeLabel"),
  modelStatus: document.getElementById("modelStatus"),
  analyzeFrameBtn: document.getElementById("analyzeFrameBtn"),
  saveCaptureBtn: document.getElementById("saveCaptureBtn"),
  panelLabel: document.getElementById("panelLabel"),
  gesture: document.getElementById("gesture"),
  attention: document.getElementById("attention"),
  headPose: document.getElementById("headPose"),
  specMs: document.getElementById("specMs"),
  activeMode: document.getElementById("activeMode"),
  ambientOrb: document.getElementById("ambientOrb"),
  cognitiveState: document.getElementById("cognitiveState"),
  interventionText: document.getElementById("interventionText"),
  reasoningPolicy: document.getElementById("reasoningPolicy"),
  importanceScore: document.getElementById("importanceScore"),
  recallAnswer: document.getElementById("recallAnswer"),
  eventLog: document.getElementById("eventLog"),
  reasoningLog: document.getElementById("reasoningLog"),
  phoneUrl: document.getElementById("phoneUrl"),
  diagnostics: document.getElementById("diagnostics"),
  captureAskPanel: document.getElementById("captureAskPanel"),
  captureQuestion: document.getElementById("captureQuestion"),
  askCaptureBtn: document.getElementById("askCaptureBtn"),
  captureAnswer: document.getElementById("captureAnswer"),
};

const appIdentity = resolveAppIdentity();

const state = {
  ws: null,
  recognizer: null,
  faceLandmarker: null,
  mediaPipeReady: null,
  stream: null,
  started: false,
  lastEventKey: "",
  lastSentKey: "",
  currentEventStarted: performance.now(),
  lastSentAt: 0,
  lastDetectionMs: 0,
  frames: 0,
  fpsStarted: performance.now(),
  latestTokens: [],
  events: [],
  reasoning: [],
  semanticMemory: loadSemanticMemory(),
  policyTrace: [],
  inputMode: "mediapipe_gemma",
  modelStatus: "checking",
  cameraFacingMode: "environment",
  switchingCamera: false,
};

applyAppIdentity();
connectWebSocket();
loadNetworkInfo();
registerPwa();
warmMediaPipe();
renderDiagnostics("Loaded app shell.");
updateModeUi();
updateCameraUi();

els.startBtn.addEventListener("click", startPerception);
els.fullscreenBtn.addEventListener("click", () => document.documentElement.requestFullscreen?.());
els.analyzeFrameBtn.addEventListener("click", analyzeCurrentFrame);
els.saveCaptureBtn.addEventListener("click", saveCurrentCapture);
els.askCaptureBtn.addEventListener("click", askSavedCaptures);
els.captureQuestion.addEventListener("keydown", (event) => {
  if (event.key === "Enter") askSavedCaptures();
});
els.frontCameraBtn.addEventListener("click", () => switchCamera("user"));
els.rearCameraBtn.addEventListener("click", () => switchCamera("environment"));
document.querySelectorAll("[data-mode]").forEach((button) => {
  button.addEventListener("click", () => setInferenceMode(button.dataset.mode));
});
document.querySelectorAll("[data-demo]").forEach((button) => {
  button.addEventListener("click", () => sendDemoEvent(button.dataset.demo));
});
document.querySelectorAll("[data-recall]").forEach((button) => {
  button.addEventListener("click", () => answerSemanticRecall(button.dataset.recall));
});

function resolveAppIdentity() {
  const port = window.location.port;
  if (port === "8443" || port === "8601") {
    return {
      title: "SecondSight",
      subtitle: "Live camera-to-text scene narrator",
      description:
        "Shows what the Samsung camera sees as short text. The phone provides the live view, and local Gemma 4 Vision turns selected frames into plain-language scene descriptions.",
      useCase:
        "Example: point the back camera at a desk, whiteboard, object, or room, then use Describe what I see to get a concise local text description.",
      panelLabel: "Live scene narrator",
      initialReasoningText: "Scene descriptions will appear here when SecondSight reads a camera frame.",
      analyzeLabel: "Describe what I see",
      captureLabel: "Save image",
      defaultInputMode: "gemma_multimodal",
      captureEnabled: true,
      taskLabels: {
        pointing: "Describe scene",
        raised_hand: "Read text",
        confused: "Identify objects",
      },
      visionTasks: true,
      context:
        "SecondSight: live camera-to-text scene narration using local Gemma 4 Vision",
    };
  }
  return {
    title: "ODML Checkpoint",
    subtitle: "Stable On-device Gemma 4 + LiteRT-LM + MediaPipe demo",
    description:
      "Preserves the event-ready ODML demo: Android browser MediaPipe converts camera signals into semantic events, and the Mac streams local Gemma 4 reasoning through LiteRT-LM.",
    useCase:
      "Example: point the Samsung camera at a whiteboard, trigger Inspect pipeline, and show how the local ODML/Gemma stack explains the visible setup.",
    panelLabel: "On-device agent loop",
    initialReasoningText: "Gemma 4 reasoning streams here after MediaPipe/ODML emits a semantic event.",
    analyzeLabel: "Analyze frame",
    captureLabel: "Save image",
    defaultInputMode: "mediapipe_gemma",
    captureEnabled: false,
    taskLabels: {
      pointing: "Inspect pipeline",
      raised_hand: "Audience Q&A",
      confused: "Explain stack",
    },
    visionTasks: false,
    context:
      "ODML checkpoint: Google-hosted On-device Gemma 4 showcase with LiteRT-LM and MediaPipe/ODML perception",
  };
}

function applyAppIdentity() {
  document.title = appIdentity.title;
  els.pageTitle.textContent = appIdentity.title;
  els.pageSubtitle.textContent = appIdentity.subtitle;
  els.projectDescription.textContent = appIdentity.description;
  els.projectUseCase.textContent = appIdentity.useCase;
  els.panelLabel.textContent = appIdentity.panelLabel;
  els.reasoningText.textContent = appIdentity.initialReasoningText;
  els.analyzeFrameBtn.textContent = appIdentity.analyzeLabel;
  els.saveCaptureBtn.textContent = appIdentity.captureLabel;
  els.saveCaptureBtn.classList.toggle("hidden", !appIdentity.captureEnabled);
  els.captureAskPanel.classList.toggle("hidden", !appIdentity.captureEnabled);
  state.inputMode = appIdentity.defaultInputMode;
  document.querySelectorAll("[data-demo]").forEach((button) => {
    button.textContent = appIdentity.taskLabels[button.dataset.demo] || button.dataset.demo;
  });
  updateAmbientState("watching", "ODML checkpoint is waiting for semantic events.", 0, "Gemma idle");
  renderSemanticRecallSeed();
}

async function startPerception() {
  if (state.started || state.switchingCamera) return;
  state.started = true;
  els.startBtn.textContent = "Starting...";
  try {
    const mediaPipeReady = state.mediaPipeReady || warmMediaPipe();
    await startCamera();
    await mediaPipeReady;
    els.startBtn.style.display = "none";
    updateModeUi();
    requestAnimationFrame(loop);
  } catch (error) {
    state.started = false;
    els.startBtn.textContent = "Retry camera";
    els.cameraStatus.textContent = "camera blocked";
    renderDiagnostics(`Camera startup failed: ${error.name || "Error"}: ${error.message || error}`);
  }
}

async function startCamera() {
  await stopCamera();
  els.cameraStatus.textContent = `camera ${cameraFacingLabel()} pending`;
  renderDiagnostics(`Requesting ${cameraFacingLabel()} camera...`);
  const stream = await requestCameraStream(state.cameraFacingMode);
  state.stream = stream;
  els.video.srcObject = stream;
  await els.video.play();
  els.cameraStatus.textContent = `${cameraFacingLabel()} camera live`;
  renderDiagnostics(`Camera live on ${cameraFacingLabel()} lens. MediaPipe is warming or ready.`);
}

async function requestCameraStream(facingMode) {
  if (!window.isSecureContext && location.hostname !== "localhost" && location.hostname !== "127.0.0.1") {
    throw new Error("Camera requires HTTPS on Android. Open the Tailscale HTTPS Serve URL, not the http://100.x.x.x URL.");
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error("This browser does not expose getUserMedia. Try Android Chrome or Samsung Internet over HTTPS.");
  }
  try {
    return await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: { exact: facingMode },
        width: { ideal: 960 },
        height: { ideal: 540 },
        frameRate: { ideal: 24, max: 30 },
      },
      audio: false,
    });
  } catch (error) {
    if (error.name !== "OverconstrainedError" && error.name !== "NotFoundError") throw error;
  }
  return navigator.mediaDevices.getUserMedia({
    video: {
      facingMode,
      width: { ideal: 960 },
      height: { ideal: 540 },
      frameRate: { ideal: 24, max: 30 },
    },
    audio: false,
  });
}

async function stopCamera() {
  state.stream?.getTracks().forEach((track) => track.stop());
  state.stream = null;
  if (els.video.srcObject) {
    els.video.pause();
    els.video.srcObject = null;
  }
}

async function switchCamera(facingMode) {
  if (state.cameraFacingMode === facingMode || state.switchingCamera) return;
  state.cameraFacingMode = facingMode;
  updateCameraUi();
  if (!state.started) {
    renderDiagnostics(`Camera lens set to ${cameraFacingLabel()}. Tap Start perception.`);
    return;
  }

  state.switchingCamera = true;
  els.cameraStatus.textContent = `switching to ${cameraFacingLabel()} camera`;
  updateCameraUi();
  try {
    await startCamera();
  } catch (error) {
    const fallbackFacingMode = facingMode === "environment" ? "user" : "environment";
    state.cameraFacingMode = fallbackFacingMode;
    updateCameraUi();
    renderDiagnostics(`Camera switch failed: ${error.name || "Error"}: ${error.message || error}`);
    try {
      await startCamera();
    } catch (fallbackError) {
      els.cameraStatus.textContent = "camera blocked";
      renderDiagnostics(`Camera recovery failed: ${fallbackError.name || "Error"}: ${fallbackError.message || fallbackError}`);
    }
  } finally {
    state.switchingCamera = false;
    updateCameraUi();
  }
}

async function initMediaPipe() {
  try {
    const { FaceLandmarker, FilesetResolver, GestureRecognizer } = await import(
      "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.18"
    );
    const vision = await FilesetResolver.forVisionTasks(
      "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.18/wasm",
    );
    state.recognizer = await GestureRecognizer.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath:
          "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task",
        delegate: "GPU",
      },
      runningMode: "VIDEO",
      numHands: 1,
    });
    state.faceLandmarker = await FaceLandmarker.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath:
          "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task",
        delegate: "GPU",
      },
      runningMode: "VIDEO",
      numFaces: 1,
    });
    els.cameraStatus.textContent = "MediaPipe live";
  } catch (error) {
    els.cameraStatus.textContent = "MediaPipe unavailable, camera fallback";
    renderDiagnostics(`Camera is live, but MediaPipe did not load: ${error.message || error}\nCheck phone internet for first model load, or vendor MediaPipe assets locally.`);
    console.warn(error);
  }
}

function warmMediaPipe() {
  state.mediaPipeReady = state.mediaPipeReady || initMediaPipe();
  return state.mediaPipeReady;
}

function loop(now) {
  state.frames += 1;
  if (now - state.fpsStarted > 1000) {
    els.fps.textContent = `${state.frames} fps`;
    state.frames = 0;
    state.fpsStarted = now;
  }

  if (els.video.readyState >= 2) {
    const detectionStarted = performance.now();
    const event = state.recognizer ? detectWithMediaPipe(now) : fallbackEvent();
    state.lastDetectionMs = performance.now() - detectionStarted;
    drawOverlay(event);
    maybeSendEvent(event, now);
  }
  requestAnimationFrame(loop);
}

function detectWithMediaPipe(now) {
  const gestureResult = state.recognizer.recognizeForVideo(els.video, now);
  const faceResult = state.faceLandmarker?.detectForVideo(els.video, now);
  const handLandmarks = gestureResult.landmarks?.[0] || [];
  const category = gestureResult.gestures?.[0]?.[0];
  const faceLandmarks = faceResult?.faceLandmarks?.[0] || [];

  const gesture = mapGesture(category?.categoryName, handLandmarks);
  const { headPose, attention } = inferFace(faceLandmarks);
  const rawGesture = category?.categoryName || "none";
  const key = `${gesture}:${attention}:${headPose}`;
  if (key !== state.lastEventKey) {
    state.lastEventKey = key;
    state.currentEventStarted = now;
  }
  const duration = (now - state.currentEventStarted) / 1000;
  const intentSignal = inferIntentSignal(gesture, attention, headPose, duration);
  const importance = scoreImportance(gesture, attention, headPose, intentSignal, duration, category?.score || 0.35);
  const reasoningPolicy = chooseReasoningPolicy(intentSignal, importance, duration);
  const cognitiveState = inferCognitiveState(attention, reasoningPolicy, intentSignal);

  return {
    source: "android-browser-pwa",
    gesture,
    attention,
    head_pose: headPose,
    input_mode: state.inputMode,
    intent_signal: intentSignal,
    raw_gesture: rawGesture,
    duration,
    context: currentEventContext(),
    confidence: category?.score || (faceLandmarks.length ? 0.68 : 0.35),
    importance,
    reasoning_policy: reasoningPolicy,
    cognitive_state: cognitiveState,
    landmarks: {
      hand: handLandmarks.slice(0, 21).map((p) => ({ x: p.x, y: p.y })),
      face: faceLandmarks.slice(0, 8).map((p) => ({ x: p.x, y: p.y })),
    },
    ts: Date.now() / 1000,
    event_id: randomId(),
  };
}

function scoreImportance(gesture, attention, headPose, intentSignal, duration, confidence) {
  let score = 0.08;
  if (gesture !== "none") score += 0.34;
  if (attention === "confused") score += 0.34;
  if (attention === "away") score += 0.24;
  if (headPose === "tilted_left" || headPose === "tilted_right") score += 0.16;
  if (duration > 2.5) score += 0.18;
  if (duration > 5) score += 0.16;
  if (intentSignal !== "ambient_monitoring") score += 0.2;
  score += Math.min(Math.max(confidence || 0, 0), 1) * 0.14;
  return Math.min(1, Number(score.toFixed(2)));
}

function chooseReasoningPolicy(intentSignal, importance, duration) {
  if (state.inputMode === "mediapipe") return "skip";
  if (state.inputMode === "gemma_multimodal") return "invoke";
  if (intentSignal === "ambient_monitoring" && duration < 5) return "skip";
  return importance >= 0.58 ? "invoke" : "skip";
}

function inferCognitiveState(attention, reasoningPolicy, intentSignal) {
  if (reasoningPolicy === "invoke") return intentSignal === "confused" ? "confused" : "reasoning";
  if (attention === "confused") return "confused";
  if (attention === "focused") return "focused";
  return "watching";
}

function mapGesture(name, landmarks) {
  if (!name) return "none";
  if (name === "Thumb_Up") return "thumbs_up";
  if (name === "Thumb_Down") return "thumbs_down";
  if (name === "Pointing_Up") return "pointing";
  if (name === "Open_Palm") {
    const wrist = landmarks[0];
    const tips = [8, 12, 16, 20].map((i) => landmarks[i]).filter(Boolean);
    const avgTipY = tips.reduce((sum, p) => sum + p.y, 0) / Math.max(tips.length, 1);
    return wrist && avgTipY < wrist.y - 0.16 ? "raised_hand" : "open_palm";
  }
  return "none";
}

function inferIntentSignal(gesture, attention, headPose, duration) {
  if (gesture === "raised_hand") return "help_request";
  if (gesture === "pointing") return "inspect_this";
  if (gesture === "thumbs_up") return "accept";
  if (gesture === "thumbs_down") return "reject";
  if (gesture === "open_palm" && duration > 1.2) return "pause";
  if (attention === "confused" || headPose === "tilted_left" || headPose === "tilted_right") return "confused";
  if (attention === "away") return "disengaged";
  if (duration > 5) return "sustained_focus";
  return "ambient_monitoring";
}

function inferFace(landmarks) {
  if (!landmarks.length) return { headPose: "unknown", attention: "unknown" };
  const left = landmarks[33] || landmarks[0];
  const right = landmarks[263] || landmarks[1] || left;
  const nose = landmarks[1] || landmarks[0];
  const slope = left.y - right.y;
  let headPose = "center";
  if (slope > 0.035) headPose = "tilted_left";
  else if (slope < -0.035) headPose = "tilted_right";
  else if (nose.x < 0.38 || nose.x > 0.62) headPose = "looking_away";

  const attention =
    headPose === "center" ? "focused" : headPose === "looking_away" ? "away" : "confused";
  return { headPose, attention };
}

function fallbackEvent() {
  return {
    source: "android-browser-pwa",
    gesture: "none",
    attention: "focused",
    head_pose: "center",
    input_mode: state.inputMode,
    intent_signal: "ambient_monitoring",
    raw_gesture: "fallback",
    duration: 0,
    context: currentEventContext(),
    confidence: 0.25,
    importance: 0.08,
    reasoning_policy: "skip",
    cognitive_state: "watching",
    landmarks: {},
    ts: Date.now() / 1000,
    event_id: randomId(),
  };
}

function maybeSendEvent(event, now) {
  els.gesture.textContent = event.gesture;
  els.attention.textContent = event.attention;
  els.headPose.textContent = event.head_pose;

  const key = `${event.gesture}:${event.attention}:${event.head_pose}`;
  const interesting = event.gesture !== "none" || event.attention === "confused" || event.duration > 2.5;
  const skipHeartbeat = event.reasoning_policy === "skip" && now - state.lastSentAt > 3200;
  if ((!interesting && !skipHeartbeat) || (key === state.lastSentKey && now - state.lastSentAt < 750)) {
    updateAmbientState(event.cognitive_state, ambientLineForEvent(event), event.importance, "Gemma skipped");
    return;
  }

  state.lastSentKey = key;
  state.lastSentAt = now;
  updateAmbientState(event.cognitive_state, ambientLineForEvent(event), event.importance, event.reasoning_policy === "invoke" ? "Gemma invoked" : "Gemma skipped");
  sendEvent(event, { includeFrame: state.inputMode === "gemma_multimodal" });
}

function sendDemoEvent(kind) {
  if (appIdentity.visionTasks) {
    sendVisionTask(kind);
    return;
  }
  const payloads = {
    raised_hand: {
      gesture: "raised_hand",
      attention: "focused",
      head_pose: "tilted_left",
      intent_signal: "focus_assistant",
      raw_gesture: "raised_hand",
      importance: 0.88,
      reasoning_policy: "invoke",
      cognitive_state: "intervening",
    },
    pointing: {
      gesture: "pointing",
      attention: "focused",
      head_pose: "center",
      intent_signal: "meeting_cognition",
      raw_gesture: "pointing",
      importance: 0.91,
      reasoning_policy: "invoke",
      cognitive_state: "reasoning",
    },
    confused: {
      gesture: "none",
      attention: "confused",
      head_pose: "tilted_right",
      intent_signal: "confusion_trace",
      raw_gesture: "confused",
      importance: 0.86,
      reasoning_policy: "invoke",
      cognitive_state: "confused",
    },
  };
  sendEvent({
    source: "browser-demo-button",
    input_mode: state.inputMode,
    duration: 5.2,
    context: currentEventContext(),
    confidence: 0.86,
    importance: 0.86,
    reasoning_policy: "invoke",
    cognitive_state: "reasoning",
    landmarks: {},
    ts: Date.now() / 1000,
    event_id: randomId(),
    ...payloads[kind],
  });
}

function sendVisionTask(kind) {
  const tasks = {
    pointing: {
      intent_signal: "describe_scene",
      raw_gesture: "describe_scene_button",
    },
    raised_hand: {
      intent_signal: "read_visible_text",
      raw_gesture: "read_text_button",
    },
    confused: {
      intent_signal: "identify_visible_objects",
      raw_gesture: "identify_objects_button",
    },
  };
  sendEvent(
    {
      source: "secondsight-task-button",
      gesture: "none",
      attention: "focused",
      head_pose: "center",
      input_mode: "gemma_multimodal",
      duration: 0,
      context: currentEventContext(),
      confidence: 0.74,
      importance: 0.9,
      reasoning_policy: "invoke",
      cognitive_state: "reasoning",
      landmarks: {},
      ts: Date.now() / 1000,
      event_id: randomId(),
      ...tasks[kind],
    },
    { includeFrame: true },
  );
}

function sendEvent(event, options = {}) {
  if (state.ws?.readyState !== WebSocket.OPEN) return;
  const payload = { ...event, input_mode: event.input_mode || state.inputMode };
  if (options.includeFrame) {
    const frame = captureFrame();
    if (frame) payload.frame = frame;
  }
  state.ws.send(JSON.stringify(payload));
  state.events.unshift(redactFrame(payload));
  state.events = state.events.slice(0, 8);
  els.eventLog.textContent = JSON.stringify(state.events, null, 2);
}

function analyzeCurrentFrame() {
  sendEvent(
    {
      source: "android-browser-pwa",
      gesture: "none",
      attention: "focused",
      head_pose: "center",
      input_mode: "gemma_multimodal",
      intent_signal: "analyze_visible_context",
      raw_gesture: "analyze_frame_button",
      duration: 0,
      context: currentEventContext(),
      confidence: 0.7,
      importance: 0.92,
      reasoning_policy: "invoke",
      cognitive_state: "reasoning",
      landmarks: {},
      ts: Date.now() / 1000,
      event_id: randomId(),
    },
    { includeFrame: true },
  );
}

async function saveCurrentCapture() {
  const frame = captureFrame();
  if (!frame) return;
  els.saveCaptureBtn.disabled = true;
  try {
    const response = await fetch("/captures", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source: "secondsight-save-button",
        label: "secondsight_capture",
        ts: Date.now() / 1000,
        metadata: {
          lens: cameraFacingLabel(),
          context: currentEventContext(),
          input_mode: state.inputMode,
          url: window.location.href,
        },
        frame,
      }),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    const capture = data.capture;
    els.captureAnswer.textContent = capture.caption || capture.summary || "Image saved.";
    els.reasoningText.textContent = capture.summary || capture.caption || els.reasoningText.textContent;
    renderDiagnostics(`Saved image ${capture.capture_id} (${capture.width}x${capture.height}, ${capture.bytes} bytes).`);
  } catch (error) {
    renderDiagnostics(`Image save failed: ${error.message || error}`);
  } finally {
    els.saveCaptureBtn.disabled = false;
  }
}

async function askSavedCaptures() {
  const question = els.captureQuestion.value.trim();
  if (!question) {
    els.captureAnswer.textContent = "Type a question about saved images first.";
    return;
  }
  els.askCaptureBtn.disabled = true;
  els.captureAnswer.textContent = "Searching saved image details...";
  try {
    const response = await fetch("/captures/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, limit: 6 }),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    els.captureAnswer.textContent = data.answer || "No answer returned.";
    state.reasoning.unshift({
      intent: "ask_saved_images",
      assistance: data.answer,
      captures: data.captures?.map((capture) => capture.capture_id) || [],
      ts: Date.now() / 1000,
    });
    state.reasoning = state.reasoning.slice(0, 6);
    els.reasoningLog.textContent = JSON.stringify(state.reasoning, null, 2);
  } catch (error) {
    els.captureAnswer.textContent = `Question failed: ${error.message || error}`;
  } finally {
    els.askCaptureBtn.disabled = false;
  }
}

function captureFrame() {
  if (els.video.readyState < 2) {
    renderDiagnostics("No live video frame is available yet.");
    return null;
  }
  const canvas = document.createElement("canvas");
  const width = Math.min(448, els.video.videoWidth || 448);
  const height = Math.round(width * ((els.video.videoHeight || 480) / (els.video.videoWidth || 640)));
  canvas.width = width;
  canvas.height = height;
  canvas.getContext("2d").drawImage(els.video, 0, 0, width, height);
  return {
    mime: "image/jpeg",
    width,
    height,
    data_url: canvas.toDataURL("image/jpeg", 0.72),
  };
}

function currentEventContext() {
  return appIdentity.context;
}

function redactFrame(event) {
  if (!event.frame) return event;
  return {
    ...event,
    frame: {
      mime: event.frame.mime,
      width: event.frame.width,
      height: event.frame.height,
      bytes: event.frame.data_url.length,
    },
  };
}

function updateAmbientState(cognitiveState, line, importance, policyLabel) {
  if (!els.ambientOrb || !els.cognitiveState || !els.interventionText || !els.reasoningPolicy || !els.importanceScore) {
    return;
  }
  const stateName = cognitiveState || "watching";
  els.ambientOrb.className = `ambient-orb ${stateName}`;
  els.cognitiveState.textContent = stateName;
  els.interventionText.textContent = line;
  els.reasoningPolicy.textContent = policyLabel;
  els.importanceScore.textContent = `importance ${Number(importance || 0).toFixed(2)}`;
}

function ambientLineForEvent(event) {
  if (event.reasoning_policy === "invoke" && event.intent_signal === "meeting_cognition") {
    return "Meeting signal detected. Compressing context for sparse Gemma reasoning.";
  }
  if (event.reasoning_policy === "invoke" && event.intent_signal === "focus_assistant") {
    return "Focus shift detected. Preparing a low-friction intervention.";
  }
  if (event.attention === "confused") return "Possible confusion detected. Waiting for a useful moment.";
  if (event.attention === "focused") return "Focused state detected. Gemma stays idle unless the signal changes.";
  return "Ambient perception active. Raw video stays on the device.";
}

function rememberSemanticMemory(memory) {
  const compact = {
    timestamp: memory.timestamp || Date.now() / 1000,
    event_id: memory.event_id || randomId(),
    summary: memory.summary || "Ambient semantic event",
    importance: Number(memory.importance || 0),
    cognitive_state: memory.cognitive_state || "watching",
    gesture: memory.gesture || "none",
    attention: memory.attention || "unknown",
    context: memory.context || currentEventContext(),
    reasoning_policy: memory.reasoning_policy || "skip",
  };
  state.semanticMemory.unshift(compact);
  state.semanticMemory = dedupeByEventId(state.semanticMemory).slice(0, 48);
  localStorage.setItem("secondsight.semanticMemory.v1", JSON.stringify(state.semanticMemory));
}

function loadSemanticMemory() {
  try {
    return JSON.parse(localStorage.getItem("secondsight.semanticMemory.v1") || "[]");
  } catch {
    return [];
  }
}

function dedupeByEventId(items) {
  const seen = new Set();
  return items.filter((item) => {
    if (seen.has(item.event_id)) return false;
    seen.add(item.event_id);
    return true;
  });
}

function renderSemanticRecallSeed() {
  if (!els.recallAnswer || !state.semanticMemory.length) return;
  els.recallAnswer.textContent = summarizeMemories(state.semanticMemory.slice(0, 3));
}

function answerSemanticRecall(kind) {
  if (!els.recallAnswer) return;
  const memories = state.semanticMemory;
  if (!memories.length) {
    els.recallAnswer.textContent = "No semantic memories yet. Trigger Focus assistant, Meeting cognition, or Confusion trace once.";
    return;
  }

  if (kind === "confusion") {
    const confused = memories.filter((memory) => memory.cognitive_state === "confused" || memory.attention === "confused");
    els.recallAnswer.textContent = confused.length
      ? summarizeMemories(confused.slice(0, 4))
      : "No confusion memories have been stored in this session.";
    return;
  }

  if (kind === "research") {
    const research = memories.filter((memory) => /research|meeting|whiteboard|pipeline|context|gemma|litert/i.test(memory.summary));
    els.recallAnswer.textContent = summarizeMemories((research.length ? research : memories).slice(0, 4));
    return;
  }

  els.recallAnswer.textContent = summarizeMemories(memories.slice(0, 6));
}

function summarizeMemories(memories) {
  return memories
    .map((memory) => {
      const time = new Date((memory.timestamp || Date.now() / 1000) * 1000).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
      return `${time}: ${memory.summary}`;
    })
    .join("\n");
}

function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  state.ws = new WebSocket(`${protocol}://${window.location.host}/ws/events`);

  state.ws.onopen = () => {
    els.wsStatus.textContent = "edge connected";
    els.wsStatus.classList.add("ready");
    sendMode(state.inputMode);
  };
  state.ws.onclose = () => {
    els.wsStatus.textContent = "reconnecting";
    els.wsStatus.classList.remove("ready");
    setTimeout(connectWebSocket, 900);
  };
  state.ws.onmessage = (message) => handleBackendMessage(JSON.parse(message.data));
}

function handleBackendMessage(message) {
  if (message.type === "snapshot") {
    state.inputMode = message.state?.inference_mode || state.inputMode;
    state.modelStatus = message.state?.model_status || state.modelStatus;
    updateModeUi();
  }
  if (message.type === "mode") {
    state.inputMode = message.mode || state.inputMode;
    state.modelStatus = message.model_status || state.modelStatus;
    updateModeUi();
  }
  if (message.type === "model_status") {
    state.modelStatus = message.status || state.modelStatus;
    updateModeUi();
  }
  if (message.type === "reasoning_policy") {
    const policyLabel = message.policy === "invoke" ? "Gemma invoked" : "Gemma skipped";
    const policyLine =
      message.policy === "invoke"
        ? `Sparse scheduler invoked Gemma for ${String(message.intent_signal || "semantic event").replaceAll("_", " ")}.`
        : "Sparse scheduler skipped Gemma to preserve thermals and battery.";
    state.policyTrace.unshift(message);
    state.policyTrace = state.policyTrace.slice(0, 12);
    updateAmbientState(message.cognitive_state, policyLine, message.importance, policyLabel);
  }
  if (message.type === "semantic_memory") {
    rememberSemanticMemory(message.memory);
    renderSemanticRecallSeed();
  }
  if (message.type === "hint") {
    els.speculativeText.textContent = message.hint.text;
    if (els.interventionText) els.interventionText.textContent = message.hint.text;
    els.specMs.textContent = `${message.hint.latency_ms.toFixed(1)} ms`;
    state.latestTokens = [];
    els.tokenRail.innerHTML = "";
  }
  if (message.type === "token") {
    state.latestTokens.push(message.token);
    const token = document.createElement("span");
    token.className = "token";
    token.textContent = message.token.replace(/\s+/g, " ");
    els.tokenRail.append(token);
    while (els.tokenRail.children.length > 44) els.tokenRail.firstChild.remove();
  }
  if (message.type === "reasoning") {
    els.reasoningText.textContent = message.result.assistance;
    updateAmbientState(message.result.should_intervene ? "intervening" : "focused", message.result.assistance, message.result.confidence, "Gemma complete");
    state.reasoning.unshift(message.result);
    state.reasoning = state.reasoning.slice(0, 6);
    els.reasoningLog.textContent = JSON.stringify(state.reasoning, null, 2);
  }
  if (message.type === "capture") {
    const caption = message.capture.caption || message.capture.summary || "Image saved.";
    els.captureAnswer.textContent = caption;
    renderDiagnostics(
      `Saved image ${message.capture.capture_id} (${message.capture.width}x${message.capture.height}, ${message.capture.bytes} bytes).`,
    );
  }
  if (message.type === "capture_answer") {
    els.captureAnswer.textContent = message.answer;
  }
}

function setInferenceMode(mode) {
  state.inputMode = mode || "mediapipe_gemma";
  updateModeUi();
  sendMode(state.inputMode);
}

function sendMode(mode) {
  if (state.ws?.readyState === WebSocket.OPEN) {
    state.ws.send(JSON.stringify({ type: "set_mode", mode }));
  }
}

function updateModeUi() {
  const labels = {
    mediapipe: "Perception only",
    mediapipe_gemma: "Sparse Gemma",
    gemma_multimodal: "Vision invoke",
  };
  els.modeLabel.textContent = labels[state.inputMode] || labels.mediapipe_gemma;
  els.activeMode.textContent = state.inputMode === "mediapipe" ? "ODML" : state.inputMode === "gemma_multimodal" ? "Vision" : "Gemma 4";
  els.modelStatus.textContent = state.modelStatus;
  els.analyzeFrameBtn.disabled = !state.started;
  document.querySelectorAll("[data-mode]").forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === state.inputMode);
  });
}

function updateCameraUi() {
  els.frontCameraBtn.classList.toggle("active", state.cameraFacingMode === "user");
  els.rearCameraBtn.classList.toggle("active", state.cameraFacingMode === "environment");
  els.frontCameraBtn.disabled = state.switchingCamera;
  els.rearCameraBtn.disabled = state.switchingCamera;
  els.fps.title = `Last detection pass: ${state.lastDetectionMs.toFixed(1)} ms`;
}

function cameraFacingLabel() {
  return state.cameraFacingMode === "environment" ? "back" : "front";
}

function drawOverlay(event) {
  const canvas = els.overlay;
  const rect = canvas.getBoundingClientRect();
  if (canvas.width !== rect.width || canvas.height !== rect.height) {
    canvas.width = rect.width;
    canvas.height = rect.height;
  }
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = event.gesture === "none" ? "rgba(123, 223, 242, 0.5)" : "#75e6b0";
  ctx.lineWidth = 2;
  const points = event.landmarks?.hand || [];
  points.forEach((point) => {
    ctx.beginPath();
    ctx.arc(point.x * canvas.width, point.y * canvas.height, 3, 0, Math.PI * 2);
    ctx.stroke();
  });
}

async function loadNetworkInfo() {
  try {
    const info = await fetch("/network-info").then((r) => r.json());
    els.phoneUrl.textContent = info.tailscale_https_url || info.tailscale_http_url || info.http_url;
    state.inputMode = info.inference_mode || state.inputMode;
    state.modelStatus = info.model_status || state.modelStatus;
    updateModeUi();
    updateCameraUi();
    renderDiagnostics(`Secure context: ${window.isSecureContext}\nCamera API: ${Boolean(navigator.mediaDevices?.getUserMedia)}\nBackend: ${info.host}\nLens: ${cameraFacingLabel()}`);
  } catch {
    els.phoneUrl.textContent = window.location.href;
  }
}

function registerPwa() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  }
}

function renderDiagnostics(message) {
  const base = [
    `URL: ${window.location.href}`,
    `Secure context: ${window.isSecureContext}`,
    `Camera API: ${Boolean(navigator.mediaDevices?.getUserMedia)}`,
    `Lens: ${cameraFacingLabel()}`,
    `Detection pass: ${state.lastDetectionMs.toFixed(1)} ms`,
    `Event context: ${currentEventContext()}`,
  ];
  els.diagnostics.textContent = `${message}\n${base.join("\n")}`;
}

function randomId() {
  return crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
