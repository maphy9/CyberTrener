let timerInterval;
let seconds = 0;
let timerStarted = false;
let isConnected = false;
let isAnalyzing = false;
let isCalibrating = false;

const socket = io("http://localhost:5000");

const cameraSettings = JSON.parse(localStorage.getItem("cameraSettings")) || {
  front: { type: "physical", value: 0 },
  profile: { type: "ip", value: "" },
};

const sessionMode = localStorage.getItem("sessionMode") || "training";

const btnConnect = document.getElementById("btn-connect");
const btnDisconnect = document.getElementById("btn-disconnect");
const frontImg = document.getElementById("front-image");
const profileImg = document.getElementById("profile-image");
const rightRepsSpan = document.getElementById("right-reps");
const leftRepsSpan = document.getElementById("left-reps");
const statusFront = document.getElementById("status-front");
const statusProfile = document.getElementById("status-profile");
const statusDotFront = document.getElementById("status-dot-front");
const statusDotProfile = document.getElementById("status-dot-profile");
const placeholderFront = document.getElementById("placeholder-front");
const placeholderProfile = document.getElementById("placeholder-profile");
const voiceStatus = document.getElementById("voice-status");
const calibrationBox = document.getElementById("calibration-box");
const calibrationStepText = document.getElementById("calibration-step-text");
const calibrationInstruction = document.getElementById("calibration-instruction");
const calibrationProgress = document.getElementById("calibration-progress");

const STEP_NAMES = {
  neutral: "Pozycja neutralna",
  right_flex: "Prawa ręka - zgięcie",
  right_extend: "Prawa ręka - wyprost",
  left_flex: "Lewa ręka - zgięcie",
  left_extend: "Lewa ręka - wyprost",
  complete: "Zakończono"
};

const STEP_ORDER = ["neutral", "right_flex", "right_extend", "left_flex", "left_extend"];

function showCalibrationUI() {
  if (calibrationBox) {
    calibrationBox.style.display = "block";
  }
  const statsCompact = document.querySelector(".stats-compact");
  if (statsCompact) {
    statsCompact.style.display = "none";
  }
}

function hideCalibrationUI() {
  if (calibrationBox) {
    calibrationBox.style.display = "none";
  }
  const statsCompact = document.querySelector(".stats-compact");
  if (statsCompact) {
    statsCompact.style.display = "block";
  }
}

function updateCalibrationStep(step, instruction) {
  if (calibrationStepText) {
    calibrationStepText.textContent = STEP_NAMES[step] || step;
  }
  if (calibrationInstruction) {
    calibrationInstruction.textContent = instruction;
  }
  
  const stepIndex = STEP_ORDER.indexOf(step);
  const progress = stepIndex >= 0 ? ((stepIndex) / STEP_ORDER.length) * 100 : 0;
  if (calibrationProgress) {
    calibrationProgress.style.width = progress + "%";
  }
  
  document.querySelectorAll(".step-dot").forEach((dot, i) => {
    dot.classList.remove("active", "completed");
    if (i < stepIndex) {
      dot.classList.add("completed");
    } else if (i === stepIndex) {
      dot.classList.add("active");
    }
  });
}

function updateTimerDisplay() {
  const mins = Math.floor(seconds / 60)
    .toString()
    .padStart(2, "0");
  const secs = (seconds % 60).toString().padStart(2, "0");
  const timerElement = document.getElementById("timer");
  if (timerElement) {
    timerElement.textContent = `${mins}:${secs}`;
  }
}

function startTimer() {
  if (!timerStarted) {
    timerStarted = true;
    timerInterval = setInterval(() => {
      if (isAnalyzing) {
        seconds++;
        updateTimerDisplay();
      }
    }, 1000);
  }
}

function stopTimer() {
  timerStarted = false;
  clearInterval(timerInterval);
}

function resetTimer() {
  stopTimer();
  seconds = 0;
  updateTimerDisplay();
}

function setVoiceStatus(message) {
  if (voiceStatus) {
    voiceStatus.textContent = message;
    voiceStatus.classList.add("visible");
  }
}

function clearVoiceStatus() {
  if (voiceStatus) {
    voiceStatus.textContent = "";
    voiceStatus.classList.remove("visible");
  }
}

