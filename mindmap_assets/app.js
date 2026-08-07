import MindElixir from './MindElixir.js';
import { de, en, es, fr, pt, ru } from './i18n.js';

const localePacks = { de, en, es, fr, pt_BR: pt, ru };
const loadingElement = document.getElementById('loading');

let mind = null;
let readOnly = false;
let saveTimer = null;
const nativeEvents = [];
let floatingItems = [];
let floatingLinks = [];
let selectedFloatingItemId = null;
let selectedFloatingLinkId = null;
let pendingFloatingLink = null;
let floatingContextMenu = null;
let floatingMenuLabels = null;
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
  const floatingIds = new Set(floatingItems.map((item) => item.id));
  floatingLinks = floatingLinks.filter((link) => {
    const fromExists = link.fromType === 'floating'
      ? floatingIds.has(link.from)
      : Boolean(findNodeData(data.nodeData, link.from));
    const toExists = link.toType === 'floating'
      ? floatingIds.has(link.to)
      : Boolean(findNodeData(data.nodeData, link.to));
    return fromExists && toExists;
  });
  if (floatingItems.length) {
    data.nfprogressFloatingItems = floatingItems;
  } else {
    delete data.nfprogressFloatingItems;
  }
  if (floatingLinks.length) {
    data.nfprogressFloatingLinks = floatingLinks;
  } else {
    delete data.nfprogressFloatingLinks;
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

function normalizedFloatingLinks(value) {
  if (!Array.isArray(value)) return [];
  return value.filter((link) => (
    link && typeof link.id === 'string' && link.id
    && (link.fromType === 'floating' || link.fromType === 'node')
    && (link.toType === 'floating' || link.toType === 'node')
    && typeof link.from === 'string' && link.from
    && typeof link.to === 'string' && link.to
  )).map((link) => ({
    id: link.id,
    fromType: link.fromType,
    from: link.from,
    toType: link.toType,
    to: link.to,
  }));
}

function endpointCenter(type, id) {
  const overlayBounds = floatingLinksElement.getBoundingClientRect();
  let element = null;
  if (type === 'floating') {
    element = floatingItemsElement.querySelector(`[data-item-id="${CSS.escape(id)}"]`);
  } else {
    element = mind?.findEle(id);
  }
  if (!element) return null;
  const bounds = element.getBoundingClientRect();
  return {
    x: bounds.left + bounds.width / 2 - overlayBounds.left,
    y: bounds.top + bounds.height / 2 - overlayBounds.top,
  };
}

function drawFloatingLinks() {
  for (const line of floatingLinksElement.querySelectorAll(':scope > line')) line.remove();
  for (const item of floatingItems) {
    if (!item.parentId) continue;
    const parent = floatingItemById(item.parentId);
    if (!parent) continue;
    const from = endpointCenter('floating', parent.id);
    const to = endpointCenter('floating', item.id);
    if (!from || !to) continue;
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', from.x);
    line.setAttribute('y1', from.y);
    line.setAttribute('x2', to.x);
    line.setAttribute('y2', to.y);
    line.setAttribute('stroke', '#4f8cff');
    line.setAttribute('stroke-width', '2');
    floatingLinksElement.appendChild(line);
  }
  for (const link of floatingLinks) {
    const from = endpointCenter(link.fromType, link.from);
    const to = endpointCenter(link.toType, link.to);
    if (!from || !to) continue;
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', from.x);
    line.setAttribute('y1', from.y);
    line.setAttribute('x2', to.x);
    line.setAttribute('y2', to.y);
    line.setAttribute('stroke', '#7c8da8');
    line.setAttribute('stroke-width', '2');
    line.setAttribute('marker-end', 'url(#nfprogress-arrowhead)');
    line.classList.add('nfprogress-floating-link');
    line.dataset.linkId = link.id;
    line.tabIndex = 0;
    if (link.id === selectedFloatingLinkId) line.classList.add('selected');
    line.addEventListener('click', (event) => {
      event.stopPropagation();
      selectedFloatingLinkId = link.id;
      drawFloatingLinks();
      floatingLinksElement.querySelector(
        `[data-link-id="${CSS.escape(link.id)}"]`,
      )?.focus();
    });
    line.addEventListener('keydown', (event) => {
      if (!readOnly && (event.key === 'Delete' || event.key === 'Backspace')) {
        event.preventDefault();
        floatingLinks = floatingLinks.filter((value) => value.id !== link.id);
        selectedFloatingLinkId = null;
        drawFloatingLinks();
        scheduleSave();
      }
    });
    floatingLinksElement.appendChild(line);
  }
}

function renderFloatingItems() {
  floatingItemsElement.replaceChildren();
  for (const item of floatingItems) {
    const element = document.createElement('div');
    element.className = `floating-item ${item.kind}${item.kind === 'node' && !item.parentId ? ' root' : ''}`;
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
      if (pendingFloatingLink) {
        finishFloatingLink('floating', item.id);
        return;
      }
      selectedFloatingItemId = item.id;
      for (const selected of floatingItemsElement.querySelectorAll('.floating-item.selected')) {
        selected.classList.remove('selected');
      }
      element.classList.add('selected');
      element.focus();
    });
    element.appendChild(content);
    element.addEventListener('contextmenu', (event) => {
      if (readOnly) return;
      event.preventDefault();
      event.stopPropagation();
      selectFloatingItem(item.id, element);
      showFloatingContextMenu(event.clientX, event.clientY, item);
    });
    element.addEventListener('pointerdown', (event) => startFloatingDrag(event, item));
    element.addEventListener('keydown', (event) => {
      if (readOnly || document.activeElement === content) return;
      if (event.key === 'Tab' && item.kind === 'node') {
        event.preventDefault();
        addFloatingChild(item);
      } else if (event.key === 'Tab' && item.kind === 'note') {
        event.preventDefault();
        addFloatingItem('note', item.x + 12, item.y);
      } else if (event.key === 'Enter' && item.kind === 'node') {
        event.preventDefault();
        addFloatingNode(item.parentId, item.x + 12, item.y);
      } else if (event.key === 'F2') {
        event.preventDefault();
        beginFloatingEdit(content, item);
      } else if (event.key === 'Delete' || event.key === 'Backspace') {
        event.preventDefault();
        removeFloatingItem(item.id);
      }
    });
    floatingItemsElement.appendChild(element);
  }
  drawFloatingLinks();
}

