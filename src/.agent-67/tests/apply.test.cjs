const test = require('node:test');
const assert = require('node:assert/strict');

const {
  generateEnvExample,
  listEnabledAgents,
  parseDotEnv,
  resolveEnvValue,
  mergeMissingTopLevelKeys,
  renderCodexMcpConfig,
} = require('../scripts/apply.cjs');

test('OS env takes precedence over .env values', () => {
  const envFile = { OPENAI_API_KEY: 'from-dotenv' };
  const osEnv = { OPENAI_API_KEY: 'from-os' };
  assert.equal(resolveEnvValue('OPENAI_API_KEY', osEnv, envFile), 'from-os');
});

test('.env values are used when OS env is missing', () => {
  const envFile = { OPENAI_API_KEY: 'from-dotenv' };
  assert.equal(resolveEnvValue('OPENAI_API_KEY', {}, envFile), 'from-dotenv');
});

test('.env.example is generated from enabled agents only', () => {
  const config = {
    agents: {
      codex: { enabled: true, requiredEnv: ['OPENAI_API_KEY'] },
      cursor: { enabled: true, requiredEnv: ['EXA_API_KEY', 'OPENAI_API_KEY'] },
      gemini: { enabled: false, requiredEnv: ['GEMINI_API_KEY'] },
    },
  };
  assert.equal(
    generateEnvExample(config),
    ['EXA_API_KEY=', 'OPENAI_API_KEY='].join('\n') + '\n'
  );
});

test('only enabled agents are selected', () => {
  const config = {
    agents: {
      codex: { enabled: true },
      cursor: { enabled: false },
      claude: { enabled: true },
    },
  };
  assert.deepEqual(listEnabledAgents(config).map(([name]) => name), ['codex', 'claude']);
});

test('top-level JSON merge injects only missing keys', () => {
  const current = { keep: true, existing: { value: 1 } };
  const incoming = { existing: { value: 2 }, add: { value: 3 } };
  assert.deepEqual(mergeMissingTopLevelKeys(current, incoming), {
    keep: true,
    existing: { value: 1 },
    add: { value: 3 },
  });
});

test('dotenv parser handles comments and simple assignments', () => {
  assert.deepEqual(
    parseDotEnv('# comment\nOPENAI_API_KEY=value\nEXA_API_KEY=two words\n'),
    { OPENAI_API_KEY: 'value', EXA_API_KEY: 'two words' }
  );
});

test('codex config appends missing MCP servers in native TOML format', () => {
  const current = [
    '[features]',
    'multi_agent = true',
    '',
    '[mcp_servers.Existing]',
    'command = "keep"',
    '',
  ].join('\n');

  const next = renderCodexMcpConfig(current, {
    Demo: {
      command: 'codex',
      args: ['mcp-server'],
    },
    Ref: {
      url: 'https://example.com/mcp',
    },
    Tauri: {
      command: 'npx',
      args: ['-y', '@hypothesi/tauri-mcp-server'],
      env: {
        FOO: 'bar',
      },
    },
    Existing: {
      command: 'should-not-overwrite',
    },
  });

  assert.match(next, /\[mcp_servers\.Existing\]\ncommand = "keep"\n/);
  assert.match(next, /# agent-67:start codex-mcp\n\n\[mcp_servers\.Demo\]\ncommand = "codex"\nargs = \["mcp-server"\]\n/);
  assert.match(next, /\[mcp_servers\.Ref\]\nurl = "https:\/\/example\.com\/mcp"\n/);
  assert.match(
    next,
    /\[mcp_servers\.Tauri\]\ncommand = "npx"\nargs = \["-y", "@hypothesi\/tauri-mcp-server"\]\n\n\[mcp_servers\.Tauri\.env\]\nFOO = "bar"\n\n# agent-67:end codex-mcp\n/
  );
  assert.equal(next.match(/\[mcp_servers\.Existing\]/g)?.length, 1);
});

test('codex config replaces the managed MCP block on reapply', () => {
  const current = [
    '[features]',
    'multi_agent = true',
    '',
    '# agent-67:start codex-mcp',
    '',
    '[mcp_servers.Ref]',
    'url = "https://stale.example/mcp"',
    '',
    '# agent-67:end codex-mcp',
    '',
  ].join('\n');

  const next = renderCodexMcpConfig(current, {
    Ref: {
      url: 'https://example.com/mcp?apiKey=secret',
    },
  });

  assert.doesNotMatch(next, /stale\.example/);
  assert.match(next, /\[mcp_servers\.Ref\]\nurl = "https:\/\/example\.com\/mcp\?apiKey=secret"\n/);
  assert.equal(next.match(/# agent-67:start codex-mcp/g)?.length, 1);
});

test('codex config renders startup timeout for Chrome DevTools MCP server', () => {
  const next = renderCodexMcpConfig('', {
    ChromeDevTools: {
      command: 'npx',
      args: ['-y', 'chrome-devtools-mcp@latest', '--browser-url=http://127.0.0.1:9222'],
      env: {
        SYSTEMROOT: 'C:\\Windows',
      },
      startup_timeout_ms: 20000,
    },
  });

  assert.match(
    next,
    /\[mcp_servers\.ChromeDevTools\]\ncommand = "npx"\nargs = \["-y", "chrome-devtools-mcp@latest", "--browser-url=http:\/\/127\.0\.0\.1:9222"\]\nstartup_timeout_ms = 20000\n/
  );
  assert.match(next, /\[mcp_servers\.ChromeDevTools\.env\]\nSYSTEMROOT = "C:\\\\Windows"\n/);
});
