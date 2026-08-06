import MindElixir from './MindElixir.js';
import { de, en, es, fr, pt, ru } from './i18n.js';

const localePacks = { de, en, es, fr, pt_BR: pt, ru };
const loadingElement = document.getElementById('loading');

let bridge = null;
let mind = null;
let readOnly = false;
let saveTimer = null;

function errorText(error) {
  if (error instanceof Error) {
    return error.stack || error.message;
  }
  return String(error);
}

function reportError(error) {
  const message = errorText(error);
  console.error(message);
  if (bridge) {
    bridge.reportError(message);
  }
}

function finishActiveEdit() {
  const activeElement = document.activeElement;
  if (activeElement && activeElement !== document.body) {
    activeElement.blur();
  }
}

function getDataString() {
  if (!mind) {
    return null;
  }
  finishActiveEdit();
  return mind.getDataString();
}

function saveNow() {
  if (!bridge || !mind || readOnly) {
    return;
  }
  if (saveTimer !== null) {
    window.clearTimeout(saveTimer);
    saveTimer = null;
  }
  try {
    bridge.save(getDataString());
  } catch (error) {
    reportError(error);
  }
}

function scheduleSave() {
  if (!bridge || readOnly) {
    return;
  }
  bridge.changed();
  if (saveTimer !== null) {
    window.clearTimeout(saveTimer);
  }
  saveTimer = window.setTimeout(saveNow, 400);
}

function initialize(payload) {
  readOnly = Boolean(payload.readOnly);
  document.documentElement.lang = payload.locale.replace('_', '-');
  document.getElementById('map').setAttribute('aria-label', payload.editorLabel);
  loadingElement.textContent = payload.loadingText;
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

  if (!readOnly) {
    mind.bus.addListener('operation', scheduleSave);
    mind.bus.addListener('expandNode', scheduleSave);
    mind.bus.addListener('updateArrowDelta', scheduleSave);
  }

  loadingElement.hidden = true;
  bridge.ready();
  if (!payload.data && !readOnly) {
    saveNow();
  }
  window.requestAnimationFrame(() => mind.toCenter());
}

window.nfprogressMindMap = {
  getDataString,
  saveNow,
  toCenter() {
    if (mind) {
      mind.toCenter();
    }
  },
};

window.addEventListener('error', (event) => reportError(event.error || event.message));
window.addEventListener('unhandledrejection', (event) => reportError(event.reason));

if (!window.qt || !window.qt.webChannelTransport || !window.QWebChannel) {
  reportError('Qt WebChannel is unavailable.');
} else {
  new window.QWebChannel(window.qt.webChannelTransport, (channel) => {
    bridge = channel.objects.mindmapBridge;
    bridge.initialPayload((payloadText) => {
      try {
        initialize(JSON.parse(payloadText));
      } catch (error) {
        reportError(error);
      }
    });
  });
}
