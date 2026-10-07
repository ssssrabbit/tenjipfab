// node tools/gen_layout_golden.js  (after tools/dump_layout_inputs.py)
// Extracts buildFlatCells/splitCellsWithRules from HomeScreen.tsx and runs them as-is.
const fs = require('fs'), path = require('path'), Module = require('module');
const APP = process.env.TENJI_RN_APP;   // path to the tenji-pfab-rn (React Native) app checkout
if (!APP) { console.error('Set TENJI_RN_APP to the tenji-pfab-rn app directory'); process.exit(1); }
const ts = require(path.join(APP, 'node_modules/typescript'));
const full = fs.readFileSync(path.join(APP, 'src/screens/HomeScreen.tsx'), 'utf8');
const a = full.indexOf('// 接頭符セット');
const endMarker = 'const INPUT_RATIO_MIN';
const body = full.slice(a, full.indexOf(endMarker));   // PREFIX_MARKS .. end of buildFlatCells
const src = `import { DAKUTEN_MARK, HANDAKUTEN_MARK, YOON_MARK, YOON_DAKU_MARK, YOON_HANDAKU_MARK, NUM_INDICATOR,
 FOREIGN_INDICATOR, SPACE_MARK, HYPHEN_MARK, BRAILLE_MAP } from '${APP}/src/logic/brailleLogic';
import { WAVE, TSUNAGI, MASK, GAP_BEFORE_PARTICLE, ATTACH_NUMBER, LETTERLIKE_CHARS } from '${APP}/src/logic/symbols';
 type FlatCellInfo = any; type BrailleLanguage = any;
${body}
export { splitCellsWithRules, buildFlatCells };`;
const out = ts.transpileModule(src, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
const file = path.join(APP, 'src/screens/__extract.js');
const m = new Module(file); m.filename = file; m.paths = Module._nodeModulePaths(path.dirname(file));
// brailleLogic is TS: register a loader hook for .ts via transpile
require.extensions['.ts'] = (mod, fn) => mod._compile(ts.transpileModule(fs.readFileSync(fn, 'utf8'),
  { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText, fn);
m._compile(out, file);
const { splitCellsWithRules, buildFlatCells } = m.exports;
const inputs = JSON.parse(fs.readFileSync('tests/layout_inputs.json', 'utf8'));
const res = [];
for (const inp of inputs) {
  const flat = buildFlatCells(inp.mapped);
  const entry = { text: inp.text, flat: flat.map(c => [c.dots.join(''), c.char, c.wordIdx]), splits: {} };
  for (const w of [3, 5, 8, 12, 20]) entry.splits[w] = splitCellsWithRules(flat, w, 'ja').map(l => l.map(c => [c.dots.join(''), c.char, c.wordIdx]));
  res.push(entry);
}
fs.writeFileSync('tests/golden_layout.json', JSON.stringify(res));
console.log('layout cases', res.length);
