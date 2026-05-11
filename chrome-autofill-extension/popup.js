/**
 * Bewerbung AutoFill – Popup Script
 */
document.addEventListener("DOMContentLoaded", () => {
  const fillBtn = document.getElementById("fillBtn");
  const statusEl = document.getElementById("status");
  const statusIcon = statusEl.querySelector(".status-icon");
  const statusText = statusEl.querySelector(".status-text");
  const resultsEl = document.getElementById("results");
  const resultList = document.getElementById("resultList");

  fillBtn.addEventListener("click", async () => {
    // Button-Loading-State
    fillBtn.disabled = true;
    fillBtn.querySelector(".btn-text").textContent = "Wird ausgefüllt…";
    fillBtn.querySelector(".btn-icon").textContent = "⏳";

    // Status und Ergebnisse zurücksetzen
    statusEl.classList.add("hidden");
    statusEl.classList.remove("error");
    resultsEl.classList.add("hidden");
    resultList.innerHTML = "";

    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

      if (!tab || !tab.id) {
        showError("Kein aktiver Tab gefunden.");
        return;
      }

      // Content Script injizieren (falls noch nicht aktiv)
      try {
        await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          files: ["content.js"],
        });
      } catch (e) {
        // Script möglicherweise bereits geladen – kein Fehler
      }

      // Nachricht an Content Script senden
      const response = await chrome.tabs.sendMessage(tab.id, { action: "fillForm" });

      if (response && response.filledCount > 0) {
        showSuccess(`${response.filledCount} Feld${response.filledCount > 1 ? "er" : ""} ausgefüllt!`);

        // Ergebnisse anzeigen
        if (response.results && response.results.length > 0) {
          response.results.forEach((r) => {
            const li = document.createElement("li");
            li.innerHTML = `<span class="field-name">${escapeHtml(r.field)}</span><span class="field-value">${escapeHtml(r.value)}</span>`;
            resultList.appendChild(li);
          });
          resultsEl.classList.remove("hidden");
        }
      } else {
        showError("Keine passenden Felder gefunden.");
      }
    } catch (err) {
      console.error("AutoFill Fehler:", err);
      showError("Fehler beim Ausfüllen. Seite neu laden und erneut versuchen.");
    } finally {
      // Button zurücksetzen
      fillBtn.disabled = false;
      fillBtn.querySelector(".btn-text").textContent = "Formular ausfüllen";
      fillBtn.querySelector(".btn-icon").textContent = "⚡";
    }
  });

  function showSuccess(msg) {
    statusEl.classList.remove("hidden", "error");
    statusIcon.textContent = "✅";
    statusText.textContent = msg;
  }

  function showError(msg) {
    statusEl.classList.remove("hidden");
    statusEl.classList.add("error");
    statusIcon.textContent = "❌";
    statusText.textContent = msg;
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }
});
