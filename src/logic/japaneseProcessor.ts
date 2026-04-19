import { Asset } from 'expo-asset';
import * as FileSystem from 'expo-file-system/legacy';

import { buildTokenizerRN } from './kuromojiLoader';
import { kanaToCells, katakanaToHiragana, fallbackConvert, SPACE_MARK, WordMapping } from './brailleLogic';

// documentDirectory は file:// URI → kuromoji の XHR ローダーでそのまま使える
const DICT_DIR = (FileSystem.documentDirectory ?? '') + 'kuromoji-dict/';

const DICT_ASSETS: Array<{ module: number; name: string }> = [
  { module: require('../../assets/dict/base.dat.gz'),       name: 'base.dat.gz' },
  { module: require('../../assets/dict/cc.dat.gz'),         name: 'cc.dat.gz' },
  { module: require('../../assets/dict/check.dat.gz'),      name: 'check.dat.gz' },
  { module: require('../../assets/dict/tid_map.dat.gz'),    name: 'tid_map.dat.gz' },
  { module: require('../../assets/dict/tid_pos.dat.gz'),    name: 'tid_pos.dat.gz' },
  { module: require('../../assets/dict/tid.dat.gz'),        name: 'tid.dat.gz' },
  { module: require('../../assets/dict/unk_char.dat.gz'),   name: 'unk_char.dat.gz' },
  { module: require('../../assets/dict/unk_compat.dat.gz'), name: 'unk_compat.dat.gz' },
  { module: require('../../assets/dict/unk_invoke.dat.gz'), name: 'unk_invoke.dat.gz' },
  { module: require('../../assets/dict/unk_map.dat.gz'),    name: 'unk_map.dat.gz' },
  { module: require('../../assets/dict/unk_pos.dat.gz'),    name: 'unk_pos.dat.gz' },
  { module: require('../../assets/dict/unk.dat.gz'),        name: 'unk.dat.gz' },
];

let _tokenizer: any = null;
let _initPromise: Promise<void> | null = null;

// 進捗: 0.0〜1.0。ファイルコピー 0〜0.3、解凍・ロード 0.3〜1.0
const COPY_WEIGHT  = 0.3;
const BUILD_WEIGHT = 0.7;

type ProgressCallback = (progress: number) => void;
const _progressListeners = new Set<ProgressCallback>();
let _currentProgress = 0;

function reportProgress(p: number) {
  _currentProgress = p;
  _progressListeners.forEach((fn) => fn(p));
}

/** 現在の初期化進捗（0.0〜1.0）を取得する */
export function getKuromojiProgress(): number {
  return _currentProgress;
}

/**
 * 進捗コールバックを登録する。
 * 返値の関数を呼ぶと登録解除される。
 */
export function onKuromojiProgress(fn: ProgressCallback): () => void {
  _progressListeners.add(fn);
  return () => _progressListeners.delete(fn);
}

async function copyDictFiles(onFileCopied?: (done: number, total: number) => void): Promise<void> {
  const dirInfo = await FileSystem.getInfoAsync(DICT_DIR);
  if (!dirInfo.exists) {
    await FileSystem.makeDirectoryAsync(DICT_DIR, { intermediates: true });
  }

  const total = DICT_ASSETS.length;
  for (let i = 0; i < total; i++) {
    const { module, name } = DICT_ASSETS[i];
    const destPath = DICT_DIR + name;
    const destInfo = await FileSystem.getInfoAsync(destPath);
    if (!destInfo.exists) {
      const asset = Asset.fromModule(module);
      await asset.downloadAsync();
      if (asset.localUri) {
        await FileSystem.copyAsync({ from: asset.localUri, to: destPath });
      }
    }
    onFileCopied?.(i + 1, total);
  }
}

/**
 * kuromoji を初期化する。2回目以降は同じ Promise を返す。
 * App 起動時に呼び出すこと。
 */
export function initializeKuromoji(): Promise<void> {
  if (_initPromise) return _initPromise;

  reportProgress(0);

  _initPromise = copyDictFiles((done, total) => {
    reportProgress((done / total) * COPY_WEIGHT);
  }).then(async () => {
    try {
      reportProgress(COPY_WEIGHT);
      _tokenizer = await buildTokenizerRN(DICT_DIR, (done, total) => {
        reportProgress(COPY_WEIGHT + (done / total) * BUILD_WEIGHT);
      });
      reportProgress(1);
    } catch (err) {
      _initPromise = null; // 失敗時は再試行可能にリセット
      throw err;
    }
  });

  return _initPromise;
}

