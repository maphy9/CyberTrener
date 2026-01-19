const trainingSettings = JSON.parse(
  localStorage.getItem("trainingSettings"),
) || {
  exercises: ["bicep_curl", "overhead_press"],
  repsPerExercise: { bicep_curl: 10, overhead_press: 10 },
  rounds: 3,
  cameraSettings: {
    front: { type: "physical", value: 0 },
    profile: { type: "ip", value: "" },
  },
  forceCalibration: false,
};

const sessionMode = localStorage.getItem("sessionMode") || "unified";

const EXERCISE_NAMES = {
  bicep_curl: "Uginanie przedramion",
  overhead_press: "Wyciskanie nad głowę",
};

const exerciseNameSpan = document.getElementById("exercise-name");
const roundInfo = document.getElementById("round-info");
const roundText = document.getElementById("round-text");

if (exerciseNameSpan) {
  exerciseNameSpan.textContent = "Kalibracja";
}
if (roundText) {
  roundText.textContent = "Kliknij POŁĄCZ";
}

const targetRepsSpan = document.getElementById("target-reps");
const targetRepsLeftSpan = document.getElementById("target-reps-left");
const statsBoxInit = document.getElementById("stats-box");
if (statsBoxInit) {
  statsBoxInit.style.display = "none";
}

let timerInterval;
let seconds = 0;
let timerStarted = false;
let isConnected = false;
let isAnalyzing = false;
let isCalibrating = false;
let currentPhase = "connecting";

const socket = io("http://localhost:5000");

const cameraSettings = trainingSettings.cameraSettings;

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
const calibrationInstruction = document.getElementById(
  "calibration-instruction",
);
const calibrationProgress = document.getElementById("calibration-progress");
const statsBox = document.getElementById("stats-box");
const completeBox = document.getElementById("complete-box");
const statRightRow = document.getElementById("stat-right-row");
const statLeftRow = document.getElementById("stat-left-row");

const STEP_NAMES = {
  neutral: "Pozycja neutralna",
  right_flex: "Prawa ręka - zgięcie",
  right_extend: "Prawa ręka - wyprost",
  left_flex: "Lewa ręka - zgięcie",
  left_extend: "Lewa ręka - wyprost",
  overhead_start: "Wyciskanie - start",
  overhead_top: "Wyciskanie - góra",
  complete: "Zakończono",
};

const STEP_ORDER = [
  "neutral",
  "right_flex",
  "right_extend",
  "left_flex",
  "left_extend",
  "overhead_start",
  "overhead_top",
];

function showCalibrationUI() {
  if (calibrationBox) {
    calibrationBox.style.display = "block";
  }
  if (statsBox) {
    statsBox.style.display = "none";
  }
  currentPhase = "calibration";
}

function hideCalibrationUI() {
  if (calibrationBox) {
    calibrationBox.style.display = "none";
  }
  if (statsBox) {
    statsBox.style.display = "block";
  }
}

function showExerciseUI() {
  hideCalibrationUI();
  if (completeBox) {
    completeBox.style.display = "none";
  }
  currentPhase = "exercise";
}

function showCompleteUI(stats) {
  if (statsBox) {
    statsBox.style.display = "none";
  }
  if (completeBox) {
    completeBox.style.display = "block";

    const totalRepsEl = document.getElementById("total-reps");
    const totalErrorsEl = document.getElementById("total-errors");
    const breakdownEl = document.getElementById("exercise-breakdown");

    if (totalRepsEl) totalRepsEl.textContent = stats.totalReps || 0;
    if (totalErrorsEl) totalErrorsEl.textContent = stats.totalErrors || 0;

    if (breakdownEl && stats.exerciseStats) {
      let html = '<div class="exercise-breakdown-list">';
      for (const [name, data] of Object.entries(stats.exerciseStats)) {
        html += `<p>${name}: <strong>${data.reps}</strong> powt., <strong>${data.errors}</strong> błędów</p>`;
      }
      html += "</div>";
      breakdownEl.innerHTML = html;
    }
  }
  currentPhase = "complete";
}

