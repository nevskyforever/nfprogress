import MindElixir from './MindElixir.js';
import { de, en, es, fr, pt, ru } from './i18n.js';

const localePacks = { de, en, es, fr, pt_BR: pt, ru };
const loadingElement = document.getElementById('loading');

let mind = null;
let readOnly = false;
let saveTimer = null;
const nativeEvents = [];
let floatingItems = [];
let selectedFloatingItemId = null;
let floatingNodeName = 'Свободный узел';
let floatingNoteName = 'Новая заметка';
const floatingItemsElement = document.getElementById('floating-items');
const floatingLinksElement = document.getElementById('floating-links');

const bridge = {
  changed() {
    nativeEvents.push({ type: 'changed' });
  },
  ready() {
    nativeEvents.push({ type: 'ready' });
  },
  reportError(details) {
    nativeEvents.push({ type: 'error', details: String(details) });
  },
  save(payload) {
    nativeEvents.push({ type: 'save', payload });
  },
  showStatus(message) {
    nativeEvents.push({ type: 'status', message: String(message) });
  },
  exportFile(format, data) {
    nativeEvents.push({ type: 'export', format, data });
  },
  exportError(details) {
    nativeEvents.push({ type: 'exportError', details: String(details) });
  },
};

function nodeObject(value) {
  if (value?.nodeObj) {
    return value.nodeObj;
  }
  if (value && typeof value === 'object' && typeof value.id === 'string') {
    return value;
  }
  return null;
}

function isReadOnlyStageNode(value) {
  return Boolean(nodeObject(value)?.nfprogressReadOnly);
}

function mutationTouchesReadOnlyStage(instance, values) {
  const explicitValues = values.flatMap((value) => (
    Array.isArray(value) ? value : [value]
  ));
  return (
    explicitValues.some(isReadOnlyStageNode)
    || (instance.currentNodes || []).some(isReadOnlyStageNode)
  );
}

function protectReadOnlyStageNodeMutations() {
  const operationNames = [
    'addChild',
    'beginEdit',
    'copyNode',
    'copyNodes',
    'insertParent',
    'insertSibling',
    'moveDownNode',
    'moveNodeAfter',
    'moveNodeBefore',
    'moveNodeIn',
    'moveUpNode',
    'removeNodes',
    'reshapeNode',
    'setNodeTopic',
  ];
  for (const operationName of operationNames) {
    protectMethod(operationName, (...values) => (
      mutationTouchesReadOnlyStage(mind, values)
    ));
  }
}

function markReadOnlyStageNodes() {
  if (!mind) {
    return;
  }
  for (const topic of mind.container.querySelectorAll('me-tpc')) {
    topic.classList.toggle(
      'nfprogress-read-only-stage',
      isReadOnlyStageNode(topic),
    );
  }
}

function mapNodeById(nodeId) {
  if (!mind || typeof nodeId !== 'string') {
    return null;
  }
  return mind.findEle(nodeId)?.nodeObj || null;
}

function arrowTouchesReadOnlyStage(arrow) {
  return Boolean(
    arrow
    && (
      isReadOnlyStageNode(mapNodeById(arrow.from))
      || isReadOnlyStageNode(mapNodeById(arrow.to))
    )
  );
}

function summaryTouchesReadOnlyStage(summary) {
  return Boolean(
    summary && isReadOnlyStageNode(mapNodeById(summary.parent))
  );
}

function protectMethod(methodName, shouldBlock) {
  const originalMethod = mind?.[methodName];
  if (typeof originalMethod !== 'function') {
    return;
  }
  mind[methodName] = function protectedMethod(...values) {
    if (shouldBlock(...values)) {
      return undefined;
    }
    return originalMethod.apply(this, values);
  };
}

