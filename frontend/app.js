/* ============================================================
   AI Knowledge System — Frontend Logic
   ============================================================ */

const API = '';

// ── State ─────────────────────────────────────────────────────────
let isQuerying = false;
let documents  = [];

// ── Init ──────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  checkHealth();
  loadDocumentsMini();
  setInterval(checkHealth, 15000);
});

// ── Tab Switching ─────────────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  document.getElementById('panel-' + name).classList.add('active');
  document.getElementById('tab-' + name).classList.add('active');
  
  // Hide sidebar on tab switch (for mobile)
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  if (sidebar) sidebar.classList.remove('active');
  if (overlay) overlay.classList.remove('active');

  if (name === 'docs')    loadDocumentsPage();
  if (name === 'metrics') loadMetrics();
}

// ── Mobile Sidebar Toggle ─────────────────────────────────────────
function toggleSidebar() {
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  if (sidebar) sidebar.classList.toggle('active');
  if (overlay) overlay.classList.toggle('active');
}

// ── Health Check ──────────────────────────────────────────────────
async function checkHealth() {
  const dot  = document.querySelector('.status-dot');
  const text = document.getElementById('status-text');
  try {
    const r = await fetch(`${API}/metrics/health`, { signal: AbortSignal.timeout(4000) });
    if (r.ok) {
      dot.className  = 'status-dot online';
      text.textContent = 'Online';
    } else throw new Error();
  } catch {
    dot.className  = 'status-dot offline';
    text.textContent = 'Offline';
  }
}

// ── File Upload ───────────────────────────────────────────────────
function handleDragOver(e) {
  e.preventDefault();
  document.getElementById('drop-zone').classList.add('drag-over');
}
function handleDragLeave(e) {
  document.getElementById('drop-zone').classList.remove('drag-over');
}
function handleDrop(e) {
  e.preventDefault();
  document.getElementById('drop-zone').classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) uploadFile(file);
}
function handleFileSelect(e) {
  const file = e.target.files[0];
  if (file) uploadFile(file);
}

async function uploadFile(file) {
  const allowed = ['pdf', 'txt', 'docx'];
  const ext = file.name.split('.').pop().toLowerCase();
  if (!allowed.includes(ext)) {
    showToast('❌ Only PDF, TXT, DOCX files are supported.', 'error');
    return;
  }

  const progress = document.getElementById('upload-progress');
  const fill     = document.getElementById('progress-fill');
  const label    = document.getElementById('progress-label');
  const result   = document.getElementById('upload-result');

  progress.classList.remove('hidden');
  result.classList.add('hidden');
  fill.style.width = '0%';
  label.textContent = `Uploading ${file.name}...`;

  // Animate progress bar
  let pct = 0;
  const timer = setInterval(() => {
    pct = Math.min(pct + Math.random() * 12, 85);
    fill.style.width = pct + '%';
  }, 200);

  const form = new FormData();
  form.append('file', file);

  try {
    const r = await fetch(`${API}/upload/`, { method: 'POST', body: form });
    clearInterval(timer);
    fill.style.width = '100%';

    const data = await r.json();

    if (r.ok) {
      label.textContent = '✅ Done!';
      result.className = 'upload-result success';
      result.textContent = `${data.message} (${data.chunks_created} chunks)`;
      result.classList.remove('hidden');
      showToast(`📄 "${file.name}" added to knowledge base!`, 'success');
      loadDocumentsMini();
    } else {
      throw new Error(data.detail || 'Upload failed');
    }
  } catch (err) {
    clearInterval(timer);
    fill.style.width = '0%';
    label.textContent = 'Upload failed';
    result.className = 'upload-result error';
    result.textContent = `❌ ${err.message}`;
    result.classList.remove('hidden');
    showToast(`❌ Upload failed: ${err.message}`, 'error');
  } finally {
    setTimeout(() => progress.classList.add('hidden'), 3000);
  }
}

// ── Load Documents (mini sidebar list) ───────────────────────────
async function loadDocumentsMini() {
  try {
    const r = await fetch(`${API}/upload/documents`);
    const data = await r.json();
    documents = data.documents || [];
    renderDocsMini(documents);
  } catch { /* offline */ }
}

