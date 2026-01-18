const sessionsList = document.getElementById("sessions-list");
const emptyState = document.getElementById("empty-state");
const detailModal = document.getElementById("detail-modal");
const modalContent = document.getElementById("modal-content");
const modalClose = document.getElementById("modal-close");
const closeDetailBtn = document.getElementById("close-detail-btn");
const deleteBtn = document.getElementById("delete-btn");
const dateFromInput = document.getElementById("date-from");
const dateToInput = document.getElementById("date-to");
const sortOrderSelect = document.getElementById("sort-order");
const clearFiltersBtn = document.getElementById("clear-filters");

let currentSessionId = null;

const ERROR_NAMES = {
  trunk_tilted: "Przechylenie tułowia",
  arm_not_vertical: "Ramię nie pionowo",
  both_arms_flexed: "Obie ręce ugięte",
  consecutive_same_side: "Kolejne powtórzenia tą samą ręką",
  arms_not_synchronized: "Niesynchroniczne ruchy rąk",
};

function formatDate(isoString) {
  const date = new Date(isoString);
  return date.toLocaleDateString("pl-PL", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function formatTime(isoString) {
  const date = new Date(isoString);
  return date.toLocaleTimeString("pl-PL", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDuration(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins === 0) return `${secs}s`;
  return `${mins}m ${secs}s`;
}

function formatImprovement(value) {
  if (value === null || value === undefined) return null;
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

function getImprovementClass(value, lowerIsBetter = false) {
  if (value === null || value === undefined) return "neutral";
  if (lowerIsBetter) {
    return value >= 0 ? "positive" : "negative";
  }
  return value >= 0 ? "positive" : "negative";
}

async function loadSessions() {
  sessionsList.innerHTML = '<div class="loading">Ładowanie...</div>';

  const params = new URLSearchParams();
  params.set("sort", sortOrderSelect.value);
  if (dateFromInput.value) params.set("dateFrom", dateFromInput.value);
  if (dateToInput.value) params.set("dateTo", dateToInput.value);

  try {
    const response = await fetch(`/api/training-history?${params}`);
    const sessions = await response.json();

    if (sessions.length === 0) {
      sessionsList.style.display = "none";
      emptyState.style.display = "block";
      return;
    }

    sessionsList.style.display = "flex";
    emptyState.style.display = "none";

    sessionsList.innerHTML = sessions
      .map(
        (session) => `
      <div class="session-card" data-id="${session.id}">
        <div class="session-header">
          <div>
            <div class="session-date">${formatDate(session.timestamp)}</div>
            <div class="session-time">${formatTime(session.timestamp)} • ${formatDuration(session.duration_seconds)}</div>
          </div>
          <div class="session-improvements">
            ${
              session.overall_reps_improvement !== null
                ? `
              <span class="improvement-badge ${getImprovementClass(session.overall_reps_improvement)}">
                Powt. ${formatImprovement(session.overall_reps_improvement)}
              </span>
            `
                : ""
            }
            ${
              session.overall_errors_improvement !== null
                ? `
              <span class="improvement-badge ${getImprovementClass(session.overall_errors_improvement, true)}">
                Błędy ${formatImprovement(session.overall_errors_improvement)}
              </span>
            `
                : ""
            }
          </div>
        </div>
        <div class="session-stats">
          <div class="stat-item">
            <span class="stat-value">${session.total_reps}</span>
            <span class="stat-label">powtórzeń</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">${session.total_errors}</span>
            <span class="stat-label">błędów</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">${session.rounds}</span>
            <span class="stat-label">rund</span>
          </div>
        </div>
      </div>
    `,
      )
      .join("");

    document.querySelectorAll(".session-card").forEach((card) => {
      card.addEventListener("click", () =>
        openSessionDetail(parseInt(card.dataset.id)),
      );
    });
  } catch (error) {
    console.error("Error loading sessions:", error);
    sessionsList.innerHTML = '<div class="loading">Błąd ładowania danych</div>';
  }
}

async function openSessionDetail(sessionId) {
  currentSessionId = sessionId;

  try {
    const response = await fetch(`/api/training-history/${sessionId}`);
    const session = await response.json();

    if (session.error) {
      alert("Nie znaleziono treningu");
      return;
    }

    modalContent.innerHTML = `
      <div class="detail-section">
        <h3>📅 Informacje ogólne</h3>
        <div class="detail-grid">
          <div class="detail-stat">
            <div class="value">${formatDate(session.timestamp)}</div>
            <div class="label">Data</div>
          </div>
          <div class="detail-stat">
            <div class="value">${formatTime(session.timestamp)}</div>
            <div class="label">Godzina</div>
          </div>
          <div class="detail-stat">
            <div class="value">${formatDuration(session.duration_seconds)}</div>
            <div class="label">Czas trwania</div>
          </div>
          <div class="detail-stat">
            <div class="value">${session.rounds}</div>
            <div class="label">Rund</div>
          </div>
        </div>
      </div>

      <div class="detail-section">
        <h3>📊 Podsumowanie</h3>
        <div class="detail-grid">
          <div class="detail-stat">
            <div class="value">${session.total_reps}</div>
            <div class="label">Powtórzeń</div>
          </div>
          <div class="detail-stat">
            <div class="value">${session.total_errors}</div>
            <div class="label">Błędów</div>
          </div>
          ${
            session.overall_reps_improvement !== null
              ? `
            <div class="detail-stat">
              <div class="value" style="color: ${session.overall_reps_improvement >= 0 ? "var(--secondary)" : "var(--bad)"}">
                ${formatImprovement(session.overall_reps_improvement)}
              </div>
              <div class="label">Poprawa powt.</div>
            </div>
          `
              : ""
          }
          ${
            session.overall_errors_improvement !== null
              ? `
            <div class="detail-stat">
              <div class="value" style="color: ${session.overall_errors_improvement >= 0 ? "var(--secondary)" : "var(--bad)"}">
                ${formatImprovement(session.overall_errors_improvement)}
              </div>
              <div class="label">Poprawa błędów</div>
            </div>
          `
              : ""
          }
        </div>
      </div>

      <div class="detail-section">
        <h3>🏋️ Ćwiczenia</h3>
        ${session.exercise_results
          .map(
            (ex) => `
          <div class="exercise-detail">
            <div class="exercise-detail-header">
              <span class="exercise-detail-name">${ex.exercise_name}</span>
              <div class="exercise-detail-stats">
                <span class="reps">${ex.reps} powt.</span>
                <span class="errors">${ex.errors} błędów</span>
                ${
                  ex.reps_improvement !== null
                    ? `
                  <span style="color: ${ex.reps_improvement >= 0 ? "var(--secondary)" : "var(--bad)"}">
                    (${formatImprovement(ex.reps_improvement)})
                  </span>
                `
                    : ""
                }
              </div>
            </div>
            <div class="error-list">
              ${
                Object.keys(ex.error_details).length > 0
                  ? Object.entries(ex.error_details)
                      .map(
                        ([errorType, count]) => `
                  <div class="error-item">
                    <span class="error-name">${ERROR_NAMES[errorType] || errorType}</span>
                    <span class="error-count">×${count}</span>
                  </div>
                `,
                      )
                      .join("")
                  : '<div class="no-errors">✓ Brak błędów</div>'
              }
            </div>
          </div>
        `,
          )
          .join("")}
      </div>
    `;

    detailModal.classList.add("active");
  } catch (error) {
    console.error("Error loading session detail:", error);
    alert("Błąd ładowania szczegółów");
  }
}

function closeModal() {
  detailModal.classList.remove("active");
  currentSessionId = null;
}

async function deleteSession() {
  if (!currentSessionId) return;

  if (!confirm("Czy na pewno chcesz usunąć ten trening?")) return;

  try {
    const response = await fetch(`/api/training-history/${currentSessionId}`, {
      method: "DELETE",
    });

    if (response.ok) {
      closeModal();
      loadSessions();
    } else {
      alert("Błąd usuwania treningu");
    }
  } catch (error) {
    console.error("Error deleting session:", error);
    alert("Błąd usuwania treningu");
  }
}

modalClose.addEventListener("click", closeModal);
closeDetailBtn.addEventListener("click", closeModal);
deleteBtn.addEventListener("click", deleteSession);

detailModal.addEventListener("click", (e) => {
  if (e.target === detailModal) closeModal();
});

dateFromInput.addEventListener("change", loadSessions);
dateToInput.addEventListener("change", loadSessions);
sortOrderSelect.addEventListener("change", loadSessions);

clearFiltersBtn.addEventListener("click", () => {
  dateFromInput.value = "";
  dateToInput.value = "";
  sortOrderSelect.value = "desc";
  loadSessions();
});

loadSessions();