function protectReadOnlyStageConnections() {
  protectMethod('createArrow', (from, to) => (
    isReadOnlyStageNode(from) || isReadOnlyStageNode(to)
  ));
  protectMethod('createArrowFrom', arrowTouchesReadOnlyStage);
  protectMethod('removeArrow', (arrowElement) => arrowTouchesReadOnlyStage(
    arrowElement?.arrowObj || mind.currentArrow?.arrowObj,
  ));
  protectMethod('editArrowLabel', (arrowElement) => arrowTouchesReadOnlyStage(
    arrowElement?.arrowObj || mind.currentArrow?.arrowObj,
  ));
  protectMethod('reshapeArrow', arrowTouchesReadOnlyStage);
  protectMethod('createSummary', () => (
    (mind.currentNodes || []).some(isReadOnlyStageNode)
  ));
  protectMethod('createSummaryFrom', summaryTouchesReadOnlyStage);
  protectMethod('removeSummary', (summaryId) => summaryTouchesReadOnlyStage(
    (mind.summaries || []).find((summary) => summary.id === summaryId),
  ));
  protectMethod('editSummary', (summaryElement) => summaryTouchesReadOnlyStage(
    summaryElement?.summaryObj,
  ));
}

function installBranchFocusControl(locale, emptyStageMapText) {
  const originalControl = mind?.el?.querySelector('#fullscreen');
  if (!originalControl) {
    return;
  }

  const focusControl = originalControl.cloneNode(false);
  focusControl.id = 'focusBranch';
  focusControl.title = locale.focus;
  focusControl.setAttribute('aria-label', locale.focus);
  focusControl.innerHTML = `
    <svg class="icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M9 4H4v5M15 4h5v5M20 15v5h-5M9 20H4v-5"
        fill="none" stroke="currentColor" stroke-width="2"
        stroke-linecap="round" stroke-linejoin="round" />
    </svg>
  `;
  originalControl.replaceWith(focusControl);
  focusControl.addEventListener('click', (event) => {
    event.preventDefault();
    event.stopPropagation();
    if (mind.isFocusMode) {
      mind.cancelFocus();
      focusControl.classList.remove('nfprogress-focus-active');
      focusControl.title = locale.focus;
      focusControl.setAttribute('aria-label', locale.focus);
      return;
    }

    const selectedNode = mind.currentNode;
    const nodeData = selectedNode?.nodeObj;
    const isFirstLevelBranch = Boolean(
      nodeData?.parent && !nodeData.parent.parent
    );
    if (!isFirstLevelBranch) {
      return;
    }
    if (nodeData.nfprogressEmptyStageMap) {
      bridge.showStatus(emptyStageMapText);
      return;
    }

    mind.focusNode(selectedNode);
    focusControl.classList.add('nfprogress-focus-active');
    focusControl.title = locale.cancelFocus;
    focusControl.setAttribute('aria-label', locale.cancelFocus);
  });
}

function errorText(error) {
  if (error instanceof Error) {
    return error.stack || error.message;
  }
  return String(error);
}

function reportError(error) {
  const message = errorText(error);
  console.error(message);
  bridge.reportError(message);
}

function finishActiveEdit() {
  const activeElement = document.activeElement;
  if (activeElement && activeElement !== document.body) {
    activeElement.blur();
  }
}

function serializeMap(finishEditing = false) {
  if (!mind) {
    return null;
  }
  if (finishEditing) {
    finishActiveEdit();
  }
  const data = JSON.parse(mind.getDataString());
  if (floatingItems.length) {
    data.nfprogressFloatingItems = floatingItems;
  } else {
    delete data.nfprogressFloatingItems;
  }
  return JSON.stringify(data);
}

function normalizedFloatingItems(value) {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item) => (
    item && typeof item.id === 'string' && item.id
    && (item.kind === 'node' || item.kind === 'note')
    && typeof item.text === 'string'
    && Number.isFinite(item.x) && Number.isFinite(item.y)
  )).map((item) => ({
    id: item.id,
    kind: item.kind,
    text: item.text,
    x: Math.max(0, Math.min(100, item.x)),
    y: Math.max(0, Math.min(100, item.y)),
    parentId: typeof item.parentId === 'string' ? item.parentId : null,
  }));
}

function floatingItemById(itemId) {
  return floatingItems.find((item) => item.id === itemId) || null;
}

function drawFloatingLinks() {
  floatingLinksElement.replaceChildren();
  for (const item of floatingItems) {
    if (!item.parentId) continue;
    const parent = floatingItemById(item.parentId);
    if (!parent) continue;
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', `${parent.x}%`);
    line.setAttribute('y1', `${parent.y}%`);
    line.setAttribute('x2', `${item.x}%`);
    line.setAttribute('y2', `${item.y}%`);
    line.setAttribute('stroke', '#4f8cff');
    line.setAttribute('stroke-width', '2');
    floatingLinksElement.appendChild(line);
  }
}

