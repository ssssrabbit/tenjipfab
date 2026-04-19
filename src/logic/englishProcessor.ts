import {
  WordMapping, BrailleCell,
  SPACE_MARK, CAPITAL_INDICATOR, BRAILLE_MAP, NUM_INDICATOR,
} from './brailleLogic';

// UEB (Unified English Braille) Grade 1 punctuation
const EN_PUNCT_MAP: Record<string, number[]> = {
  ',': [0, 1, 0, 0, 0, 0],   // dot 2
  ';': [0, 1, 1, 0, 0, 0],   // dots 2,3
  ':': [0, 1, 0, 0, 1, 0],   // dots 2,5
  '.': [0, 1, 0, 0, 1, 1],   // dots 2,5,6
  '!': [0, 1, 1, 1, 0, 1],   // dots 2,3,4,6
  '?': [0, 1, 1, 0, 0, 1],   // dots 2,3,6
  "'": [0, 0, 1, 0, 0, 0],   // dot 3
  '-': [0, 0, 1, 0, 0, 1],   // dots 3,6
};

export function englishToCells(text: string): BrailleCell[] {
  const cells: BrailleCell[] = [];
  if (!text) return cells;

  let numMode = false;

  for (const char of text) {
    if (/[0-9]/.test(char)) {
      if (!numMode) {
        cells.push({ dots: NUM_INDICATOR, char: '#' });
        numMode = true;
      }
      cells.push({ dots: BRAILLE_MAP[char] ?? SPACE_MARK, char });
    } else {
      numMode = false;
      const lower = char.toLowerCase();
      if (/[a-z]/.test(lower)) {
        if (char !== lower) {
          cells.push({ dots: CAPITAL_INDICATOR, char: '⇧' });
        }
        cells.push({ dots: BRAILLE_MAP[lower] ?? SPACE_MARK, char: lower });
      } else if (char in EN_PUNCT_MAP) {
        cells.push({ dots: EN_PUNCT_MAP[char], char });
      }
      // spaces and unknown chars are skipped; spacing is handled by buildFlatCells
    }
  }

  return cells;
}

/** 2マスインデント用の WordMapping を生成 */
function makeIndentMapping(startIndex: number): WordMapping {
  return {
    orig: '',
    reading: '',
    braille: [SPACE_MARK, SPACE_MARK],
    cells: [{ dots: SPACE_MARK, char: ' ' }, { dots: SPACE_MARK, char: ' ' }],
    start: startIndex,
    end: startIndex,
    isParagraphStart: true,
  };
}

/**
 * 英語テキストを単語単位の WordMapping[] に変換する。
 * - スペース区切りで単語を分割
 * - 複数段落（改行あり）の場合、各段落先頭に2マスインデントを挿入
 */
export function convertEnglish(text: string): WordMapping[] {
  if (!text) return [];

  const lines = text.split('\n');
  const isMultiParagraph = lines.length > 1;
  const result: WordMapping[] = [];
  let charIndex = 0;

  lines.forEach((line, lineIdx) => {
    if (isMultiParagraph) {
      result.push(makeIndentMapping(charIndex));
    }

    const wordRegex = /\S+/g;
    let match: RegExpExecArray | null;
    while ((match = wordRegex.exec(line)) !== null) {
      const word = match[0];
      const cells = englishToCells(word);
      result.push({
        orig: word,
        reading: word,
        braille: cells.map((c) => c.dots),
        cells,
        start: charIndex + match.index,
        end: charIndex + match.index + word.length,
      });
    }

    charIndex += line.length + 1; // +1 for '\n'

    if (isMultiParagraph && lineIdx < lines.length - 1) {
      result.push({
        orig: '\n',
        reading: '',
        braille: [],
        cells: [],
        start: charIndex - 1,
        end: charIndex,
      });
    }
  });

  return result;
}