function selectFloatingItem(itemId, element = null) {
  selectedFloatingItemId = itemId;
  for (const selected of floatingItemsElement.querySelectorAll('.floating-item.selected')) {
    selected.classList.remove('selected');
  }
  const target = element || floatingItemsElement.querySelector(
    `[data-item-id="${CSS.escape(itemId)}"]`,
  );
  target?.classList.add('selected');
  target?.focus();
}

function descendantFloatingIds(itemId) {
  const removedIds = new Set([itemId]);
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
  return removedIds;
}

function removeFloatingItem(itemId) {
  const removedIds = descendantFloatingIds(itemId);
  floatingItems = floatingItems.filter((value) => !removedIds.has(value.id));
  floatingLinks = floatingLinks.filter((link) => !(
    (link.fromType === 'floating' && removedIds.has(link.from))
    || (link.toType === 'floating' && removedIds.has(link.to))
  ));
  selectedFloatingItemId = null;
  selectedFloatingLinkId = null;
  renderFloatingItems();
  scheduleSave();
}

function beginFloatingLink(itemId) {
  beginFloatingLinkFrom('floating', itemId);
}

function beginFloatingLinkFrom(type, id) {
  pendingFloatingLink = { type, id };
  floatingContextMenu?.remove();
  floatingContextMenu = null;
  floatingItemsElement.classList.add('linking');
}

function beginMapNodeLink() {
  const nodeId = mind?.currentNode?.nodeObj?.id;
  const contextMenu = mind?.container.querySelector('.context-menu');
  if (contextMenu) contextMenu.hidden = true;
  if (nodeId) beginFloatingLinkFrom('node', nodeId);
}

