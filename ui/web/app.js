function kernelUI() {
  const marketplaceList = [
    { name: "SQLite Database", desc: "Interact directly with SQLite .db files for agent memory.", cmd: "npx -y @modelcontextprotocol/server-sqlite", command: "npx", args: ["-y", "@modelcontextprotocol/server-sqlite", "--db", "./data/mcp.db"] },
    { name: "Filesystem Access", desc: "Robust local drive operations.", cmd: "npx -y @modelcontextprotocol/server-filesystem", command: "npx", args: ["-y", "@modelcontextprotocol/server-filesystem", "./workspace"] },
    { name: "Brave Search", desc: "Grants internet crawling and web research capabilities.", cmd: "npx -y @modelcontextprotocol/server-brave-search", command: "npx", args: ["-y", "@modelcontextprotocol/server-brave-search"] },
    { name: "GitHub Connector", desc: "Manage repos, PRs, and issues directly.", cmd: "npx -y @modelcontextprotocol/server-github", command: "npx", args: ["-y", "@modelcontextprotocol/server-github"] }
  ];

  return {
    vantaEffect: null,
    rightTab: "toolbox",
    activeModel: "ollama/qwen2.5-coder:7b-instruct-q4_K_M",
    loadedSessions: [],
    activeSession: null,
    chatLog: [],
    userInput: "",
    isExecuting: false,
    pollInterval: null,
    globalFolders: ["./workspace"],
    sysConfig: { mesh_p2p: false, gtm_swarm: false, sre_swarm: false },
    apiKeys: { anthropic: "", openai: "" },
    newMcp: { name: "", command: "", args: "" },
    newFolder: "",
    newSkillDesc: "",
    sortables: {},
    marketplaceList,

    async api(url, options = {}) {
      const res = await fetch(url, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `${res.status} ${res.statusText}`);
      }
      if (res.status === 204) return null;
      return res.json();
    },

    async initEngine() {
      this.vantaEffect = VANTA.FOG({
        el: "#vanta-canvas",
        mouseControls: true,
        touchControls: true,
        blurFactor: 0.6,
        zoom: 1.5,
        baseColor: 0x0a0c10,
        highlightColor: 0x3fb950,
        midtoneColor: 0x243e8a,
        lowlightColor: 0x0E1116
      });
      await this.fetchState();
      this.$nextTick(() => lucide.createIcons());
    },

    async fetchState() {
      try {
        const data = await this.api("/api/ui/bootstrap");
        this.loadedSessions = data.sessions || [];
        this.activeModel = data.active_model || this.activeModel;
        this.sysConfig = data.features || this.sysConfig;

        const skills = (data.skills && data.skills.available_packs) || ["file_operations", "terminal_execution"];
        const mcps = Object.keys(data.mcp_registry || {});
        this.renderModelOptions(data.models || []);
        this.renderDraggables("source-skills", skills, "zap", "text-yellow-500");
        this.renderDraggables("source-mcps", mcps, "server", "text-primary");
        this.renderDraggables("source-folders", this.globalFolders, "folder-search", "text-accent");

        if (this.activeSession) {
          const refreshed = this.loadedSessions.find(s => (s.id || s.session_id) === (this.activeSession.id || this.activeSession.session_id));
          if (refreshed) {
            // Preserve local UI state while merging fresh data
            this.activeSession = {
              ...refreshed,
              risk_mode: refreshed.risk_mode || this.activeSession.risk_mode || "auto",
              skills: this.activeSession.skills || refreshed.skills || [],
              mcp_servers: this.activeSession.mcp_servers || refreshed.mcp_servers || [],
              folders: this.activeSession.folders || refreshed.folders || []
            };
          }
        }
      } catch (e) {
        console.error("API sync failure. Restart FastAPI backend.", e);
      }
    },

    renderModelOptions(models) {
      const selectEl = document.querySelector('select[x-model="activeModel"]');
      if (!selectEl || !models.length) return;
      selectEl.innerHTML = "";
      models.forEach(model => {
        const opt = document.createElement("option");
        opt.value = model.id;
        opt.textContent = `[${model.group}] ${model.name}`;
        selectEl.appendChild(opt);
      });
    },

    renderDraggables(containerId, items, icon, colorClass) {
      const container = document.getElementById(containerId);
      if (!container) return;
      container.innerHTML = "";
      items.forEach(value => {
        const div = document.createElement("div");
        div.className = "bg-base-200 px-3 py-2 rounded shadow-sm text-xs cursor-grab flex items-center gap-2 border border-transparent hover:border-white/10";
        div.dataset.id = value;
        div.innerHTML = `<i data-lucide="${icon}" class="w-3 h-3 ${colorClass}"></i><span class="truncate">${value}</span>`;
        container.appendChild(div);
      });
      lucide.createIcons();
    },

    async patchModelConfig() {
      try {
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
      } catch (e) {
        console.error(e);
      }
    },

    async patchSystemConfig(key) {
      try {
        await this.api("/api/runtime/config", {
          method: "PATCH",
          body: JSON.stringify({ features: { [key]: this.sysConfig[key] } })
        });
      } catch (e) {
        console.error(e);
      }
    },

    async createSession() {
      const uid = prompt("Assign Name for new Focus Node:");
      if (!uid) return;
      try {
        const session = await this.api("/api/sessions", {
          method: "POST",
          body: JSON.stringify({ user_id: uid, workspace_path: "./workspace", mode: "web" })
        });
        await this.fetchState();
        const created = this.loadedSessions.find(s => (s.id || s.session_id) === session.id) || session;
        await this.switchSession(created);
      } catch (e) {
        alert("Failed to forge session.");
      }
    },

    async deleteSession(id) {
      try {
        await this.api(`/sessions/${id}`, { method: "DELETE" });
        if (this.activeSession && (this.activeSession.id || this.activeSession.session_id) === id) {
          this.activeSession = null;
          this.chatLog = [];
          this.isExecuting = false;
          if (this.pollInterval) clearInterval(this.pollInterval);
        }
        await this.fetchState();
      } catch (e) {
        console.error(e);
      }
    },

    async switchSession(session) {
      this.activeSession = {
        ...session,
        risk_mode: session.risk_mode || "auto",
        skills: session.skills || [],
        mcp_servers: session.mcp_servers || [],
        folders: session.folders || []
      };
      this.renderDraggables("drop-skills", this.activeSession.skills, "zap", "text-yellow-500");
      this.renderDraggables("drop-mcps", this.activeSession.mcp_servers, "server", "text-primary");
      this.renderDraggables("drop-folders", this.activeSession.folders, "folder", "text-accent");
      await this.pollHistory();
      this.scrollToBottom();
      this.$nextTick(() => this.rebindDragAndDrop());
      if (this.pollInterval) clearInterval(this.pollInterval);
      this.pollInterval = setInterval(() => this.pollHistory(), 1500);
    },

    async pollHistory() {
      if (!this.activeSession) return;
      const sid = this.activeSession.id || this.activeSession.session_id;
      try {
        const data = await this.api(`/sessions/${sid}/history`);
        const history = data.history || data.messages || [];
        if (!Array.isArray(history)) return;
        // Always update if history is different from local state
        if (JSON.stringify(this.chatLog) !== JSON.stringify(history)) {
          this.chatLog = history;
          this.isExecuting = false;
          this.scrollToBottom();
        }
      } catch (e) {
        console.error(e);
      }
    },

    rebindDragAndDrop() {
      Object.values(this.sortables).forEach(sortable => sortable.destroy());
      const makeSortable = (group, src, drop) => {
        const source = document.getElementById(src);
        const target = document.getElementById(drop);
        if (!source || !target) return;
        this.sortables[src] = new Sortable(source, { group: { name: group, pull: "clone", put: false }, sort: false });
        this.sortables[drop] = new Sortable(target, { group: { name: group, pull: true, put: [group] }, animation: 150 });
      };
      makeSortable("group_skills", "source-skills", "drop-skills");
      makeSortable("group_mcps", "source-mcps", "drop-mcps");
      makeSortable("group_folders", "source-folders", "drop-folders");
      document.querySelectorAll(".glass-panel").forEach(block => {
        block.addEventListener("drop", () => setTimeout(() => lucide.createIcons(), 50));
      });
    },

    async saveSessionConstraints() {
      if (!this.activeSession) return;
      const ids = node => Array.from(document.getElementById(node).querySelectorAll("[data-id]")).map(el => el.dataset.id);
      const sid = this.activeSession.id || this.activeSession.session_id;
      try {
        const updated = await this.api(`/sessions/${sid}`, {
          method: "PATCH",
          body: JSON.stringify({
            skills: Array.from(new Set(ids("drop-skills"))),
            mcp_servers: Array.from(new Set(ids("drop-mcps"))),
            folders: Array.from(new Set(ids("drop-folders")))
          })
        });
        this.activeSession = { ...this.activeSession, ...updated };
        alert("Constraints permanently serialized!");
      } catch (e) {
        console.error(e);
      }
    },

    async patchSessionConfig() {
      if (!this.activeSession) return;
      const sid = this.activeSession.id || this.activeSession.session_id;
      try {
        await this.api(`/sessions/${sid}`, {
          method: "PATCH",
          body: JSON.stringify({ risk_mode: this.activeSession.risk_mode })
        });
      } catch (e) {
        console.error("Failed to patch session risk_mode", e);
      }
    },

    async dispatchTask() {
      if (!this.userInput || !this.activeSession) return;
      const q = this.userInput.trim();
      if (!q) return;
      this.userInput = "";
      this.isExecuting = true;
      // Optimistically add user message locally (will be overwritten by server history)
      this.chatLog = [...this.chatLog, { role: "user", content: q }];
      this.scrollToBottom();

      const sid = this.activeSession.id || this.activeSession.session_id;
      try {
        await this.api("/tasks", {
          method: "POST",
          body: JSON.stringify({
            session_id: sid,
            task_type: "code_generation",
            description: q,
            max_iterations: 8
          })
        });
        // Wait a moment for the task to start, then poll
        setTimeout(() => this.pollHistory(), 500);
        // Set up polling until execution completes
        const pollUntilDone = () => {
          if (!this.isExecuting) return;
          this.pollHistory().then(() => {
            if (this.isExecuting) {
              setTimeout(pollUntilDone, 1000);
            }
          });
        };
        setTimeout(pollUntilDone, 1000);
      } catch (e) {
        console.error("Pipeline failure.", e);
        this.isExecuting = false;
      }
    },

    addNativeFolder() {
      document.getElementById("addFolderModal").showModal();
    },

    registerLocalFolder() {
      if (!this.newFolder.trim()) return;
      if (!this.globalFolders.includes(this.newFolder)) this.globalFolders.push(this.newFolder);
      this.renderDraggables("source-folders", this.globalFolders, "folder-search", "text-accent");
      document.getElementById("addFolderModal").close();
      this.newFolder = "";
    },

    async registerNewMCP() {
      const args = this.newMcp.args.split(",").map(item => item.trim()).filter(Boolean);
      await this.executeMcpInstall(this.newMcp.name, this.newMcp.command, args);
      document.getElementById("addMcpModal").close();
      this.newMcp = { name: "", command: "", args: "" };
    },

    async oneClickInstall(item) {
      await this.executeMcpInstall(item.name.replace(/\s+/g, "-").toLowerCase(), item.command, item.args);
    },

    async executeMcpInstall(name, command, args) {
      try {
        await this.api("/api/mcp/registry", {
          method: "POST",
          body: JSON.stringify({ name, command, args, auto_start: true })
        });
        await this.fetchState();
        alert(`MCP [${name}] merged into registry.`);
      } catch (e) {
        console.error(e);
      }
    },

    scrollToBottom() {
      setTimeout(() => {
        const box = document.getElementById("chatArea");
        if (box) box.scrollTop = box.scrollHeight;
      }, 100);
    }
  };
}

window.kernelUI = kernelUI;