export function isKuromojiReady(): boolean {
  return _tokenizer !== null;
}

// ─── 点字規則 ───────────────────────────────────────────────

/**
 * 助詞「は」→「わ」、「へ」→「え」に読みを補正する。
 * kuromoji の品詞情報（pos: '助詞'）を使って判定する。
 */
function applyParticleRule(
  surface: string,
  pos: string,
  reading: string
): string {
  if (pos !== '助詞') return reading;
  if (surface === 'は') return 'わ';
  if (surface === 'へ') return 'え';
  return reading;
}

/**
 * お段・ウ段の後の「う」を長音符「ー」に変換する。
 * 例: とうきょう → とーきょー、くうき → くーき
 *
 * 対象: お段（お・こ…ぽ・ぉ・ょ）とウ段（う・く…ぷ）の後の「う」
 * 非対象: あ段・い段・え段の後の「う」（例: いう、あう）
 */
const LONG_VOWEL_RE =
  /([おこそとのほもよろをごぞどぼぽぉょうくすつぬふむゆるぐずづぶぷ])う/g;

function applyLongVowelRule(reading: string): string {
  // 繰り返し適用（連続した長音に対応）
  let prev = '';
  let result = reading;
  while (prev !== result) {
    prev = result;
    result = result.replace(LONG_VOWEL_RE, '$1ー');
  }
  return result;
}

// ─── トークナイズ ─────────────────────────────────────────────

/** 2マスインデント用の WordMapping を生成 */
function makeIndentMapping(startIndex: number): WordMapping {
  const spaces = [
    { dots: SPACE_MARK, char: ' ' },
    { dots: SPACE_MARK, char: ' ' },
  ];
  return {
    orig: '',
    reading: '',
    braille: [SPACE_MARK, SPACE_MARK],
    cells: spaces,
    start: startIndex,
    end: startIndex,
    isParagraphStart: true,
  };
}

/** 単一段落のテキストをトークナイズして WordMapping[] を返す */
function tokenizeParagraph(
  text: string,
  startIndex: number
): WordMapping[] {
  if (!_tokenizer || !text) return [];

  const tokens = _tokenizer.tokenize(text);
  const result: WordMapping[] = [];
  let currentIndex = startIndex;

  for (const token of tokens) {
    const orig = token.surface_form;

    // 読みを取得（'*' はフォールバック）
    const readingKata =
      token.reading && token.reading !== '*' ? token.reading : token.surface_form;
    let reading = katakanaToHiragana(readingKata);

    // 点字規則1: 助詞「は」→「わ」、「へ」→「え」
    reading = applyParticleRule(orig, token.pos, reading);

    // 点字規則2: 長音変換（お段・ウ段+う → ー）
    reading = applyLongVowelRule(reading);

    const start = currentIndex;
    const end = currentIndex + orig.length;
    currentIndex += orig.length;

    const cells = kanaToCells(reading);
    result.push({
      orig,
      reading,
      braille: cells.map((c) => c.dots),
      cells,
      start,
      end,
      pos: token.pos,
    });
  }

  return result;
}

/**
 * テキストを形態素解析し WordMapping[] を返す。
 * - kuromoji 未初期化時は fallbackConvert にフォールバック
 * - 複数段落（改行あり）の場合、各段落先頭に2マスインデントを挿入
 */
export function convertWithKuromoji(text: string): WordMapping[] {
  if (!text) return [];

  if (!_tokenizer) {
    return fallbackConvert(text);
  }

  const lines = text.split('\n');
  const isMultiParagraph = lines.length > 1;
  const result: WordMapping[] = [];
  let charIndex = 0;

  lines.forEach((line, lineIdx) => {
    const trimmed = line; // 改行は保持するがトリムはしない

    if (isMultiParagraph) {
      // 各段落の先頭に2マスインデント
      result.push(makeIndentMapping(charIndex));
    }

    if (trimmed.length > 0) {
      result.push(...tokenizeParagraph(trimmed, charIndex));
    }

    charIndex += line.length + 1; // +1 for '\n'

    // 最後の行以外は改行セパレータを追加（buildFlatCells がスペースを挿入しないよう空マッピング）
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
