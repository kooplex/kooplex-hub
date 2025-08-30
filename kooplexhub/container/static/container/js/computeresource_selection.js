// computeresource_selection.js

// Compute Resource Selection Modal Logic
class ComputeResourceHandler {
  /**
   * @param {Object} opts
   * @param {string} [opts.modalSelector='.computeresource-modal']
   * @param {string} [opts.triggerSelector='[id^="container-resources-"]'] // clickables per container
   * @param {string} [opts.confirmSelector='#confirm-compute-selection']
   * @param {string} [opts.nodeInputSelector='#id_node'] // select input in modal
   * @param {string} [opts.progressSelector='.progress']
   * @param {string} [opts.wsEndpoint=null] // e.g., wsURLs.monitor_node
   * @param {function} [opts.wsFactory] // optional custom WS factory; defaults to new ManagedWebSocket(endpoint,{onMessage})
   */
  constructor(opts = {}) {
    this.modalSelector = opts.modalSelector || '.computeresource-modal';
    this.triggerSelector = opts.triggerSelector || '[data-action="ComputeResourceSelection.openModal"][data-id]';
    this.confirmSelector = opts.confirmSelector || '#confirm-compute-selection';
    this.nodeInputSelector = opts.nodeInputSelector || '#id_node';
    this.progressSelector = opts.progressSelector || '.progress';

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
  }

  init() {
    // wire UI
    $(document).on('click', this.triggerSelector, this._onTriggerClick);

    $(document).on('click', this.confirmSelector, this._onConfirmClick);
    this.$nodeInput.on('change', this._onNodeChange);

    // create WS if endpoint provided
    if (this.wsEndpoint) {
      this.wssMonitor = this.wsFactory(this.wsEndpoint, { onMessage: this._onWSMessage });
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

  // Public API (match your previous global)
  openModal(containerId, node) {
    this._open(containerId, node);
  }

  update(pk, node, cpurequest, gpurequest, memoryrequest, idletime) {
    // FIXME SAVE originals (as you noted)
    this._updateButtonFace(pk, node, cpurequest, gpurequest, memoryrequest, idletime);
  }

  // ========== Internals ==========

  _onTriggerClick(e) {
    e.preventDefault();
    const $root = $(e.currentTarget).closest('[data-id]');
    const containerId = $root.data('id');
    const node = String($root.data('node') || '');
    this._open(containerId, node);
  }

  _open(containerId, node) {
    this.selectedContainerId = (containerId === 'None') ? 'None' : parseInt(containerId, 10);
    const $button = $(`#container-resources-${containerId}`);

    const currentNode = String($button.data('node') || '');
    this.currentNode = currentNode;

    const normalized = this._mynone(node);
    this.selectedNode = normalized;

    // preload values
    $("input[name='cpurequest']").val(parseFloat($button.data('cpurequest') || 0));
    $("input[name='gpurequest']").val(parseInt($button.data('gpurequest') || 0, 10));
    $("input[name='memoryrequest']").val(parseFloat($button.data('memoryrequest') || 0));
    $("input[name='idletime']").val(parseInt($button.data('idletime') || 0, 10));
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

    const $btn = $(`#container-resources-${pk}`);

    this._reg(pk, 'node',         n, this._mynone(String($btn.data('node') || ''))),
    this._reg(pk, 'cpurequest',   c, this._mynone(String($btn.data('cpurequest') || ''))),
    this._reg(pk, 'gpurequest',   g, this._mynone(String($btn.data('gpurequest') || ''))),
    this._reg(pk, 'memoryrequest',m, this._mynone(String($btn.data('memoryrequest') || ''))),
    this._reg(pk, 'idletime',     i, this._mynone(String($btn.data('idletime') || ''))),

    this._updateButtonFace(pk, n, c, g, m, i);

    this.$modal.modal('hide');
    this.selectedContainerId = null;
  }

  _updateButtonFace(pk, n, c, g, m, i) {
    $(`#container-resources-${pk} [name=node] [name=node_name]`).text(n);
    $(`#container-resources-${pk} [name=cpu] [name=node_cpu_request]`).text(c);
    $(`#container-resources-${pk} [name=gpu] [name=node_gpu_request]`).text(g);
    $(`#container-resources-${pk} [name=mem] [name=node_memory_request]`).text(`${m}GB`);
    $(`#container-resources-${pk} [name=up] [name=node_idle]`).text(`${i} h`);

    const $wid_node  = $(`#container-resources-${pk} [name=node]`);
    const $wid_cpu   = $(`#container-resources-${pk} [name=cpu]`);
    const $wid_gpu   = $(`#container-resources-${pk} [name=gpu]`);
    const $wid_mem   = $(`#container-resources-${pk} [name=mem]`);
    const $wid_up    = $(`#container-resources-${pk} [name=up]`);
    const $wid_empty = $(`#container-resources-${pk} [name=empty]`);

    n && n.length ? $wid_node.removeClass('d-none') : $wid_node.addClass('d-none');
    c ? $wid_cpu.removeClass('d-none') : $wid_cpu.addClass('d-none');
    g ? $wid_gpu.removeClass('d-none') : $wid_gpu.addClass('d-none');
    m ? $wid_mem.removeClass('d-none') : $wid_mem.addClass('d-none');
    i ? $wid_up.removeClass('d-none') : $wid_up.addClass('d-none');

    const sum = (n && n.length ? 1 : 0) + (c?1:0) + (g?1:0) + (m?1:0) + (i?1:0);
    sum === 0 ? $wid_empty.removeClass('d-none') : $wid_empty.addClass('d-none');
  }

  _mynone(x) {
    return x === 'None' ? '' : x;
  }

  _reg(pk, field, newVal, oldVal) {
    if (typeof wss_containerconfig.register_changes === 'function') {
      return !!wss_containerconfig.register_changes(pk, field, newVal, oldVal);
    }
    console.warn('ComputeResourceHandler: wss_containerconfig.register_changes not found');
    return false;
  }
}


// Run when document is ready
$(document).ready(function() {
  const ComputeResourceSelection = new ComputeResourceHandler({
    wsEndpoint: wsURLs?.monitor_node || null,
  });
  ComputeResourceSelection.init();
});




