/**
 * Antigravity Prime - Mission Control UI
 * Simplified, clean UI inspired by OpenCode/Codex
 */

// Configuration
const CONFIG = {
    apiEndpoint: '/api',
    wsEndpoint: `ws://${window.location.host}/ws/ui`
};

// State
const state = {
    schema: null,
    parameters: {},
    selectedCategory: 'llm',
    activeTab: 'parameters',
    sessions: [],
    currentSession: null,
    isConnected: false,
    uptimeStart: Date.now()
};

// Initialize
document.addEventListener('DOMContentLoaded', init);

async function init() {
    console.log('[App] Starting...');
    
    try {
        await Promise.all([fetchSchema(), fetchParameters(), fetchSessions()]);
        initUI();
        updateConnectionStatus(true);
        showToast('Connected', 'success');
    } catch (e) {
        console.error('[App] Init failed:', e);
        loadDemoData();
        updateConnectionStatus(false);
        showToast('Demo mode', 'warning');
    }
    
    setInterval(updateUptime, 1000);
}

// API Functions
async function fetchSchema() {
    const res = await fetch(`${CONFIG.apiEndpoint}/ui-schema`);
    state.schema = await res.json();
}

async function fetchParameters() {
    const res = await fetch(`${CONFIG.apiEndpoint}/params`);
    state.parameters = await res.json();
}

async function fetchSessions() {
    try {
        const res = await fetch(`${CONFIG.apiEndpoint}/sessions`);
        const data = await res.json();
        state.sessions = data.sessions || [];
        if (state.sessions.length > 0) {
            state.currentSession = state.sessions[0];
        }
    } catch (e) {
        state.sessions = [{id: 'default', name: 'Default', active: true}];
        state.currentSession = state.sessions[0];
    }
}

// UI Initialization
function initUI() {
    renderSidebar();
    renderWorkbench();
    renderStatusBar();
    setupEventListeners();
}

function renderSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;
    
    const categories = state.schema?.categories || [];
    const categoryHtml = categories.map(cat => `
        <div class="nav-item ${cat.id === state.selectedCategory ? 'active' : ''}" data-category="${cat.id}">
            <span class="nav-icon">${getIcon(cat.id)}</span>
            <span class="nav-label">${cat.label}</span>
            <span class="nav-count">${cat.parameters?.length || 0}</span>
        </div>
    `).join('');
    
    sidebar.innerHTML = `
        <div class="sidebar-header">
            <div class="logo">
                <span class="logo-icon">Λ</span>
                <span class="logo-text">Antigravity</span>
            </div>
        </div>
        <div class="sidebar-section">
            <div class="section-title">Categories</div>
            <div class="nav-list">${categoryHtml}</div>
        </div>
        <div class="sidebar-section">
            <div class="section-title">Sessions</div>
            <div class="session-list">
                ${state.sessions.map(s => `
                    <div class="session-item ${s.active ? 'active' : ''}" data-session="${s.id}">
                        <span class="session-dot"></span>
                        <span class="session-name">${s.name}</span>
                    </div>
                `).join('')}
                <button class="new-session-btn" onclick="createSession()">+ New Session</button>
            </div>
        </div>
    `;
    
    // Add click handlers
    sidebar.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            state.selectedCategory = item.dataset.category;
            renderSidebar();
            renderContent();
        });
    });
}

function renderContent() {
    const content = document.getElementById('content');
    if (!content || !state.schema) return;
    
    const category = state.schema.categories.find(c => c.id === state.selectedCategory);
    if (!category) return;
    
    const paramsHtml = category.parameters.map(p => renderParameter(p)).join('');
    
    content.innerHTML = `
        <div class="content-header">
            <h2>${category.label}</h2>
            <span class="param-count">${category.parameters.length} parameters</span>
        </div>
        <div class="params-grid">${paramsHtml}</div>
    `;
}

