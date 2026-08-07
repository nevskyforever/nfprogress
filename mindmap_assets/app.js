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
  }));
}

function renderFloatingItems() {
  floatingItemsElement.replaceChildren();
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
    content.contentEditable = String(!readOnly);
    content.spellcheck = true;
    content.addEventListener('input', () => {
      item.text = content.textContent;
      scheduleSave();
    });
    content.addEventListener('pointerdown', (event) => event.stopPropagation());
    element.appendChild(content);
    element.addEventListener('pointerdown', (event) => startFloatingDrag(event, item));
    element.addEventListener('keydown', (event) => {
      if (!readOnly && event.key === 'Delete' && document.activeElement !== content) {
        floatingItems = floatingItems.filter((value) => value.id !== item.id);
        selectedFloatingItemId = null;
        renderFloatingItems();
        scheduleSave();
      }
    });
    floatingItemsElement.appendChild(element);
  }
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
    id: `nfprogress-floating-${crypto.randomUUID()}`,
    kind,
    text: kind === 'note' ? floatingNoteName : floatingNodeName,
    x: 50,
    y: 50,
  };
  floatingItems.push(item);
  selectedFloatingItemId = item.id;
  renderFloatingItems();
  scheduleSave();
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
  installBranchFocusControl(locale, payload.emptyStageMapText);
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