function renderFloatingItems() {
  floatingItemsElement.replaceChildren();
  drawFloatingLinks();
  for (const item of floatingItems) {
    const element = document.createElement('div');
    element.className = `floating-item ${item.kind}`;
    element.style.left = `${item.x}%`;
    element.style.top = `${item.y}%`;
    element.dataset.itemId = item.id;
    element.tabIndex = readOnly ? -1 : 0;
    element.setAttribute('role', 'group');
    if (item.id === selectedFloatingItemId) element.classList.add('selected');

    const content = document.createElement('span');
    content.className = 'floating-item-content';
    content.textContent = item.text;
    content.contentEditable = 'false';
    content.spellcheck = true;
    content.addEventListener('input', () => {
      item.text = content.textContent;
      scheduleSave();
    });
    content.addEventListener('dblclick', () => beginFloatingEdit(content, item));
    element.addEventListener('click', () => {
      selectedFloatingItemId = item.id;
      renderFloatingItems();
    });
    element.appendChild(content);
    element.addEventListener('pointerdown', (event) => startFloatingDrag(event, item));
    element.addEventListener('keydown', (event) => {
      if (readOnly || document.activeElement === content) return;
      if (event.key === 'Tab' && item.kind === 'node') {
        event.preventDefault();
        addFloatingNode(item.id, item.x + 8, item.y + 10);
      } else if (event.key === 'Enter' && item.kind === 'node') {
        event.preventDefault();
        addFloatingNode(item.parentId, item.x + 12, item.y);
      } else if (event.key === 'F2') {
        event.preventDefault();
        beginFloatingEdit(content, item);
      } else if (event.key === 'Delete') {
        const removedIds = new Set([item.id]);
        let foundChild = true;
        while (foundChild) {
          foundChild = false;
          for (const value of floatingItems) {
            if (removedIds.has(value.parentId) && !removedIds.has(value.id)) {
              removedIds.add(value.id);
              foundChild = true;
            }
          }
        }
        floatingItems = floatingItems.filter((value) => !removedIds.has(value.id));
        selectedFloatingItemId = null;
        renderFloatingItems();
        scheduleSave();
      }
    });
    floatingItemsElement.appendChild(element);
  }
}

function beginFloatingEdit(content, item) {
  if (readOnly) return;
  content.contentEditable = 'true';
  content.focus();
  const selection = window.getSelection();
  selection.selectAllChildren(content);
  selection.collapseToEnd();
  const finish = () => {
    item.text = content.textContent;
    content.contentEditable = 'false';
    content.removeEventListener('keydown', onKeyDown);
    scheduleSave();
  };
  const onKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      content.blur();
    }
  };
  content.addEventListener('blur', finish, { once: true });
  content.addEventListener('keydown', onKeyDown);
}

function startFloatingDrag(event, item) {
  if (readOnly || event.target.isContentEditable) return;
  event.preventDefault();
  selectedFloatingItemId = item.id;
  const bounds = floatingItemsElement.getBoundingClientRect();
  const move = (moveEvent) => {
    item.x = Math.max(0, Math.min(100, (moveEvent.clientX - bounds.left) / bounds.width * 100));
    item.y = Math.max(0, Math.min(100, (moveEvent.clientY - bounds.top) / bounds.height * 100));
    renderFloatingItems();
  };
  const finish = () => {
    document.removeEventListener('pointermove', move);
    document.removeEventListener('pointerup', finish);
    scheduleSave();
  };
  document.addEventListener('pointermove', move);
  document.addEventListener('pointerup', finish, { once: true });
}

function addFloatingItem(kind) {
  if (readOnly || (kind !== 'node' && kind !== 'note')) return;
  const item = {
    id: `nfprogress-floating-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    kind,
    text: kind === 'note' ? floatingNoteName : floatingNodeName,
    x: 50,
    y: 50,
    parentId: null,
  };
  floatingItems.push(item);
  selectedFloatingItemId = item.id;
  renderFloatingItems();
  scheduleSave();
}

function addFloatingNode(parentId, x, y) {
  const item = {
    id: `nfprogress-floating-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    kind: 'node',
    text: floatingNodeName,
    x: Math.max(0, Math.min(100, x)),
    y: Math.max(0, Math.min(100, y)),
    parentId: parentId || null,
  };
  floatingItems.push(item);
  selectedFloatingItemId = item.id;
  renderFloatingItems();
  scheduleSave();
}

