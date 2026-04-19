// 特殊符定義
export const DAKUTEN_MARK: number[]      = [0, 0, 0, 0, 1, 0]; // 5の点
export const HANDAKUTEN_MARK: number[]   = [0, 0, 0, 0, 0, 1]; // 6の点
export const YOON_MARK: number[]         = [0, 0, 0, 1, 0, 0]; // 4の点
export const YOON_DAKU_MARK: number[]    = [0, 0, 0, 1, 1, 0]; // 4,5の点
export const YOON_HANDAKU_MARK: number[] = [0, 0, 0, 1, 0, 1]; // 4,6の点
export const NUM_INDICATOR: number[]     = [0, 0, 1, 1, 1, 1]; // 数符
export const FOREIGN_INDICATOR: number[] = [0, 0, 0, 0, 1, 1]; // 外字符
export const SPACE_MARK: number[]        = [0, 0, 0, 0, 0, 0]; // スペース
export const CAPITAL_INDICATOR: number[] = [0, 0, 0, 0, 0, 1]; // dot 6 — 英語大文字符（= HANDAKUTEN_MARK と同パターン）
export const HYPHEN_MARK: number[]       = [0, 0, 1, 0, 0, 1]; // dots 3,6 — 英語ハイフン（行継続）

export const BRAILLE_MAP: Record<string, number[]> = {
  '1': [1,0,0,0,0,0], '2': [1,1,0,0,0,0], '3': [1,0,0,1,0,0], '4': [1,0,0,1,1,0], '5': [1,0,0,0,1,0],
  '6': [1,1,0,1,0,0], '7': [1,1,0,1,1,0], '8': [1,1,0,0,1,0], '9': [0,1,0,1,0,0], '0': [0,1,0,1,1,0],
  'a': [1,0,0,0,0,0], 'b': [1,1,0,0,0,0], 'c': [1,0,0,1,0,0], 'd': [1,0,0,1,1,0], 'e': [1,0,0,0,1,0],
  'f': [1,1,0,1,0,0], 'g': [1,1,0,1,1,0], 'h': [1,1,0,0,1,0], 'i': [0,1,0,1,0,0], 'j': [0,1,0,1,1,0],
  'k': [1,0,1,0,0,0], 'l': [1,1,1,0,0,0], 'm': [1,0,1,1,0,0], 'n': [1,0,1,1,1,0], 'o': [1,0,1,0,1,0],
  'p': [1,1,1,1,0,0], 'q': [1,1,1,1,1,0], 'r': [1,1,1,0,1,0], 's': [0,1,1,1,0,0], 't': [0,1,1,1,1,0],
  'u': [1,0,1,0,0,1], 'v': [1,1,1,0,0,1], 'w': [0,1,0,1,1,1], 'x': [1,0,1,1,0,1], 'y': [1,0,1,1,1,1], 'z': [1,0,1,0,1,1],
  'あ': [1,0,0,0,0,0], 'い': [1,1,0,0,0,0], 'う': [1,0,0,1,0,0], 'え': [1,1,0,1,0,0], 'お': [0,1,0,1,0,0],
  'か': [1,0,0,0,0,1], 'き': [1,1,0,0,0,1], 'く': [1,0,0,1,0,1], 'け': [1,1,0,1,0,1], 'こ': [0,1,0,1,0,1],
  'さ': [1,0,0,0,1,1], 'し': [1,1,0,0,1,1], 'す': [1,0,0,1,1,1], 'せ': [1,1,0,1,1,1], 'そ': [0,1,0,1,1,1],
  'た': [1,0,1,0,1,0], 'ち': [1,1,1,0,1,0], 'つ': [1,0,1,1,1,0], 'て': [1,1,1,1,1,0], 'と': [0,1,1,1,1,0],
  'な': [1,0,1,0,0,0], 'に': [1,1,1,0,0,0], 'ぬ': [1,0,1,1,0,0], 'ね': [1,1,1,1,0,0], 'の': [0,1,1,1,0,0],
  'は': [1,0,1,0,0,1], 'ひ': [1,1,1,0,0,1], 'ふ': [1,0,1,1,0,1], 'へ': [1,1,1,1,0,1], 'ほ': [0,1,1,1,0,1],
  'ま': [1,0,1,0,1,1], 'み': [1,1,1,0,1,1], 'む': [1,0,1,1,1,1], 'め': [1,1,1,1,1,1], 'も': [0,1,1,1,1,1],
  'や': [0,0,1,1,0,0], 'ゆ': [0,0,1,1,0,1], 'よ': [0,0,1,1,1,0],
  'ら': [1,0,0,0,1,0], 'り': [1,1,0,0,1,0], 'る': [1,0,0,1,1,0], 'れ': [1,1,0,1,1,0], 'ろ': [0,1,0,1,1,0],
  'わ': [0,0,1,0,0,0], 'を': [0,0,1,1,1,0], 'ん': [0,0,1,0,1,1],
  'っ': [0,1,0,0,0,0], 'ー': [0,1,0,0,1,0], '、': [0,0,0,0,1,0], '。': [0,1,0,0,1,1], ' ': [0,0,0,0,0,0],
};

