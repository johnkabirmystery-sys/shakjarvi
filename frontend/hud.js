/**
 * J.A.R.V.I.S. — Shakil's Assistant HUD Core Logic
 * Real-time Telemetry, Arc Reactor Visualizer, Neural Voice & Speech Interaction
 */

// Global State
const state = {
  status: "idle", // idle, listening, thinking, executing, speaking
  isListening: false,
  continuousVoice: true,
  wakeWordEnabled: false,
  conversationActiveUntil: 0,
  soundFxEnabled: true,
  volume: 100,
  activeAudio: null,
  chatHistory: [],
  voices: [],
  speechLang: localStorage.getItem("jarvis_speech_lang") || "en-IN",
  audioMode: localStorage.getItem("jarvis_audio_mode") || "browser",
  selectedModel: localStorage.getItem("jarvis_selected_model") || "agy/gemini-3.7-flash-low",
  currentWorkspace: localStorage.getItem("jarvis_workspace") || "personal",
  audioUnlocked: false,
  jarvisIsSpeaking: false,
  speakingTurnTimer: null,
  currentThoughts: []
};

// Web Audio API Context
let audioCtx = null;
let analyser = null;
let audioSource = null;
const audioFreqData = new Uint8Array(64);

function initAudioContext() {
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    analyser = audioCtx.createAnalyser();
    analyser.fftSize = 128;
  }
  if (audioCtx.state === "suspended") {
    audioCtx.resume();
  }
}

// Active Audio Unlock Shield (primes both Web Audio & HTML5 Audio without restriction)
function unlockAllAudioEngines() {
  if (state.audioUnlocked) return;
  try {
    initAudioContext();
    if (audioCtx && audioCtx.state === "suspended") {
      audioCtx.resume();
    }
    // Prime HTML5 Audio element with a 0.01s silent wav
    const silent = new Audio("data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA");
    silent.play().then(() => {
      state.audioUnlocked = true;
      hideAudioUnlockBanner();
    }).catch(() => {
      // Will be unlocked on next gesture
    });
  } catch(e) {
    console.warn("Audio unlock attempt:", e);
  }
}

function hideAudioUnlockBanner() {
  const banner = document.getElementById("audioUnlockBanner");
  if (banner && banner.style.display !== "none") {
    banner.style.borderColor = "#38ef7d";
    banner.style.color = "#38ef7d";
    banner.innerHTML = `<span class="audio-banner-icon">🟢</span> <span id="audioBannerText">AUDIO ENGINE UNLOCKED · DIRECT NEURAL VOICE LINK ENGAGED</span>`;
    setTimeout(() => {
      banner.style.transition = "opacity 0.6s ease, transform 0.6s ease";
      banner.style.opacity = "0";
      banner.style.transform = "translateY(-10px)";
      setTimeout(() => { banner.style.display = "none"; }, 600);
    }, 1400);
  }
}

// ----------------------------------------------------
// STRICT DUPLEX TURN-TAKING LOCK & AUTO-MIC ENGINE
// ----------------------------------------------------
function lockMicForJarvisTurn(reason = "COMMUNICATING") {
  state.jarvisIsSpeaking = true;
  if (state.speakingTurnTimer) {
    clearTimeout(state.speakingTurnTimer);
    state.speakingTurnTimer = null;
  }
  if (speechSilenceTimer) {
    clearTimeout(speechSilenceTimer);
    speechSilenceTimer = null;
  }
  currentRecordedText = "";

  // Abort speech recognition immediately to kill buffer and prevent feedback
  if (recognition) {
    try {
      recognition.abort();
    } catch(e) {}
  }
  state.isListening = false;

  const micBtn = document.getElementById("btnVoiceToggle");
  if (micBtn) {
    micBtn.classList.remove("active");
    micBtn.classList.add("speaking-locked");
  }
  updateMicBadge("MUTED (JARVIS SPEAKING)", "#ff3344");

  const cmdInput = document.getElementById("cmdInput");
  const btnSend = document.getElementById("btnSend");
  if (cmdInput) {
    cmdInput.disabled = true;
    cmdInput.placeholder = "Jarvis speaking... microphone will auto-arm when complete.";
  }
  if (btnSend) btnSend.disabled = true;
}

function unlockMicAfterJarvisTurn() {
  if (state.speakingTurnTimer) {
    clearTimeout(state.speakingTurnTimer);
    state.speakingTurnTimer = null;
  }

  // Grace buffer (350ms) to allow speaker acoustic reverberation to settle
  state.speakingTurnTimer = setTimeout(() => {
    state.jarvisIsSpeaking = false;
    currentPlayingAudio = null;

    const micBtn = document.getElementById("btnVoiceToggle");
    if (micBtn) {
      micBtn.classList.remove("speaking-locked");
    }

    const cmdInput = document.getElementById("cmdInput");
    const btnSend = document.getElementById("btnSend");
    if (cmdInput) {
      cmdInput.disabled = false;
      cmdInput.placeholder = "Enter directive or speak freely ('Jarvis, check my emails')...";
    }
    if (btnSend) btnSend.disabled = false;

    // Auto-engage microphone immediately!
    if (state.continuousVoice) {
      setAssistantStatus("listening", "LISTENING FOR SIR SHAKIL");
      startVoiceListener();
      updateMicBadge("LIVE", "#00ffff");
      playSound("ack"); // Subtle futuristic chime: "Your turn to speak, Sir"
    } else {
      setAssistantStatus("idle", "AWAITING DIRECTIVE");
      updateMicBadge("STANDBY", "#888888");
    }
  }, 350);
}

// Synthetic Sci-Fi Sound FX Engine
function playSound(type) {
  if (!state.soundFxEnabled) return;
  try {
    initAudioContext();
    const now = audioCtx.currentTime;
    
    if (type === "blip") {
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(1400, now);
      osc.frequency.exponentialRampToValueAtTime(800, now + 0.05);
      gain.gain.setValueAtTime(0.08, now);
      gain.gain.linearRampToValueAtTime(0, now + 0.05);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start(now);
      osc.stop(now + 0.05);
    } else if (type === "ack") {
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(880, now);
      osc.frequency.setValueAtTime(1760, now + 0.06);
      gain.gain.setValueAtTime(0.1, now);
      gain.gain.linearRampToValueAtTime(0, now + 0.14);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start(now);
      osc.stop(now + 0.14);
    } else if (type === "boot") {
      [523.25, 659.25, 783.99, 1046.50].forEach((freq, idx) => {
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = "triangle";
        osc.frequency.setValueAtTime(freq, now + idx * 0.08);
        gain.gain.setValueAtTime(0.06, now + idx * 0.08);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.8 + idx * 0.08);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start(now + idx * 0.08);
        osc.stop(now + 0.85 + idx * 0.08);
      });
    } else if (type === "alert") {
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = "sawtooth";
      osc.frequency.setValueAtTime(440, now);
      osc.frequency.linearRampToValueAtTime(880, now + 0.15);
      gain.gain.setValueAtTime(0.12, now);
      gain.gain.linearRampToValueAtTime(0, now + 0.2);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start(now);
      osc.stop(now + 0.2);
    }
  } catch (e) {
    console.error("Audio FX error:", e);
  }
}

// ----------------------------------------------------
// CANVAS ARC REACTOR RENDERER
// ----------------------------------------------------
const canvas = document.getElementById("arcCanvas");
const ctx = canvas ? canvas.getContext("2d") : null;
let rotationRing1 = 0;
let rotationRing2 = 0;
let rotationRing3 = 0;

function drawArcReactor() {
  if (!canvas || !ctx) return;
  const w = canvas.width;
  const h = canvas.height;
  const cx = w / 2;
  const cy = h / 2;

  ctx.clearRect(0, 0, w, h);

  // Read audio frequency if active
  let avgFreq = 0;
  if (analyser && (state.status === "speaking" || state.status === "listening")) {
    try {
      analyser.getByteFrequencyData(audioFreqData);
      let sum = 0;
      for (let i = 0; i < 32; i++) sum += audioFreqData[i];
      avgFreq = sum / 32 / 255; // 0 to 1
    } catch(e){}
  }

  // Dynamic synthetic audio pulse if speaking via PC hardware speaker
  if (state.status === "speaking" && avgFreq < 0.05) {
    const t = Date.now() / 150;
    avgFreq = 0.35 + Math.sin(t) * 0.18 + Math.cos(t * 1.6) * 0.12;
    for (let i = 0; i < 32; i++) {
      audioFreqData[i] = Math.floor(avgFreq * 255 * (0.6 + 0.4 * Math.sin(t + i * 0.3)));
    }
  }

  // Color scheme based on state
  let primaryColor = "#00f0ff";
  let glowColor = "rgba(0, 240, 255, 0.4)";
  let speedMult = 1;

  if (state.status === "listening") {
    primaryColor = "#00ffff";
    glowColor = "rgba(0, 255, 255, 0.7)";
    speedMult = 1.6;
  } else if (state.status === "thinking") {
    primaryColor = "#ffaa00";
    glowColor = "rgba(255, 170, 0, 0.7)";
    speedMult = 2.8;
  } else if (state.status === "executing") {
    primaryColor = "#ff3344";
    glowColor = "rgba(255, 51, 68, 0.7)";
    speedMult = 3.5;
  } else if (state.status === "speaking") {
    primaryColor = "#38ef7d";
    glowColor = "rgba(56, 239, 125, 0.7)";
    speedMult = 1.2;
  }

  rotationRing1 += 0.008 * speedMult;
  rotationRing2 -= 0.012 * speedMult;
  rotationRing3 += 0.005 * speedMult;

  // Outer ambient glow
  const grad = ctx.createRadialGradient(cx, cy, 60, cx, cy, 260);
  grad.addColorStop(0, glowColor);
  grad.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, w, h);

  // 1. Outermost Ring with Segment Ticks
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(rotationRing1);
  ctx.strokeStyle = "rgba(0, 240, 255, 0.25)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(0, 0, 230, 0, Math.PI * 2);
  ctx.stroke();

  const numTicks = 60;
  for (let i = 0; i < numTicks; i++) {
    const angle = (i * Math.PI * 2) / numTicks;
    const len = i % 5 === 0 ? 14 : 6;
    ctx.strokeStyle = i % 5 === 0 ? primaryColor : "rgba(0, 240, 255, 0.4)";
    ctx.lineWidth = i % 5 === 0 ? 3 : 1;
    ctx.beginPath();
    ctx.moveTo(Math.cos(angle) * (230 - len), Math.sin(angle) * (230 - len));
    ctx.lineTo(Math.cos(angle) * 230, Math.sin(angle) * 230);
    ctx.stroke();
  }
  ctx.restore();

  // 2. Middle Counter-Rotating Gear Ring
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(rotationRing2);
  ctx.strokeStyle = primaryColor;
  ctx.lineWidth = 3;
  ctx.shadowColor = primaryColor;
  ctx.shadowBlur = 15;

  const numArcs = 8;
  for (let i = 0; i < numArcs; i++) {
    const start = (i * Math.PI * 2) / numArcs;
    const end = start + (Math.PI / numArcs) * 0.7;
    ctx.beginPath();
    ctx.arc(0, 0, 185, start, end);
    ctx.stroke();

    // Node dots
    const dotAngle = start + (Math.PI / numArcs) * 0.35;
    ctx.fillStyle = "#ffffff";
    ctx.beginPath();
    ctx.arc(Math.cos(dotAngle) * 185, Math.sin(dotAngle) * 185, 3, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();

  // 3. Audio Frequency Waveform Radiators (during speaking/listening)
  ctx.save();
  ctx.translate(cx, cy);
  const numBars = 32;
  for (let i = 0; i < numBars; i++) {
    const angle = (i * Math.PI * 2) / numBars;
    const barVal = (audioFreqData[i % 32] / 255) || (avgFreq * 0.8);
    const barLen = 140 + barVal * 40;
    
    ctx.strokeStyle = primaryColor;
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(Math.cos(angle) * 140, Math.sin(angle) * 140);
    ctx.lineTo(Math.cos(angle) * barLen, Math.sin(angle) * barLen);
    ctx.stroke();
  }
  ctx.restore();

  // 4. Inner Ring with Hexagon / Triangles
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(rotationRing3);
  ctx.strokeStyle = "rgba(0, 240, 255, 0.5)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(0, 0, 120, 0, Math.PI * 2);
  ctx.stroke();

  // 3 Triangular core struts
  for (let i = 0; i < 3; i++) {
    const angle = (i * Math.PI * 2) / 3;
    ctx.strokeStyle = primaryColor;
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(Math.cos(angle) * 60, Math.sin(angle) * 60);
    ctx.lineTo(Math.cos(angle) * 120, Math.sin(angle) * 120);
    ctx.stroke();
  }
  ctx.restore();

  // 5. Central Pulsing Core
  const pulse = Math.sin(Date.now() / 300) * 4 + (avgFreq * 16);
  const coreRadius = Math.max(20, 48 + pulse);
  
  const coreGrad = ctx.createRadialGradient(cx, cy, 5, cx, cy, coreRadius);
  coreGrad.addColorStop(0, "#ffffff");
  coreGrad.addColorStop(0.4, primaryColor);
  coreGrad.addColorStop(1, "rgba(0, 240, 255, 0)");

  ctx.fillStyle = coreGrad;
  ctx.beginPath();
  ctx.arc(cx, cy, coreRadius, 0, Math.PI * 2);
  ctx.fill();

  requestAnimationFrame(drawArcReactor);
}

// ============================================================================
// STARK HOLOGRAPHIC INTELLIGENCE CORE — 3D WIREFRAME IRON MAN HELMET & ORBITAL
// ============================================================================
let _holoCanvas = null;
let _holoCtx = null;
let _holoRotX = 0;
let _holoRotY = 0;
let _holoRotZ = 0;
let _holoParticles = [];
let _holoShockwaves = [];
let _holoAnimFrame = null;
let _holoMode = "helmet"; // "helmet", "arc", "globe"
let _holoScale = 235;
let _holoTargetScale = 235;
let _isDraggingHolo = false;
let _holoDragStartX = 0;
let _holoDragStartY = 0;
let _holoVelX = 0;
let _holoVelY = 0;
let _holoManualRotX = 0;
let _holoManualRotY = 0;
let _holoTheme = localStorage.getItem("jarvis_tactical_theme") || "mark-xvi";
let _soundFxEnabled = localStorage.getItem("jarvis_sound_fx") !== "false";

const HUD_THEMES = {
  "mark-xvi": { name: "MARK XVI TACTICAL", icon: "⚡", primary: "#00f0ff", glow: "rgba(0, 240, 255, 0.6)", bodyClass: "" },
  "war-machine": { name: "WAR MACHINE OVERCLOCK", icon: "🔴", primary: "#ff1744", glow: "rgba(255, 23, 68, 0.7)", bodyClass: "theme-war-machine" },
  "stealth-obsidian": { name: "STEALTH OBSIDIAN", icon: "🟢", primary: "#00e676", glow: "rgba(0, 230, 118, 0.7)", bodyClass: "theme-stealth-obsidian" },
  "neural-matrix": { name: "NEURAL MATRIX", icon: "🟣", primary: "#d500f9", glow: "rgba(213, 0, 249, 0.7)", bodyClass: "theme-neural-matrix" }
};

// 3D Helmet Vertices [x, y, z] (Symmetric canonical Iron Man mesh)
const HELMET_VERTICES = [
  // Jaw & Chin
  [0, 52, 28], [-14, 50, 24], [14, 50, 24], [-28, 36, 12], [28, 36, 12],
  [-38, 14, -2], [38, 14, -2],
  // Mouth
  [-12, 36, 26], [12, 36, 26], [-10, 42, 26], [10, 42, 26],
  // Cheeks
  [-16, 20, 28], [16, 20, 28], [-34, 18, 16], [34, 18, 16],
  [-22, 6, 26], [22, 6, 26],
  // Nose Bridge & Crest
  [0, 18, 32], [0, 4, 30], [0, -8, 28],
  // Eye Slit Loops (Left Eye)
  [-25, -4, 25], [-8, -4, 28], [-9, 1, 28], [-23, 1, 25],
  // Eye Slit Loops (Right Eye)
  [8, -4, 28], [25, -4, 25], [23, 1, 25], [9, 1, 28],
  // Brow Ridge
  [-14, -14, 28], [14, -14, 28], [-32, -10, 18], [32, -10, 18],
  // Forehead & Crest
  [0, -28, 26], [-16, -26, 23], [16, -26, 23],
  [0, -46, 18], [-14, -44, 15], [14, -44, 15],
  // Cranium Dome
  [0, -56, 4], [-20, -54, 2], [20, -54, 2],
  [-38, -22, 6], [38, -22, 6],
  // Ear Pods (Receptors)
  [-42, 10, -4], [42, 10, -4],
  // Skull Rear / Depth
  [-24, -48, -18], [0, -50, -18], [24, -48, -18],
  [-30, -18, -26], [0, -20, -28], [30, -18, -26],
  [-22, 22, -20], [0, 24, -22], [22, 22, -20]
];

// Edges connecting vertex indices
const HELMET_EDGES = [
  // Chin & Jawline
  [0, 1], [0, 2], [1, 3], [2, 4], [3, 5], [4, 6], [5, 43], [6, 44],
  // Mouth
  [7, 8], [9, 10], [7, 9], [8, 10], [9, 1], [10, 2],
  // Cheeks & Nose
  [17, 18], [18, 19], [17, 11], [17, 12],
  [11, 13], [12, 14], [13, 3], [14, 4],
  [15, 11], [16, 12], [11, 7], [12, 8],
  // Brow & Eyes
  [19, 29], [19, 30], [29, 31], [30, 32],
  [31, 15], [32, 16], [5, 41], [6, 42],
  [41, 31], [42, 32],
  // Forehead & Crest
  [19, 33], [33, 36], [29, 34], [30, 35],
  [34, 37], [35, 38], [37, 36], [38, 36],
  [41, 34], [42, 35],
  // Cranium Dome
  [36, 39], [37, 40], [38, 41],
  [39, 46], [40, 45], [41, 47],
  [45, 46], [46, 47],
  // Skull Rear
  [45, 48], [46, 49], [47, 50],
  [48, 49], [49, 50],
  [48, 51], [49, 52], [50, 53],
  [51, 52], [52, 53],
  [43, 48], [44, 50],
  [5, 51], [6, 53]
];

// Eye loop polygon indices
const LEFT_EYE_LOOP = [20, 21, 22, 23];
const RIGHT_EYE_LOOP = [24, 25, 26, 27];

// Project 3D point (x,y,z) with pitch, yaw, roll to 2D screen
function project3D(x, y, z, cx, cy, rotX, rotY, rotZ, scale, dist) {
  // Yaw (Y-axis rotation)
  const cosY = Math.cos(rotY), sinY = Math.sin(rotY);
  const x1 = x * cosY + z * sinY;
  const z1 = -x * sinY + z * cosY;

  // Pitch (X-axis rotation)
  const cosX = Math.cos(rotX), sinX = Math.sin(rotX);
  const y1 = y * cosX - z1 * sinX;
  const z2 = y * sinX + z1 * cosX;

  // Roll (Z-axis rotation)
  const cosZ = Math.cos(rotZ), sinZ = Math.sin(rotZ);
  const x2 = x1 * cosZ - y1 * sinZ;
  const y2 = x1 * sinZ + y1 * cosZ;

  const k = scale / (z2 + dist);
  return { x: cx + x2 * k, y: cy + y2 * k, z: z2, k: k };
}

function initHologramCore() {
  _holoCanvas = document.getElementById("refHologramCanvas");
  if (!_holoCanvas) return;
  _holoCtx = _holoCanvas.getContext("2d");
  if (!_holoCtx) return;

  // Generate 60 ambient drifting holographic particles
  _holoParticles = [];
  for (let i = 0; i < 60; i++) {
    _holoParticles.push({
      x: (Math.random() - 0.5) * 500,
      y: (Math.random() - 0.5) * 300,
      z: (Math.random() - 0.5) * 200,
      vx: (Math.random() - 0.5) * 0.35,
      vy: (Math.random() - 0.5) * 0.35,
      vz: (Math.random() - 0.5) * 0.35,
      size: Math.random() * 1.6 + 0.6,
      alpha: Math.random() * 0.5 + 0.25
    });
  }

  // Interactive Orbit Drag & Physics Inertia
  _holoCanvas.addEventListener("pointerdown", (e) => {
    _isDraggingHolo = true;
    _holoDragStartX = e.clientX;
    _holoDragStartY = e.clientY;
    _holoVelX = 0;
    _holoVelY = 0;
    _holoCanvas.classList.add("grabbing");
    try { _holoCanvas.setPointerCapture(e.pointerId); } catch(err) {}
    playSynthSound("click");
  });

  _holoCanvas.addEventListener("pointermove", (e) => {
    if (!_isDraggingHolo) return;
    const dx = e.clientX - _holoDragStartX;
    const dy = e.clientY - _holoDragStartY;
    _holoVelY = dx * 0.007;
    _holoVelX = dy * 0.007;
    _holoManualRotY += _holoVelY;
    _holoManualRotX += _holoVelX;
    _holoManualRotX = Math.max(-1.1, Math.min(1.1, _holoManualRotX));
    _holoDragStartX = e.clientX;
    _holoDragStartY = e.clientY;
  });

  const stopHoloDrag = (e) => {
    if (_isDraggingHolo) {
      _isDraggingHolo = false;
      _holoCanvas.classList.remove("grabbing");
      try { _holoCanvas.releasePointerCapture(e.pointerId); } catch(err) {}
    }
  };
  _holoCanvas.addEventListener("pointerup", stopHoloDrag);
  _holoCanvas.addEventListener("pointercancel", stopHoloDrag);
  _holoCanvas.addEventListener("pointerleave", stopHoloDrag);

  _holoCanvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    _holoTargetScale = Math.max(140, Math.min(360, _holoTargetScale - e.deltaY * 0.25));
  }, { passive: false });

  _holoCanvas.addEventListener("dblclick", () => {
    _holoManualRotX = 0;
    _holoManualRotY = 0;
    _holoTargetScale = 235;
    _holoShockwaves.push({ r: 15, maxR: 220, alpha: 1.0 });
    playSynthSound("arc_pulse");
  });

  // Apply initial theme
  applyHudTheme(_holoTheme, false);

  if (_holoAnimFrame) cancelAnimationFrame(_holoAnimFrame);
  _holoAnimFrame = requestAnimationFrame(renderIronManHologram);
}

function renderIronManHologram() {
  if (!_holoCanvas || !_holoCtx) return;

  // Auto-sync canvas resolution to element client dimensions
  const rect = _holoCanvas.getBoundingClientRect();
  if (rect.width > 20 && (_holoCanvas.width !== Math.floor(rect.width) || _holoCanvas.height !== Math.floor(rect.height))) {
    _holoCanvas.width = Math.floor(rect.width);
    _holoCanvas.height = Math.floor(rect.height);
  }

  const w = _holoCanvas.width;
  const h = _holoCanvas.height;
  const cx = w / 2;
  const cy = h / 2 - 8;

  _holoCtx.clearRect(0, 0, w, h);

  const t = Date.now() / 1000;
  
  // Real Web Audio API frequency analysis
  let audioAmp = 0;
  let bassFreq = 0;
  let midFreq = 0;
  let trebleFreq = 0;

  if (analyser) {
    try {
      analyser.getByteFrequencyData(audioFreqData);
      let bSum = 0, mSum = 0, tSum = 0;
      for (let i = 0; i < 8; i++) bSum += audioFreqData[i];
      for (let i = 8; i < 24; i++) mSum += audioFreqData[i];
      for (let i = 24; i < 48; i++) tSum += audioFreqData[i];
      bassFreq = (bSum / 8) / 255;
      midFreq = (mSum / 16) / 255;
      trebleFreq = (tSum / 24) / 255;
      audioAmp = (bassFreq * 0.5 + midFreq * 0.35 + trebleFreq * 0.15);
    } catch(e) {}
  }

  // Natural synthetic audio animation if audio input is idle
  if (audioAmp < 0.04) {
    if (state.status === "speaking") {
      audioAmp = 0.28 + Math.sin(t * 14) * 0.14 + Math.cos(t * 20) * 0.08;
      bassFreq = audioAmp * 1.1;
      midFreq = audioAmp * 0.9;
      trebleFreq = audioAmp * 0.8;
    } else if (state.status === "listening") {
      audioAmp = 0.12 + Math.sin(t * 7) * 0.06;
      bassFreq = audioAmp * 0.8;
      midFreq = audioAmp;
    }
  }

  // Smooth scale interpolation (Zoom)
  _holoScale += (_holoTargetScale - _holoScale) * 0.1;

  // Inertia and rotation
  if (!_isDraggingHolo) {
    _holoManualRotX *= 0.95;
    _holoVelY *= 0.94;
    _holoManualRotY += _holoVelY;
    _holoRotY += 0.006 + _holoManualRotY * 0.3;
    _holoRotX = Math.sin(t * 0.7) * 0.12 + _holoManualRotX;
  } else {
    _holoRotY += _holoVelY;
    _holoRotX = _holoManualRotX;
  }
  _holoRotZ = Math.cos(t * 0.5) * 0.04;

  // Get active theme colors
  const themeObj = HUD_THEMES[_holoTheme] || HUD_THEMES["mark-xvi"];
  const primaryColor = themeObj.primary;
  const glowColor = themeObj.glow;

  // 1. Drifting background holographic dust/stars
  _holoParticles.forEach(p => {
    p.x += p.vx * (1 + trebleFreq * 1.2);
    p.y += p.vy * (1 + trebleFreq * 1.2);
    p.z += p.vz;
    if (p.x < -250) p.x = 250;
    if (p.x > 250) p.x = -250;
    if (p.y < -150) p.y = 150;
    if (p.y > 150) p.y = -150;
    if (p.z < -100) p.z = 100;
    if (p.z > 100) p.z = -100;

    const pt = project3D(p.x, p.y, p.z, cx, cy, _holoRotX * 0.3, _holoRotY * 0.3, 0, 240, 280);
    _holoCtx.beginPath();
    _holoCtx.arc(pt.x, pt.y, p.size * pt.k * 0.8, 0, Math.PI * 2);
    _holoCtx.fillStyle = primaryColor;
    _holoCtx.globalAlpha = p.alpha * 0.7;
    _holoCtx.fill();
    _holoCtx.globalAlpha = 1.0;
  });

  // 2. Holographic Circuit Ring Base / Floor Halo (Bass-Reactive)
  const floorY = 66;
  const floorRadii = [45, 80, 115, 140];
  floorRadii.forEach((fr, fIdx) => {
    const dynR = fr * (1 + bassFreq * 0.12);
    _holoCtx.beginPath();
    const segs = 36;
    for (let s = 0; s <= segs; s++) {
      const angle = (s / segs) * Math.PI * 2;
      const fx = Math.cos(angle) * dynR;
      const fz = Math.sin(angle) * dynR;
      const fpt = project3D(fx, floorY, fz, cx, cy, 0.45, 0, 0, 240, 270);
      if (s === 0) _holoCtx.moveTo(fpt.x, fpt.y);
      else _holoCtx.lineTo(fpt.x, fpt.y);
    }
    _holoCtx.strokeStyle = (fIdx % 2 === 0) ? primaryColor : "rgba(255, 171, 0, 0.25)";
    _holoCtx.globalAlpha = (fIdx % 2 === 0) ? 0.35 + bassFreq * 0.3 : 0.2;
    _holoCtx.setLineDash((fIdx === 1) ? [4, 6] : (fIdx === 3) ? [2, 4] : []);
    _holoCtx.lineWidth = 1;
    _holoCtx.stroke();
    _holoCtx.setLineDash([]);
    _holoCtx.globalAlpha = 1.0;
  });

  // Rotating Radar Floor Sweep
  const sweepAngle = (t * 1.8) % (Math.PI * 2);
  const swX = Math.cos(sweepAngle) * 135;
  const swZ = Math.sin(sweepAngle) * 135;
  const pCenter = project3D(0, floorY, 0, cx, cy, 0.45, 0, 0, 240, 270);
  const pEdge = project3D(swX, floorY, swZ, cx, cy, 0.45, 0, 0, 240, 270);
  _holoCtx.beginPath();
  _holoCtx.moveTo(pCenter.x, pCenter.y);
  _holoCtx.lineTo(pEdge.x, pEdge.y);
  _holoCtx.strokeStyle = primaryColor;
  _holoCtx.globalAlpha = 0.5 + bassFreq * 0.3;
  _holoCtx.lineWidth = 1.2;
  _holoCtx.stroke();
  _holoCtx.globalAlpha = 1.0;

  // 3. Audio shockwave rings
  if ((state.status === "speaking" || bassFreq > 0.4) && Math.random() < 0.18) {
    _holoShockwaves.push({ r: 25, maxR: 160 + bassFreq * 60, alpha: 0.85 });
  }
  for (let i = _holoShockwaves.length - 1; i >= 0; i--) {
    const sw = _holoShockwaves[i];
    sw.r += 3.2;
    sw.alpha *= 0.93;
    _holoCtx.beginPath();
    _holoCtx.arc(cx, cy, sw.r, 0, Math.PI * 2);
    _holoCtx.strokeStyle = primaryColor;
    _holoCtx.globalAlpha = sw.alpha * 0.6;
    _holoCtx.lineWidth = 1.4;
    _holoCtx.stroke();
    _holoCtx.globalAlpha = 1.0;
    if (sw.alpha < 0.02 || sw.r >= sw.maxR) {
      _holoShockwaves.splice(i, 1);
    }
  }

  // ==========================================
  // BRANCH BY ACTIVE HOLOGRAM MODE
  // ==========================================
  if (_holoMode === "arc") {
    // ----------------------------------------
    // MODE: HYPER-ROTATING ARC REACTOR CORE
    // ----------------------------------------
    const rotSpeed1 = t * 0.8 + _holoManualRotY;
    const rotSpeed2 = -t * 1.2 + _holoManualRotY;

    // Outer gear ring
    _holoCtx.save();
    _holoCtx.translate(cx, cy);
    _holoCtx.rotate(rotSpeed1);
    _holoCtx.strokeStyle = primaryColor;
    _holoCtx.lineWidth = 2.5;
    _holoCtx.shadowColor = primaryColor;
    _holoCtx.shadowBlur = 12;
    _holoCtx.beginPath();
    _holoCtx.arc(0, 0, 115 + bassFreq * 10, 0, Math.PI * 2);
    _holoCtx.stroke();

    // 24 Radial ticks
    for (let i = 0; i < 24; i++) {
      const a = (i / 24) * Math.PI * 2;
      const r1 = 115 + bassFreq * 10;
      const r2 = r1 - (i % 2 === 0 ? 14 : 7);
      _holoCtx.beginPath();
      _holoCtx.moveTo(Math.cos(a) * r1, Math.sin(a) * r1);
      _holoCtx.lineTo(Math.cos(a) * r2, Math.sin(a) * r2);
      _holoCtx.stroke();
    }
    _holoCtx.restore();

    // Inner counter-rotating segmented ring
    _holoCtx.save();
    _holoCtx.translate(cx, cy);
    _holoCtx.rotate(rotSpeed2);
    _holoCtx.strokeStyle = "#ffffff";
    _holoCtx.lineWidth = 3;
    for (let i = 0; i < 8; i++) {
      const start = (i / 8) * Math.PI * 2;
      const end = start + (Math.PI / 8) * 0.7;
      _holoCtx.beginPath();
      _holoCtx.arc(0, 0, 85, start, end);
      _holoCtx.stroke();
    }
    _holoCtx.restore();

    // Central Plasma Iris Core
    const irisR = 38 + audioAmp * 22;
    const grad = _holoCtx.createRadialGradient(cx, cy, 5, cx, cy, irisR);
    grad.addColorStop(0, "#ffffff");
    grad.addColorStop(0.4, primaryColor);
    grad.addColorStop(1, "rgba(0,0,0,0)");
    _holoCtx.fillStyle = grad;
    _holoCtx.beginPath();
    _holoCtx.arc(cx, cy, irisR, 0, Math.PI * 2);
    _holoCtx.fill();

  } else if (_holoMode === "globe") {
    // ----------------------------------------
    // MODE: TACTICAL GLOBAL INTELLIGENCE GRID
    // ----------------------------------------
    const globeR = 105 + midFreq * 12;
    const lats = [-60, -35, 0, 35, 60];
    
    // Latitude parallels
    lats.forEach(latY => {
      const latR = Math.sqrt(Math.max(0, globeR * globeR - latY * latY));
      _holoCtx.beginPath();
      const segs = 32;
      for (let s = 0; s <= segs; s++) {
        const a = (s / segs) * Math.PI * 2;
        const sx = Math.cos(a) * latR;
        const sz = Math.sin(a) * latR;
        const pt = project3D(sx, latY, sz, cx, cy, _holoRotX, _holoRotY, _holoRotZ, _holoScale, 270);
        if (s === 0) _holoCtx.moveTo(pt.x, pt.y);
        else _holoCtx.lineTo(pt.x, pt.y);
      }
      _holoCtx.strokeStyle = primaryColor;
      _holoCtx.globalAlpha = 0.25;
      _holoCtx.lineWidth = 1;
      _holoCtx.stroke();
      _holoCtx.globalAlpha = 1.0;
    });

    // 8 Longitude great circles
    for (let l = 0; l < 8; l++) {
      const lAngle = (l / 8) * Math.PI;
      _holoCtx.beginPath();
      const segs = 32;
      for (let s = 0; s <= segs; s++) {
        const a = (s / segs) * Math.PI * 2;
        const sx = Math.sin(a) * Math.cos(lAngle) * globeR;
        const sy = Math.cos(a) * globeR;
        const sz = Math.sin(a) * Math.sin(lAngle) * globeR;
        const pt = project3D(sx, sy, sz, cx, cy, _holoRotX, _holoRotY, _holoRotZ, _holoScale, 270);
        if (s === 0) _holoCtx.moveTo(pt.x, pt.y);
        else _holoCtx.lineTo(pt.x, pt.y);
      }
      _holoCtx.strokeStyle = primaryColor;
      _holoCtx.globalAlpha = 0.28;
      _holoCtx.lineWidth = 1;
      _holoCtx.stroke();
      _holoCtx.globalAlpha = 1.0;
    }

    // Orbiting tactical satellite nodes
    for (let sat = 0; sat < 4; sat++) {
      const satAngle = t * 1.2 + sat * 1.57;
      const satR = globeR + 25;
      const satX = Math.cos(satAngle) * satR;
      const satZ = Math.sin(satAngle) * satR;
      const satY = Math.sin(satAngle * 1.5) * 40;
      const spt = project3D(satX, satY, satZ, cx, cy, _holoRotX, _holoRotY, _holoRotZ, _holoScale, 270);
      _holoCtx.beginPath();
      _holoCtx.arc(spt.x, spt.y, 3, 0, Math.PI * 2);
      _holoCtx.fillStyle = "#ffffff";
      _holoCtx.shadowColor = primaryColor;
      _holoCtx.shadowBlur = 10;
      _holoCtx.fill();
      _holoCtx.shadowBlur = 0;
    }

  } else {
    // ----------------------------------------
    // MODE: 3D WIREFRAME IRON MAN HELMET (DEFAULT)
    // ----------------------------------------
    // Geodesic Wireframe Globe Encircling the Helmet
    const sphereR = 92;
    const sphereLats = [-55, -28, 0, 28, 55];
    sphereLats.forEach(latY => {
      const latR = Math.sqrt(Math.max(0, sphereR * sphereR - latY * latY));
      _holoCtx.beginPath();
      const segs = 32;
      for (let s = 0; s <= segs; s++) {
        const a = (s / segs) * Math.PI * 2;
        const sx = Math.cos(a) * latR;
        const sz = Math.sin(a) * latR;
        const pt = project3D(sx, latY, sz, cx, cy, _holoRotX * 0.4, _holoRotY * 0.5, _holoRotZ * 0.3, 240, 270);
        if (s === 0) _holoCtx.moveTo(pt.x, pt.y);
        else _holoCtx.lineTo(pt.x, pt.y);
      }
      _holoCtx.strokeStyle = primaryColor;
      _holoCtx.globalAlpha = 0.12;
      _holoCtx.lineWidth = 0.8;
      _holoCtx.stroke();
      _holoCtx.globalAlpha = 1.0;
    });

    // 3D Orbital Rings around Helmet
    const orbitalRings = [
      { r: 96, y: -24, tiltX: 0.12, tiltZ: 0.18, speed: 1.0 },
      { r: 106, y: 0, tiltX: 0.38, tiltZ: -0.28, speed: -1.2 },
      { r: 96, y: 24, tiltX: -0.22, tiltZ: 0.32, speed: 0.85 }
    ];

    orbitalRings.forEach((ring, idx) => {
      _holoCtx.beginPath();
      const segments = 36;
      for (let s = 0; s <= segments; s++) {
        const angle = (s / segments) * Math.PI * 2;
        const rx = Math.cos(angle) * ring.r;
        const rz = Math.sin(angle) * ring.r;
        const ry = ring.y;
        const pt = project3D(rx, ry, rz, cx, cy, _holoRotX + ring.tiltX, _holoRotY * ring.speed, ring.tiltZ, 250, 270);
        if (s === 0) _holoCtx.moveTo(pt.x, pt.y);
        else _holoCtx.lineTo(pt.x, pt.y);
      }
      _holoCtx.strokeStyle = primaryColor;
      _holoCtx.globalAlpha = 0.28;
      _holoCtx.lineWidth = 1;
      _holoCtx.stroke();
      _holoCtx.globalAlpha = 1.0;

      // Orbiting quantum spark
      const sparkAngle = (t * ring.speed * 1.5 + idx * 2.1) % (Math.PI * 2);
      const sx = Math.cos(sparkAngle) * ring.r;
      const sz = Math.sin(sparkAngle) * ring.r;
      const spt = project3D(sx, ring.y, sz, cx, cy, _holoRotX + ring.tiltX, _holoRotY * ring.speed, ring.tiltZ, 250, 270);
      _holoCtx.beginPath();
      _holoCtx.arc(spt.x, spt.y, 2.5, 0, Math.PI * 2);
      _holoCtx.fillStyle = "#ffffff";
      _holoCtx.shadowColor = primaryColor;
      _holoCtx.shadowBlur = 10;
      _holoCtx.fill();
      _holoCtx.shadowBlur = 0;
    });

    // Project 3D Helmet Vertices (Mid-frequency harmonic deformation)
    const scale = _holoScale * (1 + midFreq * 0.14);
    const dist = 270;
    const projectedVerts = HELMET_VERTICES.map(v => {
      return project3D(v[0], v[1], v[2], cx, cy, _holoRotX, _holoRotY, _holoRotZ, scale, dist);
    });

    // Draw Iron Man Wireframe Edges
    _holoCtx.beginPath();
    HELMET_EDGES.forEach(([i1, i2]) => {
      const p1 = projectedVerts[i1];
      const p2 = projectedVerts[i2];
      if (p1 && p2) {
        _holoCtx.moveTo(p1.x, p1.y);
        _holoCtx.lineTo(p2.x, p2.y);
      }
    });

    _holoCtx.strokeStyle = primaryColor;
    _holoCtx.globalAlpha = (state.status === "speaking" || state.status === "listening") ? 0.95 : 0.75;
    _holoCtx.lineWidth = 1.35;
    _holoCtx.shadowColor = primaryColor;
    _holoCtx.shadowBlur = 8 + audioAmp * 12;
    _holoCtx.stroke();
    _holoCtx.shadowBlur = 0;
    _holoCtx.globalAlpha = 1.0;

    // Draw Glowing Eye Slits (Treble-Reactive Flare)
    function renderEyeLoop(indices) {
      _holoCtx.beginPath();
      indices.forEach((idx, i) => {
        const p = projectedVerts[idx];
        if (p) {
          if (i === 0) _holoCtx.moveTo(p.x, p.y);
          else _holoCtx.lineTo(p.x, p.y);
        }
      });
      _holoCtx.closePath();

      const eyeGlow = 0.8 + trebleFreq * 0.6;
      _holoCtx.fillStyle = `rgba(255, 255, 255, ${Math.min(1.0, eyeGlow)})`;
      _holoCtx.shadowColor = primaryColor;
      _holoCtx.shadowBlur = 16 + trebleFreq * 20;
      _holoCtx.fill();
      _holoCtx.strokeStyle = "#ffffff";
      _holoCtx.lineWidth = 1.4;
      _holoCtx.stroke();
      _holoCtx.shadowBlur = 0;
    }

    renderEyeLoop(LEFT_EYE_LOOP);
    renderEyeLoop(RIGHT_EYE_LOOP);
  }

  _holoAnimFrame = requestAnimationFrame(renderIronManHologram);
}

