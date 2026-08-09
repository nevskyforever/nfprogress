(() => {
  'use strict';

  const nativeEvents = [];
  const state = {
    notes: new Map(),
    labels: {},
    locale: 'ru',
    readOnly: false,
    archiveMode: false,
    query: '',
    selectedTag: null,
    hasStages: false,
    stages: [],
    includeStageNotes: false,
    selectedStageId: null,
    sortByStage: false,
    creatingNote: false,
    activeNoteId: null,
    grids: [],
    saveTimers: new Map(),
    pendingPatches: new Map(),
    resizeObserver: null,
    layoutFrame: null,
    viewportTimer: null,
    lastRevision: 0,
  };

  const appElement = document.getElementById('app');
  const skipLink = document.getElementById('skip-link');
  const notesActions = document.getElementById('notes-actions');
  const newNoteButton = document.getElementById('new-note');
  const searchInput = document.getElementById('search-input');
  const tagFilterButton = document.getElementById('tag-filter-button');
  const tagFilterMenu = document.getElementById('tag-filter-menu');
  const stageNotesToggle = document.getElementById('stage-notes-toggle');
  const stageFilterWrap = document.getElementById('stage-filter-wrap');
  const stageFilterButton = document.getElementById('stage-filter-button');
  const stageFilterMenu = document.getElementById('stage-filter-menu');
  const stageSortToggle = document.getElementById('stage-sort-toggle');
  const archiveToggle = document.getElementById('archive-toggle');
  const readOnlyBanner = document.getElementById('read-only-banner');
  const pinnedSection = document.getElementById('pinned-section');
  const otherSection = document.getElementById('other-section');
  const pinnedHeading = document.getElementById('pinned-heading');
  const otherHeading = document.getElementById('other-heading');
  const pinnedGridElement = document.getElementById('pinned-grid');
  const otherGridElement = document.getElementById('other-grid');
  const emptyState = document.getElementById('empty-state');
  const liveStatus = document.getElementById('live-status');
  const errorToast = document.getElementById('error-toast');
  const noteEditorLayer = document.getElementById('note-editor-layer');
  const noteEditorDialog = document.getElementById('note-editor-dialog');
  const noteEditorHost = document.getElementById('note-editor-host');

  const icons = {
    drag: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="8" cy="7" r="1" fill="currentColor" stroke="none"/><circle cx="16" cy="7" r="1" fill="currentColor" stroke="none"/><circle cx="8" cy="12" r="1" fill="currentColor" stroke="none"/><circle cx="16" cy="12" r="1" fill="currentColor" stroke="none"/><circle cx="8" cy="17" r="1" fill="currentColor" stroke="none"/><circle cx="16" cy="17" r="1" fill="currentColor" stroke="none"/></svg>',
    pin: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m8 3 8 0-1 6 3 3v2H6v-2l3-3zM12 14v7"/></svg>',
    pinFilled: '<svg viewBox="0 0 24 24" aria-hidden="true"><path class="pin-fill" d="M8 3h8l-1 6 3 3v2H6v-2l3-3-1-6Z" fill="currentColor"/><path d="M12 14v7"/></svg>',
    archive: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16v13H4zM3 3h18v4H3zM9 11h6"/></svg>',
    restore: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16v13H4zM3 3h18v4H3zM12 17V10M8.5 13.5 12 10l3.5 3.5"/></svg>',
    trash: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3M7 7l1 14h8l1-14M10 11v6M14 11v6"/></svg>',
    checklist: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 7 2 2 3-4M11 7h10M3 15l2 2 3-4M11 15h10"/></svg>',
    list: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 6h13M8 12h13M8 18h13M3 6h1M3 12h1M3 18h1"/></svg>',
    ordered: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 6h12M9 12h12M9 18h12M3 5h2v3M3 11h2l-2 3h2M3 17h2v3H3"/></svg>',
    link: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 13a5 5 0 0 0 7 0l2-2a5 5 0 0 0-7-7l-1 1M14 11a5 5 0 0 0-7 0l-2 2a5 5 0 0 0 7 7l1-1"/></svg>',
    map: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="5" cy="12" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="m7.5 11 8-4M7.5 13l8 4"/></svg>',
    palette: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3a9 9 0 1 0 0 18h1.5a2 2 0 0 0 0-4H12a1.8 1.8 0 0 1 0-3.6h2.7A6.3 6.3 0 0 0 21 7.1 4.1 4.1 0 0 0 16.9 3z"/><circle cx="7.5" cy="9" r="1" fill="currentColor" stroke="none"/><circle cx="10.5" cy="6.5" r="1" fill="currentColor" stroke="none"/><circle cx="15" cy="6.5" r="1" fill="currentColor" stroke="none"/></svg>',
  };

  function emit(type, values = {}) {
    nativeEvents.push({ type, ...values });
  }

  function setLiveStatus(message) {
    liveStatus.textContent = '';
    window.requestAnimationFrame(() => { liveStatus.textContent = message || ''; });
  }

  function applyTheme(theme) {
    if (!theme || typeof theme !== 'object') return;
    const root = document.documentElement;
    const variables = {
      window: '--window',
      surface: '--surface',
      surfaceAlt: '--surface-alt',
      text: '--text',
      muted: '--muted',
      border: '--border',
      accent: '--accent',
      accentText: '--accent-text',
    };
    for (const [key, variable] of Object.entries(variables)) {
      if (typeof theme[key] === 'string') root.style.setProperty(variable, theme[key]);
    }
    root.style.colorScheme = theme.dark ? 'dark' : 'light';
    document.body.classList.toggle('dark-theme', Boolean(theme.dark));
  }

  function makeButton(className, label, icon = '') {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = className;
    button.title = label;
    button.setAttribute('aria-label', label);
    if (icon) button.innerHTML = icon;
    return button;
  }

  function normalizeTag(tag) {
    return String(tag || '').trim().replace(/^#+/, '').trim();
  }

  function normalizedTags(value) {
    const result = [];
    const seen = new Set();
    for (const rawTag of Array.isArray(value) ? value : []) {
      const tag = normalizeTag(rawTag).slice(0, 64);
      const key = tag.toLocaleLowerCase();
      if (!tag || key === 'карта' || seen.has(key)) continue;
      seen.add(key);
      result.push(tag);
    }
    return result;
  }

  function safeHref(value) {
    try {
      const url = new URL(value);
      return ['http:', 'https:', 'mailto:'].includes(url.protocol) ? url.href : null;
    } catch (_error) {
      return null;
    }
  }

  const allowedTags = new Set([
    'A', 'B', 'BR', 'DIV', 'EM', 'I', 'LI', 'OL', 'P', 'S', 'STRIKE',
    'STRONG', 'U', 'UL',
  ]);

  function sanitizeNode(source, destination) {
    for (const child of source.childNodes) {
      if (child.nodeType === Node.TEXT_NODE) {
        destination.appendChild(document.createTextNode(child.data));
        continue;
      }
      if (child.nodeType !== Node.ELEMENT_NODE) continue;
      if (!allowedTags.has(child.tagName)) {
        sanitizeNode(child, destination);
        continue;
      }
      if (child.tagName === 'A') {
        const href = safeHref(child.getAttribute('href'));
        if (!href) {
          sanitizeNode(child, destination);
          continue;
        }
        const link = document.createElement('a');
        link.href = href;
        link.rel = 'noopener noreferrer';
        sanitizeNode(child, link);
        destination.appendChild(link);
        continue;
      }
      const clean = document.createElement(child.tagName.toLowerCase());
      sanitizeNode(child, clean);
      destination.appendChild(clean);
    }
  }

  function sanitizedEditableHtml(element) {
    const container = document.createElement('div');
    sanitizeNode(element, container);
    return container.innerHTML.slice(0, 300000);
  }

  function plainContent(note) {
    if (note.source_type === 'mindmap') return String(note.content || '');
    const container = document.createElement('div');
    container.innerHTML = String(note.content || '');
    return container.textContent || '';
  }

  function noteInStageScope(note) {
    const isStageNote = Boolean(note.stage_name);
    if (isStageNote && !state.includeStageNotes) return false;
    if (state.selectedStageId) {
      return isStageNote && note.owner_id === state.selectedStageId;
    }
    return true;
  }

  function noteMatches(note) {
    if (!noteInStageScope(note)) return false;
    if (Boolean(note.archived) !== state.archiveMode) return false;
    if (state.selectedTag) {
      const selected = state.selectedTag.toLocaleLowerCase();
      const tags = [...(note.tags || []), ...(note.system_tags || [])]
        .map(tag => String(tag).toLocaleLowerCase());
      if (!tags.includes(selected)) return false;
    }
    const query = state.query.trim().toLocaleLowerCase();
    if (!query) return true;
    const checklistText = (note.checklist || []).map(item => item.text).join(' ');
    const searchable = [
      note.title,
      note.display_title,
      plainContent(note),
      checklistText,
      ...(note.tags || []).map(tag => `#${tag}`),
      ...(note.system_tags || []).map(tag => `#${tag}`),
      note.stage_name || '',
      note.source_type === 'mindmap' ? '#карта карта' : '',
    ].join(' ').toLocaleLowerCase();
    return searchable.includes(query);
  }

  function compareNotes(left, right) {
    if (state.sortByStage) {
      const stageOrder = Number(left.owner_order || 0) - Number(right.owner_order || 0);
      if (stageOrder) return stageOrder;
    }
    const manualOrder = Number(left.sort_order || 0) - Number(right.sort_order || 0);
    if (manualOrder) return manualOrder;
    const createdOrder = String(left.created_at || '').localeCompare(
      String(right.created_at || ''),
    );
    if (createdOrder) return createdOrder;
    const ownerOrder = Number(left.owner_order || 0) - Number(right.owner_order || 0);
    if (ownerOrder) return ownerOrder;
    return String(left.id).localeCompare(String(right.id));
  }

  function updateLocalNote(noteId, patch) {
    const note = state.notes.get(noteId);
    if (!note) return;
    Object.assign(note, patch);
  }

  function queuePatch(noteId, patch, immediate = false) {
    if (state.readOnly) return;
    const pending = state.pendingPatches.get(noteId) || {};
    Object.assign(pending, patch);
    state.pendingPatches.set(noteId, pending);
    window.clearTimeout(state.saveTimers.get(noteId));
    setLiveStatus(state.labels.savePending);
    if (immediate) flushPendingPatch(noteId);
    else state.saveTimers.set(
      noteId,
      window.setTimeout(() => flushPendingPatch(noteId), 450),
    );
  }

  function flushPendingPatch(noteId) {
    const queued = state.pendingPatches.get(noteId);
    if (!queued) return;
    window.clearTimeout(state.saveTimers.get(noteId));
    state.pendingPatches.delete(noteId);
    state.saveTimers.delete(noteId);
    emit('updateNote', { id: noteId, patch: queued });
  }

  function flushAllPendingPatches() {
    for (const noteId of [...state.pendingPatches.keys()]) {
      flushPendingPatch(noteId);
    }
  }

  function responsiveColumnCount(containerWidth) {
    if (!containerWidth || containerWidth < 620) return 1;
    return Math.max(1, Math.floor(containerWidth / 270));
  }

  function applyResponsiveItemWidths() {
    for (const gridElement of [pinnedGridElement, otherGridElement]) {
      const containerWidth = gridElement.clientWidth || 0;
      const columns = responsiveColumnCount(containerWidth);
      for (const item of gridElement.querySelectorAll('.note-item')) {
        const itemWidth = containerWidth > 0
          ? `${Math.floor(containerWidth / columns)}px`
          : '100%';
        item.style.setProperty('width', itemWidth, 'important');
      }
    }
  }

  function refreshResponsiveLayout() {
    applyResponsiveItemWidths();
    for (const grid of state.grids) grid.refreshItems().layout();
  }

  function scheduleLayout() {
    if (state.layoutFrame !== null) return;
    state.layoutFrame = window.requestAnimationFrame(() => {
      state.layoutFrame = null;
      refreshResponsiveLayout();
    });
  }

  function installPasteAsPlainText(element) {
    element.addEventListener('paste', event => {
      if (!event.clipboardData) return;
      event.preventDefault();
      const text = event.clipboardData.getData('text/plain') || '';
      document.execCommand('insertText', false, text);
    });
    element.addEventListener('dragover', event => event.preventDefault());
    element.addEventListener('drop', event => {
      event.preventDefault();
      const text = event.dataTransfer?.getData('text/plain') || '';
      element.focus();
      document.execCommand('insertText', false, text);
    });
  }

  function applyEditorCommand(command, contentElement) {
    contentElement.focus();
    if (command === 'createLink') {
      let href = window.prompt(state.labels.linkPrompt, 'https://');
      if (!href) return false;
      if (!/^[a-z][a-z0-9+.-]*:/i.test(href)) href = `https://${href}`;
      if (!safeHref(href)) return false;
      document.execCommand(command, false, href);
    } else {
      document.execCommand(command, false, null);
    }
    contentElement.dispatchEvent(new Event('input', { bubbles: true }));
    return true;
  }

  function selectEditableContents(contentElement) {
    contentElement.focus();
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(contentElement);
    selection?.removeAllRanges();
    selection?.addRange(range);
  }

  function installEditorShortcuts(contentElement) {
    contentElement.addEventListener('keydown', event => {
      if (event.defaultPrevented || event.isComposing) return;
      const key = event.key.toLocaleLowerCase();
      const primary = event.ctrlKey || event.metaKey;
      const eventCode = event.code || '';
      const digit = eventCode.startsWith('Digit') ? eventCode.slice(5) : '';
      const shortcutKey = eventCode.startsWith('Key')
        ? eventCode.slice(3).toLocaleLowerCase()
        : key;
      let command = null;

      if (primary && !event.altKey) {
        if (!event.shiftKey && shortcutKey === 'a') command = 'selectAll';
        else if (!event.shiftKey && shortcutKey === 'b') command = 'bold';
        else if (!event.shiftKey && shortcutKey === 'i') command = 'italic';
        else if (!event.shiftKey && shortcutKey === 'u') command = 'underline';
        else if (!event.shiftKey && shortcutKey === 'k') command = 'createLink';
        else if (!event.shiftKey && shortcutKey === 'z') command = 'undo';
        else if (
          (!event.shiftKey && shortcutKey === 'y')
          || (event.shiftKey && shortcutKey === 'z')
        ) {
          command = 'redo';
        } else if (event.shiftKey && shortcutKey === 'x') command = 'strikeThrough';
        else if (event.shiftKey && (key === '7' || digit === '7')) {
          command = 'insertOrderedList';
        } else if (event.shiftKey && (key === '8' || digit === '8')) {
          command = 'insertUnorderedList';
        }
      } else if (event.altKey && event.shiftKey && (key === '5' || digit === '5')) {
        command = 'strikeThrough';
      }

      if (!command) return;
      event.preventDefault();
      if (command === 'selectAll') selectEditableContents(contentElement);
      else applyEditorCommand(command, contentElement);
    });
  }

  function formatButton(
    label,
    icon,
    command,
    contentElement,
    readOnly = false,
    ariaShortcuts = '',
  ) {
    const button = makeButton('format-button', label, icon);
    button.disabled = readOnly;
    if (ariaShortcuts) button.setAttribute('aria-keyshortcuts', ariaShortcuts);
    button.addEventListener('pointerdown', event => event.preventDefault());
    button.addEventListener('click', () => applyEditorCommand(command, contentElement));
    return button;
  }

  function createChecklist(note, container, readOnly = false) {
    const checklist = document.createElement('div');
    checklist.className = 'checklist';
    const saveChecklist = () => {
      updateLocalNote(note.id, { checklist: note.checklist });
      queuePatch(note.id, { checklist: note.checklist });
      scheduleLayout();
    };
    for (const item of note.checklist || []) {
      const row = document.createElement('div');
      row.className = `checklist-row${item.checked ? ' checked' : ''}`;
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.checked = Boolean(item.checked);
      checkbox.disabled = readOnly;
      checkbox.setAttribute('aria-label', item.text || state.labels.checklist);
      checkbox.addEventListener('change', () => {
        item.checked = checkbox.checked;
        row.classList.toggle('checked', item.checked);
        saveChecklist();
      });
      const input = document.createElement('input');
      input.type = 'text';
      input.className = 'checklist-text';
      input.value = item.text || '';
      input.disabled = readOnly;
      input.setAttribute('aria-label', state.labels.checklist);
      input.addEventListener('input', () => {
        item.text = input.value.slice(0, 2000);
        saveChecklist();
      });
      const remove = makeButton('checklist-remove', state.labels.removeChecklistItem, '×');
      remove.disabled = readOnly;
      remove.addEventListener('click', () => {
        note.checklist = note.checklist.filter(candidate => candidate.id !== item.id);
        renderAll();
        queuePatch(note.id, { checklist: note.checklist }, true);
      });
      row.append(checkbox, input, remove);
      checklist.appendChild(row);
    }
    const add = document.createElement('button');
    add.type = 'button';
    add.className = 'add-checklist-item';
    add.textContent = `＋ ${state.labels.addChecklistItem}`;
    add.disabled = readOnly;
    add.addEventListener('click', () => {
      note.checklist = [...(note.checklist || []), {
        id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
        text: '',
        checked: false,
      }];
      renderAll();
      queuePatch(note.id, { checklist: note.checklist }, true);
      window.requestAnimationFrame(() => {
        const noteElement = [...document.querySelectorAll('.note-editor-item')]
          .find(candidate => candidate.dataset.noteId === note.id);
        const inputs = noteElement?.querySelectorAll('.checklist-text') || [];
        inputs[inputs.length - 1]?.focus();
      });
    });
    checklist.appendChild(add);
    container.appendChild(checklist);
  }

  function createTagArea(note, container, readOnly = false, editable = true) {
    const tagArea = document.createElement('div');
    tagArea.className = `tag-area${editable ? ' is-editing' : ''}`;
    const tagList = document.createElement('div');
    tagList.className = 'tag-list';

    const activateTagFilter = tag => {
      if (editable) {
        flushPendingPatch(note.id);
        state.activeNoteId = null;
      }
      selectTag(tag);
    };

    const createFilterChip = (tag, system = false) => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = `tag-chip${system ? ' system-tag' : ''}`;
      chip.textContent = `#${tag}`;
      chip.addEventListener('click', () => activateTagFilter(tag));
      return chip;
    };

    const saveTags = tags => {
      const normalized = normalizedTags(tags);
      if (JSON.stringify(normalized) === JSON.stringify(note.tags || [])) return;
      note.tags = normalized;
      updateLocalNote(note.id, { tags: normalized });
      queuePatch(note.id, { tags: normalized });
      renderTagList();
      rebuildTagMenu();
    };

    const renderTagList = () => {
      tagList.replaceChildren();
      for (const systemTag of note.system_tags || []) {
        tagList.appendChild(createFilterChip(systemTag, true));
      }
      for (const tag of note.tags || []) {
        if (!editable || readOnly) {
          tagList.appendChild(createFilterChip(tag));
          continue;
        }
        const editableChip = document.createElement('span');
        editableChip.className = 'editable-tag-chip';
        editableChip.appendChild(createFilterChip(tag));
        const remove = document.createElement('button');
        remove.type = 'button';
        remove.className = 'tag-remove';
        remove.textContent = '×';
        remove.title = `${state.labels.removeTag}: #${tag}`;
        remove.setAttribute('aria-label', `${state.labels.removeTag}: #${tag}`);
        remove.addEventListener('click', event => {
          event.stopPropagation();
          saveTags((note.tags || []).filter(candidate => candidate !== tag));
        });
        editableChip.appendChild(remove);
        tagList.appendChild(editableChip);
      }
    };

    renderTagList();
    tagArea.appendChild(tagList);
    if (!editable || readOnly) {
      if (tagList.childElementCount) container.appendChild(tagArea);
      return;
    }

    const tagInput = document.createElement('input');
    tagInput.type = 'text';
    tagInput.className = 'tag-input';
    tagInput.placeholder = state.labels.tagsPlaceholder;
    tagInput.setAttribute('aria-label', state.labels.tagsPlaceholder);
    const resizeInput = () => {
      const measured = tagInput.value || tagInput.placeholder || '';
      const characters = Math.max(10, Math.min(36, measured.length + 2));
      tagInput.style.width = `${characters}ch`;
    };
    const addTags = rawTags => {
      saveTags([...(note.tags || []), ...rawTags]);
    };
    const commitInput = () => {
      if (tagInput.value.trim()) addTags(tagInput.value.split(','));
      tagInput.value = '';
      resizeInput();
    };
    tagInput.addEventListener('input', () => {
      const parts = tagInput.value.split(',');
      if (parts.length > 1) {
        const remainder = parts.pop();
        addTags(parts);
        tagInput.value = remainder.replace(/^\s+/, '');
      }
      resizeInput();
    });
    tagInput.addEventListener('keydown', event => {
      if (event.key === 'Enter') {
        event.preventDefault();
        commitInput();
      } else if (
        event.key === 'Backspace'
        && !tagInput.value
        && (note.tags || []).length
      ) {
        event.preventDefault();
        saveTags((note.tags || []).slice(0, -1));
      }
    });
    tagInput.addEventListener('blur', commitInput);
    resizeInput();
    tagArea.appendChild(tagInput);
    container.appendChild(tagArea);
  }

  function closeColorPalettes(except = null, restoreFocus = false) {
    let changed = false;
    for (const palette of document.querySelectorAll('.color-palette:not([hidden])')) {
      if (palette === except) continue;
      palette.hidden = true;
      palette._toggleButton?.setAttribute('aria-expanded', 'false');
      if (restoreFocus) palette._toggleButton?.focus();
      changed = true;
    }
    if (changed) scheduleLayout();
  }

  function createColorPalette(note, item, readOnly = false) {
    const palette = document.createElement('div');
    palette.className = 'color-palette';
    palette.hidden = true;
    palette.id = `color-palette-${Math.random().toString(16).slice(2)}`;
    palette.setAttribute('role', 'group');
    palette.setAttribute('aria-label', state.labels.color);

    const toggle = makeButton(
      'color-palette-toggle', state.labels.color, icons.palette,
    );
    toggle.setAttribute('aria-haspopup', 'true');
    toggle.setAttribute('aria-expanded', 'false');
    toggle.setAttribute('aria-controls', palette.id);
    toggle.disabled = readOnly;
    const updateToggleLabel = value => {
      const colorLabel = state.labels.colors?.[value] || value;
      const label = `${state.labels.color}: ${colorLabel}`;
      toggle.title = label;
      toggle.setAttribute('aria-label', label);
    };
    updateToggleLabel(note.color || 'default');
    const currentSwatch = document.createElement('span');
    currentSwatch.className = 'color-current-swatch';
    currentSwatch.dataset.noteColor = note.color || 'default';
    currentSwatch.setAttribute('aria-hidden', 'true');
    toggle.appendChild(currentSwatch);
    palette._toggleButton = toggle;

    for (const [value, label] of Object.entries(state.labels.colors || {})) {
      const swatch = makeButton(
        'color-swatch',
        `${state.labels.color}: ${label}`,
      );
      swatch.dataset.noteColor = value;
      swatch.setAttribute('aria-pressed', String(value === note.color));
      swatch.disabled = readOnly;
      swatch.addEventListener('click', () => {
        note.color = value;
        item.dataset.color = value;
        currentSwatch.dataset.noteColor = value;
        updateToggleLabel(value);
        for (const candidate of palette.querySelectorAll('.color-swatch')) {
          candidate.setAttribute(
            'aria-pressed',
            String(candidate === swatch),
          );
        }
        closeColorPalettes();
        queuePatch(note.id, { color: value }, true);
        toggle.focus();
      });
      palette.appendChild(swatch);
    }

    toggle.addEventListener('click', () => {
      const shouldOpen = palette.hidden;
      closeColorPalettes(palette);
      palette.hidden = !shouldOpen;
      toggle.setAttribute('aria-expanded', String(shouldOpen));
      scheduleLayout();
      if (shouldOpen) {
        window.requestAnimationFrame(() => {
          palette.querySelector('.color-swatch[aria-pressed="true"]')?.focus();
        });
      }
    });
    palette.addEventListener('keydown', event => {
      const swatches = [...palette.querySelectorAll('.color-swatch')];
      const index = swatches.indexOf(document.activeElement);
      let targetIndex = index;
      if (['ArrowRight', 'ArrowDown'].includes(event.key)) targetIndex = index + 1;
      if (['ArrowLeft', 'ArrowUp'].includes(event.key)) targetIndex = index - 1;
      if (event.key === 'Home') targetIndex = 0;
      if (event.key === 'End') targetIndex = swatches.length - 1;
      if (targetIndex === index || targetIndex < 0 || !swatches.length) return;
      event.preventDefault();
      swatches[(targetIndex + swatches.length) % swatches.length].focus();
    });
    return { palette, toggle };
  }

  function createChecklistPreview(note, container) {
    if (!(note.checklist || []).length) return;
    const checklist = document.createElement('div');
    checklist.className = 'checklist-preview';
    for (const checklistItem of note.checklist) {
      const row = document.createElement('div');
      row.className = `checklist-preview-row${checklistItem.checked ? ' checked' : ''}`;
      const marker = document.createElement('span');
      marker.className = 'checklist-preview-marker';
      marker.textContent = checklistItem.checked ? '☑' : '☐';
      marker.setAttribute('aria-hidden', 'true');
      const text = document.createElement('span');
      text.textContent = checklistItem.text || '';
      row.append(marker, text);
      checklist.appendChild(row);
    }
    container.appendChild(checklist);
  }

  function createNoteItem(note, editing = false) {
    const noteReadOnly = state.readOnly || Boolean(note.read_only);
    const visibleTitle = String(
      note.title || (note.source_type === 'mindmap' ? note.display_title : '') || '',
    ).trim();
    const item = document.createElement('div');
    item.className = `note-item${editing ? ' note-editor-item' : ''}`;
    item.dataset.noteId = note.id;
    item.dataset.color = note.color || 'default';
    item.dataset.source = note.source_type;
    item.dataset.order = String(note.sort_order || 0);
    item.dataset.ownerOrder = String(note.owner_order || 0);
    item.dataset.createdAt = note.created_at || '';
    if (note.stage_name) item.dataset.stageId = note.owner_id || '';

    const card = document.createElement('article');
    card.className = `note-card ${editing ? 'is-editor' : 'is-preview'}`;
    card.classList.toggle('read-only-note', noteReadOnly);
    card.setAttribute(
      'aria-label',
      visibleTitle || plainContent(note).trim().slice(0, 100) || state.labels.contentPlaceholder,
    );
    if (!editing) card.tabIndex = 0;

    const header = document.createElement('div');
    header.className = `card-header${editing ? ' editor-header' : ''}`;
    if (!editing) {
      const drag = makeButton('drag-handle', state.labels.drag, icons.drag);
      drag.disabled = noteReadOnly || Boolean(
        state.query || state.selectedTag || state.selectedStageId || state.sortByStage,
      );
      header.appendChild(drag);
    }
    let titleInput = null;
    if (editing) {
      titleInput = document.createElement('input');
      titleInput.type = 'text';
      titleInput.className = 'note-title';
      titleInput.value = note.title || '';
      titleInput.placeholder = note.source_type === 'mindmap'
        ? (note.display_title || state.labels.titlePlaceholder)
        : state.labels.titlePlaceholder;
      titleInput.maxLength = 500;
      titleInput.disabled = noteReadOnly;
      titleInput.setAttribute('aria-label', state.labels.titlePlaceholder);
      titleInput.addEventListener('input', () => {
        note.title = titleInput.value;
        queuePatch(note.id, { title: titleInput.value });
      });
      header.appendChild(titleInput);
    } else if (visibleTitle) {
      const title = document.createElement('h3');
      title.className = 'note-preview-title';
      title.textContent = visibleTitle;
      header.appendChild(title);
    }
    const pin = makeButton(
      'card-action pin-action',
      note.pinned ? state.labels.unpin : state.labels.pin,
      note.pinned ? icons.pinFilled : icons.pin,
    );
    pin.setAttribute('aria-pressed', String(Boolean(note.pinned)));
    pin.classList.toggle('is-pinned', Boolean(note.pinned));
    pin.disabled = noteReadOnly;
    pin.addEventListener('click', () => {
      note.pinned = !note.pinned;
      renderAll();
      queuePatch(note.id, { pinned: note.pinned }, true);
    });
    header.appendChild(pin);
    card.appendChild(header);

    if (note.stage_name) {
      const stageBadge = document.createElement('div');
      stageBadge.className = 'stage-badge';
      stageBadge.textContent = `${state.labels.stage}: ${note.stage_name}`;
      stageBadge.title = stageBadge.textContent;
      card.appendChild(stageBadge);
    }

    if (note.source_type === 'mindmap') {
      if (editing) {
        const textarea = document.createElement('textarea');
        textarea.className = 'map-note-content';
        textarea.value = note.content || '';
        textarea.placeholder = state.labels.contentPlaceholder;
        textarea.setAttribute('aria-label', state.labels.contentPlaceholder);
        textarea.disabled = noteReadOnly;
        textarea.addEventListener('input', () => {
          note.content = textarea.value;
          if (!note.title) {
            note.display_title = textarea.value
              .split(/\r?\n/)
              .map(line => line.trim())
              .find(Boolean)
              ?.slice(0, 100) || state.labels.mapNote;
            titleInput.placeholder = note.display_title;
            card.setAttribute('aria-label', note.display_title);
          }
          queuePatch(note.id, { content: textarea.value });
        });
        card.appendChild(textarea);
        const plainInfo = document.createElement('div');
        plainInfo.className = 'map-format-note';
        plainInfo.textContent = state.labels.plainMapNote;
        card.appendChild(plainInfo);
      } else if (note.content) {
        const preview = document.createElement('div');
        preview.className = 'note-content-preview map-content-preview';
        preview.textContent = note.content;
        card.appendChild(preview);
      }
    } else {
      if (editing) {
        const content = document.createElement('div');
        content.className = 'note-content';
        content.contentEditable = noteReadOnly ? 'false' : 'true';
        content.spellcheck = true;
        content.dataset.placeholder = state.labels.contentPlaceholder;
        content.setAttribute('role', 'textbox');
        content.setAttribute('aria-multiline', 'true');
        content.setAttribute('aria-label', state.labels.contentPlaceholder);
        content.innerHTML = note.content || '';
        installPasteAsPlainText(content);
        installEditorShortcuts(content);
        content.addEventListener('input', () => {
          const clean = sanitizedEditableHtml(content);
          note.content = clean;
          queuePatch(note.id, { content: clean });
        });
        content.addEventListener('blur', () => {
          const clean = sanitizedEditableHtml(content);
          if (content.innerHTML !== clean) content.innerHTML = clean;
        });
        content.addEventListener('click', event => {
          const link = event.target.closest?.('a');
          if (!link) return;
          event.preventDefault();
          const href = safeHref(link.href);
          if (href) emit('openExternalLink', { url: href });
        });

        const toolbar = document.createElement('div');
        toolbar.className = 'rich-toolbar';
        toolbar.setAttribute('role', 'toolbar');
        toolbar.setAttribute('aria-label', state.labels.contentPlaceholder);
        toolbar.append(
          formatButton(
            state.labels.bold, '<strong>B</strong>', 'bold', content, noteReadOnly,
            'Control+B Meta+B',
          ),
          formatButton(
            state.labels.italic, '<em>I</em>', 'italic', content, noteReadOnly,
            'Control+I Meta+I',
          ),
          formatButton(
            state.labels.strike, '<s>S</s>', 'strikeThrough', content, noteReadOnly,
            'Control+Shift+X Meta+Shift+X Alt+Shift+5',
          ),
          formatButton(
            state.labels.unorderedList, icons.list, 'insertUnorderedList', content,
            noteReadOnly, 'Control+Shift+8 Meta+Shift+8',
          ),
          formatButton(
            state.labels.orderedList, icons.ordered, 'insertOrderedList', content,
            noteReadOnly, 'Control+Shift+7 Meta+Shift+7',
          ),
          formatButton(
            state.labels.link, icons.link, 'createLink', content, noteReadOnly,
            'Control+K Meta+K',
          ),
        );
        const checklistToggle = makeButton(
          'format-button', state.labels.checklist, icons.checklist,
        );
        checklistToggle.disabled = noteReadOnly;
        checklistToggle.addEventListener('click', () => {
          if (!(note.checklist || []).length) {
            note.checklist = [{
              id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
              text: '',
              checked: false,
            }];
          }
          renderAll();
          queuePatch(note.id, { checklist: note.checklist }, true);
        });
        toolbar.appendChild(checklistToggle);
        card.append(toolbar, content);
        if ((note.checklist || []).length) {
          createChecklist(note, card, noteReadOnly);
        }
      } else {
        if (note.content) {
          const preview = document.createElement('div');
          preview.className = 'note-content-preview';
          preview.innerHTML = note.content;
          preview.addEventListener('click', event => {
            const link = event.target.closest?.('a');
            if (!link) return;
            event.preventDefault();
            const href = safeHref(link.href);
            if (href) emit('openExternalLink', { url: href });
          });
          card.appendChild(preview);
        }
        createChecklistPreview(note, card);
      }
    }

    createTagArea(note, card, noteReadOnly, editing);

    const footer = document.createElement('div');
    footer.className = 'card-footer';
    if (note.source_type === 'mindmap') {
      const openMap = document.createElement('button');
      openMap.type = 'button';
      openMap.className = 'open-map-action';
      openMap.innerHTML = `${icons.map}<span>${state.labels.openOnMap}</span>`;
      openMap.addEventListener('click', () => {
        flushPendingPatch(note.id);
        emit('openMindMapNode', { id: note.id });
      });
      footer.appendChild(openMap);
    }
    const spacer = document.createElement('span');
    spacer.className = 'spacer';
    footer.appendChild(spacer);

    const colorPalette = createColorPalette(note, item, noteReadOnly);
    footer.appendChild(colorPalette.toggle);

    const archive = makeButton(
      'card-action',
      note.archived ? state.labels.restore : state.labels.archiveAction,
      note.archived ? icons.restore : icons.archive,
    );
    archive.disabled = noteReadOnly;
    archive.addEventListener('click', () => {
      note.archived = !note.archived;
      if (editing) state.activeNoteId = null;
      renderAll();
      queuePatch(note.id, { archived: note.archived }, true);
    });
    footer.appendChild(archive);

    const remove = makeButton('card-action', state.labels.delete, icons.trash);
    remove.disabled = noteReadOnly;
    remove.addEventListener('click', () => {
      flushPendingPatch(note.id);
      emit('deleteNote', { id: note.id });
    });
    footer.appendChild(remove);
    if (editing) {
      const done = document.createElement('button');
      done.id = 'note-editor-done';
      done.type = 'button';
      done.textContent = state.labels.done || '';
      done.setAttribute('aria-label', state.labels.closeEditor || '');
      done.addEventListener('click', () => closeEditor());
      footer.appendChild(done);
    }
    card.append(colorPalette.palette, footer);
    item.appendChild(card);
    if (!editing) {
      const openEditor = event => {
        if (event.target.closest?.('button, input, textarea, a')) return;
        state.activeNoteId = note.id;
        renderEditor(true);
      };
      card.addEventListener('click', openEditor);
      card.addEventListener('keydown', event => {
        if (event.target !== card || !['Enter', ' '].includes(event.key)) return;
        event.preventDefault();
        state.activeNoteId = note.id;
        renderEditor(true);
      });
    }
    return item;
  }

  function focusEditorContent() {
    const editor = noteEditorHost.querySelector('.note-content, .map-note-content');
    editor?.focus();
    if (editor?.isContentEditable) {
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(editor);
      range.collapse(false);
      selection?.removeAllRanges();
      selection?.addRange(range);
    }
  }

  function renderEditor(shouldFocus = false) {
    const note = state.activeNoteId
      ? state.notes.get(state.activeNoteId)
      : null;
    if (!note) {
      noteEditorLayer.hidden = true;
      noteEditorHost.replaceChildren();
      document.body.classList.remove('editor-open');
      return;
    }
    noteEditorHost.replaceChildren(createNoteItem(note, true));
    const editorTitle = note.display_title || state.labels.titlePlaceholder || '';
    noteEditorDialog.setAttribute(
      'aria-label', `${state.labels.editNote || ''}: ${editorTitle}`,
    );
    noteEditorLayer.hidden = false;
    document.body.classList.add('editor-open');
    if (shouldFocus) {
      focusEditorContent();
      window.setTimeout(focusEditorContent, 0);
    }
  }

  function closeEditor(restoreFocus = true) {
    const closedNoteId = state.activeNoteId;
    if (closedNoteId) flushPendingPatch(closedNoteId);
    state.activeNoteId = null;
    renderAll();
    if (restoreFocus && closedNoteId) {
      window.requestAnimationFrame(() => {
        [...document.querySelectorAll('.notes-grid .note-item')]
          .find(item => item.dataset.noteId === closedNoteId)
          ?.querySelector('.note-card')
          ?.focus();
      });
    }
  }

  function destroyGrids() {
    for (const grid of state.grids) grid.destroy();
    state.grids = [];
    state.resizeObserver?.disconnect();
    state.resizeObserver = null;
  }

  function visibleOrderedIds() {
    const result = [];
    for (const grid of state.grids) {
      for (const item of grid.getItems()) result.push(item.getElement().dataset.noteId);
    }
    return result;
  }

  function createGrid(element) {
    applyResponsiveItemWidths();
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const dragEnabled = !state.readOnly
      && !state.query
      && !state.selectedTag
      && !state.selectedStageId
      && !state.sortByStage;
    const grid = new Muuri(element, {
      items: '.note-item',
      dragEnabled,
      dragHandle: '.drag-handle',
      dragStartPredicate: { distance: 7, delay: 100 },
      dragSortPredicate: { threshold: 50, action: 'move' },
      layout: {
        fillGaps: false,
        horizontal: false,
        alignRight: false,
        alignBottom: false,
        rounding: true,
      },
      layoutDuration: reducedMotion ? 1 : 180,
      layoutEasing: 'ease-out',
      dragRelease: {
        duration: reducedMotion ? 1 : 160,
        easing: 'ease-out',
        useDragContainer: false,
      },
    });
    if (dragEnabled) {
      grid.on('dragEnd', () => {
        grid.synchronize();
        grid.refreshItems().layout();
        window.setTimeout(() => emit('updateOrder', { ids: visibleOrderedIds() }), 0);
      });
      grid.on('dragReleaseEnd', () => grid.refreshItems().layout());
      for (const item of grid.getItems()) {
        const handle = item.getElement().querySelector('.drag-handle');
        handle?.addEventListener('keydown', event => {
          const direction = ['ArrowUp', 'ArrowLeft'].includes(event.key)
            ? -1
            : (['ArrowDown', 'ArrowRight'].includes(event.key) ? 1 : 0);
          if (!direction) return;
          const items = grid.getItems();
          const index = items.indexOf(item);
          const targetIndex = Math.max(0, Math.min(items.length - 1, index + direction));
          if (targetIndex === index) return;
          event.preventDefault();
          grid.move(item, items[targetIndex], { layout: true }).synchronize();
          emit('updateOrder', { ids: visibleOrderedIds() });
          setLiveStatus(state.labels.saved);
        });
      }
    }
    state.grids.push(grid);
    grid.refreshItems().layout(reducedMotion);
    return grid;
  }

  function rebuildResponsiveGrids() {
    renderAll();
  }

  function scheduleViewportRebuild() {
    window.clearTimeout(state.viewportTimer);
    state.viewportTimer = window.setTimeout(rebuildResponsiveGrids, 80);
  }

  function updateStaticLabels() {
    document.title = state.labels.documentTitle || '';
    skipLink.textContent = state.labels.skipToNotes || '';
    notesActions.setAttribute('aria-label', state.labels.notesActions || '');
    newNoteButton.querySelector('.button-label').textContent = state.labels.newNote || '';
    searchInput.placeholder = state.labels.searchPlaceholder || '';
    searchInput.setAttribute('aria-label', state.labels.searchPlaceholder || '');
    tagFilterButton.querySelector('.button-label').textContent = state.selectedTag
      ? `#${state.selectedTag}`
      : (state.labels.tags || '');
    stageNotesToggle.hidden = !state.hasStages;
    stageNotesToggle.querySelector('.button-label').textContent = state.labels.stageNotes || '';
    stageNotesToggle.setAttribute('aria-pressed', String(state.includeStageNotes));
    stageNotesToggle.title = state.labels.stageNotes || '';
    stageNotesToggle.setAttribute('aria-label', state.labels.stageNotes || '');
    const showStageControls = state.hasStages && state.includeStageNotes;
    stageFilterWrap.hidden = !showStageControls;
    stageSortToggle.hidden = !showStageControls;
    const selectedStage = state.stages.find(
      stage => stage.id === state.selectedStageId,
    );
    stageFilterButton.querySelector('.button-label').textContent = selectedStage?.name
      || state.labels.allStages
      || '';
    stageFilterButton.title = state.labels.filterByStage || '';
    stageFilterButton.setAttribute('aria-label', state.labels.filterByStage || '');
    stageSortToggle.querySelector('.button-label').textContent = state.labels.byStages || '';
    stageSortToggle.setAttribute('aria-pressed', String(state.sortByStage));
    const sortLabel = state.sortByStage
      ? state.labels.sortByAdded
      : state.labels.sortByStage;
    stageSortToggle.title = sortLabel || '';
    stageSortToggle.setAttribute('aria-label', sortLabel || '');
    archiveToggle.querySelector('.button-label').textContent = state.archiveMode
      ? (state.labels.activeNotes || '')
      : (state.labels.archive || '');
    archiveToggle.setAttribute('aria-pressed', String(state.archiveMode));
    pinnedHeading.textContent = state.labels.pinned || '';
    otherHeading.textContent = state.archiveMode
      ? (state.labels.archive || '')
      : (state.labels.others || '');
    readOnlyBanner.textContent = state.labels.readOnly || '';
    readOnlyBanner.hidden = !state.readOnly;
    newNoteButton.disabled = state.readOnly || state.creatingNote;
  }

  function rebuildTagMenu() {
    const tags = new Map();
    for (const note of state.notes.values()) {
      if (!noteInStageScope(note)) continue;
      if (note.source_type === 'mindmap') tags.set('карта', '#карта');
      for (const tag of note.tags || []) {
        const key = String(tag).toLocaleLowerCase();
        if (!tags.has(key)) tags.set(key, `#${tag}`);
      }
    }
    tagFilterMenu.replaceChildren();
    const all = document.createElement('button');
    all.type = 'button';
    all.role = 'menuitemradio';
    all.textContent = state.labels.allTags;
    all.setAttribute('aria-checked', String(state.selectedTag === null));
    all.addEventListener('click', () => selectTag(null));
    tagFilterMenu.appendChild(all);
    for (const [key, label] of [...tags.entries()].sort((a, b) => a[1].localeCompare(b[1]))) {
      const button = document.createElement('button');
      button.type = 'button';
      button.role = 'menuitemradio';
      button.textContent = label;
      button.setAttribute(
        'aria-checked',
        String(state.selectedTag?.toLocaleLowerCase() === key),
      );
      button.addEventListener('click', () => selectTag(key));
      tagFilterMenu.appendChild(button);
    }
  }

  function selectStage(stageId) {
    state.selectedStageId = stageId || null;
    stageFilterMenu.hidden = true;
    stageFilterButton.setAttribute('aria-expanded', 'false');
    renderAll();
  }

  function rebuildStageMenu() {
    stageFilterMenu.replaceChildren();
    const all = document.createElement('button');
    all.type = 'button';
    all.role = 'menuitemradio';
    all.textContent = state.labels.allStages || '';
    all.setAttribute('aria-checked', String(state.selectedStageId === null));
    all.addEventListener('click', () => selectStage(null));
    stageFilterMenu.appendChild(all);
    for (const stage of state.stages) {
      const button = document.createElement('button');
      button.type = 'button';
      button.role = 'menuitemradio';
      button.textContent = stage.name;
      button.setAttribute('aria-checked', String(state.selectedStageId === stage.id));
      button.addEventListener('click', () => selectStage(stage.id));
      stageFilterMenu.appendChild(button);
    }
  }

  function observeGridCards() {
    if (typeof ResizeObserver !== 'function') return;
    state.resizeObserver = new ResizeObserver(scheduleLayout);
    for (const card of document.querySelectorAll('.note-card')) {
      state.resizeObserver.observe(card);
    }
  }

  function renderAll(focusNoteId = null) {
    destroyGrids();
    pinnedGridElement.replaceChildren();
    otherGridElement.replaceChildren();
    const notes = [...state.notes.values()]
      .filter(noteMatches)
      .sort(compareNotes);
    const pinned = notes.filter(note => note.pinned);
    const others = notes.filter(note => !note.pinned);
    for (const note of pinned) pinnedGridElement.appendChild(createNoteItem(note));
    for (const note of others) otherGridElement.appendChild(createNoteItem(note));

    pinnedSection.hidden = pinned.length === 0;
    otherSection.hidden = others.length === 0;
    emptyState.hidden = notes.length !== 0;
    emptyState.textContent = state.archiveMode
      ? state.labels.emptyArchive
      : state.labels.empty;
    updateStaticLabels();
    rebuildTagMenu();
    rebuildStageMenu();
    if (pinned.length) createGrid(pinnedGridElement);
    if (others.length) createGrid(otherGridElement);
    if (focusNoteId) state.activeNoteId = focusNoteId;
    renderEditor(Boolean(focusNoteId));
    observeGridCards();
  }

  function selectTag(tag) {
    state.selectedTag = tag ? normalizeTag(tag) : null;
    tagFilterMenu.hidden = true;
    tagFilterButton.setAttribute('aria-expanded', 'false');
    renderAll();
  }

  function replaceOneExternalNote(note, previous) {
    const previousVisible = previous && noteMatches(previous);
    const nextVisible = noteMatches(note);
    if (!previousVisible && !nextVisible) {
      rebuildTagMenu();
      return;
    }
    const sameGrid = previousVisible && nextVisible
      && Boolean(previous.pinned) === Boolean(note.pinned)
      && Boolean(previous.archived) === Boolean(note.archived);
    if (!sameGrid) {
      renderAll();
      return;
    }
    const grid = state.grids.find(candidate => candidate.getItems().some(
      item => item.getElement().dataset.noteId === note.id,
    ));
    const oldItem = grid?.getItems().find(
      item => item.getElement().dataset.noteId === note.id,
    );
    if (!grid || !oldItem) {
      renderAll();
      return;
    }
    const element = createNoteItem(note);
    grid.remove([oldItem], { removeElements: true, layout: false });
    grid.add(element, { layout: false });
    grid.sort((itemA, itemB) => compareNotes(
      state.notes.get(itemA.getElement().dataset.noteId),
      state.notes.get(itemB.getElement().dataset.noteId),
    ), { layout: true });
    state.resizeObserver?.observe(element.querySelector('.note-card'));
    if (state.activeNoteId === note.id) renderEditor(false);
  }

  function applyEvent(event) {
    if (!event || typeof event !== 'object') return;
    const revision = Number(event.revision) || 0;
    if (revision && revision <= state.lastRevision) return;
    if (revision) state.lastRevision = revision;
    const payload = event.payload;
    if (event.type === 'noteDeleted') {
      const noteId = String(payload);
      window.clearTimeout(state.saveTimers.get(noteId));
      state.saveTimers.delete(noteId);
      state.pendingPatches.delete(noteId);
      state.notes.delete(noteId);
      if (state.activeNoteId === noteId) state.activeNoteId = null;
      renderAll();
      setLiveStatus(state.labels.saved);
      return;
    }
    if (!payload || typeof payload.id !== 'string') return;
    const previous = state.notes.get(payload.id);
    if (event.type === 'noteCreated') {
      state.notes.set(payload.id, payload);
      if (event.origin === 'notes') {
        state.creatingNote = false;
        state.activeNoteId = payload.id;
      }
      renderAll(event.origin === 'notes' ? payload.id : null);
    } else if (event.origin === 'notes' && previous) {
      // Keep the object captured by the open editor's handlers. Replacing it here
      // would make the next local action mutate a detached, stale note object.
      const pending = state.pendingPatches.get(payload.id) || {};
      const openChecklist = state.activeNoteId === payload.id
        ? previous.checklist
        : null;
      Object.assign(previous, payload, pending);
      // Checklist row handlers also retain their item objects until the editor is
      // rerendered, so keep that array alive while acknowledging local saves.
      if (openChecklist) previous.checklist = openChecklist;
      state.notes.set(payload.id, previous);
      rebuildTagMenu();
    } else {
      state.notes.set(payload.id, payload);
      replaceOneExternalNote(payload, previous);
    }
    setLiveStatus(state.labels.saved);
  }

  function showError(value) {
    state.creatingNote = false;
    updateStaticLabels();
    const message = typeof value === 'string' ? value : value?.message;
    errorToast.textContent = message || state.labels.error || '';
    errorToast.hidden = false;
    window.clearTimeout(showError.timer);
    showError.timer = window.setTimeout(() => { errorToast.hidden = true; }, 6000);
  }

  function updateTranslations(payload) {
    if (!payload || typeof payload !== 'object') return;
    state.labels = payload.labels || state.labels;
    state.locale = payload.locale || state.locale;
    document.documentElement.lang = state.locale.replace('_', '-');
    renderAll();
  }

  function updateViewContext(view) {
    const stages = Array.isArray(view?.stages) ? view.stages : [];
    state.hasStages = Boolean(view?.hasStages && stages.length);
    state.stages = stages
      .filter(stage => stage && typeof stage.id === 'string')
      .map(stage => ({ id: stage.id, name: String(stage.name || '') }));
    if (!state.hasStages) {
      state.includeStageNotes = false;
      state.selectedStageId = null;
      state.sortByStage = false;
    } else if (
      state.selectedStageId
      && !state.stages.some(stage => stage.id === state.selectedStageId)
    ) {
      state.selectedStageId = null;
    }
    renderAll();
  }

  let searchTimer = null;
  function bindStaticControls() {
    newNoteButton.addEventListener('click', () => {
      if (state.readOnly || state.creatingNote) return;
      state.archiveMode = false;
      state.query = '';
      state.selectedTag = null;
      state.selectedStageId = null;
      searchInput.value = '';
      state.creatingNote = true;
      renderAll();
      emit('createNote');
    });
    searchInput.addEventListener('input', () => {
      window.clearTimeout(searchTimer);
      searchTimer = window.setTimeout(() => {
        state.query = searchInput.value;
        renderAll();
      }, 140);
    });
    tagFilterButton.addEventListener('click', () => {
      tagFilterMenu.hidden = !tagFilterMenu.hidden;
      tagFilterButton.setAttribute('aria-expanded', String(!tagFilterMenu.hidden));
      if (!tagFilterMenu.hidden) tagFilterMenu.querySelector('button')?.focus();
    });
    stageNotesToggle.addEventListener('click', () => {
      state.includeStageNotes = !state.includeStageNotes;
      if (!state.includeStageNotes) {
        state.selectedStageId = null;
        state.sortByStage = false;
      }
      renderAll();
    });
    stageFilterButton.addEventListener('click', () => {
      stageFilterMenu.hidden = !stageFilterMenu.hidden;
      stageFilterButton.setAttribute(
        'aria-expanded', String(!stageFilterMenu.hidden),
      );
      if (!stageFilterMenu.hidden) stageFilterMenu.querySelector('button')?.focus();
    });
    stageSortToggle.addEventListener('click', () => {
      state.sortByStage = !state.sortByStage;
      renderAll();
    });
    archiveToggle.addEventListener('click', () => {
      state.archiveMode = !state.archiveMode;
      renderAll();
    });
    noteEditorLayer.addEventListener('pointerdown', event => {
      if (event.target === noteEditorLayer) closeEditor();
    });
    document.addEventListener('pointerdown', event => {
      if (!tagFilterMenu.contains(event.target) && !tagFilterButton.contains(event.target)) {
        tagFilterMenu.hidden = true;
        tagFilterButton.setAttribute('aria-expanded', 'false');
      }
      if (
        !stageFilterMenu.contains(event.target)
        && !stageFilterButton.contains(event.target)
      ) {
        stageFilterMenu.hidden = true;
        stageFilterButton.setAttribute('aria-expanded', 'false');
      }
      if (!event.target.closest?.('.color-palette, .color-palette-toggle')) {
        closeColorPalettes();
      }
    });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && document.querySelector('.color-palette:not([hidden])')) {
        event.preventDefault();
        closeColorPalettes(null, true);
        return;
      }
      if (event.key === 'Escape' && !tagFilterMenu.hidden) {
        tagFilterMenu.hidden = true;
        tagFilterButton.setAttribute('aria-expanded', 'false');
        tagFilterButton.focus();
        return;
      }
      if (event.key === 'Escape' && !stageFilterMenu.hidden) {
        stageFilterMenu.hidden = true;
        stageFilterButton.setAttribute('aria-expanded', 'false');
        stageFilterButton.focus();
        return;
      }
      if (event.key === 'Escape' && !noteEditorLayer.hidden) {
        event.preventDefault();
        closeEditor();
        return;
      }
      if (event.key === 'Tab' && !noteEditorLayer.hidden) {
        const focusable = [...noteEditorDialog.querySelectorAll(
          'button:not(:disabled), input:not(:disabled), textarea:not(:disabled), '
          + '[contenteditable="true"], [tabindex]:not([tabindex="-1"])',
        )];
        if (!focusable.length) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
      if ((event.ctrlKey || event.metaKey) && event.key.toLocaleLowerCase() === 'f') {
        event.preventDefault();
        searchInput.focus();
      }
    });
    window.addEventListener('resize', scheduleViewportRebuild);
  }

  let initialized = false;
  function initialize(payload) {
    if (initialized) return;
    initialized = true;
    state.labels = payload.labels || {};
    state.locale = payload.locale || 'ru';
    state.readOnly = Boolean(payload.readOnly);
    state.notes = new Map((payload.notes || []).map(note => [note.id, note]));
    const stages = Array.isArray(payload.view?.stages) ? payload.view.stages : [];
    state.hasStages = Boolean(payload.view?.hasStages && stages.length);
    state.stages = stages
      .filter(stage => stage && typeof stage.id === 'string')
      .map(stage => ({ id: stage.id, name: String(stage.name || '') }));
    document.documentElement.lang = state.locale.replace('_', '-');
    applyTheme(payload.theme);
    bindStaticControls();
    renderAll();
    appElement.setAttribute('aria-busy', 'false');
    emit('ready');
  }

  window.nfprogressNotes = {
    initialize,
    applyEvent,
    showError,
    updateTranslations,
    updateViewContext,
    themeChanged: applyTheme,
    viewportChanged: rebuildResponsiveGrids,
    flushAndTakeEvents() {
      flushAllPendingPatches();
      return JSON.stringify(nativeEvents.splice(0));
    },
    takeEvents() {
      return JSON.stringify(nativeEvents.splice(0));
    },
    getState() {
      return JSON.stringify({
        noteCount: state.notes.size,
        archiveMode: state.archiveMode,
        selectedTag: state.selectedTag,
        hasStages: state.hasStages,
        includeStageNotes: state.includeStageNotes,
        selectedStageId: state.selectedStageId,
        sortByStage: state.sortByStage,
        creatingNote: state.creatingNote,
        activeNoteId: state.activeNoteId,
        editorOpen: !noteEditorLayer.hidden,
        visibleIds: visibleOrderedIds(),
      });
    },
  };
})();
