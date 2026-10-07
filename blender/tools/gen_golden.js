// Generates tests/golden.json from the TS app's real logic (read-only access to the app repo).
//   node tools/gen_golden.js
const fs = require('fs'), path = require('path'), Module = require('module');
const APP = process.env.TENJI_RN_APP;   // path to the tenji-pfab-rn (React Native) app checkout
if (!APP) { console.error('Set TENJI_RN_APP to the tenji-pfab-rn app directory'); process.exit(1); }
const ts = require(path.join(APP, 'node_modules/typescript'));
const kuromoji = require(path.join(APP, 'node_modules/kuromoji'));

function loadTs(file) {
  const src = ts.transpileModule(fs.readFileSync(file, 'utf8'),
    { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
  const m = new Module(file); m.filename = file; m.paths = Module._nodeModulePaths(path.dirname(file));
  m._compile(src, file); return m.exports;
}
const bl = loadTs(path.join(APP, 'src/logic/brailleLogic.ts'));

// kanaToCells inputs: every table key, plus mixed samples
const kana = [...Object.keys(bl.BRAILLE_MAP), 'がっこう', 'きゃく', 'ぴょん', 'ぢゃ', 'らーめん', 'ABC', '123', 'a1b2', 'あ1い', '、。', '   ', 'ぱぴぷぺぽ', 'ふぁ', 'ゔ', 'ウ', '漢', 'X', 'DOS', 'aBc', 'Dos', 'ABc', 'A1', 'Xせん'];
const kanaCases = kana.map(t => ({ text: t, cells: bl.kanaToCells(t).map(c => [c.dots.join(''), c.char]) }));

const texts = ['私は東京へ行きました。', 'こんにちは', '今日はいい天気です', '点字を自動的に変換する', '東京都', '大きい', '十二月三日', 'お父さんは本を読む', '学校へ行く', '京都大学', '100円玉', '東京8時36分→長野10時2分', '10時～12時', 'X線', '山田さん', '3らしい', '第3回'];
kuromoji.builder({ dicPath: path.join(APP, 'assets/dict') + '/' }).build((err, tk) => {
  if (err) throw err;
  const tokens = texts.map(t => ({ text: t, tokens: tk.tokenize(t).map(x => [x.surface_form, x.reading, x.pos, x.pos_detail_1]) }));
  fs.mkdirSync('tests', { recursive: true });
  fs.writeFileSync('tests/golden.json', JSON.stringify({ kanaCases, tokens }, null, 1));
  console.log('kana', kanaCases.length, 'tokens', tokens.length);
});