// ============================================================================
// HOLOGRAPHIC MODE SWITCHER
// ============================================================================
function setHologramMode(mode) {
  _holoMode = mode;
  const modes = ["helmet", "arc", "globe"];
  modes.forEach(m => {
    const btn = document.getElementById("btnHolo" + m.charAt(0).toUpperCase() + m.slice(1));
    if (btn) {
      if (m === mode) btn.classList.add("active");
      else btn.classList.remove("active");
    }
  });
  _holoShockwaves.push({ r: 15, maxR: 200, alpha: 1.0 });
  playSynthSound("arc_pulse");
}

// ============================================================================
// TACTICAL THEME ENGINE
// ============================================================================
function cycleHudTheme() {
  const keys = Object.keys(HUD_THEMES);
  const curIdx = keys.indexOf(_holoTheme);
  const nextKey = keys[(curIdx + 1) % keys.length];
  applyHudTheme(nextKey);
  playSynthSound("click");
}

function applyHudTheme(themeKey, notify = true) {
  if (!HUD_THEMES[themeKey]) themeKey = "mark-xvi";
  _holoTheme = themeKey;
  localStorage.setItem("jarvis_tactical_theme", themeKey);

  // Clear existing theme classes
  document.body.classList.remove("theme-war-machine", "theme-stealth-obsidian", "theme-neural-matrix");
  if (HUD_THEMES[themeKey].bodyClass) {
    document.body.classList.add(HUD_THEMES[themeKey].bodyClass);
  }

  const lbl = document.getElementById("labelTheme");
  const icon = document.getElementById("themePillIcon");
  if (lbl) lbl.textContent = `THEME: ${HUD_THEMES[themeKey].name.split(" ")[0]}`;
  if (icon) icon.textContent = HUD_THEMES[themeKey].icon;

  if (notify) {
    appendLog("info", "THEME", `Tactical HUD Theme calibrated: ${HUD_THEMES[themeKey].name}`);
  }
}

// ============================================================================
// STARK SOUNDSCAPE ENGINE (0ms Procedural Web Audio Synthesis)
// ============================================================================
function playSynthSound(type = "click") {
  if (!_soundFxEnabled) return;
  try {
    initAudioContext();
    if (!audioCtx) return;
    const now = audioCtx.currentTime;
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain);
    gain.connect(audioCtx.destination);

    if (type === "click") {
      osc.type = "sine";
      osc.frequency.setValueAtTime(1400, now);
      osc.frequency.exponentialRampToValueAtTime(450, now + 0.035);
      gain.gain.setValueAtTime(0.06, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.035);
      osc.start(now);
      osc.stop(now + 0.035);
    } else if (type === "arc_pulse") {
      osc.type = "triangle";
      osc.frequency.setValueAtTime(120, now);
      osc.frequency.exponentialRampToValueAtTime(550, now + 0.16);
      gain.gain.setValueAtTime(0.12, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.18);
      osc.start(now);
      osc.stop(now + 0.18);
    } else if (type === "success") {
      osc.type = "sine";
      osc.frequency.setValueAtTime(523, now); // C5
      osc.frequency.setValueAtTime(659, now + 0.05); // E5
      osc.frequency.setValueAtTime(784, now + 0.1); // G5
      gain.gain.setValueAtTime(0.08, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.18);
      osc.start(now);
      osc.stop(now + 0.18);
    } else if (type === "alert") {
      osc.type = "sawtooth";
      osc.frequency.setValueAtTime(440, now);
      osc.frequency.setValueAtTime(330, now + 0.08);
      gain.gain.setValueAtTime(0.08, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.16);
      osc.start(now);
      osc.stop(now + 0.16);
    }
  } catch(e) {}
}

function toggleAudioFx() {
  _soundFxEnabled = !_soundFxEnabled;
  localStorage.setItem("jarvis_sound_fx", _soundFxEnabled ? "true" : "false");
  const lbl = document.getElementById("labelAudioFx");
  if (lbl) lbl.textContent = `FX: ${_soundFxEnabled ? "ON" : "OFF"}`;
  if (_soundFxEnabled) playSynthSound("success");
}

// ============================================================================
// CYBERNETIC TERMINAL DRAWER CONTROLLER
// ============================================================================
function toggleTerminalDrawer(forceState = null) {
  const drawer = document.getElementById("refTerminalDrawer");
  if (!drawer) return;
  const isOpen = forceState !== null ? forceState : !drawer.classList.contains("open");
  if (isOpen) {
    drawer.classList.add("open");
    playSynthSound("click");
    setTimeout(() => {
      const inp = document.getElementById("inpTerminalCmd");
      if (inp) inp.focus();
    }, 150);
  } else {
    drawer.classList.remove("open");
    playSynthSound("click");
  }
}

function clearTerminalLogs() {
  const feed = document.getElementById("refTerminalLogFeed");
  if (feed) {
    feed.innerHTML = '<div class="term-line sys">[SYSTEM] Log feed cleared. Terminal online.</div>';
    playSynthSound("click");
  }
}

async function executeTerminalInput() {
  const inp = document.getElementById("inpTerminalCmd");
  if (!inp || !inp.value.trim()) return;
  const cmd = inp.value.trim();
  inp.value = "";
  
  const feed = document.getElementById("refTerminalLogFeed");
  if (feed) {
    feed.innerHTML += `<div class="term-line cmd">&gt; ${escapeHtml(cmd)}</div>`;
    feed.scrollTop = feed.scrollHeight;
  }
  
  const badge = document.getElementById("terminalStatusBadge");
  if (badge) { badge.textContent = "RUNNING"; badge.style.color = "#ffb300"; }
  playSynthSound("click");

  try {
    const resp = await fetch("/api/terminal/exec", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command: cmd, timeout: 20 })
    });
    const data = await resp.json();
    if (badge) {
      badge.textContent = data.success ? "SUCCESS" : "ERROR";
      badge.style.color = data.success ? "#38ef7d" : "#ff5252";
    }
    
    if (feed) {
      if (data.stdout) feed.innerHTML += `<div class="term-line out">${escapeHtml(data.stdout)}</div>`;
      if (data.stderr) feed.innerHTML += `<div class="term-line err">${escapeHtml(data.stderr)}</div>`;
      if (!data.stdout && !data.stderr) feed.innerHTML += `<div class="term-line sys">[Process exited with code ${data.exit_code}]</div>`;
      feed.scrollTop = feed.scrollHeight;
    }
    if (data.success) playSynthSound("success");
    else playSynthSound("alert");
  } catch(e) {
    if (feed) feed.innerHTML += `<div class="term-line err">[COMMUNICATION ERROR] ${escapeHtml(String(e))}</div>`;
    playSynthSound("alert");
  }
}

// Bind Enter key on terminal input
document.addEventListener("DOMContentLoaded", () => {
  const termInput = document.getElementById("inpTerminalCmd");
  if (termInput) {
    termInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        executeTerminalInput();
      }
    });
  }
});

// ============================================================================
// SPOTLIGHT COMMAND PALETTE MODAL
// ============================================================================
const COMMAND_PALETTE_ITEMS = [
  { id: "term", title: "Open Cybernetic Terminal Drawer", category: "SYS", icon: "⬛", action: () => toggleTerminalDrawer(true) },
  { id: "lock", title: "Lock Workstation Display", category: "SYS", icon: "🔒", action: () => handleDirectWorkstationAction("lock") },
  { id: "mute", title: "Mute Master Audio", category: "SYS", icon: "🔇", action: () => handleDirectWorkstationAction("mute") },
  { id: "unmute", title: "Unmute Master Audio", category: "SYS", icon: "🔊", action: () => handleDirectWorkstationAction("unmute") },
  { id: "shot", title: "Capture Screen (Screenshot)", category: "SYS", icon: "📸", action: () => handleDirectWorkstationAction("screenshot") },
  { id: "vision", title: "Screen Vision: Analyze Current Display", category: "VISION", icon: "👁️", action: () => triggerScreenVisionAnalysis() },
  { id: "chrome", title: "Launch Dedicated Jarvis Browser", category: "APP", icon: "🧭", action: () => handleDirectWorkstationAction("launch", "chrome") },
  { id: "vscode", title: "Launch Visual Studio Code", category: "APP", icon: "💻", action: () => handleDirectWorkstationAction("launch", "code") },
  { id: "taskmgr", title: "Open Windows Task Manager", category: "APP", icon: "📊", action: () => handleDirectWorkstationAction("launch", "taskmgr") },
  { id: "theme_mark", title: "Tactical Theme: Mark XVI Arc Cyan", category: "THEME", icon: "⚡", action: () => applyHudTheme("mark-xvi") },
  { id: "theme_war", title: "Tactical Theme: War Machine Overclock", category: "THEME", icon: "🔴", action: () => applyHudTheme("war-machine") },
  { id: "theme_stealth", title: "Tactical Theme: Stealth Obsidian", category: "THEME", icon: "🟢", action: () => applyHudTheme("stealth-obsidian") },
  { id: "theme_neural", title: "Tactical Theme: Neural Matrix", category: "THEME", icon: "🟣", action: () => applyHudTheme("neural-matrix") },
  { id: "mode_helmet", title: "Center Hologram: 3D Helmet Wireframe", category: "HOLO", icon: "🤖", action: () => setHologramMode("helmet") },
  { id: "mode_arc", title: "Center Hologram: Arc Reactor Mark XVI", category: "HOLO", icon: "⚛️", action: () => setHologramMode("arc") },
  { id: "mode_globe", title: "Center Hologram: Planetary Intelligence Grid", category: "HOLO", icon: "🌐", action: () => setHologramMode("globe") },
  { id: "audio_matrix", title: "Configure Audio Devices (Mic & Speaker)", category: "AUDIO", icon: "🎧", action: () => openAudioMatrixModal() },
  { id: "agent_research", title: "Switch to Research Workspace", category: "AGENT", icon: "🌐", action: () => switchWorkspace("research") },
  { id: "agent_coding", title: "Switch to Coding & Development", category: "AGENT", icon: "💻", action: () => switchWorkspace("chat") },
  { id: "agent_marketing", title: "Switch to Business & Marketing Intel", category: "AGENT", icon: "📣", action: () => switchWorkspace("marketing") }
];

let _selectedPaletteIdx = 0;
let _filteredPaletteItems = [];

function openCommandPalette() {
  const modal = document.getElementById("refCmdPaletteModal");
  if (!modal) return;
  modal.style.display = "flex";
  playSynthSound("click");
  const inp = document.getElementById("inpPaletteQuery");
  if (inp) {
    inp.value = "";
    inp.focus();
  }
  renderPaletteResults("");
}

function closeCommandPalette() {
  const modal = document.getElementById("refCmdPaletteModal");
  if (modal) modal.style.display = "none";
}

function handlePaletteBackdropClick(e) {
  if (e.target && e.target.id === "refCmdPaletteModal") {
    closeCommandPalette();
  }
}

function renderPaletteResults(filter = "") {
  const container = document.getElementById("refPaletteResults");
  if (!container) return;
  const q = (filter || "").toLowerCase().trim();
  _filteredPaletteItems = COMMAND_PALETTE_ITEMS.filter(it => {
    return !q || it.title.toLowerCase().includes(q) || it.category.toLowerCase().includes(q);
  });
  _selectedPaletteIdx = 0;

  if (_filteredPaletteItems.length === 0) {
    container.innerHTML = '<div style="padding:14px; text-align:center; font-family:var(--font-mono); font-size:11px; color:#888;">No matching directives found.</div>';
    return;
  }

  container.innerHTML = _filteredPaletteItems.map((it, idx) => {
    return `
      <div class="ref-palette-item ${idx === 0 ? 'selected' : ''}" onclick="executePaletteItem(${idx})" data-idx="${idx}">
        <div class="ref-palette-item-left">
          <span class="ref-palette-item-icon">${it.icon}</span>
          <span class="ref-palette-item-title">${escapeHtml(it.title)}</span>
        </div>
        <span class="ref-palette-item-category">${it.category}</span>
      </div>
    `;
  }).join("");
}

function executePaletteItem(index) {
  if (index >= 0 && index < _filteredPaletteItems.length) {
    const item = _filteredPaletteItems[index];
    closeCommandPalette();
    playSynthSound("success");
    if (typeof item.action === "function") {
      item.action();
    }
  }
}

// Global Keyboard Navigation for Command Palette & Terminal
window.addEventListener("keydown", (e) => {
  // Toggle Terminal on ~
  if (e.key === "`" || e.key === "~") {
    const activeTag = document.activeElement ? document.activeElement.tagName : "";
    if (activeTag !== "INPUT" && activeTag !== "TEXTAREA") {
      e.preventDefault();
      toggleTerminalDrawer();
      return;
    }
  }

  // Spotlight Command Palette on Ctrl + K or Ctrl + Space
  if ((e.ctrlKey && (e.key === "k" || e.key === "K")) || (e.ctrlKey && e.code === "Space")) {
    e.preventDefault();
    const modal = document.getElementById("refCmdPaletteModal");
    if (modal && modal.style.display !== "none") {
      closeCommandPalette();
    } else {
      openCommandPalette();
    }
    return;
  }

  // Handle Palette modal navigation
  const paletteModal = document.getElementById("refCmdPaletteModal");
  if (paletteModal && paletteModal.style.display !== "none") {
    if (e.key === "Escape") {
      e.preventDefault();
      closeCommandPalette();
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (_filteredPaletteItems.length > 0) {
        _selectedPaletteIdx = (_selectedPaletteIdx + 1) % _filteredPaletteItems.length;
        updatePaletteSelectionDOM();
      }
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (_filteredPaletteItems.length > 0) {
        _selectedPaletteIdx = (_selectedPaletteIdx - 1 + _filteredPaletteItems.length) % _filteredPaletteItems.length;
        updatePaletteSelectionDOM();
      }
      return;
    }
    if (e.key === "Enter") {
      e.preventDefault();
      executePaletteItem(_selectedPaletteIdx);
      return;
    }
  }

  // Close Terminal on Escape if focused
  if (e.key === "Escape") {
    const drawer = document.getElementById("refTerminalDrawer");
    if (drawer && drawer.classList.contains("open")) {
      toggleTerminalDrawer(false);
    }
  }
});

function updatePaletteSelectionDOM() {
  const items = document.querySelectorAll(".ref-palette-item");
  items.forEach((it, idx) => {
    if (idx === _selectedPaletteIdx) {
      it.classList.add("selected");
      it.scrollIntoView({ block: "nearest" });
    } else {
      it.classList.remove("selected");
    }
  });
}

// Bind palette query input
document.addEventListener("DOMContentLoaded", () => {
  const pInput = document.getElementById("inpPaletteQuery");
  if (pInput) {
    pInput.addEventListener("input", (e) => {
      renderPaletteResults(e.target.value);
    });
  }
});

// ============================================================================
// SCREEN VISION TRIGGER & LOCAL CODE SANDBOX RUNNER
// ============================================================================
async function triggerScreenVisionAnalysis() {
  setAssistantStatus("thinking", "ANALYZING DISPLAY");
  appendLog("info", "VISION", "Screen Vision Copilot acquired visual capture. Analyzing...");
  playSynthSound("click");

  try {
    const res = await fetch("/api/vision/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: "inspect" })
    });
    const data = await res.json();
    if (data.success && data.analysis) {
      appendDedicatedChatMessage("jarvis", data.analysis, data.model_used);
      setAssistantStatus("idle", "ANALYSIS COMPLETE");
      playSynthSound("success");
    } else {
      appendLog("error", "VISION", data.error || "Vision analysis failed.");
      setAssistantStatus("idle", "VISION ERROR");
      playSynthSound("alert");
    }
  } catch(e) {
    appendLog("error", "VISION", String(e));
    setAssistantStatus("idle");
    playSynthSound("alert");
  }
}

async function executeSandboxCodeFromChat(btn) {
  const code = btn.getAttribute("data-code");
  const lang = btn.getAttribute("data-lang") || "python";
  if (!code) return;

  const card = btn.closest(".code-block-container");
  let outputBox = card ? card.querySelector(".sandbox-output-block") : null;
  if (!outputBox && card) {
    outputBox = document.createElement("div");
    outputBox.className = "sandbox-output-block";
    card.appendChild(outputBox);
  }

  btn.innerHTML = "⏳ RUNNING...";
  btn.disabled = true;
  playSynthSound("click");

  try {
    const resp = await fetch("/api/sandbox/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: code, language: lang, timeout: 15 })
    });
    const res = await resp.json();

    btn.innerHTML = "⚡ RUN LOCALLY";
    btn.disabled = false;

    if (outputBox) {
      outputBox.style.display = "block";
      const statusColor = res.success ? "#38ef7d" : "#ff5252";
      let html = `<div style="display:flex; justify-content:space-between; margin-bottom:4px; font-weight:bold; color:${statusColor}; font-size:10px;">
        <span>${res.success ? "✔ EXECUTED SUCCESSFULLY" : "✖ EXECUTION FAILED"}</span>
        <span>${res.duration_ms || 0}ms · Exit ${res.exit_code}</span>
      </div>`;
      if (res.stdout) html += `<div style="color:#e0f7fa; white-space:pre-wrap;">${escapeHtml(res.stdout)}</div>`;
      if (res.stderr) html += `<div style="color:#ff5252; white-space:pre-wrap; margin-top:4px;">${escapeHtml(res.stderr)}</div>`;
      outputBox.innerHTML = html;
    }

    if (res.success) playSynthSound("success");
    else playSynthSound("alert");
  } catch(e) {
    btn.innerHTML = "⚡ RUN LOCALLY";
    btn.disabled = false;
    if (outputBox) {
      outputBox.style.display = "block";
      outputBox.innerHTML = `<div style="color:#ff5252;">[Execution Error] ${escapeHtml(String(e))}</div>`;
    }
    playSynthSound("alert");
  }
}

// ============================================================================
// AGENT CONSTELLATION NETWORK RENDERER
// ============================================================================
const CONSTELLATION_NODES = [
  { id: "coding", label: "Coding", icon: "💻", color: "#00e5ff", angle: 0 },
  { id: "research", label: "Research", icon: "🌐", color: "#00e5ff", angle: 40 },
  { id: "qa", label: "QA Engine", icon: "🧪", color: "#38ef7d", angle: 80 },
  { id: "marketing", label: "Marketing", icon: "📣", color: "#ffab00", angle: 120 },
  { id: "seo", label: "SEO & Event", icon: "🎯", color: "#ffd600", angle: 160 },
  { id: "leadgen", label: "Lead Gen", icon: "📬", color: "#b388ff", angle: 200 },
  { id: "wordpress", label: "WordPress", icon: "🧩", color: "#40c4ff", angle: 240 },
  { id: "business", label: "Crypto/Biz", icon: "📊", color: "#ff9100", angle: 280 },
  { id: "system", label: "Windows OS", icon: "⚙️", color: "#00e5ff", angle: 320 }
];

let _constellationPulse = 0;
let _hoveredNode = null;
let _constellationAnimFrame = null;

function initConstellationGraph() {
  const canvas = document.getElementById("refConstellationCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  canvas.addEventListener("mousemove", (e) => {
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    let found = null;
    CONSTELLATION_NODES.forEach(n => {
      if (n._x && n._y && Math.hypot(mx - n._x, my - n._y) < 14) {
        found = n;
      }
    });
    _hoveredNode = found;
    canvas.style.cursor = found ? "pointer" : "default";
  });

  canvas.addEventListener("mouseleave", () => {
    _hoveredNode = null;
    canvas.style.cursor = "default";
  });

  canvas.addEventListener("click", () => {
    if (_hoveredNode) {
      playSound("ack");
      switchWorkspace("agents");
      const b = document.querySelector(`.spec-tab-btn[data-spec='${_hoveredNode.id}']`);
      if (b) b.click();
      showToast(`Selected Agent: ${_hoveredNode.label}`, "info", 2000);
    }
  });

  function animLoop() {
    renderConstellationGraph();
    _constellationAnimFrame = requestAnimationFrame(animLoop);
  }
  if (_constellationAnimFrame) cancelAnimationFrame(_constellationAnimFrame);
  _constellationAnimFrame = requestAnimationFrame(animLoop);
}