function renderDocsMini(docs) {
  const list = document.getElementById('docs-mini-list');
  if (!docs.length) {
    list.innerHTML = '<li class="empty-state">No documents yet</li>';
    return;
  }
  list.innerHTML = docs.map(d => `
    <li>
      <span>${fileIcon(d.filename)}</span>
      <span class="doc-name">${d.filename}</span>
      <span class="doc-badge">${d.chunks}ch</span>
      <button class="mini-delete-btn" onclick="deleteDocument('${d.document_id}', event)" title="Delete Document">✖</button>
    </li>
  `).join('');
}

async function deleteDocument(doc_id, event) {
  if (event) event.stopPropagation();
  if (!confirm('Are you sure you want to delete this document?')) return;
  
  try {
    const r = await fetch(`${API}/upload/${doc_id}`, { method: 'DELETE' });
    if (r.ok) {
      showToast('Document deleted successfully', 'success');
      loadDocumentsMini();
      if (document.getElementById('panel-docs').classList.contains('active')) {
        loadDocumentsPage();
      }
    } else {
      const data = await r.json();
      throw new Error(data.detail || 'Failed to delete');
    }
  } catch(err) {
    showToast(err.message, 'error');
  }
}

// ── Load Documents (full page) ───────────────────────────────────
async function loadDocumentsPage() {
  try {
    const r = await fetch(`${API}/upload/documents`);
    const data = await r.json();
    renderDocsPage(data.documents || []);
  } catch {
    showToast('Could not load documents. Is the server running?', 'error');
  }
}

function renderDocsPage(docs) {
  const grid = document.getElementById('docs-grid');
  if (!docs.length) {
    grid.innerHTML = `
      <div class="empty-card">
        <div class="empty-icon">📂</div>
        <p>No documents uploaded yet.</p>
        <p class="empty-sub">Go to the Chat tab and upload a document to get started.</p>
      </div>`;
    return;
  }
  grid.innerHTML = docs.map(d => `
    <div class="doc-card">
      <button class="doc-delete-btn" onclick="deleteDocument('${d.document_id}', event)" title="Delete Document">🗑️</button>
      <div class="doc-card-icon">${fileIcon(d.filename)}</div>
      <div class="doc-card-name">${d.filename}</div>
      <div class="doc-card-meta">
        <span class="doc-tag">ID: ${d.document_id.substring(0,8)}</span>
        <span class="doc-tag">${d.chunks} chunks</span>
        <span class="doc-tag">${formatBytes(d.size_bytes)}</span>
        <span class="doc-tag">${formatDate(d.uploaded_at)}</span>
      </div>
    </div>
  `).join('');
}

// ── Query ─────────────────────────────────────────────────────────
function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendQuery();
  }
}

function useExample(btn) {
  const input = document.getElementById('chat-input');
  input.value = btn.textContent;
  autoResize(input);
  input.focus();
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 140) + 'px';
}

