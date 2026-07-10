(function () {
  class KooplexLiveUpdates {
    constructor(endpoint) {
      this.endpoint = endpoint;
      this.socket = null;
      this.reconnectDelay = 1500;
    }

    connect() {
      if (!this.endpoint) return;

      this.socket = new WebSocket(this.endpoint);

      this.socket.addEventListener("message", (event) => {
        this.handleMessage(event);
      });

      this.socket.addEventListener("close", () => {
        setTimeout(() => this.connect(), this.reconnectDelay);
      });
    }

    handleMessage(event) {
      let payload;

      try {
        payload = JSON.parse(event.data);
      } catch {
        return;
      }

      const keys = payload.keys || [];

      keys.forEach((key) => {
        this.refreshKey(key);
      });
    }

    refreshKey(key) {
      const selector = `[data-live-key="${CSS.escape(key)}"]`;

      document.querySelectorAll(selector).forEach((el) => {
        const url = el.dataset.liveUrl;
        const swap = el.dataset.liveSwap || "outerHTML";

        if (!url) return;

        if (el.matches(":focus-within") || el.dataset.liveDirty === "true") {
          el.dataset.liveStale = "true";
          return;
        }

        htmx.ajax("GET", url, {
          target: el,
          swap,
        });
      });
    }
  }

  window.KooplexLiveUpdates = KooplexLiveUpdates;

  document.addEventListener("DOMContentLoaded", () => {
    const configEl = document.getElementById("kooplex-live-config");
    if (!configEl) return;

    const config = JSON.parse(configEl.textContent);

    if (config.endpoint) {
      window.kooplexLive = new KooplexLiveUpdates(config.endpoint);
      window.kooplexLive.connect();
    }
  });
})();