function renderConstellationGraph() {
  const canvas = document.getElementById("refConstellationCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const rect = canvas.getBoundingClientRect();
  if (rect.width > 20 && (canvas.width !== Math.floor(rect.width) || canvas.height !== Math.floor(rect.height))) {
    canvas.width = Math.floor(rect.width);
    canvas.height = Math.floor(rect.height);
  }

  const w = canvas.width;
  const h = canvas.height;
  const cx = w / 2;
  const cy = h / 2 - 2;

  ctx.clearRect(0, 0, w, h);
  _constellationPulse += 0.04;

  const rx = w * 0.38;
  const ry = h * 0.36;

  // 1. Draw Connecting Beams & Photon Pulses
  CONSTELLATION_NODES.forEach((node, idx) => {
    const rad = (node.angle * Math.PI) / 180;
    const nx = cx + rx * Math.cos(rad);
    const ny = cy + ry * Math.sin(rad);
    node._x = nx;
    node._y = ny;

    ctx.beginPath();
    ctx.setLineDash([3, 4]);
    ctx.moveTo(cx, cy);
    ctx.lineTo(nx, ny);
    ctx.strokeStyle = "rgba(0, 229, 255, 0.22)";
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.setLineDash([]);

    // Photon traveling on beam
    const progress = (_constellationPulse * 0.4 + idx * 0.22) % 1;
    const px = cx + (nx - cx) * progress;
    const py = cy + (ny - cy) * progress;
    ctx.beginPath();
    ctx.arc(px, py, 1.8, 0, Math.PI * 2);
    ctx.fillStyle = node.color;
    ctx.shadowColor = node.color;
    ctx.shadowBlur = 6;
    ctx.fill();
    ctx.shadowBlur = 0;
  });

  // 2. Draw Satellite Nodes
  CONSTELLATION_NODES.forEach((node) => {
    const isHovered = _hoveredNode === node;
    const radius = isHovered ? 10.5 : 8;

    ctx.beginPath();
    ctx.arc(node._x, node._y, radius + 3, 0, Math.PI * 2);
    ctx.fillStyle = isHovered ? "rgba(0, 229, 255, 0.35)" : "rgba(0, 229, 255, 0.08)";
    ctx.fill();

    ctx.beginPath();
    ctx.arc(node._x, node._y, radius, 0, Math.PI * 2);
    ctx.fillStyle = "#02121e";
    ctx.strokeStyle = node.color;
    ctx.lineWidth = isHovered ? 2 : 1.2;
    ctx.shadowColor = node.color;
    ctx.shadowBlur = isHovered ? 12 : 5;
    ctx.fill();
    ctx.stroke();
    ctx.shadowBlur = 0;

    ctx.font = isHovered ? "10px sans-serif" : "8.5px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(node.icon, node._x, node._y);

    // Node label under node
    ctx.font = isHovered ? "bold 8.5px var(--font-mono, monospace)" : "7.5px var(--font-mono, monospace)";
    ctx.fillStyle = isHovered ? "#ffffff" : "rgba(224, 247, 250, 0.8)";
    const labelY = (node._y > cy) ? node._y + 11 : node._y - 11;
    ctx.fillText(node.label, node._x, labelY);
  });

  // 3. Central Orchestrator Hub
  const hubRadius = 13 + Math.sin(_constellationPulse) * 1.5;
  ctx.beginPath();
  ctx.arc(cx, cy, hubRadius + 6, 0, Math.PI * 2);
  ctx.strokeStyle = "rgba(0, 229, 255, 0.3)";
  ctx.lineWidth = 1;
  ctx.stroke();

  ctx.beginPath();
  ctx.arc(cx, cy, hubRadius, 0, Math.PI * 2);
  const hubGrad = ctx.createRadialGradient(cx, cy, 2, cx, cy, hubRadius);
  hubGrad.addColorStop(0, "#ffffff");
  hubGrad.addColorStop(0.4, "#00e5ff");
  hubGrad.addColorStop(1, "#003b52");
  ctx.fillStyle = hubGrad;
  ctx.shadowColor = "#00e5ff";
  ctx.shadowBlur = 15;
  ctx.fill();
  ctx.shadowBlur = 0;

  ctx.font = "bold 10px sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillStyle = "#001020";
  ctx.fillText("⚡", cx, cy);

  // Hub Labels
  ctx.font = "bold 8.5px var(--font-display, sans-serif)";
  ctx.fillStyle = "#00e5ff";
  ctx.fillText("Orchestrator", cx, cy - hubRadius - 8);

  ctx.font = "bold 7px var(--font-mono, monospace)";
  ctx.fillStyle = "#38ef7d";
  ctx.fillText("Active · 3 tasks", cx, cy + hubRadius + 9);
}

// ============================================================================
// SPARKLINE & OSCILLOSCOPE GRAPH RENDERERS
// ============================================================================
const _localCpuHistory = [21, 24, 19, 28, 22, 20, 25, 23, 21, 22, 24, 21];
const _localRamHistory = [52, 53, 53, 54, 54, 54, 55, 54, 54, 54, 54, 54];
const _localGpuHistory = [35, 36, 38, 37, 39, 36, 37, 38, 37, 36, 37, 37];
const _localNetHistory = [4.5, 4.8, 5.1, 4.9, 4.6, 5.0, 4.9, 4.8, 4.9, 4.8];

function drawSparkline(canvas, values, strokeColor, fillColor) {
  if (!canvas || !values || values.length === 0) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const w = canvas.width = (canvas.parentElement ? canvas.parentElement.clientWidth : 120) || 120;
  const h = canvas.height = (canvas.parentElement ? canvas.parentElement.clientHeight : 38) || 38;

  ctx.clearRect(0, 0, w, h);

  const minVal = 0;
  const maxVal = Math.max(...values, 100);
  const step = w / Math.max(values.length - 1, 1);

  ctx.beginPath();
  values.forEach((v, i) => {
    const x = i * step;
    const y = h - ((v - minVal) / (maxVal - minVal || 1)) * (h - 6) - 3;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });

  ctx.strokeStyle = strokeColor || "#00e5ff";
  ctx.lineWidth = 1.4;
  ctx.shadowColor = strokeColor || "#00e5ff";
  ctx.shadowBlur = 5;
  ctx.stroke();
  ctx.shadowBlur = 0;

  ctx.lineTo(w, h);
  ctx.lineTo(0, h);
  ctx.closePath();
  const grad = ctx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, fillColor || "rgba(0, 229, 255, 0.22)");
  grad.addColorStop(1, "rgba(0, 229, 255, 0.0)");
  ctx.fillStyle = grad;
  ctx.fill();
}

let _netWavePhase = 0;
function drawNetOscilloscope(canvas, downSpeed, upSpeed) {
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const w = canvas.width = 110;
  const h = canvas.height = 24;
  ctx.clearRect(0, 0, w, h);

  _netWavePhase += 0.08;
  const cy = h / 2;

  // Download wave (cyan)
  ctx.beginPath();
  for (let x = 0; x < w; x++) {
    const y = cy + Math.sin(x * 0.12 + _netWavePhase) * 6 * Math.sin(x * 0.04);
    if (x === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.strokeStyle = "rgba(0, 229, 255, 0.9)";
  ctx.lineWidth = 1.4;
  ctx.stroke();

  // Upload wave (green)
  ctx.beginPath();
  for (let x = 0; x < w; x++) {
    const y = cy + Math.cos(x * 0.15 - _netWavePhase * 1.2) * 5 * Math.cos(x * 0.05);
    if (x === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.strokeStyle = "rgba(56, 239, 125, 0.75)";
  ctx.lineWidth = 1.2;
  ctx.stroke();
}

function renderAllSparklines(data) {
  const hist = (data && data.history) || {};
  const cpuVals = hist.cpu || _localCpuHistory;
  const ramVals = hist.ram || _localRamHistory;
  const gpuVals = hist.gpu || _localGpuHistory;
  const netVals = hist.network || _localNetHistory;

  // Mini sparklines under gauges
  drawSparkline(document.getElementById("refCpuSparkline"), cpuVals, "#00e5ff", "rgba(0,229,255,0.2)");
  drawSparkline(document.getElementById("refRamSparkline"), ramVals, "#b388ff", "rgba(179,136,255,0.2)");
  drawSparkline(document.getElementById("refGpuSparkline"), gpuVals, "#38ef7d", "rgba(56,239,125,0.2)");

  // 4 Cards in System Monitor Grid
  drawSparkline(document.getElementById("canvasCpuSpark"), cpuVals, "#00e5ff", "rgba(0,229,255,0.25)");
  drawSparkline(document.getElementById("canvasRamSpark"), ramVals, "#b388ff", "rgba(179,136,255,0.25)");
  drawSparkline(document.getElementById("canvasGpuSpark"), gpuVals, "#38ef7d", "rgba(56,239,125,0.25)");
  drawSparkline(document.getElementById("canvasNetSpark"), netVals, "#00e5ff", "rgba(0,229,255,0.25)");
}


// ----------------------------------------------------
// TELEMETRY WEBSOCKET (/ws/telemetry)
// ----------------------------------------------------
let wsTelemetry = null;

function connectTelemetry() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/telemetry`;
  wsTelemetry = new WebSocket(wsUrl);

  wsTelemetry.onopen = () => {
    document.getElementById("badgeWs").innerHTML = `<span class="dot"></span> LINK: SYNCED`;
    document.getElementById("badgeWs").style.color = "var(--hud-cyan)";
  };

  wsTelemetry.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      updateTelemetryUI(data);
    } catch (e) {
      console.error("Telemetry parse error:", e);
    }
  };

  wsTelemetry.onclose = () => {
    document.getElementById("badgeWs").innerHTML = `<span class="dot" style="background:#ff3344"></span> LINK: OFFLINE`;
    document.getElementById("badgeWs").style.color = "#ff3344";
    setTimeout(connectTelemetry, 3000);
  };
}

function renderOperationsPipeline(orch) {
  if (!orch) return;
  const deckEl = document.getElementById("orchestratorPipelineDeck");
  const opsList = document.getElementById("opsFullTaskList");

  let activeHtml = "";
  let fullOpsHtml = "";

  if (orch.active_tasks && orch.active_tasks.length > 0) {
    orch.active_tasks.forEach(t => {
      const stateColor = t.state === "needs_approval" ? "#ffaa00" : (t.state === "running" ? "#00e5ff" : "#38ef7d");
      const stateBadge = t.state === "needs_approval" ? "NEEDS APPROVAL" : (t.state || "RUNNING").toUpperCase();

      activeHtml += `<div style="margin-bottom:6px; border-left:2px solid ${stateColor}; padding-left:6px;">
        <div style="font-weight:700; color:${stateColor};">[${escapeHtml(stateBadge)}] ${escapeHtml(t.title || 'Task')}</div>
        <div style="font-size:10px; opacity:0.8;">Specialist: ${escapeHtml(t.specialist || 'core')} · ${t.runtime_sec || 0}s</div>
      </div>`;

      fullOpsHtml += `<div class="task-card-item ${escapeHtml(t.state)}">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
          <span style="font-family:var(--font-display); font-size:13px; color:${stateColor}; font-weight:700;">${escapeHtml(t.title || 'Directive')}</span>
          <span class="agent-status-indicator" style="background:${stateColor}; color:#000;">${escapeHtml(stateBadge)}</span>
        </div>
        <div style="font-family:var(--font-mono); font-size:11px; color:#a7ffeb; margin-bottom:6px;">
          Task ID: <code>${escapeHtml(t.id || 'N/A')}</code> · Specialist: <strong>${escapeHtml(t.specialist || 'core')}</strong> · Runtime: ${t.runtime_sec || 0}s
        </div>`;

      if (t.state === "needs_approval") {
        fullOpsHtml += `<div style="margin-top:8px; display:flex; gap:8px;">
          <button class="hud-btn" style="border-color:#38ef7d; color:#38ef7d; font-size:10px; padding:4px 10px;" onclick="window.authorizeTaskInline('${escapeHtml(t.id)}')">✓ AUTHORIZE</button>
          <button class="hud-btn" style="border-color:#ff3344; color:#ff3344; font-size:10px; padding:4px 10px;" onclick="window.rejectTaskInline('${escapeHtml(t.id)}')">✕ REJECT</button>
        </div>`;
      }
      fullOpsHtml += `</div>`;

      // Auto-trigger approval modal if needed and not already open
      if (t.state === "needs_approval" && !state.approvalModalOpen) {
        openApprovalModal(t);
      }
    });
  }

  if (orch.recent_history && orch.recent_history.length > 0) {
    orch.recent_history.forEach(item => {
      fullOpsHtml += `<div class="task-card-item" style="border-left:3px solid #38ef7d;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
          <span style="font-family:var(--font-display); font-size:12px; color:#38ef7d; font-weight:700;">✓ ${escapeHtml(item.title || 'Completed Task')}</span>
          <span style="font-family:var(--font-mono); font-size:10px; color:rgba(255,255,255,0.5);">COMPLETED</span>
        </div>
        <div style="font-family:var(--font-mono); font-size:10px; color:#e0f7fa; opacity:0.85;">
          ${escapeHtml(item.evidence || 'Execution verified.')}
        </div>
      </div>`;
    });
  }

  if (!orch.active_tasks?.length && !orch.recent_history?.length) {
    fullOpsHtml = `<div class="task-card-item">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
        <span style="font-family:var(--font-display); font-size:13px; color:#00e5ff;">System Standby</span>
        <span class="agent-status-indicator">READY</span>
      </div>
      <div style="font-family:var(--font-mono); font-size:11px; color:#a7ffeb;">
        Master Orchestrator active. Concurrency bounded to ${orch.max_concurrency || 2} simultaneous tasks. All directives are logged with empirical evidence.
      </div>
    </div>`;
  }

  if (deckEl) {
    if (activeHtml) {
      deckEl.innerHTML = activeHtml;
    } else if (orch.recent_history && orch.recent_history.length > 0) {
      const last = orch.recent_history[orch.recent_history.length - 1];
      deckEl.innerHTML = `<div style="opacity:0.85;">
        <span style="color:#38ef7d;">✓ LAST COMPLETED:</span> ${escapeHtml(last.title || '')}<br>
        <small style="opacity:0.7;">${escapeHtml(last.evidence || '')}</small>
      </div>`;
    } else {
      deckEl.innerHTML = `<div style="opacity:0.6;">All systems nominal. Ready for directives.</div>`;
    }
  }

  if (opsList) {
    opsList.innerHTML = fullOpsHtml;
  }
}

window.authorizeTaskInline = async function(taskId) {
  try {
    playSound("ack");
    await fetch("/api/orchestrator/approve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task_id: taskId })
    });
    if (typeof showToast === "function") showToast(`Task #${taskId} authorized`, "success");
    window.refreshOperationsPipeline();
  } catch(e) {
    if (typeof showToast === "function") showToast("Authorization failed: " + e.message, "error");
  }
};

window.rejectTaskInline = async function(taskId) {
  try {
    playSound("blip");
    await fetch("/api/orchestrator/reject", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task_id: taskId, reason: "Rejected via Operations Console" })
    });
    if (typeof showToast === "function") showToast(`Task #${taskId} rejected`, "info");
    window.refreshOperationsPipeline();
  } catch(e) {
    if (typeof showToast === "function") showToast("Rejection failed: " + e.message, "error");
  }
};

window.refreshOperationsPipeline = async function() {
  try {
    const res = await fetch("/api/orchestrator/status");
    if (res.ok) {
      const data = await res.json();
      renderOperationsPipeline(data);
    }
  } catch(e) {}
};

function updateTelemetryUI(data) {
  if (!data) return;

  // CPU
  const cpuPct = Math.round(data.cpu ? data.cpu.percent : 0);
  const cpuEl = document.getElementById("cpuPercent");
  if (cpuEl) cpuEl.innerText = `${cpuPct}%`;

  const cpuCircle = document.getElementById("refCpuCircle") || document.getElementById("cpuCircle");
  if (cpuCircle) {
    const circ = 150.8;
    const offset = circ - (circ * Math.min(100, Math.max(0, cpuPct))) / 100;
    cpuCircle.style.strokeDashoffset = offset;
  }
  const cpuFreq = document.getElementById("cpuFreq");
  if (cpuFreq && data.cpu) {
    cpuFreq.innerText = `${data.cpu.freq_mhz || 3800} MHz · ${data.cpu.count || 16} Cores`;
  }

  // RAM
  const ram = data.memory || {};
  const ramPct = Math.round(ram.percent || 0);
  const refRamPct = document.getElementById("refRamPercent");
  if (refRamPct) refRamPct.innerText = `${ramPct}%`;

  const ramCircle = document.getElementById("refRamCircle");
  if (ramCircle) {
    const circ = 150.8;
    const offset = circ - (circ * Math.min(100, Math.max(0, ramPct))) / 100;
    ramCircle.style.strokeDashoffset = offset;
  }
  const ramDetail = document.getElementById("ramDetail");
  if (ramDetail) ramDetail.innerText = `${ram.used_gb || 0} / ${ram.total_gb || 16} GB`;

  const ramProgressFill = document.getElementById("ramProgressFill");
  if (ramProgressFill) ramProgressFill.style.width = `${ramPct}%`;
  const ramPercentLabel = document.getElementById("ramPercentLabel");
  if (ramPercentLabel) ramPercentLabel.innerText = `ALLOCATION: ${ramPct}% (${ram.free_gb || 0} GB FREE)`;

  // GPU
  const gpu = data.gpu || {};
  const gpuPct = Math.round(gpu.percent || 35);
  const refGpuPct = document.getElementById("refGpuPercent");
  if (refGpuPct) refGpuPct.innerText = `${gpuPct}%`;

  const gpuCircle = document.getElementById("refGpuCircle");
  if (gpuCircle) {
    const circ = 150.8;
    const offset = circ - (circ * Math.min(100, Math.max(0, gpuPct))) / 100;
    gpuCircle.style.strokeDashoffset = offset;
  }
  const refGpuModel = document.getElementById("refGpuModel");
  if (refGpuModel) refGpuModel.innerText = gpu.name || "AMD Radeon 780M";

  // STORAGE
  if (data.disks && data.disks.length > 0) {
    const d = data.disks[0];
    const storageText = document.getElementById("refStorageText");
    if (storageText) storageText.innerText = `${d.used_gb} GB / ${d.total_gb} GB`;
    const storagePct = document.getElementById("refStoragePercent");
    if (storagePct) storagePct.innerText = `${d.percent}%`;
    const storageFill = document.getElementById("refStorageFill");
    if (storageFill) storageFill.style.width = `${d.percent}%`;
  }

  // NETWORK
  const net = data.network || {};
  const downSpeed = net.download_mbps || (net.download_kbps ? (net.download_kbps / 1024).toFixed(1) : 4.9);
  const upSpeed = net.upload_mbps || (net.upload_kbps ? (net.upload_kbps / 1024).toFixed(1) : 4.8);
  const refNetSpeeds = document.getElementById("refNetSpeeds");
  if (refNetSpeeds) refNetSpeeds.innerText = `${downSpeed} MB/s ↓  ${upSpeed} MB/s ↑`;

  const netUp = document.getElementById("netUp");
  if (netUp) netUp.innerText = `${net.upload_kbps || 0} KB/s`;
  const netDown = document.getElementById("netDown");
  if (netDown) netDown.innerText = `${net.download_kbps || 0} KB/s`;

  // SYSTEM MONITOR SPARKLINE CARDS
  const monCpu = document.getElementById("refMonitorCpuVal");
  if (monCpu) monCpu.innerText = `${cpuPct}%`;
  const monRam = document.getElementById("refMonitorRamVal");
  if (monRam) monRam.innerText = `${ramPct}%`;
  const monGpu = document.getElementById("refMonitorGpuVal");
  if (monGpu) monGpu.innerText = `${gpuPct}%`;
  const monNet = document.getElementById("refMonitorNetVal");
  if (monNet) monNet.innerText = `${downSpeed} / ${upSpeed} MB/s`;

  // TOP PROCESSES TABLE
  const procTable = document.getElementById("processTable");
  if (procTable && data.top_processes) {
    let target = procTable.querySelector("tbody");
    if (!target && procTable.tagName.toLowerCase() === "table") {
      target = document.createElement("tbody");
      procTable.appendChild(target);
    }
    if (!target) target = procTable;
    target.innerHTML = "";

    const dotIcons = ["🟢", "🟡", "🔵", "🐍", "🔷"];
    data.top_processes.slice(0, 5).forEach((p, idx) => {
      const tr = document.createElement("tr");
      const ramText = p.ram_str || (p.ram_mb >= 1024 ? `${(p.ram_mb/1024).toFixed(1)} GB` : `${p.ram_mb} MB`);
      const cpuVal = (p.cpu !== undefined) ? `${p.cpu}%` : `${(Math.random() * 5 + 1).toFixed(1)}%`;
      const dot = dotIcons[idx % dotIcons.length];
      tr.innerHTML = `
        <td class="ref-proc-name">${dot} ${escapeHtml(p.name)}</td>
        <td class="ref-proc-mem">${ramText}</td>
        <td class="ref-proc-cpu">${cpuVal}</td>
      `;
      target.appendChild(tr);
    });
  }

  // Uptime & Active Window
  const uptimeEl = document.getElementById("uptimeLabel");
  if (uptimeEl && data.uptime) uptimeEl.innerText = data.uptime;
  const activeWin = document.getElementById("activeWindowTitle");
  if (activeWin) activeWin.innerText = data.active_window || "Desktop";

  // Trigger sparklines & oscilloscope
  if (typeof renderAllSparklines === "function") {
    renderAllSparklines(data);
  }
  if (typeof drawNetOscilloscope === "function") {
    const netWaveCanvas = document.getElementById("refNetWaveCanvas");
    if (netWaveCanvas) drawNetOscilloscope(netWaveCanvas, downSpeed, upSpeed);
  }

  // Evolution Telemetry
  if (data.evolution) {
    const evo = data.evolution;
    const badge = document.getElementById("badgeEvolution");
    if (badge) {
      badge.innerHTML = `<span class="dot" style="background:#ffaa00; box-shadow:0 0 8px #ffaa00;"></span> EVOLUTION: LVL ${evo.level} (${evo.knowledge_nodes} NODES)`;
    }
  }

  // Master Orchestrator Telemetry & Pipeline
  if (data.orchestrator) {
    const orch = data.orchestrator;
    const badgeTasks = document.getElementById("badgeTasks");
    if (badgeTasks) {
      const activeCnt = orch.active_tasks_count || 0;
      const maxConc = orch.max_concurrency || 2;
      const dotColor = activeCnt > 0 ? "#00e5ff" : "#38ef7d";
      badgeTasks.innerHTML = `<span class="dot" style="background:${dotColor}; box-shadow:0 0 8px ${dotColor};"></span> TASKS: ${activeCnt}/${maxConc}`;
    }
    if (typeof renderOperationsPipeline === "function") renderOperationsPipeline(orch);
  }

  // Model Gateway Status
  if (data.gateway) {
    const badgeGateway = document.getElementById("badgeGateway");
    if (badgeGateway) {
      const gStatus = data.gateway.status || "online";
      const gColor = gStatus === "online" ? "#38ef7d" : (gStatus === "degraded" ? "#ffaa00" : "#ff3344");
      const lat = data.gateway.average_latency_sec || 0.45;
      badgeGateway.innerHTML = `<span class="dot" style="background:${gColor}; box-shadow:0 0 8px ${gColor};"></span> GATEWAY: ${gStatus.toUpperCase()} · ${lat}s`;
    }
  }
}

// ----------------------------------------------------
// CHAT & VOICE WEBSOCKET (/ws/chat)
// ----------------------------------------------------
let wsChat = null;
let _chatReconnectDelay = 1000;
let _chatHeartbeatTimer = null;

