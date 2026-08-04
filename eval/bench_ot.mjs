// Minimal MCP stdio client to bench OpenTakeoff against a J&J residential plan set.
// Usage: node bench_ot.mjs <plan.pdf>
import { spawn } from 'node:child_process';

const PLAN = process.argv[2];
const MCP_DIR = 'C:/Users/jason/AppData/Local/Temp/claude/C--Users-jason-OneDrive-Desktop-Claude/a1f137e3-0929-4308-a51c-3e11b29a3130/scratchpad/opentakeoff/mcp';

const child = spawn('node', ['--import', 'tsx', 'server.ts'], {
  cwd: MCP_DIR, stdio: ['pipe', 'pipe', 'pipe'], shell: false,
});

let buf = '';
const pending = new Map();
let nextId = 1;

child.stdout.on('data', (d) => {
  buf += d.toString();
  let i;
  while ((i = buf.indexOf('\n')) >= 0) {
    const line = buf.slice(0, i).trim();
    buf = buf.slice(i + 1);
    if (!line) continue;
    let msg;
    try { msg = JSON.parse(line); } catch { continue; }
    if (msg.id && pending.has(msg.id)) {
      const { resolve } = pending.get(msg.id);
      pending.delete(msg.id);
      resolve(msg);
    }
  }
});
child.stderr.on('data', (d) => process.stderr.write('[mcp] ' + d.toString()));

function send(method, params) {
  const id = nextId++;
  const msg = { jsonrpc: '2.0', id, method, params };
  child.stdin.write(JSON.stringify(msg) + '\n');
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    setTimeout(() => { if (pending.has(id)) { pending.delete(id); reject(new Error('timeout ' + method)); } }, 180000);
  });
}

const call = async (name, args = {}) => {
  const r = await send('tools/call', { name, arguments: args });
  if (r.error) return { ERROR: r.error };
  const c = r.result?.content?.[0];
  return c?.text ?? r.result;
};

(async () => {
  await send('initialize', {
    protocolVersion: '2024-11-05',
    capabilities: {},
    clientInfo: { name: 'bench', version: '1.0' },
  });
  child.stdin.write(JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' }) + '\n');

  const tools = await send('tools/list', {});
  console.log('=== TOOLS EXPOSED:', (tools.result?.tools || []).length);

  console.log('\n=== load_plan ===');
  console.log((await call('load_plan', { path: PLAN })).slice?.(0, 3000) ?? '');

  console.log('\n=== sheet_info (page 1) ===');
  console.log((await call('sheet_info', { sheet: 'plan.pdf' })).slice?.(0, 2500) ?? '');

  console.log('\n=== takeoff_summary ===');
  console.log((await call('takeoff_summary', {})).slice?.(0, 1500) ?? '');

  child.kill();
  process.exit(0);
})().catch((e) => { console.error('FATAL', e); child.kill(); process.exit(1); });
