const fs = require('node:fs');
const fsp = fs.promises;
const os = require('node:os');
const path = require('node:path');
const ROOT = path.resolve(__dirname, '..');
const SKILLS_ROOT = path.join(process.env.HOME || process.env.USERPROFILE, '.agentskills');
const CONFIG_PATH = path.join(ROOT, 'agents.json');
const ENV_PATH = path.join(ROOT, '.env');
const ENV_EXAMPLE_PATH = path.join(ROOT, '.env.example');
const MANAGED_START = '<!-- agent-67:start -->';
const MANAGED_END = '<!-- agent-67:end -->';
const CODEX_MCP_START = '# agent-67:start codex-mcp';
const CODEX_MCP_END = '# agent-67:end codex-mcp';

function parseArgs(argv) {
  return {
    dryRun: argv.includes('--dry-run'),
    agentNames: argv.filter((arg) => !arg.startsWith('--')),
  };
}

function parseDotEnv(content) {
  const out = {};
  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) {
      continue;
    }
    const eqIndex = line.indexOf('=');
    if (eqIndex === -1) {
      continue;
    }
    const key = line.slice(0, eqIndex).trim();
    const value = line.slice(eqIndex + 1).trim();
    if (key) {
      out[key] = value;
    }
  }
  return out;
}

function resolveEnvValue(name, osEnv, envFile) {
  if (Object.prototype.hasOwnProperty.call(osEnv, name) && osEnv[name]) {
    return osEnv[name];
  }
  if (Object.prototype.hasOwnProperty.call(envFile, name) && envFile[name]) {
    return envFile[name];
  }
  return '';
}

function listEnabledAgents(config) {
  return Object.entries(config.agents || {}).filter(([, agent]) => agent && agent.enabled);
}

function generateEnvExample(config) {
  const keys = new Set();
  for (const [, agent] of listEnabledAgents(config)) {
    for (const key of agent.requiredEnv || []) {
      keys.add(key);
    }
  }
  return [...keys].sort().map((key) => `${key}=`).join('\n') + (keys.size ? '\n' : '');
}

function mergeMissingTopLevelKeys(current, incoming) {
  const next = { ...current };
  for (const [key, value] of Object.entries(incoming)) {
    if (!(key in next)) {
      next[key] = value;
    }
  }
  return next;
}

function mergeMissingNamedChildren(current, parentKey, incoming) {
  const next = { ...current };
  const base = next[parentKey] && typeof next[parentKey] === 'object' ? next[parentKey] : {};
  next[parentKey] = { ...base };
  for (const [key, value] of Object.entries(incoming)) {
    if (!(key in next[parentKey])) {
      next[parentKey][key] = value;
    }
  }
  return next;
}

function renderTemplateValue(value, resolvedEnv) {
  if (typeof value === 'string') {
    return value.replace(/\$\{([A-Z0-9_]+)\}/g, (_, key) => resolvedEnv[key] || '');
  }
  if (Array.isArray(value)) {
    return value.map((item) => renderTemplateValue(item, resolvedEnv));
  }
  if (value && typeof value === 'object') {
    const out = {};
    for (const [key, child] of Object.entries(value)) {
      out[key] = renderTemplateValue(child, resolvedEnv);
    }
    return out;
  }
  return value;
}

function formatTomlString(value) {
  return JSON.stringify(String(value));
}

function formatTomlArray(values) {
  return `[${values.map((value) => formatTomlString(value)).join(', ')}]`;
}