function connectChat() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/chat`;
  wsChat = new WebSocket(wsUrl);

  wsChat.onopen = () => {
    _chatReconnectDelay = 1000; // Reset backoff on successful connect
    document.getElementById("badgeCore").innerHTML = `<span class="dot"></span> CORE: ONLINE`;
    checkAntigravityStatus();
    appendLog("info", "LINK", "Neural chat WebSocket connected.");

    // Start heartbeat ping every 15 seconds
    if (_chatHeartbeatTimer) clearInterval(_chatHeartbeatTimer);
    _chatHeartbeatTimer = setInterval(() => {
      if (wsChat && wsChat.readyState === WebSocket.OPEN) {
        try {
          wsChat.send(JSON.stringify({ type: "ping" }));
        } catch (e) {}
      }
    }, 15000);
  };

  wsChat.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      handleIncomingChatMessage(msg);
    } catch (e) {
      console.error("Chat parse error:", e);
    }
  };

  wsChat.onclose = () => {
    if (_chatHeartbeatTimer) clearInterval(_chatHeartbeatTimer);
    document.getElementById("badgeCore").innerHTML = `<span class="dot" style="background:#ff3344; box-shadow:0 0 8px #ff3344;"></span> CORE: RECONNECTING`;
    appendLog("warning", "LINK", `Chat WebSocket disconnected. Reconnecting in ${_chatReconnectDelay / 1000}s...`);

    // Exponential backoff: 1s → 2s → 4s → 8s → 16s → max 30s
    setTimeout(connectChat, _chatReconnectDelay);
    _chatReconnectDelay = Math.min(_chatReconnectDelay * 2, 30000);
  };

  wsChat.onerror = () => {
    // Will trigger onclose automatically
  };
}

async function checkAntigravityStatus() {
  try {
    const res = await fetch("/api/antigravity/status");
    const data = await res.json();
    const badge = document.getElementById("badgeAntigravity");
    if (badge) {
      badge.innerHTML = `<span class="dot" style="background:#00e5ff; box-shadow:0 0 8px #00e5ff;"></span> ANTIGRAVITY: CONNECTED`;
      badge.title = `Google Antigravity Project Workspace Linked · Zero API Keys Required · ${data.tools_count || 12} PC Tools Active`;
    }
  } catch (e) {
    console.warn("Antigravity status fetch error:", e);
  }
}

function setAssistantStatus(newStatus, subtext) {
  state.status = newStatus;
  const statusEl = document.getElementById("coreStatusLabel");
  const subtextEl = document.getElementById("coreSubtext");
  const lightEl = document.getElementById("inputStatusIndicator");
  const micBtn = document.getElementById("btnVoiceToggle");
  const cmdInput = document.getElementById("cmdInput");
  const btnSend = document.getElementById("btnSend");

  // Reference UI Orbiting Nodes Synchronization
  const orbitalNodes = {
    "listening": "nodeListening",
    "speech_detected": "nodeListening",
    "thinking": "nodeProcessing",
    "transcribing": "nodeProcessing",
    "processing": "nodeProcessing",
    "researching": "nodeResearching",
    "executing": "nodeExecuting",
    "generating": "nodeGenerating",
    "speaking": "nodeSpeaking",
    "idle": "nodeMonitoring",
    "waiting_for_approval": "nodeWaiting",
    "error": "nodeWaiting",
    "cancelled": "nodeWaiting"
  };
  const allNodeIds = [
    "nodeListening", "nodeProcessing", "nodeResearching", "nodeExecuting",
    "nodeGenerating", "nodeSpeaking", "nodeMonitoring", "nodeWaiting"
  ];
  allNodeIds.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.remove("active");
  });
  const activeId = orbitalNodes[newStatus] || "nodeMonitoring";
  const activeNodeEl = document.getElementById(activeId);
  if (activeNodeEl) activeNodeEl.classList.add("active");

  // Pedestal status label
  if (statusEl) {
    const statusLabels = {
      "listening": "LISTENING",
      "speech_detected": "LISTENING",
      "thinking": "PROCESSING",
      "transcribing": "PROCESSING",
      "processing": "PROCESSING",
      "researching": "RESEARCHING",
      "executing": "EXECUTING",
      "generating": "GENERATING",
      "speaking": "SPEAKING",
      "idle": "ONLINE",
      "waiting_for_approval": "WAITING",
      "error": "ERROR",
      "cancelled": "ABORTED"
    };
    statusEl.innerText = statusLabels[newStatus] || newStatus.toUpperCase().replace(/_/g, " ");
    statusEl.className = "ref-pedestal-status state-" + newStatus.toLowerCase().replace(/_/g, "-");
  }

  // Animate pedestal equalizer waveforms
  const waveLeft = document.getElementById("refPedestalWaveLeft");
  const waveRight = document.getElementById("refPedestalWaveRight");
  if (waveLeft && waveRight) {
    const isActive = (newStatus === "speaking" || newStatus === "listening" || newStatus === "processing");
    const barsL = waveLeft.querySelectorAll(".ref-waveform-bar");
    const barsR = waveRight.querySelectorAll(".ref-waveform-bar");
    if (isActive) {
      barsL.forEach(b => {
        b.style.height = `${Math.floor(Math.random() * 16 + 6)}px`;
        b.style.background = (newStatus === "speaking") ? "#ff4081" : "#00e5ff";
      });
      barsR.forEach(b => {
        b.style.height = `${Math.floor(Math.random() * 16 + 6)}px`;
        b.style.background = (newStatus === "speaking") ? "#ff4081" : "#00e5ff";
      });
    } else {
      barsL.forEach((b, i) => { b.style.height = `${[6, 12, 18, 9, 14][i % 5]}px`; b.style.background = "#00e5ff"; });
      barsR.forEach((b, i) => { b.style.height = `${[14, 9, 18, 12, 6][i % 5]}px`; b.style.background = "#00e5ff"; });
    }
  }

  if (subtext && subtextEl) {
    subtextEl.innerText = subtext.toUpperCase();
  }

  if (newStatus === "listening" || newStatus === "speech_detected") {
    if (lightEl) {
      lightEl.style.background = "#00ffff";
      lightEl.style.boxShadow = "0 0 10px #00ffff";
    }
    if (micBtn) {
      micBtn.classList.remove("speaking-locked");
      micBtn.classList.add("active");
    }
    updateMicBadge("LIVE", "#00ffff");
    if (cmdInput) { cmdInput.disabled = false; cmdInput.placeholder = "Listening to your voice, Sir Shakil..."; }
    if (btnSend) btnSend.disabled = false;
  } else if (newStatus === "thinking" || newStatus === "transcribing" || newStatus === "generating" || newStatus === "processing") {
    if (lightEl) {
      lightEl.style.background = "var(--hud-amber)";
      lightEl.style.boxShadow = "0 0 10px var(--hud-amber)";
    }
    if (micBtn) {
      micBtn.classList.add("speaking-locked");
      micBtn.classList.remove("active");
    }
    updateMicBadge("PROCESSING", "#ffaa00");
    if (cmdInput) { cmdInput.disabled = true; cmdInput.placeholder = "Jarvis processing directive..."; }
    if (btnSend) btnSend.disabled = true;
  } else if (newStatus === "executing") {
    if (lightEl) {
      lightEl.style.background = "var(--hud-purple)";
      lightEl.style.boxShadow = "0 0 10px var(--hud-purple)";
    }
    if (micBtn) {
      micBtn.classList.add("speaking-locked");
    }
    updateMicBadge("EXECUTING", "#9d4edd");
    if (cmdInput) cmdInput.disabled = true;
    if (btnSend) btnSend.disabled = true;
  } else if (newStatus === "speaking") {
    if (lightEl) {
      lightEl.style.background = "#38ef7d";
      lightEl.style.boxShadow = "0 0 10px #38ef7d";
    }
    if (micBtn) {
      micBtn.classList.add("speaking-locked");
      micBtn.classList.remove("active");
    }
    updateMicBadge("MUTED (SPEAKING)", "#38ef7d");
    if (cmdInput) { cmdInput.disabled = true; cmdInput.placeholder = "Jarvis speaking... microphone will auto-arm when complete."; }
    if (btnSend) btnSend.disabled = true;
  } else if (newStatus === "waiting_for_approval") {
    if (lightEl) {
      lightEl.style.background = "#ffaa00";
      lightEl.style.boxShadow = "0 0 15px #ffaa00";
    }
    if (micBtn) micBtn.classList.remove("active");
    updateMicBadge("AWAITING APPROVAL", "#ffaa00");
  } else if (newStatus === "error" || newStatus === "cancelled") {
    if (lightEl) {
      lightEl.style.background = "var(--hud-red)";
      lightEl.style.boxShadow = "0 0 12px var(--hud-red)";
    }
    updateMicBadge("ABORTED", "#ff3344");
    setTimeout(() => { if (state.status === "error" || state.status === "cancelled") setAssistantStatus("idle"); }, 2000);
  } else {
    if (lightEl) {
      lightEl.style.background = "var(--hud-cyan)";
      lightEl.style.boxShadow = "0 0 8px var(--hud-cyan)";
    }
    if (statusEl) statusEl.innerText = "ONLINE";
    if (subtextEl) subtextEl.innerText = "AWAITING DIRECTIVE";
    if (micBtn) {
      micBtn.classList.remove("speaking-locked");
      if (!state.isListening) micBtn.classList.remove("active");
    }
    updateMicBadge("STANDBY", "#888888");
    if (cmdInput) { cmdInput.disabled = false; cmdInput.placeholder = "Type a message or press / for commands..."; }
    if (btnSend) btnSend.disabled = false;
  }
}

// Streaming text accumulator for progressive rendering
let _streamingAccumulated = "";
let _streamingLogLine = null;
let _streamingChatBubble = null;

function handleIncomingChatMessage(msg) {
  const feed = document.getElementById("terminalFeed");

  if (msg.type === "abort") {
    clearAudioQueue();
    if (_streamingLogLine) {
      _streamingLogLine.remove();
      _streamingLogLine = null;
    }
    if (_streamingChatBubble) {
      _streamingChatBubble.remove();
      _streamingChatBubble = null;
    }
    _streamingAccumulated = "";
    state.jarvisIsSpeaking = false;
    currentPlayingAudio = null;
    unlockMicAfterJarvisTurn();
    setAssistantStatus("idle", "ABORTED");
    appendLog("warning", "ABORT", msg.reason || "Directive interrupted.");
    return;
  }

  if (msg.type === "status") {
    if (msg.status === "thinking") {
      lockMicForJarvisTurn("PROCESSING");
      setAssistantStatus("thinking", msg.subtext || "PROCESSING DIRECTIVE");
      // Reset streaming accumulator for new response
      _streamingAccumulated = "";
      _streamingLogLine = null;
      _streamingChatBubble = null;
    } else if (msg.status === "speaking") {
      lockMicForJarvisTurn("SPEAKING");
      setAssistantStatus("speaking", msg.subtext || "COMMUNICATING");
      // If speaker duration provided, set watchdog
      if (msg.duration) {
        if (state.speakingTurnTimer) clearTimeout(state.speakingTurnTimer);
        state.speakingTurnTimer = setTimeout(() => {
          if (state.status === "speaking") {
            unlockMicAfterJarvisTurn();
          }
        }, (msg.duration + 0.5) * 1000);
      }
    } else if (msg.status === "idle") {
      state.jarvisIsSpeaking = false;
      unlockMicAfterJarvisTurn();
      setAssistantStatus("idle", msg.subtext || "AWAITING DIRECTIVE");
    } else if (msg.status === "speech_detected") {
      setAssistantStatus("speech_detected", msg.subtext || "HEARING SIR SHAKIL...");
      updateMicBadge("HEARING", "#00ffff");
      const btn = document.getElementById("btnVoiceToggle");
      if (btn) btn.classList.add("active");
    } else if (msg.status === "transcribing") {
      setAssistantStatus("transcribing", msg.subtext || "TRANSCRIBING...");
      updateMicBadge("TRANSCRIBING", "#ffaa00");
    } else if (msg.status === "listening") {
      state.jarvisIsSpeaking = false;
      unlockMicAfterJarvisTurn();
      setAssistantStatus("listening", msg.subtext || "LISTENING");
      updateMicBadge("LIVE", "#00ffff");
      const btn = document.getElementById("btnVoiceToggle");
      if (btn) btn.classList.add("active");
    } else {
      setAssistantStatus(msg.status, msg.subtext);
    }
  } else if (msg.type === "audio_matrix_updated") {
    syncHardwareMicStatus();
    appendLog("info", "AUDIO", `Audio routing matrix updated: Mic -> ${msg.active_input?.name || "Auto"}, Speaker -> ${msg.active_output?.name || "Auto"}`);
  } else if (msg.type === "terminal_log") {
    const termFeed = document.getElementById("refTerminalLogFeed");
    if (termFeed) {
      if (msg.source === "sandbox") {
        termFeed.innerHTML += `<div class="term-line sys">[SANDBOX ${escapeHtml((msg.language || "python").toUpperCase())}] Duration: ${msg.duration_ms || 0}ms · Status: ${msg.success ? "OK" : "FAILED"}</div>`;
        if (msg.stdout) termFeed.innerHTML += `<div class="term-line out">${escapeHtml(msg.stdout)}</div>`;
        if (msg.stderr) termFeed.innerHTML += `<div class="term-line err">${escapeHtml(msg.stderr)}</div>`;
      } else if (msg.source === "cli") {
        termFeed.innerHTML += `<div class="term-line cmd">&gt; ${escapeHtml(msg.command)}</div>`;
        if (msg.stdout) termFeed.innerHTML += `<div class="term-line out">${escapeHtml(msg.stdout)}</div>`;
        if (msg.stderr) termFeed.innerHTML += `<div class="term-line err">${escapeHtml(msg.stderr)}</div>`;
      }
      termFeed.scrollTop = termFeed.scrollHeight;
    }
  } else if (msg.type === "thought") {
    appendLog("thought", "THOUGHT", msg.content);

    if (!state.currentThoughts) state.currentThoughts = [];
    state.currentThoughts.push(msg.content);
  } else if (msg.type === "user_speech") {
    // Natively heard speech from Python background
    appendLog("user", "SIR SHAKIL", msg.text);
    appendDedicatedChatMessage("user", msg.text);
  } else if (msg.type === "chunk") {
    // STREAMING: Progressive text rendering as tokens arrive
    _streamingAccumulated = msg.accumulated || (_streamingAccumulated + (msg.content || ""));
    setAssistantStatus("thinking", `STREAMING RESPONSE...`);

    // Update terminal feed progressively
    if (!_streamingLogLine && feed) {
      _streamingLogLine = document.createElement("div");
      _streamingLogLine.className = "log-line jarvis streaming-active";
      const timeStr = new Date().toTimeString().split(" ")[0];
      _streamingLogLine.innerHTML = `
        <span class="log-time">[${timeStr}]</span>
        <span class="log-sender">J.A.R.V.I.S.:</span>
        <span class="log-text streaming-text"></span>
      `;
      feed.appendChild(_streamingLogLine);
    }
    if (_streamingLogLine) {
      const logTextEl = _streamingLogLine.querySelector(".streaming-text");
      if (logTextEl) logTextEl.textContent = _streamingAccumulated;
      if (feed) feed.scrollTop = feed.scrollHeight;
    }

    // Update dedicated chat progressively
    const chatContainer = document.getElementById("dedicatedChatMessages");
    if (chatContainer && !_streamingChatBubble) {
      _streamingChatBubble = document.createElement("div");
      _streamingChatBubble.className = "chat-msg chat-msg-jarvis streaming-active";
      const timeStr2 = new Date().toTimeString().split(" ")[0];
      const modelTag = state.selectedModel ? `<span class="chat-model-pill">${escapeHtml(state.selectedModel.replace("agy/", "").replace("auto/", "").toUpperCase())}</span>` : "";
      _streamingChatBubble.innerHTML = `
        <div class="chat-meta">
          <span>J.A.R.V.I.S.</span>
          <span>${timeStr2}</span>
          ${modelTag}
        </div>
        <div class="chat-bubble">
          <div class="chat-bubble-text streaming-chat-text"></div>
        </div>
      `;
      chatContainer.appendChild(_streamingChatBubble);
    }
    if (_streamingChatBubble) {
      const chatTextEl = _streamingChatBubble.querySelector(".streaming-chat-text");
      if (chatTextEl) chatTextEl.textContent = _streamingAccumulated;
      const body = document.getElementById("dedicatedChatBody");
      if (body) body.scrollTop = body.scrollHeight;
    }
  } else if (msg.type === "tool_call") {
    playSound("ack");
    const toolName = msg.tool || msg.name || "TOOL";
    setAssistantStatus("executing", `EXECUTING: ${toolName}`);
    appendLog("tool", "ACTION", `Invoking protocol '${toolName}' with params: ${JSON.stringify(msg.args || {})}`);
  } else if (msg.type === "tool_result") {
    appendLog("tool", "RESULT", `Protocol '${msg.name || msg.tool}' response: ${JSON.stringify(msg.result)}`);
  } else if (msg.type === "response") {
    // Final response arrived — replace streaming placeholders with final formatted version
    if (_streamingLogLine) {
      _streamingLogLine.remove();
      _streamingLogLine = null;
    }
    if (_streamingChatBubble) {
      _streamingChatBubble.remove();
      _streamingChatBubble = null;
    }
    _streamingAccumulated = "";

    appendLog("jarvis", "J.A.R.V.I.S.", msg.text);
    state.chatHistory.push({ role: "model", content: msg.text });

    // Cap chat history at 20 entries
    if (state.chatHistory.length > 20) {
      state.chatHistory = state.chatHistory.slice(-20);
    }

    appendDedicatedChatMessage("jarvis", msg.text, state.selectedModel, state.currentThoughts ? state.currentThoughts.slice() : []);
    state.currentThoughts = [];
  } else if (msg.type === "audio") {
    enqueueBase64Audio(msg.audio_base64, (msg.text || "").length, msg.mime || "audio/wav", msg.duration || 3.0);
  } else if (msg.type === "proactive_update") {
    playSound("alert");
    appendLog("warning", "PROACTIVE ALERT", msg.text);
    if (msg.audio_base64) {
      enqueueBase64Audio(msg.audio_base64, (msg.text || "").length, msg.mime || "audio/wav", msg.duration || 3.0);
    }
  } else if (msg.type === "spatial_event") {
    // Real-time spatial broadcast event from Python backend
    window.dispatchEvent(new CustomEvent("jarvis:spatial-event", { detail: msg.data || msg }));
    const act = (msg.data && msg.data.action) ? msg.data.action : (msg.action || "UPDATE");
    appendLog("tool", "SPATIAL", `Spatial directive: ${act.toUpperCase()}`);
  } else if (msg.type === "pong") {
    // Heartbeat response received — connection is alive
  }
}

function appendLog(category, sender, text) {
  const feed = document.getElementById("terminalFeed");
  const timeStr = new Date().toTimeString().split(" ")[0];
  if (feed) {
    const line = document.createElement("div");
    line.className = `log-line ${category}`;
    line.innerHTML = `
      <span class="log-time">[${timeStr}]</span>
      <span class="log-sender">${sender}:</span>
      <span class="log-text">${escapeHtml(text)}</span>
    `;
    feed.appendChild(line);
    feed.scrollTop = feed.scrollHeight;
  }
  console.log(`[${category.toUpperCase()}] ${sender}: ${text}`);
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

// ----------------------------------------------------
// AUDIO PLAYBACK & VISUALIZER BINDING
// ----------------------------------------------------
const audioQueue = [];
let isPlayingQueue = false;

function enqueueBase64Audio(b64, textLength = 50, mime = "audio/wav", duration = 3.0) {
  if (!b64) return;
  audioQueue.push({b64, textLength, mime, duration});
  processAudioQueue();
}

function processAudioQueue() {
  if (isPlayingQueue || audioQueue.length === 0) return;
  isPlayingQueue = true;
  const nextItem = audioQueue.shift();
  playBase64Audio(nextItem.b64, nextItem.textLength, nextItem.mime, nextItem.duration, () => {
     isPlayingQueue = false;
     processAudioQueue();
  });
}

function clearAudioQueue() {
  audioQueue.length = 0;
  if (currentPlayingAudio) {
      try { currentPlayingAudio.pause(); currentPlayingAudio = null; } catch(e){}
  }
  isPlayingQueue = false;
  unlockMicAfterJarvisTurn();
}

let currentPlayingAudio = null;

function playBase64Audio(b64, textLength, mime, duration, onComplete) {
  unlockAllAudioEngines();
  lockMicForJarvisTurn("SPEAKING");
  setAssistantStatus("speaking", "COMMUNICATING");

  const estSec = duration || Math.max(2, Math.min(30, (textLength || 60) / 14));

  if (!b64) {
    setTimeout(() => {
       unlockMicAfterJarvisTurn();
       if (onComplete) onComplete();
    }, estSec * 1000);
    return;
  }

  // Pure PC Speaker mode: backend already dispatched speech to Windows hardware
  if (state.audioMode === "speaker") {
    setAssistantStatus("speaking", "COMMUNICATING (PC HARDWARE)");
    setTimeout(() => {
       unlockMicAfterJarvisTurn();
       if (onComplete) onComplete();
    }, estSec * 1000);
    return;
  }

  try {
    if (currentPlayingAudio) {
      try { currentPlayingAudio.pause(); } catch(e){}
    }

    const actualMime = (mime && mime.includes("wav")) ? "audio/wav" : (b64.startsWith("UklGR") ? "audio/wav" : "audio/mp3");
    const audio = new Audio(`data:${actualMime};base64,${b64}`);
    currentPlayingAudio = audio;
    audio.volume = Math.max(0.05, Math.min(1.0, (state.volume / 100) || 1.0));

    if (audioCtx && analyser && audioCtx.state === "running") {
      try {
        const source = audioCtx.createMediaElementSource(audio);
        source.connect(analyser);
      } catch (e) {}
    }

    let endedFired = false;
    const handlePlaybackFinished = () => {
      if (endedFired) return;
      endedFired = true;
      unlockMicAfterJarvisTurn();
      if (onComplete) onComplete();
    };

    audio.onended = handlePlaybackFinished;
    audio.onerror = (e) => {
      console.warn("Browser audio error, falling back to timer:", e);
      setTimeout(handlePlaybackFinished, estSec * 1000);
    };

    const p = audio.play();
    if (p !== undefined) {
      p.catch(async (err) => {
        console.warn("Browser autoplay error, relying on timer:", err);
        setTimeout(handlePlaybackFinished, estSec * 1000);
      });
    }

    // Safety watchdog timer
    setTimeout(() => {
      if (state.jarvisIsSpeaking && !endedFired) {
        handlePlaybackFinished();
      }
    }, (estSec + 1.5) * 1000);

  } catch (err) {
    console.error("Audio playback exception:", err);
    setTimeout(unlockMicAfterJarvisTurn, estSec * 1000);
  }
}

// ----------------------------------------------------
// SPEECH RECOGNITION (VOICE INPUT & ALWAYS-ON WAKE)
// ----------------------------------------------------
let recognition = null;
let speechSilenceTimer = null;
let currentRecordedText = "";
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

// Phonetic auto-corrector & regional speech normalizer
function normalizeSpokenText(text) {
  if (!text) return "";
  let clean = text.trim();

  // 1. Wake-word phonetic mishearings from Google Speech engine
  clean = clean.replace(/\b(travis|service|harvest|charles|starbucks|java|jawis|job is|chavez|drvis|jarbis|javish|jarv|jervis|davis|garvis|tarvis)\b/gi, "Jarvis");

  // 2. Antigravity and OmniRoute platform mishearings
  clean = clean.replace(/\b(anti\s*gravity|anti-gravity|anti\s*grabby|integrative|integra)\b/gi, "antigravity");
  clean = clean.replace(/\b(omni\s*route|omni\s*road|army\s*route|omni\s*root)\b/gi, "omniroute");

  // 3. AI Models and Providers
  clean = clean.replace(/\b(cloud|claud|clod)\s*(sonnet|opus|3\.5|3\.7|4\.6)?\b/gi, "Claude $2");
  clean = clean.replace(/\b(jiminy|jimmy|gemini)\s*(flash|pro|3\.7|3\.8)?\b/gi, "Gemini $2");
  clean = clean.replace(/\b(sonit|senate)\b/gi, "sonnet");

  // 4. Common application and tool mishearings
  clean = clean.replace(/\b(note\s*pad|not\s*pad|no\s*pad)\b/gi, "notepad");
  clean = clean.replace(/\b(cal\s*culator|calculater|calc|cockulator)\b/gi, "calculator");
  clean = clean.replace(/\b(event\s*bright|even\s*bright|event\s*bride|event\s*bite|even\s*bite)\b/gi, "eventbrite");
  clean = clean.replace(/\b(google\s*chrome|chrome\s*browser)\b/gi, "chrome");
  clean = clean.replace(/\b(vs\s*code|visual\s*studio\s*code|visual\s*code|v\s*s\s*code)\b/gi, "vscode");
  clean = clean.replace(/\b(you\s*tube|u\s*tube)\b/gi, "youtube");
  clean = clean.replace(/\b(screen\s*shot|clean\s*shot|screen\s*short|capture\s*screen|take\s*a\s*screenshot)\b/gi, "screenshot");

  // 5. Regional / Banglish directives translated to English intents
  clean = clean.replace(/\b(kholo|khulo|open koro|chalu koro|start koro)\b/gi, "open");
  clean = clean.replace(/\b(bondho koro|bondho|close koro|off koro)\b/gi, "close");
  clean = clean.replace(/\b(dekhao|dekhiye dao|show koro)\b/gi, "show");
  clean = clean.replace(/\b(email dekhao|email check koro|inbox dekhao|mail dekhao)\b/gi, "check emails");
  clean = clean.replace(/\b(internet e search koro|internet e research koro|online e research koro|online search koro|web research)\b/gi, "research online");
  clean = clean.replace(/\b(ki obostha|kemon acho|status ki|diagnostics dekhao)\b/gi, "status report");
  clean = clean.replace(/\b(sound barhao|volume barhao|sound increase|sound up)\b/gi, "turn up volume");
  clean = clean.replace(/\b(sound komao|volume komao|sound decrease|sound down)\b/gi, "turn down volume");

  return clean;
}

function isWakeCommand(text) {
  const clean = text.toLowerCase().trim().replace(/[^a-z0-9\s]/g, "");
  return /^(jarvis|hey jarvis|hello jarvis|jarvis wake up|wake up jarvis|wake up|are you awake|are you there jarvis|jarvis are you awake|javis|jarv|service|travis)$/i.test(clean);
}

function containsWakeTrigger(text) {
  const clean = text.toLowerCase().trim();
  return [
    "jarvis", "javis", "jarv", "shakil", "hey jarvis", "wake up", "wake up jarvis",
    "travis", "service", "harvest", "charles", "starbucks", "java", "jawis", "job is", "assistant"
  ].some(w => clean.includes(w));
}

function startVoiceListener() {
  if (!recognition) return;
  if (state.jarvisIsSpeaking || state.status === "speaking" || state.status === "thinking") {
    return;
  }
  try {
    initAudioContext();
    if (!state.isListening) {
      recognition.start();
    }
  } catch (e) {
    // If already active or in transition
  }
}

function updateMicBadge(statusText, color = "#00e5ff") {
  const badge = document.getElementById("badgeMicStatus");
  if (badge) {
    badge.innerHTML = `<span class="dot" style="background:${color}; box-shadow:0 0 8px ${color};"></span> MIC: ${statusText.toUpperCase()}`;
  }
}

if (SpeechRecognition) {
  recognition = new SpeechRecognition();
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = state.speechLang || "en-IN";

  recognition.onstart = () => {
    if (state.jarvisIsSpeaking || state.status === "speaking" || state.status === "thinking") {
      try { recognition.abort(); } catch(e){}
      state.isListening = false;
      return;
    }
    state.isListening = true;
    currentRecordedText = "";
    document.getElementById("btnVoiceToggle").classList.add("active");
    updateMicBadge("LIVE", "#00ffff");
    
    setAssistantStatus("listening", "LISTENING...");
    appendLog("info", "VOICE", "Microphone audio engine online & listening.");
  };

  function evaluateAndTransmitSpeech(text) {
    if (!text.trim()) return;
    transmitCommand(text);
  }

  recognition.onresult = (event) => {
    if (state.jarvisIsSpeaking || state.status === "speaking" || state.status === "thinking") {
      return;
    }

    let fullTranscript = "";
    let hasFinal = false;
    let finalConfidence = 1.0;
    let finalCount = 0;

    for (let i = 0; i < event.results.length; i++) {
      const item = event.results[i];
      fullTranscript += item[0].transcript + " ";
      if (item.isFinal) {
        hasFinal = true;
        if (item[0].confidence > 0) {
          finalConfidence = Math.min(finalConfidence, item[0].confidence);
          finalCount++;
        }
      }
    }

    const rawText = fullTranscript.trim();
    if (!rawText) return;

    // Reject extremely low-confidence final transcripts (prevents phantom triggers in noise)
    if (hasFinal && finalCount > 0 && finalConfidence < 0.3) {
      console.log("Rejected low-confidence transcript:", rawText, "confidence:", finalConfidence);
      return;
    }

    const currentText = normalizeSpokenText(rawText);
    currentRecordedText = currentText;
    document.getElementById("cmdInput").value = currentText;
    setAssistantStatus("listening", `HEARING: "${currentText.slice(0, 36)}"`);

    if (speechSilenceTimer) clearTimeout(speechSilenceTimer);

    const isFastWake = isWakeCommand(currentText);
    const delay = isFastWake ? 250 : (hasFinal ? 500 : 800);

    speechSilenceTimer = setTimeout(() => {
      if (currentRecordedText && !state.jarvisIsSpeaking && state.status !== "speaking") {
        const textToSubmit = currentRecordedText;
        currentRecordedText = "";
        
        // Voice Cancel feature - robust multi-layer matching
        const checkText = textToSubmit.toLowerCase().trim().replace(/[^a-z\s]/g, "");
        if (/^(cancel|stop|abort|never mind|nevermind|stop processing|cancel that|be quiet|wait|shut up|halt|silence)$/.test(checkText)) {
          setAssistantStatus("listening", "VOICE INPUT CANCELLED.");
          document.getElementById("cmdInput").value = "";
          playSound("blip");
          clearAudioQueue();
          if (wsChat && wsChat.readyState === WebSocket.OPEN) {
              wsChat.send(JSON.stringify({ type: "cancel" }));
          }
          fetch("/api/voice/stop", { method: "POST" }).catch(() => {});
          try { recognition.stop(); } catch(e){} // Force stop to clear buffer
          return;
        }

        evaluateAndTransmitSpeech(textToSubmit);
        try { recognition.stop(); } catch(e){} // Force stop to flush current recognition buffer and prevent duplicates
      }
    }, delay);
  };

  recognition.onerror = (e) => {
    if (e.error === "no-speech") {
      // Natural silence event from Chrome engine, safely ignored
      return;
    }
    console.warn("Speech recognition event:", e.error);
    if (e.error === "not-allowed") {
      updateMicBadge("BLOCKED", "#ff3344");
      appendLog("warning", "PERMISSION", "Microphone access blocked. Click the microphone icon in your browser URL bar to allow audio.");
      state.continuousVoice = false;
      state.isListening = false;
      document.getElementById("btnVoiceToggle").classList.remove("active");
      setAssistantStatus("idle");
    } else if (e.error === "audio-capture") {
      updateMicBadge("NO MIC", "#ffaa00");
      appendLog("warning", "HARDWARE", "No audio input hardware detected. Please connect your microphone.");
    }
  };

  recognition.onend = () => {
    state.isListening = false;
    
    // Strict Turn-Taking Lock: If Jarvis is speaking or thinking, DO NOT restart mic!
    if (state.jarvisIsSpeaking || state.status === "speaking" || state.status === "thinking") {
      updateMicBadge("MUTED (JARVIS SPEAKING)", "#ff3344");
      return;
    }

    if (!state.continuousVoice) {
      updateMicBadge("STANDBY", "#888888");
      document.getElementById("btnVoiceToggle").classList.remove("active");
      if (state.status === "listening") setAssistantStatus("idle");
    } else {
      updateMicBadge("SYNCING", "#00e5ff");
    }

    if (currentRecordedText && !state.jarvisIsSpeaking && state.status !== "speaking") {
      const textToSubmit = currentRecordedText;
      currentRecordedText = "";
      evaluateAndTransmitSpeech(textToSubmit);
    }
    
    // Always-on loop with safe debounce so Chrome Speech API does not raise InvalidStateError
    if (state.continuousVoice && !state.jarvisIsSpeaking && state.status !== "speaking" && state.status !== "thinking") {
      setTimeout(() => {
        if (state.continuousVoice && !state.isListening && !state.jarvisIsSpeaking && state.status !== "speaking" && state.status !== "thinking") {
          try {
            recognition.start();
          } catch(e){}
        }
      }, 150);
    }
  };
}

function evaluateAndTransmitSpeech(transcript) {
  transcript = transcript.trim();
  if (!transcript) return;
  if (state.jarvisIsSpeaking || state.status === "speaking" || state.status === "thinking") {
    console.log("Duplex guard: dropped speech during Jarvis turn:", transcript);
    return;
  }

  // Wake-word filtering (ONLY if explicitly enabled by user)
  if (state.continuousVoice && state.wakeWordEnabled) {
    const isConversationActive = Date.now() < state.conversationActiveUntil;
    const hasWakeWord = containsWakeTrigger(transcript);
    const isDirectAction = /^(open|launch|start|close|kill|check|what|how|who|why|where|tell|turn|set|play|pause|mute|lock|screenshot|status|help|diagnostics)\b/i.test(transcript);

    if (!hasWakeWord && !isConversationActive && !isDirectAction) {
      console.log("Wake word filter: ignoring ambient speech:", transcript);
      setAssistantStatus("listening", "AWAITING 'JARVIS'...");
      document.getElementById("cmdInput").value = "";
      return;
    }

    // Refresh active conversation window for 25 seconds of seamless interaction
    state.conversationActiveUntil = Date.now() + 25000;
  }

  // Instant auditory and visual confirmation
  playSound("ack");
  lockMicForJarvisTurn("PROCESSING");
  setAssistantStatus("thinking", `EXECUTING: "${transcript.slice(0, 24)}"`);

  // Transmit directive immediately!
  transmitCommand(transcript);

  // If not continuous voice, stop active mic
  if (!state.continuousVoice && recognition && state.isListening) {
    try { recognition.stop(); } catch(e){}
  }
}

function toggleVoiceListening() {
  playSound("blip");
  if (!recognition) {
    // Mini PC / Desktop PyWebView mode: Native STT runs in Python backend!
    fetch("/api/voice/listen/toggle", { method: "POST" })
      .then(res => res.json())
      .then(data => {
        if (data.is_muted) {
          updateMicBadge("MUTED", "#888888");
          const btn = document.getElementById("btnVoiceToggle");
          if (btn) btn.classList.remove("active");
          setAssistantStatus("idle", "AWAITING DIRECTIVE");
          appendLog("info", "VOICE", "Microphone listening paused.");
        } else {
          updateMicBadge("LIVE", "#00ffff");
          const btn = document.getElementById("btnVoiceToggle");
          if (btn) btn.classList.add("active");
          setAssistantStatus("listening", `LISTENING (${data.device_name ? data.device_name.slice(0, 18) : "MIC"})`);
          appendLog("info", "VOICE", `Native microphone active on ${data.device_name || "Hardware Mic"}`);
        }
      })
      .catch(err => {
        console.warn("Native mic toggle failed:", err);
        updateMicBadge("LIVE", "#00ffff");
        const btn = document.getElementById("btnVoiceToggle");
        if (btn) btn.classList.toggle("active");
        setAssistantStatus("listening", "LISTENING...");
      });
    return;
  }
  if (state.isListening) {
    state.continuousVoice = false;
    const chk1 = document.getElementById("chkContinuousVoice"); if (chk1) chk1.checked = false;
    try { recognition.stop(); } catch(e){}
    state.isListening = false;
    document.getElementById("btnVoiceToggle").classList.remove("active");
    setAssistantStatus("idle");
    fetch("/api/voice/listen/pause", { method: "POST" }).catch(() => {});
  } else {
    state.continuousVoice = true;
    const chk2 = document.getElementById("chkContinuousVoice"); if (chk2) chk2.checked = true;
    startVoiceListener();
    fetch("/api/voice/listen/resume", { method: "POST" }).catch(() => {});
  }
}

// ----------------------------------------------------
// AUDIO MATRIX & DYNAMIC ROUTING (MINI PC SUPPORT)
// ----------------------------------------------------
let _audioMatrixData = null;

async function syncHardwareMicStatus() {
  try {
    const res = await fetch("/api/audio/matrix");
    if (res.ok) {
      const data = await res.json();
      _audioMatrixData = data;
      
      const badgeMic = document.getElementById("badgeMicStatus");
      const badgeAudio = document.getElementById("labelAudioMatrix");
      
      if (badgeAudio) {
        const outName = data.active_output?.name ? data.active_output.name.split("(")[0].trim().slice(0, 12) : "AUTO";
        badgeAudio.innerText = `AUDIO: ${outName.toUpperCase()}`;
      }
      
      if (badgeMic) {
        const inName = data.active_input?.name || "MIC";
        badgeMic.title = `Microphone: ${inName}\nSpeaker: ${data.active_output?.name || "Default"}\n(Click to configure)`;
      }
    }
  } catch (e) {
    console.warn("Audio matrix sync error:", e);
  }
}

window.openAudioMatrixModal = async function() {
  playSound("blip");
  const modal = document.getElementById("audioMatrixModal");
  if (!modal) return;
  modal.classList.add("active");
  
  const selIn = document.getElementById("selAudioInput");
  const selOut = document.getElementById("selAudioOutput");
  const lblIn = document.getElementById("audioMatrixActiveInLabel");
  const lblOut = document.getElementById("audioMatrixActiveOutLabel");
  
  try {
    const res = await fetch("/api/audio/matrix");
    const data = await res.json();
    _audioMatrixData = data;
    
    if (lblIn) lblIn.innerText = `ACTIVE: ${data.active_input?.name || "None"}`;
    if (lblOut) lblOut.innerText = `ACTIVE: ${data.active_output?.name || "None"}`;
    
    if (selIn) {
      selIn.innerHTML = `<option value="auto">⚡ AUTO-SENSE (Smart failover between Bluetooth / USB / 3.5mm)</option>`;
      (data.inputs || []).forEach(dev => {
        const isSelected = String(data.preferred_input) === String(dev.id);
        const isDefault = dev.is_default ? " [SYSTEM DEFAULT]" : "";
        selIn.innerHTML += `<option value="${dev.id}" ${isSelected ? "selected" : ""}>[#${dev.id}] ${dev.name}${isDefault}</option>`;
      });
      if (String(data.preferred_input) === "auto") selIn.value = "auto";
    }
    
    if (selOut) {
      selOut.innerHTML = `<option value="auto">⚡ AUTO-SENSE (Windows Default Audio Device)</option>`;
      (data.outputs || []).forEach(dev => {
        const isSelected = String(data.preferred_output) === String(dev.id);
        const isDefault = dev.is_default ? " [SYSTEM DEFAULT]" : "";
        selOut.innerHTML += `<option value="${dev.id}" ${isSelected ? "selected" : ""}>[#${dev.id}] ${dev.name}${isDefault}</option>`;
      });
      if (String(data.preferred_output) === "auto") selOut.value = "auto";
    }
  } catch (e) {
    console.error("Failed to load audio matrix:", e);
  }
};

window.closeAudioMatrixModal = function() {
  playSound("blip");
  const modal = document.getElementById("audioMatrixModal");
  if (modal) modal.classList.remove("active");
};

window.saveAudioMatrixSettings = async function() {
  const selIn = document.getElementById("selAudioInput")?.value || "auto";
  const selOut = document.getElementById("selAudioOutput")?.value || "auto";
  
  try {
    const res = await fetch("/api/audio/select", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input_id: selIn, output_id: selOut })
    });
    const data = await res.json();
    playSound("ack");
    appendLog("info", "AUDIO", `Audio routing saved: Mic -> ${data.active_input?.name || "Auto"}, Speaker -> ${data.active_output?.name || "Auto"}`);
    syncHardwareMicStatus();
    closeAudioMatrixModal();
  } catch (e) {
    alert("Failed to save audio settings: " + e.message);
  }
};

window.testMicHardware = async function() {
  const btn = document.getElementById("btnTestMic");
  const bar = document.getElementById("barMicEnergy");
  const lbl = document.getElementById("lblMicEnergyVal");
  const selIn = document.getElementById("selAudioInput")?.value || "auto";
  
  if (btn) {
    btn.disabled = true;
    btn.innerText = "LISTENING... SPEAK NOW!";
  }
  if (lbl) lbl.innerText = "PROBING SIGNAL...";
  if (bar) bar.style.width = "40%";
  
  try {
    const res = await fetch("/api/audio/test_mic", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device_id: selIn })
    });
    const data = await res.json();
    
    if (data.success && data.active) {
      playSound("ack");
      const pct = Math.min(Math.round(data.energy * 2.5), 100);
      if (bar) bar.style.width = `${Math.max(pct, 20)}%`;
      if (lbl) lbl.innerText = `SIGNAL DETECTED! Energy: ${data.energy} (${data.chunks_received} chunks)`;
      appendLog("info", "MIC TEST", `Microphone input verified! Energy: ${data.energy}`);
    } else {
      if (bar) bar.style.width = "5%";
      if (lbl) lbl.innerText = `SILENT (0 chunks or device in sleep mode)`;
      appendLog("warning", "MIC TEST", `No signal detected on selected device. Try switching to Auto-Sense or another mic.`);
    }
  } catch (e) {
    if (lbl) lbl.innerText = "Error: " + e.message;
  } finally {
    setTimeout(() => {
      if (btn) {
        btn.disabled = false;
        btn.innerText = "🎤 TEST LIVE MIC INPUT";
      }
    }, 1500);
  }
};

window.testSpeakerHardware = async function() {
  const btn = document.getElementById("btnTestSpeaker");
  const selOut = document.getElementById("selAudioOutput")?.value || "auto";
  if (btn) {
    btn.disabled = true;
    btn.innerText = "COMMUNICATING...";
  }
  try {
    await fetch("/api/audio/test_speaker", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device_id: selOut })
    });
    appendLog("info", "SPEAKER TEST", "Playing audio verification to selected speaker.");
  } catch (e) {
    console.error("Speaker test error:", e);
  } finally {
    setTimeout(() => {
      if (btn) {
        btn.disabled = false;
        btn.innerText = "🔊 TEST JARVIS SPEAKER VOICE";
      }
    }, 2000);
  }
};