function finishFloatingLink(type, id) {
  if (!pendingFloatingLink) return false;
  const source = pendingFloatingLink;
  pendingFloatingLink = null;
  floatingItemsElement.classList.remove('linking');
  if (source.type === type && source.id === id) return true;
  const duplicate = floatingLinks.some((link) => (
    link.fromType === source.type && link.from === source.id
    && link.toType === type && link.to === id
  ));
  if (!duplicate) {
    floatingLinks.push({
      id: `nfprogress-link-${Date.now()}-${Math.random().toString(16).slice(2)}`,
      fromType: source.type,
      from: source.id,
      toType: type,
      to: id,
    });
    selectedFloatingLinkId = floatingLinks[floatingLinks.length - 1].id;
    drawFloatingLinks();
    scheduleSave();
  }
  return true;
}

function contextMenuAction(label, callback) {
  const item = document.createElement('button');
  item.type = 'button';
  item.textContent = label;
  item.addEventListener('click', () => {
    floatingContextMenu?.remove();
    floatingContextMenu = null;
    callback();
  });
  return item;
}

function showFloatingContextMenu(x, y, item) {
  floatingContextMenu?.remove();
  const menu = document.createElement('div');
  menu.className = 'nfprogress-floating-menu';
  if (item.kind === 'node') {
    menu.appendChild(contextMenuAction(floatingMenuLabels.addChild, () => (
      addFloatingChild(item)
    )));
    menu.appendChild(contextMenuAction(floatingMenuLabels.addSibling, () => (
      addFloatingNode(item.parentId, item.x + 12, item.y)
    )));
  } else {
    menu.appendChild(contextMenuAction(floatingMenuLabels.addNote, () => (
      addFloatingItem('note', item.x + 12, item.y)
    )));
  }
  menu.appendChild(contextMenuAction(floatingMenuLabels.edit, () => {
    const content = floatingItemsElement.querySelector(
      `[data-item-id="${CSS.escape(item.id)}"] .floating-item-content`,
    );
    if (content) beginFloatingEdit(content, item);
  }));
  menu.appendChild(contextMenuAction(floatingMenuLabels.link, () => (
    beginFloatingLink(item.id)
  )));
  menu.appendChild(contextMenuAction(floatingMenuLabels.remove, () => (
    removeFloatingItem(item.id)
  )));
  document.body.appendChild(menu);
  const bounds = menu.getBoundingClientRect();
  menu.style.left = `${Math.min(x, window.innerWidth - bounds.width - 8)}px`;
  menu.style.top = `${Math.min(y, window.innerHeight - bounds.height - 8)}px`;
  floatingContextMenu = menu;
}

function installFloatingLinkTargets() {
  mind.container.addEventListener('pointerdown', (event) => {
    if (!pendingFloatingLink) return;
    const topic = event.target.closest?.('me-tpc');
    if (!topic?.nodeObj?.id) return;
    event.preventDefault();
    event.stopPropagation();
    finishFloatingLink('node', topic.nodeObj.id);
    mind.selectNode(topic);
  }, true);
  document.addEventListener('pointerdown', (event) => {
    if (floatingContextMenu && !floatingContextMenu.contains(event.target)) {
      floatingContextMenu.remove();
      floatingContextMenu = null;
    }
    if (
      pendingFloatingLink
      && !event.target.closest?.('.floating-item')
      && !event.target.closest?.('me-tpc')
      && !event.target.closest?.('.nfprogress-floating-menu')
    ) {
      pendingFloatingLink = null;
      floatingItemsElement.classList.remove('linking');
    }
  });
}

function focusSelectedFloatingItem() {
  window.requestAnimationFrame(() => {
    floatingItemsElement.querySelector('.floating-item.selected')?.focus();
  });
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
  if (
    readOnly || pendingFloatingLink || event.button !== 0
    || event.target.isContentEditable
  ) return;
  event.preventDefault();
  selectedFloatingItemId = item.id;
  const bounds = floatingItemsElement.getBoundingClientRect();
  const startX = event.clientX;
  const startY = event.clientY;
  const movedIds = item.kind === 'node' ? descendantFloatingIds(item.id) : new Set([item.id]);
  const originalPositions = new Map(
    floatingItems.filter((value) => movedIds.has(value.id)).map((value) => (
      [value.id, { x: value.x, y: value.y }]
    )),
  );
  const move = (moveEvent) => {
    const dx = (moveEvent.clientX - startX) / bounds.width * 100;
    const dy = (moveEvent.clientY - startY) / bounds.height * 100;
    for (const value of floatingItems) {
      const original = originalPositions.get(value.id);
      if (!original) continue;
      value.x = Math.max(0, Math.min(100, original.x + dx));
      value.y = Math.max(0, Math.min(100, original.y + dy));
    }
    renderFloatingItems();
  };
  const finish = () => {
    document.removeEventListener('pointermove', move);
    document.removeEventListener('pointerup', finish);
    focusSelectedFloatingItem();
    scheduleSave();
  };
  document.addEventListener('pointermove', move);
  document.addEventListener('pointerup', finish, { once: true });
}

