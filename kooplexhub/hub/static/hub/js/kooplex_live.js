(function () {
  class KooplexLiveUpdates {
    constructor(endpoint) {
      this.endpoint = endpoint;
      this.socket = null;

      this.reconnectDelay = 1500;
      this.refreshDelay = 100;

      this.refreshTimers = new Map();
      this.refreshInProgress = new Set();
      this.refreshQueued = new Set();
    }

    connect() {
      if (!this.endpoint) return;

      this.socket = new WebSocket(this.endpoint);

      this.socket.addEventListener("open", () => {
        console.debug("Kooplex live connection opened");
      });

      this.socket.addEventListener("message", (event) => {
        this.handleMessage(event);
      });

      this.socket.addEventListener("close", () => {
        console.debug("Kooplex live connection closed; reconnecting");

        window.setTimeout(
          () => this.connect(),
          this.reconnectDelay
        );
      });

      this.socket.addEventListener("error", (event) => {
        console.error("Kooplex live WebSocket error", event);
      });
    }

    handleMessage(event) {
      let payload;

      try {
        payload = JSON.parse(event.data);
      } catch (error) {
        console.warn(
          "Ignoring invalid Kooplex live message",
          event.data,
          error
        );
        return;
      }

      const keys = Array.isArray(payload.keys)
        ? payload.keys
        : [];

      keys.forEach((key) => {
        this.scheduleRefresh(key);
      });
    }

    scheduleRefresh(key) {
      const existingTimer = this.refreshTimers.get(key);

      if (existingTimer) {
        window.clearTimeout(existingTimer);
      }

      const timer = window.setTimeout(() => {
        this.refreshTimers.delete(key);
        this.refreshKey(key);
      }, this.refreshDelay);

      this.refreshTimers.set(key, timer);
    }

    async refreshKey(key) {
      /*
       * If another refresh of the same logical key is running, remember
       * that one more refresh is needed when it finishes.
       */
      if (this.refreshInProgress.has(key)) {
        this.refreshQueued.add(key);
        return;
      }

      this.refreshInProgress.add(key);

      try {
        const selector =
          `[data-live-key="${CSS.escape(key)}"]`;

        /*
         * Make a stable snapshot. HTMX outerHTML swaps will replace the
         * original DOM elements while these requests are running.
         */
        const elements = Array.from(
          document.querySelectorAll(selector)
        );

        console.debug(
          `Refreshing live key ${key}:`,
          elements.length,
          "elements"
        );

        const requests = elements.map((element) => {
          /*
           * A previous swap may already have detached this element.
           */
          if (!element.isConnected) {
            return Promise.resolve();
          }

          const url = element.dataset.liveUrl;
          const swap =
            element.dataset.liveSwap || "outerHTML";

          if (!url) {
            console.warn(
              "Live element is missing data-live-url",
              element
            );
            return Promise.resolve();
          }

          /*
           * Do not destroy an active inline edit.
           */
          if (
            element.matches(":focus-within") ||
            element.dataset.liveDirty === "true"
          ) {
            element.dataset.liveStale = "true";
            return Promise.resolve();
          }

          return Promise.resolve(
            htmx.ajax("GET", url, {
              source: element,
              target: element,
              swap: swap,
            })
          ).catch((error) => {
            console.error(
              `Failed to refresh ${url}`,
              error
            );
          });
        });

        await Promise.allSettled(requests);
      } finally {
        this.refreshInProgress.delete(key);

        /*
         * A newer Kubernetes observation arrived while requests were
         * running. Refresh once more to obtain the latest state.
         */
        if (this.refreshQueued.delete(key)) {
          this.scheduleRefresh(key);
        }
      }
    }
  }

  window.KooplexLiveUpdates = KooplexLiveUpdates;

  document.addEventListener("DOMContentLoaded", () => {
    const configElement = document.getElementById(
      "kooplex-live-config"
    );

    if (!configElement) return;

    let config;

    try {
      config = JSON.parse(configElement.textContent);
    } catch (error) {
      console.error(
        "Invalid Kooplex live configuration",
        error
      );
      return;
    }

    if (!config.endpoint) return;

    window.kooplexLive = new KooplexLiveUpdates(
      config.endpoint
    );

    window.kooplexLive.connect();
  });
})();