// ----------------------------------------------------
// CODE EXPORT & CLIPBOARD UTILITIES
// ----------------------------------------------------
window.saveCodeSnippetToDesktop = async function(btn) {
  const code = btn.getAttribute("data-code") || "";
  const lang = btn.getAttribute("data-lang") || "txt";
  const origText = btn.innerText;

  const extMap = {
    python: "py", py: "py", javascript: "js", js: "js",
    html: "html", css: "css", json: "json", batch: "bat",
    bat: "bat", powershell: "ps1", ps1: "ps1", sh: "sh",
    bash: "sh", sql: "sql", typescript: "ts", ts: "ts"
  };
  const ext = extMap[lang.toLowerCase()] || "txt";
  const filename = `code_${Date.now()}.${ext}`;

  btn.innerText = "💾 SAVING...";
  btn.disabled = true;

  try {
    const res = await fetch("/api/code/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        code: code,
        filename: filename,
        folder: "Jarvis_Generated_Code"
      })
    });
    const data = await res.json();
    if (data.success) {
      playSound("ack");
      btn.innerText = "✓ SAVED TO DESKTOP";
      btn.style.borderColor = "#38ef7d";
      btn.style.color = "#38ef7d";
      appendLog("info", "FILE SAVED", `Saved '${data.filename}' to Desktop\\${data.folder}`);
    } else {
      btn.innerText = "❌ FAILED";
      btn.style.borderColor = "#ff3366";
      btn.style.color = "#ff3366";
    }
  } catch (err) {
    btn.innerText = "❌ ERROR";
  } finally {
    setTimeout(() => {
      btn.innerText = origText;
      btn.disabled = false;
      btn.style.borderColor = "#00e5ff";
      btn.style.color = "#00e5ff";
    }, 2500);
  }
};

window.copyCodeSnippet = function(btn) {
  const code = btn.getAttribute("data-code") || "";
  if (code) {
    navigator.clipboard.writeText(code);
    const origText = btn.innerText;
    btn.innerText = "✓ COPIED";
    setTimeout(() => { btn.innerText = origText; }, 1500);
  }
};

window.openDesktopCodeFolder = async function() {
  playSound("blip");
  try {
    await fetch("/api/code/open", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ folder: "Jarvis_Generated_Code" })
    });
    appendLog("info", "EXPLORER", "Opened Desktop\\Jarvis_Generated_Code in Windows Explorer.");
  } catch (e) {
    console.error("Open code folder failed:", e);
  }
};

// ----------------------------------------------------
// DEDICATED CHAT FORMATTER & RENDERER
// ----------------------------------------------------
function formatMarkdownSimple(text) {
  if (!text) return "";

  // 1. Extract and format multi-line code blocks ```lang ... ```
  let codeBlocks = [];
  let processed = text.replace(/```([a-zA-Z0-9_\-\+]*)\n([\s\S]*?)```/g, (match, lang, code) => {
    const idx = codeBlocks.length;
    const cleanLang = (lang || 'code').toUpperCase();
    const escapedCode = escapeHtml(code.trim());
    codeBlocks.push(`
      <div class="code-block-container" style="margin: 10px 0; background: rgba(0, 15, 25, 0.95); border: 1px solid rgba(0, 229, 255, 0.35); border-radius: 6px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.5);">
        <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(0, 229, 255, 0.12); padding: 6px 12px; border-bottom: 1px solid rgba(0, 229, 255, 0.25);">
          <span style="font-family: var(--font-mono); font-size: 11px; font-weight: 700; color: #00e5ff; letter-spacing: 1px;">📁 ${cleanLang} SCRIPT</span>
          <div style="display:flex; gap:6px;">
            <button class="btn-run-locally" onclick="executeSandboxCodeFromChat(this)" data-code="${escapeHtml(code.trim())}" data-lang="${cleanLang.toLowerCase()}">⚡ RUN LOCALLY</button>
            <button class="chat-action-btn" onclick="saveCodeSnippetToDesktop(this)" data-code="${escapeHtml(code.trim())}" data-lang="${cleanLang.toLowerCase()}" style="font-size:10px; padding:2px 8px; border-color:#00e5ff; color:#00e5ff;">💾 SAVE</button>
            <button class="chat-action-btn" onclick="copyCodeSnippet(this)" data-code="${escapeHtml(code.trim())}" style="font-size:10px; padding:2px 8px;">📋 COPY</button>
          </div>
        </div>
        <pre style="margin:0; padding:12px; max-height:280px; overflow-y:auto; font-family:var(--font-mono); font-size:12px; line-height:1.5; color:#a0f0ff; background:transparent;"><code>${escapedCode}</code></pre>
        <div class="sandbox-output-block" style="display:none;"></div>
      </div>
    `);
    return `__CODE_BLOCK_${idx}__`;
  });

  let esc = escapeHtml(processed);
  // bold **text**
  esc = esc.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  // italic *text*
  esc = esc.replace(/\*([^\*]+)\*/g, '<em>$1</em>');
  // inline code `code`
  esc = esc.replace(/`([^`]+)`/g, '<code style="background:rgba(0,229,255,0.15); color:#00e5ff; padding:2px 5px; border-radius:3px; font-family:var(--font-mono); font-size:12px;">$1</code>');
  // line breaks
  esc = esc.replace(/\n/g, '<br>');

  // Re-inject rendered code blocks
  codeBlocks.forEach((blockHtml, idx) => {
    esc = esc.replace(`__CODE_BLOCK_${idx}__`, blockHtml);
  });

  return esc;
}

function appendDedicatedChatMessage(role, text, model = null, thoughts = []) {
  const container = document.getElementById("dedicatedChatMessages");
  if (!container) return;

  const msgDiv = document.createElement("div");
  msgDiv.className = `chat-msg ${role === "user" ? "chat-msg-user" : "chat-msg-jarvis"}`;

  const timeStr = new Date().toTimeString().split(" ")[0];
  const modelTag = (role !== "user" && model) ? `<span class="chat-model-pill">${escapeHtml(model.replace("agy/", "").replace("auto/", "").toUpperCase())}</span>` : "";

  let thoughtHtml = "";
  if (thoughts && thoughts.length > 0) {
    const validThoughts = thoughts.filter(t => t && t.trim());
    if (validThoughts.length > 0) {
      thoughtHtml = `
        <details class="chat-thought-block">
          <summary class="chat-thought-summary">🧠 Neural Reasoning (${validThoughts.length} step${validThoughts.length > 1 ? 's' : ''})</summary>
          <div style="margin-top:6px; white-space:pre-wrap; opacity:0.9;">${escapeHtml(validThoughts.join('\n'))}</div>
        </details>
      `;
    }
  }

  const avatarLabel = role === "user" ? "SIR SHAKIL" : "J.A.R.V.I.S.";

  msgDiv.innerHTML = `
    <div class="chat-meta">
      <span>${avatarLabel}</span>
      <span>${timeStr}</span>
      ${modelTag}
    </div>
    ${thoughtHtml}
    <div class="chat-bubble">
      <div class="chat-bubble-text">${formatMarkdownSimple(text)}</div>
      ${role !== "user" ? `
        <div class="chat-actions-bar">
          <button class="chat-action-btn btn-copy-chat" title="Copy to clipboard">📋 COPY</button>
          <button class="chat-action-btn btn-speak-chat" title="Replay on speakers">🔊 SPEAK</button>
          ${text.includes("```") ? `<button class="chat-action-btn" onclick="openDesktopCodeFolder()" title="Open Desktop Code Folder" style="border-color:#38ef7d; color:#38ef7d;">📂 OPEN DESKTOP FOLDER</button>` : ''}
        </div>
      ` : ''}
    </div>
  `;

  // Attach button events
  const copyBtn = msgDiv.querySelector(".btn-copy-chat");
  if (copyBtn) {
    copyBtn.addEventListener("click", () => {
      navigator.clipboard.writeText(text);
      copyBtn.innerText = "✓ COPIED";
      setTimeout(() => { copyBtn.innerText = "📋 COPY"; }, 1500);
    });
  }

  const speakBtn = msgDiv.querySelector(".btn-speak-chat");
  if (speakBtn) {
    speakBtn.addEventListener("click", async () => {
      speakBtn.innerText = "SYNTHESIZING...";
      try {
        const res = await fetch("/api/tts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: text.slice(0, 300) })
        });
        const data = await res.json();
        if (data.base64) {
          playBase64Audio(data.base64, text.length, data.mime || "audio/wav", data.duration || 3.0);
        }
      } catch (e) {}
      speakBtn.innerText = "🔊 SPEAK";
    });
  }

  container.appendChild(msgDiv);
  const body = document.getElementById("dedicatedChatBody");
  if (body) {
    body.scrollTop = body.scrollHeight;
  }
}

// ----------------------------------------------------
// COMMAND TRANSMISSION (DUAL-CHANNEL: WS + REST)
// ----------------------------------------------------
async function transmitCommand(text) {
  text = text.trim();
  if (!text) return;

  playSound("blip");
  appendLog("user", "SIR SHAKIL", text);
  state.chatHistory.push({ role: "user", content: text });
  
  const cmdInput = document.getElementById("cmdInput");
  if (cmdInput) cmdInput.value = "";
  const inpDedicated = document.getElementById("inpDedicatedChat");
  if (inpDedicated) inpDedicated.value = "";

  // Append to dedicated chat view
  appendDedicatedChatMessage("user", text);

  // Eliminate double voice: Only send play_speaker=true if user explicitly chose PC hardware speaker mode!
  const shouldPlaySpeaker = state.audioMode === "speaker";

  // 1. Primary: WebSocket transmission
  if (wsChat && wsChat.readyState === WebSocket.OPEN) {
    try {
      wsChat.send(JSON.stringify({
        type: "message",
        text: text,
        voice_enabled: true,
        play_speaker: shouldPlaySpeaker,
        model: state.selectedModel,
        workspace: state.currentWorkspace || "personal",
        history: state.chatHistory
      }));
      return;
    } catch (e) {
      console.warn("WebSocket send error, falling back to REST:", e);
    }
  }

  // 2. Reliable Fallback: Direct REST API (/api/chat)
  try {
    setAssistantStatus("thinking", "PROCESSING DIRECTIVE");
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        voice_enabled: true,
        play_speaker: shouldPlaySpeaker,
        model: state.selectedModel,
        workspace: state.currentWorkspace || "personal",
        history: state.chatHistory
      })
    });
    const data = await res.json();
    if (data.response) {
      appendLog("jarvis", "J.A.R.V.I.S.", data.response);
      state.chatHistory.push({ role: "model", content: data.response });
      appendDedicatedChatMessage("jarvis", data.response, state.selectedModel, state.currentThoughts ? state.currentThoughts.slice() : []);
      state.currentThoughts = [];
    }
    if (data.audio_base64) {
      playBase64Audio(data.audio_base64, (data.spoken_summary || data.response || "").length, data.mime || "audio/wav", data.duration || 3.0);
    } else {
      unlockMicAfterJarvisTurn();
    }
  } catch (err) {
    console.error("Command transmission error:", err);
    appendLog("warning", "ERROR", `Command delivery failed: ${err.message}`);
    unlockMicAfterJarvisTurn();
  }
}

// ----------------------------------------------------
// REST ACTIONS & CONTROLS
// ----------------------------------------------------
async function triggerPcAction(action, params = {}) {
  playSound("blip");
  try {
    const res = await fetch("/api/action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, params })
    });
    const json = await res.json();
    if (json.base64) {
      // Screenshot preview
      document.getElementById("screenPreviewImg").src = `data:image/png;base64,${json.base64}`;
      document.getElementById("screenModal").classList.add("active");
    }
    return json;
  } catch (e) {
    console.error("Action failed:", e);
  }
}

// ----------------------------------------------------
// WORKSPACE NAVIGATION ENGINE (HOISTED)
// ----------------------------------------------------
const WORKSPACES = {
  "command_center": { id: "command_center", name: "COMMAND CENTER", viewId: "workspaceCommandCenter" },
  "chat": { id: "chat", name: "NEURAL CHAT", viewId: "workspaceChat" },
  "agents": { id: "agents", name: "AGENT NETWORK", viewId: "workspaceAgents" },
  "operations": { id: "operations", name: "OPERATIONS & TASKS", viewId: "workspaceOperations" },
  "research": { id: "research", name: "RESEARCH & INTEL", viewId: "workspaceResearch" },
  "marketing": { id: "marketing", name: "MARKETING HUB", viewId: "workspaceMarketing" },
  "memory": { id: "memory", name: "MEMORY VAULT", viewId: "workspaceMemory" },
  "diagnostics": { id: "diagnostics", name: "SYSTEM DIAGNOSTICS", viewId: "workspaceDiagnostics" },
  "settings": { id: "settings", name: "SETTINGS", viewId: "workspaceSettings" },
  "spatial": { id: "spatial", name: "SPATIAL INTEL (GOD'S EYE)", viewId: "workspaceSpatial" },
  "family": { id: "family", name: "FAMILY SAFETY & MOBILE", viewId: "workspaceFamily" }
};

let currentActiveWorkspace = localStorage.getItem("jarvis_active_workspace") || "command_center";

window.switchWorkspace = function(workspaceKey) {
  if (!WORKSPACES[workspaceKey]) return;

  // Spatial engine power governor deactivation if switching away
  if (currentActiveWorkspace === "spatial" && workspaceKey !== "spatial") {
    try {
      if (window.spatialService && typeof window.spatialService.deactivate === "function") {
        window.spatialService.deactivate();
      }
    } catch (e) {
      console.warn("Spatial deactivation error:", e);
    }
  }

  currentActiveWorkspace = workspaceKey;
  localStorage.setItem("jarvis_active_workspace", workspaceKey);

  // Update Left Sidebar Nav items (.ref-nav-item)
  document.querySelectorAll(".ref-nav-item").forEach(item => {
    if (item.getAttribute("data-workspace") === workspaceKey) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });

  // Update Navigation Rail active classes (.nav-rail-item)
  document.querySelectorAll(".nav-rail-item").forEach(item => {
    if (item.getAttribute("data-workspace") === workspaceKey) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });

  // Update Workspace Views
  document.querySelectorAll(".workspace-view").forEach(view => {
    view.classList.remove("active");
  });
  const targetView = document.getElementById(WORKSPACES[workspaceKey].viewId);
  if (targetView) {
    targetView.classList.add("active");
  }

  // Update Header Badges
  const badgeEl = document.getElementById("currentWorkspaceHeaderBadge");
  if (badgeEl) badgeEl.innerText = WORKSPACES[workspaceKey].name;
  const refActiveWsTitle = document.getElementById("refActiveWsTitle");
  if (refActiveWsTitle) refActiveWsTitle.innerText = WORKSPACES[workspaceKey].name;

  // Auto-focus and workspace-specific refresh triggers
  try {
    if (workspaceKey === "chat") {
      const inp = document.getElementById("inpDedicatedChat");
      if (inp) setTimeout(() => inp.focus(), 150);
    } else if (workspaceKey === "command_center") {
      const inp = document.getElementById("cmdInput");
      if (inp) setTimeout(() => inp.focus(), 150);
    } else if (workspaceKey === "operations") {
      if (typeof window.refreshOperationsPipeline === "function") window.refreshOperationsPipeline();
    } else if (workspaceKey === "memory") {
      if (typeof loadUserFacts === "function") loadUserFacts();
      if (typeof loadResearchedKnowledge === "function") loadResearchedKnowledge();
    } else if (workspaceKey === "family") {
      if (typeof window.renderFamilySafetyWorkspace === "function") window.renderFamilySafetyWorkspace();
    } else if (workspaceKey === "spatial") {
      if (window.spatialService && typeof window.spatialService.activate === "function") {
        window.spatialService.activate();
      }
      const inp = document.getElementById("inpSpatialCmd");
      if (inp) setTimeout(() => inp.focus(), 150);
    } else {
      if (window.spatialService && typeof window.spatialService.deactivate === "function") {
        window.spatialService.deactivate();
      }
    }
  } catch(err) {
    console.warn("Workspace post-switch hook error:", err);
  }

  try { playSound("blip"); } catch(_) {}
  try { showToast(`Switched to ${WORKSPACES[workspaceKey].name}`, "info", 1800); } catch(_) {}
};

// ----------------------------------------------------
// SPATIAL INTELLIGENCE // GOD'S EYE VIEW HUD CONTROLS
// ----------------------------------------------------
function initSpatialHudControls() {
  // 1. Layer Chips
  document.querySelectorAll(".spatial-layer-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const layerId = chip.getAttribute("data-layer");
      chip.classList.toggle("active");
      const isNowActive = chip.classList.contains("active");
      if (window.spatialCommandBus) {
        window.spatialCommandBus.dispatch({
          action: isNowActive ? "ENABLE_LAYER" : "DISABLE_LAYER",
          params: { layerId }
        });
      }
      try { playSound("blip"); } catch(_) {}
    });
  });

  // 2. Sensor Visual Style Buttons
  document.querySelectorAll(".spatial-style-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".spatial-style-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const style = btn.getAttribute("data-style") || "normal";
      
      const container = document.getElementById("workspaceSpatial");
      if (container) {
        container.classList.remove("spatial-mode-surveillance", "spatial-mode-thermal", "spatial-mode-retro", "spatial-mode-noir");
        if (style !== "normal") {
          container.classList.add(`spatial-mode-${style}`);
        }
      }

      if (window.spatialCommandBus) {
        window.spatialCommandBus.dispatch({
          action: "SET_VISUAL_STYLE",
          params: { style }
        });
      }
      try { playSound("click"); } catch(_) {}
    });
  });

  // 3. Quick Camera Location Buttons
  const locMap = {
    "btnSpatialFindMe": { action: "CENTER_ON_SELF" },
    "btnCenterOnSelf": { action: "CENTER_ON_SELF" },
    "btnSpatialHomeGlobe": { action: "HOME_GLOBE" },
    "btnSpatialTokyo": { action: "NAVIGATE", params: { latitude: 35.6762, longitude: 139.6503, rangeM: 15000, name: "Tokyo, Japan" } },
    "btnSpatialLondon": { action: "NAVIGATE", params: { latitude: 51.5074, longitude: -0.1278, rangeM: 15000, name: "London, UK" } },
    "btnSpatialNYC": { action: "NAVIGATE", params: { latitude: 40.7128, longitude: -74.0060, rangeM: 15000, name: "New York City, USA" } },
    "btnSpatialSF": { action: "NAVIGATE", params: { latitude: 37.7749, longitude: -122.4194, rangeM: 15000, name: "San Francisco, USA" } },
    "btnSpatialDhaka": { action: "NAVIGATE", params: { latitude: 23.8103, longitude: 90.4125, rangeM: 15000, name: "Dhaka, Bangladesh" } },
    "btnSpatialCockpit": { action: "ENTER_COCKPIT" }
  };

  Object.entries(locMap).forEach(([btnId, cmd]) => {
    const btn = document.getElementById(btnId);
    if (btn) {
      btn.addEventListener("click", () => {
        if (window.spatialCommandBus) {
          window.spatialCommandBus.dispatch(cmd);
        }
        try { playSound("ack"); } catch(_) {}
      });
    }
  });

  // 3.5 Personal GEOINT & Privacy Controls
  const btnToggleTracking = document.getElementById("btnToggleSelfTracking");
  if (btnToggleTracking) {
    btnToggleTracking.addEventListener("click", async () => {
      if (window.selfLocationEngine) {
        if (!window.selfLocationEngine.isTracking) {
          btnToggleTracking.textContent = "ACQUIRING...";
          const res = await window.selfLocationEngine.startTracking("HIGH_ACCURACY");
          if (res.ok) {
            btnToggleTracking.textContent = "STOP TRACKING";
            btnToggleTracking.style.background = "rgba(255, 82, 82, 0.2)";
            btnToggleTracking.style.borderColor = "#ff5252";
            btnToggleTracking.style.color = "#ff5252";
            const badge = document.getElementById("badgeSelfTrackingState");
            if (badge) {
              badge.textContent = "LIVE GPS";
              badge.style.background = "rgba(0, 240, 255, 0.2)";
              badge.style.color = "#00f0ff";
            }
            const pill = document.getElementById("hudSpatialSelfStatus");
            if (pill) {
              pill.textContent = "LIVE GPS";
              pill.style.color = "#00f0ff";
            }
          } else {
            btnToggleTracking.textContent = "ENABLE TRACKING";
            showToast(`Location Error: ${res.error || "Permission Denied"}`, "error", 3000);
          }
        } else {
          window.selfLocationEngine.stopTracking();
          btnToggleTracking.textContent = "ENABLE TRACKING";
          btnToggleTracking.style.background = "rgba(0, 240, 255, 0.15)";
          btnToggleTracking.style.borderColor = "#00f0ff";
          btnToggleTracking.style.color = "#00f0ff";
          const badge = document.getElementById("badgeSelfTrackingState");
          if (badge) {
            badge.textContent = "DISABLED";
            badge.style.background = "#222";
            badge.style.color = "#aaa";
          }
          const pill = document.getElementById("hudSpatialSelfStatus");
          if (pill) {
            pill.textContent = "STANDBY (OFF)";
            pill.style.color = "#888";
          }
        }
      }
      try { playSound("click"); } catch(_) {}
    });
  }

  const chkHistory = document.getElementById("chkLocationHistory");
  if (chkHistory) {
    chkHistory.addEventListener("change", () => {
      if (window.locationHistoryManager) {
        if (chkHistory.checked) {
          window.locationHistoryManager.enableHistory("session_only");
          showToast("Breadcrumb trail enabled for current session", "info", 2000);
        } else {
          window.locationHistoryManager.disableHistory();
        }
      }
    });
  }

  const btnPurge = document.getElementById("btnPurgeHistory");
  if (btnPurge) {
    btnPurge.addEventListener("click", () => {
      if (window.locationHistoryManager) {
        const res = window.locationHistoryManager.clearAllHistory();
        showToast(`Purged ${res.deletedCount} location breadcrumb points`, "info", 2000);
      }
      try { playSound("blip"); } catch(_) {}
    });
  }

  // Hook live location telemetry feedback to HUD
  if (window.spatialEventBus) {
    window.spatialEventBus.on("spatial.location.fused", (obs) => {
      const accEl = document.getElementById("lblSelfAccuracy");
      const confEl = document.getElementById("lblSelfConfidence");
      if (accEl) accEl.textContent = `±${Math.round(obs.horizontalAccuracyMeters)}M · ${obs.accuracyLevel.code}`;
      if (confEl) confEl.textContent = `${Math.round(obs.confidenceScore * 100)}% (${obs.confidenceLabel})`;

      // Trigger building resolution if within accuracy threshold
      if (window.buildingResolutionService) {
        window.buildingResolutionService.resolveBuildingAndAddress(obs.latitude, obs.longitude, obs.horizontalAccuracyMeters);
      }
    });

    window.spatialEventBus.on("spatial.building.resolved", (res) => {
      const bldgEl = document.getElementById("lblSelfBuilding");
      if (bldgEl) {
        if (res.buildingCandidate) {
          bldgEl.textContent = res.buildingCandidate.name;
          bldgEl.style.color = "#00ffcc";
        } else if (res.address?.displayName) {
          bldgEl.textContent = res.address.displayName.substring(0, 32) + "...";
          bldgEl.style.color = "#aaa";
        } else {
          bldgEl.textContent = res.status;
          bldgEl.style.color = "#888";
        }
      }
    });
  }

  // 4. Spatial Direct Input Dispatch
  const inp = document.getElementById("inpSpatialCmd");
  const sendBtn = document.getElementById("btnSpatialSend");

  const submitSpatialCommand = () => {
    if (!inp) return;
    const text = inp.value.trim();
    if (!text) return;
    inp.value = "";
    
    // Direct to Jarvis AI Brain — classified as SPATIAL_INTELLIGENCE
    transmitCommand(`Jarvis, ${text}`);
    try { playSound("send"); } catch(_) {}
  };

  if (sendBtn) sendBtn.addEventListener("click", submitSpatialCommand);
  if (inp) {
    inp.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        submitSpatialCommand();
      }
    });
  }
}

// ----------------------------------------------------
// FAMILY SAFETY & REMOTE COMPANION ENGINE
// ----------------------------------------------------
let pairingCountdownTimer = null;

function initFamilySafetyUi() {
  // 1. Pair Phone Button & Modal
  const btnPair = document.getElementById("btnPairDevice");
  const modalPair = document.getElementById("pairingCodeModal");
  const btnClosePair = document.getElementById("btnClosePairing");
  const lblCode = document.getElementById("lblPairingCode");
  const lblTimer = document.getElementById("lblPairingTimer");

  if (btnPair) {
    btnPair.addEventListener("click", async () => {
      playSound("blip");
      if (modalPair) modalPair.style.display = "block";
      if (lblCode) lblCode.innerText = "GEN...";

      try {
        const res = await fetch("/api/family/devices/pair/init", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ device_name: "Phone Companion" })
        });
        const data = await res.json();
        if (data.pairing_code) {
          if (lblCode) lblCode.innerText = data.pairing_code;
          let remaining = data.expires_in_seconds || 600;
          if (pairingCountdownTimer) clearInterval(pairingCountdownTimer);
          pairingCountdownTimer = setInterval(() => {
            remaining--;
            if (lblTimer) lblTimer.innerText = `Expires in ${remaining}s`;
            if (remaining <= 0) {
              clearInterval(pairingCountdownTimer);
              if (lblCode) lblCode.innerText = "EXPIRED";
            }
          }, 1000);
        } else {
          if (lblCode) lblCode.innerText = "ERROR";
          showToast(data.error || "Pairing initiation failed", "error");
        }
      } catch (err) {
        if (lblCode) lblCode.innerText = "FAIL";
        showToast("Network error: " + err.message, "error");
      }
    });
  }

  if (btnClosePair && modalPair) {
    btnClosePair.addEventListener("click", () => {
      modalPair.style.display = "none";
      if (pairingCountdownTimer) clearInterval(pairingCountdownTimer);
    });
  }

  // 2. Scan Wi-Fi Discovery Button
  const btnScanWifi = document.getElementById("btnScanWifi");
  if (btnScanWifi) {
    btnScanWifi.addEventListener("click", async () => {
      playSound("ack");
      btnScanWifi.disabled = true;
      btnScanWifi.innerText = "SCANNING...";
      showToast("Scanning local subnet for active devices...", "info", 2000);
      try {
        const res = await fetch("/api/family/network/scan", { method: "POST" });
        const data = await res.json();
        showToast(`Discovered ${data.discovered_nodes?.length || 0} active local devices`, "success", 2500);
        await window.renderFamilySafetyWorkspace();
      } catch (err) {
        showToast("Wi-Fi scan failed: " + err.message, "error");
      } finally {
        btnScanWifi.disabled = false;
        btnScanWifi.innerText = "📶 SCAN WI-FI";
      }
    });
  }

  // 3. Master Location Kill Switch
  const btnKillSwitch = document.getElementById("btnMasterKillSwitch");
  if (btnKillSwitch) {
    btnKillSwitch.addEventListener("click", async () => {
      playSound("alert");
      if (!confirm("🚨 MASTER LOCATION KILL SWITCH\n\nAre you sure you want to instantly revoke and halt ALL family location sharing?")) {
        return;
      }
      try {
        const res = await fetch("/api/family/consent/kill_switch", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ reason: "Emergency master kill switch triggered by Sir Shakil from HUD" })
        });
        const data = await res.json();
        showToast("🛑 EMERGENCY: All family location sharing has been revoked!", "error", 4000);
        appendLog("warning", "KILL SWITCH", "Master location kill switch activated. All consent tokens purged.");
        await window.renderFamilySafetyWorkspace();
      } catch (err) {
        showToast("Kill switch execution failed: " + err.message, "error");
      }
    });
  }

  // 4. Test Safety Alert Button
  const btnTestAlert = document.getElementById("btnTriggerTestAlert");
  if (btnTestAlert) {
    btnTestAlert.addEventListener("click", async () => {
      playSound("ack");
      try {
        const res = await fetch("/api/family/alerts/test", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ severity: "HIGH", message: "Manual test alert from J.A.R.V.I.S. HUD" })
        });
        const data = await res.json();
        showToast("Triggered test alert: " + (data.message || "Alert dispatched"), "warning", 3000);
        await window.renderFamilySafetyWorkspace();
      } catch (err) {
        showToast("Test alert failed: " + err.message, "error");
      }
    });
  }

  // 5. Voluntary Check-in Buttons
  const btnSafe = document.getElementById("btnCheckInSafe");
  if (btnSafe) {
    btnSafe.addEventListener("click", async () => {
      playSound("ack");
      try {
        const res = await fetch("/api/family/checkins", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: "SAFE", note: "Checked in via desktop HUD" })
        });
        showToast("🟢 Voluntary Check-in: Marked as SAFE", "success", 2500);
        await window.renderFamilySafetyWorkspace();
      } catch (err) {
        showToast("Check-in failed: " + err.message, "error");
      }
    });
  }

  const btnNeedHelp = document.getElementById("btnCheckInNeedHelp");
  if (btnNeedHelp) {
    btnNeedHelp.addEventListener("click", async () => {
      playSound("alert");
      try {
        const res = await fetch("/api/family/checkins", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: "NEED_HELP", note: "Emergency SOS triggered from HUD" })
        });
        showToast("🔴 EMERGENCY SOS Dispatched to Family Platform", "error", 4000);
        await window.renderFamilySafetyWorkspace();
      } catch (err) {
        showToast("SOS failed: " + err.message, "error");
      }
    });
  }

  // 6. Schedule Check-in Button
  const btnSchedCheckin = document.getElementById("btnScheduleCheckIn");
  if (btnSchedCheckin) {
    btnSchedCheckin.addEventListener("click", async () => {
      const mins = prompt("Schedule next voluntary check-in in how many minutes?", "60");
      if (!mins || isNaN(parseInt(mins, 10))) return;
      try {
        const res = await fetch("/api/family/checkins/schedule", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ interval_minutes: parseInt(mins, 10) })
        });
        showToast(`Scheduled voluntary check-in in ${mins} minutes`, "info", 2500);
        await window.renderFamilySafetyWorkspace();
      } catch (err) {
        showToast("Schedule failed: " + err.message, "error");
      }
    });
  }
}

