let timerInterval;
let seconds = 0;
let timerStarted = false;

const socket = io("http://localhost:5000");

const btnStart = document.getElementById("btn-start");
const btnStop = document.getElementById("btn-stop");
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
let skeletons = document.getElementsByClassName("skeleton-preview");

let prevRightReps = 0;
let prevLeftReps = 0;
let prevErrors = new Set();

const audioContext = new (window.AudioContext || window.webkitAudioContext)();
const speechSynth = window.speechSynthesis;
const soundQueue = [];
let isPlaying = false;

function playBeep() {
  return new Promise((resolve) => {
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);

    oscillator.frequency.value = 800;
    oscillator.type = "sine";

    gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(
      0.01,
      audioContext.currentTime + 0.1
    );

    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.1);

    oscillator.onended = resolve;
  });
}

function speakText(text) {
  return new Promise((resolve) => {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 0.8;
    utterance.onend = resolve;
    utterance.onerror = resolve;
    speechSynth.speak(utterance);
  });
}

async function processQueue() {
  if (isPlaying || soundQueue.length === 0) return;

  isPlaying = true;
  const sound = soundQueue.shift();

  if (sound.type === "beep") {
    await playBeep();
  } else if (sound.type === "speech") {
    await speakText(sound.text);
  }

  isPlaying = false;
  processQueue();
}

function queueSound(sound) {
  soundQueue.push(sound);
  processQueue();
}

function startTimer() {
  if (timerStarted) return;
  timerStarted = true;
  seconds = 0;
  updateTimerDisplay();
  timerInterval = setInterval(() => {
    seconds++;
    updateTimerDisplay();
  }, 1000);
}

function stopTimer() {
  clearInterval(timerInterval);
  updateTimerDisplay();
  setTimeout(() => (timerStarted = false), 200);
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

if (document.getElementById("timer")) {
  updateTimerDisplay();
}

if (btnStart) {
  btnStart.addEventListener("click", () => {
    socket.emit("start-session");
    btnStart.disabled = true;
    btnStop.disabled = false;
    prevRightReps = 0;
    prevLeftReps = 0;
    prevErrors.clear();
    tipsMessage.textContent = "Czekam na pierwsze klatki...";
  });
}

if (btnStop) {
  btnStop.addEventListener("click", () => {
    socket.emit("end-session");
    resetUI();
    stopTimer();
    setTimeout(() => {
      if (statusFront) {
        statusFront.textContent = "Roz\u0142ączono";
        statusDotFront.style.background = "var(--bad)";
      }
      if (statusProfile) {
        statusProfile.textContent = "Roz\u0142ączono";
        statusDotProfile.style.background = "var(--bad)";
      }
    }, 200);
  });
}

function changeStateToConnected() {
  if (statusFront) {
    statusFront.textContent = "Po\u0142ączono";
    statusDotFront.style.background = "var(--perfect)";
  }
  if (statusProfile) {
    statusProfile.textContent = "Po\u0142ączono";
    statusDotProfile.style.background = "var(--perfect)";
  }
}

socket.on("front-frame", (data) => {
  if (!timerStarted) {
    startTimer();
  }
  changeStateToConnected();
  updateImage(frontImg, data, placeholderFront);
});

socket.on("profile-frame", (data) => {
  if (!timerStarted) {
    startTimer();
  }
  changeStateToConnected();
  updateImage(profileImg, data, placeholderProfile);
});

socket.on("metrics", (data) => {
  if (data.right_reps > prevRightReps) {
    queueSound({ type: "beep" });
    prevRightReps = data.right_reps;
  }

  if (data.left_reps > prevLeftReps) {
    queueSound({ type: "beep" });
    prevLeftReps = data.left_reps;
  }

  if (rightRepsSpan) rightRepsSpan.textContent = data.right_reps;
  if (leftRepsSpan) leftRepsSpan.textContent = data.left_reps;

  if (data.errors && data.errors.length > 0) {
    data.errors.forEach((error) => {
      if (!prevErrors.has(error)) {
        queueSound({ type: "speech", text: error });
        prevErrors.add(error);
        if (tipsMessage) tipsMessage.textContent = error;
      }
    });
  }
});

function resetUI() {
  if (btnStart) btnStart.disabled = false;
  if (btnStop) btnStop.disabled = true;

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

  if (tipsMessage) tipsMessage.textContent = "Gotowy do rozpoczęcia!";

  prevRightReps = 0;
  prevLeftReps = 0;
  prevErrors.clear();
  soundQueue.length = 0;
  speechSynth.cancel();
}

function updateImage(imgElement, data, placeholder) {
  const arrayBufferView = new Uint8Array(data);
  const blob = new Blob([arrayBufferView], { type: "image/jpeg" });
  const url = URL.createObjectURL(blob);

  if (imgElement.src) {
    URL.revokeObjectURL(imgElement.src);
  }

  if (placeholder) {
    placeholder.style.display = "none";
  }

  imgElement.style.display = "block";
  imgElement.src = url;

  for (const skeleton of skeletons) {
    skeleton.remove();
  }
  skeletons = [];
}
