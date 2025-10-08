// computeresource_selection.js

// Compute Resource Selection Modal Logic
class ComputeResourceHandler {
  constructor(register, opts = {}) {
    this.register = register;
    this.modalSelector = opts.modalSelector || '.computeresource-modal';
    this.triggerSelector = opts.triggerSelector || '[data-pk][data-name=resources]';
    this.confirmSelector = opts.confirmSelector || '#confirm-compute-selection';
    this.nodeInputSelector = opts.nodeInputSelector || '#id_node';
    this.progressSelector = opts.progressSelector || '.progress';
    this.busy = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>render...`;

    this.wsEndpoint = opts.wsEndpoint || null;
    this.wsFactory = typeof opts.wsFactory === 'function'
      ? opts.wsFactory
      : (endpoint, handlers) => new ManagedWebSocket(endpoint, handlers);

    // state
    this.selectedContainerId = null; // number | 'None'
    this.selectedNode = '';          // current selected node in UI
    this.currentNode = null;         // node that container currently uses
    this.containerRunning = null;    // TODO: set if you have this info

    // cache
    this.$modal = $(this.modalSelector);
    this.$nodeInput = $(this.nodeInputSelector);

    // bind handlers
    this._onWSMessage = this._onWSMessage.bind(this);
    this._onTriggerClick = this._onTriggerClick.bind(this);
    this._onConfirmClick = this._onConfirmClick.bind(this);
    this._onNodeChange = this._onNodeChange.bind(this);

    // ws instance
    this.wssMonitor = null;

    this.init();
  }

  init() {
    // wire UI
    $(document).on('click', this.triggerSelector, this._onTriggerClick);

    $(document).on('click', this.confirmSelector, this._onConfirmClick);
    this.$nodeInput.on('change', this._onNodeChange);

    // create WS if endpoint provided
    if (this.wsEndpoint) {
      this.wssMonitor = this.wsFactory(this.wsEndpoint, { onMessage: this._onWSMessage });
    } else {
      console.warn("option wsEndpoint is not specified.");
    }
  }

  destroy() {
    $(document).off('click', this.triggerSelector, this._onTriggerClick);
    $(document).off('click', this.confirmSelector, this._onConfirmClick);
    this.$nodeInput.off('change', this._onNodeChange);
    // optionally close WS
    if (this.wssMonitor && typeof this.wssMonitor.close === 'function') {
      this.wssMonitor.close();
    }
  }

  // Public API
  openModal(containerId) {
    this._open(containerId);
  }

  // ========== Internals ==========

  _onTriggerClick(e) {
    e.preventDefault();
    const $root = $(e.currentTarget).closest('[data-id]');
    const containerId = $root.data('id') || 'None';
    this._open(containerId);
  }

  _open(containerId) {
    this.selectedContainerId = (containerId === 'None') ? 'None' : parseInt(containerId, 10);
    const $button = $(`button[data-name=resources][data-pk="${containerId}"]`);

    const $node_bar = $(`[data-pk=${containerId}][data-name="node"][data-value]`).first();
    const currentNode = $node_bar.length ? $node_bar.data('value') : '';
    this.currentNode = currentNode;
    const normalized = this._mynone(currentNode);
    this.selectedNode = normalized;

    // preload values
    $("input[name='cpurequest']").val(parseFloat($(`[data-pk=${containerId}][data-name=cpu][data-value]`).data('value') || 0.1));
    $("input[name='gpurequest']").val(parseInt($(`[data-pk=${containerId}][data-name=gpu][data-value]`).data('value') || 0, 10));
    $("input[name='memoryrequest']").val(parseFloat($(`[data-pk=${containerId}][data-name=memory][data-value]`).data('value') || 0.1));
    $("input[name='idletime']").val(parseInt($(`[data-pk=${containerId}][data-name=idletime][data-value]`).data('value') || 1, 10));
    $("select[name='node']").val(currentNode).change();

    // show modal
    this.$modal.modal('show');

    setTimeout(() => {
      $(this.nodeInputSelector).val(normalized);
      this._retrieveResources(normalized);
    }, 200);
  }

  _onNodeChange() {
    const node = $(this.nodeInputSelector).val() || '';
    this.selectedNode = node;
    this._retrieveResources(node);
  }

  _retrieveResources(node) {
    if (this.wssMonitor && typeof this.wssMonitor.send === 'function') {
      this.wssMonitor.send(JSON.stringify({
        request: 'monitor-node',
        node: node,
      }));
    }
    $(this.progressSelector).removeClass('d-none');
    $("input[name$='request']").each(function() { $(this).attr('disabled', true); });
  }

  _onWSMessage(message) {
    // normalize to JS object if MessageEvent or JSON string
    let data = message;
    if (data && data.data !== undefined) {
      try { data = JSON.parse(data.data); } catch {}
    } else if (typeof data === 'string') {
      try { data = JSON.parse(data); } catch {}
    }

    const node = data?.node || '';
    if (node !== this.selectedNode) {
      console.error(`out of sync? >>${node}>>${this.selectedNode}>>`);
      return;
    }

    let cpu, gpu, memory;
    if (node === this.currentNode && node !== '' && this.containerRunning) {
      // If container running, add back old allocated amounts
      const cpuOld = parseFloat($("#id_cpurequest_old").val() || 0);
      const gpuOld = parseInt($("#id_gpurequest_old").val() || 0, 10);
      const memOld = parseFloat($("#id_memoryrequest_old").val() || 0);
      cpu = cpuOld + parseFloat(data.avail_cpu || 0);
      gpu = gpuOld + parseInt(data.avail_gpu || 0, 10);
      memory = memOld + parseFloat(data.avail_memory || 0);
    } else {
      cpu = parseFloat(data.avail_cpu || 0);
      gpu = parseInt(data.avail_gpu || 0, 10);
      memory = parseFloat(data.avail_memory || 0);
    }

    $(this.progressSelector).addClass('d-none');

    $("input[name='cpurequest']").attr('max', cpu);
    $("input[name='memoryrequest']").attr('max', memory);
    $("input[name='gpurequest']").attr('max', gpu);
    $("#thresholdhigh-cpurequest").text(cpu);
    $("#thresholdhigh-memoryrequest").text(memory);
    $("#thresholdhigh-gpurequest").text(gpu);

    $("input[name$='request']").each(function() {
      const mx = parseFloat($(this).attr('max') || 0);
      if (mx > 0) $(this).attr('disabled', false);
    });
  }

  _onConfirmClick() {
    const pk = this.selectedContainerId;
    if (!pk) return;

    const n = $('#id_node').val() || '';
    const c = $('#id_cpurequest').val();
    const g = $('#id_gpurequest').val();
    const m = $('#id_memoryrequest').val();
    const i = $('#id_idletime').val();

    const $btn = $(`button[data-name=resources][data-pk="${this.selectedContainerId}"]`);
    //$btn.html(this.busy).prop('disabled', true);
    $btn.prop('disabled', true);
    try {
        $btn.find("span[data-name=node]").html(this.busy);
        $btn.find("span[data-name=node]").removeClass('d-none');
        this.register.register_changes(pk, 'node',         n, this._mynone(String($btn.data('node') || '')));
        $btn.find("span[data-name=cpurequest]").html(this.busy);
        $btn.find("span[data-name=cpurequest]").removeClass('d-none');
        this.register.register_changes(pk, 'cpurequest',   c, this._mynone(String($btn.data('cpurequest') || '')));
        $btn.find("span[data-name=gpurequest]").html(this.busy);
        $btn.find("span[data-name=gpurequest]").removeClass('d-none');
        this.register.register_changes(pk, 'gpurequest',   g, this._mynone(String($btn.data('gpurequest') || '')));
        $btn.find("span[data-name=memoryrequest]").html(this.busy);
        $btn.find("span[data-name=memoryrequest]").removeClass('d-none');
        this.register.register_changes(pk, 'memoryrequest',m, this._mynone(String($btn.data('memoryrequest') || '')));
        $btn.find("span[data-name=idletime]").html(this.busy);
        $btn.find("span[data-name=idletime]").removeClass('d-none');
        this.register.register_changes(pk, 'idletime',     i, this._mynone(String($btn.data('idletime') || '')));
    } catch (err) {
        console.error(err);
        // Basic error hint (replace with your toast)
        $btn.html(`<span class="text-danger">Save failed</span>`).prop('disabled', true);
    } finally {
        this.$modal.modal('hide');
        this.selectedContainerId = null;
    }
  }

  _mynone(x) {
    return x === 'None' ? '' : x;
  }
}