btnConnect.addEventListener("click", () => {
  socket.emit("start-session", {
    cameras: cameraSettings,
    mode: sessionMode
  });
  btnConnect.disabled = true;
  btnDisconnect.disabled = false;
  isConnected = true;
  
  if (sessionMode === "calibration") {
    isCalibrating = true;
    setVoiceStatus("Rozpoczynam kalibrację...");
  }
});

btnDisconnect.addEventListener("click", () => {
  socket.emit("end-session");
  fullDisconnect();
});

function fullDisconnect() {
  isConnected = false;
  isAnalyzing = false;

  resetTimer();
  resetUI();
  clearVoiceStatus();

  statusFront.textContent = "Rozłączono";
  statusDotFront.style.background = "var(--bad)";
  statusProfile.textContent = "Rozłączono";
  statusDotProfile.style.background = "var(--bad)";

  btnConnect.disabled = false;
  btnDisconnect.disabled = true;
}

function changeStateToConnected() {
  statusFront.textContent = "Połączono";
  statusDotFront.style.background = "var(--perfect)";
  statusProfile.textContent = "Połączono";
  statusDotProfile.style.background = "var(--perfect)";
}

socket.on("status", (data) => {
  if (data.state === "waiting") {
    isAnalyzing = false;
    setVoiceStatus("Powiedz 'zacznij' aby rozpocząć");
  } else if (data.state === "analyzing") {
    isAnalyzing = true;
    setVoiceStatus("Powiedz 'pauza' aby zatrzymać");
    startTimer();
  }
});

socket.on("connection-error", (data) => {
  alert(
    `Błąd połączenia z kamerą: ${data.message}\nSprawdź ustawienia kamer na stronie głównej.`
  );
  fullDisconnect();
});

socket.on("front-frame", (data) => {
  if (!isConnected) return;
  changeStateToConnected();
  updateImage(frontImg, data, placeholderFront);
});

socket.on("profile-frame", (data) => {
  if (!isConnected) return;
  changeStateToConnected();
  updateImage(profileImg, data, placeholderProfile);
});

socket.on("metrics", (data) => {
  if (rightRepsSpan) rightRepsSpan.textContent = data.right_reps;
  if (leftRepsSpan) leftRepsSpan.textContent = data.left_reps;
});

socket.on("calibration-step", (data) => {
  showCalibrationUI();
  updateCalibrationStep(data.step, data.instruction);
  setVoiceStatus(data.instruction);
});

socket.on("calibration-complete", (data) => {
  isCalibrating = false;
  
  if (calibrationProgress) {
    calibrationProgress.style.width = "100%";
  }
  document.querySelectorAll(".step-dot").forEach((dot) => {
    dot.classList.add("completed");
    dot.classList.remove("active");
  });
  if (calibrationStepText) {
    calibrationStepText.textContent = "Zakończono!";
  }
  if (calibrationInstruction) {
    calibrationInstruction.textContent = "Kalibracja zakończona pomyślnie.";
  }
  
  setVoiceStatus("Kalibracja zakończona! Przekierowuję...");
  localStorage.setItem("sessionMode", "training");
  setTimeout(() => {
    hideCalibrationUI();
    socket.emit("end-session");
    window.location.href = "/";
  }, 2000);
});

socket.on("session-ended", () => {
  fullDisconnect();
});

function resetUI() {
  if (frontImg) {
    frontImg.style.display = "none";
    frontImg.src = "";
  }
  if (profileImg) {
    profileImg.style.display = "none";
    profileImg.src = "";
  }

  if (placeholderFront) placeholderFront.style.display = "block";
  if (placeholderProfile) placeholderProfile.style.display = "block";

  if (rightRepsSpan) rightRepsSpan.textContent = "0";
  if (leftRepsSpan) leftRepsSpan.textContent = "0";
}

function updateImage(imgElement, data, placeholder) {
  const arrayBufferView = new Uint8Array(data);
  const blob = new Blob([arrayBufferView], { type: "image/jpeg" });
  const url = URL.createObjectURL(blob);

  imgElement.onload = function () {
    imgElement.onload = null;
  };

  if (imgElement.src) {
    URL.revokeObjectURL(imgElement.src);
  }

  if (placeholder) {
    placeholder.style.display = "none";
  }

  imgElement.style.display = "block";
  imgElement.src = url;
}
