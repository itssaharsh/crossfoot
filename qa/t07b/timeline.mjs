// The replay's timeline check: node qa/t07b/timeline.mjs [county.json]
// Builds the timeline from the real county data (site/data/panola.json by default) and checks it against the run's own events:
// the sample step first, one read step per block_read event in event order, one suspect step per suspect event in event order,
// then the audit step, then the end; every step has a caption and a length; the whole lasts 25 to 35 seconds.
import { readFileSync } from 'node:fs';
import { buildTimeline, suspectCaptions } from '../../site/replay.js';

const file = process.argv[2] || new URL('../../site/data/panola.json', import.meta.url).pathname;
const d = JSON.parse(readFileSync(file, 'utf8'));
const tl = buildTimeline(d);
const fails = [];
const ok = (cond, msg) => { if (!cond) fails.push(msg); };

const beats = tl.steps.map(s => s.beat);
const reads = d.events.filter(e => e.k === 'block_read');
const suspects = d.events.filter(e => e.k === 'suspect');
ok(beats[0] === 'sample', `first step is the sample (got ${beats[0]})`);
ok(beats[beats.length - 1] === 'end' && beats[beats.length - 2] === 'audit', 'the audit, then the end, come last');
const rs = tl.steps.filter(s => s.beat === 'read');
ok(rs.length === reads.length, `one read step per block_read event: ${rs.length} steps, ${reads.length} events`);
ok(rs.every((s, i) => s.page === reads[i].p.page && s.block === reads[i].p.block), 'read steps are in event order');
const ss = tl.steps.filter(s => s.beat === 'suspect');
ok(ss.length === suspects.length, `one step per suspect event: ${ss.length} steps, ${suspects.length} events`);
ok(ss.every((s, i) => s.item === suspects[i].p.item), 'suspect steps are in event order');
const order = ['sample', 'read', 'check', 'suspect', 'audit', 'end'];
ok(beats.every((b, i) => i === 0 || order.indexOf(b) >= order.indexOf(beats[i - 1])), `beats run in order: ${[...new Set(beats)].join(' > ')}`);
ok(tl.steps.filter(s => s.beat === 'audit').length === 1, 'one audit step');
ok(tl.steps.every(s => s.ms > 0), 'every step has a length');
ok(tl.steps.filter(s => s.beat !== 'end').every(s => typeof s.caption === 'string' && s.caption.length > 0), 'every step but the end has a caption');
ok(tl.seconds >= 25 && tl.seconds <= 35, `the replay lasts 25 to 35 seconds (${tl.seconds.toFixed(1)})`);
const sample = d.events.find(e => e.k === 'choose_reader').p;
ok(tl.steps[0].caption.includes(`${sample.failing} of ${sample.row_sums}`), 'the sample caption carries the run\'s figures');
const doc = ss.find(s => s.verdict === 'document_inconsistent');
if (doc) ok(suspectCaptions(doc).then.includes('The document disagrees with itself. Listed for a person.'), 'a document_inconsistent verdict is said in the verdict\'s words');
// a county without events has no replay; a step without its data is left out
ok(buildTimeline({ ...d, events: [] }).steps.length === 0, 'no events, no steps');
ok(!buildTimeline({ ...d, events: d.events.filter(e => e.k !== 'choose_reader'), fd: { ...d.fd, run_info: {} } }).steps.some(s => s.beat === 'sample'), 'no sample figures, no sample step');

console.log(JSON.stringify({ file: file.replace(/^.*\/site\/data\//, 'site/data/'), steps: tl.steps.length, beats: Object.fromEntries(order.map(b => [b, beats.filter(x => x === b).length])), seconds: +tl.seconds.toFixed(2), failures: fails }, null, 1));
process.exit(fails.length ? 1 : 0);
