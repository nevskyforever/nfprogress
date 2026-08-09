import MindElixir from './MindElixir.js';
import { de, en, es, fr, pt, ru } from './i18n.js';

const localePacks = { de, en, es, fr, pt_BR: pt, ru };
const loadingElement = document.getElementById('loading');

let mind = null;
let readOnly = false;
let saveTimer = null;
let suppressExternalSync = false;
const nativeEvents = [];
let floatingNodeName = 'Свободный узел';
let floatingNoteName = 'Новая заметка';

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
  return mind.getDataString();
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
    element.addEventListener('click', () => addNativeFreeElement(control.kind));
    element.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        addNativeFreeElement(control.kind);
      }
    });
    toolbar.appendChild(element);
  }
}

function migrateFloatingData(data) {
  if (!data || typeof data !== 'object') return data;
  data.freeNodes = Array.isArray(data.freeNodes) ? data.freeNodes : [];
  const legacyItems = normalizedFloatingItems(data.nfprogressFloatingItems);
  if (legacyItems.length && !data.freeNodes.length) {
    const nodes = new Map(legacyItems.map((item) => [item.id, {
      id: item.id,
      topic: item.text,
      children: [],
      nfprogressNote: item.kind === 'note',
      position: { x: item.x * 10, y: item.y * 7 },
    }]));
    for (const item of legacyItems) {
      if (item.parentId && nodes.has(item.parentId) && item.kind === 'node') {
        nodes.get(item.parentId).children.push(nodes.get(item.id));
      } else {
        data.freeNodes.push(nodes.get(item.id));
      }
    }
  }
  if (Array.isArray(data.nfprogressFloatingLinks)) {
    data.arrows = Array.isArray(data.arrows) ? data.arrows : [];
    for (const link of normalizedFloatingLinks(data.nfprogressFloatingLinks)) {
      if (!data.arrows.some((arrow) => arrow.id === link.id)) {
        data.arrows.push({
          id: link.id,
          label: '',
          from: link.from,
          to: link.to,
        });
      }
    }
  }
  delete data.nfprogressFloatingItems;
  delete data.nfprogressFloatingLinks;
  return data;
}

function nextFreePosition() {
  const index = mind.freeNodes.length;
  return {
    x: Math.max(160, mind.nodes.offsetWidth / 2 + 180 + index * 24),
    y: Math.max(100, mind.nodes.offsetHeight / 2 - 80 + index * 44),
  };
}

