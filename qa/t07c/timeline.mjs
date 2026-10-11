// The replay timeline of the report counties: node qa/t07c/timeline.mjs [county ...]   (default: san_saba jones lynn cottle)
// Builds the timeline from the real county data (site/data/<county>.json) and checks it against the run's own events: the sample
// step first, one read step per page_read event in event order, one step per item the run worked (an item with re-reads), in
// event order, then the audit step when the county has findings, then the end; every step has a caption and a length; every
// step that points at a row names a value the county has, and that row has a crop for the loupe.
import { readFileSync } from 'node:fs';
import { buildTimeline } from '../../site/replay.js';

const keys = process.argv.slice(2).length ? process.argv.slice(2) : ['san_saba', 'jones', 'lynn', 'cottle'];
const out = [];
let bad = 0;
for (const key of keys) {
  const d = JSON.parse(readFileSync(new URL(`../../site/data/${key}.json`, import.meta.url), 'utf8'));
  const tl = buildTimeline(d);
  const fails = [];
  const ok = (c, m) => { if (!c) fails.push(m); };
  const beats = tl.steps.map(s => s.beat);
  const reads = d.events.filter(e => e.k === 'page_read');
  const rs = tl.steps.filter(s => s.beat === 'read');
  ok(beats[0] === 'sample', `first step is the sample (got ${beats[0]})`);
  ok(rs.length === reads.length && rs.every((s, i) => s.page === reads[i].p.page), `one read step per page_read event, in order: ${rs.length} steps, ${reads.length} events`);
  const worked = new Map();
  for (const e of d.events) if (e.k === 'reread') worked.set(e.p.item, true);
  const starts = d.events.filter(e => e.k === 'item_start' && worked.has(e.p.item));
  const ss = tl.steps.filter(s => s.beat === 'suspect');
  ok(ss.length === starts.length && ss.every((s, i) => s.item === starts[i].p.item), `one step per item with re-reads, in order: ${ss.length} steps, ${starts.length} items`);
  const hasFindings = d.fd && d.fd.items.length > 0;
  ok(tl.steps.filter(s => s.beat === 'audit').length === (hasFindings ? 1 : 0), 'the audit step is there when the county has findings');
  ok(beats[beats.length - 1] === 'end', 'the end comes last');
  const order = ['sample', 'read', 'check', 'suspect', 'audit', 'end'];
  ok(beats.every((b, i) => i === 0 || order.indexOf(b) >= order.indexOf(beats[i - 1])), 'beats run in order');
  ok(tl.steps.every(s => s.ms > 0), 'every step has a length');
  ok(tl.steps.filter(s => s.beat !== 'end').every(s => typeof s.caption === 'string' && s.caption.length > 0), 'every step but the end has a caption');
  const byId = new Map(d.values.map((v, i) => [`${v.p}:${v.b}:${v.r}:${v.c}`, i]));
  const rc = new Set((d.rc || []).map(r => `${r.p}:${r.b}:${r.r}`));
  for (const s of ss) {
    ok(byId.has(s.entity.join(':')), `step ${s.item} names a value the county has (${s.entity.join(':')})`);
    ok(rc.has(s.entity.slice(0, 3).join(':')), `step ${s.item}: the row has a crop for the loupe`);
  }
  ok(buildTimeline({ ...d, events: [] }).steps.length === 0, 'no events, no steps');
  out.push({ county: key, steps: tl.steps.length, beats: Object.fromEntries(order.map(b => [b, beats.filter(x => x === b).length])), seconds: +tl.seconds.toFixed(1), failures: fails });
  bad += fails.length;
}
console.log(JSON.stringify(out, null, 1));
process.exit(bad ? 1 : 0);
