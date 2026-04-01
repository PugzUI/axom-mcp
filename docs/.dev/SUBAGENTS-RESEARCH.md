# Launching Agentic Subagents (Agent-Agnostic)

Research summary: how to launch subagents from **any** orchestrating agent (Cursor, Codex, OpenCode, Kilo, etc.). Axom MCP is agent-agnostic at all endpoints: **any-to-any** — whichever agent has Axom MCP connected can orchestrate; which specific agents (Cursor, Codex, OpenCode, Kilo, …) are available is configured per environment via **agent-registry.json** and **`.env`** (e.g. `AXOM_READ_ONLY`). Built-in mechanisms (e.g. Cursor’s `mcp_task`), native subagent templates, and third-party MCP/CLI backends are described below.

---

## 1. Cursor built-in: `mcp_task` (in-Composer)

The Composer agent has a built-in **`mcp_task`** tool. Use it to spawn a subagent in parallel or in the background.

- **Parameters (typical):**
  - `subagent_type`: `"generalPurpose"` | `"explore"` | `"shell"` | `"axom-agent"` (or other custom names if registered)
  - `prompt`: string — task for the subagent
  - `description`: short label (e.g. "Context gatherer")
  - `attachments`: optional array of file paths (e.g. `["docs/agents/subagent/axom-agent.md"]`) to pass as context
  - `model`: optional — e.g. `"fast"` for a cheaper/faster model; omit to inherit
  - `readonly`: optional — restrict subagent to read-only
  - `run_in_background`: optional — don’t block on result
  - `resume`: optional — agent ID to resume a previous run

- **Built-in subagent types:**
  - **generalPurpose** — broad tasks, full tool access
  - **explore** — codebase/environment discovery (read-only style)
  - **shell** — terminal / command execution
  - **axom-agent** — custom type (when Axom subagent is installed/registered)

- **Example (from this repo):**
  Dispatch context-gathering in parallel by calling `mcp_task` with `subagent_type="axom-agent"` (or `"generalPurpose"` with the axom-agent spec as context), `prompt="Gather context for [topic]. Return context envelope."`, and `attachments: [docs/agents/subagent/axom-agent.md]`.

---

## 2. Cursor native subagents (2.4+): `.cursor/agents/` and slash commands

Cursor 2.4+ supports **custom subagents** as Markdown files. They appear as slash commands in the Agent input.

- **Locations:**
  - **Workspace:** `.cursor/agents/` at project root
  - **User-wide:** `~/.cursor/agents/` (e.g. used by Axom’s `make agents`)

- **Format:** One `.md` file per agent. Frontmatter example:

  ```yaml
  ---
  name: axom-agent
  description: Context gatherer for complex problems...
  model: inherit
  readonly: true
  is_background: false
  ---
  ```

- **Invocation:** In Composer/Agent chat, type `/` and choose the agent (e.g. `/axom-agent`), then add the task in the same or next message.

- **In this repo:**
  `scripts/install_agent_config.py` installs `axom-agent` to `~/.cursor/agents/` when you run `make agents`. The source is `docs/agents/subagent/axom-agent.md`.

- **Note:** There is a known issue where the model set in the subagent frontmatter is not always used; the parent model may be used instead.

---

## 3. Third-party MCP: sub-agents-mcp (Cursor + Codex agent + Claude + Gemini)

