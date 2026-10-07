// Runs the TS app's REAL pipeline (convertWithKuromoji + buildFlatCells + splitCellsWithRules) under Node
// (expo modules and the RN dictionary loader are mocked; kuromoji itself is the real one).
//   node tools/gen_pipeline_golden.js  -> tests/golden_pipeline.json
const fs = require('fs'), path = require('path'), Module = require('module');
const APP = process.env.TENJI_RN_APP;   // path to the tenji-pfab-rn (React Native) app checkout
if (!APP) { console.error('Set TENJI_RN_APP to the tenji-pfab-rn app directory'); process.exit(1); }
const ts = require(path.join(APP, 'node_modules/typescript'));
const kuromoji = require(path.join(APP, 'node_modules/kuromoji'));
const opts = { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } };

require.extensions['.ts'] = (mod, fn) => mod._compile(ts.transpileModule(fs.readFileSync(fn, 'utf8'), opts).outputText, fn);
require.extensions['.gz'] = (mod) => { mod.exports = 0; };

let nodeTokenizer;
const origLoad = Module._load;
Module._load = function (request, parent, isMain) {
  if (request === 'expo-asset') return { Asset: { fromModule: () => ({}) } };
  if (request === 'expo-file-system/legacy') return { documentDirectory: 'file:///', getInfoAsync: async () => ({ exists: true }), makeDirectoryAsync: async () => {}, copyAsync: async () => {} };
  if (/kuromojiLoader$/.test(request)) return { buildTokenizerRN: async () => nodeTokenizer };
  return origLoad.call(this, request, parent, isMain);
};

const full = fs.readFileSync(path.join(APP, 'src/screens/HomeScreen.tsx'), 'utf8');
const body = full.slice(full.indexOf('// 接頭符セット'), full.indexOf('const INPUT_RATIO_MIN'));
const src = `import { DAKUTEN_MARK, HANDAKUTEN_MARK, YOON_MARK, YOON_DAKU_MARK, YOON_HANDAKU_MARK, NUM_INDICATOR,
 FOREIGN_INDICATOR, SPACE_MARK, HYPHEN_MARK, BRAILLE_MAP } from '${APP}/src/logic/brailleLogic';
import { WAVE, TSUNAGI, MASK, GAP_BEFORE_PARTICLE, ATTACH_NUMBER, LETTERLIKE_CHARS } from '${APP}/src/logic/symbols';
 type FlatCellInfo = any; type BrailleLanguage = any;
${body}
export { splitCellsWithRules, buildFlatCells };`;
const file = path.join(APP, 'src/screens/__extract.js');
const m = new Module(file); m.filename = file; m.paths = Module._nodeModulePaths(path.dirname(file));
m._compile(ts.transpileModule(src, opts).outputText, file);
const { splitCellsWithRules, buildFlatCells } = m.exports;
const jp = require(path.join(APP, 'src/logic/japaneseProcessor.ts'));

const texts = JSON.parse(fs.readFileSync('tests/pipeline_texts.json', 'utf8'));
kuromoji.builder({ dicPath: path.join(APP, 'assets/dict') + '/' }).build(async (err, tk) => {
  if (err) throw err;
  nodeTokenizer = tk;
  await jp.initializeKuromoji();
  const ser = (cells) => cells.map(c => [c.dots.join(''), c.char]);
  const res = texts.map(text => {
    const mapped = jp.convertWithKuromoji(text);
    const flat = buildFlatCells(mapped);
    const f = c => [c.dots.join(''), c.char, c.wordIdx];
    const splits = {};
    for (const w of [8, 16]) splits[w] = splitCellsWithRules(flat, w, 'ja').map(l => l.map(f));
    return { text, mapped: mapped.map(x => [x.orig, x.reading, x.pos ?? null, !!x.attachPrev, !!x.isParagraphStart, ser(x.cells)]), flat: flat.map(f), splits };
  });
  fs.writeFileSync('tests/golden_pipeline.json', JSON.stringify(res));
  console.log('pipeline cases', res.length);
});
