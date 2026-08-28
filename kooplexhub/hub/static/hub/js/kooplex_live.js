(function () {
  class KooplexLiveUpdates {
    constructor(config) {
      this.config = config || {};

      this.socket = null;
      this.reconnectTimer = null;

      this.reconnectDelay =
        this.config.reconnectInitialMs || 500;

      this.reconnectInitial =
        this.config.reconnectInitialMs || 500;

      this.reconnectMax =
        this.config.reconnectMaxMs || 10000;

      this.refreshDelay =
        this.config.refreshDebounceMs || 300;

      this.refreshTimers = new Map();
      this.refreshInProgress = new Set();
      this.refreshQueued = new Set();
    }

    get endpoint() {
      const path = this.config.path;

      if (!path) {
        return null;
      }

      /*
       * Allow a complete ws:// or wss:// URL,
       * but normally config only contains a path.
       */
      if (
        path.startsWith("ws://") ||
        path.startsWith("wss://")
      ) {
        return path;
      }

      const protocol =
        window.location.protocol === "https:"
          ? "wss:"
          : "ws:";

      return (
        `${protocol}//${window.location.host}` +
        path
      );
    }

    connect() {
      const endpoint = this.endpoint;

      if (!endpoint) {
        return;
      }

      /*
       * Avoid creating a second connection while
       * one is already open or connecting.
       */
      if (
        this.socket &&
        (
          this.socket.readyState === WebSocket.OPEN ||
          this.socket.readyState === WebSocket.CONNECTING
        )
      ) {
        return;
      }

      console.debug(
        "Opening Kooplex live connection",
        endpoint
      );

      this.socket = new WebSocket(endpoint);

      this.socket.addEventListener(
        "open",
        () => {
          console.debug(
            "Kooplex live connection opened"
          );

          this.reconnectDelay =
            this.reconnectInitial;
        }
      );

      this.socket.addEventListener(
        "message",
        (event) => {
          this.handleMessage(event);
        }
      );

      this.socket.addEventListener(
        "close",
        () => {
          console.debug(
            "Kooplex live connection closed"
          );

          this.socket = null;
          this.scheduleReconnect();
        }
      );

      this.socket.addEventListener(
        "error",
        (event) => {
          console.error(
            "Kooplex live WebSocket error",
            event
          );
        }
      );
    }

    scheduleReconnect() {
      if (this.reconnectTimer) {
        return;
      }

      const delay = this.reconnectDelay;

      this.reconnectTimer =
        window.setTimeout(
          () => {
            this.reconnectTimer = null;
            this.connect();
          },
          delay
        );

      this.reconnectDelay = Math.min(
        this.reconnectDelay * 2,
        this.reconnectMax
      );
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

      console.debug(
        "Kooplex live event",
        payload
      );

      /*
       * Messages/toasts are handled by
       * kooplex_ui.js.
       */
      if (payload.notification) {
        document.body.dispatchEvent(
          new CustomEvent(
            "kooplex-toast",
            {
              detail: payload.notification,
            }
          )
        );
      }

      const keys = Array.isArray(payload.keys)
        ? payload.keys
        : [];

      keys.forEach((key) => {
        this.scheduleRefresh(key);
      });
    }

    scheduleRefresh(key) {
      const existingTimer =
        this.refreshTimers.get(key);

      if (existingTimer) {
        window.clearTimeout(existingTimer);
      }

      const timer =
        window.setTimeout(
          () => {
            this.refreshTimers.delete(key);
            this.refreshKey(key);
          },
          this.refreshDelay
        );

      this.refreshTimers.set(key, timer);
    }

    cancelDescendantRefreshes(element) {
      element
        .querySelectorAll("[data-live-key]")
        .forEach((child) => {
          const childKey = child.dataset.liveKey;
    
          if (!childKey) {
            return;
          }
    
          const timer =
            this.refreshTimers.get(childKey);
    
          if (timer) {
            window.clearTimeout(timer);
            this.refreshTimers.delete(childKey);
          }
    
          this.refreshQueued.delete(childKey);
        });
    }

    async refreshKey(key) {
      if (
        this.refreshInProgress.has(key)
      ) {
        this.refreshQueued.add(key);
        return;
      }

      this.refreshInProgress.add(key);

      try {
        const selector =
          `[data-live-key="${CSS.escape(key)}"]`;

        const elements = Array.from(
          document.querySelectorAll(selector)
        );

        /*
         * This is the important page scoping:
         * if the current page does not contain a
         * matching component, there is no request.
         */
        if (!elements.length) {
          return;
        }

        console.debug(
          `Refreshing live key ${key}:`,
          elements.length,
          "elements"
        );

        const requests = elements.map(
          (element) => {
            if (!element.isConnected) {
              return Promise.resolve();
            }

            const url =
              element.dataset.liveUrl;

            const swap =
              element.dataset.liveSwap ||
              "outerHTML";

            if (!url) {
              console.warn(
                "Live element is missing data-live-url",
                element
              );

              return Promise.resolve();
            }

            this.cancelDescendantRefreshes(
              element
            );

            /*
             * Do not destroy active editing.
             */
            if (
              element.matches(":focus-within") ||
              element.dataset.liveDirty ===
                "true"
            ) {
              element.dataset.liveStale =
                "true";

              return Promise.resolve();
            }

            return Promise.resolve(
              htmx.ajax(
                "GET",
                url,
                {
                  source: element,
                  target: element,
                  swap: swap,
                }
              )
            ).catch(
              (error) => {
                console.error(
                  `Failed to refresh ${url}`,
                  error
                );
              }
            );
          }
        );

        await Promise.allSettled(
          requests
        );
      } finally {
        this.refreshInProgress.delete(key);

        if (
          this.refreshQueued.delete(key)
        ) {
          this.scheduleRefresh(key);
        }
      }
    }
  }

  window.KooplexLiveUpdates =
    KooplexLiveUpdates;

  document.addEventListener(
    "DOMContentLoaded",
    () => {
      const configElement =
        document.getElementById(
          "kooplex-live-config"
        );

      if (!configElement) {
        return;
      }

      let config;

      try {
        config = JSON.parse(
          configElement.textContent
        );
      } catch (error) {
        console.error(
          "Invalid Kooplex live configuration",
          error
        );

        return;
      }

      window.kooplexLive =
        new KooplexLiveUpdates(config);

      window.kooplexLive.connect();
    }
  );
})();


