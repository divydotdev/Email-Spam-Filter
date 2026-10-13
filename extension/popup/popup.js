document.addEventListener("DOMContentLoaded", () => {
  // UI Elements
  const statusPill = document.getElementById("statusPill");
  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabContents = document.querySelectorAll(".tab-content");

  const textInput = document.getElementById("textInput");
  const scanBtn = document.getElementById("scanBtn");
  const btnText = scanBtn.querySelector(".btn-text");
  const spinner = scanBtn.querySelector(".spinner");

  const resultCard = document.getElementById("resultCard");
  const resultBadge = document.getElementById("resultBadge");
  const riskBadge = document.getElementById("riskBadge");
  const confidenceVal = document.getElementById("confidenceVal");
  const triggerSection = document.getElementById("triggerSection");
  const triggerTags = document.getElementById("triggerTags");
  const reportFeedbackBtn = document.getElementById("reportFeedbackBtn");

  const scannedTotal = document.getElementById("scannedTotal");
  const spamTotal = document.getElementById("spamTotal");
  const feedbackTotal = document.getElementById("feedbackTotal");

  const historyList = document.getElementById("historyList");
  const clearHistoryBtn = document.getElementById("clearHistoryBtn");

  const apiUrlInput = document.getElementById("apiUrlInput");
  const sensitivityRange = document.getElementById("sensitivityRange");
  const sensitivityVal = document.getElementById("sensitivityVal");
  const saveSettingsBtn = document.getElementById("saveSettingsBtn");

  let lastAnalysisResult = null;

  // Initialize popup
  initPopup();

  function initPopup() {
    loadSettings();
    checkBackendHealth();
    loadStats();
    loadHistory();
    setupEventListeners();
  }

  // Load Settings from Chrome Storage
  function loadSettings() {
    chrome.storage.local.get(["apiUrl", "sensitivity"], (res) => {
      if (res.apiUrl) apiUrlInput.value = res.apiUrl;
      if (res.sensitivity) {
        sensitivityRange.value = res.sensitivity;
        sensitivityVal.textContent = parseFloat(res.sensitivity).toFixed(2);
      }
    });
  }

  // Check Backend Server Health
  async function checkBackendHealth() {
    const apiUrl = apiUrlInput.value.trim() || "http://127.0.0.1:8000";
    try {
      const res = await fetch(`${apiUrl}/api/v1/health`);
      if (res.ok) {
        const data = await res.json();
        statusPill.className = "status-pill online";
        statusPill.querySelector(".status-text").textContent = data.model_loaded ? "Online" : "Model Loading";
      } else {
        throw new Error("Offline");
      }
    } catch (e) {
      statusPill.className = "status-pill offline";
      statusPill.querySelector(".status-text").textContent = "API Offline";
    }
  }

  // Load Stats from storage and API
  async function loadStats() {
    chrome.storage.local.get(["scannedTotal", "spamTotal"], (res) => {
      scannedTotal.textContent = res.scannedTotal || 0;
      spamTotal.textContent = res.spamTotal || 0;
    });

    const apiUrl = apiUrlInput.value.trim() || "http://127.0.0.1:8000";
    try {
      const res = await fetch(`${apiUrl}/api/v1/stats`);
      if (res.ok) {
        const stats = await res.json();
        feedbackTotal.textContent = stats.total_feedback_reports || 0;
      }
    } catch (e) {
      feedbackTotal.textContent = "0";
    }
  }

  // Setup UI event listeners
  function setupEventListeners() {
    // Tab switching
    tabBtns.forEach(btn => {
      btn.addEventListener("click", () => {
        tabBtns.forEach(b => b.classList.remove("active"));
        tabContents.forEach(c => c.classList.remove("active"));
        btn.classList.add("active");
        document.getElementById(btn.dataset.tab).classList.add("active");
        if (btn.dataset.tab === "tab-history") loadHistory();
      });
    });

    // Sensitivity slider display
    sensitivityRange.addEventListener("input", (e) => {
      sensitivityVal.textContent = parseFloat(e.target.value).toFixed(2);
    });

    // Save Settings
    saveSettingsBtn.addEventListener("click", () => {
      const newUrl = apiUrlInput.value.trim();
      const newSens = parseFloat(sensitivityRange.value);
      chrome.storage.local.set({ apiUrl: newUrl, sensitivity: newSens }, () => {
        alert("Settings saved successfully!");
        checkBackendHealth();
      });
    });

    // Scan Content Click
    scanBtn.addEventListener("click", handleScan);

    // Report Error Click
    reportFeedbackBtn.addEventListener("click", handleReportFeedback);

    // Clear History Click
    clearHistoryBtn.addEventListener("click", () => {
      chrome.storage.local.set({ recentScans: [] }, () => {
        loadHistory();
      });
    });
  }

  // Perform Scan Request
  async function handleScan() {
    const text = textInput.value.trim();
    if (!text) {
      alert("Please enter a message to scan.");
      return;
    }

    setLoading(true);
    const apiUrl = apiUrlInput.value.trim() || "http://127.0.0.1:8000";
    const threshold = parseFloat(sensitivityRange.value) || 0.5;

    try {
      const response = await fetch(`${apiUrl}/api/v1/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: text,
          threshold: threshold
        })
      });

      if (!response.ok) throw new Error(`Server returned HTTP ${response.status}`);

      const data = await response.json();
      data.text = text;
      lastAnalysisResult = data;
      renderResult(data);

      // Save scan to Chrome local storage
      updateLocalStorageStats(data);
    } catch (err) {
      alert(`Error connecting to backend: ${err.message}. Make sure FastAPI is running!`);
    } finally {
      setLoading(false);
    }
  }

  // Render scan result card
  function renderResult(data) {
    resultCard.classList.remove("hidden");
    const isSpam = data.is_spam;

    if (isSpam) {
      resultCard.className = "card result-card is-spam";
      resultBadge.textContent = "🚨 SPAM DETECTED";
    } else {
      resultCard.className = "card result-card";
      resultBadge.textContent = "✅ HAM / LEGITIMATE";
    }

    riskBadge.textContent = `${data.risk_level} RISK`;
    confidenceVal.textContent = `${data.confidence}%`;

    // Render trigger tags
    if (data.trigger_words && data.trigger_words.length > 0) {
      triggerSection.classList.remove("hidden");
      triggerTags.innerHTML = data.trigger_words
        .map(word => `<span class="trigger-tag">${word}</span>`)
        .join("");
    } else {
      triggerSection.classList.add("hidden");
    }

    loadStats();
  }

  // Save to local storage
  async function updateLocalStorageStats(result) {
    chrome.storage.local.get(["scannedTotal", "spamTotal", "recentScans"], (res) => {
      const scanned = (res.scannedTotal || 0) + 1;
      const spam = (res.spamTotal || 0) + (result.is_spam ? 1 : 0);
      const newScan = {
        id: Date.now(),
        text: result.text,
        prediction: result.prediction,
        confidence: result.confidence,
        risk_level: result.risk_level,
        trigger_words: result.trigger_words,
        timestamp: new Date().toLocaleTimeString()
      };
      const history = [newScan, ...(res.recentScans || [])].slice(0, 20);

      chrome.storage.local.set({
        scannedTotal: scanned,
        spamTotal: spam,
        recentScans: history
      }, () => {
        loadStats();
      });
    });
  }

  // Load Recent Scans History
  function loadHistory() {
    chrome.storage.local.get(["recentScans"], (res) => {
      const scans = res.recentScans || [];
      if (scans.length === 0) {
        historyList.innerHTML = `<div class="empty-state">No scans recorded yet.</div>`;
        return;
      }

      historyList.innerHTML = scans.map(item => `
        <div class="history-item">
          <div class="history-top">
            <span style="font-weight: 700; color: ${item.prediction === 'spam' ? '#ef4444' : '#10b981'}">
              ${item.prediction.toUpperCase()} (${item.confidence}%)
            </span>
            <span class="history-time">${item.timestamp}</span>
          </div>
          <div class="history-text" title="${escapeHtml(item.text)}">${escapeHtml(item.text)}</div>
        </div>
      `).join("");
    });
  }

  // Report Incorrect Result
  async function handleReportFeedback() {
    if (!lastAnalysisResult) return;
    const actual = lastAnalysisResult.prediction === "spam" ? "ham" : "spam";
    const note = prompt(`Reporting incorrect classification for:\n"${lastAnalysisResult.text.substring(0, 60)}..."\n\nCorrect label should be (${actual.toUpperCase()})? Enter optional note:`);

    if (note !== null) {
      const apiUrl = apiUrlInput.value.trim() || "http://127.0.0.1:8000";
      try {
        const res = await fetch(`${apiUrl}/api/v1/feedback`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text: lastAnalysisResult.text,
            predicted: lastAnalysisResult.prediction,
            actual: actual,
            user_note: note
          })
        });

        if (res.ok) {
          alert("Thank you! Feedback recorded successfully.");
          loadStats();
        }
      } catch (e) {
        alert("Failed to send feedback to backend.");
      }
    }
  }

  function setLoading(isLoading) {
    if (isLoading) {
      btnText.textContent = "Analyzing...";
      spinner.classList.remove("hidden");
      scanBtn.disabled = true;
    } else {
      btnText.textContent = "Scan Content";
      spinner.classList.add("hidden");
      scanBtn.disabled = false;
    }
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
});
