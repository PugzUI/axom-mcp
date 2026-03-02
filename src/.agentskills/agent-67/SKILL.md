---
name: agent-67
description: Shared agent bootstrap and config sync skill. Use when an agent needs to verify its own local config, resolve shared env-backed settings from `C:\Users\User\.agent-67`, apply the shared map to enabled agents, or confirm the user should restart after sync.
---

# Agent 67

Use `C:\Users\User\.agent-67` as the only source of truth.

## Workflow

1. Verify your own local config surface before changing anything.
2. Read `C:\Users\User\.agent-67\agents.json` to see which agents are enabled.
3. Resolve secrets from OS environment first, then `C:\Users\User\.agent-67\.env`.
4. Update `C:\Users\User\.agent-67\.env.example` from the enabled agents' required keys.
5. Run `C:\Users\User\.agent-67\scripts\windows.ps1` on Windows or `~/.agent-67/scripts/linux.sh` on Linux.
6. Verify the expected target files were updated for the enabled agents you touched.
7. Tell the user to restart the affected agent instances.

## Rules

- Edit shared skills only under `C:\Users\User\.agentskills\`.
- Do not edit generated target copies first.
- Do not use symlinks.
- Only update enabled agents.
- Inject or append missing config; do not remove unrelated user settings.
