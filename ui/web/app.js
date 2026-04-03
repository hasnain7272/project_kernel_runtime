function agenticIde() {
  return {
    vantaEffect: null,
    navTab: "explorer",
    midTab: "code",
    termTab: "terminal",
    activeModel: "ollama/qwen2.5-coder:7b-instruct-q4_K_M",
    activeSessionId: "",
    newFolder: "",
    byokProvider: "anthropic",
    byokKey: "",
    dragOver: false,

    // Core Session State
    loadedSessions: [],
    activeSession: null,
    project: { skills: [], mcp_servers: [], folders: [], a2a: { peers: [], mesh: {} } },
    ops: {
      health: null,
      fullStatus: null,
      providers: null,
      events: [],
      workflow: { active: false, name: "", step: 0, total: 0 }
    },

    // Dynamic Schema
    uiSchema: [],

    // NVIDIA NIM Config
    nvidiaNimBase: "",
    nvidiaNimKey: "",
    
    // Session Governance
    sessionFolder: "",
    sessionFolders: [],

    // IDE Panes Info
    explorerNodes: [],
    selectedFile: null,
    selectedFileContent: "",

    // Chat & Terminal
    chatLog: [],
    userInput: "",
    isExecuting: false,
    terminalCommand: "",
    terminalOutput: "Agentic OS v2 Terminal initialized.",
    terminalBusy: false,
    currentAgentStatus: "",
    shelfPulse: false,
    pendingApproval: null,
    selectedNode: null,
    missions: [],
    
    // MCP Mounting State
    newMcp: { name: "", command: "", args: "" },
    showMcpForm: false,
    
    // Governance State
    governanceMode: "auto",
    requireApprovalFor: "bash_execute,git_commit",
    newKnowledge: "",
    isInjecting: false,
    swarmAgents: [],
    credits: { tool_calls_remaining: 0, tokens_remaining: 0, compute_seconds_remaining: 0 },

    memoryResults: [],
    memoryQuery: "",
    meshGraph: null,
    ws: null,

    // UI Visual Themes
    MCP_VISUALS: {
      "3d": { color: "#ff9900", icon: "box", geometry: "cube" },
      "web": { color: "#06b6d4", icon: "globe", geometry: "sphere" },
      "system": { color: "#94a3b8", icon: "terminal", geometry: "box" },
      "default": { color: "#38bdf8", icon: "orbit", geometry: "sphere" }
    },

    pollInterval: null,
    justGotResponse: false,

    async api(url, options = {}) {
      const response = await fetch(url, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options
      });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `${response.status} ${response.statusText}`);
      }
      if (response.status === 204) return null;
      return response.json();
    },

    normalizeSession(session) {
      return {
        ...session,
        skills: session.skills || [],
        mcp_servers: session.mcp_servers || [],
        folders: session.folders || [],
        a2a_enabled: !!session.a2a_enabled,
        a2a_peers: session.a2a_peers || []
      };
    },

    async bootstrap() {
      // Initialize 3D Backdrop
      if (window.VANTA && window.VANTA.FOG) {
        this.vantaEffect = VANTA.FOG({
          el: "#vanta-backdrop",
          mouseControls: true,
          touchControls: true,
          blurFactor: 0.65,
          zoom: 1.5,
          baseColor: 0x03040b,
          highlightColor: 0x4ade80,
          midtoneColor: 0x1d4ed8,
          lowlightColor: 0x0f172a
        });
      }

      await this.refreshAll();
      this.initSplitPanes();
      this.loadUiSchema();
      this.setupWebSocket();

      this.$nextTick(() => {
        if (window.lucide) lucide.createIcons();
      });
    },

    setupWebSocket() {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsUrl = `${protocol}//${window.location.host}/ws/ui?client_id=${Math.random().toString(36).substring(7)}`;

      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log("[WS] Connected to Agentic OS Stream");
        this.ws.send(JSON.stringify({
          type: "command",
          method: "SUBSCRIBE",
          params: { events: ["tool.called", "tool.result", "param_changed", "agent.thought", "tool.executing", "task.completed", "task.failed"] }
        }));
      };

      this.ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === "event") {
          this.handleLiveEvent(msg);
        }
      };

      this.ws.onclose = () => {
        console.warn("[WS] Disconnected. Retrying in 5s...");
        setTimeout(() => this.setupWebSocket(), 5000);
      };
    },

    handleLiveEvent(event) {
      const type = event.event_type;
      const data = event.data;

      if (type === "agent.thought") {
        this.currentAgentStatus = data.content;
        this.terminalOutput += `\n[THOUGHT] ${data.content}`;
        this.scrollToBottomTerminal();
      }

      // New: Manager thinking states
      if (type === "agent.thinking") {
        this.currentAgentStatus = `[${data.status.toUpperCase()}] ${data.task || ''}`;
        this.terminalOutput += `\n[${data.status.toUpperCase()}] ${data.task || ''}`;
        this.scrollToBottomTerminal();
      }

      // New: Manager executing subtask
      if (type === "agent.executing") {
        const agentIcon = data.agent_type === 'coder' ? '💻' : data.agent_type === 'researcher' ? '🔍' : '🔧';
        this.currentAgentStatus = `${agentIcon} ${data.subtask}: ${data.description}`;
        this.terminalOutput += `\n${agentIcon} [${data.subtask}] ${data.description}`;
        this.scrollToBottomTerminal();
      }

      if (type === "governance.approval_required") {
        this.pendingApproval = {
          id: data.metadata.approval_id,
          tool: data.tool_name,
          args: data.metadata.arguments
        };
        this.currentAgentStatus = "Awaiting Approval...";
      }

      if (type === "tool.executing") {
        this.currentAgentStatus = `Executing: ${data.tool_name}...`;
        this.terminalOutput += `\n[EXECUTING] ${data.tool_name}...`;
        const m = this.missions.find(mi => mi.id === event.task_id);
        if (m) {
          m.status = "Acting";
          m.last_thought = `Executing ${data.tool_name}...`;
        }
        this.scrollToBottomTerminal();
        this.pulseMeshLink(data.tool_name, true);
      }

      if (type === "tool.called" || type === "tool.result") {
        if (type === "tool.result") this.currentAgentStatus = "Last tool finished.";
        this.terminalOutput += `\n[${type.toUpperCase()}] ${data.tool_name || "Tool"} finished.`;
        this.scrollToBottomTerminal();
        this.pulseMeshLink(data.tool_name, type === "tool.called", data.source);
      }

      if (type === "task.completed" || type === "task.failed") {
        this.currentAgentStatus = type === "task.completed" ? "Task Done." : "Task Failed.";
        const m = this.missions.find(mi => mi.id === event.task_id);
        if (m) {
          m.status = type === "task.completed" ? "Success" : "Failed";
          m.progress = 100;
        }
        this.isExecuting = false;
        this.pollCore(); // Refresh one last time
      }

      if (type.startsWith("workflow.")) {
        this.handleWorkflowEvent(type, data);
      }

      if (type === "param_changed") {
        this.loadUiSchema(); // Refresh settings UI
      }
    },

    pulseMeshLink(toolName, isCalling, source = "agent") {
      if (!this.meshGraph || !this.activeSession) return;

      const parts = toolName.split("__");
      const targetNodeId = parts.length > 1 ? `m-${parts[0]}` : null;
      if (!targetNodeId) return;

      let sourceNodeId = `Core-${this.activeSession.session_id}`;

      // If the call is inter-tool (Service Hub), pulse from the source tool
      if (source && source.startsWith("tool:")) {
        const sourceToolName = source.split(":")[1].split("__")[0];
        sourceNodeId = `m-${sourceToolName}`;
      }

      const graphData = this.meshGraph.graphData();
      const link = graphData.links.find(l =>
        (l.source.id === sourceNodeId && l.target.id === targetNodeId) ||
        (l.source === sourceNodeId && l.target === targetNodeId)
      );

      if (link) {
        this.meshGraph.emitParticle(link);
      }
    },

    handleWorkflowEvent(type, data) {
      if (type === "workflow.started") {
        this.ops.workflow = { active: true, name: data.name, step: 0, total: data.total_steps };
      } else if (type === "workflow.step") {
        this.ops.workflow.step = data.step_index;
      } else if (type === "workflow.completed" || type === "workflow.failed") {
        this.ops.workflow.active = false;
      }
    },

    initSplitPanes() {
      if (!window.Split) return;
      Split(["#pane-sidebar", "#pane-editor-split", "#pane-chat"], {
        sizes: [20, 50, 30],
        minSize: [200, 400, 250],
        gutterSize: 6,
        snapOffset: 0
      });
      Split(["#pane-editor", "#pane-terminal"], {
        direction: 'vertical',
        sizes: [75, 25],
        minSize: [200, 100],
        gutterSize: 6
      });
    },

    async loadUiSchema() {
      try {
        const schema = await this.api("/api/runtime/ui-schema");
        this.uiSchema = schema.categories || [];
      } catch (e) {
        console.warn("Could not load backend UI schema", e);
      }
    },

    async setParamValue(paramId, val) {
      await this.api(`/api/runtime/params/${encodeURIComponent(paramId)}`, {
        method: "PUT",
        body: JSON.stringify(val)
      });
    },

    async patchParam(paramId, val) {
      try {
        await this.setParamValue(paramId, val);
        for (let cat of this.uiSchema) {
          for (let p of cat.parameters) {
            if (p.id === paramId) p.value = val;
          }
        }
      } catch (e) {
        this.terminalOutput += `\n[Config] Failed to set ${paramId}: ${e.message}`;
      }
    },

    async refreshAll() {
      const data = await this.api("/api/ui/bootstrap");
      this.loadedSessions = (data.sessions || []).map(s => this.normalizeSession(s));
      this.project = data.project_registry || this.project;
      this.activeModel = data.active_model || this.activeModel;

      this.switchSessionById();
    },

    switchSessionById() {
      if (!this.activeSessionId) {
        this.activeSession = null;
        this.chatLog = [];
        if (this.pollInterval) clearInterval(this.pollInterval);
        return;
      }
      this.activeSession = this.loadedSessions.find(s => s.session_id === this.activeSessionId);
      if (this.activeSession) {
        this.governanceMode = this.activeSession.risk_mode || "auto";
        this.requireApprovalFor = this.activeSession.approval_list || [];
        this.loadWorkspaceTree();
        this.pollCore();
        this.startPolling();
        if (this.midTab === 'mesh') this.renderMesh();
      }
    },

    async loadOpsData() {
      try {
        const [health, status] = await Promise.all([
          this.api("/api/runtime/health"),
          this.api("/api/runtime/status/full")
        ]);
        this.ops.health = health;
        this.ops.fullStatus = status;
      } catch (e) { }
    },

    startPolling() {
      if (this.pollInterval) clearInterval(this.pollInterval);
      this.pollInterval = setInterval(() => this.pollCore(), 2500);
    },

    async pollCore() {
      if (!this.activeSession) return;
      // Skip if we just got a response
      if (this.justGotResponse) {
        this.justGotResponse = false;
        return;
      }
      await this.loadOpsData();
      try {
        // Don't update while executing - will overwrite new messages
        if (this.isExecuting) return;
        
        const data = await this.api(`/api/agent/sessions/${this.activeSession.session_id}/history`);
        const history = data.history || [];
        if (JSON.stringify(history) !== JSON.stringify(this.chatLog)) {
          this.chatLog = history;
          this.scrollToBottom();
        }
        // Always poll mesh/topology - show even for simple "hi"
        if (this.midTab === 'mesh' || this.navTab === 'network') {
          this.updateMeshTopology();
        }
        // Poll swarm status
        try {
          const swarm = await this.api("/api/runtime/swarm/status");
          this.swarmAgents = swarm.agents || [];
        } catch(e) { this.swarmAgents = []; }
        await this.pollCredits();
      } catch (e) {
        console.debug("Poll history failed: ", e.message);
      }
    },

    async createSession() {
      const userId = prompt("Assign global ID to new session (e.g. 'agent-zero'):");
      if (!userId) return;
      try {
        const session = await this.api("/api/agent/sessions", {
          method: "POST",
          body: JSON.stringify({ user_id: userId, workspace_path: "", mode: "web" })
        });
        await this.refreshAll();
        this.activeSessionId = session.session_id;
        this.switchSessionById();
        this.terminalOutput += `\n[Context] New bare session created: ${session.session_id}`;
      } catch (e) {
        this.terminalOutput += `\n[Error] Creating session failed: ${e.message}`;
      }
    },

    async deleteActiveSession() {
      if (!this.activeSession) return;
      const yes = confirm("Destroy current session forever?");
      if (!yes) return;
      try {
        await this.api(`/api/agent/sessions/${this.activeSession.session_id}`, { method: "DELETE" });
        this.activeSessionId = "";
        this.terminalOutput += `\n[Warning] Session purged successfully.`;
        await this.refreshAll();
      } catch (e) {
        this.terminalOutput += `\n[Error] Deleting session failed: ${e.message}`;
      }
    },

    primaryWorkspace() {
      if (!this.activeSession) return "";
      return this.activeSession.folders[0] || this.activeSession.workspace_path || "";
    },

    async loadWorkspaceTree() {
      if (!this.activeSession) return;
      const p = this.primaryWorkspace();
      if (!p) return;
      try {
        const data = await this.api(`/api/runtime/workspace/tree?path=${encodeURIComponent(p)}&depth=3`);
        this.explorerNodes = this.flattenTree(data.tree || {});
      } catch (e) {
        this.explorerNodes = [];
      }
      this.$nextTick(() => { if (window.lucide) lucide.createIcons(); });
    },

    flattenTree(node, depth = 0, rows = []) {
      if (!node || !node.path) return rows;
      rows.push({
        name: node.name || node.path,
        path: node.path,
        depth,
        type: node.type || "file"
      });
      (node.children || []).forEach(child => this.flattenTree(child, depth + 1, rows));
      return rows;
    },

    async openFile(node) {
      if (!node || node.type !== "file") return;
      this.midTab = 'code';
      try {
        const data = await this.api(`/api/runtime/workspace/file?path=${encodeURIComponent(node.path)}`);
        this.selectedFile = data.path;
        this.selectedFileContent = data.binary ? "[Binary or unsupported file type]" : (data.content || "");
      } catch (error) {
        this.selectedFileContent = "** Error loading file **";
      }
    },

    async saveEditorFile() {
      if (!this.activeSession || !this.selectedFile) return;
      try {
        await this.api(`/api/agent/sessions/${this.activeSession.session_id}/workspace/file`, {
          method: "PUT",
          body: JSON.stringify({ path: this.selectedFile, content: this.selectedFileContent })
        });
        this.terminalOutput += `\n[Editor] Saved ${this.selectedFile}`;
      } catch (error) {
        this.terminalOutput += `\n[Editor Error] ${error.message}`;
      }
      this.scrollToBottomTerminal();
    },

    async runTerminal() {
      if (!this.activeSession || !this.terminalCommand.trim()) return;
      const cmd = this.terminalCommand;
      this.terminalBusy = true;
      try {
        const data = await this.api(`/api/agent/sessions/${this.activeSession.session_id}/terminal`, {
          method: "POST",
          body: JSON.stringify({ command: cmd, cwd: this.primaryWorkspace(), timeout: 30 })
        });
        const out = data.result?.output || {};
        this.terminalOutput += `\n\n❯ ${cmd}\n${out.stdout || ""}${out.stderr || ""}${data.result?.error || ""}`;
        this.terminalCommand = "";
      } catch (error) {
        this.terminalOutput += `\n\n❯ ${cmd}\nError: ${error.message}`;
      } finally {
        this.terminalBusy = false;
        this.scrollToBottomTerminal();
      }
    },

    async handleDragStart(e, type, name) {
      e.dataTransfer.setData("application/json", JSON.stringify({ type, name }));
    },

    async handleDrop(e) {
      if (!this.activeSession) return;
      try {
        const data = JSON.parse(e.dataTransfer.getData("application/json"));
        const mapProp = data.type;

        const currentList = Array.from(new Set([...(this.activeSession[mapProp] || []), data.name]));

        await this.api(`/api/agent/sessions/${this.activeSession.session_id}/governance`, {
          method: "PUT",
          body: JSON.stringify({ [mapProp]: currentList })
        });

        this.activeSession[mapProp] = currentList;
        
        // Trigger pulse animation
        this.shelfPulse = true;
        setTimeout(() => this.shelfPulse = false, 1000);

        if (mapProp === 'folders') this.loadWorkspaceTree();
        this.terminalOutput += `\n[Context] Attached ${data.type}: ${data.name} to active session.`;
        this.scrollToBottomTerminal();
        if (this.midTab === 'mesh') this.updateMeshTopology();
      } catch (err) {
        this.terminalOutput += `\n[Drop Error] ${err.message}`;
        this.scrollToBottomTerminal();
      }
    },

    async unbindItem(type, item) {
      if (!this.activeSession) return;
      const list = this.activeSession[type] || [];
      const currentList = list.filter(n => n !== item);
      try {
        await this.api(`/api/agent/sessions/${this.activeSession.session_id}/governance`, {
          method: "PUT",
          body: JSON.stringify({ [type]: currentList })
        });

        this.activeSession[type] = currentList;
        if (type === 'folders') this.loadWorkspaceTree();
        this.terminalOutput += `\n[Context] Unbound ${type}: ${item}.`;
        
        this.shelfPulse = true;
        setTimeout(() => this.shelfPulse = false, 1000);
        
        this.scrollToBottomTerminal();
        if (this.midTab === 'mesh') this.updateMeshTopology();
      } catch (err) {
        this.terminalOutput += `\n[Unbind Error] ${err.message}`;
      }
    },

    async updateGovernance() {
      if (!this.activeSession) return;
      try {
        await this.api(`/api/agent/sessions/${this.activeSession.session_id}/governance`, {
          method: "PUT",
          body: JSON.stringify({
            risk_mode: this.governanceMode,
            require_approval_for: (this.requireApprovalFor || "").split(",").map(s => s.trim())
          })
        });
        this.terminalOutput += `\n[Governance] Session policy updated. Mode: ${this.governanceMode}`;
        this.scrollToBottomTerminal();
      } catch (err) {
        this.terminalOutput += `\n[Governance Error] ${err.message}`;
      }
    },

    async dispatchTask() {
      if (!this.userInput.trim() || !this.activeSession) return;
      if (this.isExecuting) {
        this.terminalOutput += `\n[System] Still processing previous request...`;
        this.scrollToBottomTerminal();
        return;
      }
      const input = this.userInput.trim();
      this.userInput = '';
      this.isExecuting = true;
      this.currentAgentStatus = "Initializing task...";
      
      this.chatLog.push({ role: "user", content: input });
      this.scrollToBottom();

      try {
        const payload = {
          session_id: this.activeSession.session_id,
          input: input,
          context_bindings: {
            folders: this.activeSession.folders || [],
            skills: this.activeSession.skills || [],
            mcp_servers: this.activeSession.mcp_servers || []
          }
        };

        const result = await this.api("/api/agent/dispatch", {
          method: "POST",
          body: JSON.stringify(payload)
        });

        this.missions.unshift({
          id: result.task_id,
          description: input,
          status: "Planning",
          progress: 10,
          last_thought: "Initializing agentic swarm..."
        });

        this.terminalOutput += `\n[System] Task dispatched (${result.task_id})`;
        this.scrollToBottomTerminal();
        this.navTab = "missions";
        
        // Wait for result and add to chat
        this.pollForResult(result.task_id);
      } catch (err) {
        this.terminalOutput += `\n[Dispatch Error] ${err.message}`;
        this.isExecuting = false;
        this.currentAgentStatus = null;
      }
    },

    async respondToApproval(approved) {
      if (!this.pendingApproval) return;
      const aid = this.pendingApproval.id;
      this.pendingApproval = null;
      try {
        const endpoint = approved ? `/api/agent/governance/approve/${aid}` : `/api/agent/governance/deny/${aid}`;
        await this.api(endpoint, { method: "POST" });
        this.terminalOutput += `\n[Governance] Security decision: ${approved ? 'APPROVED' : 'DENIED'}`;
      } catch (err) {
        this.terminalOutput += `\n[Governance Error] Failed to resolve approval: ${err.message}`;
      }
      this.scrollToBottomTerminal();
    },

    async mountMcp() {
      if (!this.newMcp.name || !this.newMcp.command) return;
      try {
        const result = await this.api("/api/mcp/mount", {
          method: "POST",
          body: JSON.stringify({
            name: this.newMcp.name,
            command: this.newMcp.command,
            args: this.newMcp.args.split(" ").filter(a => a.trim())
          })
        });
        this.terminalOutput += `\n[MCP] Mounted server: ${result.name}`;
        this.newMcp = { name: "", command: "", args: "" };
        this.showMcpForm = false;
        await this.pollCore();
        this.renderMesh();
      } catch (err) {
        this.terminalOutput += `\n[MCP Error] ${err.message}`;
      }
    },

    async injectKnowledge() {
      if (!this.newKnowledge.trim()) return;
      this.isInjecting = true;
      try {
        await this.api("/api/agent/memory/inject", {
          method: "POST",
          body: JSON.stringify({ content: this.newKnowledge, session_id: this.activeSession?.session_id })
        });
        this.terminalOutput += `\n[Memory] Knowledge injected successfully.`;
        this.newKnowledge = "";
      } catch (err) {
        this.terminalOutput += `\n[Memory Error] ${err.message}`;
      } finally {
        this.isInjecting = false;
      }
    },

    async searchKnowledge() {
      if (!this.newKnowledge.trim()) return;
      try {
        const data = await this.api("/api/agent/memory/search", {
          method: "POST",
          body: JSON.stringify({ query: this.newKnowledge })
        });
        this.memoryResults = data.results || [];
      } catch (err) {
        this.terminalOutput += `\n[Memory Error] ${err.message}`;
      }
    },

    async pollSwarm() {
      try {
        const data = await this.api("/api/runtime/swarm/status");
        this.swarmAgents = data.agents || [];
      } catch (err) { }
    },

    async pollCredits() {
      try {
        const data = await this.api("/api/runtime/credits/balance");
        this.credits = data || this.credits;
      } catch (err) { }
    },

    // 3D Swarm Visualization Linkage
    renderMesh() {
      if (!document.getElementById("3d-graph")) return;
      if (!window.ForceGraph3D) {
        console.warn("ForceGraph3D not loaded yet!");
        return;
      }

      if (!this.meshGraph) {
        let container = document.getElementById("3d-graph");
        const { width, height } = container.getBoundingClientRect();
        this.meshGraph = ForceGraph3D()(container)
          .backgroundColor("rgba(0,0,0,0)")
          .width(width)
          .height(height)
          .nodeLabel("name")
          .nodeAutoColorBy("type")
          .linkDirectionalParticles(2)
          .linkDirectionalParticleSpeed(d => 0.005)
          .onNodeClick(node => {
            this.selectedNode = node;
            this.midTab = 'mesh';
          });
      }
      this.updateMeshTopology();
    },

    updateMeshTopology() {
      if (!this.activeSession || !this.meshGraph) return;

      // Always show Manager and Orchestrator
      const nodes = [
        { id: "Manager", name: "Manager", type: "manager", color: "#8b5cf6" },
        { id: "Orchestrator", name: "Orchestrator", type: "core", color: "#38bdf8" }
      ];
      const links = [
        { source: "Manager", target: "Orchestrator", type: "controls" }
      ];

      // Show skills as tools
      (this.activeSession.skills || []).forEach(s => {
        nodes.push({ id: `skill-${s}`, name: s, type: "skill", color: "#22c55e" });
        links.push({ source: "Orchestrator", target: `skill-${s}`, type: "uses" });
      });

      // Add MCP servers
      (this.activeSession.mcp_servers || []).forEach(m => {
        nodes.push({ id: `mcp-${m}`, name: m, type: "mcp", color: "#ff9900" });
        links.push({ source: "Orchestrator", target: `mcp-${m}`, type: "protocol" });
      });

      // Add swarm agents (real or active tasks)
      if (this.swarmAgents && this.swarmAgents.length > 0) {
        this.swarmAgents.forEach(a => {
          nodes.push({ id: `agent-${a.id}`, name: a.name, type: "agent", color: "#4ade80" });
          links.push({ source: "Manager", target: `agent-${a.id}`, type: "spawns" });
        });
      }

      // Add active missions as agents running
      (this.missions || []).filter(m => m.status === "Planning" || m.status === "Acting").forEach(m => {
        nodes.push({ id: `task-${m.id}`, name: m.description?.slice(0,15) || " task", type: "task", color: "#f472b6" });
        links.push({ source: "Manager", target: `task-${m.id}`, type: "running" });
      });

      this.meshGraph.graphData({ nodes, links });
    },

    async pollForResult(taskId) {
      for (let i = 0; i < 30; i++) {
        await new Promise(r => setTimeout(r, 500));
        try {
          const task = await this.api(`/api/agent/tasks/${taskId}`);
          if (task.status === "completed" || task.status === "failed") {
            const response = task.response?.response || task.steps?.[0]?.result || "Done";
            if (response !== "Done") {
              this.justGotResponse = true;  // Signal pollCore to skip
              this.chatLog.push({ role: "assistant", content: response });
              this.scrollToBottom();
            }
            this.isExecuting = false;
            this.currentAgentStatus = null;
            return;
          }
        } catch(e) { }
      }
      this.isExecuting = false;
      this.currentAgentStatus = null;
    },

    scrollToBottom() {
      this.$nextTick(() => {
        const el = document.getElementById("chatArea");
        if (el) el.scrollTop = el.scrollHeight;
      });
    },

    scrollToBottomTerminal() {
      this.$nextTick(() => {
        const el = document.getElementById("pane-terminal");
        if (el) el.scrollTop = el.scrollHeight;
      });
    },

    async registerWorkspace() {
      const path = (this.newFolder || "").trim();
      if (!path) return;
      try {
        const data = await this.api("/api/runtime/project/folders", {
          method: "POST",
          body: JSON.stringify({ path })
        });
        this.project.folders = (data.folders || []).map(p => ({ path: p }));
        this.newFolder = "";
        this.terminalOutput += `\n[Workspace] Registered folder: ${path}`;
        this.scrollToBottomTerminal();
      } catch (err) {
        this.terminalOutput += `\n[Workspace Error] ${err.message}`;
      }
    },

    async saveByok() {
      if (!this.byokKey.trim() || !this.activeSession) return;
      try {
        await this.api(`/api/agent/sessions/${this.activeSession.session_id}/byok`, {
          method: "POST",
          body: JSON.stringify({ provider: this.byokProvider, api_key: this.byokKey })
        });
        this.terminalOutput += `[BYOK] Key saved for ${this.byokProvider}`;
        this.byokKey = "";
        this.scrollToBottomTerminal();
      } catch (err) {
        this.terminalOutput += `[BYOK Error] ${err.message}`;
      }
    },

    async saveNvidiaNim() {
      if (!this.nvidiaNimBase.trim()) return;
      try {
        await this.api("/api/runtime/nvidia-nim", {
          method: "POST",
          body: JSON.stringify({ base_url: this.nvidiaNimBase, api_key: this.nvidiaNimKey })
        });
        this.terminalOutput += `[NIM] Configured: ${this.nvidiaNimBase}`;
      } catch (err) {
        this.terminalOutput += `[NIM Error] ${err.message}`;
      }
    },

    async addSessionFolder() {
      if (!this.sessionFolder.trim() || !this.activeSession) return;
      this.sessionFolders.push(this.sessionFolder);
      this.sessionFolder = "";
      this.terminalOutput += `[Gov] Folder added to session`;
    },

    async searchMemory() {
      if (!this.memoryQuery.trim()) return;
      try {
        const data = await this.api("/api/agent/memory/search", {
          method: "POST",
          body: JSON.stringify({ query: this.memoryQuery })
        });
        this.memoryResults = data.results || [];
      } catch (err) {
        this.terminalOutput += `\n[Memory Error] ${err.message}`;
      }
    }
  };
}