function installFloatingItemControls(payload) {
  if (readOnly) return;
  const toolbar = mind?.el?.querySelector('.mind-elixir-toolbar.rb');
  if (!toolbar) return;

  const controls = [
    {
      kind: 'node',
      label: payload.addFloatingNodeLabel,
      icon: '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="6" cy="6" r="3" fill="currentColor"/><circle cx="18" cy="7" r="3" fill="currentColor"/><circle cx="12" cy="18" r="3" fill="currentColor"/><path d="M8.5 7.5l6.8-0.1M7.5 8.5l3 6.5M16.5 9.5l-3 5.5" fill="none" stroke="currentColor" stroke-width="1.7"/></svg>',
    },
    {
      kind: 'note',
      label: payload.addFloatingNoteLabel,
      icon: '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 3h14v18l-4-3-4 3-4-3-2 1.5V3z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M8 8h8M8 12h6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
    },
  ];
  for (const control of controls) {
    const element = document.createElement('span');
    element.className = 'nfprogress-floating-control';
    element.tabIndex = 0;
    element.title = control.label;
    element.setAttribute('aria-label', control.label);
    element.setAttribute('role', 'button');
    element.innerHTML = control.icon;
    element.addEventListener('click', () => addFloatingItem(control.kind));
    element.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        addFloatingItem(control.kind);
      }
    });
    toolbar.appendChild(element);
  }
}

function collectSearchResults(node, query, results) {
  if (!node) return;
  const text = String(node.topic || '');
  if (text.toLocaleLowerCase().includes(query)) {
    results.push({ type: 'node', id: node.id, text });
  }
  for (const child of node.children || []) collectSearchResults(child, query, results);
}

function revealMapNode(nodeId) {
  const targetData = findNodeData(mind.nodeData, nodeId);
  if (!targetData) return;
  const ancestors = [];
  for (let parent = targetData.parent; parent; parent = parent.parent) ancestors.push(parent);
  for (const ancestor of ancestors.reverse()) {
    const element = mind.findEle(ancestor.id);
    if (element && ancestor.expanded === false) mind.expandNode(element, true);
  }
  const element = mind.findEle(nodeId);
  if (element) {
    mind.selectNode(element);
    mind.scrollIntoView(element, true);
  }
}

function findNodeData(node, nodeId) {
  if (!node) return null;
  if (node.id === nodeId) return node;
  for (const child of node.children || []) {
    const found = findNodeData(child, nodeId);
    if (found) return found;
  }
  return null;
}

function revealFloatingItem(itemId) {
  const item = floatingItemById(itemId);
  if (!item) return;
  item.x = 50;
  item.y = 50;
  selectedFloatingItemId = itemId;
  renderFloatingItems();
  scheduleSave();
}

function installSearchControl(payload) {
  const toolbar = mind?.el?.querySelector('.mind-elixir-toolbar.lt');
  if (!toolbar) return;
  const control = document.createElement('span');
  control.className = 'nfprogress-floating-control';
  control.tabIndex = 0;
  control.title = payload.searchMapLabel;
  control.setAttribute('aria-label', payload.searchMapLabel);
  control.setAttribute('role', 'button');
  control.innerHTML = '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="m16 16 5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
  const panel = document.createElement('div');
  panel.className = 'nfprogress-search-panel';
  panel.hidden = true;
  const input = document.createElement('input');
  input.className = 'nfprogress-search-input';
  input.type = 'search';
  input.placeholder = payload.searchPlaceholder;
  input.setAttribute('aria-label', payload.searchPlaceholder);
  const resultsElement = document.createElement('div');
  resultsElement.className = 'nfprogress-search-results';
  panel.append(input, resultsElement);
  mind.el.appendChild(panel);

  const updateResults = () => {
    const query = input.value.trim().toLocaleLowerCase();
    resultsElement.replaceChildren();
    if (!query) return;
    const results = [];
    collectSearchResults(mind.nodeData, query, results);
    for (const item of floatingItems) {
      if (item.text.toLocaleLowerCase().includes(query)) {
        results.push({ type: 'floating', id: item.id, text: item.text, kind: item.kind });
      }
    }
    if (!results.length) {
      const empty = document.createElement('div');
      empty.className = 'nfprogress-search-empty';
      empty.textContent = payload.nothingFoundText;
      resultsElement.appendChild(empty);
      return;
    }
    for (const result of results) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'nfprogress-search-result';
      button.textContent = result.type === 'floating'
        ? `${result.kind === 'note' ? '📝 ' : '◉ '}${result.text}`
        : result.text;
      button.addEventListener('click', () => {
        if (result.type === 'node') revealMapNode(result.id);
        else revealFloatingItem(result.id);
        panel.hidden = true;
      });
      resultsElement.appendChild(button);
    }
  };
  const toggle = () => {
    panel.hidden = !panel.hidden;
    if (!panel.hidden) input.focus();
  };
  control.addEventListener('click', toggle);
  control.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      toggle();
    }
  });
  input.addEventListener('input', updateResults);
  toolbar.appendChild(control);
}

