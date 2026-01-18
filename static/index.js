// DOM Elements
const startTrainingBtn = document.getElementById("start-training-btn");
const settingsBtn = document.getElementById("settings-btn");
const historyBtn = document.getElementById("history-btn");
const settingsModal = document.getElementById("settings-modal");
const modalClose = document.getElementById("modal-close");
const saveSettingsBtn = document.getElementById("save-settings-btn");
const calibrationStatus = document.getElementById("calibration-status");

// Camera inputs
const frontTypeRadios = document.querySelectorAll('input[name="front-type"]');
const profileTypeRadios = document.querySelectorAll(
  'input[name="profile-type"]',
);
const frontPhysicalInput = document.getElementById("front-physical-input");
const frontIpInput = document.getElementById("front-ip-input");
const profilePhysicalInput = document.getElementById("profile-physical-input");
const profileIpInput = document.getElementById("profile-ip-input");

// Training settings inputs
const roundsInput = document.getElementById("rounds");
const exerciseList = document.getElementById("exercise-list");

// Default settings
const DEFAULT_SETTINGS = {
  exercises: ["bicep_curl", "overhead_press"],
  repsPerExercise: {
    bicep_curl: 10,
    overhead_press: 10,
  },
  rounds: 3,
  cameraSettings: {
    front: { type: "physical", value: 0 },
    profile: { type: "ip", value: "" },
  },
  forceCalibration: false,
};

// Load settings from localStorage or use defaults
function loadSettings() {
  const stored = localStorage.getItem("trainingSettings");
  if (stored) {
    try {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) };
    } catch (e) {
      return DEFAULT_SETTINGS;
    }
  }
  return DEFAULT_SETTINGS;
}

// Save settings to localStorage
function saveSettings(settings) {
  localStorage.setItem("trainingSettings", JSON.stringify(settings));
}

// Get current settings from UI
function getSettingsFromUI() {
  // Get exercise order and enabled state
  const exerciseItems = exerciseList.querySelectorAll(".exercise-item");
  const exercises = [];
  const repsPerExercise = {};

  exerciseItems.forEach((item) => {
    const checkbox = item.querySelector('input[type="checkbox"]');
    const repsInput = item.querySelector(".exercise-reps-input");
    const exerciseId = item.dataset.exercise;

    if (checkbox && checkbox.checked) {
      exercises.push(exerciseId);
    }
    if (repsInput) {
      repsPerExercise[exerciseId] = parseInt(repsInput.value) || 10;
    }
  });

  // Get camera settings
  const frontType = document.querySelector(
    'input[name="front-type"]:checked',
  ).value;
  const profileType = document.querySelector(
    'input[name="profile-type"]:checked',
  ).value;

  let frontValue, profileValue;
  if (frontType === "physical") {
    frontValue = parseInt(document.getElementById("front-index").value);
  } else {
    frontValue = document.getElementById("front-url").value.trim();
  }

  if (profileType === "physical") {
    profileValue = parseInt(document.getElementById("profile-index").value);
  } else {
    profileValue = document.getElementById("profile-url").value.trim();
  }

  return {
    exercises: exercises,
    repsPerExercise: repsPerExercise,
    rounds: parseInt(roundsInput.value) || 3,
    cameraSettings: {
      front: { type: frontType, value: frontValue },
      profile: { type: profileType, value: profileValue },
    },
    forceCalibration: false,
  };
}

// Apply settings to UI
function applySettingsToUI(settings) {
  // Training params
  roundsInput.value = settings.rounds;

  // Exercise order and enabled state
  const exerciseItems = Array.from(
    exerciseList.querySelectorAll(".exercise-item"),
  );

  // Reorder based on settings
  settings.exercises.forEach((exerciseId) => {
    const item = exerciseItems.find((el) => el.dataset.exercise === exerciseId);
    if (item) {
      exerciseList.appendChild(item);
    }
  });

  // Set checkbox states and per-exercise reps
  const repsPerExercise = settings.repsPerExercise || {};
  exerciseList.querySelectorAll(".exercise-item").forEach((item) => {
    const checkbox = item.querySelector('input[type="checkbox"]');
    const repsInput = item.querySelector(".exercise-reps-input");
    const exerciseId = item.dataset.exercise;

    if (checkbox) {
      checkbox.checked = settings.exercises.includes(exerciseId);
    }
    if (repsInput) {
      repsInput.value = repsPerExercise[exerciseId] || 10;
    }
  });

  // Camera settings
  const cam = settings.cameraSettings;

  if (cam.front.type === "physical") {
    document.querySelector(
      'input[name="front-type"][value="physical"]',
    ).checked = true;
    document.getElementById("front-index").value = cam.front.value;
    frontPhysicalInput.style.display = "block";
    frontIpInput.style.display = "none";
  } else {
    document.querySelector('input[name="front-type"][value="ip"]').checked =
      true;
    document.getElementById("front-url").value = cam.front.value;
    frontPhysicalInput.style.display = "none";
    frontIpInput.style.display = "block";
  }

  if (cam.profile.type === "physical") {
    document.querySelector(
      'input[name="profile-type"][value="physical"]',
    ).checked = true;
    document.getElementById("profile-index").value = cam.profile.value;
    profilePhysicalInput.style.display = "block";
    profileIpInput.style.display = "none";
  } else {
    document.querySelector('input[name="profile-type"][value="ip"]').checked =
      true;
    document.getElementById("profile-url").value = cam.profile.value;
    profilePhysicalInput.style.display = "none";
    profileIpInput.style.display = "block";
  }
}