window.renderFamilySafetyWorkspace = async function() {
  // A. Devices List
  const deviceList = document.getElementById("familyDeviceList");
  if (deviceList) {
    try {
      const res = await fetch("/api/family/devices");
      const data = await res.json();
      const devices = data.devices || [];
      if (devices.length === 0) {
        deviceList.innerHTML = `<div style="color:#777; font-size:12px; text-align:center; padding:20px;">No registered devices. Click <strong>+ PAIR PHONE</strong> to connect a mobile device.</div>`;
      } else {
        deviceList.innerHTML = devices.map(d => {
          const isOnline = d.status === "ACTIVE" || d.status === "ONLINE";
          const statusColor = isOnline ? "#38ef7d" : "#888";
          return `
            <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(0,240,255,0.15); border-radius:6px; padding:10px; display:flex; justify-content:space-between; align-items:center;">
              <div>
                <div style="font-weight:700; color:#fff; font-size:13px; display:flex; align-items:center; gap:6px;">
                  <span>📱</span>
                  <span>${escapeHtml(d.device_name || d.device_id)}</span>
                  <span style="font-size:10px; color:${statusColor}; border:1px solid ${statusColor}; padding:1px 5px; border-radius:3px;">${escapeHtml(d.status || 'OFFLINE')}</span>
                </div>
                <div style="font-size:11px; color:#aaa; margin-top:3px;">
                  Member: <strong style="color:#00e5ff;">${escapeHtml(d.member_name || 'Primary')}</strong> · IP: ${escapeHtml(d.ip_address || 'Local')} · Batt: ${d.battery_level ? d.battery_level + '%' : 'N/A'}
                </div>
              </div>
              <div>
                <button class="hud-btn" onclick="window.revokeFamilyDevice('${escapeHtml(d.device_id)}')" style="padding:3px 8px; font-size:10px; border-color:#ff5252; color:#ff5252;">REVOKE</button>
              </div>
            </div>
          `;
        }).join("");
      }
    } catch (err) {
      deviceList.innerHTML = `<div style="color:#ff5252; font-size:11px; padding:10px;">Failed to load devices: ${escapeHtml(err.message)}</div>`;
    }
  }

  // B. Alerts List
  const alertsList = document.getElementById("familyAlertsList");
  if (alertsList) {
    try {
      const res = await fetch("/api/family/alerts");
      const data = await res.json();
      const alerts = data.alerts || [];
      if (alerts.length === 0) {
        alertsList.innerHTML = `<div style="color:#777; font-size:12px; text-align:center; padding:20px;">Zero active safety alerts. All family safety indicators normal.</div>`;
      } else {
        alertsList.innerHTML = alerts.map(a => {
          const sevColor = a.severity === "CRITICAL" ? "#ff3344" : a.severity === "HIGH" ? "#ff7744" : a.severity === "MEDIUM" ? "#ffaa00" : "#00e5ff";
          return `
            <div style="background:rgba(255,50,50,0.06); border:1px solid ${sevColor}; border-radius:6px; padding:10px; display:flex; justify-content:space-between; align-items:center;">
              <div>
                <div style="display:flex; align-items:center; gap:6px;">
                  <span style="background:${sevColor}; color:#000; font-size:9px; font-weight:900; padding:1px 5px; border-radius:3px;">${escapeHtml(a.severity)}</span>
                  <span style="font-weight:700; color:#fff; font-size:12px;">${escapeHtml(a.message || a.title)}</span>
                </div>
                <div style="font-size:10px; color:#aaa; margin-top:4px;">${new Date(a.created_at || Date.now()).toLocaleTimeString()}</div>
              </div>
              <button class="hud-btn" onclick="window.dismissFamilyAlert('${escapeHtml(a.alert_id)}')" style="padding:3px 8px; font-size:10px;">DISMISS</button>
            </div>
          `;
        }).join("");
      }
    } catch (err) {
      alertsList.innerHTML = `<div style="color:#ff5252; font-size:11px; padding:10px;">Failed to load alerts: ${escapeHtml(err.message)}</div>`;
    }
  }

  // C. Check-ins Status
  const lblNextCheckin = document.getElementById("lblNextCheckin");
  const lblCheckinStatus = document.getElementById("lblCheckinStatus");
  if (lblNextCheckin || lblCheckinStatus) {
    try {
      const res = await fetch("/api/family/checkins/status");
      const data = await res.json();
      if (lblNextCheckin) lblNextCheckin.innerText = data.next_scheduled ? new Date(data.next_scheduled).toLocaleTimeString() : "None scheduled";
      if (lblCheckinStatus) lblCheckinStatus.innerText = data.status || "ALL CLEAR";
    } catch (err) {}
  }

  // D. Persistent Remote Tasks
  const tasksList = document.getElementById("remoteTasksList");
  if (tasksList) {
    try {
      const res = await fetch("/api/remote/tasks");
      const data = await res.json();
      const tasks = data.tasks || [];
      if (tasks.length === 0) {
        tasksList.innerHTML = `<div style="color:#777; font-size:12px; text-align:center; padding:20px;">No persistent tasks currently running.</div>`;
      } else {
        tasksList.innerHTML = tasks.map(t => {
          const isPaused = t.status === "PAUSED";
          const prog = t.progress_pct || 0;
          return `
            <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(0,240,255,0.15); border-radius:6px; padding:10px;">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:700; color:#fff; font-size:12px;">${escapeHtml(t.description || t.task_id)}</span>
                <span style="font-size:10px; color:#00e5ff; border:1px solid #00e5ff; padding:1px 5px; border-radius:3px;">${escapeHtml(t.status)}</span>
              </div>
              <div class="ref-progress-bar-bg" style="height:4px; margin-top:6px;">
                <div class="ref-progress-bar-fill" style="width:${prog}%;"></div>
              </div>
              <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px; font-size:11px;">
                <span style="color:#888;">Progress: ${prog}%</span>
                <div style="display:flex; gap:6px;">
                  ${isPaused 
                    ? `<button class="hud-btn" onclick="window.resumeRemoteTask('${escapeHtml(t.task_id)}')" style="padding:2px 6px; font-size:10px; border-color:#38ef7d; color:#38ef7d;">RESUME</button>`
                    : `<button class="hud-btn" onclick="window.pauseRemoteTask('${escapeHtml(t.task_id)}')" style="padding:2px 6px; font-size:10px; border-color:#ffaa00; color:#ffaa00;">PAUSE</button>`
                  }
                  <button class="hud-btn" onclick="window.cancelRemoteTask('${escapeHtml(t.task_id)}')" style="padding:2px 6px; font-size:10px; border-color:#ff5252; color:#ff5252;">CANCEL</button>
                </div>
              </div>
            </div>
          `;
        }).join("");
      }
    } catch (err) {
      tasksList.innerHTML = `<div style="color:#ff5252; font-size:11px; padding:10px;">Failed to load tasks: ${escapeHtml(err.message)}</div>`;
    }
  }
};

window.revokeFamilyDevice = async function(deviceId) {
  if (!confirm(`Revoke and unpair device ${deviceId}?`)) return;
  try {
    const res = await fetch("/api/family/devices/revoke", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device_id: deviceId })
    });
    showToast("Device revoked and disconnected", "info");
    await window.renderFamilySafetyWorkspace();
  } catch (err) {
    showToast("Revoke failed: " + err.message, "error");
  }
};

window.dismissFamilyAlert = async function(alertId) {
  try {
    const res = await fetch("/api/family/alerts/dismiss", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ alert_id: alertId })
    });
    showToast("Alert dismissed", "info");
    await window.renderFamilySafetyWorkspace();
  } catch (err) {
    showToast("Dismiss failed: " + err.message, "error");
  }
};

window.pauseRemoteTask = async function(taskId) {
  try {
    await fetch("/api/remote/tasks/pause", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task_id: taskId })
    });
    showToast("Task paused", "info");
    await window.renderFamilySafetyWorkspace();
  } catch (err) {
    showToast("Pause error: " + err.message, "error");
  }
};

window.resumeRemoteTask = async function(taskId) {
  try {
    await fetch("/api/remote/tasks/resume", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task_id: taskId })
    });
    showToast("Task resumed", "info");
    await window.renderFamilySafetyWorkspace();
  } catch (err) {
    showToast("Resume error: " + err.message, "error");
  }
};

window.cancelRemoteTask = async function(taskId) {
  if (!confirm(`Cancel and terminate task ${taskId}?`)) return;
  try {
    await fetch("/api/remote/tasks/cancel", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task_id: taskId })
    });
    showToast("Task canceled", "warning");
    await window.renderFamilySafetyWorkspace();
  } catch (err) {
    showToast("Cancel error: " + err.message, "error");
  }
};

// ----------------------------------------------------
// REFERENCE COMMAND CENTER ENGINE & COMPONENT WIRING
// ----------------------------------------------------
let _refCommandCenterInitialized = false;

function initReferenceCommandCenter() {
  if (_refCommandCenterInitialized) return;
  _refCommandCenterInitialized = true;

  // Family Safety Controls Wire-up
  try {
    initFamilySafetyUi();
  } catch (e) {
    console.error("Family Safety UI initialization error:", e);
  }

  // Spatial Intel Controls Wire-up
  try {
    initSpatialHudControls();
  } catch (e) {
    console.error("Spatial HUD Controls initialization error:", e);
  }

  // 1. Initialize 3D Holographic Core & Constellation Graph immediately
  try {
    initHologramCore();
  } catch (e) {
    console.error("Hologram Core initialization error:", e);
  }

  try {
    initConstellationGraph();
  } catch (e) {
    console.error("Constellation Graph initialization error:", e);
  }

  // 2. Wire Left Sidebar Nav Items (14 items)
  document.querySelectorAll(".ref-nav-item").forEach(item => {
    item.addEventListener("click", () => {
      const ws = item.getAttribute("data-workspace");
      if (ws && typeof window.switchWorkspace === "function") {
        window.switchWorkspace(ws);
      }
    });
    item.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        const ws = item.getAttribute("data-workspace");
        if (ws && typeof window.switchWorkspace === "function") {
          window.switchWorkspace(ws);
        }
      }
    });
  });

  // 3. Wire Quick Launch Buttons
  document.querySelectorAll(".ref-quick-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const action = btn.getAttribute("data-action");
      const target = btn.getAttribute("data-target");
      if (action === "launch" && target) {
        playSound("ack");
        showToast(`Launching ${target.toUpperCase()}...`, "info", 2000);
        triggerPcAction("launch_app", { app_name: target });
      }
    });
  });

  const btnQuickEmails = document.getElementById("btnQuickEmails");
  if (btnQuickEmails) {
    btnQuickEmails.addEventListener("click", () => {
      playSound("ack");
      transmitCommand("Jarvis, check my emails and give me an executive brief");
    });
  }

  const btnQuickEventbrite = document.getElementById("btnQuickEventbrite");
  if (btnQuickEventbrite) {
    btnQuickEventbrite.addEventListener("click", () => {
      playSound("ack");
      window.switchWorkspace("agents");
      const b = document.querySelector(".spec-tab-btn[data-spec='seo']");
      if (b) b.click();
    });
  }

  const btnQuickAds = document.getElementById("btnQuickAds");
  if (btnQuickAds) {
    btnQuickAds.addEventListener("click", () => {
      playSound("ack");
      window.switchWorkspace("marketing");
    });
  }

  const btnQuickJarvisBrowser = document.getElementById("btnQuickJarvisBrowser");
  if (btnQuickJarvisBrowser) {
    btnQuickJarvisBrowser.addEventListener("click", () => {
      playSound("ack");
      triggerPcAction("launch_app", { app_name: "chrome_profile" });
    });
  }

  const btnQuickAddApp = document.getElementById("btnQuickAddApp");
  if (btnQuickAddApp) {
    btnQuickAddApp.addEventListener("click", () => {
      const app = prompt("Enter Windows application or executable name to launch (e.g., notepad, calc, spotify):");
      if (app && app.trim()) {
        playSound("ack");
        triggerPcAction("launch_app", { app_name: app.trim().toLowerCase() });
      }
    });
  }

  // 4. Wire 8 Orbital Nodes around the Hologram Helmet
  const orbitalActions = {
    nodeListening: () => { toggleVoiceListening(); },
    nodeProcessing: () => { transmitCommand("Jarvis, system status report"); },
    nodeResearching: () => { window.switchWorkspace("research"); },
    nodeExecuting: () => { window.switchWorkspace("operations"); },
    nodeGenerating: () => { 
      window.switchWorkspace("agents");
      const b = document.querySelector(".spec-tab-btn[data-spec='coding']");
      if (b) b.click();
    },
    nodeSpeaking: () => {
      playSound("ack");
      fetch("/api/voice/test", { method: "POST" })
        .then(r => r.json())
        .then(d => { if (d.base64) playBase64Audio(d.base64); })
        .catch(console.error);
    },
    nodeMonitoring: () => { window.switchWorkspace("diagnostics"); },
    nodeWaiting: () => {
      playSound("blip");
      setAssistantStatus("idle", "Standby mode active");
      showToast("J.A.R.V.I.S. in standby mode", "info", 1500);
    }
  };

  document.querySelectorAll(".ref-orbital-node").forEach(node => {
    node.addEventListener("click", () => {
      playSound("blip");
      document.querySelectorAll(".ref-orbital-node").forEach(n => n.classList.remove("active"));
      node.classList.add("active");
      const label = node.querySelector(".ref-orbital-label")?.innerText || "NODE";
      const statusEl = document.getElementById("coreStatusLabel");
      if (statusEl) statusEl.innerText = label;
      if (orbitalActions[node.id]) {
        orbitalActions[node.id]();
      }
    });
  });

  // 5. Wire Central Pedestal Mic Button
  const btnVoiceToggle = document.getElementById("btnVoiceToggle");
  if (btnVoiceToggle) {
    btnVoiceToggle.addEventListener("click", () => {
      toggleVoiceListening();
    });
  }

  // 6. Wire Equalizer Waveforms Animation on Pedestal
  setInterval(() => {
    const isSpeaking = state.status === "speaking";
    const isListening = state.isListening || state.status === "listening";
    const bars = document.querySelectorAll(".ref-waveform-bar");
    bars.forEach((bar, idx) => {
      if (isSpeaking) {
        const h = Math.floor(Math.random() * 22) + 4;
        bar.style.height = `${h}px`;
      } else if (isListening) {
        const h = Math.floor(Math.sin(Date.now() / 150 + idx) * 8) + 10;
        bar.style.height = `${h}px`;
      } else {
        const defaultHeights = [6, 12, 18, 9, 14, 14, 9, 18, 12, 6];
        bar.style.height = `${defaultHeights[idx % defaultHeights.length]}px`;
      }
    });
  }, 100);

  // 7. Wire Conversation Deck Tabs
  document.querySelectorAll(".ref-conv-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      const tabName = tab.getAttribute("data-tab");
      if (!tabName) return;
      document.querySelectorAll(".ref-conv-tab").forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      playSound("blip");

      if (tabName === "research") window.switchWorkspace("research");
      else if (tabName === "business") window.switchWorkspace("marketing");
      else if (tabName === "memory") window.switchWorkspace("memory");
      else if (tabName === "monitor" || tabName === "diagnostics") window.switchWorkspace("diagnostics");
      else if (tabName === "conversation") window.switchWorkspace("command_center");
    });
  });

  const btnAddNewTab = document.getElementById("btnAddNewTab");
  if (btnAddNewTab) {
    btnAddNewTab.addEventListener("click", () => {
      const title = prompt("Enter new workspace tab title:");
      if (title && title.trim()) {
        const newTab = document.createElement("div");
        newTab.className = "ref-conv-tab";
        newTab.innerText = `📂 ${title.trim().toUpperCase()}`;
        newTab.setAttribute("data-tab", "custom_" + Date.now());
        newTab.addEventListener("click", () => {
          document.querySelectorAll(".ref-conv-tab").forEach(t => t.classList.remove("active"));
          newTab.classList.add("active");
          playSound("blip");
        });
        btnAddNewTab.parentNode.insertBefore(newTab, btnAddNewTab);
        playSound("ack");
        showToast(`Created tab: ${title.trim()}`, "success", 2000);
      }
    });
  }

  // 8. Wire Mini Chat History Sidebar (New Chat & Search)
  const btnNewChat = document.getElementById("btnNewChat");
  if (btnNewChat) {
    btnNewChat.addEventListener("click", () => {
      playSound("ack");
      const container = document.getElementById("dedicatedChatMessages");
      if (container) {
        container.innerHTML = `
          <div class="ref-chat-bubble" style="max-width:92%;">
            <div class="ref-bubble-header">
              <span class="ref-bubble-author">🤖 J.A.R.V.I.S.</span>
              <span class="ref-bubble-time">${new Date().toTimeString().split(" ")[0].slice(0, 5)}</span>
            </div>
            <div class="ref-bubble-text">
              New session initialized, Sir. All operational systems online and awaiting your command.
            </div>
          </div>
        `;
      }
      showToast("New conversation session started", "info", 2000);
      const cmdInp = document.getElementById("cmdInput");
      if (cmdInp) cmdInp.focus();
    });
  }

  const inpSearchChats = document.getElementById("inpSearchChats");
  if (inpSearchChats) {
    inpSearchChats.addEventListener("input", (e) => {
      const q = e.target.value.toLowerCase().trim();
      document.querySelectorAll(".ref-session-item").forEach(item => {
        const title = (item.querySelector(".ref-session-title")?.innerText || "").toLowerCase();
        item.style.display = (!q || title.includes(q)) ? "flex" : "none";
      });
    });
  }

  document.querySelectorAll(".ref-session-item").forEach(item => {
    item.addEventListener("click", () => {
      document.querySelectorAll(".ref-session-item").forEach(i => i.classList.remove("active"));
      item.classList.add("active");
      playSound("blip");
      const title = item.querySelector(".ref-session-title")?.innerText || "Conversation";
      showToast(`Loaded session: ${title}`, "info", 1800);
    });
  });

  // 9. Wire Header Links and View All buttons
  const btnViewAllTasks = document.getElementById("btnViewAllTasks");
  if (btnViewAllTasks) {
    btnViewAllTasks.addEventListener("click", () => {
      playSound("blip");
      window.switchWorkspace("operations");
    });
  }

  const btnViewAllAgents = document.getElementById("btnViewAllAgents");
  if (btnViewAllAgents) {
    btnViewAllAgents.addEventListener("click", () => {
      playSound("blip");
      window.switchWorkspace("agents");
    });
  }

  const btnViewAllNotifs = document.getElementById("btnViewAllNotifs");
  if (btnViewAllNotifs) {
    btnViewAllNotifs.addEventListener("click", () => {
      playSound("blip");
      const notifDrawer = document.getElementById("notificationDrawer");
      if (notifDrawer) notifDrawer.classList.toggle("open");
    });
  }

  const btnReviewApproval = document.getElementById("btnReviewApproval");
  if (btnReviewApproval) {
    btnReviewApproval.addEventListener("click", () => {
      playSound("blip");
      const card = document.getElementById("refApprovalCard");
      if (card) {
        card.scrollIntoView({ behavior: "smooth", block: "center" });
        card.style.boxShadow = "0 0 20px rgba(255, 171, 0, 0.6)";
        setTimeout(() => { card.style.boxShadow = ""; }, 2000);
      }
    });
  }

  // 10. Wire Approval Center Inline Actions
  const btnInlineApprove = document.getElementById("btnInlineApprove");
  const btnInlineDeny = document.getElementById("btnInlineDeny");
  const refApprovalCard = document.getElementById("refApprovalCard");

  if (btnInlineApprove) {
    btnInlineApprove.addEventListener("click", async () => {
      playSound("ack");
      btnInlineApprove.innerText = "APPROVING...";
      btnInlineApprove.disabled = true;
      try {
        await fetch("/api/orchestrator/approve", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ task_id: "install_playwright" })
        });
        showToast("✔ Approved: Package 'playwright' authorized.", "success", 3000);
        if (refApprovalCard) {
          refApprovalCard.innerHTML = `<div style="padding:14px; color:#38ef7d; font-family:var(--font-mono); font-size:11px; text-align:center;">✔ Direct authorization granted.</div>`;
        }
      } catch(e) {
        showToast("Approval error: " + e.message, "error", 3000);
        btnInlineApprove.innerText = "Approve";
        btnInlineApprove.disabled = false;
      }
    });
  }

  if (btnInlineDeny) {
    btnInlineDeny.addEventListener("click", async () => {
      playSound("alert");
      btnInlineDeny.innerText = "DENYING...";
      btnInlineDeny.disabled = true;
      try {
        await fetch("/api/orchestrator/reject", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ task_id: "install_playwright", reason: "Denied by operator" })
        });
        showToast("❌ Denied: Action aborted by user.", "warning", 3000);
        if (refApprovalCard) {
          refApprovalCard.innerHTML = `<div style="padding:14px; color:#ff3344; font-family:var(--font-mono); font-size:11px; text-align:center;">❌ Authorization rejected by operator.</div>`;
        }
      } catch(e) {
        showToast("Deny error: " + e.message, "error", 3000);
        btnInlineDeny.innerText = "Deny";
        btnInlineDeny.disabled = false;
      }
    });
  }

  // 11. Wire Native Window Controls
  const btnWinMin = document.getElementById("btnWinMinimize");
  if (btnWinMin) {
    btnWinMin.addEventListener("click", () => {
      playSound("blip");
      if (window.pywebview && window.pywebview.api && window.pywebview.api.minimize_window) {
        window.pywebview.api.minimize_window();
      }
    });
  }

  const btnWinMax = document.getElementById("btnWinMaximize");
  if (btnWinMax) {
    btnWinMax.addEventListener("click", () => {
      playSound("blip");
      if (window.pywebview && window.pywebview.api && window.pywebview.api.maximize_window) {
        window.pywebview.api.maximize_window();
      }
    });
  }

  const btnWinClose = document.getElementById("btnWinClose");
  if (btnWinClose) {
    btnWinClose.addEventListener("click", () => {
      playSound("alert");
      if (window.pywebview && window.pywebview.api && window.pywebview.api.close_window) {
        window.pywebview.api.close_window();
      } else {
        window.close();
      }
    });
  }

  // Double-click top bar to toggle maximize
  const refTopBar = document.getElementById("refTopBar");
  if (refTopBar) {
    refTopBar.addEventListener("dblclick", (e) => {
      if (e.target.closest("button, .ref-win-btn, .ref-status-pill, .ref-user-badge, input, select")) return;
      if (window.pywebview && window.pywebview.api && window.pywebview.api.maximize_window) {
        window.pywebview.api.maximize_window();
      }
    });
  }

  // 12. Wire Bottom Status Bar Buttons
  const btnOpenBrowserBottom = document.getElementById("btnOpenBrowserBottom");
  if (btnOpenBrowserBottom) {
    btnOpenBrowserBottom.addEventListener("click", () => {
      playSound("ack");
      triggerPcAction("launch_app", { app_name: "chrome_profile" });
    });
  }

  const btnLockPcBottom = document.getElementById("btnLockPcBottom");
  if (btnLockPcBottom) {
    btnLockPcBottom.addEventListener("click", () => {
      playSound("alert");
      triggerPcAction("lock", {});
      showToast("🔒 Workstation locked.", "warning", 2500);
    });
  }

  const btnEmergencyStopBottom = document.getElementById("btnEmergencyStopBottom");
  if (btnEmergencyStopBottom) {
    btnEmergencyStopBottom.addEventListener("click", () => {
      window.executeEmergencyStop();
    });
  }

  // 13. Top Header Notification and Settings buttons
  const btnSettingsHeader = document.getElementById("btnSettingsHeader");
  if (btnSettingsHeader) {
    btnSettingsHeader.addEventListener("click", () => {
      playSound("blip");
      window.switchWorkspace("settings");
    });
  }

  // 14. Network Waveform Canvas animation loop
  const netWave = document.getElementById("refNetWaveCanvas");
  if (netWave) {
    const netCtx = netWave.getContext("2d");
    let netPhase = 0;
    function renderNetWave() {
      if (!netWave || !netCtx) return;
      const rect = netWave.getBoundingClientRect();
      if (rect.width > 10 && (netWave.width !== Math.floor(rect.width) || netWave.height !== Math.floor(rect.height))) {
        netWave.width = Math.floor(rect.width);
        netWave.height = Math.floor(rect.height);
      }
      const nw = netWave.width;
      const nh = netWave.height;
      netCtx.clearRect(0, 0, nw, nh);
      netPhase += 0.05;

      netCtx.beginPath();
      netCtx.strokeStyle = "#00e5ff";
      netCtx.lineWidth = 1.5;
      for (let x = 0; x < nw; x += 3) {
        const y = nh / 2 + Math.sin(x * 0.08 + netPhase) * (nh * 0.35) * Math.sin(x * 0.03 + netPhase * 0.5);
        if (x === 0) netCtx.moveTo(x, y);
        else netCtx.lineTo(x, y);
      }
      netCtx.stroke();
      requestAnimationFrame(renderNetWave);
    }
    requestAnimationFrame(renderNetWave);
  }

  // 15. Set Initial Active Workspace
  if (currentActiveWorkspace) {
    window.switchWorkspace(currentActiveWorkspace);
  }
}