function addFloatingItem(kind, x = 50, y = 50) {
  if (readOnly || (kind !== 'node' && kind !== 'note')) return;
  const item = {
    id: `nfprogress-floating-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    kind,
    text: kind === 'note' ? floatingNoteName : floatingNodeName,
    x: Math.max(0, Math.min(100, x)),
    y: Math.max(0, Math.min(100, y)),
    parentId: null,
  };
  floatingItems.push(item);
  selectedFloatingItemId = item.id;
  renderFloatingItems();
  focusSelectedFloatingItem();
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
  focusSelectedFloatingItem();
  scheduleSave();
}

function addFloatingChild(parent) {
  const childCount = floatingItems.filter((item) => item.parentId === parent.id).length;
  addFloatingNode(parent.id, parent.x - 15, parent.y + childCount * 8);
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
        panel.classList.remove('open');
      });
      resultsElement.appendChild(button);
    }
  };
  const toggle = () => {
    const controlBounds = control.getBoundingClientRect();
    const editorBounds = mind.el.getBoundingClientRect();
    panel.style.left = `${controlBounds.right - editorBounds.left + 8}px`;
    panel.style.top = `${controlBounds.top - editorBounds.top - 7}px`;
    panel.style.maxWidth = `${Math.max(220, editorBounds.right - controlBounds.right - 24)}px`;
    panel.classList.toggle('open');
    if (panel.classList.contains('open')) input.focus();
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
  document.addEventListener('pointerdown', (event) => {
    if (!panel.contains(event.target) && !control.contains(event.target)) {
      panel.classList.remove('open');
    }
  });
  document.addEventListener('keydown', (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'f') {
      event.preventDefault();
      if (!panel.classList.contains('open')) {
        const controlBounds = control.getBoundingClientRect();
        const editorBounds = mind.el.getBoundingClientRect();
        panel.style.left = `${controlBounds.right - editorBounds.left + 8}px`;
        panel.style.top = `${controlBounds.top - editorBounds.top - 7}px`;
        panel.style.maxWidth = `${Math.max(220, editorBounds.right - controlBounds.right - 24)}px`;
        panel.classList.add('open');
      }
      input.focus();
    }
  });
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
      bridge.exportFile(format, serializeMap(true));
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
  floatingMenuLabels = {
    addChild: payload.addChildLabel,
    addSibling: payload.addSiblingLabel,
    addNote: payload.addNearbyNoteLabel,
    edit: payload.editLabel,
    link: payload.linkLabel,
    remove: payload.removeLabel,
  };
  const locale = localePacks[payload.locale] || en;
  const options = {
    el: '#map',
    direction: MindElixir.SIDE,
    contextMenu: readOnly ? false : {
      focus: true,
      link: true,
      locale,
      extend: [{
        name: payload.linkFloatingLabel,
        onclick: beginMapNodeLink,
      }],
    },
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
  floatingLinks = normalizedFloatingLinks(payload.data?.nfprogressFloatingLinks);
  renderFloatingItems();
  installFloatingItemControls(payload);
  installBranchFocusControl(locale, payload.emptyStageMapText);
  installSearchControl(payload);
  installFloatingLinkTargets();
  protectReadOnlyStageNodeMutations();
  protectReadOnlyStageConnections();
  markReadOnlyStageNodes();
  mind.bus.addListener('linkDiv', markReadOnlyStageNodes);
  for (const eventName of ['linkDiv', 'move', 'scale', 'expandNode']) {
    mind.bus.addListener(eventName, () => window.requestAnimationFrame(drawFloatingLinks));
  }

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