function renderParameter(param) {
    const value = state.parameters[param.id] ?? param.default;
    const displayValue = formatValue(value);
    
    let controlHtml = '';
    
    if (param.type === 'boolean') {
        controlHtml = `
            <label class="toggle">
                <input type="checkbox" ${value ? 'checked' : ''} 
                    onchange="updateParam('${param.id}', this.checked)">
                <span class="toggle-slider"></span>
            </label>
        `;
    } else if (param.type === 'slider' || typeof value === 'number') {
        const min = param.min ?? 0;
        const max = param.max ?? 100;
        controlHtml = `
            <div class="slider-container">
                <input type="range" min="${min}" max="${max}" value="${value}"
                    oninput="this.nextElementSibling.textContent = this.value"
                    onchange="updateParam('${param.id}', parseFloat(this.value))">
                <span class="slider-value">${value}</span>
            </div>
        `;
    } else if (Array.isArray(value)) {
        controlHtml = `<div class="array-display">${value.length} items</div>`;
    } else if (typeof value === 'object') {
        controlHtml = `<div class="object-display">{...}</div>`;
    } else {
        controlHtml = `
            <input type="text" value="${escapeHtml(String(value))}" 
                onchange="updateParam('${param.id}', this.value)"
                class="text-input">
        `;
    }
    
    return `
        <div class="param-card">
            <div class="param-header">
                <span class="param-label">${param.label}</span>
                <span class="param-id">${param.id}</span>
            </div>
            <div class="param-control">${controlHtml}</div>
            <div class="param-desc">${param.description || ''}</div>
        </div>
    `;
}

function renderWorkbench() {
    const workbench = document.getElementById('workbench');
    if (!workbench) return;
    
    workbench.innerHTML = `
        <div class="workbench-header">
            <h3>Task Input</h3>
        </div>
        <div class="workbench-input">
            <textarea id="taskInput" placeholder="Describe what you want to build or fix..." rows="4"></textarea>
            <div class="input-actions">
                <button class="btn-secondary" onclick="clearOutput()">Clear</button>
                <button class="btn-primary" onclick="executeTask()">Run</button>
            </div>
        </div>
        <div class="workbench-output">
            <div class="output-header">
                <span>Output</span>
                <span class="output-status" id="outputStatus">Ready</span>
            </div>
            <pre id="outputContent"><code>Output will appear here...</code></pre>
        </div>
    `;
}

function renderStatusBar() {
    const statusbar = document.getElementById('statusbar');
    if (!statusbar) return;
    
    statusbar.innerHTML = `
        <div class="status-left">
            <span class="status-item">
                <span class="status-dot" id="connectionDot"></span>
                <span id="connectionText">Connected</span>
            </span>
            <span class="status-item">
                <span class="status-label">Session:</span>
                <span id="sessionName">${state.currentSession?.name || 'Default'}</span>
            </span>
        </div>
        <div class="status-right">
            <span class="status-item">
                <span class="status-label">Uptime:</span>
                <span id="uptime">00:00:00</span>
            </span>
            <span class="status-item">
                <span class="status-label">Params:</span>
                <span>${Object.keys(state.parameters).length}</span>
            </span>
        </div>
    `;
}

// Event Handlers
function setupEventListeners() {
    document.getElementById('taskInput')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            executeTask();
        }
    });
}