function updateExerciseDisplay(exerciseType) {
  if (exerciseNameSpan) {
    exerciseNameSpan.textContent = EXERCISE_NAMES[exerciseType] || exerciseType;
  }

  if (statLeftRow) {
    if (exerciseType === "overhead_press") {
      statLeftRow.style.display = "none";
      if (statRightRow) {
        const label = statRightRow.querySelector(".stat-label");
        if (label) label.textContent = "Powtórzenia:";
      }
    } else {
      statLeftRow.style.display = "flex";
      if (statRightRow) {
        const label = statRightRow.querySelector(".stat-label");
        if (label) label.textContent = "Prawe ramię:";
      }
    }
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
  const progress = stepIndex >= 0 ? (stepIndex / STEP_ORDER.length) * 100 : 0;
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

function showCalibrationLoading() {
  showCalibrationUI();
  if (calibrationStepText) {
    calibrationStepText.textContent = "Inicjalizacja...";
  }
  if (calibrationInstruction) {
    calibrationInstruction.textContent = "Łączenie z kamerami...";
  }
  if (calibrationProgress) {
    calibrationProgress.style.width = "0%";
  }
  document.querySelectorAll(".step-dot").forEach((dot) => {
    dot.classList.remove("active", "completed");
  });
}

btnConnect.addEventListener("click", () => {
  btnConnect.disabled = true;
  btnConnect.textContent = "ŁĄCZENIE...";

  setVoiceStatus("Łączenie z kamerami...");

  socket.emit("start-session", {
    cameras: cameraSettings,
    mode: sessionMode,
    trainingSettings: trainingSettings,
  });
  btnDisconnect.disabled = false;
  isConnected = true;
});

btnDisconnect.addEventListener("click", () => {
  socket.emit("end-session");
  fullDisconnect();
});

function fullDisconnect() {
  isConnected = false;
  isAnalyzing = false;
  btnConnect.textContent = "CONNECT";

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
  btnConnect.textContent = "POŁĄCZ";
  if (data.state === "waiting") {
    isAnalyzing = false;
    setVoiceStatus("Powiedz 'zacznij' lub kliknij przycisk");
  } else if (data.state === "analyzing") {
    isAnalyzing = true;
    setVoiceStatus(
      "Trening w toku... (powiedz 'następne' lub 'poprzednie' aby zmienić ćwiczenie)",
    );
    startTimer();
  }
});

socket.on("session-phase", (data) => {
  if (data.phase === "calibration") {
    isCalibrating = true;
    showCalibrationLoading();
    setVoiceStatus("Rozpoczynam kalibrację...");
  } else if (data.phase === "exercise") {
    isCalibrating = false;
    showExerciseUI();
  }
});

socket.on("training-state", (data) => {
  if (exerciseNameSpan && data.currentExercise) {
    exerciseNameSpan.textContent = data.currentExercise;
  }

  if (roundText) {
    roundText.textContent = `Runda ${data.currentRound}/${data.totalRounds}`;
  }

  if (targetRepsSpan) {
    targetRepsSpan.textContent = data.targetReps || 10;
  }
  if (targetRepsLeftSpan) {
    targetRepsLeftSpan.textContent = data.targetReps || 10;
  }

  if (data.currentExerciseType) {
    updateExerciseDisplay(data.currentExerciseType);
  }
});

socket.on("training-complete", (data) => {
  showCompleteUI(data);
  setVoiceStatus("Trening zakończony! 🎉");
  stopTimer();
});

socket.on("connection-error", (data) => {
  alert(
    `Błąd połączenia z kamerą: ${data.message}\nSprawdź ustawienia kamer na stronie głównej.`,
  );
  fullDisconnect();
  if (sessionMode === "calibration") {
    hideCalibrationUI();
  }
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
    calibrationInstruction.textContent =
      "Kalibracja zakończona. Przechodzimy do treningu...";
  }

  setVoiceStatus("Kalibracja zakończona! Rozpoczynam trening...");
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