function hasCodexMcpServer(content, serverName) {
  const pattern = new RegExp(`^\\[mcp_servers\\.${escapeRegExp(serverName)}\\]$`, 'm');
  return pattern.test(content);
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function upsertCodexManagedBlock(content, block) {
  const managed = `${CODEX_MCP_START}\n\n${block.trim()}\n\n${CODEX_MCP_END}\n`;
  if (content.includes(CODEX_MCP_START) && content.includes(CODEX_MCP_END)) {
    return content.replace(
      new RegExp(`${escapeRegExp(CODEX_MCP_START)}[\\s\\S]*?${escapeRegExp(CODEX_MCP_END)}\\n?`, 'm'),
      managed
    );
  }
  const prefix = content && !content.endsWith('\n') ? '\n' : '';
  const spacer = content ? '\n' : '';
  return `${content}${prefix}${spacer}${managed}`;
}

function renderCodexMcpServer(name, server) {
  const lines = [`[mcp_servers.${name}]`];

  if (server.url) {
    lines.push(`url = ${formatTomlString(server.url)}`);
  } else {
    lines.push(`command = ${formatTomlString(server.command || '')}`);
    if (Array.isArray(server.args) && server.args.length) {
      lines.push(`args = ${formatTomlArray(server.args)}`);
    }
  }

  if (typeof server.startup_timeout_ms === 'number') {
    lines.push(`startup_timeout_ms = ${server.startup_timeout_ms}`);
  }

  if (server.bearer_token_env_var) {
    lines.push(`bearer_token_env_var = ${formatTomlString(server.bearer_token_env_var)}`);
  }

  if (server.env && Object.keys(server.env).length) {
    lines.push('');
    lines.push(`[mcp_servers.${name}.env]`);
    for (const [key, value] of Object.entries(server.env)) {
      lines.push(`${key} = ${formatTomlString(value)}`);
    }
  }

  return lines.join('\n');
}

function renderCodexMcpConfig(current, sharedServers) {
  let unmanaged = current;
  if (current.includes(CODEX_MCP_START) && current.includes(CODEX_MCP_END)) {
    unmanaged = current.replace(
      new RegExp(`${escapeRegExp(CODEX_MCP_START)}[\\s\\S]*?${escapeRegExp(CODEX_MCP_END)}\\n?`, 'm'),
      ''
    ).trimEnd();
  }

  const blocks = [];

  for (const [name, server] of Object.entries(sharedServers)) {
    if (hasCodexMcpServer(unmanaged, name)) {
      continue;
    }
    blocks.push(renderCodexMcpServer(name, server));
  }

  if (!blocks.length) {
    return unmanaged ? `${unmanaged}\n` : '';
  }

  return upsertCodexManagedBlock(unmanaged, blocks.join('\n\n'));
}

async function pathExists(targetPath) {
  try {
    await fsp.access(targetPath);
    return true;
  } catch {
    return false;
  }
}

async function ensureDir(targetPath) {
  await fsp.mkdir(targetPath, { recursive: true });
}

async function readText(targetPath, fallback = '') {
  try {
    return await fsp.readFile(targetPath, 'utf8');
  } catch {
    return fallback;
  }
}

async function readJson(targetPath, fallback) {
  try {
    return JSON.parse(await fsp.readFile(targetPath, 'utf8'));
  } catch {
    return fallback;
  }
}

async function writeText(targetPath, content, dryRun, changes, summary) {
  changes.push(summary);
  if (dryRun) {
    return;
  }
  await ensureDir(path.dirname(targetPath));
  await fsp.writeFile(targetPath, content, 'utf8');
}

async function copyDir(sourceDir, targetDir, dryRun, changes) {
  changes.push(`sync dir ${targetDir}`);
  if (dryRun) {
    return;
  }
  await ensureDir(targetDir);
  for (const entry of await fsp.readdir(sourceDir, { withFileTypes: true })) {
    const sourcePath = path.join(sourceDir, entry.name);
    const targetPath = path.join(targetDir, entry.name);
    if (entry.isDirectory()) {
      await copyDir(sourcePath, targetPath, dryRun, changes);
    } else {
      await ensureDir(path.dirname(targetPath));
      await fsp.copyFile(sourcePath, targetPath);
    }
  }
}

function upsertManagedBlock(content, block) {
  const managed = `${MANAGED_START}\n${block.trim()}\n${MANAGED_END}\n`;
  if (content.includes(MANAGED_START) && content.includes(MANAGED_END)) {
    return content.replace(
      new RegExp(`${escapeRegExp(MANAGED_START)}[\\s\\S]*?${escapeRegExp(MANAGED_END)}\\n?`, 'm'),
      managed
    );
  }
  const prefix = content && !content.endsWith('\n') ? '\n' : '';
  return `${content}${prefix}${managed}`;
}

function expandTilde(filepath) {
  if (typeof filepath !== 'string') return filepath;
  if (filepath.startsWith('~')) {
    return filepath.replace(/^~/, os.homedir());
  }
  return filepath;
}

function expandAgentPaths(agent) {
  if (!agent.paths) return agent;
  const expanded = {};
  for (const [key, value] of Object.entries(agent.paths)) {
    expanded[key] = expandTilde(value);
  }
  return { ...agent, paths: expanded };
}

async function applySkillFolder(skillName, targetDir, dryRun, changes) {
  const sourceDir = path.join(SKILLS_ROOT, skillName);
  await copyDir(sourceDir, path.join(targetDir, skillName), dryRun, changes);
}

async function applyClaudeSkill(skillName, targetDir, dryRun, changes) {
  const sourcePath = path.join(SKILLS_ROOT, skillName, 'SKILL.md');
  const targetPath = path.join(targetDir, `${skillName}.md`);
  const content = await readText(sourcePath, '');
  await writeText(targetPath, content, dryRun, changes, `write file ${targetPath}`);
}

async function applyJsonServers(jsonPath, sharedServers, resolvedEnv, dryRun, changes) {
  const current = await readJson(jsonPath, { mcpServers: {} });
  const renderedServers = renderTemplateValue(sharedServers, resolvedEnv);
  const merged = mergeMissingNamedChildren(current, 'mcpServers', renderedServers);
  await writeText(jsonPath, `${JSON.stringify(merged, null, 2)}\n`, dryRun, changes, `write file ${jsonPath}`);
}

async function applyCodexServers(configPath, sharedServers, resolvedEnv, dryRun, changes) {
  const current = await readText(configPath, '');
  const renderedServers = renderTemplateValue(sharedServers, resolvedEnv);
  const next = renderCodexMcpConfig(current, renderedServers);
  if (next === current) {
    return;
  }
  await writeText(configPath, next, dryRun, changes, `write file ${configPath}`);
}

async function applyManagedText(targetPath, block, dryRun, changes) {
  const current = await readText(targetPath, '');
  const next = upsertManagedBlock(current, block);
  await writeText(targetPath, next, dryRun, changes, `write file ${targetPath}`);
}

function getMissingEnv(agent, resolvedEnv) {
  return (agent.requiredEnv || []).filter((key) => !resolvedEnv[key]);
}

function buildKiroBlock() {
  return [
    '# Agent 67',
    '',
    '- Source of truth lives in `C:\\Users\\User\\.agent-67`.',
    '- Edit shared skills, rules, and config only at `C:\\Users\\User\\.agentskills\\`.',
    '- Resolve secrets from OS env first, then `C:\\Users\\User\\.agent-67\\.env`.',
    '- Run `C:\\Users\\User\\.agent-67\\scripts\\windows.ps1` after changes.',
    '- Verify local config is present before claiming setup is complete.',
    '- Tell the user to restart Kiro after apply.',
  ].join('\n');
}

async function applyAgent(name, agent, config, resolvedEnv, options, changes, notices) {
  agent = expandAgentPaths(agent);
  const missingEnv = getMissingEnv(agent, resolvedEnv);
  if (missingEnv.length) {
    notices.push(`${name}: skipped, missing env ${missingEnv.join(', ')}`);
    return;
  }

  if (name === 'codex') {
    if (agent.paths.skills) {
      for (const skillName of config.shared.skills || []) {
        await applySkillFolder(skillName, agent.paths.skills, options.dryRun, changes);
      }
    }
    if (agent.paths.config) {
      await applyCodexServers(agent.paths.config, config.shared.mcpServers, resolvedEnv, options.dryRun, changes);
    }
    notices.push('codex: restart Codex to pick up skill and MCP updates');
    return;
  }

  if (name === 'cursor') {
    if (agent.paths['skills-cursor']) {
      for (const skillName of config.shared.skills || []) {
        await applySkillFolder(skillName, agent.paths['skills-cursor'], options.dryRun, changes);
      }
    }
    if (agent.paths.mcp) {
      await applyJsonServers(agent.paths.mcp, config.shared.mcpServers, resolvedEnv, options.dryRun, changes);
    }
    notices.push('cursor: restart Cursor to pick up config changes');
    return;
  }

  if (name === 'claude') {
    if (agent.paths.skills) {
      for (const skillName of config.shared.skills || []) {
        await applyClaudeSkill(skillName, agent.paths.skills, options.dryRun, changes);
      }
    }
    notices.push('claude: restart Claude to pick up skill updates');
    return;
  }

  if (name === 'gemini') {
    if (agent.paths.mcp) {
      await applyJsonServers(agent.paths.mcp, config.shared.mcpServers, resolvedEnv, options.dryRun, changes);
    }
    notices.push('gemini: restart Gemini to pick up MCP changes');
    return;
  }

  if (name === 'kilocode') {
    if (agent.paths.skills) {
      for (const skillName of config.shared.skills || []) {
        await applySkillFolder(skillName, agent.paths.skills, options.dryRun, changes);
      }
    }
    if (agent.paths.mcp) {
      await applyJsonServers(agent.paths.mcp, config.shared.mcpServers, resolvedEnv, options.dryRun, changes);
    }
    notices.push('kilocode: restart Kilocode to pick up config changes');
    return;
  }

  if (name === 'cline') {
    if (agent.paths.skills) {
      for (const skillName of config.shared.skills || []) {
        await applySkillFolder(skillName, agent.paths.skills, options.dryRun, changes);
      }
    }
    if (agent.paths.mcp) {
      await applyJsonServers(agent.paths.mcp, config.shared.mcpServers, resolvedEnv, options.dryRun, changes);
    }
    notices.push('cline: restart Cline to pick up config changes');
    return;
  }

  if (name === 'vibe') {
    if (agent.paths.config) {
      await applyJsonServers(agent.paths.config, config.shared.mcpServers, resolvedEnv, options.dryRun, changes);
    }
    notices.push('vibe: restart Vibe to pick up config changes');
    return;
  }

  if (name === 'kiro') {
    if (agent.paths.agents) {
      await applyManagedText(agent.paths.agents, buildKiroBlock(), options.dryRun, changes);
    }
    notices.push('kiro: restart Kiro to pick up AGENTS changes');
  }
}

async function main(argv = process.argv.slice(2)) {
  const options = parseArgs(argv);
  const config = JSON.parse(await fsp.readFile(CONFIG_PATH, 'utf8'));
  const envFile = (await pathExists(ENV_PATH)) ? parseDotEnv(await fsp.readFile(ENV_PATH, 'utf8')) : {};
  const enabledAgents = listEnabledAgents(config).filter(([name]) => {
    return !options.agentNames.length || options.agentNames.includes(name);
  });

  const envExample = generateEnvExample({
    agents: Object.fromEntries(enabledAgents),
  });
  const changes = [];
  const notices = [];
  const resolvedEnv = {};

  for (const [, agent] of enabledAgents) {
    for (const key of agent.requiredEnv || []) {
      resolvedEnv[key] = resolveEnvValue(key, process.env, envFile);
    }
  }

  await writeText(ENV_EXAMPLE_PATH, envExample, options.dryRun, changes, `write file ${ENV_EXAMPLE_PATH}`);

  for (const [name, agent] of enabledAgents) {
    const expandedAgent = expandAgentPaths(agent);
    const firstPath = Object.values(expandedAgent.paths || {})[0];
    if (!firstPath || !(await pathExists(path.dirname(firstPath))) && !(await pathExists(firstPath))) {
      notices.push(`${name}: skipped, target path not found`);
      continue;
    }
    await applyAgent(name, expandedAgent, config, resolvedEnv, options, changes, notices);
  }

  return {
    dryRun: options.dryRun,
    enabledAgents: enabledAgents.map(([name]) => name),
    envKeys: Object.keys(resolvedEnv).sort(),
    changes,
    notices,
  };
}

if (require.main === module) {
  main()
    .then((result) => {
      process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
    })
    .catch((error) => {
      process.stderr.write(`${error.stack || error.message}\n`);
      process.exitCode = 1;
    });
}

module.exports = {
  ROOT,
  SKILLS_ROOT,
  generateEnvExample,
  listEnabledAgents,
  mergeMissingTopLevelKeys,
  parseDotEnv,
  renderCodexMcpConfig,
  resolveEnvValue,
  main,
};
