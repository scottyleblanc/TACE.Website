// AI coach chat view: thread management, message rendering, send flow, and
// the coach_scope setting. Reuses apiRequest()/esc() from app.js -- the
// /conversations* and /settings routes return the {ok, data, message}
// envelope (Stage 3.10), unlike /days's bare body, so every call here
// unwraps `.data` itself rather than changing the shared apiRequest().

import { apiRequest, esc } from './app.js';

let _initialized = false;
let _threads = [];
let _currentThreadId = null;
let _coachScope = 'plan_only';

// --- Markdown-lite rendering (no library) ---------------------------------
// Escape first with the shared esc(), then apply a small, safe set of
// replacements for the markdown the coach actually uses (**bold**, "- "
// bullet lists, blank-line-separated paragraphs).
function renderMarkdownLite(raw) {
  const escaped = esc(raw).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  const blocks = escaped.split(/\n\s*\n/).filter(b => b.trim() !== '');
  return blocks.map(block => {
    const lines = block.split('\n').filter(l => l.length > 0);
    const isList = lines.length > 0 && lines.every(l => /^-\s+/.test(l));
    if (isList) {
      return `<ul>${lines.map(l => `<li>${l.replace(/^-\s+/, '')}</li>`).join('')}</ul>`;
    }
    return `<p>${block.replace(/\n/g, '<br>')}</p>`;
  }).join('');
}

// --- Message rendering -----------------------------------------------------
function messageBubbleHTML(message) {
  const roleClass = message.role === 'user' ? 'msg-user'
    : message.rail_triggered ? 'msg-rail' : 'msg-coach';
  const label = message.rail_triggered
    ? '<div class="msg-rail-label">Deferred to physio</div>' : '';
  return `
    <div class="msg-bubble ${roleClass}">
      ${label}
      <div class="msg-content">${renderMarkdownLite(message.content)}</div>
    </div>`;
}

function renderMessages(messages) {
  const el = document.getElementById('coach-messages');
  if (!messages.length) {
    el.innerHTML = '<p class="coach-empty">Say hello to get started.</p>';
    return;
  }
  el.innerHTML = messages.map(messageBubbleHTML).join('');
  el.scrollTop = el.scrollHeight;
}

function appendThinkingBubble() {
  const el = document.getElementById('coach-messages');
  const div = document.createElement('div');
  div.className = 'msg-bubble msg-coach msg-thinking';
  div.id = 'coach-thinking-bubble';
  div.innerHTML = '<div class="msg-content">Thinking&hellip;</div>';
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
}

function removeThinkingBubble() {
  document.getElementById('coach-thinking-bubble')?.remove();
}

function appendErrorBubble(text) {
  const el = document.getElementById('coach-messages');
  const div = document.createElement('div');
  div.className = 'msg-bubble msg-error';
  div.innerHTML = `<div class="msg-content">${esc(text)}</div>`;
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
}

// --- Threads -----------------------------------------------------------
async function loadMessages(threadId) {
  const res = await apiRequest('GET', `/conversations/${threadId}`);
  renderMessages(res?.data?.messages ?? []);
}

function renderEmptyThreadState() {
  document.getElementById('coach-messages').innerHTML =
    '<p class="coach-empty">No conversations yet. Click "+ New" to start one.</p>';
}

async function loadThreads() {
  const res = await apiRequest('GET', '/conversations');
  _threads = res?.data ?? [];
  const select = document.getElementById('thread-select');

  if (!_threads.length) {
    select.innerHTML = '';
    _currentThreadId = null;
    renderEmptyThreadState();
    return;
  }

  select.innerHTML = _threads.map(t =>
    `<option value="${esc(t.conversation_id)}">${esc(t.title)}</option>`
  ).join('');

  const stillExists = _threads.some(t => t.conversation_id === _currentThreadId);
  _currentThreadId = stillExists ? _currentThreadId : _threads[0].conversation_id;
  select.value = _currentThreadId;
  await loadMessages(_currentThreadId);
}

async function createThread() {
  const title = prompt('Name this conversation:');
  if (!title || !title.trim()) return;
  const res = await apiRequest('POST', '/conversations', { title: title.trim() });
  _currentThreadId = res?.data?.conversation_id ?? null;
  await loadThreads();
}

async function renameThread() {
  if (!_currentThreadId) return;
  const current = _threads.find(t => t.conversation_id === _currentThreadId);
  const title = prompt('Rename conversation:', current?.title ?? '');
  if (!title || !title.trim()) return;
  await apiRequest('PATCH', `/conversations/${_currentThreadId}`, { title: title.trim() });
  await loadThreads();
}

async function deleteThread() {
  if (!_currentThreadId) return;
  if (!confirm('Delete this conversation? This cannot be undone.')) return;
  await apiRequest('DELETE', `/conversations/${_currentThreadId}`);
  _currentThreadId = null;
  await loadThreads();
}

// --- Sending -----------------------------------------------------------
async function sendMessage(text) {
  if (!_currentThreadId) {
    alert('Create a conversation first.');
    return;
  }

  const el = document.getElementById('coach-messages');
  el.querySelector('.coach-empty')?.remove();
  el.insertAdjacentHTML('beforeend', messageBubbleHTML({ role: 'user', content: text }));
  appendThinkingBubble();
  el.scrollTop = el.scrollHeight;

  try {
    const res = await apiRequest('POST', `/conversations/${_currentThreadId}/messages`, { content: text });
    removeThinkingBubble();
    const reply = res?.data;
    if (reply) {
      el.insertAdjacentHTML('beforeend', messageBubbleHTML(reply));
      el.scrollTop = el.scrollHeight;
    }
  } catch {
    removeThinkingBubble();
    appendErrorBubble('Coach is temporarily unavailable -- please try again.');
  }
}

// --- Settings (coach_scope) ---------------------------------------------
function updateScopeButtons() {
  document.querySelectorAll('.scope-btn').forEach(btn => {
    btn.classList.toggle('scope-btn-active', btn.dataset.scope === _coachScope);
  });
}

async function loadSettings() {
  const res = await apiRequest('GET', '/settings');
  _coachScope = res?.data?.coach_scope ?? 'plan_only';
  updateScopeButtons();
}

async function setScope(scope) {
  if (scope === _coachScope) return;
  _coachScope = scope;
  updateScopeButtons();
  await apiRequest('PATCH', '/settings', { coach_scope: scope });
}

// --- Init ----------------------------------------------------------------
function bindOnce() {
  if (_initialized) return;
  _initialized = true;

  document.getElementById('thread-new-btn').addEventListener('click', createThread);
  document.getElementById('thread-rename-btn').addEventListener('click', renameThread);
  document.getElementById('thread-delete-btn').addEventListener('click', deleteThread);
  document.getElementById('thread-select').addEventListener('change', async e => {
    _currentThreadId = e.target.value;
    await loadMessages(_currentThreadId);
  });

  document.querySelectorAll('.scope-btn').forEach(btn => {
    btn.addEventListener('click', () => setScope(btn.dataset.scope));
  });

  const input = document.getElementById('coach-input');
  const form = document.getElementById('coach-send-form');
  form.addEventListener('submit', async e => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    document.getElementById('coach-send-btn').disabled = true;
    await sendMessage(text);
    document.getElementById('coach-send-btn').disabled = false;
    input.focus();
  });
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      form.requestSubmit();
    }
  });
}

export async function initCoach() {
  bindOnce();
  await loadSettings();
  await loadThreads();
}
