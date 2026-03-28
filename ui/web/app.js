/**
 * Antigravity Prime - Mission Control UI
 * 
 * Dynamic single-page application that:
 * - Fetches UI schema from backend
 * - Renders controls automatically based on parameter types
 * - Connects via WebSocket for real-time updates
 * - Provides smart category-based organization
 * 
 * Lightweight implementation using vanilla JS with ES modules
 */

// ============================================================================
// Configuration
// ============================================================================
const CONFIG = {
    wsEndpoint: `ws://${window.location.host}/ws/ui`,
    apiEndpoint: '/api',
    reconnectDelay: 3000,
    maxReconnectAttempts: 10,
    eventBufferSize: 100
};

// ============================================================================
// State Management
// ============================================================================
class AppState {
    constructor() {
        this.schema = null;
        this.parameters = {};
        this.ws = null;
        this.reconnectAttempts = 0;
        this.isConnected = false;
        this.selectedCategory = null;
        this.activeTab = 'parameters';
        this.uptimeStart = Date.now();
        this.eventHistory = [];
        this.searchResults = [];
    }
}

const state = new AppState();

// ============================================================================
// WebSocket Manager
// ============================================================================
class WebSocketManager {
    constructor() {
        this.ws = null;
        this.messageHandlers = new Map();
        this.pendingRequests = new Map();
    }

    async connect() {
        return new Promise((resolve, reject) => {
            try {
                this.ws = new WebSocket(CONFIG.wsEndpoint);

                this.ws.onopen = () => {
                    console.log('[WS] Connected');
                    state.isConnected = true;
                    state.reconnectAttempts = 0;
                    updateConnectionStatus(true);
                    this.send('GET_SCHEMA', {}).then(resolve);
                };

                this.ws.onmessage = (event) => {
                    try {
                        const message = JSON.parse(event.data);
                        this.handleMessage(message);
                    } catch (e) {
                        console.error('[WS] Parse error:', e);
                    }
                };

                this.ws.onclose = () => {
                    console.log('[WS] Disconnected');
                    state.isConnected = false;
                    updateConnectionStatus(false);
                    this.attemptReconnect();
                };

                this.ws.onerror = (error) => {
                    console.error('[WS] Error:', error);
                    reject(error);
                };

            } catch (e) {
                reject(e);
            }
        });
    }

    attemptReconnect() {
        if (state.reconnectAttempts < CONFIG.maxReconnectAttempts) {
            state.reconnectAttempts++;
            console.log(`[WS] Reconnecting... attempt ${state.reconnectAttempts}`);
            setTimeout(() => this.connect(), CONFIG.reconnectDelay);
        }
    }

    send(method, params = {}) {
        return new Promise((resolve, reject) => {
            if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
                reject(new Error('WebSocket not connected'));
                return;
            }

            const id = crypto.randomUUID();
            const message = { id, method, params };
            
            this.pendingRequests.set(id, { resolve, reject, timeout: setTimeout(() => {
                this.pendingRequests.delete(id);
                reject(new Error('Request timeout'));
            }, 10000) });

            this.ws.send(JSON.stringify(message));
        });
    }

    handleMessage(message) {
        const { id, type, method, result, error, event_type, data } = message;

        if (type === 'response' && id && this.pendingRequests.has(id)) {
            const { resolve, reject, timeout } = this.pendingRequests.get(id);
            clearTimeout(timeout);
            this.pendingRequests.delete(id);
            if (error) {
                reject(new Error(error));
            } else {
                resolve(result);
            }
            return;
        }

        if (type === 'event') {
            this.handleEvent(event_type, data);
        }
    }

    handleEvent(eventType, data) {
        switch (eventType) {
            case 'param_changed':
                handleParamChange(data);
                break;
            case 'buffered_events':
                data.forEach(e => this.handleEvent(e.event_type, e.data));
                break;
            case 'task_update':
                handleTaskUpdate(data);
                break;
            case 'agent_activity':
                handleAgentActivity(data);
                break;
            case 'reasoning_stream':
                handleReasoningStream(data);
                break;
            case 'system_metrics':
                handleSystemMetrics(data);
                break;
        }
    }
}

const wsManager = new WebSocketManager();