// Validate camera settings
function validateCameraSettings(settings) {
  const cam = settings.cameraSettings;

  if (cam.front.type === "ip" && !cam.front.value) {
    alert("Podaj adres URL dla kamery frontalnej");
    return false;
  }

  if (cam.profile.type === "ip" && !cam.profile.value) {
    alert("Podaj adres URL dla kamery profilowej");
    return false;
  }

  if (
    cam.front.type === "physical" &&
    cam.profile.type === "physical" &&
    cam.front.value === cam.profile.value
  ) {
    alert("Nie możesz użyć tej samej kamery fizycznej dla obu widoków");
    return false;
  }

  if (settings.exercises.length === 0) {
    alert("Wybierz przynajmniej jedno ćwiczenie");
    return false;
  }

  return true;
}

// Check calibration status
function checkCalibrationStatus() {
  fetch("/api/calibration-status")
    .then((res) => res.json())
    .then((data) => {
      if (data.calibrated) {
        calibrationStatus.textContent = `✓ Skalibrowano: ${data.date}`;
        calibrationStatus.className = "calibration-status calibrated";
        if (calibrationDetail) {
          calibrationDetail.textContent = `Skalibrowano: ${data.date}`;
          calibrationDetail.className = "calibrated";
        }
      } else {
        calibrationStatus.textContent =
          "⚠ Brak kalibracji - zostanie wykonana automatycznie";
        calibrationStatus.className = "calibration-status not-calibrated";
        if (calibrationDetail) {
          calibrationDetail.textContent =
            "Brak kalibracji - zostanie wykonana przed treningiem";
          calibrationDetail.className = "not-calibrated";
        }
      }
    })
    .catch(() => {
      calibrationStatus.textContent = "";
    });
}

// Modal controls
function openModal() {
  settingsModal.classList.add("active");
  applySettingsToUI(loadSettings());
  checkCalibrationStatus();
}

function closeModal() {
  settingsModal.classList.remove("active");
}

// Start training
function startTraining(forceCalibration = false) {
  const settings = getSettingsFromUI();
  settings.forceCalibration = forceCalibration;

  if (!validateCameraSettings(settings)) return;

  saveSettings(settings);

  // Set session mode - will be determined by server based on calibration status
  localStorage.setItem("sessionMode", "unified");

  window.location.href = "/training";
}

// Drag and drop for exercise reordering
let draggedItem = null;

function initDragDrop() {
  const items = exerciseList.querySelectorAll(".exercise-item");

  items.forEach((item) => {
    item.addEventListener("dragstart", (e) => {
      draggedItem = item;
      item.classList.add("dragging");
      e.dataTransfer.effectAllowed = "move";
    });

    item.addEventListener("dragend", () => {
      item.classList.remove("dragging");
      draggedItem = null;
    });

    item.addEventListener("dragover", (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";

      if (draggedItem && draggedItem !== item) {
        const rect = item.getBoundingClientRect();
        const midY = rect.top + rect.height / 2;

        if (e.clientY < midY) {
          exerciseList.insertBefore(draggedItem, item);
        } else {
          exerciseList.insertBefore(draggedItem, item.nextSibling);
        }
      }
    });
  });
}

// Camera type toggle handlers
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

// Event listeners
startTrainingBtn.addEventListener("click", () => {
  const settings = loadSettings();
  applySettingsToUI(settings);
  if (validateCameraSettings(settings)) {
    saveSettings(settings);
    localStorage.setItem("sessionMode", "unified");
    window.location.href = "/training";
  }
});

historyBtn.addEventListener("click", () => {
  window.location.href = "/history";
});

settingsBtn.addEventListener("click", openModal);
modalClose.addEventListener("click", closeModal);
settingsModal.addEventListener("click", (e) => {
  if (e.target === settingsModal) closeModal();
});

saveSettingsBtn.addEventListener("click", () => {
  const settings = getSettingsFromUI();
  if (validateCameraSettings(settings)) {
    saveSettings(settings);
    closeModal();
    checkCalibrationStatus();
  }
});

// Keyboard support
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && settingsModal.classList.contains("active")) {
    closeModal();
  }
});

// Initialize
applySettingsToUI(loadSettings());
checkCalibrationStatus();
initDragDrop();
