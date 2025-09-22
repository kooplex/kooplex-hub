// fetchlogs.js
// Container logs Modal Logic
class FetchLogs {
  constructor(opts = {}) {
    this.endpoint = opts.endpoint || null;
    this.logSelector = opts.logSelector || '#container-log';
    this.progressSelector = opts.progressSelector || '.progress';

    this.$log = $(this.logSelector);
    this.$progress = $(this.progressSelector);

    if (this.endpoint) {
    this.wss = new ManagedWebSocket(this.endpoint, {
      onMessage: (msg) => this.onMessage(msg),
    });
    } else {
      console.error("option endpoint is not provided");
    }

    this.init();
  }

  onMessage(message) {
    this.$log.text(message["podlog"]);
    this.$log.scrollTop(this.$log[0].scrollHeight);
    this.$progress.addClass("d-none");
  }

  requestLogs(objectId) {
    this.$log.text("Retrieving container logs. It may take a while to download...");
    this.$progress.removeClass("d-none");

    this.wss.send(
      JSON.stringify({
        pk: objectId,
        request: "container-log",
      })
    );
  }

  init() {
    $(document).on("click", '[data-bs-target="#fetchlogsModal"]', (e) => {
      const objectId = $(e.currentTarget).data("id");
      this.requestLogs(objectId);
    });
  }
}

