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

  const icons = {
    drag: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="8" cy="7" r="1" fill="currentColor" stroke="none"/><circle cx="16" cy="7" r="1" fill="currentColor" stroke="none"/><circle cx="8" cy="12" r="1" fill="currentColor" stroke="none"/><circle cx="16" cy="12" r="1" fill="currentColor" stroke="none"/><circle cx="8" cy="17" r="1" fill="currentColor" stroke="none"/><circle cx="16" cy="17" r="1" fill="currentColor" stroke="none"/></svg>',
    pin: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m8 3 8 0-1 6 3 3v2H6v-2l3-3zM12 14v7"/></svg>',
    archive: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16v13H4zM3 3h18v4H3zM9 11h6"/></svg>',
    restore: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16v13H4zM3 3h18v4H3zM12 17V10M8.5 13.5 12 10l3.5 3.5"/></svg>',
    trash: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3M7 7l1 14h8l1-14M10 11v6M14 11v6"/></svg>',
    checklist: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 7 2 2 3-4M11 7h10M3 15l2 2 3-4M11 15h10"/></svg>',
    list: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 6h13M8 12h13M8 18h13M3 6h1M3 12h1M3 18h1"/></svg>',
    ordered: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 6h12M9 12h12M9 18h12M3 5h2v3M3 11h2l-2 3h2M3 17h2v3H3"/></svg>',
    link: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 13a5 5 0 0 0 7 0l2-2a5 5 0 0 0-7-7l-1 1M14 11a5 5 0 0 0-7 0l-2 2a5 5 0 0 0 7 7l1-1"/></svg>',
    map: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="5" cy="12" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="m7.5 11 8-4M7.5 13l8 4"/></svg>',
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

  function noteMatches(note) {
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
      note.source_type === 'mindmap' ? '#карта карта' : '',
    ].join(' ').toLocaleLowerCase();
    return searchable.includes(query);
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

  function responsiveColumnCount() {
    if (window.innerWidth <= 620) return 1;
    if (window.innerWidth <= 900) return 2;
    return 3;
  }

  function applyResponsiveItemWidths() {
    for (const item of document.querySelectorAll('.note-item')) {
      const containerWidth = item.parentElement?.clientWidth || 0;
      const columns = responsiveColumnCount();
      const width = containerWidth > 0
        ? `${containerWidth / columns}px`
        : `${100 / columns}%`;
      item.style.setProperty('width', width, 'important');
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
      event.preventDefault();
      const text = event.clipboardData?.getData('text/plain') || '';
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

  function formatButton(label, icon, command, contentElement) {
    const button = makeButton('format-button', label, icon);
    button.disabled = state.readOnly;
    button.addEventListener('pointerdown', event => event.preventDefault());
    button.addEventListener('click', () => {
      contentElement.focus();
      if (command === 'createLink') {
        let href = window.prompt(state.labels.linkPrompt, 'https://');
        if (!href) return;
        if (!/^[a-z][a-z0-9+.-]*:/i.test(href)) href = `https://${href}`;
        if (!safeHref(href)) return;
        document.execCommand(command, false, href);
      } else {
        document.execCommand(command, false, null);
      }
      contentElement.dispatchEvent(new Event('input', { bubbles: true }));
    });
    return button;
  }

  function createChecklist(note, container) {
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
      checkbox.disabled = state.readOnly;
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
      input.disabled = state.readOnly;
      input.setAttribute('aria-label', state.labels.checklist);
      input.addEventListener('input', () => {
        item.text = input.value.slice(0, 2000);
        saveChecklist();
      });
      const remove = makeButton('checklist-remove', state.labels.removeChecklistItem, '×');
      remove.disabled = state.readOnly;
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
    add.disabled = state.readOnly;
    add.addEventListener('click', () => {
      note.checklist = [...(note.checklist || []), {
        id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
        text: '',
        checked: false,
      }];
      renderAll();
      queuePatch(note.id, { checklist: note.checklist }, true);
      window.requestAnimationFrame(() => {
        const noteElement = [...document.querySelectorAll('.note-item')]
          .find(candidate => candidate.dataset.noteId === note.id);
        const inputs = noteElement?.querySelectorAll('.checklist-text') || [];
        inputs[inputs.length - 1]?.focus();
      });
    });
    checklist.appendChild(add);
    container.appendChild(checklist);
  }

  function createTagArea(note, container) {
    const tagArea = document.createElement('div');
    tagArea.className = 'tag-area';
    const tagList = document.createElement('div');
    tagList.className = 'tag-list';
    for (const systemTag of note.system_tags || []) {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'tag-chip system-tag';
      chip.textContent = `#${systemTag}`;
      chip.addEventListener('click', () => selectTag(systemTag));
      tagList.appendChild(chip);
    }
    for (const tag of note.tags || []) {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'tag-chip';
      chip.textContent = `#${tag}`;
      chip.addEventListener('click', () => selectTag(tag));
      tagList.appendChild(chip);
    }
    tagArea.appendChild(tagList);
    const tagInput = document.createElement('input');
    tagInput.type = 'text';
    tagInput.className = 'tag-input';
    tagInput.value = (note.tags || []).join(', ');
    tagInput.placeholder = state.labels.tagsPlaceholder;
    tagInput.setAttribute('aria-label', state.labels.tagsPlaceholder);
    tagInput.disabled = state.readOnly;
    tagInput.addEventListener('input', () => {
      const tags = normalizedTags(tagInput.value.split(','));
      updateLocalNote(note.id, { tags });
      queuePatch(note.id, { tags });
    });
    tagArea.appendChild(tagInput);
    container.appendChild(tagArea);
  }

  function createNoteItem(note) {
    const item = document.createElement('div');
    item.className = 'note-item';
    item.style.setProperty(
      'width',
      `${100 / responsiveColumnCount()}%`,
      'important',
    );
    item.dataset.noteId = note.id;
    item.dataset.color = note.color || 'default';
    item.dataset.source = note.source_type;
    item.dataset.order = String(note.sort_order || 0);

    const card = document.createElement('article');
    card.className = 'note-card';
    card.setAttribute('aria-label', note.display_title || state.labels.titlePlaceholder);

    const header = document.createElement('div');
    header.className = 'card-header';
    const drag = makeButton('drag-handle', state.labels.drag, icons.drag);
    drag.disabled = state.readOnly || Boolean(state.query || state.selectedTag);
    const title = document.createElement('input');
    title.type = 'text';
    title.className = 'note-title';
    title.value = note.title || '';
    title.placeholder = note.display_title || state.labels.titlePlaceholder;
    title.maxLength = 500;
    title.disabled = state.readOnly;
    title.setAttribute('aria-label', state.labels.titlePlaceholder);
    title.addEventListener('input', () => {
      note.title = title.value;
      queuePatch(note.id, { title: title.value });
    });
    const pin = makeButton(
      'card-action',
      note.pinned ? state.labels.unpin : state.labels.pin,
      icons.pin,
    );
    pin.setAttribute('aria-pressed', String(Boolean(note.pinned)));
    pin.disabled = state.readOnly;
    pin.addEventListener('click', () => {
      note.pinned = !note.pinned;
      renderAll();
      queuePatch(note.id, { pinned: note.pinned }, true);
    });
    header.append(drag, title, pin);
    card.appendChild(header);

    if (note.source_type === 'mindmap') {
      const textarea = document.createElement('textarea');
      textarea.className = 'map-note-content';
      textarea.value = note.content || '';
      textarea.placeholder = state.labels.contentPlaceholder;
      textarea.setAttribute('aria-label', state.labels.contentPlaceholder);
      textarea.disabled = state.readOnly;
      textarea.addEventListener('input', () => {
        note.content = textarea.value;
        if (!note.title) {
          note.display_title = textarea.value
            .split(/\r?\n/)
            .map(line => line.trim())
            .find(Boolean)
            ?.slice(0, 100) || state.labels.mapNote;
          title.placeholder = note.display_title;
          card.setAttribute('aria-label', note.display_title);
        }
        queuePatch(note.id, { content: textarea.value });
        scheduleLayout();
      });
      card.appendChild(textarea);
      const plainInfo = document.createElement('div');
      plainInfo.className = 'map-format-note';
      plainInfo.textContent = state.labels.plainMapNote;
      card.appendChild(plainInfo);
    } else {
      const content = document.createElement('div');
      content.className = 'note-content';
      content.contentEditable = state.readOnly ? 'false' : 'true';
      content.spellcheck = true;
      content.dataset.placeholder = state.labels.contentPlaceholder;
      content.setAttribute('role', 'textbox');
      content.setAttribute('aria-multiline', 'true');
      content.setAttribute('aria-label', state.labels.contentPlaceholder);
      content.innerHTML = note.content || '';
      installPasteAsPlainText(content);
      content.addEventListener('input', () => {
        const clean = sanitizedEditableHtml(content);
        note.content = clean;
        queuePatch(note.id, { content: clean });
        scheduleLayout();
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
        formatButton(state.labels.bold, '<strong>B</strong>', 'bold', content),
        formatButton(state.labels.italic, '<em>I</em>', 'italic', content),
        formatButton(state.labels.strike, '<s>S</s>', 'strikeThrough', content),
        formatButton(state.labels.unorderedList, icons.list, 'insertUnorderedList', content),
        formatButton(state.labels.orderedList, icons.ordered, 'insertOrderedList', content),
        formatButton(state.labels.link, icons.link, 'createLink', content),
      );
      const checklistToggle = makeButton(
        'format-button', state.labels.checklist, icons.checklist,
      );
      checklistToggle.disabled = state.readOnly;
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
      if ((note.checklist || []).length) createChecklist(note, card);
    }

    createTagArea(note, card);

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

    const color = document.createElement('select');
    color.className = 'color-select';
    color.title = state.labels.color;
    color.setAttribute('aria-label', state.labels.color);
    color.disabled = state.readOnly;
    for (const [value, label] of Object.entries(state.labels.colors || {})) {
      const option = document.createElement('option');
      option.value = value;
      option.textContent = label;
      option.selected = value === note.color;
      color.appendChild(option);
    }
    color.addEventListener('change', () => {
      note.color = color.value;
      item.dataset.color = color.value;
      queuePatch(note.id, { color: color.value }, true);
    });
    footer.appendChild(color);

    const archive = makeButton(
      'card-action',
      note.archived ? state.labels.restore : state.labels.archiveAction,
      note.archived ? icons.restore : icons.archive,
    );
    archive.disabled = state.readOnly;
    archive.addEventListener('click', () => {
      note.archived = !note.archived;
      renderAll();
      queuePatch(note.id, { archived: note.archived }, true);
    });
    footer.appendChild(archive);

    const remove = makeButton('card-action', state.labels.delete, icons.trash);
    remove.disabled = state.readOnly;
    remove.addEventListener('click', () => {
      flushPendingPatch(note.id);
      emit('deleteNote', { id: note.id });
    });
    footer.appendChild(remove);
    card.appendChild(footer);
    item.appendChild(card);
    return item;
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
    const dragEnabled = !state.readOnly && !state.query && !state.selectedTag;
    const grid = new Muuri(element, {
      items: '.note-item',
      dragEnabled,
      dragHandle: '.drag-handle',
      dragStartPredicate: { distance: 7, delay: 100 },
      layoutDuration: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 180,
      layoutEasing: 'ease-out',
      dragRelease: { duration: 160, easing: 'ease-out', useDragContainer: true },
    });
    if (dragEnabled) {
      grid.on('dragEnd', () => {
        window.setTimeout(() => emit('updateOrder', { ids: visibleOrderedIds() }), 0);
      });
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
    newNoteButton.disabled = state.readOnly;
  }

  function rebuildTagMenu() {
    const tags = new Map();
    tags.set('карта', '#карта');
    for (const note of state.notes.values()) {
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
      .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
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
    if (pinned.length) createGrid(pinnedGridElement);
    if (others.length) createGrid(otherGridElement);
    observeGridCards();
    if (focusNoteId) {
      window.requestAnimationFrame(() => {
        const element = [...document.querySelectorAll('.note-item')]
          .find(item => item.dataset.noteId === focusNoteId);
        element?.querySelector('.note-title')?.focus();
        element?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      });
    }
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
    grid.sort((itemA, itemB) => (
      Number(itemA.getElement().dataset.order)
      - Number(itemB.getElement().dataset.order)
    ), { layout: true });
    state.resizeObserver?.observe(element.querySelector('.note-card'));
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
      renderAll();
      setLiveStatus(state.labels.saved);
      return;
    }
    if (!payload || typeof payload.id !== 'string') return;
    const previous = state.notes.get(payload.id);
    state.notes.set(payload.id, payload);
    if (event.type === 'noteCreated') {
      renderAll(event.origin === 'notes' ? payload.id : null);
    } else if (event.origin === 'notes') {
      // The local card already contains this edit. Keeping it avoids losing focus.
      rebuildTagMenu();
    } else {
      replaceOneExternalNote(payload, previous);
    }
    setLiveStatus(state.labels.saved);
  }

  function showError(value) {
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

  let searchTimer = null;
  function bindStaticControls() {
    newNoteButton.addEventListener('click', () => emit('createNote'));
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
    archiveToggle.addEventListener('click', () => {
      state.archiveMode = !state.archiveMode;
      renderAll();
    });
    document.addEventListener('pointerdown', event => {
      if (!tagFilterMenu.contains(event.target) && !tagFilterButton.contains(event.target)) {
        tagFilterMenu.hidden = true;
        tagFilterButton.setAttribute('aria-expanded', 'false');
      }
    });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && !tagFilterMenu.hidden) {
        tagFilterMenu.hidden = true;
        tagFilterButton.setAttribute('aria-expanded', 'false');
        tagFilterButton.focus();
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
        visibleIds: visibleOrderedIds(),
      });
    },
  };
})();