// ============================================================================
// Schema & Parameter Management
// ============================================================================
async function fetchSchema() {
    try {
        const response = await fetch(`${CONFIG.apiEndpoint}/ui-schema`);
        const schema = await response.json();
        state.schema = schema;
        renderCategories(schema.categories);
        renderControls(schema.categories);
        console.log(`[Schema] Loaded ${schema.total_parameters} parameters in ${schema.categories.length} categories`);
    } catch (e) {
        console.error('[Schema] Failed to load:', e);
        showToast('Failed to load schema', 'error');
    }
}

async function fetchParameters() {
    try {
        const response = await fetch(`${CONFIG.apiEndpoint}/params`);
        const params = await response.json();
        state.parameters = params;
    } catch (e) {
        console.error('[Params] Failed to load:', e);
    }
}

async function setParameter(paramId, value) {
    try {
        const response = await fetch(`${CONFIG.apiEndpoint}/params/${paramId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(value)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail);
        }
        
        state.parameters[paramId] = value;
        showToast(`Updated ${paramId}`, 'success');
        
        const control = document.querySelector(`[data-param-id="${paramId}"]`);
        if (control) {
            control.classList.add('modified');
        }
        
    } catch (e) {
        console.error('[SetParam] Failed:', e);
        showToast(e.message, 'error');
    }
}

// ============================================================================
// UI Rendering
// ============================================================================
function renderCategories(categories) {
    const nav = document.getElementById('categoryNav');
    nav.innerHTML = '';

    categories.forEach((category, index) => {
        const item = document.createElement('button');
        item.className = `category-item${index === 0 ? ' active' : ''}`;
        item.dataset.category = category.id;
        item.innerHTML = `
            <span class="category-icon">${getCategoryIcon(category.id)}</span>
            <span class="category-label">${category.label}</span>
            <span class="category-count">${category.parameters.length}</span>
        `;
        item.addEventListener('click', () => selectCategory(category.id));
        nav.appendChild(item);
    });

    if (categories.length > 0) {
        selectCategory(categories[0].id);
    }
}

function getCategoryIcon(categoryId) {
    const icons = {
        llm: '🧠',
        sandbox: '📦',
        orchestrator: '⚙️',
        governance: '🛡️',
        memory: '💾',
        observability: '📊',
        mcp: '🔗',
        a2a: '🌐',
        server: '🖥️',
        features: '⚡',
        general: '⚙️'
    };
    return icons[categoryId] || '📌';
}

function selectCategory(categoryId) {
    state.selectedCategory = categoryId;
    
    document.querySelectorAll('.category-item').forEach(item => {
        item.classList.toggle('active', item.dataset.category === categoryId);
    });

    renderControls(state.schema?.categories || []);
}

function renderControls(categories) {
    const container = document.getElementById('controlsContainer');
    container.innerHTML = '';

    const category = categories.find(c => c.id === state.selectedCategory);
    if (!category) {
        container.innerHTML = '<div class="empty-state"><p>No parameters</p></div>';
        return;
    }

    category.parameters.forEach(param => {
        const control = createControl(param);
        container.appendChild(control);
    });
}

function createControl(param) {
    const item = document.createElement('div');
    item.className = 'control-item';
    item.dataset.paramId = param.id;

    const value = state.parameters[param.id] ?? param.default;

    let inputHtml = '';
    switch (param.type) {
        case 'slider':
            inputHtml = `
                <div class="slider-control">
                    <input type="range" class="slider-input" 
                        min="${param.min ?? 0}" 
                        max="${param.max ?? 100}" 
                        step="${param.step ?? 1}"
                        value="${value}">
                    <span class="slider-value">${value}${param.unit || ''}</span>
                </div>
            `;
            break;
            
        case 'boolean':
            inputHtml = `
                <div class="toggle-control">
                    <span class="toggle-value">${value ? 'Enabled' : 'Disabled'}</span>
                    <div class="toggle-switch${value ? ' active' : ''}" data-param="${param.id}"></div>
                </div>
            `;
            break;
            
        case 'select':
            const options = param.options || [];
            inputHtml = `
                <select class="select-control" data-param="${param.id}">
                    ${options.map(opt => `<option value="${opt}"${opt === value ? ' selected' : ''}>${opt}</option>`).join('')}
                </select>
            `;
            break;
            
        case 'password':
            inputHtml = `
                <input type="password" class="text-input" 
                    value="${value || ''}" 
                    placeholder="Enter value..."
                    data-param="${param.id}">
            `;
            break;
            
        default:
            inputHtml = `
                <input type="text" class="text-input" 
                    value="${value || ''}" 
                    data-param="${param.id}">
            `;
    }

    item.innerHTML = `
        <div class="control-label">
            <span>${param.label}</span>
            <span class="control-id">${param.id}</span>
        </div>
        ${inputHtml}
    `;

    item.querySelectorAll('input, select').forEach(input => {
        const paramId = input.dataset.param;
        
        if (input.type === 'range') {
            input.addEventListener('input', (e) => {
                const value = parseFloat(e.target.value);
                const valueSpan = item.querySelector('.slider-value');
                valueSpan.textContent = `${value}${param.unit || ''}`;
            });
            input.addEventListener('change', (e) => {
                setParameter(paramId, parseFloat(e.target.value));
            });
        }
        
        if (input.tagName === 'SELECT') {
            input.addEventListener('change', (e) => {
                setParameter(paramId, e.target.value);
            });
        }
        
        if (input.type === 'text' || input.type === 'password') {
            input.addEventListener('change', (e) => {
                setParameter(paramId, e.target.value);
            });
        }
    });

    const toggle = item.querySelector('.toggle-switch');
    if (toggle) {
        toggle.addEventListener('click', () => {
            const paramId = toggle.dataset.param;
            const newValue = !state.parameters[paramId];
            setParameter(paramId, newValue);
            toggle.classList.toggle('active', newValue);
            toggle.parentElement.querySelector('.toggle-value').textContent = newValue ? 'Enabled' : 'Disabled';
        });
    }

    return item;
}

function handleParamChange(data) {
    const { param_id, new_value } = data;
    state.parameters[param_id] = new_value;
    
    const control = document.querySelector(`[data-param-id="${param_id}"]`);
    if (control) {
        const input = control.querySelector('input, select');
        if (input) {
            if (input.type === 'range') {
                input.value = new_value;
                const valueSpan = control.querySelector('.slider-value');
                valueSpan.textContent = new_value;
            } else if (input.tagName === 'SELECT') {
                input.value = new_value;
            } else {
                input.value = new_value;
            }
        }
        
        const toggle = control.querySelector('.toggle-switch');
        if (toggle) {
            toggle.classList.toggle('active', new_value);
        }
    }
}

// ============================================================================
// Event Handlers
// ============================================================================
function handleTaskUpdate(data) {
    document.getElementById('taskCount').textContent = `${data.active || 0} Active`;
    
    const content = document.getElementById('reactContent');
    if (data.status === 'reasoning') {
        addReasoningStep('reasoning', data.thought || 'Analyzing request...');
    } else if (data.status === 'planning') {
        addReasoningStep('planning', 'Planning execution steps...');
    } else if (data.status === 'acting') {
        addReasoningStep('acting', data.action || 'Executing...');
    } else if (data.status === 'complete') {
        addReasoningStep('result', 'Task completed');
        updateOutput(data.result || '');
    }
}

function handleAgentActivity(data) {
    const agentList = document.getElementById('agentList');
    document.getElementById('agentCount').textContent = `${data.agents?.length || 0} active`;
    
    if (!data.agents || data.agents.length === 0) {
        agentList.innerHTML = '<div class="agent-empty">No active agents</div>';
        return;
    }
    
    agentList.innerHTML = data.agents.map(agent => `
        <div class="agent-item">
            <span class="agent-status ${agent.status}"></span>
            <span class="agent-name">${agent.name}</span>
            <span class="agent-task">${agent.task || ''}</span>
        </div>
    `).join('');
}

function handleReasoningStream(data) {
    const stream = document.getElementById('reasoningStream');
    
    const empty = stream.querySelector('.stream-empty');
    if (empty) empty.remove();
    
    const item = document.createElement('div');
    item.className = `stream-item ${data.type || 'thinking'}`;
    item.innerHTML = `
        <span class="stream-time">${new Date().toLocaleTimeString()}</span>
        <span class="stream-text">${data.content || ''}</span>
    `;
    
    stream.insertBefore(item, stream.firstChild);
    
    while (stream.children.length > 50) {
        stream.removeChild(stream.lastChild);
    }

    updateReActStage(data.stage);
}

function updateReActStage(stage) {
    document.querySelectorAll('.stage').forEach(el => {
        el.classList.remove('active', 'completed');
    });
    
    if (stage) {
        const stageEl = document.querySelector(`[data-stage="${stage}"]`);
        if (stageEl) {
            stageEl.classList.add('active');
            const allStages = ['reasoning', 'planning', 'acting', 'observing'];
            const stageIndex = allStages.indexOf(stage);
            allStages.forEach((s, i) => {
                if (i < stageIndex) {
                    const el = document.querySelector(`[data-stage="${s}"]`);
                    if (el) el.classList.add('completed');
                }
            });
        }
    }
}

function addReasoningStep(type, content) {
    const container = document.getElementById('reactContent');
    const empty = container.querySelector('.empty-state');
    if (empty) empty.remove();
    
    const step = document.createElement('div');
    step.className = `reasoning-step`;
    step.innerHTML = `
        <div class="step-label">${type}</div>
        <div class="step-content">${content}</div>
    `;
    
    container.appendChild(step);
    container.scrollTop = container.scrollHeight;
}

function handleSystemMetrics(data) {
    if (data.cpu !== undefined) {
        document.getElementById('cpuBar').style.width = `${data.cpu}%`;
        document.getElementById('cpuValue').textContent = `${data.cpu}%`;
    }
    if (data.memory !== undefined) {
        document.getElementById('memBar').style.width = `${data.memory}%`;
        document.getElementById('memValue').textContent = `${data.memory}%`;
    }
    if (data.gpu !== undefined) {
        document.getElementById('gpuBar').style.width = `${data.gpu}%`;
        document.getElementById('gpuValue').textContent = `${data.gpu}%`;
    }
    if (data.latency !== undefined) {
        document.getElementById('latencyValue').textContent = `${data.latency}ms`;
    }
}

// ============================================================================
// UI Utilities
// ============================================================================
function updateConnectionStatus(connected) {
    const wsStatus = document.getElementById('wsStatus');
    const wsStatusText = document.getElementById('wsStatusText');
    
    if (connected) {
        wsStatus.classList.add('connected');
        wsStatusText.textContent = 'Connected';
    } else {
        wsStatus.classList.remove('connected');
        wsStatusText.textContent = 'Disconnected';
    }
}

function updateUptime() {
    const elapsed = Date.now() - state.uptimeStart;
    const hours = Math.floor(elapsed / 3600000);
    const minutes = Math.floor((elapsed % 3600000) / 60000);
    const seconds = Math.floor((elapsed % 60000) / 1000);
    
    document.getElementById('uptime').textContent = 
        `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

function updateLastSync() {
    document.getElementById('lastSync').textContent = new Date().toLocaleTimeString();
}

function updateOutput(text) {
    const output = document.getElementById('responseOutput');
    output.querySelector('code').textContent = text || '// Output will appear here...';
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icons = {
        success: '✓',
        error: '✕',
        warning: '⚠',
        info: 'ℹ'
    };
    
    toast.innerHTML = `
        <span class="toast-icon">${icons[type]}</span>
        <span class="toast-message">${message}</span>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ============================================================================
// Search Functionality
// ============================================================================
function initSearch() {
    const searchInput = document.getElementById('globalSearch');
    const searchResults = document.getElementById('searchResults');
    
    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        if (query.length < 2) {
            searchResults.classList.remove('active');
            return;
        }
        
        performSearch(query);
    });
    
    searchInput.addEventListener('focus', () => {
        if (searchInput.value.trim().length >= 2) {
            searchResults.classList.add('active');
        }
    });
    
    document.addEventListener('click', (e) => {
        if (!searchResults.contains(e.target) && e.target !== searchInput) {
            searchResults.classList.remove('active');
        }
    });
    
    document.addEventListener('keydown', (e) => {
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
            e.preventDefault();
            searchInput.focus();
        }
    });
}

function performSearch(query) {
    if (!state.schema) return;
    
    const results = [];
    const queryLower = query.toLowerCase();
    
    state.schema.categories.forEach(cat => {
        cat.parameters.forEach(param => {
            if (param.label.toLowerCase().includes(queryLower) ||
                param.id.toLowerCase().includes(queryLower) ||
                param.description?.toLowerCase().includes(queryLower)) {
                results.push({ ...param, category: cat.label });
            }
        });
    });
    
    renderSearchResults(results.slice(0, 10));
}

function renderSearchResults(results) {
    const container = document.getElementById('searchResults');
    
    if (results.length === 0) {
        container.innerHTML = '<div class="search-result-item"><span class="result-info">No results found</span></div>';
    } else {
        container.innerHTML = results.map(r => `
            <div class="search-result-item" data-param="${r.id}">
                <span class="result-icon">${getCategoryIcon(r.category.toLowerCase())}</span>
                <span class="result-info">
                    <span class="result-label">${r.label}</span>
                    <span class="result-id">${r.id}</span>
                </span>
                <span class="result-category">${r.category}</span>
            </div>
        `).join('');
        
        container.querySelectorAll('.search-result-item').forEach(item => {
            item.addEventListener('click', () => {
                const paramId = item.dataset.param;
                const category = state.schema.categories.find(c => 
                    c.parameters.some(p => p.id === paramId)
                );
                if (category) {
                    selectCategory(category.id);
                    document.getElementById('searchResults').classList.remove('active');
                    document.getElementById('globalSearch').value = '';
                }
            });
        });
    }
    
    container.classList.add('active');
}

// ============================================================================
// Tab Handling
// ============================================================================
function initTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            state.activeTab = tab;
            
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.getElementById(`${tab}Tab`).classList.add('active');
        });
    });
}

function initOutputTabs() {
    document.querySelectorAll('.output-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.output-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
        });
    });
}

// ============================================================================
// Task Execution
// ============================================================================
function initTaskInput() {
    const input = document.getElementById('taskInput');
    const charCount = document.getElementById('charCount');
    const runBtn = document.getElementById('runTaskBtn');
    
    input.addEventListener('input', () => {
        charCount.textContent = input.value.length;
    });
    
    runBtn.addEventListener('click', () => executeTask(input.value));
    
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
            executeTask(input.value);
        }
    });
}

async function executeTask(description) {
    if (!description.trim()) return;
    
    const btn = document.getElementById('runTaskBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner" style="width:14px;height:14px;"></span> Running';
    
    try {
        const response = await fetch('/agent/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ description })
        });
        
        const result = await response.json();
        
        if (result.response) {
            updateOutput(result.response);
        }
        
        showToast('Task completed', 'success');
    } catch (e) {
        console.error('[Task] Failed:', e);
        showToast('Task failed: ' + e.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg> Execute';
    }
}

// ============================================================================
// Initialize Application
// ============================================================================
async function init() {
    console.log('[App] Initializing...');
    
    try {
        await wsManager.connect();
        await fetchSchema();
        await fetchParameters();
        
        initTabs();
        initOutputTabs();
        initSearch();
        initTaskInput();
        
        setInterval(updateUptime, 1000);
        setInterval(updateLastSync, 5000);
        
        simulateInitialData();
        
        console.log('[App] Ready');
        showToast('Connected to backend', 'success');
        
    } catch (e) {
        console.error('[App] Init failed:', e);
        showToast('Connection failed, retrying...', 'warning');
        setTimeout(init, 5000);
    }
}

function simulateInitialData() {
    document.getElementById('meshStatus').textContent = '3 Nodes';
    document.getElementById('taskCount').textContent = '0 Active';
    document.getElementById('tokenCount').textContent = '0';
    
    setTimeout(() => {
        handleReasoningStream({ type: 'thinking', content: 'Analyzing request context...', stage: 'reasoning' });
    }, 1500);
    
    setTimeout(() => {
        handleReasoningStream({ type: 'action', content: 'Checking available tools and agents...', stage: 'planning' });
    }, 3000);
}

document.addEventListener('DOMContentLoaded', init);