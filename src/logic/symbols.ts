// 括弧（カギ類・カッコ類）・波線・矢印。
// 文部科学省「点字表記法」第6章第3節（囲み符号・関係符号の用法）の図から読み取った点の配置。
// 点は左列=点1,2,3 / 右列=点4,5,6 の順の6桁。
import { WordMapping } from './brailleLogic';

const d = (p: string): number[] => p.split('').map(Number);

export const TSUNAGI = '001001'; // 第1つなぎ符（点3,6）

type Style = 'KAGI1' | 'KAGI_FUTAE' | 'KAGI2' | 'KAKKO1' | 'KAKKO_FUTAE' | 'KAKKO2';
type Family = 'KAGI' | 'KAKKO';

// 種別 -> [開き符号のセル列, 閉じ符号のセル列]
const STYLES: Record<Style, [string[], string[]]> = {
  KAGI1:       [['001001'],           ['001001']],
  KAGI_FUTAE:  [['000011', '001001'], ['001001', '011000']],
  KAGI2:       [['000011', '001000'], ['000001', '011000']],
  KAKKO1:      [['011011'],           ['011011']],
  KAKKO_FUTAE: [['000011', '011011'], ['011011', '011000']],
  KAKKO2:      [['000010', '011011'], ['011011', '010000']],
};

// 文字 -> [系統, 既定の種別]
// 「」第1カギ（カギの中のカギ・『』はふたえカギ） 〈〉第2カギ / （）第1カッコ（カッコの中のカッコは二重カッコ） 〔〕［］第2カッコ
const OPENERS: Record<string, [Family, Style]> = {
  '「': ['KAGI', 'KAGI1'], '『': ['KAGI', 'KAGI_FUTAE'], '〈': ['KAGI', 'KAGI2'],
  '（': ['KAKKO', 'KAKKO1'], '(': ['KAKKO', 'KAKKO1'],
  '〔': ['KAKKO', 'KAKKO2'], '［': ['KAKKO', 'KAKKO2'], '[': ['KAKKO', 'KAKKO2'],
};
const CLOSERS_MAP: Record<string, [Family, Style]> = {
  '」': ['KAGI', 'KAGI1'], '』': ['KAGI', 'KAGI_FUTAE'], '〉': ['KAGI', 'KAGI2'],
  '）': ['KAKKO', 'KAKKO1'], ')': ['KAKKO', 'KAKKO1'],
  '〕': ['KAKKO', 'KAKKO2'], '］': ['KAKKO', 'KAKKO2'], ']': ['KAKKO', 'KAKKO2'],
};

// 波線 = つなぎ符×2（前後を空けない） / 矢印 = 「ーーた」（前後1マス）
const SYMBOLS: Record<string, string[]> = {
  '〜': [TSUNAGI, TSUNAGI], '～': [TSUNAGI, TSUNAGI],
  '→': ['010010', '010010', '101010'],
  '…': ['010000', '010000', '010000'],                    // 点線（点2 ×3）。「…」1字につき1つ
  '・': ['000010'], '･': ['000010'],                       // 中点（点5）。数字の区切りには書かない
};
// 棒線 = 点2,5 ×2セル（ーー）。「―」「—」「─」の連なり2字につき1つ。前後1マス
const DASHES = new Set([...'―—─']);
export const WAVE = new Set(['〜', '～']);

// 外字系の記号 = 外字符(点5,6) + 1セル: ％(点1,2,3,4) ＆(点1,2,3,4,6) ＃(点1,4,6) ＊(点1,6) ＠(点2,4,6)
//  - ％は数字の後ろに続ける。＃＊の直後に数字が続くときは続ける。＆＠は前後1マス。
//  - ％＃＊の後ろに助詞・助動詞が続くときは1マス、ひと続きの語（接尾語など）が続くときはつなぎ符。
const FOREIGN = '000011';
const FOREIGN_SYMBOL: Record<string, string> = { '％': '111100', '＆': '111101', '＃': '100101', '＊': '100001', '＠': '010101' };
const FULLWIDTH: Record<string, string> = { '%': '％', '&': '＆', '#': '＃', '*': '＊', '@': '＠' };
export const FOREIGN_SYMBOLS = new Set([...Object.keys(FOREIGN_SYMBOL), ...Object.keys(FULLWIDTH)]);

// 数字の伏せ字「×」: 1つにつき2セル（点5 / 点1〜6）。数符の有効範囲の中なので後ろの数字に数符は付けない。
export const MASK = '×';
const MASK_CELLS = ['000010', '111111'];
export const GAP_BEFORE_PARTICLE = new Set(['％', '%', '＃', '#', '＊', '*', MASK, '…']); // 後ろに助詞・助動詞が続くとき1マス
export const ATTACH_NUMBER = new Set(['＃', '#', '＊', '*']);                           // 直後に数字が続くとき空けない
export const LETTERLIKE_CHARS = new Set(['％', '＃', '＊', MASK]);                       // つなぎ符の判定で「アルファベット相当」
export const SPLIT_CHARS = new Set([...FOREIGN_SYMBOLS, MASK, '→', '〜', '～', '…', '・', '･', ...DASHES]);        // 複数文字トークンに混ざっていたら単独に切り出す

