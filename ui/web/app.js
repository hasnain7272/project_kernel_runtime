function kernelUI() {
  const marketplaceList = [
    {
      name: "Filesystem Access",
      desc: "Local workspace read/write via MCP filesystem server.",
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-filesystem", "./workspace"]
    },
    {
      name: "SQLite Database",
      desc: "Structured storage and retrieval over SQLite files.",
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-sqlite", "--db", "./data/mcp.db"]
    },
    {
      name: "Brave Search",
      desc: "Web research MCP for external search workflows.",
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-brave-search"]
    }
  ];

  return {
    vantaEffect: null,
    rightTab: "project",
    activeModel: "ollama/qwen2.5-coder:7b-instruct-q4_K_M",
    apiKeys: { anthropic: "", openai: "" },
    sysConfig: { mesh_p2p: false, gtm_swarm: false, sre_swarm: false },
    loadedSessions: [],
    activeSession: null,
    project: { skills: [], mcp_servers: [], folders: [], a2a: { peers: [], mesh: {} }, governance_defaults: {} },
    ops: {
      health: null,
      fullStatus: null,
      providers: null,
      jobs: [],
      artifacts: [],
      audit: [],
      approvals: [],
      events: [],
      runtimeYaml: ""
    },
    opsLoading: false,
    explorerNodes: [],
    chatLog: [],
    userInput: "",
    isExecuting: false,
    pollInterval: null,
    newFolder: "",
    newMcp: { name: "", command: "", args: "" },
    selectedFile: null,
    selectedFileContent: "",
    terminalCommand: "",
    terminalOutput: "",
    terminalBusy: false,
    memoryQuery: "",
    memoryResults: [],
    a2aDraft: "",
    topology: { nodes: [], edges: [], mesh: {} },
    artifactPreview: null,
    marketplaceList,

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
        user_role: session.user_role || "developer",
        risk_mode: session.risk_mode || "auto",
        skills: session.skills || [],
        mcp_servers: session.mcp_servers || [],
        folders: session.folders || [session.workspace_path].filter(Boolean),
        a2a_enabled: !!session.a2a_enabled,
        a2a_peers: session.a2a_peers || []
      };
    },

    async initEngine() {
      if (window.VANTA && window.VANTA.FOG) {
        this.vantaEffect = VANTA.FOG({
          el: "#vanta-canvas",
          mouseControls: true,
          touchControls: true,
          blurFactor: 0.5,
          zoom: 1.2,
          baseColor: 0x090b11,
          highlightColor: 0x4ade80,
          midtoneColor: 0x1d4ed8,
          lowlightColor: 0x0f172a
        });
      }
      await this.refreshAll();
      this.initWorkbenchSplit();
      this.$nextTick(() => lucide.createIcons());
    },

    async switchTab(tab) {
      this.rightTab = tab;
      if (tab === "runtime" || tab === "ops") {
        await this.loadOpsData();
      }
      if (tab === "project") {
        await this.loadTopology(true);
      }
    },

    async refreshAll() {
      const data = await this.api("/api/ui/bootstrap");
      this.loadedSessions = (data.sessions || []).map(session => this.normalizeSession(session));
      this.project = data.project_registry || this.project;
      this.activeModel = data.active_model || this.activeModel;
      this.sysConfig = data.features || this.sysConfig;

      if (this.activeSession) {
        const refreshed = this.loadedSessions.find(item => item.session_id === this.activeSession.session_id);
        if (refreshed) {
          this.activeSession = refreshed;
        } else {
          this.activeSession = this.loadedSessions[0] || null;
        }
      } else if (this.loadedSessions.length) {
        this.activeSession = this.loadedSessions[0];
      }

      if (this.activeSession) {
        await Promise.all([this.pollHistory(), this.loadWorkspaceTree()]);
        this.startPolling();
      } else if (this.pollInterval) {
        clearInterval(this.pollInterval);
        this.pollInterval = null;
      }
      if (this.rightTab === "runtime" || this.rightTab === "ops") {
        await this.loadOpsData();
      }
      if (this.rightTab === "project") {
        await this.loadTopology();
      }
      this.$nextTick(() => lucide.createIcons());
    },

    async loadOpsData(force = false) {
      if (this.opsLoading && !force) return;
      this.opsLoading = true;
      try {
        const [health, fullStatus, providers, jobs, artifacts, audit, approvals, events, runtimeYaml] = await Promise.all([
          this.api("/health"),
          this.api("/status/full"),
          this.api("/api/providers/live"),
          this.api("/api/jobs"),
          this.api("/api/artifacts"),
          this.api("/api/governance/audit"),
          this.api("/api/governance/approvals"),
          this.api("/api/events?limit=80"),
          this.api("/api/runtime/yaml")
        ]);
        this.ops.health = health;
        this.ops.fullStatus = fullStatus;
        this.ops.providers = providers;
        this.ops.jobs = jobs.jobs || [];
        this.ops.artifacts = artifacts.artifacts || [];
        this.ops.audit = audit.entries || [];
        this.ops.approvals = approvals.approvals || [];
        this.ops.events = events.events || [];
        this.ops.runtimeYaml = runtimeYaml.yaml || "";
      } finally {
        this.opsLoading = false;
      }
    },

    startPolling() {
      if (this.pollInterval) clearInterval(this.pollInterval);
      this.pollInterval = setInterval(() => this.pollHistory(), 1500);
    },

    async createSession() {
      const userId = prompt("Session name");
      if (!userId) return;
      const session = await this.api("/api/sessions", {
        method: "POST",
        body: JSON.stringify({ user_id: userId, workspace_path: "./workspace", mode: "web" })
      });
      await this.refreshAll();
      await this.switchSession(session);
    },

    async switchSession(session) {
      this.activeSession = this.normalizeSession(session);
      this.selectedFile = null;
      this.selectedFileContent = "";
      await Promise.all([this.pollHistory(), this.loadWorkspaceTree()]);
      this.startPolling();
    },

    async deleteSession(sessionId) {
      await this.api(`/sessions/${sessionId}`, { method: "DELETE" });
      if (this.activeSession && this.activeSession.session_id === sessionId) {
        this.activeSession = null;
        this.chatLog = [];
        this.explorerNodes = [];
        this.selectedFile = null;
        this.selectedFileContent = "";
      }
      await this.refreshAll();
    },

    async pollHistory() {
      if (!this.activeSession) return;
      const data = await this.api(`/sessions/${this.activeSession.session_id}/history`);
      const history = data.history || [];
      if (JSON.stringify(history) !== JSON.stringify(this.chatLog)) {
        this.chatLog = history;
        this.isExecuting = false;
        this.scrollToBottom();
      }
    },

    async dispatchTask() {
      if (!this.activeSession || !this.userInput.trim()) return;
      const description = this.userInput.trim();
      this.userInput = "";
      this.isExecuting = true;
      this.chatLog = [...this.chatLog, { role: "user", content: description }];
      this.scrollToBottom();

      await this.api("/tasks", {
        method: "POST",
        body: JSON.stringify({
          session_id: this.activeSession.session_id,
          task_type: "code_generation",
          description,
          max_iterations: 8
        })
      });
      setTimeout(() => this.pollHistory(), 500);
    },

    async saveSessionGovernance() {
      if (!this.activeSession) return;
      const updated = await this.api(`/sessions/${this.activeSession.session_id}`, {
        method: "PATCH",
        body: JSON.stringify({
          user_role: this.activeSession.user_role,
          risk_mode: this.activeSession.risk_mode,
          skills: this.activeSession.skills,
          mcp_servers: this.activeSession.mcp_servers,
          folders: this.activeSession.folders,
          a2a_enabled: this.activeSession.a2a_enabled,
          a2a_peers: this.activeSession.a2a_peers
        })
      });
      this.activeSession = this.normalizeSession(updated);
      this.loadedSessions = this.loadedSessions.map(item =>
        item.session_id === updated.session_id ? this.activeSession : item
      );
      await this.loadWorkspaceTree();
    },

    toggleSessionItem(kind, value) {
      if (!this.activeSession) return;
      const map = { skill: "skills", mcp: "mcp_servers", folder: "folders" };
      const key = map[kind];
      const list = new Set(this.activeSession[key] || []);
      if (list.has(value)) {
        list.delete(value);
      } else {
        list.add(value);
      }
      this.activeSession[key] = Array.from(list);
      this.saveSessionGovernance();
    },

    toggleA2APeer(peerId) {
      if (!this.activeSession) return;
      const list = new Set(this.activeSession.a2a_peers || []);
      if (list.has(peerId)) {
        list.delete(peerId);
      } else {
        list.add(peerId);
      }
      this.activeSession.a2a_peers = Array.from(list);
      this.saveSessionGovernance();
    },

    isSessionBound(kind, value) {
      if (!this.activeSession) return false;
      const map = { skill: "skills", mcp: "mcp_servers", folder: "folders" };
      const list = this.activeSession[map[kind]] || [];
      return list.includes(value);
    },

    isPeerBound(peerId) {
      return !!this.activeSession && (this.activeSession.a2a_peers || []).includes(peerId);
    },

    primaryWorkspace() {
      if (!this.activeSession) return "";
      return this.activeSession.folders[0] || this.activeSession.workspace_path || "";
    },

    initWorkbenchSplit() {
      if (!window.Split) return;
      if (!this._mainSplit) {
        this._mainSplit = Split(["#workbench-main", "#workbench-side"], {
          gutterSize: 10,
          minSize: [680, 360],
          sizes: [67, 33]
        });
      }
      if (!this._editorSplit) {
        this._editorSplit = Split(["#pane-explorer", "#pane-editor", "#pane-terminal"], {
          gutterSize: 8,
          minSize: [220, 320, 260],
          sizes: [24, 44, 32]
        });
      }
    },

    sessionStats() {
      return this.activeSession || {
        user_role: "developer",
        risk_mode: "auto",
        skills: [],
        mcp_servers: [],
        folders: [],
        a2a_enabled: false,
        a2a_peers: []
      };
    },

    async loadWorkspaceTree() {
      if (!this.activeSession) {
        this.explorerNodes = [];
        return;
      }
      const path = this.primaryWorkspace();
      if (!path) {
        this.explorerNodes = [];
        return;
      }
      try {
        const data = await this.api(`/api/workspace/tree?path=${encodeURIComponent(path)}&depth=2`);
        this.explorerNodes = this.flattenTree(data.tree || {});
        if (data.exists === false) {
          this.selectedFile = null;
          this.selectedFileContent = "Workspace path is registered but does not exist yet.";
        }
      } catch (error) {
        this.explorerNodes = [{ path, name: "Workspace unavailable", depth: 0, type: "error" }];
        this.selectedFile = null;
        this.selectedFileContent = "Workspace tree could not be loaded.";
      }
      this.$nextTick(() => lucide.createIcons());
    },

    async loadTopology(force = false) {
      if (!force && this.topology.nodes.length) {
        this.$nextTick(() => this.renderA2ATopology());
        return;
      }
      try {
        this.topology = await this.api("/api/a2a/topology");
      } catch (error) {
        this.topology = { nodes: [], edges: [], mesh: {} };
      }
      this.$nextTick(() => this.renderA2ATopology());
    },

    renderA2ATopology() {
      if (!window.cytoscape) return;
      const el = document.getElementById("a2a-topology");
      if (!el) return;
      if (this._cy) {
        this._cy.destroy();
        this._cy = null;
      }
      const nodes = (this.topology.nodes || []).map(node => ({
        data: {
          id: node.id,
          label: node.label || node.id,
          status: node.status || node.type || "unknown"
        }
      }));
      const edges = (this.topology.edges || []).map((edge, index) => ({
        data: {
          id: `edge-${index}`,
          source: edge.from,
          target: edge.to,
          label: edge.label || "mesh"
        }
      }));
      this._cy = window.cytoscape({
        container: el,
        elements: { nodes, edges },
        layout: { name: "cose", animate: false, padding: 16 },
        style: [
          {
            selector: "node",
            style: {
              "background-color": "#38bdf8",
              color: "#e2e8f0",
              label: "data(label)",
              "font-size": "10px",
              "text-wrap": "wrap",
              "text-max-width": "90px",
              "border-color": "#0f172a",
              "border-width": 2
            }
          },
          {
            selector: "edge",
            style: {
              width: 2,
              "line-color": "#64748b",
              "target-arrow-color": "#64748b",
              "target-arrow-shape": "triangle",
              "curve-style": "bezier"
            }
          }
        ]
      });
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

    async openNode(node) {
      if (!node || node.type !== "file") return;
      try {
        const data = await this.api(`/api/workspace/file?path=${encodeURIComponent(node.path)}`);
        this.selectedFile = data.path;
        this.selectedFileContent = data.binary ? "[binary file]" : (data.content || "");
        this.$nextTick(() => lucide.createIcons());
      } catch (error) {
        this.selectedFile = node.path;
        this.selectedFileContent = "Unable to read file.";
      }
    },

    async saveEditorFile() {
      if (!this.activeSession || !this.selectedFile) return;
      try {
        const data = await this.api(`/sessions/${this.activeSession.session_id}/workspace/file`, {
          method: "PUT",
          body: JSON.stringify({
            path: this.selectedFile,
            content: this.selectedFileContent
          })
        });
        const result = data.result || {};
        this.terminalOutput = `write_file -> ${result.success ? "ok" : "failed"}\n${result.error || ""}`.trim();
        await this.refreshAll();
      } catch (error) {
        this.terminalOutput = `write_file -> failed\n${error.message}`;
      }
    },

    async runTerminal() {
      if (!this.activeSession || !this.terminalCommand.trim()) return;
      const command = this.terminalCommand;
      this.terminalBusy = true;
      try {
        const data = await this.api(`/sessions/${this.activeSession.session_id}/terminal`, {
          method: "POST",
          body: JSON.stringify({
            command,
            cwd: this.primaryWorkspace(),
            timeout: 30
          })
        });
        const result = data.result || {};
        const output = result.output || {};
        this.terminalOutput = [
          `$ ${command}`,
          output.stdout || "",
          output.stderr || "",
          output.error || "",
          result.error || ""
        ].filter(Boolean).join("\n");
        this.terminalCommand = "";
        await this.loadOpsData(true);
      } catch (error) {
        this.terminalOutput = [`$ ${command}`, error.message].join("\n");
      } finally {
        this.terminalBusy = false;
      }
    },

    async searchMemory() {
      if (!this.memoryQuery.trim()) return;
      const data = await this.api("/memory/search", {
        method: "POST",
        body: JSON.stringify({ query: this.memoryQuery.trim(), limit: 10 })
      });
      this.memoryResults = data.results || [];
    },

    async patchModelConfig() {
      await this.api("/api/models/status", {
        method: "PUT",
        body: JSON.stringify({
          active_model: this.activeModel,
          providers: [
            { name: "anthropic", api_key_env: this.apiKeys.anthropic },
            { name: "openai", api_key_env: this.apiKeys.openai }
          ]
        })
      });
      await this.loadOpsData(true);
    },

    async patchSystemConfig(key) {
      await this.api("/api/runtime/config", {
        method: "PATCH",
        body: JSON.stringify({ features: { [key]: this.sysConfig[key] } })
      });
      await this.loadOpsData(true);
    },

    async toggleSkill(skill) {
      await this.api(`/api/skills/${encodeURIComponent(skill.name)}/toggle`, {
        method: "POST",
        body: JSON.stringify({ enabled: !skill.enabled, pack: skill.pack })
      });
      await this.refreshAll();
    },

    async toggleMcp(server) {
      await this.api(`/api/mcp/servers/${encodeURIComponent(server.name)}/toggle`, {
        method: "POST",
        body: JSON.stringify({ disabled: !server.disabled })
      });
      await this.refreshAll();
    },

    async controlMcp(serverName, action) {
      try {
        await this.api(`/api/mcp/servers/${encodeURIComponent(serverName)}/${action}`, {
          method: "POST"
        });
        this.terminalOutput = `mcp.${action} -> ${serverName}`;
      } catch (error) {
        this.terminalOutput = `mcp.${action} -> failed\n${error.message}`;
      }
      await this.refreshAll();
      await this.loadOpsData(true);
      await this.loadTopology(true);
    },

    openAddFolder() {
      document.getElementById("addFolderModal").showModal();
    },

    async registerLocalFolder() {
      if (!this.newFolder.trim()) return;
      await this.api("/api/project/folders", {
        method: "POST",
        body: JSON.stringify({ path: this.newFolder.trim() })
      });
      document.getElementById("addFolderModal").close();
      this.newFolder = "";
      await this.refreshAll();
    },

    async removeProjectFolder(path) {
      await this.api(`/api/project/folders?path=${encodeURIComponent(path)}`, { method: "DELETE" });
      if (this.activeSession && this.activeSession.folders.includes(path)) {
        this.activeSession.folders = this.activeSession.folders.filter(item => item !== path);
        await this.saveSessionGovernance();
      }
      await this.refreshAll();
    },

    async registerNewMCP() {
      if (!this.newMcp.name.trim() || !this.newMcp.command.trim()) return;
      const args = this.newMcp.args.split(",").map(item => item.trim()).filter(Boolean);
      await this.api("/api/mcp/registry", {
        method: "POST",
        body: JSON.stringify({
          name: this.newMcp.name.trim(),
          command: this.newMcp.command.trim(),
          args,
          auto_start: true
        })
      });
      document.getElementById("addMcpModal").close();
      this.newMcp = { name: "", command: "", args: "" };
      await this.refreshAll();
    },

    async saveRuntimeYaml() {
      await this.api("/api/runtime/yaml", {
        method: "PUT",
        body: JSON.stringify({ yaml: this.ops.runtimeYaml })
      });
      await this.refreshAll();
      await this.loadOpsData(true);
    },

    async resolveApproval(approvalId, approved) {
      await this.api(`/api/governance/approvals/${approvalId}`, {
        method: "POST",
        body: JSON.stringify({ approved, reviewer_id: "web-ui" })
      });
      await this.loadOpsData(true);
    },

    async delegateA2A() {
      const peers = (this.project.a2a && this.project.a2a.peers) || [];
      if (!this.a2aDraft.trim() || !peers.length) return;
      const payload = {
        target_peer: peers[0].id,
        description: this.a2aDraft.trim(),
        session_id: this.activeSession ? this.activeSession.session_id : null,
        workspace_path: this.primaryWorkspace(),
        user_id: this.activeSession ? this.activeSession.user_id : "web-ui"
      };
      const response = await this.api("/api/a2a/delegate", {
        method: "POST",
        body: JSON.stringify(payload)
      });
      this.terminalOutput = `a2a.delegate -> ${response.target_peer}\njob ${response.job.id}`;
      this.a2aDraft = "";
      await this.loadOpsData(true);
    },

    async viewArtifact(artifactId) {
      const artifact = await this.api(`/api/artifacts/${encodeURIComponent(artifactId)}`);
      this.artifactPreview = artifact;
    },

    async oneClickInstall(item) {
      await this.api("/api/mcp/registry", {
        method: "POST",
        body: JSON.stringify({
          name: item.name.toLowerCase().replace(/\s+/g, "-"),
          command: item.command,
          args: item.args,
          auto_start: true
        })
      });
      await this.refreshAll();
    },

    statusClass(status) {
      if (status === "connected") return "badge-success";
      if (status === "error") return "badge-error";
      return "badge-ghost";
    },

    jobStatusClass(status) {
      if (status === "completed") return "badge-success";
      if (status === "failed") return "badge-error";
      if (status === "running") return "badge-warning";
      return "badge-ghost";
    },

    providerStatusClass(provider) {
      if (!provider) return "badge-ghost";
      if (provider.reachable) return "badge-success";
      if (provider.enabled) return "badge-warning";
      return "badge-ghost";
    },

    auditDecisionClass(entry) {
      const decision = (entry && entry.decision) || "";
      if (decision === "ALLOW") return "text-success";
      if (decision === "DENY") return "text-error";
      if (decision === "REQUIRE_APPROVAL") return "text-warning";
      return "text-base-content/60";
    },

    formatTime(value) {
      if (!value) return "";
      return new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    },

    scrollToBottom() {
      setTimeout(() => {
        const chatArea = document.getElementById("chatArea");
        if (chatArea) chatArea.scrollTop = chatArea.scrollHeight;
      }, 60);
    }
  };
}

window.kernelUI = kernelUI;