async function updateParam(id, value) {
    try {
        await fetch(`${CONFIG.apiEndpoint}/params/${id}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(value)
        });
        state.parameters[id] = value;
        showToast(`Updated ${id}`, 'success');
    } catch (e) {
        showToast('Update failed', 'error');
    }
}

async function executeTask() {
    const input = document.getElementById('taskInput');
    const output = document.getElementById('outputContent');
    const status = document.getElementById('outputStatus');
    
    if (!input?.value.trim()) {
        showToast('Enter a task', 'warning');
        return;
    }
    
    status.textContent = 'Running...';
    status.className = 'output-status running';
    
    try {
        const res = await fetch('/agent/execute', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({description: input.value})
        });
        
        const data = await res.json();
        output.querySelector('code').textContent = data.response || data.error || 'No response';
        status.textContent = 'Complete';
        status.className = 'output-status success';
    } catch (e) {
        output.querySelector('code').textContent = 'Error: ' + e.message;
        status.textContent = 'Error';
        status.className = 'output-status error';
    }
}

function clearOutput() {
    document.getElementById('outputContent').querySelector('code').textContent = 'Output will appear here...';
    document.getElementById('outputStatus').textContent = 'Ready';
}

async function createSession() {
    const name = prompt('Session name:');
    if (!name) return;
    
    try {
        await fetch(`${CONFIG.apiEndpoint}/sessions`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name})
        });
        await fetchSessions();
        renderSidebar();
        showToast('Session created', 'success');
    } catch (e) {
        showToast('Failed to create session', 'error');
    }
}

// Utilities
function formatValue(value) {
    if (Array.isArray(value)) return `[${value.length} items]`;
    if (typeof value === 'object' && value !== null) return '{...}';
    return String(value);
}

function escapeHtml(str) {
    return str.replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
}

function getIcon(id) {
    const icons = {
        llm: '🧠', sandbox: '📦', governance: '🛡️', mcp: '🔗',
        a2a: '🌐', server: '🖥️', observability: '📊', features: '⚡',
        vector_db: '💾', skills: '🎯', general: '⚙️'
    };
    return icons[id] || '📌';
}

function updateConnectionStatus(connected) {
    const dot = document.getElementById('connectionDot');
    const text = document.getElementById('connectionText');
    if (dot) dot.className = connected ? 'status-dot connected' : 'status-dot';
    if (text) text.textContent = connected ? 'Connected' : 'Disconnected';
}

function updateUptime() {
    const elapsed = Date.now() - state.uptimeStart;
    const h = Math.floor(elapsed / 3600000);
    const m = Math.floor((elapsed % 3600000) / 60000);
    const s = Math.floor((elapsed % 60000) / 1000);
    const el = document.getElementById('uptime');
    if (el) {
        el.textContent = `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toasts') || (() => {
        const el = document.createElement('div');
        el.id = 'toasts';
        el.className = 'toast-container';
        document.body.appendChild(el);
        return el;
    })();
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    
    setTimeout(() => toast.remove(), 3000);
}

function loadDemoData() {
    state.schema = {
        categories: [
            {id: 'llm', label: 'LLM & Models', parameters: [
                {id: 'llm.model', label: 'Model', type: 'text', default: 'qwen2.5-coder'},
                {id: 'llm.temperature', label: 'Temperature', type: 'slider', default: 0.7, min: 0, max: 2},
                {id: 'llm.max_tokens', label: 'Max Tokens', type: 'slider', default: 4096, min: 100, max: 128000}
            ]},
            {id: 'sandbox', label: 'Sandbox', parameters: [
                {id: 'sandbox.timeout', label: 'Timeout (s)', type: 'slider', default: 300, min: 1, max: 3600},
                {id: 'sandbox.memory_mb', label: 'Memory (MB)', type: 'slider', default: 512, min: 64, max: 8192}
            ]},
            {id: 'mcp', label: 'MCP Servers', parameters: [
                {id: 'mcp.enabled', label: 'MCP Enabled', type: 'boolean', default: true}
            ]}
        ]
    };
    
    state.parameters = {
        'llm.model': 'qwen2.5-coder',
        'llm.temperature': 0.7,
        'llm.max_tokens': 4096,
        'sandbox.timeout': 300,
        'sandbox.memory_mb': 512,
        'mcp.enabled': true
    };
    
    state.sessions = [{id: 'default', name: 'Default', active: true}];
    state.currentSession = state.sessions[0];
    
    renderSidebar();
    renderWorkbench();
    renderStatusBar();
}