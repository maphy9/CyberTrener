const frontTypeRadios = document.querySelectorAll('input[name="front-type"]');
const profileTypeRadios = document.querySelectorAll(
  'input[name="profile-type"]'
);
const frontPhysicalInput = document.getElementById("front-physical-input");
const frontIpInput = document.getElementById("front-ip-input");
const profilePhysicalInput = document.getElementById("profile-physical-input");
const profileIpInput = document.getElementById("profile-ip-input");
const startTrainingBtn = document.getElementById("start-training-btn");
const startCalibrationBtn = document.getElementById("start-calibration-btn");
const calibrationStatus = document.getElementById("calibration-status");

function checkCalibrationStatus() {
  fetch("/api/calibration-status")
    .then((res) => res.json())
    .then((data) => {
      if (data.calibrated) {
        calibrationStatus.textContent = `✓ Skalibrowano: ${data.date}`;
        calibrationStatus.className = "calibration-status calibrated";
      } else {
        calibrationStatus.textContent = "⚠ Brak kalibracji";
        calibrationStatus.className = "calibration-status not-calibrated";
      }
    })
    .catch(() => {
      calibrationStatus.textContent = "";
    });
}

function getCameraSettings() {
  const frontType = document.querySelector(
    'input[name="front-type"]:checked'
  ).value;
  const profileType = document.querySelector(
    'input[name="profile-type"]:checked'
  ).value;

  let frontValue, profileValue;

  if (frontType === "physical") {
    frontValue = parseInt(document.getElementById("front-index").value);
  } else {
    frontValue = document.getElementById("front-url").value.trim();
    if (!frontValue) {
      alert("Podaj adres URL dla kamery frontalnej");
      return null;
    }
  }

  if (profileType === "physical") {
    profileValue = parseInt(document.getElementById("profile-index").value);
  } else {
    profileValue = document.getElementById("profile-url").value.trim();
    if (!profileValue) {
      alert("Podaj adres URL dla kamery profilowej");
      return null;
    }
  }

  if (
    frontType === "physical" &&
    profileType === "physical" &&
    frontValue === profileValue
  ) {
    alert("Nie możesz użyć tej samej kamery fizycznej dla obu widoków");
    return null;
  }

  return {
    front: { type: frontType, value: frontValue },
    profile: { type: profileType, value: profileValue },
  };
}

function loadSettings() {
  const settings = localStorage.getItem("cameraSettings");
  if (settings) {
    const parsed = JSON.parse(settings);

    if (parsed.front.type === "physical") {
      document.querySelector(
        'input[name="front-type"][value="physical"]'
      ).checked = true;
      document.getElementById("front-index").value = parsed.front.value;
      frontPhysicalInput.style.display = "block";
      frontIpInput.style.display = "none";
    } else {
      document.querySelector(
        'input[name="front-type"][value="ip"]'
      ).checked = true;
      document.getElementById("front-url").value = parsed.front.value;
      frontPhysicalInput.style.display = "none";
      frontIpInput.style.display = "block";
    }

    if (parsed.profile.type === "physical") {
      document.querySelector(
        'input[name="profile-type"][value="physical"]'
      ).checked = true;
      document.getElementById("profile-index").value = parsed.profile.value;
      profilePhysicalInput.style.display = "block";
      profileIpInput.style.display = "none";
    } else {
      document.querySelector(
        'input[name="profile-type"][value="ip"]'
      ).checked = true;
      document.getElementById("profile-url").value = parsed.profile.value;
      profilePhysicalInput.style.display = "none";
      profileIpInput.style.display = "block";
    }
  }
}

frontTypeRadios.forEach((radio) => {
  radio.addEventListener("change", (e) => {
    if (e.target.value === "physical") {
      frontPhysicalInput.style.display = "block";
      frontIpInput.style.display = "none";
    } else {
      frontPhysicalInput.style.display = "none";
      frontIpInput.style.display = "block";
    }
  });
});

profileTypeRadios.forEach((radio) => {
  radio.addEventListener("change", (e) => {
    if (e.target.value === "physical") {
      profilePhysicalInput.style.display = "block";
      profileIpInput.style.display = "none";
    } else {
      profilePhysicalInput.style.display = "none";
      profileIpInput.style.display = "block";
    }
  });
});

startTrainingBtn.addEventListener("click", () => {
  const settings = getCameraSettings();
  if (!settings) return;

  fetch("/api/calibration-status")
    .then((res) => res.json())
    .then((data) => {
      if (!data.calibrated) {
        if (confirm("Brak kalibracji. Czy chcesz najpierw przeprowadzić kalibrację?")) {
          localStorage.setItem("cameraSettings", JSON.stringify(settings));
          localStorage.setItem("sessionMode", "calibration");
          window.location.href = "/training";
        }
      } else {
        localStorage.setItem("cameraSettings", JSON.stringify(settings));
        localStorage.setItem("sessionMode", "training");
        window.location.href = "/training";
      }
    })
    .catch(() => {
      localStorage.setItem("cameraSettings", JSON.stringify(settings));
      localStorage.setItem("sessionMode", "training");
      window.location.href = "/training";
    });
});

startCalibrationBtn.addEventListener("click", () => {
  const settings = getCameraSettings();
  if (!settings) return;

  localStorage.setItem("cameraSettings", JSON.stringify(settings));
  localStorage.setItem("sessionMode", "calibration");
  window.location.href = "/training";
});

loadSettings();
checkCalibrationStatus();
