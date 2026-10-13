const DEFAULT_API_URL = "http://127.0.0.1:8000";

// Register context menu on install
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "check-smart-guard",
    title: "🛡️ Scan selection with Smart Guard",
    contexts: ["selection"]
  });

  // Initialize storage defaults
  chrome.storage.local.get(["apiUrl", "sensitivity", "scannedTotal", "spamTotal", "recentScans"], (res) => {
    if (!res.apiUrl) chrome.storage.local.set({ apiUrl: DEFAULT_API_URL });
    if (!res.sensitivity) chrome.storage.local.set({ sensitivity: 0.5 });
    if (res.scannedTotal === undefined) chrome.storage.local.set({ scannedTotal: 0 });
    if (res.spamTotal === undefined) chrome.storage.local.set({ spamTotal: 0 });
    if (!res.recentScans) chrome.storage.local.set({ recentScans: [] });
  });
});

// Handle Context Menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === "check-smart-guard" && info.selectionText) {
    const selectedText = info.selectionText.trim();
    if (!selectedText) return;

    try {
      const storage = await chrome.storage.local.get(["apiUrl", "sensitivity"]);
      const apiUrl = storage.apiUrl || DEFAULT_API_URL;
      const threshold = storage.sensitivity || 0.5;

      const response = await fetch(`${apiUrl}/api/v1/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: selectedText,
          source_url: tab ? tab.url : "",
          threshold: threshold
        })
      });

      if (!response.ok) {
        throw new Error(`API returned status ${response.status}`);
      }

      const result = await response.json();
      updateScanStats(result);

      // Show Browser Notification
      const isSpam = result.is_spam;
      const iconUrl = chrome.runtime.getURL("assets/icon128.png");
      const title = isSpam
        ? `🚨 SPAM DETECTED (${result.risk_level})`
        : `✅ LEGITIMATE CONTENT (${result.risk_level})`;

      const triggerText = result.trigger_words.length > 0
        ? `\nSuspicious terms: ${result.trigger_words.join(", ")}`
        : "";

      const message = `Confidence: ${result.confidence}%\nText: "${selectedText.substring(0, 60)}..."${triggerText}`;

      chrome.notifications.create({
        type: "basic",
        iconUrl: iconUrl,
        title: title,
        message: message,
        priority: 2
      });

      // Send result back to content script for visual highlighting if active
      if (tab && tab.id) {
        chrome.tabs.sendMessage(tab.id, {
          action: "HIGHLIGHT_RESULT",
          result: result,
          selectedText: selectedText
        }).catch(() => {}); // Ignore if content script isn't loaded on page
      }

    } catch (err) {
      console.error("[Smart Guard SW Error]:", err);
      chrome.notifications.create({
        type: "basic",
        iconUrl: chrome.runtime.getURL("assets/icon128.png"),
        title: "🛡️ Smart Guard Error",
        message: `Could not connect to API server at ${DEFAULT_API_URL}. Please ensure backend is running.`,
        priority: 1
      });
    }
  }
});

// Helper to update scan stats in storage
async function updateScanStats(result) {
  const data = await chrome.storage.local.get(["scannedTotal", "spamTotal", "recentScans"]);
  const scannedTotal = (data.scannedTotal || 0) + 1;
  const spamTotal = (data.spamTotal || 0) + (result.is_spam ? 1 : 0);

  const newScan = {
    id: Date.now(),
    text: result.text || "",
    prediction: result.prediction,
    confidence: result.confidence,
    risk_level: result.risk_level,
    trigger_words: result.trigger_words,
    timestamp: new Date().toLocaleTimeString()
  };

  const recentScans = [newScan, ...(data.recentScans || [])].slice(0, 20);

  await chrome.storage.local.set({
    scannedTotal,
    spamTotal,
    recentScans
  });
}

// Handle runtime messages from Popup or Content Script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "CHECK_TEXT") {
    chrome.storage.local.get(["apiUrl", "sensitivity"], async (storage) => {
      const apiUrl = storage.apiUrl || DEFAULT_API_URL;
      const threshold = storage.sensitivity || 0.5;

      try {
        const response = await fetch(`${apiUrl}/api/v1/predict`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text: request.text,
            source_url: request.source_url || "",
            threshold: threshold
          })
        });

        if (!response.ok) {
          sendResponse({ success: false, error: `API status ${response.status}` });
          return;
        }

        const result = await response.json();
        result.text = request.text;
        await updateScanStats(result);
        sendResponse({ success: true, data: result });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    });
    return true; // async sendResponse
  }

  if (request.action === "GET_HEALTH") {
    chrome.storage.local.get(["apiUrl"], async (storage) => {
      const apiUrl = storage.apiUrl || DEFAULT_API_URL;
      try {
        const response = await fetch(`${apiUrl}/api/v1/health`);
        const data = await response.json();
        sendResponse({ success: true, data });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    });
    return true;
  }
});
