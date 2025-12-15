const socket = io("http://localhost:5000");

const btnStart = document.getElementById("btn-start");
const btnStop = document.getElementById("btn-stop");
const statusSpan = document.getElementById("status");
const frontImg = document.getElementById("front-image");
const profileImg = document.getElementById("profile-image");
const rightRepsSpan = document.getElementById("right-reps");
const leftRepsSpan = document.getElementById("left-reps");

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

btnStart.addEventListener("click", () => {
  socket.emit("start-session");
  btnStart.disabled = true;
  btnStop.disabled = false;
  statusSpan.innerText = "Streaming...";
  prevRightReps = 0;
  prevLeftReps = 0;
  prevErrors.clear();
});

btnStop.addEventListener("click", () => {
  socket.emit("end-session");
  resetUI();
});

socket.on("connect", () => {
  statusSpan.innerText = "Connected to Server";
  statusSpan.style.color = "#22c55e";
});

socket.on("disconnect", () => {
  statusSpan.innerText = "Disconnected";
  statusSpan.style.color = "#ef4444";
  resetUI();
});

socket.on("front-frame", (data) => {
  updateImage(frontImg, data);
});

socket.on("profile-frame", (data) => {
  updateImage(profileImg, data);
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

  rightRepsSpan.innerText = data.right_reps;
  leftRepsSpan.innerText = data.left_reps;

  if (data.errors && data.errors.length > 0) {
    data.errors.forEach((error) => {
      if (!prevErrors.has(error)) {
        queueSound({ type: "speech", text: error });
        prevErrors.add(error);
      }
    });
  }
});

function resetUI() {
  btnStart.disabled = false;
  btnStop.disabled = true;
  statusSpan.innerText = "Session Ended";
  statusSpan.style.color = "#b0b0b0";
  frontImg.src = "";
  profileImg.src = "";
  rightRepsSpan.innerText = "0";
  leftRepsSpan.innerText = "0";
  prevRightReps = 0;
  prevLeftReps = 0;
  prevErrors.clear();
  soundQueue.length = 0;
  speechSynth.cancel();
}

function updateImage(imgElement, data) {
  const arrayBufferView = new Uint8Array(data);
  const blob = new Blob([arrayBufferView], { type: "image/jpeg" });
  const url = URL.createObjectURL(blob);

  if (imgElement.src) {
    URL.revokeObjectURL(imgElement.src);
  }

  const placeholders = document.getElementsByClassName("placeholder");
  for (const placeholder of placeholders) {
    placeholder.innerText = "";
  }

  imgElement.src = url;
}