type SpecialRule = 'DAKU' | 'HANDAKU' | 'YOON' | 'YOON_DAKU' | 'YOON_HANDAKU';

const SPECIAL_KANA_RULES: Record<string, [SpecialRule, string]> = {
  'が': ['DAKU', 'か'], 'ぎ': ['DAKU', 'き'], 'ぐ': ['DAKU', 'く'], 'げ': ['DAKU', 'け'], 'ご': ['DAKU', 'こ'],
  'ざ': ['DAKU', 'さ'], 'じ': ['DAKU', 'し'], 'ず': ['DAKU', 'す'], 'ぜ': ['DAKU', 'せ'], 'ぞ': ['DAKU', 'そ'],
  'だ': ['DAKU', 'た'], 'ぢ': ['DAKU', 'ち'], 'づ': ['DAKU', 'つ'], 'で': ['DAKU', 'て'], 'ど': ['DAKU', 'と'],
  'ば': ['DAKU', 'は'], 'び': ['DAKU', 'ひ'], 'ぶ': ['DAKU', 'ふ'], 'べ': ['DAKU', 'へ'], 'ぼ': ['DAKU', 'ほ'],
  'ぱ': ['HANDAKU', 'は'], 'ぴ': ['HANDAKU', 'ひ'], 'ぷ': ['HANDAKU', 'ふ'], 'ぺ': ['HANDAKU', 'へ'], 'ぽ': ['HANDAKU', 'ほ'],
  'きゃ': ['YOON', 'か'], 'きゅ': ['YOON', 'く'], 'きょ': ['YOON', 'こ'],
  'しゃ': ['YOON', 'さ'], 'しゅ': ['YOON', 'す'], 'しょ': ['YOON', 'そ'],
  'ちゃ': ['YOON', 'た'], 'ちゅ': ['YOON', 'つ'], 'ちょ': ['YOON', 'と'],
  'にゃ': ['YOON', 'な'], 'にゅ': ['YOON', 'ぬ'], 'にょ': ['YOON', 'の'],
  'ひゃ': ['YOON', 'は'], 'ひゅ': ['YOON', 'ふ'], 'ひょ': ['YOON', 'ほ'],
  'みゃ': ['YOON', 'ま'], 'みゅ': ['YOON', 'む'], 'みょ': ['YOON', 'も'],
  'りゃ': ['YOON', 'ら'], 'りゅ': ['YOON', 'る'], 'りょ': ['YOON', 'ろ'],
  'ぎゃ': ['YOON_DAKU', 'か'], 'ぎゅ': ['YOON_DAKU', 'く'], 'ぎょ': ['YOON_DAKU', 'こ'],
  'じゃ': ['YOON_DAKU', 'さ'], 'じゅ': ['YOON_DAKU', 'す'], 'じょ': ['YOON_DAKU', 'そ'],
  'ぢゃ': ['YOON_DAKU', 'た'], 'ぢゅ': ['YOON_DAKU', 'つ'], 'ぢょ': ['YOON_DAKU', 'と'],
  'びゃ': ['YOON_DAKU', 'は'], 'びゅ': ['YOON_DAKU', 'ふ'], 'びょ': ['YOON_DAKU', 'ほ'],
  'ぴゃ': ['YOON_HANDAKU', 'は'], 'ぴゅ': ['YOON_HANDAKU', 'ふ'], 'ぴょ': ['YOON_HANDAKU', 'ほ'],
};

