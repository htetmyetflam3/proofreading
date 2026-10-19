// Offline production entry: supplied Engine + freshly rebuilt required WASM.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { configureWorkspace } from './Bridge/path.js';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const [sourceArg, workArg, resultArg] = process.argv.slice(2);
if (!sourceArg || !workArg || !resultArg) {
  console.error('usage: node engine/tag-text.mjs SOURCE_TEXT WORK_DIR RESULT_JSON');
  process.exit(2);
}
const source = path.resolve(sourceArg), work = path.resolve(workArg);
const masterPath = path.join(ROOT, 'engine/knowledge/isTreasure/master.json');
const masterBytes = fs.readFileSync(masterPath), masterHash = hash(masterBytes);
const build = JSON.parse(fs.readFileSync(path.join(ROOT, 'scraper/wasm/box/build-info.json')));
if (build.input_sha256['engine/knowledge/isTreasure/master.json'] !== masterHash) {
  throw new Error('Master data changed after the WASM build. Rebuild WASM before tagging; no fallback.');
}
const treeDir = path.join(work, 'tree'), dataDir = path.join(work, 'data');
const outputDir = path.join(work, 'out'), logDir = path.join(work, 'log');
for (const dir of [treeDir, dataDir, outputDir, logDir]) fs.mkdirSync(dir, {recursive:true});
const cacheRoot = path.join(ROOT, 'scraper/Engine/.cache-tree');
const cacheSource = JSON.parse(fs.readFileSync(path.join(ROOT, 'scraper/Engine/CACHE-SOURCE.json')));
for (const [name, expected] of Object.entries(cacheSource.sha256)) {
  const bytes = fs.readFileSync(path.join(cacheRoot, name));
  if (hash(bytes) !== expected) throw new Error(`Original scraper cache hash mismatch: ${name}`);
  fs.writeFileSync(path.join(treeDir, name), bytes);
}
// Never let the supplied builder's cleanup overwrite the owner's master.
fs.writeFileSync(path.join(dataDir, 'master.json'), masterBytes);
for (const name of ['pos.tree.json','pos-fail.txt']) {
  fs.rmSync(path.join(treeDir, name), {force:true});
}
configureWorkspace({treeDir, dataDir, outputDir, logDir});
const { init: initLog } = await import('./Bridge/logen.js');
initLog({DEBUG:false, MODE:'multi', SEGMENTED_MODE:'fromdisk'});
const { runBuildPos } = await import('./MonoSyllabism/graph/build.js');
const tree = await runBuildPos(treeDir);
if (!Object.keys(tree).length) throw new Error('POS build produced an empty tree; refusing to label an untagged book as tagged');
const { readAndPrepare } = await import('./MonoSyllabism/generators/input.js');
const { runSegmentor } = await import('./MonoSyllabism/main/phoneme/lexer.js');
const { setHash } = await import('./MonoSyllabism/utilities/disk.js');
const { bridge } = await import('./Bridge/bridge.js');
const session = hash(fs.readFileSync(source)).slice(0,24);
setHash(session);
const result = await bridge(runSegmentor(readAndPrepare(source)), {syllable:false, rawPos:true}, session, source);
if (!result.rawPosPath || !fs.statSync(result.rawPosPath).size) throw new Error('No tagged output produced');
if (hash(fs.readFileSync(masterPath)) !== masterHash) throw new Error('Original master was modified');
const raw = fs.readFileSync(result.rawPosPath, 'utf8');
const failFile = path.join(treeDir, 'pos-fail.txt');
const stats = {
  runtime:'required rebuilt scraper WASM',
  wasm_box:'scraper/wasm/box/box.wasm',
  wasm_host:'scraper/wasm/box/host.mjs',
  wasm_instance_scope:'shared module instance',
  input_pipeline:'WASM mapperNormalize; English/digit blocks masked before segmentation',
  wasm_sha256:build.box_sha256, master_sha256:masterHash,
  scraper_cache_commit:cacheSource.commit,
  source_sha256:hash(fs.readFileSync(source)),
  raw_pos_path:result.rawPosPath, raw_pos_sha256:hash(Buffer.from(raw)),
  raw_pos_bytes:Buffer.byteLength(raw), output_units:result.lineCount,
  pos_tree_roots:Object.keys(tree).length,
  rejected_dictionary_entries:fs.existsSync(failFile) ? fs.readFileSync(failFile,'utf8').trim().split('\n').filter(Boolean).length : 0,
  tag_occurrences:[...raw.matchAll(/\{[^{}]+\}/g)].length,
  unknown_tag_occurrences:[...raw.matchAll(/\{\?\}/g)].length,
  ambiguous_tag_occurrences:[...raw.matchAll(/\{[^{}]*,[^{}]*\}/g)].length,
  rule_engine:'owner pass-through; raw POS candidates retained, not grammar-disambiguated',
  phrase_alignment:'not established',
  original_master_unchanged:true,
};
fs.writeFileSync(path.resolve(resultArg), JSON.stringify(stats,null,2)+'\n');
console.log(`[tagged] ${result.lineCount} units -> ${result.rawPosPath}`);