// ----------------------------------------------------
// EVENT LISTENERS & INITIALIZATION
// ----------------------------------------------------
window.addEventListener("DOMContentLoaded", () => {
  // 1. Initialize Reference Command Center immediately (3D Hologram, Constellation, all buttons)
  initReferenceCommandCenter();

  // Start Arc Canvas
  try { drawArcReactor(); } catch(e) { console.warn("Arc reactor canvas error:", e); }

  // Connect WebSockets
  connectTelemetry();
  connectChat();

  // Clock
  setInterval(() => {
    const now = new Date();
    document.getElementById("hudClock").innerText = now.toTimeString().split(" ")[0];
    document.getElementById("hudDate").innerText = now.toDateString().toUpperCase();
  }, 1000);

  // Automatically unlock audio since WebView2 autoplay policy is bypassed
  unlockAllAudioEngines();

  // Mini PC Audio Hardware Matrix initialization
  syncHardwareMicStatus();


  // Global proactive audio unlock listeners on ANY user interaction
  const unlockEvents = ["click", "keydown", "pointerdown", "touchstart"];
  unlockEvents.forEach(evt => {
    window.addEventListener(evt, () => {
      unlockAllAudioEngines();
      if (state.continuousVoice && !state.isListening && recognition) {
        startVoiceListener();
      }
    }, { capture: true, passive: true });
  });

  // Test Voice Button
  const btnTestVoice = document.getElementById("btnTestVoice");
  if (btnTestVoice) {
    btnTestVoice.addEventListener("click", async () => {
      playSound("ack");
      appendLog("info", "TEST", "Testing Neural Voice Link (PC speakers & HUD audio)...");
      try {
        const res = await fetch("/api/voice/test", { method: "POST" });
        const data = await res.json();
        if (data.base64) {
          playBase64Audio(data.base64);
        }
      } catch(e) {
        console.error("Voice test error:", e);
      }
    });
  }

  // Auto-start always-on listening if permitted
  if (state.continuousVoice) {
    setTimeout(startVoiceListener, 600);
  }

  // Play boot chime
  setTimeout(() => { playSound("boot"); }, 500);

  // Transmit Button & Enter Key
  document.getElementById("btnSend").addEventListener("click", () => {
    transmitCommand(document.getElementById("cmdInput").value);
  });
  document.getElementById("cmdInput").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      transmitCommand(e.target.value);
    }
  });

  // Voice Toggle Button
  document.getElementById("btnVoiceToggle").addEventListener("click", toggleVoiceListening);

  // Always-On checkbox
  const chkCont = document.getElementById("chkContinuousVoice"); if (chkCont) chkCont.addEventListener("change", (e) => {
    state.continuousVoice = e.target.checked;
    if (state.continuousVoice && !state.isListening && recognition) {
      startVoiceListener();
    }
  });

  // Wake-word checkbox
  const chkWake = document.getElementById("chkWakeWord"); if (chkWake) chkWake.addEventListener("change", (e) => {
    state.wakeWordEnabled = e.target.checked;
  });

  // Speech Accent & Language Selector
  const selSpeechLang = document.getElementById("selSpeechLang");
  if (selSpeechLang) {
    selSpeechLang.value = state.speechLang;
    selSpeechLang.addEventListener("change", (e) => {
      state.speechLang = e.target.value;
      localStorage.setItem("jarvis_speech_lang", state.speechLang);
      if (recognition) {
        recognition.lang = state.speechLang;
        try { recognition.stop(); } catch(err){}
        if (state.continuousVoice) {
          setTimeout(startVoiceListener, 250);
        }
      }
      appendLog("info", "SPEECH", `Speech accent calibrated to ${state.speechLang}. Acoustic model synced.`);
    });
  }

  // Speaker Output Route Selector
  const selAudioMode = document.getElementById("selAudioMode");
  if (selAudioMode) {
    selAudioMode.value = state.audioMode;
    selAudioMode.addEventListener("change", (e) => {
      state.audioMode = e.target.value;
      localStorage.setItem("jarvis_audio_mode", state.audioMode);
      unlockAllAudioEngines();
      playSound("ack");
      appendLog("info", "SPEAKER ROUTE", `Audio output set to: ${e.target.options[e.target.selectedIndex].text}`);
    });
  }

  // Model Selectors Synchronization (Main HUD + Dedicated Chat)
  const selMainModel = document.getElementById("selMainModel");
  const selDedicatedChatModel = document.getElementById("selDedicatedChatModel");

  function syncModelSelection(val) {
    state.selectedModel = val;
    localStorage.setItem("jarvis_selected_model", val);
    if (selMainModel) selMainModel.value = val;
    if (selDedicatedChatModel) selDedicatedChatModel.value = val;
    const optText = (selMainModel && selMainModel.options[selMainModel.selectedIndex]) 
      ? selMainModel.options[selMainModel.selectedIndex].text 
      : val;
    const modelVal = document.getElementById("refModelVal");
    if (modelVal) {
      modelVal.innerText = optText.replace(/^[^\w]+/, "").trim();
    }
    appendLog("info", "AI BRAIN", `Active neural model calibrated to: ${optText}`);
    playSound("ack");
  }

  if (selMainModel) {
    selMainModel.value = state.selectedModel;
    selMainModel.addEventListener("change", (e) => syncModelSelection(e.target.value));
  }
  if (selDedicatedChatModel) {
    selDedicatedChatModel.value = state.selectedModel;
    selDedicatedChatModel.addEventListener("change", (e) => syncModelSelection(e.target.value));
  }

  // Dedicated Chat Modal Triggers
  const dedicatedChatModal = document.getElementById("dedicatedChatModal");
  const btnOpenDedicatedChat = document.getElementById("btnOpenDedicatedChat");
  const btnCloseDedicatedChat = document.getElementById("btnCloseDedicatedChat");
  const btnClearDedicatedChat = document.getElementById("btnClearDedicatedChat");
  const btnDedicatedChatSend = document.getElementById("btnDedicatedChatSend");
  const inpDedicatedChat = document.getElementById("inpDedicatedChat");
  const btnDedicatedChatMic = document.getElementById("btnDedicatedChatMic");

  if (btnOpenDedicatedChat && dedicatedChatModal) {
    btnOpenDedicatedChat.addEventListener("click", () => {
      dedicatedChatModal.classList.add("active");
      playSound("blip");
      if (inpDedicatedChat) inpDedicatedChat.focus();
    });
  }

  if (btnCloseDedicatedChat && dedicatedChatModal) {
    btnCloseDedicatedChat.addEventListener("click", () => {
      dedicatedChatModal.classList.remove("active");
    });
  }

  if (btnClearDedicatedChat) {
    btnClearDedicatedChat.addEventListener("click", () => {
      const container = document.getElementById("dedicatedChatMessages");
      if (container) container.innerHTML = "";
      state.chatHistory = [];
      playSound("blip");
      appendLog("info", "CHAT", "Dedicated chat history cleared.");
    });
  }

  if (btnDedicatedChatSend && inpDedicatedChat) {
    btnDedicatedChatSend.addEventListener("click", () => {
      const text = inpDedicatedChat.value.trim();
      if (text) transmitCommand(text);
    });
  }

  if (inpDedicatedChat) {
    inpDedicatedChat.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        const text = inpDedicatedChat.value.trim();
        if (text) transmitCommand(text);
      }
    });
  }

  if (btnDedicatedChatMic) {
    btnDedicatedChatMic.addEventListener("click", () => {
      toggleVoiceListening();
      btnDedicatedChatMic.classList.toggle("active", state.isListening);
    });
  }

  // Quick Chat Directives Toolbar
  document.querySelectorAll("[data-chat-cmd]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const cmd = btn.getAttribute("data-chat-cmd");
      if (cmd) transmitCommand(cmd);
    });
  });

  // Quick Application Dispatch buttons
  document.querySelectorAll(".quick-btn[data-action='launch']").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.getAttribute("data-target");
      triggerPcAction("launch", { app_name: target });
      appendLog("tool", "ACTION", `Initiated launch for '${target}' via quick dock.`);
    });
  });

  // Master Volume Slider
  const volSlider = document.getElementById("volumeSlider");
  if (volSlider) {
    volSlider.addEventListener("input", (e) => {
      const val = e.target.value;
      const vDisp = document.getElementById("volumeDisplay"); if (vDisp) vDisp.innerText = `${val}%`;
    });
    volSlider.addEventListener("change", (e) => {
      const val = e.target.value;
      triggerPcAction("set_volume", { percent: parseInt(val) });
    });
  }

  // Hardware buttons
  const el_btnMuteToggle = document.getElementById("btnMuteToggle"); if (el_btnMuteToggle) el_btnMuteToggle.addEventListener("click", () => {
    triggerPcAction("mute", {});
  });
  const el_btnMediaPlay = document.getElementById("btnMediaPlay"); if (el_btnMediaPlay) el_btnMediaPlay.addEventListener("click", () => {
    triggerPcAction("media", { media_action: "play_pause" });
  });
  const el_btnScreenshot = document.getElementById("btnScreenshot"); if (el_btnScreenshot) el_btnScreenshot.addEventListener("click", () => {
    triggerPcAction("screenshot", {});
  });
  const el_btnLockPc = document.getElementById("btnLockPc"); if (el_btnLockPc) el_btnLockPc.addEventListener("click", () => {
    if (confirm("Sir Shakil, do you wish to secure and lock this workstation now?")) {
      triggerPcAction("lock", {});
    }
  });

  // Suggestion Chips
  document.querySelectorAll(".chip-btn").forEach((chip) => {
    chip.addEventListener("click", () => {
      const cmd = chip.getAttribute("data-cmd");
      transmitCommand(cmd);
    });
  });

  // Fullscreen Button
  document.getElementById("btnFullscreen").addEventListener("click", () => {
    playSound("blip");
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(err => alert(err.message));
    } else {
      document.exitFullscreen();
    }
  });

  // Diagnostics Button
  document.getElementById("btnDiagnostics").addEventListener("click", () => {
    transmitCommand("Jarvis, perform full system diagnostics and report status");
  });

  // Config Modal
  const cfgModal = document.getElementById("configModal");
  document.getElementById("btnSettings").addEventListener("click", async () => {
    playSound("blip");
    cfgModal.classList.add("active");
    try {
      const res = await fetch("/api/settings");
      const data = await res.json();
      if (data.has_api_key) {
        const cfgKey = document.getElementById("cfgApiKey"); if (cfgKey) cfgKey.placeholder = `Configured (${data.api_key_masked})`;
      }
      const select = document.getElementById("cfgVoiceSelect");
      select.innerHTML = "";
      data.voices.forEach((v) => {
        const opt = document.createElement("option");
        opt.value = v.id;
        opt.innerText = v.name;
        if (v.id === data.default_voice) opt.selected = true;
        select.appendChild(opt);
      });
    } catch(e) { console.error(e); }
  });

  const btnCloseCfg = document.getElementById("btnCloseConfig"); if (btnCloseCfg) btnCloseCfg.addEventListener("click", () => {
    cfgModal.classList.remove("active");
  });

  document.getElementById("btnSaveConfig").addEventListener("click", async () => {
    playSound("ack");
    const key = (document.getElementById("cfgApiKey") ? document.getElementById("cfgApiKey").value : "");
    const voice = document.getElementById("cfgVoiceSelect") ? document.getElementById("cfgVoiceSelect").value : "en-US-Standard-B";
    state.soundFxEnabled = document.getElementById("cfgSoundFx") ? document.getElementById("cfgSoundFx").checked : true;

    await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_key: key, voice: voice })
    });

    const bVoice = document.getElementById("badgeVoice"); if (bVoice) bVoice.innerHTML = `<span class="dot"></span> VOICE: ${voice.split("-")[2] || "GB"}`;
    cfgModal.classList.remove("active");
    appendLog("info", "SYSTEM", "Configuration protocols committed successfully, Sir Shakil.");
  });

  // Screenshot Modal Close
  document.getElementById("btnCloseScreen").addEventListener("click", () => {
    document.getElementById("screenModal").classList.remove("active");
  });

  // Memory Vault
  const memModal = document.getElementById("memoryModal");
  async function loadMemoryVault() {
    try {
      const res = await fetch("/api/memory");
      const data = await res.json();
      const fCnt = document.getElementById("factsCount"); if (fCnt) fCnt.innerText = data.facts.length;
      const kCnt = document.getElementById("knowledgeCount"); if (kCnt) kCnt.innerText = data.knowledge.length;

      const factList = document.getElementById("memFactList");
      factList.innerHTML = "";
      data.facts.forEach((f) => {
        const item = document.createElement("div");
        item.className = "fact-item";
        item.innerHTML = `
          <div class="fact-content">
            <span class="fact-cat">[${f.category.toUpperCase()}]</span>
            <span class="fact-key">${escapeHtml(f.key)}</span>
            <span class="fact-val">${escapeHtml(f.value)}</span>
          </div>
          <button class="fact-delete-btn" data-id="${f.id}">PURGE</button>
        `;
        factList.appendChild(item);
      });

      // Delete fact handlers
      factList.querySelectorAll(".fact-delete-btn").forEach((btn) => {
        btn.addEventListener("click", async (e) => {
          const id = e.target.getAttribute("data-id");
          await fetch(`/api/memory/fact/${id}`, { method: "DELETE" });
          loadMemoryVault();
        });
      });

      // Knowledge nodes
      const kList = document.getElementById("memKnowledgeList");
      kList.innerHTML = "";
      data.knowledge.forEach((k) => {
        const item = document.createElement("div");
        item.className = "knowledge-item";
        const dateStr = k.created_at ? new Date(k.created_at).toLocaleDateString() : "";
        item.innerHTML = `
          <div class="knowledge-title-row">
            <span class="knowledge-title">${escapeHtml(k.topic)}</span>
            <span class="knowledge-date">${dateStr} · [${escapeHtml(k.category)}]</span>
          </div>
          <div class="knowledge-summary">${escapeHtml(k.summary)}</div>
          ${k.details ? `<div class="knowledge-summary" style="margin-top:4px; opacity:0.85; font-size:12px;">${escapeHtml(k.details)}</div>` : ''}
          <div class="knowledge-tags">Tags: ${escapeHtml(k.tags || "research")}</div>
        `;
        kList.appendChild(item);
      });

    } catch(e) {
      console.error("Memory load failed:", e);
    }
  }

  document.getElementById("btnMemoryVault").addEventListener("click", () => {
    playSound("blip");
    loadMemoryVault();
    memModal.classList.add("active");
  });

  const bCloseMem = document.getElementById("btnCloseMemory"); if (bCloseMem) bCloseMem.addEventListener("click", () => {
    memModal.classList.remove("active");
  });

  // Memory Tabs switching
  document.querySelectorAll(".mem-tab-btn").forEach((tabBtn) => {
    tabBtn.addEventListener("click", () => {
      playSound("blip");
      document.querySelectorAll(".mem-tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach((p) => p.classList.remove("active"));
      tabBtn.classList.add("active");
      const target = tabBtn.getAttribute("data-tab");
      document.getElementById(target).classList.add("active");
    });
  });

  // Trigger Research Button in Modal
  const bTrigRes = document.getElementById("btnTriggerResearch"); if (bTrigRes) bTrigRes.addEventListener("click", async () => {
    const topic = document.getElementById("inpResearchTopic") ? document.getElementById("inpResearchTopic").value.trim() : "";
    playSound("ack");
    const bRes1 = document.getElementById("btnTriggerResearch"); if (bRes1) bRes1.innerText = "RESEARCHING...";
    const bRes2 = document.getElementById("btnTriggerResearch"); if (bRes2) bRes2.disabled = true;

    try {
      await fetch("/api/research/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: topic })
      });
      const inpRes = document.getElementById("inpResearchTopic"); if (inpRes) inpRes.value = "";
      await loadMemoryVault();
    } catch(e) {
      console.error("Research failed:", e);
    } finally {
      const bRes1 = document.getElementById("btnTriggerResearch"); if (bRes1) bRes1.innerText = "RESEARCH NOW";
      const bRes2 = document.getElementById("btnTriggerResearch"); if (bRes2) bRes2.disabled = false;
    }
  });

  // Add Fact Button in Modal
  const bSaveFact = document.getElementById("btnSaveNewFact"); if (bSaveFact) bSaveFact.addEventListener("click", async () => {
    const cat = document.getElementById("newFactCategory") ? document.getElementById("newFactCategory").value : "general";
    const key = document.getElementById("newFactKey") ? document.getElementById("newFactKey").value.trim() : "";
    const val = document.getElementById("newFactValue") ? document.getElementById("newFactValue").value.trim() : "";
    if (!key || !val) return;

    playSound("ack");
    await fetch("/api/memory/fact", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category: cat, key: key, value: val })
    });

    document.getElementById("newFactKey").value = "";
    document.getElementById("newFactValue").value = "";
    await loadMemoryVault();

    // Switch back to facts tab
    document.querySelector(".mem-tab-btn[data-tab='tabFacts']").click();
  });

  // Neural RAG Search in Modal
  const btnExecRag = document.getElementById("btnExecuteRagSearch");
  const inpRag = document.getElementById("inpRagQuery");
  const ragDeck = document.getElementById("ragResultsDeck");

  async function executeRagModalSearch() {
    const q = inpRag ? inpRag.value.trim() : "";
    if (!q) return;

    playSound("blip");
    btnExecRag.innerText = "QUERYING RAG...";
    btnExecRag.disabled = true;

    try {
      const res = await fetch("/api/rag/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q })
      });
      const data = await res.json();

      let html = `<div style="color:#00e5ff; font-weight:700; margin-bottom:8px;">🔍 RAG RECALL DOSSIER FOR: '${escapeHtml(q)}'</div>`;

      if (data.dialogue && data.dialogue.length > 0) {
        html += `<strong style="color:#38ef7d;">Relevant Past Conversation Threads (${data.dialogue.length}):</strong><br>`;
        data.dialogue.forEach(d => {
          html += `<div style="margin:4px 0 8px 8px; padding-left:6px; border-left:2px solid #38ef7d;">
            <span style="opacity:0.7; font-size:10px;">${escapeHtml(d.date)} · ${escapeHtml(d.role)}:</span><br>
            <span>${escapeHtml(d.content)}</span>
          </div>`;
        });
      }

      if (data.knowledge && data.knowledge.length > 0) {
        html += `<strong style="color:#ffaa00;">Relevant Knowledge Vault Nodes (${data.knowledge.length}):</strong><br>`;
        data.knowledge.forEach(k => {
          html += `<div style="margin:4px 0 8px 8px; padding-left:6px; border-left:2px solid #ffaa00;">
            <span style="font-weight:700; color:#ffaa00;">${escapeHtml(k.topic)}</span> <span style="opacity:0.7; font-size:10px;">[${escapeHtml(k.category)}]</span><br>
            <span>${escapeHtml(k.summary)}</span>
          </div>`;
        });
      }

      if (data.facts && data.facts.length > 0) {
        html += `<strong style="color:#00e5ff;">Matched User Facts (${data.facts.length}):</strong><br>`;
        data.facts.forEach(f => {
          html += `<div style="margin:4px 0 8px 8px; padding-left:6px; border-left:2px solid #00e5ff;">
            <span style="font-weight:700;">${escapeHtml(f.key)}</span>: ${escapeHtml(f.value)}
          </div>`;
        });
      }

      if ((!data.dialogue || data.dialogue.length === 0) &&
          (!data.knowledge || data.knowledge.length === 0) &&
          (!data.facts || data.facts.length === 0)) {
        html += `<span style="color:#aaa;">No direct indexed matches found for '${escapeHtml(q)}'. Jarvis will rely on real-time neural reasoning.</span>`;
      }

      ragDeck.innerHTML = html;
      playSound("ack");
    } catch (err) {
      ragDeck.innerHTML = `<span style="color:#ff3366;">RAG query failed: ${escapeHtml(err.message)}</span>`;
    } finally {
      btnExecRag.innerText = "RECALL CONTEXT";
      btnExecRag.disabled = false;
    }
  }

  if (btnExecRag) {
    btnExecRag.addEventListener("click", executeRagModalSearch);
  }
  if (inpRag) {
    inpRag.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        executeRagModalSearch();
      }
    });
  }

  // ----------------------------------------------------
  // OMNIROUTE MODEL GATEWAY STATUS
  // ----------------------------------------------------
  async function checkOmnirouteStatus() {
    try {
      const res = await fetch("/api/omniroute/status");
      const data = await res.json();
      const badge = document.getElementById("badgeOmniroute");
      if (badge && data.active) {
        badge.innerHTML = `<span class="dot" style="background:#76ff03; box-shadow:0 0 8px #76ff03;"></span> OMNIROUTE: ${data.total_models || '1,189+'} MODELS`;
        badge.title = `OmniRoute Online (${(data.active_providers || []).length} active providers, ${data.total_models} free models linked)`;
      }
    } catch(e) {
      console.warn("OmniRoute status check failed", e);
    }
  }
  checkOmnirouteStatus();

  // ----------------------------------------------------
  // MARKETING HUB & BROWSER CONTROLLER LOGIC
  // ----------------------------------------------------
  const mktModal = document.getElementById("marketingModal");
  const openMarketingHub = (tabId = "tabEventbrite") => {
    playSound("blip");
    if (mktModal) mktModal.classList.add("active");
    if (tabId) {
      const btn = document.querySelector(`.marketing-tab-btn[data-tab='${tabId}']`);
      if (btn) btn.click();
    }
  };

  const btnMktHub = document.getElementById("btnMarketingHub");
  if (btnMktHub) btnMktHub.addEventListener("click", () => openMarketingHub("tabEventbrite"));

  const btnBrowserResearchHdr = document.getElementById("btnBrowserResearchHeader");
  if (btnBrowserResearchHdr) btnBrowserResearchHdr.addEventListener("click", () => openMarketingHub("tabBrowserResearch"));

  const btnCloseMkt = document.getElementById("btnCloseMarketing");
  if (btnCloseMkt) btnCloseMkt.addEventListener("click", () => mktModal.classList.remove("active"));
  
  const btnQuickMkt = document.getElementById("btnQuickMarketingHub");
  if (btnQuickMkt) btnQuickMkt.addEventListener("click", () => openMarketingHub("tabCampaigns"));

  const btnQuickEb = document.getElementById("btnQuickEventbrite");
  if (btnQuickEb) btnQuickEb.addEventListener("click", () => openMarketingHub("tabEventbrite"));

  const btnQuickEm = document.getElementById("btnQuickCheckEmails");
  if (btnQuickEm) btnQuickEm.addEventListener("click", () => {
    openMarketingHub("tabEmailBrowser");
    const scanBtn = document.getElementById("btnScanInboxNow");
    if (scanBtn) scanBtn.click();
  });

  // Marketing Tabs
  document.querySelectorAll(".marketing-tab-btn").forEach((tabBtn) => {
    tabBtn.addEventListener("click", () => {
      playSound("blip");
      document.querySelectorAll(".marketing-tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".mkt-tab-pane").forEach((p) => p.classList.remove("active"));
      tabBtn.classList.add("active");
      const target = tabBtn.getAttribute("data-tab");
      const pane = document.getElementById(target);
      if (pane) pane.classList.add("active");
    });
  });

  // Eventbrite SEO Generator
  const btnGenEb = document.getElementById("btnGenEventbrite");
  if (btnGenEb) {
    btnGenEb.addEventListener("click", async () => {
      const topic = document.getElementById("ebTopic") ? document.getElementById("ebTopic").value.trim() : "";
      const audience = document.getElementById("ebAudience") ? document.getElementById("ebAudience").value.trim() : "";
      const loc = document.getElementById("ebLocation") ? document.getElementById("ebLocation").value.trim() : "";
      if (!topic) {
        alert("Sir Shakil, please provide an event topic or title.");
        return;
      }
      playSound("ack");
      const outBox = document.getElementById("ebOutput");
      btnGenEb.innerText = "OPTIMIZING EVENTBRITE SEO...";
      btnGenEb.disabled = true;
      outBox.style.display = "block";
      outBox.innerHTML = "<span style='color:#00e5ff;'>Analyzing high-search Eventbrite keywords, crafting conversion copy, and structuring ticket tiers...</span>";

      try {
        const res = await fetch("/api/marketing/eventbrite", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ topic: topic, target_audience: audience, location: loc })
        });
        const data = await res.json();
        
        let html = `<h4>1. HIGH-SEARCH SEO TITLES</h4>`;
        if (Array.isArray(data.seo_titles)) {
          data.seo_titles.forEach((t) => { html += `<div>• ${escapeHtml(t)}</div>`; });
        } else if (data.seo_title) {
          html += `<div>• ${escapeHtml(data.seo_title)}</div>`;
        }
        
        html += `<h4>2. 140-CHARACTER SEARCH SUMMARY</h4><div>${escapeHtml(data.event_summary || '')}</div>`;
        
        const tags = data.tags || data.seo_tags || [];
        html += `<h4>3. EVENTBRITE ALGORITHM TAGS</h4><div style="color:#76ff03;">${tags.join(" · ")}</div>`;
        
        html += `<h4>4. HIGH-CONVERTING HTML DESCRIPTION</h4><div style="background:rgba(0,0,0,0.5); padding:8px; border:1px solid rgba(0,240,255,0.2); max-height:150px; overflow-y:auto; font-size:11px;">${escapeHtml(data.html_description || '')}</div>`;
        
        html += `<h4>5. PROFIT-MAXIMIZING TICKET TIERS</h4>`;
        (data.ticket_tiers || []).forEach(tier => {
          html += `<div><strong>${escapeHtml(tier.name)} (${escapeHtml(tier.price)})</strong>: ${escapeHtml(tier.description || '')}</div>`;
        });
        
        html += `<h4>6. EARLY-BIRD PROMOTION STRATEGY</h4>`;
        if (Array.isArray(data.promo_strategy)) {
          data.promo_strategy.forEach(p => {
            html += `<div>Code: <code>${escapeHtml(p.code)}</code> (${escapeHtml(p.discount)}) — ${escapeHtml(p.trigger)}</div>`;
          });
        } else if (data.promo_strategy) {
          html += `<div>Code: <code>${escapeHtml(data.promo_strategy.discount_code || 'VIPSHAKIL')}</code> (${escapeHtml(data.promo_strategy.discount_percent || '20% OFF')})<br>${escapeHtml(data.promo_strategy.urgency_trigger || '')}</div>`;
        }

        outBox.innerHTML = html;
        appendLog("jarvis", "MARKETING", `Eventbrite SEO optimization package generated for '${topic}'.`);
      } catch(err) {
        outBox.innerHTML = `<span style="color:#ff3366;">Error optimizing listing: ${escapeHtml(err.message)}</span>`;
      } finally {
        btnGenEb.innerText = "GENERATE SEO-OPTIMIZED EVENTBRITE PACK";
        btnGenEb.disabled = false;
      }
    });
  }

  // Multi-Channel Campaign Generator
  const btnGenCamp = document.getElementById("btnGenCampaign");
  if (btnGenCamp) {
    btnGenCamp.addEventListener("click", async () => {
      const product = document.getElementById("campProduct") ? document.getElementById("campProduct").value.trim() : "";
      const valueProp = document.getElementById("campValue") ? document.getElementById("campValue").value.trim() : "";
      const price = document.getElementById("campPrice") ? document.getElementById("campPrice").value.trim() : "";
      const cType = document.getElementById("campType") ? document.getElementById("campType").value : "omni";
      if (!product) {
        alert("Sir Shakil, please provide the offer or product name.");
        return;
      }
      playSound("ack");
      const outBox = document.getElementById("campOutput");
      btnGenCamp.innerText = "GENERATING CAMPAIGN ARSENAL...";
      btnGenCamp.disabled = true;
      outBox.style.display = "block";
      outBox.innerHTML = "<span style='color:#00e5ff;'>Formulating multi-channel copy across Email, SMS, Google Ads, and Meta Ads...</span>";

      try {
        const res = await fetch("/api/marketing/campaign", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ product_name: product, value_prop: valueProp, price_point: price, type: cType })
        });
        const data = await res.json();
        let html = "";
        
        if (data.email) {
          html += `<h4>📧 EMAIL CONVERSION SEQUENCE</h4>`;
          (data.email.sequence || []).forEach(em => {
            const subj = em.subject_lines ? em.subject_lines[0] : (em.subjects ? em.subjects[0] : '');
            html += `<div style="margin-bottom:8px; border-left:2px solid #00e5ff; padding-left:8px;"><strong>Email #${em.step || em.email_num}: ${escapeHtml(em.purpose || em.type || '')}</strong><br><em>Subject: ${escapeHtml(subj)}</em><br><span style="opacity:0.85;">${escapeHtml(em.preview_text || em.body_preview || '')}</span></div>`;
          });
        }
        
        if (data.sms) {
          html += `<h4>📱 SMS URGENCY BLASTS</h4>`;
          const smsList = data.sms.variants || data.sms.sms_campaigns || [];
          smsList.forEach(s => {
            const timing = s.type || s.timing || 'Alert';
            html += `<div style="margin-bottom:6px;"><strong>[${escapeHtml(timing)}]</strong>: ${escapeHtml(s.text)}</div>`;
          });
        }

        if (data.google_ads) {
          html += `<h4>🎯 GOOGLE ADS ASSETS</h4>`;
          html += `<div><strong>Headlines:</strong> ${(data.google_ads.headlines || []).slice(0, 5).join(" | ")}</div>`;
          html += `<div><strong>Descriptions:</strong> ${(data.google_ads.descriptions || []).join(" ")}</div>`;
        }

        if (data.meta_ads) {
          html += `<h4>📱 META / INSTAGRAM ADS</h4>`;
          const creatives = data.meta_ads.angles || data.meta_ads.ad_creatives || data.meta_ads.creatives || [];
          creatives.forEach(c => {
            html += `<div style="margin-bottom:6px; border-left:2px solid #ff0055; padding-left:8px;"><strong>Angle: ${escapeHtml(c.angle || c.angle_name || '')}</strong><br><em>Headline: ${escapeHtml(c.headline || '')} (${escapeHtml(c.cta_button || 'Learn More')})</em><br>${escapeHtml(c.primary_text || '')}</div>`;
          });
        }

        outBox.innerHTML = html;
        appendLog("jarvis", "MARKETING", `Multi-channel campaigns deployed for '${product}'.`);
      } catch(err) {
        outBox.innerHTML = `<span style="color:#ff3366;">Error generating campaigns: ${escapeHtml(err.message)}</span>`;
      } finally {
        btnGenCamp.innerText = "DEPLOY MARKETING COPY ENGINE";
        btnGenCamp.disabled = false;
      }
    });
  }

  // Dedicated Browser Controls
  const launchJarvisChrome = async (targetUrl = "https://mail.google.com") => {
    playSound("ack");
    try {
      await fetch("/api/browser/launch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: targetUrl })
      });
      appendLog("tool", "BROWSER", `Dedicated Chrome Profile launched at ${targetUrl}.`);
    } catch(e) {
      console.error(e);
    }
  };

  const btnJarvisBrowser = document.getElementById("btnJarvisBrowser");
  if (btnJarvisBrowser) btnJarvisBrowser.addEventListener("click", () => launchJarvisChrome("https://mail.google.com"));

  const btnQuickChrome = document.getElementById("btnQuickJarvisChrome");
  if (btnQuickChrome) btnQuickChrome.addEventListener("click", () => launchJarvisChrome("https://mail.google.com"));

  const btnLaunchDed = document.getElementById("btnLaunchDedicatedChrome");
  if (btnLaunchDed) btnLaunchDed.addEventListener("click", () => launchJarvisChrome("https://mail.google.com"));

  const btnOpenEbDash = document.getElementById("btnOpenEventbriteDash");
  if (btnOpenEbDash) btnOpenEbDash.addEventListener("click", () => launchJarvisChrome("https://www.eventbrite.com/signin/"));

  const btnOpenMetaDash = document.getElementById("btnOpenMetaAdsDash");
  if (btnOpenMetaDash) btnOpenMetaDash.addEventListener("click", () => launchJarvisChrome("https://adsmanager.facebook.com"));

  // Inbox Scan
  const btnScanInbox = document.getElementById("btnScanInboxNow");
  if (btnScanInbox) {
    btnScanInbox.addEventListener("click", async () => {
      const resBox = document.getElementById("emailScanResults");
      resBox.innerHTML = "<span style='color:#00e5ff;'>Inspecting dedicated Chrome profile sessions for unread emails...</span>";
      playSound("blip");
      try {
        const res = await fetch("/api/browser/emails");
        const data = await res.json();
        
        let html = `<strong>Status:</strong> ${data.status} | <strong>Unread Count:</strong> ${data.unread_count || 0}<br>`;
        html += `<strong>Executive Brief:</strong> ${escapeHtml(data.executive_brief || data.message)}<br><br>`;
        
        if (data.emails && data.emails.length > 0) {
          html += `<strong>Detected Emails:</strong><br>`;
          data.emails.forEach(e => {
            html += `• <strong>${escapeHtml(e.sender)}:</strong> ${escapeHtml(e.subject)} — <em>${escapeHtml(e.snippet)}</em><br>`;
          });
        } else {
          html += `<em>(If you have not logged in yet, click 'LAUNCH DEDICATED CHROME' above, sign into your email account once, and subsequent checks will read your inbox automatically.)</em>`;
        }
        resBox.innerHTML = html;
        appendLog("jarvis", "EMAIL BRIEF", data.executive_brief || data.message);
      } catch(e) {
        resBox.innerHTML = `<span style="color:#ff3366;">Failed scanning inbox: ${escapeHtml(e.message)}</span>`;
      }
    });
  }

  // Email Confirmation Gate
  const btnConfirmEmail = document.getElementById("btnConfirmSendEmail");
  if (btnConfirmEmail) {
    btnConfirmEmail.addEventListener("click", async () => {
      playSound("ack");
      try {
        const res = await fetch("/api/browser/email/reply", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "confirm_send" })
        });
        const data = await res.json();
        alert("Directives executed: " + data.message);
        const draftBox = document.getElementById("emailDraftStageBox"); if (draftBox) draftBox.style.display = "none";
        appendLog("tool", "EMAIL TRANSMIT", data.message);
      } catch(e) {
        alert("Transmission failed: " + e.message);
      }
    });
  }

  const btnCancelEmail = document.getElementById("btnCancelSendEmail");
  if (btnCancelEmail) {
    btnCancelEmail.addEventListener("click", () => {
      playSound("blip");
      const draftBox = document.getElementById("emailDraftStageBox"); if (draftBox) draftBox.style.display = "none";
      appendLog("system", "CANCEL", "Draft transmission aborted by Sir Shakil.");
    });
  }

  // Autonomous Browser Online Research Logic
  const btnOpenGoogleJarvis = document.getElementById("btnOpenGoogleJarvis");
  if (btnOpenGoogleJarvis) {
    btnOpenGoogleJarvis.addEventListener("click", () => launchJarvisChrome("https://www.google.com"));
  }

  const btnCaptureBrowser = document.getElementById("btnCaptureBrowserScreen");
  if (btnCaptureBrowser) {
    btnCaptureBrowser.addEventListener("click", async () => {
      playSound("ack");
      appendLog("info", "BROWSER", "Capturing live Chrome view from 'Jarvis' profile...");
      try {
        const res = await fetch("/api/browser/screenshot");
        const data = await res.json();
        if (data.success && data.base64) {
          const previewImg = document.getElementById("screenPreviewImg");
          const screenModal = document.getElementById("screenModal");
          if (previewImg && screenModal) {
            previewImg.src = `data:image/png;base64,${data.base64}`;
            screenModal.classList.add("active");
          }
          appendLog("tool", "SCREENSHOT", `Captured live view of: ${data.title || data.url}`);
        } else {
          alert("Capture failed: " + (data.error || "Browser tab unavailable"));
        }
      } catch(err) {
        console.error("Screenshot error:", err);
      }
    });
  }

  const btnExecResearch = document.getElementById("btnExecBrowserResearch");
  if (btnExecResearch) {
    btnExecResearch.addEventListener("click", async () => {
      const topic = document.getElementById("txtResearchTopic").value.trim();
      const mode = document.getElementById("selResearchMode").value;
      const outDeck = document.getElementById("researchOutputDeck");

      if (!topic) {
        alert("Please enter a research topic, market niche, or URL, Sir Shakil.");
        return;
      }

      playSound("ack");
      btnExecResearch.innerText = "DEPLOYING RESEARCH MATRIX...";
      btnExecResearch.disabled = true;
      outDeck.innerHTML = `<span style="color:#00e5ff;">Deploying dedicated Chrome profile ('Jarvis') across live web sources for '${escapeHtml(topic)}'...</span>`;
      appendLog("jarvis", "RESEARCH", `Initiated live browser research for '${topic}' via profile 'Jarvis'.`);

      try {
        let endpoint = "/api/browser/research";
        let payload = { topic: topic };

        if (mode === "search_only") {
          endpoint = "/api/browser/search";
          payload = { query: topic };
        } else if (mode === "browse_url") {
          endpoint = "/api/browser/browse";
          payload = { url: topic };
        }

        const res = await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await res.json();

        let html = "";
        if (mode === "deep") {
          html += `<div style="color:#00e5ff; font-weight:700; margin-bottom:8px;">EXECUTIVE INTELLIGENCE DOSSIER: ${escapeHtml(data.topic || topic)}</div>`;
          html += `<strong>Executive Briefing:</strong><br>${escapeHtml(data.summary || '')}<br><br>`;
          if (data.monetization) {
            html += `<strong style="color:#38ef7d;">Wealth & Monetization Vector:</strong><br>${escapeHtml(data.monetization)}<br><br>`;
          }
          if (data.technical_roadmap) {
            html += `<strong style="color:#ffaa00;">Technical Implementation Roadmap:</strong><br>${escapeHtml(data.technical_roadmap)}<br><br>`;
          }
          if (data.discoveries && data.discoveries.length > 0) {
            html += `<strong>Key Discoveries:</strong><br>`;
            data.discoveries.forEach(d => {
              html += `• ${escapeHtml(d)}<br>`;
            });
          }
          if (data.stats) {
            html += `<br><div style="font-size:11px; color:#ffaa00; border-top:1px dashed rgba(255,170,0,0.3); padding-top:6px;">⚡ COGNITIVE LEVEL UP: EVOLUTION LEVEL ${data.stats.level} (${data.stats.knowledge_nodes} NODES CATALOGED IN MEMORY VAULT)</div>`;
          }
          appendLog("jarvis", "INTEL DOSSIER", data.summary || "Online research cycle completed.");
        } else if (mode === "search_only") {
          html += `<strong>Query:</strong> ${escapeHtml(data.query)} | <strong>Found:</strong> ${data.results ? data.results.length : 0} results<br><br>`;
          (data.results || []).forEach(r => {
            html += `• <a href="${escapeHtml(r.url)}" target="_blank" style="color:#00e5ff; text-decoration:none;"><strong>${escapeHtml(r.title)}</strong></a><br><em>${escapeHtml(r.snippet)}</em><br><br>`;
          });
        } else if (mode === "browse_url") {
          html += `<strong>Title:</strong> ${escapeHtml(data.title || '')}<br>`;
          html += `<strong>URL:</strong> <a href="${escapeHtml(data.url)}" target="_blank" style="color:#00e5ff;">${escapeHtml(data.url)}</a><br><br>`;
          if (data.headings && data.headings.length > 0) {
            html += `<strong>Key Headings:</strong> ${escapeHtml(data.headings.join(' · '))}<br><br>`;
          }
          html += `<strong>Extracted Content:</strong><br><pre style="white-space:pre-wrap; font-family:var(--font-mono); font-size:11px; color:#b2ebf2;">${escapeHtml(data.body || '')}</pre>`;
        }

        outDeck.innerHTML = html;
        playSound("blip");
      } catch(err) {
        outDeck.innerHTML = `<span style="color:#ff3366;">Research execution failed: ${escapeHtml(err.message)}</span>`;
      } finally {
        btnExecResearch.innerText = "DEPLOY CHROME RESEARCH AGENT";
        btnExecResearch.disabled = false;
      }
    });
  }

  // ====================================================
  // MARK XVI: EXECUTIVE OS CONTROLS & NATIVE DESKTOP INTEGRATION
  // ====================================================

  // 1. Emergency Abort & Instant Cancellation (<100ms)
  window.executeEmergencyStop = async function() {
    console.log("[JARVIS] Emergency Hard Abort Activated!");
    // Audio kill
    if (state.activeAudio) {
      try {
        state.activeAudio.pause();
        state.activeAudio.currentTime = 0;
      } catch(e) {}
      state.activeAudio = null;
    }
    if (window.speechSynthesis) {
      try { window.speechSynthesis.cancel(); } catch(e) {}
    }
    unlockMicAfterJarvisTurn();
    setAssistantStatus("idle", "ABORTED BY SIR SHAKIL");
    appendLog("warning", "EMERGENCY ABORT", "Active directive, tasks, and speech purged (<100ms).");

    // Inform WebSocket
    if (wsChat && wsChat.readyState === WebSocket.OPEN) {
      try { wsChat.send(JSON.stringify({ type: "cancel" })); } catch(e) {}
    }

    // Call Native PyWebView bridge if present
    if (window.pywebview && window.pywebview.api && window.pywebview.api.emergency_cancel) {
      try { window.pywebview.api.emergency_cancel(); } catch(e) {}
    }

    // REST fallback
    try {
      fetch("/api/conversation/cancel", { method: "POST" });
    } catch(e) {}
  };

  const btnEmergencyAbort = document.getElementById("btnEmergencyAbort");
  if (btnEmergencyAbort) {
    btnEmergencyAbort.addEventListener("click", () => {
      playSound("ack");
      window.executeEmergencyStop();
    });
  }

  // 1b. Isolated Workspace Switcher
  const selWorkspace = document.getElementById("selWorkspace");
  if (selWorkspace) {
    selWorkspace.value = state.currentWorkspace || "personal";
    selWorkspace.addEventListener("change", (e) => {
      state.currentWorkspace = e.target.value;
      localStorage.setItem("jarvis_workspace", e.target.value);
      playSound("blip");
      appendLog("system", "WORKSPACE", `Active context isolated to: ${state.currentWorkspace.toUpperCase()}`);
    });
  }

  // 2. Open Artifacts Folder (Desktop\Jarvis_Created_Files)
  window.openDesktopCodeFolder = async function() {
    playSound("ack");
    if (window.pywebview && window.pywebview.api && window.pywebview.api.open_created_files_folder) {
      try {
        await window.pywebview.api.open_created_files_folder();
        appendLog("tool", "EXPLORER", "Opened Desktop\\Jarvis_Created_Files in Windows Explorer.");
        return;
      } catch(e) {}
    }
    try {
      const res = await fetch("/api/desktop/open_folder", { method: "POST" });
      const data = await res.json();
      appendLog("tool", "EXPLORER", `Opened directory: ${data.path}`);
    } catch(e) {
      console.error("Open folder error:", e);
    }
  };

  const btnOpenArtifacts = document.getElementById("btnOpenArtifactsFolder");
  if (btnOpenArtifacts) btnOpenArtifacts.addEventListener("click", window.openDesktopCodeFolder);

  const btnOpenArtifactsFromSpec = document.getElementById("btnOpenArtifactsFromSpec");
  if (btnOpenArtifactsFromSpec) btnOpenArtifactsFromSpec.addEventListener("click", window.openDesktopCodeFolder);

  // 3. Interactive Human Approval Gate
  let currentPendingApprovalTask = null;
  window.openApprovalModal = function(task) {
    currentPendingApprovalTask = task;
    state.approvalModalOpen = true;
    const modal = document.getElementById("approvalModal");
    const detailsEl = document.getElementById("approvalTaskDetails");
    if (!modal || !detailsEl) return;

    detailsEl.innerHTML = `
      <div style="color:#ffaa00; font-weight:700; margin-bottom:4px;">TASK ID: ${escapeHtml(task.id)}</div>
      <div><strong>Action:</strong> ${escapeHtml(task.title || 'High-Risk Operation')}</div>
      <div><strong>Specialist:</strong> ${escapeHtml(task.specialist || 'Core Brain')}</div>
      <div style="margin-top:6px; color:#ffdd80;"><strong>Authorization Prompt:</strong> ${escapeHtml(task.approval_prompt || 'Sir Shakil, do you authorize execution of this directive?')}</div>
    `;
    modal.classList.add("active");
    playSound("blip");
  };

  window.closeApprovalModal = function() {
    const modal = document.getElementById("approvalModal");
    if (modal) modal.classList.remove("active");
    state.approvalModalOpen = false;
    currentPendingApprovalTask = null;
  };

  const btnCloseApproval = document.getElementById("btnCloseApproval");
  if (btnCloseApproval) btnCloseApproval.addEventListener("click", window.closeApprovalModal);

  const btnAuthorizeApproval = document.getElementById("btnAuthorizeApproval");
  if (btnAuthorizeApproval) {
    btnAuthorizeApproval.addEventListener("click", async () => {
      if (!currentPendingApprovalTask) return;
      playSound("ack");
      const taskId = currentPendingApprovalTask.id;
      try {
        const res = await fetch("/api/orchestrator/approve", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ task_id: taskId })
        });
        const data = await res.json();
        appendLog("jarvis", "AUTHORIZED", `Directive #${taskId} authorized by Sir Shakil.`);
        window.closeApprovalModal();
      } catch(e) {
        alert("Authorization failed: " + e.message);
      }
    });
  }

  const btnRejectApproval = document.getElementById("btnRejectApproval");
  if (btnRejectApproval) {
    btnRejectApproval.addEventListener("click", async () => {
      if (!currentPendingApprovalTask) return;
      playSound("blip");
      const taskId = currentPendingApprovalTask.id;
      try {
        const res = await fetch("/api/orchestrator/reject", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ task_id: taskId, reason: "Rejected by Sir Shakil" })
        });
        appendLog("warning", "REJECTED", `Directive #${taskId} aborted by Sir Shakil.`);
        window.closeApprovalModal();
      } catch(e) {
        alert("Rejection failed: " + e.message);
      }
    });
  }

  // 4. Specialist Agents Mission Deck
  const specialistConfigs = {
    coding: {
      title: "Coding & Software Engineer",
      desc: "Production-grade script & application generation saved directly to Desktop.",
      defaultPrompt: "Build a Python utility to monitor crypto price alerts and export to CSV"
    },
    research: {
      title: "Research & Intelligence Specialist",
      desc: "Deep web synthesis, academic literature queries, and knowledge vault assimilation.",
      defaultPrompt: "Conduct deep competitive analysis on top AI agency services"
    },
    qa: {
      title: "QA & Testing Engineer",
      desc: "Syntax validation, regression auditing, and code test verification.",
      defaultPrompt: "Perform comprehensive QA test on current Jarvis orchestrator components"
    },
    marketing: {
      title: "Chief Marketing Strategist",
      desc: "Direct response funnels, multi-channel customer acquisition, and monetization strategy.",
      defaultPrompt: "Develop complete customer acquisition funnel for $3k/mo AI automation retainers"
    },
    seo: {
      title: "SEO & Content Strategist",
      desc: "Eventbrite ranking optimization, programmatic SEO, and metadata engineering.",
      defaultPrompt: "Generate an Eventbrite SEO optimization pack for an AI Automation Agency workshop"
    },
    leadgen: {
      title: "B2B Lead Generation Specialist",
      desc: "Cold outreach email sequences, LinkedIn messaging, and B2B pipeline development.",
      defaultPrompt: "Craft a 4-step personalized cold outreach sequence for Canadian dental clinic owners"
    },
    wordpress: {
      title: "WordPress & CMS Architect",
      desc: "Custom WordPress architectures, Elementor layout blueprints, and PHP snippets.",
      defaultPrompt: "Create custom Elementor landing page blueprint with booking form integration"
    },
    business: {
      title: "Strategic Business & Financial Analyst",
      desc: "Crypto market technical analysis (EMA 9/20, 109) and niche market unit economics.",
      defaultPrompt: "Analyze Solana (SOL) EMA 9 and EMA 20 trading indicator signal setup"
    },
    system: {
      title: "Windows Systems Automation Engineer",
      desc: "Workstation automation, audio endpoint control, screenshot captures, and process inspection.",
      defaultPrompt: "Report full system diagnostics and memory allocation status"
    }
  };

  let selectedSpecialist = "coding";
  const specialistsModal = document.getElementById("specialistsModal");
  const btnSpecialistsDeck = document.getElementById("btnSpecialistsDeck");
  const btnCloseSpecialists = document.getElementById("btnCloseSpecialists");

  if (btnSpecialistsDeck) {
    btnSpecialistsDeck.addEventListener("click", () => {
      playSound("blip");
      specialistsModal.classList.add("active");
    });
  }
  if (btnCloseSpecialists) {
    btnCloseSpecialists.addEventListener("click", () => {
      specialistsModal.classList.remove("active");
    });
  }

  // Spec tab buttons
  document.querySelectorAll(".spec-tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".spec-tab-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      selectedSpecialist = btn.getAttribute("data-spec");
      const cfg = specialistConfigs[selectedSpecialist] || specialistConfigs.coding;
      document.getElementById("specAgentTitle").innerText = cfg.title;
      document.getElementById("specAgentDesc").innerText = cfg.desc;
      document.getElementById("inpSpecPrompt").placeholder = cfg.defaultPrompt;
      playSound("blip");
    });
  });

  // Dispatch Specialist
  const btnDispatch = document.getElementById("btnDispatchSpecialist");
  if (btnDispatch) {
    btnDispatch.addEventListener("click", async () => {
      const prompt = document.getElementById("inpSpecPrompt").value.trim() || document.getElementById("inpSpecPrompt").placeholder;
      const outDeck = document.getElementById("specOutputDeck");
      playSound("ack");
      btnDispatch.innerText = "DISPATCHING...";
      btnDispatch.disabled = true;
      outDeck.innerHTML = `<span style="color:#00e5ff;">Dispatching <strong>${selectedSpecialist.toUpperCase()}</strong> under Master Orchestrator supervision...</span>`;
      appendLog("jarvis", "SPECIALIST DISPATCH", `Deployed ${selectedSpecialist} agent for '${prompt.slice(0, 40)}...'`);

      try {
        const res = await fetch("/api/specialist/dispatch", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ specialist_id: selectedSpecialist, prompt: prompt })
        });
        const data = await res.json();
        if (data.success) {
          let html = `<div style="color:#38ef7d; font-weight:700; margin-bottom:8px;">✓ TASK #${escapeHtml(data.task_id)} COMPLETED [${escapeHtml(data.state).toUpperCase()}]</div>`;
          html += `<div style="margin-bottom:8px; opacity:0.8;">Evidence: ${escapeHtml(data.evidence || 'Verified')}</div>`;
          
          const r = data.result || {};
          if (r.saved_files && r.saved_files.length > 0) {
            html += `<div style="background:rgba(56,239,125,0.1); border:1px solid #38ef7d; padding:8px; border-radius:3px; margin-bottom:8px;">`;
            html += `<strong>Saved to Desktop\\Jarvis_Created_Files:</strong><br>`;
            r.saved_files.forEach(f => {
              html += `• <code>${escapeHtml(f.filename)}</code> (${f.lines} lines)<br>`;
            });
            html += `</div>`;
          }

          const rawText = r.response || r.summary || r.strategy || r.seo_pack || r.outreach_sequence || r.blueprint || r.analysis || r.report || JSON.stringify(r, null, 2);
          html += `<div style="white-space:pre-wrap; max-height:260px; overflow-y:auto; font-family:var(--font-mono); font-size:11px; background:rgba(0,0,0,0.5); padding:10px; border:1px solid rgba(0,229,255,0.2);">${escapeHtml(rawText)}</div>`;
          outDeck.innerHTML = html;
          playSound("blip");
        } else {
          outDeck.innerHTML = `<span style="color:#ff3344;">Dispatch failed: ${escapeHtml(data.error || 'Unknown error')}</span>`;
        }
      } catch(e) {
        outDeck.innerHTML = `<span style="color:#ff3344;">Dispatch network error: ${escapeHtml(e.message)}</span>`;
      } finally {
        btnDispatch.innerText = "DISPATCH AGENT";
        btnDispatch.disabled = false;
      }
    });
  }

  // ==========================================================================
  // J.A.R.V.I.S. MARK XVI ADVANCED UI ENGINE & WORKSPACE ROUTING
  // ==========================================================================

  // 1. Emergency Hard Abort (<100ms)
  window.executeEmergencyStop = async function() {
    playSound("alert");
    clearAudioQueue();
    state.jarvisIsSpeaking = false;
    currentPlayingAudio = null;

    // WebSocket abort signal
    if (wsChat && wsChat.readyState === WebSocket.OPEN) {
      try {
        wsChat.send(JSON.stringify({ type: "cancel" }));
      } catch (e) {}
    }

    // Direct REST abort signal
    try {
      fetch("/api/conversation/cancel", { method: "POST" }).catch(() => {});
    } catch (e) {}

    // Cancel native speech recognition
    if (recognition) {
      try { recognition.stop(); } catch(e){}
    }

    unlockMicAfterJarvisTurn();
    setAssistantStatus("idle", "ABORTED");
    appendLog("warning", "ABORT", "Emergency hard abort executed. Operations paused.");
    showToast("🛑 Emergency Abort: All Operations Halted", "error", 3000);
  };

  // 2. Toast & Notification System
  const systemNotifications = [];

  window.showToast = function(message, type = "info", duration = 3500) {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast-item toast-${type}`;

    const iconMap = { info: "💎", success: "✓", warning: "⚠️", error: "❌" };
    toast.innerHTML = `
      <span style="font-size:16px;">${iconMap[type] || "ℹ️"}</span>
      <span style="flex:1;">${escapeHtml(message)}</span>
    `;

    container.appendChild(toast);
    addNotificationRecord(message, type);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateY(-10px)";
      setTimeout(() => toast.remove(), 250);
    }, duration);
  };

  function addNotificationRecord(message, type = "info") {
    const list = document.getElementById("notificationList");
    const badge = document.getElementById("notificationBadgeCount");
    if (!list) return;

    const timeStr = new Date().toTimeString().split(" ")[0];
    const item = document.createElement("div");
    item.className = `notification-item ${type}`;
    item.innerHTML = `
      <div>${escapeHtml(message)}</div>
      <div class="notification-time">[${timeStr}] · ${type.toUpperCase()}</div>
    `;

    list.insertBefore(item, list.firstChild);
    systemNotifications.unshift({ message, type, time: timeStr });
    if (badge) {
      badge.innerText = systemNotifications.length;
    }
  }

  // 3. Workspace Navigation Engine (managed by hoisted window.switchWorkspace)

  // Bind Navigation Rail click events
  document.querySelectorAll(".nav-rail-item").forEach(item => {
    item.addEventListener("click", () => {
      const ws = item.getAttribute("data-workspace");
      if (ws) switchWorkspace(ws);
    });
    item.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        const ws = item.getAttribute("data-workspace");
        if (ws) switchWorkspace(ws);
      }
    });
  });

  // Toggle Navigation Rail expand/collapse
  const btnToggleRail = document.getElementById("btnToggleRail");
  const mainNavRail = document.getElementById("mainNavRail");
  if (btnToggleRail && mainNavRail) {
    // Restore saved expansion state
    const isExpanded = localStorage.getItem("jarvis_nav_expanded") === "true";
    if (isExpanded) mainNavRail.classList.add("expanded");

    btnToggleRail.addEventListener("click", () => {
      mainNavRail.classList.toggle("expanded");
      localStorage.setItem("jarvis_nav_expanded", mainNavRail.classList.contains("expanded"));
      playSound("blip");
    });
  }

  // 4. Command Palette (Ctrl+K)
  const COMMANDS_REGISTRY = [
    { title: "Go to Command Center", category: "Workspaces", shortcut: "Alt+1", action: () => switchWorkspace("command_center") },
    { title: "Go to Neural Chat", category: "Workspaces", shortcut: "Alt+2", action: () => switchWorkspace("chat") },
    { title: "Go to Agent Network", category: "Workspaces", shortcut: "Alt+3", action: () => switchWorkspace("agents") },
    { title: "Go to Operations & Tasks", category: "Workspaces", shortcut: "Alt+4", action: () => switchWorkspace("operations") },
    { title: "Go to Research & Intel", category: "Workspaces", shortcut: "Alt+5", action: () => switchWorkspace("research") },
    { title: "Go to Marketing Hub", category: "Workspaces", shortcut: "Alt+6", action: () => switchWorkspace("marketing") },
    { title: "Go to Family Safety & Mobile Companion", category: "Workspaces", shortcut: "Alt+7", action: () => switchWorkspace("family") },
    { title: "Go to Memory Vault", category: "Workspaces", shortcut: "Alt+8", action: () => switchWorkspace("memory") },
    { title: "Go to System Diagnostics", category: "Workspaces", shortcut: "Alt+9", action: () => switchWorkspace("diagnostics") },
    { title: "Go to Spatial Intel (God's Eye View)", category: "Workspaces", shortcut: "Alt+0", action: () => switchWorkspace("spatial") },
    { title: "Go to Settings", category: "Workspaces", shortcut: "", action: () => switchWorkspace("settings") },

    { title: "Family Safety: Scan Local Wi-Fi Network", category: "Family Safety", shortcut: "", action: () => { switchWorkspace("family"); const b = document.getElementById("btnScanWifi"); if (b) b.click(); } },
    { title: "Family Safety: Pair New Companion Phone", category: "Family Safety", shortcut: "", action: () => { switchWorkspace("family"); const b = document.getElementById("btnPairDevice"); if (b) b.click(); } },
    { title: "Family Safety: Voluntary Check-In (I'm Safe)", category: "Family Safety", shortcut: "", action: () => { switchWorkspace("family"); const b = document.getElementById("btnCheckInSafe"); if (b) b.click(); } },
    { title: "Family Safety: Emergency SOS (Need Help)", category: "Family Safety", shortcut: "", action: () => { switchWorkspace("family"); const b = document.getElementById("btnCheckInNeedHelp"); if (b) b.click(); } },
    { title: "Family Safety: Emergency Master Location Kill Switch", category: "Family Safety", shortcut: "", action: () => { switchWorkspace("family"); const b = document.getElementById("btnMasterKillSwitch"); if (b) b.click(); } },

    { title: "Spatial: Reset Globe Overview", category: "Spatial Intelligence", shortcut: "", action: () => { switchWorkspace("spatial"); window.spatialCommandBus?.dispatch({ action: "HOME_GLOBE" }); } },
    { title: "Spatial: Fly to Tokyo", category: "Spatial Intelligence", shortcut: "", action: () => { switchWorkspace("spatial"); window.spatialCommandBus?.dispatch({ action: "NAVIGATE", params: { latitude: 35.6762, longitude: 139.6503, rangeM: 15000, name: "Tokyo, Japan" } }); } },
    { title: "Spatial: Fly to London", category: "Spatial Intelligence", shortcut: "", action: () => { switchWorkspace("spatial"); window.spatialCommandBus?.dispatch({ action: "NAVIGATE", params: { latitude: 51.5074, longitude: -0.1278, rangeM: 15000, name: "London, UK" } }); } },
    { title: "Spatial: Fly to New York City", category: "Spatial Intelligence", shortcut: "", action: () => { switchWorkspace("spatial"); window.spatialCommandBus?.dispatch({ action: "NAVIGATE", params: { latitude: 40.7128, longitude: -74.0060, rangeM: 15000, name: "New York City, USA" } }); } },
    { title: "Spatial: Fly to San Francisco", category: "Spatial Intelligence", shortcut: "", action: () => { switchWorkspace("spatial"); window.spatialCommandBus?.dispatch({ action: "NAVIGATE", params: { latitude: 37.7749, longitude: -122.4194, rangeM: 15000, name: "San Francisco, USA" } }); } },
    { title: "Spatial: Fly to Dhaka", category: "Spatial Intelligence", shortcut: "", action: () => { switchWorkspace("spatial"); window.spatialCommandBus?.dispatch({ action: "NAVIGATE", params: { latitude: 23.8103, longitude: 90.4125, rangeM: 15000, name: "Dhaka, Bangladesh" } }); } },
    { title: "Spatial: Toggle Flight Layer", category: "Spatial Intelligence", shortcut: "", action: () => { switchWorkspace("spatial"); window.spatialCommandBus?.dispatch({ action: "TOGGLE_LAYER", params: { layerId: "flights" } }); } },
    { title: "Spatial: Toggle Weather Layer", category: "Spatial Intelligence", shortcut: "", action: () => { switchWorkspace("spatial"); window.spatialCommandBus?.dispatch({ action: "TOGGLE_LAYER", params: { layerId: "weather" } }); } },
    { title: "Spatial: Toggle Satellite Layer", category: "Spatial Intelligence", shortcut: "", action: () => { switchWorkspace("spatial"); window.spatialCommandBus?.dispatch({ action: "TOGGLE_LAYER", params: { layerId: "satellites" } }); } },
    { title: "Spatial: NVG Surveillance Sensor Mode", category: "Spatial Intelligence", shortcut: "", action: () => { switchWorkspace("spatial"); window.spatialCommandBus?.dispatch({ action: "SET_VISUAL_STYLE", params: { style: "surveillance" } }); } },
    { title: "Spatial: FLIR Thermal Sensor Mode", category: "Spatial Intelligence", shortcut: "", action: () => { switchWorkspace("spatial"); window.spatialCommandBus?.dispatch({ action: "SET_VISUAL_STYLE", params: { style: "thermal" } }); } },
    { title: "Spatial: Standard Sensor Mode", category: "Spatial Intelligence", shortcut: "", action: () => { switchWorkspace("spatial"); window.spatialCommandBus?.dispatch({ action: "SET_VISUAL_STYLE", params: { style: "normal" } }); } },

    { title: "Check Unread Emails", category: "PC Actions", shortcut: "", action: () => transmitCommand("Jarvis, check my emails and give me an executive brief") },
    { title: "Capture Screen", category: "PC Actions", shortcut: "", action: () => transmitCommand("Jarvis, take a screenshot") },
    { title: "Lock Workstation", category: "PC Actions", shortcut: "", action: () => transmitCommand("Jarvis, lock my computer") },
    { title: "Launch Jarvis Chrome Profile", category: "PC Actions", shortcut: "", action: () => transmitCommand("Jarvis, open dedicated browser profile named Jarvis") },
    { title: "Open Desktop Created Files Folder", category: "PC Actions", shortcut: "Ctrl+O", action: () => window.openDesktopCodeFolder() },
    { title: "Emergency Hard Abort", category: "PC Actions", shortcut: "Esc", action: () => window.executeEmergencyStop() },

    { title: "Dispatch Coding Specialist", category: "Agents", shortcut: "", action: () => { switchWorkspace("agents"); const b = document.querySelector(".spec-tab-btn[data-spec='coding']"); if (b) b.click(); } },
    { title: "Dispatch Research Specialist", category: "Agents", shortcut: "", action: () => { switchWorkspace("agents"); const b = document.querySelector(".spec-tab-btn[data-spec='research']"); if (b) b.click(); } },
    { title: "Dispatch Marketing Specialist", category: "Agents", shortcut: "", action: () => { switchWorkspace("agents"); const b = document.querySelector(".spec-tab-btn[data-spec='marketing']"); if (b) b.click(); } },
    { title: "Dispatch SEO & Eventbrite Agent", category: "Agents", shortcut: "", action: () => { switchWorkspace("agents"); const b = document.querySelector(".spec-tab-btn[data-spec='seo']"); if (b) b.click(); } },
    { title: "Dispatch B2B Lead Gen Agent", category: "Agents", shortcut: "", action: () => { switchWorkspace("agents"); const b = document.querySelector(".spec-tab-btn[data-spec='leadgen']"); if (b) b.click(); } }
  ];

  let selectedPaletteIndex = 0;
  let filteredCommands = [];

  window.openCommandPalette = function() {
    const modal = document.getElementById("cmdPaletteModal");
    const input = document.getElementById("inpCmdPalette");
    if (!modal || !input) return;

    modal.classList.add("open");
    input.value = "";
    selectedPaletteIndex = 0;
    renderPaletteResults("");
    setTimeout(() => input.focus(), 60);
    playSound("blip");
  };

  window.closeCommandPalette = function() {
    const modal = document.getElementById("cmdPaletteModal");
    if (modal) modal.classList.remove("open");
  };

  function renderPaletteResults(query) {
    const resultsContainer = document.getElementById("cmdPaletteResults");
    if (!resultsContainer) return;

    const q = (query || "").toLowerCase().trim();
    filteredCommands = COMMANDS_REGISTRY.filter(cmd => {
      return !q || cmd.title.toLowerCase().includes(q) || cmd.category.toLowerCase().includes(q);
    });

    if (filteredCommands.length === 0) {
      resultsContainer.innerHTML = `<div style="padding:16px; font-family:var(--font-mono); font-size:12px; color:var(--hud-text-muted); text-align:center;">No matching directives found for "${escapeHtml(query)}"</div>`;
      return;
    }

    const groups = {};
    filteredCommands.forEach((cmd, idx) => {
      if (!groups[cmd.category]) groups[cmd.category] = [];
      groups[cmd.category].push({ cmd, idx });
    });

    let html = "";
    for (const [category, items] of Object.entries(groups)) {
      html += `<div class="cmd-palette-group-title">${escapeHtml(category)}</div>`;
      items.forEach(({ cmd, idx }) => {
        const isSel = idx === selectedPaletteIndex;
        html += `
          <div class="cmd-palette-item ${isSel ? 'selected' : ''}" data-idx="${idx}">
            <div class="cmd-palette-item-left">
              <span>${escapeHtml(cmd.title)}</span>
            </div>
            ${cmd.shortcut ? `<span class="cmd-palette-item-shortcut">${escapeHtml(cmd.shortcut)}</span>` : ''}
          </div>
        `;
      });
    }

    resultsContainer.innerHTML = html;

    resultsContainer.querySelectorAll(".cmd-palette-item").forEach(el => {
      el.addEventListener("click", () => {
        const idx = parseInt(el.getAttribute("data-idx"), 10);
        executePaletteIndex(idx);
      });
    });
  }

  function executePaletteIndex(idx) {
    if (filteredCommands[idx]) {
      closeCommandPalette();
      filteredCommands[idx].action();
    }
  }

  const inpCmdPalette = document.getElementById("inpCmdPalette");
  if (inpCmdPalette) {
    inpCmdPalette.addEventListener("input", (e) => {
      selectedPaletteIndex = 0;
      renderPaletteResults(e.target.value);
    });

    inpCmdPalette.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        selectedPaletteIndex = Math.min(selectedPaletteIndex + 1, filteredCommands.length - 1);
        renderPaletteResults(inpCmdPalette.value);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        selectedPaletteIndex = Math.max(selectedPaletteIndex - 1, 0);
        renderPaletteResults(inpCmdPalette.value);
      } else if (e.key === "Enter") {
        e.preventDefault();
        executePaletteIndex(selectedPaletteIndex);
      } else if (e.key === "Escape") {
        e.preventDefault();
        closeCommandPalette();
      }
    });
  }

  // Click outside Command Palette modal closes it
  const cmdPaletteModal = document.getElementById("cmdPaletteModal");
  if (cmdPaletteModal) {
    cmdPaletteModal.addEventListener("click", (e) => {
      if (e.target === cmdPaletteModal) closeCommandPalette();
    });
  }

  // 5. Notification Center Drawer
  const btnOpenNotifications = document.getElementById("btnOpenNotifications");
  const notificationDrawer = document.getElementById("notificationDrawer");
  const btnCloseNotifications = document.getElementById("btnCloseNotifications");
  const btnClearNotifications = document.getElementById("btnClearNotifications");

  if (btnOpenNotifications && notificationDrawer) {
    btnOpenNotifications.addEventListener("click", () => {
      notificationDrawer.classList.toggle("open");
      playSound("blip");
    });
  }
  if (btnCloseNotifications && notificationDrawer) {
    btnCloseNotifications.addEventListener("click", () => {
      notificationDrawer.classList.remove("open");
    });
  }
  if (btnClearNotifications) {
    btnClearNotifications.addEventListener("click", () => {
      const list = document.getElementById("notificationList");
      const badge = document.getElementById("notificationBadgeCount");
      if (list) list.innerHTML = `<div style="padding:14px; text-align:center; color:var(--hud-text-muted); font-size:12px;">All notifications cleared.</div>`;
      systemNotifications.length = 0;
      if (badge) badge.innerText = "0";
      playSound("blip");
    });
  }

  // 6. Header Buttons & Legacy Hooks
  const btnOpenCmdPalette = document.getElementById("btnOpenCmdPalette");
  if (btnOpenCmdPalette) {
    btnOpenCmdPalette.addEventListener("click", openCommandPalette);
  }

  // Link legacy modal buttons to switch directly to full workspaces
  const legacyLinks = [
    { id: "btnOpenDedicatedChat", ws: "chat" },
    { id: "btnSpecialistsDeck", ws: "agents" },
    { id: "btnBrowserResearchHeader", ws: "research" },
    { id: "btnMarketingHub", ws: "marketing" },
    { id: "btnMemoryVault", ws: "memory" },
    { id: "btnDiagnostics", ws: "diagnostics" },
    { id: "btnSettings", ws: "settings" }
  ];
  legacyLinks.forEach(({ id, ws }) => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener("click", () => switchWorkspace(ws));
    }
  });

  const btnRefreshOps = document.getElementById("btnRefreshOps");
  if (btnRefreshOps) {
    btnRefreshOps.addEventListener("click", () => {
      playSound("blip");
      if (typeof window.refreshOperationsPipeline === "function") {
        window.refreshOperationsPipeline();
      }
      showToast("Operations pipeline refreshed", "info", 1500);
    });
  }

  // 7. Global Keyboard Shortcuts
  window.addEventListener("keydown", (e) => {
    // ESC: Emergency Abort or Close Modals
    if (e.key === "Escape") {
      const cmdPalette = document.getElementById("cmdPaletteModal");
      const notifDrawer = document.getElementById("notificationDrawer");
      if (cmdPalette && cmdPalette.classList.contains("open")) {
        closeCommandPalette();
        return;
      }
      if (notifDrawer && notifDrawer.classList.contains("open")) {
        notifDrawer.classList.remove("open");
        return;
      }
      const activeModals = document.querySelectorAll(".modal-overlay.active");
      if (activeModals.length > 0) {
        activeModals.forEach(m => m.classList.remove("active"));
        return;
      }
      window.executeEmergencyStop();
      return;
    }

    // Ctrl + K: Command Palette
    if ((e.ctrlKey || e.metaKey) && (e.key === "k" || e.key === "K")) {
      e.preventDefault();
      openCommandPalette();
      return;
    }

    // Alt + M: Toggle Navigation Rail
    if (e.altKey && (e.key === "m" || e.key === "M")) {
      e.preventDefault();
      if (mainNavRail) {
        mainNavRail.classList.toggle("expanded");
        localStorage.setItem("jarvis_nav_expanded", mainNavRail.classList.contains("expanded"));
      }
      return;
    }

    // Alt + Number (0-9): Workspace Switcher
    if (e.altKey && e.key >= "0" && e.key <= "9") {
      e.preventDefault();
      const numMap = {
        "1": "command_center",
        "2": "chat",
        "3": "agents",
        "4": "operations",
        "5": "research",
        "6": "marketing",
        "7": "family",
        "8": "memory",
        "9": "diagnostics",
        "0": "spatial"
      };
      if (numMap[e.key]) switchWorkspace(numMap[e.key]);
      return;
    }

    // Ctrl + O: Open Artifacts Folder
    if (e.ctrlKey && (e.key === "o" || e.key === "O")) {
      e.preventDefault();
      window.openDesktopCodeFolder();
      return;
    }

    // F11: Toggle Fullscreen
    if (e.key === "F11") {
      e.preventDefault();
      if (window.pywebview && window.pywebview.api && window.pywebview.api.toggle_fullscreen) {
        window.pywebview.api.toggle_fullscreen();
      }
      return;
    }
  });

  // Final verification of Reference Command Center
  initReferenceCommandCenter();
});

// Also immediately initialize Reference Command Center if DOM is already ready
if (document.readyState === "complete" || document.readyState === "interactive") {
  setTimeout(initReferenceCommandCenter, 10);
}