export interface BrailleCell {
  dots: number[];
  char: string;
}

export interface WordMapping {
  orig: string;
  reading: string;
  braille: number[][];
  cells: BrailleCell[];
  start: number;
  end: number;
  isParagraphStart?: boolean; // 段落先頭（2マス空け対象）
  pos?: string; // kuromoji 品詞（助詞・助動詞の分かち書き判定に使用）
}

export function katakanaToHiragana(text: string): string {
  return text.replace(/[\u30A1-\u30F6]/g, (ch) =>
    String.fromCharCode(ch.charCodeAt(0) - 0x60)
  );
}

function addSpecialCells(cells: BrailleCell[], rule: SpecialRule, baseChar: string, displayChar: string): void {
  const markMap: Record<SpecialRule, [number[], string]> = {
    DAKU:         [DAKUTEN_MARK,      '゛'],
    HANDAKU:      [HANDAKUTEN_MARK,   '゜'],
    YOON:         [YOON_MARK,         '拗'],
    YOON_DAKU:    [YOON_DAKU_MARK,    '拗゛'],
    YOON_HANDAKU: [YOON_HANDAKU_MARK, '拗゜'],
  };
  const [mark, markChar] = markMap[rule];
  cells.push({ dots: mark, char: markChar });
  cells.push({ dots: BRAILLE_MAP[baseChar] ?? SPACE_MARK, char: baseChar });
}

export function kanaToCells(text: string): BrailleCell[] {
  const cells: BrailleCell[] = [];
  if (!text) return cells;

  if (text.trim() === '') {
    for (const _ of text) {
      cells.push({ dots: SPACE_MARK, char: ' ' });
    }
    return cells;
  }

  let mode: 'kana' | 'number' | 'foreign' = 'kana';
  let i = 0;
  while (i < text.length) {
    const char = text[i];
    const pair = text.slice(i, i + 2);

    if (pair.length === 2 && pair in SPECIAL_KANA_RULES) {
      const [rule, baseChar] = SPECIAL_KANA_RULES[pair];
      addSpecialCells(cells, rule, baseChar, pair);
      i += 2;
      continue;
    }

    if (char in SPECIAL_KANA_RULES) {
      const [rule, baseChar] = SPECIAL_KANA_RULES[char];
      addSpecialCells(cells, rule, baseChar, char);
      i += 1;
      continue;
    }

    if (/[0-9]/.test(char)) {
      if (mode !== 'number') {
        cells.push({ dots: NUM_INDICATOR, char: '#' });
        mode = 'number';
      }
      cells.push({ dots: BRAILLE_MAP[char] ?? SPACE_MARK, char });
    } else if (/[a-zA-Z]/.test(char)) {
      if (mode !== 'foreign') {
        cells.push({ dots: FOREIGN_INDICATOR, char: '外' });
        mode = 'foreign';
      }
      cells.push({ dots: BRAILLE_MAP[char.toLowerCase()] ?? SPACE_MARK, char });
    } else if (char in BRAILLE_MAP) {
      mode = 'kana';
      cells.push({ dots: BRAILLE_MAP[char], char });
    }
    // 未対応文字はスキップ

    i += 1;
  }
  return cells;
}

export function fallbackConvert(text: string): WordMapping[] {
  const result: WordMapping[] = [];
  let currentIndex = 0;
  for (const char of text) {
    const cells = kanaToCells(char);
    result.push({
      orig: char,
      reading: char,
      braille: cells.map((c) => c.dots),
      cells,
      start: currentIndex,
      end: currentIndex + 1,
    });
    currentIndex += 1;
  }
  return result;
}

export type BrailleLanguage = 'ja' | 'en';

export class BrailleConverter {
  convertWithMapping(text: string, lang: BrailleLanguage = 'ja'): WordMapping[] {
    if (!text) return [];
    if (lang === 'en') {
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      const { convertEnglish } = require('./englishProcessor') as typeof import('./englishProcessor');
      return convertEnglish(text);
    }
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { convertWithKuromoji } = require('./japaneseProcessor') as typeof import('./japaneseProcessor');
    return convertWithKuromoji(text);
  }
}