export const BRACKET_CHARS = [...Object.keys(OPENERS), ...Object.keys(CLOSERS_MAP)];
const cellsOf = (patterns: string[], ch: string) => patterns.map((p) => ({ dots: d(p), char: ch }));
const isNumber = (m: WordMapping) => m.cells.length > 0 && m.cells[0].dots.join('') === '001111';
const endsWithDigit = (m: WordMapping) => m.cells.length > 0 && /^[0-9]$/.test(m.cells[m.cells.length - 1].char);

/** 括弧トークンのセルを、入れ子の状態を見て決める（破壊的）。 */
export function resolveBrackets(mapped: WordMapping[]): void {
  const stack: [Family, Style][] = [];
  for (const m of mapped) {
    const ch = m.orig;
    if (ch in OPENERS) {
      const [family, base] = OPENERS[ch];
      let style: Style = base;
      if (family === 'KAGI' && style === 'KAGI1' && stack.some(([f, s]) => f === 'KAGI' && (s === 'KAGI1' || s === 'KAGI_FUTAE'))) {
        style = 'KAGI_FUTAE'; // カギの中のカギ
      } else if (family === 'KAKKO' && stack.some(([f]) => f === 'KAKKO')) {
        style = 'KAKKO_FUTAE'; // カッコの中のカッコ
      }
      stack.push([family, style]);
      m.cells = cellsOf(STYLES[style][0], ch);
    } else if (ch in CLOSERS_MAP) {
      const [family, base] = CLOSERS_MAP[ch];
      let style: Style = base;
      for (let i = stack.length - 1; i >= 0; i--) {
        if (stack[i][0] === family) { style = stack.splice(i, 1)[0][1]; break; }
      }
      m.cells = cellsOf(STYLES[style][1], ch);
    }
    m.braille = m.cells.map((c) => c.dots);
  }
}

export function resolveSymbols(mapped: WordMapping[]): void {
  for (const m of mapped) {
    const ch = m.orig;
    if (ch in SYMBOLS) {
      m.cells = cellsOf(SYMBOLS[ch], ch);
    } else if (FOREIGN_SYMBOLS.has(ch)) {
      const full = FULLWIDTH[ch] ?? ch;
      m.cells = [{ dots: d(FOREIGN), char: '外' }, { dots: d(FOREIGN_SYMBOL[full]), char: full }];
      m.attachPrev = full === '％'; // ％は数字の後ろに続ける（他は辞書の品詞に関わらず分かち書き）
    }
    m.braille = m.cells.map((c) => c.dots);
  }

  // 中点: 数字の区切りには書かない（後ろの数字の数符が区切りになる）
  for (let i = 1; i < mapped.length - 1; i++) {
    const m = mapped[i];
    if ((m.orig === '・' || m.orig === '･') && endsWithDigit(mapped[i - 1]) && isNumber(mapped[i + 1])) {
      m.cells = [];
      m.braille = [];
      mapped[i + 1].attachPrev = true;
    }
  }

  // 棒線: 連なった「―」2字につき1つ（2セル）
  const isDash = (m: WordMapping) => m.orig.length > 0 && [...m.orig].every((c) => DASHES.has(c));
  for (let i = 0; i < mapped.length; ) {
    if (isDash(mapped[i])) {
      let j = i;
      let count = 0;
      while (j < mapped.length && isDash(mapped[j])) { count += [...mapped[j].orig].length; j++; }
      mapped[i].cells = Array.from({ length: 2 * Math.floor((count + 1) / 2) }, () => ({ dots: d('010010'), char: 'ー' }));
      mapped[i].braille = mapped[i].cells.map((c) => c.dots);
      for (let k = i + 1; k < j; k++) { mapped[k].cells = []; mapped[k].braille = []; mapped[k].attachPrev = true; }
      i = j;
    } else {
      i++;
    }
  }

  // 数字の伏せ字: 数字の直後の「×」の連なり
  let i = 0;
  const n = mapped.length;
  while (i < n) {
    if (mapped[i].orig === MASK && i > 0 && endsWithDigit(mapped[i - 1])) {
      let j = i;
      while (j < n && mapped[j].orig === MASK) j++;
      const nxt = j < n ? mapped[j] : undefined;
      // 掛け算(3×4)との区別: 1つだけで後ろに数字が続く場合は伏せ字とみなさない
      if (j - i >= 2 || !nxt || !isNumber(nxt)) {
        for (let k = i; k < j; k++) {
          mapped[k].cells = cellsOf(MASK_CELLS, MASK);
          mapped[k].braille = mapped[k].cells.map((c) => c.dots);
          mapped[k].attachPrev = true;
        }
        if (nxt && isNumber(nxt)) {
          nxt.cells = nxt.cells.slice(1); // 数符の有効範囲内: 数符を付け直さない
          nxt.braille = nxt.cells.map((c) => c.dots);
          nxt.attachPrev = true;
        }
      }
      i = j;
    } else {
      i++;
    }
  }
}

/** 括弧・波線・矢印のセルを確定する（文脈が要るので、全体が揃ってから呼ぶ）。 */
export function resolveSpecial(mapped: WordMapping[]): void {
  resolveBrackets(mapped);
  resolveSymbols(mapped);
}
