// Head-to-head: measure the SAME traced room at OpenTakeoff's detected (title-block) scale
// vs v1's dimension-regressed scale, on the print-rescaled Roberts set.
import { spawn } from 'node:child_process';

const PLAN = 'C:/Users/jason/.claude/skills/jnj-estimate-takeoff/tools/tests/golden/roberts/plan.pdf';
const SHEET = 'plan.pdf#5';           // floor plan
const MCP_DIR = 'C:/Users/jason/AppData/Local/Temp/claude/C--Users-jason-OneDrive-Desktop-Claude/a1f137e3-0929-4308-a51c-3e11b29a3130/scratchpad/opentakeoff/mcp';

// upp = real feet per image px at render scale 2.0  =>  1 / (points_per_foot * 2)
const UPP_DETECTED = 1 / (18.0 * 2);      // 1/4" = 1'-0"  (what OT reads off the title block)
const UPP_V1       = 1 / (16.714 * 2);    // v1's 187-vote dimension regression for p5

const child = spawn('node', ['--import', 'tsx', 'server.ts'], { cwd: MCP_DIR, stdio: ['pipe','pipe','pipe'] });
let buf = ''; const pending = new Map(); let nextId = 1;
child.stdout.on('data', d => { buf += d; let i;
  while ((i = buf.indexOf('\n')) >= 0) { const l = buf.slice(0,i).trim(); buf = buf.slice(i+1); if (!l) continue;
    let m; try { m = JSON.parse(l); } catch { continue; }
    if (m.id && pending.has(m.id)) { pending.get(m.id).resolve(m); pending.delete(m.id); } } });
child.stderr.on('data', () => {});

const send = (method, params) => { const id = nextId++;
  child.stdin.write(JSON.stringify({ jsonrpc:'2.0', id, method, params }) + '\n');
  return new Promise((res, rej) => { pending.set(id, {resolve:res});
    setTimeout(() => { if (pending.has(id)) { pending.delete(id); rej(new Error('timeout '+method)); } }, 180000); }); };
const call = async (name, args={}) => { const r = await send('tools/call', {name, arguments:args});
  if (r.error) return {ERROR:r.error.message};
  try { return JSON.parse(r.result.content[0].text); } catch { return r.result?.content?.[0]?.text; } };

(async () => {
  await send('initialize', { protocolVersion:'2024-11-05', capabilities:{}, clientInfo:{name:'bench',version:'1'} });
  child.stdin.write(JSON.stringify({jsonrpc:'2.0', method:'notifications/initialized'}) + '\n');
  await call('load_plan', { path: PLAN });

  // find a seed inside the building: scan a grid, keep traces that look like rooms
  await call('set_scale', { sheet: SHEET, upp: UPP_DETECTED });
  const seeds = [];
  for (let x = 1400; x <= 3400; x += 400)
    for (let y = 900; y <= 2400; y += 300) seeds.push([x,y]);

  const found = [];
  for (const [x,y] of seeds) {
    const r = await call('one_click', { sheet: SHEET, x, y });
    if (r && r.area_sf && r.area_sf > 40 && r.area_sf < 800) found.push({ x, y, area: r.area_sf, perim: r.perimeter_lf, conf: r.confidence });
    if (found.length >= 4) break;
  }

  console.log('=== ROBERTS p5 — same traces, two scales ===');
  console.log('OT detected scale : 1/4" = 1\'-0"  (18.000 pt/ft)   <- read off the title block');
  console.log('v1 measured scale : 16.714 pt/ft, 187 dimension-string votes  <- print-rescaled set\n');
  console.log('seed(px)        area @ OT-detected   area @ v1-measured    OT overstates by');
  console.log('-'.repeat(78));

  let sumOT = 0, sumV1 = 0;
  for (const f of found) {
    await call('set_scale', { sheet: SHEET, upp: UPP_V1 });
    const rv = await call('one_click', { sheet: SHEET, x: f.x, y: f.y });
    await call('set_scale', { sheet: SHEET, upp: UPP_DETECTED });
    const ro = await call('one_click', { sheet: SHEET, x: f.x, y: f.y });
    if (!rv?.area_sf || !ro?.area_sf) continue;
    sumOT += ro.area_sf; sumV1 += rv.area_sf;
    const pct = ((ro.area_sf / rv.area_sf) - 1) * 100;
    console.log(`(${String(f.x).padStart(4)},${String(f.y).padStart(4)})   ${ro.area_sf.toFixed(1).padStart(10)} SF   ${rv.area_sf.toFixed(1).padStart(14)} SF   ${pct.toFixed(1).padStart(12)}%`);
  }
  console.log('-'.repeat(78));
  if (sumV1) console.log(`TOTAL         ${sumOT.toFixed(1).padStart(10)} SF   ${sumV1.toFixed(1).padStart(14)} SF   ${(((sumOT/sumV1)-1)*100).toFixed(1).padStart(12)}%`);
  child.kill(); process.exit(0);
})().catch(e => { console.error('FATAL', e.message); child.kill(); process.exit(1); });