async function sendQuery() {
  if (isQuerying) return;
  const input = document.getElementById('chat-input');
  const question = input.value.trim();
  if (!question) return;

  isQuerying = true;
  const sendBtn = document.getElementById('send-btn');
  sendBtn.disabled = true;

  // Add user message
  appendMessage('user', question);
  input.value = '';
  input.style.height = 'auto';

  // Show typing indicator
  const typingId = appendTyping();

  try {
    const r = await fetch(`${API}/query/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });

    removeTyping(typingId);

    if (!r.ok) {
      const err = await r.json();
      appendMessage('ai', `⚠️ ${err.detail || 'Something went wrong.'}`, [], null);
    } else {
      const data = await r.json();
      appendMessage('ai', data.answer, data.sources, {
        latency: data.latency_ms,
        tokens: data.tokens_used,
        cost: data.estimated_cost_usd,
      });
    }
  } catch (err) {
    removeTyping(typingId);
    appendMessage('ai', `⚠️ Cannot connect to the server. Make sure it's running at ${API}`, [], null);
  } finally {
    isQuerying = false;
    sendBtn.disabled = false;
    input.focus();
  }
}

// ── Message Rendering ─────────────────────────────────────────────
function appendMessage(role, text, sources = [], meta = null) {
  const container = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = `message message-${role}`;

  const avatar = role === 'user' ? '👤' : '🧠';

  let sourcesHtml = '';
  if (sources && sources.length) {
    const chips = sources.map(s =>
      `<span class="source-chip" title="${s.content.substring(0, 120)}...">
        📄 ${s.filename} #${s.chunk_index + 1}
        <small>(${(s.relevance_score * 100).toFixed(1)}%)</small>
      </span>`
    ).join('');
    sourcesHtml = `<div class="msg-sources">
      <div class="sources-label">📌 SOURCES</div>
      ${chips}
    </div>`;
  }

  let metaHtml = '';
  if (meta) {
    metaHtml = `<div class="msg-meta">
      <span class="meta-tag">⏱ ${meta.latency?.toFixed(0)}ms</span>
      ${meta.tokens ? `<span class="meta-tag">🔢 ${meta.tokens} tokens</span>` : ''}
      ${meta.cost !== undefined ? `<span class="meta-tag">💰 $${meta.cost.toFixed(5)}</span>` : ''}
    </div>`;
  }

  div.innerHTML = `
    <div class="msg-avatar">${avatar}</div>
    <div class="msg-bubble">
      <p class="msg-text">${escapeHtml(text)}</p>
      ${sourcesHtml}
      ${metaHtml}
    </div>`;

  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function appendTyping() {
  const container = document.getElementById('chat-messages');
  const id = 'typing-' + Date.now();
  const div = document.createElement('div');
  div.className = 'message message-ai';
  div.id = id;
  div.innerHTML = `
    <div class="msg-avatar">🧠</div>
    <div class="msg-bubble">
      <div class="typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    </div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return id;
}

function removeTyping(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

// ── Metrics ───────────────────────────────────────────────────────
async function loadMetrics() {
  try {
    const r = await fetch(`${API}/metrics/`);
    const d = await r.json();

    document.getElementById('mv-queries').textContent = d.total_queries;
    document.getElementById('mv-docs').textContent    = d.total_documents;
    document.getElementById('mv-chunks').textContent  = d.total_chunks;
    document.getElementById('mv-tokens').textContent  = formatNum(d.total_tokens_used);
    document.getElementById('mv-cost').textContent    = '$' + d.estimated_total_cost_usd.toFixed(4);
    document.getElementById('mv-uptime').textContent  = formatUptime(d.uptime_seconds);

    // Latency bars
    const lat = d.latency;
    const max = Math.max(lat.p99_ms, 1);
    setLatBar('p50', lat.p50_ms, max);
    setLatBar('p95', lat.p95_ms, max);
    setLatBar('p99', lat.p99_ms, max);
    setLatBar('avg', lat.avg_ms,  max);

    // Recent queries table
    const tbody = document.getElementById('queries-tbody');
    if (!d.recent_queries || !d.recent_queries.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="empty-row">No queries yet</td></tr>';
    } else {
      tbody.innerHTML = d.recent_queries.slice().reverse().map(q => `
        <tr>
          <td>${formatDate(q.timestamp)}</td>
          <td>${escapeHtml((q.question || '').substring(0, 80))}${(q.question || '').length > 80 ? '…' : ''}</td>
          <td>${q.num_sources ?? '—'}</td>
          <td>${q.latency_ms != null ? q.latency_ms.toFixed(0) + 'ms' : '—'}</td>
          <td>${q.tokens_used ?? '—'}</td>
        </tr>`).join('');
    }
  } catch (err) {
    showToast('Could not load metrics. Is the server running?', 'error');
  }
}

function setLatBar(key, value, max) {
  const pct = Math.min((value / max) * 100, 100);
  document.getElementById(`lb-${key}`).style.width = pct + '%';
  document.getElementById(`lv-${key}`).textContent = value ? value.toFixed(0) + 'ms' : '—';
}

// ── Toast ─────────────────────────────────────────────────────────
function showToast(msg, type = 'info') {
  const c = document.getElementById('toast-container');
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => {
    t.style.animation = 'slideOut 0.3s ease forwards';
    setTimeout(() => t.remove(), 300);
  }, 4000);
}

// ── Helpers ───────────────────────────────────────────────────────
function fileIcon(name) {
  const ext = (name || '').split('.').pop().toLowerCase();
  return { pdf: '📕', txt: '📝', docx: '📘' }[ext] || '📄';
}

function formatBytes(b) {
  if (!b) return '0 B';
  if (b < 1024) return b + ' B';
  if (b < 1048576) return (b / 1024).toFixed(1) + ' KB';
  return (b / 1048576).toFixed(1) + ' MB';
}

function formatNum(n) {
  if (!n) return '0';
  return n.toLocaleString();
}

function formatDate(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' });
  } catch { return iso; }
}

function formatUptime(s) {
  if (!s) return '0s';
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = Math.floor(s % 60);
  if (h) return `${h}h ${m}m`;
  if (m) return `${m}m ${sec}s`;
  return `${sec}s`;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
