// Smart Guard Gmail Content Script
(function () {
  console.log("%c[Smart Guard Gmail Guard]: Active and observing Gmail emails...", "color: #38bdf8; font-weight: bold; font-size: 14px;");

  let scanTimer = null;

  // Observe Gmail's dynamic DOM changes
  const observer = new MutationObserver(() => {
    if (scanTimer) clearTimeout(scanTimer);
    scanTimer = setTimeout(scanOpenedEmailsInGmail, 300);
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true
  });

  // Initial check & periodic fallback
  setTimeout(scanOpenedEmailsInGmail, 500);
  setInterval(scanOpenedEmailsInGmail, 2500);

  // Scan opened email bodies in Gmail view
  function scanOpenedEmailsInGmail() {
    // Target only the primary email body container in Gmail (.a3s)
    const emailContainers = document.querySelectorAll(".a3s");
    if (!emailContainers.length) return;

    emailContainers.forEach(container => {
      // Prevent scanning nested inner elements or already processed containers
      if (container.dataset.smartGuardScanned === "true") return;

      const messageWrapper = container.closest(".adn, .gs, .h7") || container.parentElement;
      if (!messageWrapper) return;

      // Check if a banner is already injected for this email message
      if (messageWrapper.querySelector(".smart-guard-gmail-banner")) {
        container.dataset.smartGuardScanned = "true";
        return;
      }

      const bodyText = container.textContent ? container.textContent.trim() : "";
      if (!bodyText || bodyText.length < 5) return;

      container.dataset.smartGuardScanned = "true";

      // Extract subject line if available
      const subjectEl = document.querySelector("h1.hP, .hP, .ha");
      const subjectText = subjectEl ? subjectEl.textContent.trim() : "";
      const fullText = subjectText ? `Subject: ${subjectText}\n\n${bodyText}` : bodyText;

      console.log("[Smart Guard Gmail]: Scanning email message (Length: " + fullText.length + ")...");

      // Send to background service worker for ML classification
      chrome.runtime.sendMessage({
        action: "CHECK_TEXT",
        text: fullText,
        source_url: window.location.href
      }, (response) => {
        if (chrome.runtime.lastError || !response || !response.success) {
          console.warn("[Smart Guard Gmail]: Could not connect to API or server offline.");
          return;
        }

        const result = response.data;
        console.log("[Smart Guard Gmail]: Prediction Result:", result);

        // Inject exactly ONE single inline banner above the email
        injectInlineGmailBanner(container, result, fullText);

        if (result.is_spam && result.trigger_words && result.trigger_words.length > 0) {
          highlightTriggerWordsInContainer(container, result.trigger_words);
        }
      });
    });
  }

  // Inject a single Security Banner directly above the email body
  function injectInlineGmailBanner(emailContainer, result, fullText) {
    const parent = emailContainer.parentNode;
    if (!parent) return;

    const messageWrapper = emailContainer.closest(".adn, .gs, .h7") || parent;

    // Check if banner already exists anywhere in this message container
    const existing = messageWrapper.querySelector(".smart-guard-gmail-banner");
    if (existing) {
      existing.remove();
    }

    const isSpam = result.is_spam;
    const banner = document.createElement("div");
    banner.className = `smart-guard-gmail-banner ${isSpam ? "sg-spam-banner" : "sg-ham-banner"}`;

    const icon = isSpam ? "🚨" : "🛡️";
    const titleText = isSpam
      ? `Smart Guard Alert: SPAM DETECTED (${result.risk_level} RISK)`
      : `Smart Guard: LEGITIMATE EMAIL (${result.risk_level} RISK)`;
    const confidenceText = `Model Confidence: ${result.confidence}%`;

    let tagsHtml = "";
    if (isSpam && result.trigger_words && result.trigger_words.length > 0) {
      tagsHtml = `
        <div class="sg-banner-tags">
          <span style="font-size: 11px; font-weight:700;">Suspicious Terms:</span>
          ${result.trigger_words.map(w => `<span class="sg-banner-tag">${w}</span>`).join("")}
        </div>
      `;
    }

    banner.innerHTML = `
      <div class="sg-banner-left">
        <div class="sg-banner-icon">${icon}</div>
        <div>
          <div class="sg-banner-title">${titleText}</div>
          <div class="sg-banner-sub">${confidenceText}</div>
          ${tagsHtml}
        </div>
      </div>
      <button class="sg-banner-action" id="reportErrorBtn">Report Error</button>
    `;

    banner.querySelector("#reportErrorBtn").addEventListener("click", () => {
      const actual = isSpam ? "ham" : "spam";
      const note = prompt(`Report classification correction for this Gmail message.\nMark as (${actual.toUpperCase()})? Optional note:`);
      if (note !== null) {
        chrome.storage.local.get(["apiUrl"], async (res) => {
          const apiUrl = res.apiUrl || "http://127.0.0.1:8000";
          try {
            await fetch(`${apiUrl}/api/v1/feedback`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                text: fullText,
                predicted: result.prediction,
                actual: actual,
                user_note: note
              })
            });
            alert("Feedback saved! Thank you for helping improve the model.");
          } catch (e) {
            alert("Could not connect to backend server.");
          }
        });
      }
    });

    parent.insertBefore(banner, emailContainer);
  }

  // Highlight suspicious words inside email body
  function highlightTriggerWordsInContainer(container, triggerWords) {
    if (!triggerWords || !triggerWords.length) return;

    triggerWords.forEach(word => {
      if (word.length < 3) return;
      const regex = new RegExp(`\\b(${word})\\b`, "gi");

      const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null, false);
      const textNodes = [];
      while (walker.nextNode()) {
        textNodes.push(walker.currentNode);
      }

      textNodes.forEach(node => {
        if (node.parentNode && node.parentNode.tagName !== "MARK" && regex.test(node.nodeValue)) {
          const span = document.createElement("span");
          span.innerHTML = node.nodeValue.replace(regex, '<mark class="smart-guard-trigger">$1</mark>');
          node.parentNode.replaceChild(span, node);
        }
      });
    });
  }
})();