function persistMap(finishEditing = false) {
  if (!mind || readOnly) {
    return;
  }
  if (saveTimer !== null) {
    window.clearTimeout(saveTimer);
    saveTimer = null;
  }
  try {
    bridge.save(serializeMap(finishEditing));
  } catch (error) {
    reportError(error);
  }
}

function scheduleSave(operation) {
  if (readOnly) {
    return;
  }
  bridge.changed();
  if (operation?.name === 'beginEdit') {
    return;
  }
  if (saveTimer !== null) {
    window.clearTimeout(saveTimer);
  }
  saveTimer = window.setTimeout(() => persistMap(false), 400);
}

function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
}

async function requestExport(format) {
  if (!mind) {
    bridge.exportError('Mind Elixir is not initialized.');
    return;
  }
  try {
    finishActiveEdit();
    if (format === 'json') {
      bridge.exportFile(format, mind.getDataString());
      return;
    }
    const blob = format === 'png'
      ? await mind.exportPng()
      : mind.exportSvg();
    bridge.exportFile(format, await blobToDataUrl(blob));
  } catch (error) {
    reportError(error);
    bridge.exportError(errorText(error));
  }
}

function initialize(payload) {
  readOnly = Boolean(payload.readOnly);
  document.documentElement.lang = payload.locale.replace('_', '-');
  document.getElementById('map').setAttribute('aria-label', payload.editorLabel);
  loadingElement.textContent = payload.loadingText;
  floatingItemsElement.setAttribute('aria-label', payload.floatingItemsLabel);
  floatingNodeName = payload.floatingNodeName;
  floatingNoteName = payload.floatingNoteName;
  const locale = localePacks[payload.locale] || en;
  const options = {
    el: '#map',
    direction: MindElixir.SIDE,
    contextMenu: readOnly ? false : { focus: true, link: true, locale },
    toolBar: true,
    keypress: !readOnly,
    draggable: !readOnly,
    editable: !readOnly,
    newTopicName: payload.newTopicName,
    allowUndo: true,
    alignment: 'nodes',
  };

  mind = new MindElixir(options);
  mind.init(payload.data || MindElixir.new(payload.rootTopic));
  floatingItems = normalizedFloatingItems(payload.data?.nfprogressFloatingItems);
  renderFloatingItems();
  installFloatingItemControls(payload);
  installBranchFocusControl(locale, payload.emptyStageMapText);
  installSearchControl(payload);
  protectReadOnlyStageNodeMutations();
  protectReadOnlyStageConnections();
  markReadOnlyStageNodes();
  mind.bus.addListener('linkDiv', markReadOnlyStageNodes);

  if (!readOnly) {
    mind.bus.addListener('operation', scheduleSave);
    mind.bus.addListener('expandNode', scheduleSave);
    mind.bus.addListener('updateArrowDelta', scheduleSave);
  }

  loadingElement.hidden = true;
  bridge.ready();
  if (!payload.data && !readOnly) {
    persistMap(false);
  }
  window.requestAnimationFrame(() => mind.toCenter());
}

window.nfprogressMindMap = {
  initialize,
  getDataString() {
    return serializeMap(true);
  },
  addFloatingItem,
  requestExport,
  saveNow() {
    persistMap(true);
  },
  toCenter() {
    if (mind) {
      mind.toCenter();
    }
  },
  takeEvents() {
    return JSON.stringify(nativeEvents.splice(0));
  },
};

window.addEventListener('error', (event) => reportError(event.error || event.message));
window.addEventListener('unhandledrejection', (event) => reportError(event.reason));
