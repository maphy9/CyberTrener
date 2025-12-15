const socket = io("http://localhost:5000");

const btnStart = document.getElementById("btn-start");
const btnStop = document.getElementById("btn-stop");
const statusSpan = document.getElementById("status");
const frontImg = document.getElementById("front-image");
const profileImg = document.getElementById("profile-image");
const rightRepsSpan = document.getElementById("right-reps");
const leftRepsSpan = document.getElementById("left-reps");

btnStart.addEventListener("click", () => {
  socket.emit("start-session");
  btnStart.disabled = true;
  btnStop.disabled = false;
  statusSpan.innerText = "Streaming...";
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
  rightRepsSpan.innerText = data.right_reps;
  leftRepsSpan.innerText = data.left_reps;

  if (data.errors && data.errors.length > 0) {
    console.log("Errors detected:", data.errors);
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
