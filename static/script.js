let timerInterval;
let seconds = 0;
let timerStarted = false;
let pressedStop = true;

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
const tipsMessage = document.getElementById("tips-message");

function startTimer() {
  if (timerStarted) {
    return;
  }
  timerStarted = true;
  seconds = 0;
  updateTimerDisplay();
  timerInterval = setInterval(() => {
    if (pressedStop) {
      return;
    }
    seconds++;
    updateTimerDisplay();
  }, 1000);
}

function stopTimer() {
  timerStarted = false;
  clearInterval(timerInterval);
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

btnStart.addEventListener("click", () => {
  pressedStop = false;
  socket.emit("start-session");
  btnStart.disabled = true;
  btnStop.disabled = false;
});

btnStop.addEventListener("click", () => {
  pressedStop = true;
  socket.emit("end-session");
  resetUI();
  stopTimer();
  statusFront.textContent = "Rozłączono";
  statusDotFront.style.background = "var(--bad)";
  statusProfile.textContent = "Rozłączono";
  statusDotProfile.style.background = "var(--bad)";
  if (tipsMessage) {
    tipsMessage.textContent = "";
    tipsMessage.style.display = "none";
  }
});

function changeStateToConnected() {
  statusFront.textContent = "Połączono";
  statusDotFront.style.background = "var(--perfect)";
  statusProfile.textContent = "Połączono";
  statusDotProfile.style.background = "var(--perfect)";
}

socket.on("status", (data) => {
  if (data.state === "waiting") {
    if (tipsMessage) {
      tipsMessage.textContent =
        "Powiedz 'start' aby rozpocząć lub 'stop' aby anulować";
      tipsMessage.style.display = "block";
      tipsMessage.style.fontSize = "1.2rem";
      tipsMessage.style.color = "var(--primary)";
      tipsMessage.style.textAlign = "center";
      tipsMessage.style.marginTop = "1rem";
    }
  } else if (data.state === "analyzing") {
    if (tipsMessage) {
      tipsMessage.textContent = "Powiedz 'stop' lub 'koniec' aby zakończyć";
      tipsMessage.style.fontSize = "0.9rem";
      tipsMessage.style.color = "var(--text-muted)";
    }
    startTimer();
  }
});

socket.on("front-frame", (data) => {
  if (pressedStop) {
    return;
  }
  changeStateToConnected();
  updateImage(frontImg, data, placeholderFront);
});

socket.on("profile-frame", (data) => {
  if (pressedStop) {
    return;
  }
  changeStateToConnected();
  updateImage(profileImg, data, placeholderProfile);
});

socket.on("metrics", (data) => {
  if (rightRepsSpan) rightRepsSpan.textContent = data.right_reps;
  if (leftRepsSpan) leftRepsSpan.textContent = data.left_reps;
});

socket.on("voice-stop", () => {
  pressedStop = true;
  resetUI();
  stopTimer();
  statusFront.textContent = "Rozłączono";
  statusDotFront.style.background = "var(--bad)";
  statusProfile.textContent = "Rozłączono";
  statusDotProfile.style.background = "var(--bad)";
  if (tipsMessage) {
    tipsMessage.textContent = "";
    tipsMessage.style.display = "none";
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
