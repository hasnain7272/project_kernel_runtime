import { spatialEngine } from './spatial_engine.js';

class SovereignApp {
    constructor() {
        this.apiBase = ''; // Relative paths
        this.lastThoughtTime = 0;
        this.activeMissions = new Map();
        
        // UI Elements
        this.els = {
            meshStatus: document.getElementById('ui-mesh-status'),
            credits: document.getElementById('ui-credits'),
            secScore: document.getElementById('ui-sec-score'),
            mcpList: document.getElementById('ui-mcp-list'),
            missionGrid: document.getElementById('ui-mission-grid'),
            thoughtStream: document.getElementById('ui-thought-stream'),
            input: document.getElementById('ui-input'),
            vlmSelect: document.getElementById('vlm-engine'),
            activeTaskCount: document.getElementById('active-task-count')
        };

        this.init();
    }

    init() {
        console.log("Sovereign Mission Control: CORE INITIALIZATION");
        
        // Event Listeners
        this.els.input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.dispatchDirective();
        });
        
        this.els.vlmSelect.addEventListener('change', (e) => this.updateVlm(e.target.value));
        
        // Start Heartbeat
        this.startHeartbeat();
        
        // Restore Scratchpad
        const saved = localStorage.getItem('sovereign_scratchpad');
        if (saved) document.getElementById('ui-scratchpad').value = saved;
        
        document.getElementById('ui-scratchpad').addEventListener('input', (e) => {
            localStorage.setItem('sovereign_scratchpad', e.target.value);
        });

        // Push initial state
        this.syncIntelligence();
    }

    async startHeartbeat() {
        this.heartbeat = setInterval(() => {
            this.syncIntelligence();
            this.syncThoughts();
            this.syncMcps();
        }, 2000);
    }

    async syncIntelligence() {
        try {
            const res = await fetch(`${this.apiBase}/status/intelligence?user_id=root`);
            if (!res.ok) return;
            
            const data = await res.json();
            const { hub, security, a2a_peers_count, a2a_peers, recent_tasks } = data;

            // Updated Telemetry
            this.els.meshStatus.innerText = `${a2a_peers_count} PEERS • LIVE`;
            this.els.credits.innerText = hub?.credits?.balance?.toFixed(2) || "0.00";
            
            // Fix: Security score might be a nested object or a primitive
            let scoreVal = security;
            if (typeof security === 'object' && security !== null) {
                scoreVal = security.status_score || security.score || 98;
            }
            this.els.secScore.innerText = `${scoreVal}%`;
            
            this.els.activeTaskCount.innerText = `${recent_tasks?.length || 0} ACTIVE`;

            // Update Active Mind Telemetry
            if (data.active_mind) {
                const mindEl = document.getElementById('ui-active-mind');
                if (mindEl) {
                    mindEl.innerHTML = `
                        <span style="color:var(--primary)">${data.active_mind.model}</span>
                        <span style="font-size:0.6rem; opacity:0.5;">[${data.active_mind.provider}]</span>
                    `;
                }
            }

            // Update Mesh Topology
            if (a2a_peers) {
                a2a_peers.forEach(peer => {
                    spatialEngine.addNode(peer.id, 'agent', peer);
                });
            }

            // Update Mission Grid
            this.renderMissionGrid(recent_tasks);

        } catch (e) {
            console.warn("Intelligence sync interrupted:", e);
            this.els.meshStatus.innerText = "OFFLINE";
        }
    }

    async syncThoughts() {
        try {
            const res = await fetch(`${this.apiBase}/intelligence/thoughts`);
            if (!res.ok) return;
            
            const { thoughts } = await res.json();
            if (!thoughts?.length) return;

            const newThoughts = thoughts.filter(t => (t.timestamp * 1000) > this.lastThoughtTime);
            
            newThoughts.forEach(t => {
                this.renderThought(t);
                this.lastThoughtTime = t.timestamp * 1000;
                
                // Animate node pulse in 3D scene
                if (spatialEngine.nodes.has(t.agent_id)) {
                    spatialEngine.handleNodeInteraction(spatialEngine.nodes.get(t.agent_id));
                }
            });
        } catch (e) {}
    }

    async syncMcps() {
        try {
            const res = await fetch(`${this.apiBase}/intelligence/mcp/discovery`);
            if (!res.ok) return;
            const { servers } = await res.json();
            
            if (servers && servers.length > 0) {
                this.els.mcpList.innerHTML = servers.map(s => {
                    const statusColor = s.status === 'connected' ? 'var(--success)' : 'var(--warning)';
                    return `
                        <div class="mcp-unit" style="padding:0.75rem; background:rgba(255,255,255,0.03); border-radius:8px; border:1px solid var(--glass-border); animation: slideIn 0.3s ease-out;">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                                <span class="mono" style="color:${statusColor}">${s.name || s.url}</span>
                                <span class="tag" style="background:${statusColor}22; color:${statusColor}">${s.status?.toUpperCase() || 'PROBING'}</span>
                            </div>
                            <div style="display:flex; gap:0.5rem;">
                                <button onclick="reprobeMcp('${s.url}')" class="tag" style="border:none; cursor:pointer; background:rgba(255,255,255,0.1); font-weight:600;">RE-PROBE</button>
                                <button onclick="launchAppForMcp('${s.name}')" class="tag" style="border:none; cursor:pointer; background:rgba(0,229,255,0.1); color:var(--primary); font-weight:600;">BOOT HUB</button>
                            </div>
                        </div>
                    `;
                }).join("");
                
                servers.forEach(s => {
                    spatialEngine.addNode(s.name, 'mcp', s);
                });
            }
        } catch (e) {}
    }

    renderMissionGrid(tasks) {
        if (!tasks || tasks.length === 0) {
            this.els.missionGrid.innerHTML = `
                <div style="display:flex; align-items:center; justify-content:center; height:100%; opacity:0.3; width:100%;">
                    <span class="tele-label">_ Awaiting Directive Injection...</span>
                </div>`;
            return;
        }

        this.els.missionGrid.innerHTML = tasks.map(t => {
            const isRunning = t.status === "running";
            return `
                <div class="mission-unit">
                    <div class="unit-status">
                        <span class="mono" style="color:var(--text-mute)">${t.id.substring(0,8)}</span>
                        <span class="tag ${isRunning ? 'running pulse' : 'success'}">${t.status}</span>
                    </div>
                    <div style="font-size:0.85rem; font-weight:500; color:var(--primary);">${t.type?.toUpperCase()}</div>
                    <div style="font-size:0.75rem; color:var(--text-dim); line-height:1.4;">${t.description}</div>
                </div>
            `;
        }).join("");
    }

    renderThought(t) {
        const frame = document.createElement('div');
        frame.className = 'thought-frame';
        frame.innerHTML = `
            <div class="agent"><span>${t.agent_id || 'System'}</span></div>
            <div class="content">${t.thought}</div>
            <div class="timestamp">${new Date(t.timestamp*1000).toLocaleTimeString()}</div>
        `;
        this.els.thoughtStream.prepend(frame);
        
        while (this.els.thoughtStream.children.length > 30) {
            this.els.thoughtStream.removeChild(this.els.thoughtStream.lastChild);
        }
    }

    async dispatchDirective() {
        const val = this.els.input.value.trim();
        if (!val) return;
        
        this.els.input.value = "";
        this.renderThought({
            agent_id: 'User',
            thought: `Dispatching directive: ${val}`,
            timestamp: Date.now() / 1000
        });

        try {
            const res = await fetch(`${this.apiBase}/tasks`, {
                method: "POST", headers: {"Content-Type":"application/json"},
                body: JSON.stringify({ 
                    user_id: "root", 
                    task_type: "custom", 
                    description: val, 
                    steps: [
                        {id: "s1", description: "Initialize mesh context", tools: []},
                        {id: "s2", description: "Execute A2A Swarm logic", tools: []}
                    ] 
                })
            });
            const task = await res.json();
            if (task?.task_id) {
                await fetch(`${this.apiBase}/tasks/${task.task_id}/execute`, {
                    method: "POST", headers: {"Content-Type":"application/json"},
                    body: JSON.stringify({ user_id:"root" })
                });
            }
        } catch (e) {
            console.error("Directive dispatch failed:", e);
        }
    }

    async updateVlm(modelId) {
        try {
            await fetch(`${this.apiBase}/intelligence/vision/config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_id: modelId })
            });
        } catch (e) {}
    }

    async dispatchScratchpad() {
        const code = document.getElementById('ui-scratchpad').value.trim();
        if (!code) return;
        
        this.renderThought({
            agent_id: 'User',
            thought: `Dispatching Scratchpad Script: \n${code.substring(0, 50)}...`,
            timestamp: Date.now() / 1000
        });

        try {
            const res = await fetch(`${this.apiBase}/intelligence/scratchpad/dispatch`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ script: code })
            });
            const data = await res.json();
            if (data.status === "success") {
                console.log("Scratchpad Dispatched Successfully");
            }
        } catch (e) {
            console.error("Scratchpad dispatch failed:", e);
        }
    }

    focusNode(nodeId) {
        console.log(`Focusing on node: ${nodeId}`);
        // Highlight logic here
    }
}

// Initialize Application
window.appController = new SovereignApp();

// Globals for simple HTML onclick handlers
window.addMcp = async () => {
    const url = document.getElementById('mcp-url').value;
    if (!url) return;
    try {
        await fetch('/intelligence/mcp/discover', { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url })
        });
        document.getElementById('mcp-url').value = '';
    } catch (e) {}
};

window.dispatchDirective = () => window.appController.dispatchDirective();

window.reprobeMcp = async (url) => {
    try {
        await fetch('/intelligence/mcp/reprobe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url })
        });
    } catch (e) {}
};

window.launchAppForMcp = async (appName) => {
    // True Neutrality: We send the raw Hub Name to the kernel.
    // The InstanceManager handles the mapping via its internal AppRegistry.
    try {
        await fetch('/intelligence/mcp/launch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ app_name: appName })
        });
    } catch (e) {}
};

window.dispatchScratchpad = () => window.appController.dispatchScratchpad();