**[shinpr/sub-agents-mcp](https://github.com/shinpr/sub-agents-mcp)** provides portable, task-specific subagents for Cursor (and other MCP hosts) by calling an external CLI under the hood.

- **Backends:** `AGENT_TYPE` can be `"cursor"` | `"claude"` | `"gemini"` | `"codex"`.
- **Cursor backend:** Uses **Cursor CLI** (`cursor-agent`). Install: `curl https://cursor.com/install -fsS | bash` then `cursor-agent login`.
- **Setup:**
  1. Create an agents folder with one `.md` or `.txt` per agent (filename = agent name).
  2. Add the server to Cursor MCP config (e.g. `~/.cursor/mcp.json`):

  ```json
  {
    "mcpServers": {
      "sub-agents": {
        "command": "npx",
        "args": ["-y", "sub-agents-mcp"],
        "env": {
          "AGENTS_DIR": "/absolute/path/to/agents",
          "AGENT_TYPE": "cursor"
        }
      }
    }
  }
  ```

  3. Use absolute paths for `AGENTS_DIR`.
- **Invocation:** Ask the main agent in natural language, e.g. “Use the code-reviewer agent to check my UserService class.” The model will call the MCP tool, which runs the chosen CLI with that agent’s definition.
- **Optional:** `EXECUTION_TIMEOUT_MS`, `AGENTS_SETTINGS_PATH`, and session-related env vars for persistence.

This gives you **one agent definition format** that can run via **Cursor, Codex agent, OpenCode agent–style flows, or Gemini** depending on `AGENT_TYPE`.

---

## 4. Codex agent–specific: codex-subagents-mcp (archived) and successor

- **leonardsellem/codex-subagents-mcp** (GitHub): MCP server that runs **Codex agent** (Codex CLI) subagents via a `delegate` tool. Agents are file-based (e.g. `agents/review.md`), with frontmatter for `profile`, `approval_policy`, `sandbox_mode`. The server runs `codex exec --profile <name> "<task>"` in a temp workdir with an injected `AGENTS.md`. **Status:** archived; successor repo: **codex-specialized-subagents**.
- So “launch a Codex subagent” from Cursor can mean: (1) use **sub-agents-mcp** with `AGENT_TYPE: "codex"` (runs Codex agent/CLI when the tool is invoked), or (2) use the Codex-specific MCP in a Codex-centric setup.

---

## 5. OpenCode agent and Kilo agent

- **OpenCode agent** (open-code.ai) is a separate autonomous coding platform. It has its own notion of primary agents (Build, Plan) and subagents (General, Explore), invoked via @ mentions. **CLI:** `opencode run "prompt"` for non-interactive execution. It is **not** a Cursor plugin; it’s an alternative environment.
- **Kilo agent** (Kilo Code) did not show up in search as a Cursor subagent template or documented CLI; if it offers a `kilocode run "prompt"`-style command, the same orchestration patterns (exec shell, background, combine) apply as for the Codex and OpenCode agents.

---

## 6. Cursor Background Agents API (cloud)

Cursor’s **Background Agents API** is for launching agents **on Cursor’s infrastructure** via HTTP, not for in-IDE subagent templates.

- Endpoint: `POST https://api.cursor.com/v0/agents`
- Auth: Bearer token from [Cursor dashboard → Background Agents](https://cursor.com/dashboard?tab=background-agents).
- Body: `prompt`, `source` (e.g. repo URL + ref), optional image attachments.
- Use case: orchestration from scripts/CI, not from the Composer `mcp_task` or slash-command subagents.

---

## 7. Codex / OpenCode / Kilo agents: non-interactive CLI + Axom subagents (async, any-to-any orchestration)

Use the **Codex agent**, **OpenCode agent**, or **Kilo agent** (and other agent CLIs) in **non-interactive mode** so the **orchestrating agent** (whichever agent has Axom MCP and is configured for your environment) can run them as async tasks, feed them Axom subagent specs (e.g. context gatherer), and combine results. This builds on existing Axom scaffolding: **exec shell + chain**, **AXOM_READ_ONLY** gating (from `.env`), **run_in_background**-style dispatch when the host supports it, and the **dispatch → combine** flow in axom-dispatch. Which agents can be invoked (Codex, OpenCode, Kilo, etc.) is determined by your setup; see **agent-registry.json** and `make agents` for configuring endpoints.

### Non-interactive CLI commands

| CLI                | Non-interactive launch           | Notes                                                                   |
| ------------------ | -------------------------------- | ----------------------------------------------------------------------- |
| **Codex agent**    | `codex exec "prompt"`            | Or with profile: `codex exec --profile <name> "prompt"`.                |
| **OpenCode agent** | `opencode run "prompt"`          | Optional: `-m provider/model`, `-f file`, `--attach` to running server. |
| **Kilo agent**     | (CLI not documented in research) | Use same pattern if a `kilo run "prompt"`-style command exists.         |

These run one task and exit; no TUI. Ideal for scripting and for the **orchestrating agent** (any host with Axom MCP) to invoke via `axom_mcp_exec` shell or via sub-agents-mcp when using a matching backend (e.g. Codex agent).

### Using Axom subagents with those CLIs

**Axom subagent definitions** (e.g. `docs/agents/subagent/axom-agent.md`) describe a single responsibility (e.g. “gather context; return envelope”). To use them with the Codex or OpenCode agent:

1. **Same repo, same workspace**
   The CLI runs in the project directory. Point the CLI at the repo’s agent docs (e.g. via `AGENTS.md` or a copied spec). The Codex agent reads `AGENTS.md`; the OpenCode agent can use project config. So “Axom subagents” here means: the **orchestrating agent** passes a **task string** that encodes the same instructions as the Axom subagent (e.g. “Gather context for &lt;topic&gt;. Return context envelope. Use only memory search and discover.”), and optionally ensures the run has access to Axom MCP (if the agent CLI is configured with Axom MCP server).

2. **sub-agents-mcp with Codex agent**
   Configure `AGENT_TYPE: "codex"` and `AGENTS_DIR` pointing to a folder that contains **Axom-style agent .md files** (e.g. a copy of `axom-agent.md` or a thin wrapper). When the **orchestrating agent** says “Use the axom-agent to gather context for X”, sub-agents-mcp runs the Codex agent with that agent definition; the Codex agent runs non-interactively and returns the result. No extra shell from the orchestrator.

3. **Direct shell from orchestrating agent (axom_mcp_exec)**
   The **orchestrating agent** (any host with Axom MCP) calls `axom_mcp_exec(operation="shell", target='codex exec "Gather context for X. Return context envelope."')` (or `opencode run "..."` for the OpenCode agent, or `kilo run "..."` for the Kilo agent). Output is in the tool result. For **async**, use run_in_background when the host supports it, or a shell that backgrounds and writes to a file (see below).

### Orchestration: async patterns (agent-agnostic)

Existing Axom tools and workflows support gated and async-style integration from **any** orchestrating agent; behavior is controlled by **`.env`** (e.g. `AXOM_READ_ONLY`) at the endpoint where Axom MCP runs.

- **Gating:** `AXOM_READ_ONLY` — when `true`, `axom_mcp_exec` rejects `write` and `shell`. So external agent CLIs (Codex, OpenCode, Kilo) are only run when the environment allows shell (e.g. Cursor’s MCP run has `AXOM_READ_ONLY` unset or false). See `src/axom_mcp/handlers/exec.py` and `docs/agents/skills/axom-exec/SKILL.md`.
- **Chains:** `axom_mcp_exec` supports a `chain` parameter so one call can do read → analyze → memory write, or **shell → later steps**. The **orchestrating agent** can do “shell: run Codex/OpenCode/Kilo agent” then chain to “memory write” or “read result file” when you use a result file. See `docs/agents/skills/axom-exec/SKILL.md` and `docs/agents/INDEX.md`.
- **Async dispatch:** When the host supports it (e.g. Cursor's mcp_task), the “complex-problem” prompt in `src/axom_mcp/server.py` and `docs/agents/skills/axom-dispatch/SKILL.md` describe: (1) dispatch subagent first (parallel), (2) main agent does discover/read/analyze, (3) combine at end with timeout. Use **`mcp_task`** with `run_in_background: true` to run a subagent without blocking. Otherwise use exec shell with a backgrounded command and a result file (see axom-dispatch SKILL and complex-problem prompt).
- **Partial results and timeouts:** Store partial or timeout outcomes in Axom memory so the next agent can recover (see axom-dispatch SKILL: “Subagent timed out; proceeded with [summary]” and the `partial_[task]_[YYYYMMDD]` pattern in memory). See `docs/agents/skills/axom-memory/SKILL.md` for REFLECTION and naming.

**Concrete orchestration options:**

| Goal                                                           | How                                                                                                                                                                                                                                                                                                                                                           |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Run Codex/OpenCode/Kilo agent and wait for result**          | `axom_mcp_exec(operation="shell", target='codex exec "task"' )` or `opencode run "task"` (or `kilo run "task"`). Parse stdout from the JSON result.                                                                                                                                                                                                           |
| **Run Codex/OpenCode/Kilo agent in background, combine later** | Option A: If the host supports it (e.g. Cursor `mcp_task` with `run_in_background: true`), use that. Option B: `axom_mcp_exec` shell with a command that backgrounds and writes to a file (e.g. `codex exec "task" > /tmp/axom-out.json 2>&1 &`), then later `axom_mcp_exec(operation="read", target="/tmp/axom-out.json")` and chain or next step to memory. |
| **Use Axom context-gatherer spec with Codex agent**            | Either (1) sub-agents-mcp with `AGENT_TYPE=codex` and `AGENTS_DIR` containing an axom-agent–style .md, or (2) shell: `codex exec "Gather context for &lt;topic&gt;. Return context envelope. [paste key constraints from axom-agent.md]"`.                                                                                                                    |
| **Use Axom context-gatherer with OpenCode agent**              | OpenCode agent is not a backend of sub-agents-mcp; use shell: `opencode run "Gather context for &lt;topic&gt;. Return context envelope. ..."`. Redirect to file if you need to combine in a later step.                                                                                                                                                       |

### Reference: existing Axom scaffolding

| Piece                        | Location                                                                     | Use                                                                           |
| ---------------------------- | ---------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Exec shell + chain           | `src/axom_mcp/handlers/exec.py`, `docs/agents/skills/axom-exec/SKILL.md`     | Run Codex/OpenCode/Kilo agent and chain to read result or memory write.       |
| AXOM_READ_ONLY               | `exec.py` (write/shell guarded), **`.env`** (see `.env.example`)             | Gate whether external agent CLIs are allowed at this endpoint.                |
| run_in_background / dispatch | Host-dependent (e.g. Cursor `mcp_task`); else exec shell + result file       | Async subagent; combine with timeout.                                         |
| Dispatch → combine + timeout | `docs/agents/skills/axom-dispatch/SKILL.md`, server prompt “complex-problem” | Pattern: dispatch first, main agent works, combine; store partial on timeout. |
| Memory for partial/timeout   | axom-dispatch SKILL, axom-memory SKILL                                       | Store `partial_[task]_[date]` and REFLECTION so next agent can continue.      |

---

## Quick reference

| Mechanism                                  | Where                  | How to launch                                                      | Backend / scope                                                 |
| ------------------------------------------ | ---------------------- | ------------------------------------------------------------------ | --------------------------------------------------------------- |
| **mcp_task**                               | In Composer            | Tool call: `subagent_type`, `prompt`, `attachments`                | Cursor built-in                                                 |
| **mcp_task (background)**                  | In Composer            | Same + `run_in_background: true`                                   | Async; combine later / timeout                                  |
| **Slash subagents**                        | In Composer            | Type `/agent-name` (e.g. `/axom-agent`)                            | `.cursor/agents/`                                               |
| **sub-agents-mcp**                         | MCP server             | “Use the &lt;name&gt; agent to…” → tool call                       | cursor / codex / claude / gemini                                |
| **Exec shell (Codex/OpenCode/Kilo agent)** | Any host with Axom MCP | `axom_mcp_exec(operation="shell", target='codex exec "..."')` etc. | Async/gated by `AXOM_READ_ONLY` in `.env`; chain to read result |
| **Codex-subagents-mcp**                    | MCP (Codex agent)      | `delegate(agent=..., task=...)`                                    | Codex agent CLI only                                            |
| **Background Agents API**                  | HTTP                   | `POST /v0/agents`                                                  | Cursor cloud                                                    |

---

## Applying a subagent template in this repo

- **Use built-in `mcp_task`:**
  Call `mcp_task` with `subagent_type="axom-agent"` (or `"generalPurpose"`) and `attachments: ["docs/agents/subagent/axom-agent.md"]` and a clear `prompt` (e.g. “Gather context for [topic]. Return context envelope.”). See `docs/agents/skills/axom-dispatch/SKILL.md` and the “complex-problem” prompt in `src/axom_mcp/server.py`.

- **Use Cursor slash command:**
  Run `make agents` to install `axom-agent` into `~/.cursor/agents/`. In chat, type `/axom-agent` and then the task.

- **Use sub-agents-mcp with Codex/OpenCode agent–style backend:**
  Install sub-agents-mcp, set `AGENT_TYPE` to `"codex"` (or another supported CLI), point `AGENTS_DIR` at a folder of agent `.md` files, and ask the main agent to “Use the &lt;agent-name&gt; agent to …”.

- **Use Codex / OpenCode / Kilo agents for async tasks (any-to-any orchestration):**
  See **§7** for non-interactive CLI commands, feeding Axom subagent specs, and orchestration using `axom_mcp_exec` shell, run_in_background when supported, and existing exec chain / gating (`.env`) / dispatch–combine scaffolding. Which agents are available is configured via **agent-registry.json** and **`.env`** at each endpoint.

---

*Summary from web research and repo docs (e.g. axom-dispatch SKILL, install_agent_config, server prompts). Axom is agent-agnostic: any-to-any orchestration; specific agents are configured per endpoint via agent-registry.json and .env.*
