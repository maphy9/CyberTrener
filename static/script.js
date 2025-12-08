const socket = io("http://localhost:5000");

const btnStart = document.getElementById("btn-start");
const btnStop = document.getElementById("btn-stop");
const statusSpan = document.getElementById("status");
const frontImg = document.getElementById("front-image");
const profileImg = document.getElementById("profile-image");

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
  statusSpan.style.color = "green";
});

socket.on("disconnect", () => {
  statusSpan.innerText = "Disconnected";
  statusSpan.style.color = "red";
  resetUI();
});

socket.on("front-frame", (data) => {
  updateImage(frontImg, data);
});

socket.on("profile-frame", (data) => {
  updateImage(profileImg, data);
});

function resetUI() {
  btnStart.disabled = false;
  btnStop.disabled = true;
  statusSpan.innerText = "Session Ended";
  statusSpan.style.color = "#666";
  frontImg.src = "";
  profileImg.src = "";
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