function addNativeFreeElement(kind, position = null) {
  if (readOnly || (kind !== 'node' && kind !== 'note')) return null;
  const node = {
    id: `nfprogress-free-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    topic: kind === 'note' ? floatingNoteName : floatingNodeName,
    children: [],
    position: position || nextFreePosition(),
    nfprogressFreeRoot: true,
  };
  if (kind === 'note') node.nfprogressNote = true;
  mind.freeNodes.push(node);
  mind.rebuildParents();
  mind.renderFreeNodes();
  mind.linkDiv();
  const element = mind.findEle(node.id);
  mind.selectNode(element, true);
  mind.beginEdit(element);
  mind.bus.fire('operation', { name: 'addFreeNode', obj: node });
  return node;
}

function installNativeFreeBehavior() {
  const originalAddChild = mind.addChild.bind(mind);
  const originalInsertSibling = mind.insertSibling.bind(mind);
  const originalInsertParent = mind.insertParent.bind(mind);
  mind.addChild = function addChildWithNotes(node, data) {
    const target = node || this.currentNode;
    if (!node && !data && target?.nodeObj?.nfprogressNote) {
      const source = target.nodeObj;
      return addNativeFreeElement('note', {
        x: source.position.x + 40,
        y: source.position.y + 45,
      });
    }
    return originalAddChild(node, data);
  };
  mind.insertSibling = function insertFreeSibling(direction, data) {
    const source = this.currentNode?.nodeObj;
    if (!data && source?.nfprogressFreeRoot) {
      return addNativeFreeElement(source.nfprogressNote ? 'note' : 'node', {
        x: source.position.x + 40,
        y: source.position.y + 45,
      });
    }
    return originalInsertSibling(direction, data);
  };
  mind.insertParent = function insertFreeParent(node, data) {
    const target = node || this.currentNode;
    const source = target?.nodeObj;
    if (!data && source?.nfprogressFreeRoot) {
      const parent = {
        id: `nfprogress-free-${Date.now()}-${Math.random().toString(16).slice(2)}`,
        topic: floatingNodeName,
        children: [source],
        position: source.position,
        nfprogressFreeRoot: true,
      };
      source.nfprogressFreeRoot = false;
      delete source.position;
      const index = this.freeNodes.indexOf(source);
      this.freeNodes.splice(index, 1, parent);
      this.rebuildParents();
      this.renderFreeNodes();
      this.linkDiv();
      const element = this.findEle(parent.id);
      this.selectNode(element, true);
      this.beginEdit(element);
      this.bus.fire('operation', { name: 'insertFreeParent', obj: parent });
      return parent;
    }
    return originalInsertParent(node, data);
  };

  mind.container.addEventListener('pointerdown', (event) => {
    if (
      readOnly || event.button !== 0 || event.target.closest?.('#input-box')
      || mind.container.querySelector('.tips')
    ) return;
    const topic = event.target.closest?.('me-tpc');
    if (!topic?.nodeObj?.nfprogressFreeRoot) return;
    event.preventDefault();
    event.stopPropagation();
    mind.selectNode(topic);
    const node = topic.nodeObj;
    const main = topic.closest('me-main.nfprogress-free-main');
    const start = { x: event.clientX, y: event.clientY };
    const origin = { ...node.position };
    let moved = false;
    let dropTarget = null;
    const clearDropTarget = () => {
      dropTarget?.classList.remove('nfprogress-drop-target');
      dropTarget = null;
    };
    const move = (moveEvent) => {
      const dx = (moveEvent.clientX - start.x) / mind.scaleVal;
      const dy = (moveEvent.clientY - start.y) / mind.scaleVal;
      moved = moved || Math.abs(dx) > 2 || Math.abs(dy) > 2;
      node.position = { x: origin.x + dx, y: origin.y + dy };
      main.style.left = `${node.position.x}px`;
      main.style.top = `${node.position.y}px`;
      clearDropTarget();
      main.style.visibility = 'hidden';
      const hit = document.elementFromPoint(moveEvent.clientX, moveEvent.clientY);
      main.style.visibility = '';
      const eventTarget = moveEvent.target.closest?.('me-tpc');
      const target = eventTarget?.nodeObj !== node
        ? eventTarget
        : hit?.closest?.('me-tpc');
      if (
        target
        && !target.nodeObj.nfprogressFreeRoot
        && !target.nodeObj.nfprogressNote
        && !target.nodeObj.nfprogressReadOnly
      ) {
        dropTarget = target;
        dropTarget.classList.add('nfprogress-drop-target');
      }
      mind.linkDiv();
    };
    const finish = (upEvent) => {
      document.removeEventListener('pointermove', move);
      document.removeEventListener('pointerup', finish);
      const target = dropTarget?.nodeObj;
      clearDropTarget();
      if (moved && target && attachFreeBranch(node, target)) return;
      if (moved) mind.bus.fire('operation', { name: 'moveFreeNode', obj: node });
    };
    document.addEventListener('pointermove', move);
    document.addEventListener('pointerup', finish, { once: true });
  }, true);
}

function canDetachBranch(node) {
  return Boolean(
    node?.parent
    && !node.parent.nfprogressFreeContainer
    && !node.nfprogressNote
    && !node.nfprogressReadOnly
    && !node.nfprogressStageId
  );
}

function canAttachFreeBranch(node) {
  return Boolean(
    node?.nfprogressFreeRoot
    && !node.nfprogressNote
    && !node.nfprogressReadOnly
  );
}

function closeContextMenu() {
  const contextMenu = mind?.container.querySelector('.context-menu');
  if (contextMenu) contextMenu.hidden = true;
}

function branchPosition(topic) {
  const wrapperBounds = topic.closest('me-wrapper').getBoundingClientRect();
  const nodesBounds = mind.nodes.getBoundingClientRect();
  return {
    x: (wrapperBounds.left - nodesBounds.left) / mind.scaleVal,
    y: (wrapperBounds.top - nodesBounds.top) / mind.scaleVal,
  };
}

function updateSummariesAfterDetach(node, parent, detachedIndex) {
  for (const summary of mind.summaries || []) {
    if (summary.parent !== parent.id) continue;
    if (summary.start === detachedIndex && summary.end === detachedIndex) {
      summary.parent = node.id;
      summary.start = 0;
      summary.end = 0;
      summary.nfprogressFreeSelf = true;
    } else if (detachedIndex < summary.start) {
      summary.start -= 1;
      summary.end -= 1;
    } else if (detachedIndex <= summary.end) {
      summary.end -= 1;
    }
  }
}

function detachBranch(topic, position = null) {
  const node = topic?.nodeObj;
  if (!canDetachBranch(node)) return;
  const parent = node.parent;
  const detachedIndex = parent.children.indexOf(node);
  if (detachedIndex < 0) return;

  const freePosition = position || branchPosition(topic);
  parent.children.splice(detachedIndex, 1);
  node.position = freePosition;
  node.nfprogressFreeRoot = true;
  updateSummariesAfterDetach(node, parent, detachedIndex);
  mind.freeNodes.push(node);
  closeContextMenu();
  mind.refresh();
  const detachedTopic = mind.findEle(node.id);
  if (detachedTopic) mind.selectNode(detachedTopic, true);
  mind.bus.fire('operation', { name: 'detachBranch', obj: node });
}

function detachSelectedBranch() {
  detachBranch(mind?.currentNode);
}

function attachFreeBranch(source, target) {
  if (
    !canAttachFreeBranch(source)
    || !target
    || target.nfprogressFreeRoot
    || target.nfprogressNote
    || target.nfprogressReadOnly
  ) return false;

  const sourceIndex = mind.freeNodes.indexOf(source);
  if (sourceIndex < 0) return false;
  const targetIndex = target.children?.length || 0;
  mind.freeNodes.splice(sourceIndex, 1);
  target.children = target.children || [];
  target.children.push(source);
  delete source.position;
  delete source.nfprogressFreeRoot;
  for (const summary of mind.summaries || []) {
    if (summary.parent === source.id && summary.nfprogressFreeSelf) {
      summary.parent = target.id;
      summary.start = targetIndex;
      summary.end = targetIndex;
      delete summary.nfprogressFreeSelf;
    }
  }
  mind.refresh();
  const attachedTopic = mind.findEle(source.id);
  if (attachedTopic) mind.selectNode(attachedTopic, true);
  mind.bus.fire('operation', { name: 'attachBranch', obj: source });
  return true;
}

function beginAttachFreeBranch(targetPrompt) {
  const source = mind?.currentNode?.nodeObj;
  if (!canAttachFreeBranch(source)) return;
  closeContextMenu();
  const tips = document.createElement('div');
  tips.className = 'tips';
  tips.textContent = targetPrompt;
  mind.container.appendChild(tips);
  mind.map.addEventListener('click', (event) => {
    event.preventDefault();
    event.stopPropagation();
    tips.remove();
    const targetTopic = event.target.closest?.('me-tpc');
    if (targetTopic) attachFreeBranch(source, targetTopic.nodeObj);
  }, { once: true });
}

function installBranchTransferBehavior() {
  const detachItem = document.getElementById('nfprogress-detach-branch');
  const attachItem = document.getElementById('nfprogress-attach-branch');
  mind.bus.addListener('showContextMenu', () => {
    const node = mind.currentNode?.nodeObj;
    detachItem?.classList.toggle('disabled', !canDetachBranch(node));
    attachItem?.classList.toggle('disabled', !canAttachFreeBranch(node));
  });
}

function dropPosition(event, topic) {
  const nodesBounds = mind.nodes.getBoundingClientRect();
  const wrapperBounds = topic.closest('me-wrapper').getBoundingClientRect();
  return {
    x: (event.clientX - nodesBounds.left - wrapperBounds.width / 2) / mind.scaleVal,
    y: (event.clientY - nodesBounds.top - wrapperBounds.height / 2) / mind.scaleVal,
  };
}

function installBranchDragTransferBehavior() {
  let draggedTopic = null;
  let pointerId = null;
  let start = null;
  let moved = false;

  const clear = () => {
    mind.container.classList.remove('nfprogress-detach-drop');
    draggedTopic = null;
    pointerId = null;
    start = null;
    moved = false;
  };
  const move = (event) => {
    if (!draggedTopic || event.pointerId !== pointerId) return;
    const distance = Math.hypot(
      event.clientX - start.x,
      event.clientY - start.y,
    );
    moved = moved || distance > 5;
    if (!moved) return;
    const hit = document.elementFromPoint(event.clientX, event.clientY);
    const targetTopic = hit?.closest?.('me-tpc');
    const containerBounds = mind.container.getBoundingClientRect();
    const insideContainer = (
      event.clientX >= containerBounds.left
      && event.clientX <= containerBounds.right
      && event.clientY >= containerBounds.top
      && event.clientY <= containerBounds.bottom
    );
    const overControls = Boolean(hit?.closest?.(
      '.mind-elixir-toolbar, .context-menu, .nfprogress-search-panel',
    ));
    mind.container.classList.toggle(
      'nfprogress-detach-drop',
      insideContainer && !targetTopic && !overControls,
    );
  };
  const finish = (event) => {
    if (!draggedTopic || event.pointerId !== pointerId) return;
    const topic = draggedTopic;
    const hit = document.elementFromPoint(event.clientX, event.clientY);
    const containerBounds = mind.container.getBoundingClientRect();
    const insideContainer = (
      event.clientX >= containerBounds.left
      && event.clientX <= containerBounds.right
      && event.clientY >= containerBounds.top
      && event.clientY <= containerBounds.bottom
    );
    const shouldDetach = Boolean(
      moved
      && insideContainer
      && !hit?.closest?.('me-tpc')
      && !hit?.closest?.(
        '.mind-elixir-toolbar, .context-menu, .nfprogress-search-panel',
      )
    );
    const position = shouldDetach ? dropPosition(event, topic) : null;
    document.removeEventListener('pointermove', move);
    document.removeEventListener('pointerup', finish);
    clear();
    if (shouldDetach) detachBranch(topic, position);
  };

  mind.container.addEventListener('pointerdown', (event) => {
    if (
      readOnly || event.button !== 0 || pointerId !== null
      || event.ctrlKey || event.metaKey
    ) return;
    const topic = event.target.closest?.('me-tpc');
    if (!topic || !canDetachBranch(topic.nodeObj)) return;
    if ((mind.currentNodes || []).length > 1 && mind.currentNodes.includes(topic)) {
      return;
    }
    draggedTopic = topic;
    pointerId = event.pointerId;
    start = { x: event.clientX, y: event.clientY };
    document.addEventListener('pointermove', move);
    document.addEventListener('pointerup', finish);
  }, true);
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
  const targetData = findAnyNodeData(nodeId);
  if (!targetData) return;
  const ancestors = [];
  for (let parent = targetData.parent; parent; parent = parent.parent) {
    if (!parent.nfprogressFreeContainer) ancestors.push(parent);
  }
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

function findAnyNodeData(nodeId) {
  const regular = findNodeData(mind.nodeData, nodeId);
  if (regular) return regular;
  for (const freeNode of mind.freeNodes || []) {
    const found = findNodeData(freeNode, nodeId);
    if (found) return found;
  }
  return null;
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
    for (const freeNode of mind.freeNodes || []) collectSearchResults(freeNode, query, results);
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
      const resultNode = findAnyNodeData(result.id);
      button.textContent = resultNode?.nfprogressNote ? `📝 ${result.text}` : result.text;
      button.addEventListener('click', () => {
        revealMapNode(result.id);
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
  if (readOnly || suppressExternalSync) {
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

function updateNodeNote(nodeId, text) {
  if (!mind || typeof nodeId !== 'string' || typeof text !== 'string') return false;
  const node = findAnyNodeData(nodeId);
  if (!node?.nfprogressNote) return false;
  suppressExternalSync = true;
  try {
    node.topic = text;
    const element = mind.findEle(nodeId);
    if (element?.text) element.text.textContent = text;
    mind.linkDiv();
    return true;
  } finally {
    suppressExternalSync = false;
  }
}

function removeNodeNote(nodeId) {
  if (!mind || typeof nodeId !== 'string') return false;
  const node = findAnyNodeData(nodeId);
  const element = mind.findEle(nodeId);
  if (!node?.nfprogressNote || !element) return false;
  suppressExternalSync = true;
  try {
    mind.removeNodes([element]);
    return true;
  } finally {
    suppressExternalSync = false;
  }
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
  floatingNodeName = payload.floatingNodeName;
  floatingNoteName = payload.floatingNoteName;
  const locale = localePacks[payload.locale] || en;
  const contextMenu = readOnly ? false : {
    focus: true,
    link: true,
    locale,
    extend: [
      {
        id: 'nfprogress-detach-branch',
        name: payload.detachBranchLabel,
        onclick: detachSelectedBranch,
      },
      {
        id: 'nfprogress-attach-branch',
        name: payload.attachBranchLabel,
        onclick: () => beginAttachFreeBranch(payload.attachTargetPrompt),
      },
    ],
  };
  const options = {
    el: '#map',
    direction: MindElixir.SIDE,
    contextMenu,
    toolBar: true,
    keypress: !readOnly,
    draggable: !readOnly,
    editable: !readOnly,
    newTopicName: payload.newTopicName,
    allowUndo: true,
    alignment: 'nodes',
  };

  mind = new MindElixir(options);
  const initialData = migrateFloatingData(
    payload.data || MindElixir.new(payload.rootTopic),
  );
  mind.init(initialData);
  installNativeFreeBehavior();
  installBranchTransferBehavior();
  installBranchDragTransferBehavior();
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
  addFloatingItem(kind) {
    return addNativeFreeElement(kind);
  },
  requestExport,
  focusNode(nodeId) {
    if (!mind || typeof nodeId !== 'string') return false;
    revealMapNode(nodeId);
    return Boolean(findAnyNodeData(nodeId));
  },
  updateNodeNote,
  removeNodeNote,
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
