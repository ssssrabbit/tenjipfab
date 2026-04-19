import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  View, Text, TextInput, Pressable, ScrollView, SafeAreaView,
  StyleSheet, Alert, ActivityIndicator,
  Image, PanResponder, useWindowDimensions,
} from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import * as FileSystem from 'expo-file-system/legacy';
import * as Sharing from 'expo-sharing';
import Toast from 'react-native-toast-message';

import { AppColors } from '../constants/colors';
import {
  BrailleConverter, BrailleCell, WordMapping, BrailleLanguage,
  BRAILLE_MAP, SPACE_MARK, DAKUTEN_MARK, HANDAKUTEN_MARK,
  NUM_INDICATOR, FOREIGN_INDICATOR, YOON_MARK, YOON_DAKU_MARK, YOON_HANDAKU_MARK,
  HYPHEN_MARK,
} from '../logic/brailleLogic';
import { initializeKuromoji, getKuromojiProgress } from '../logic/japaneseProcessor';
import { generatePackageFromPlates } from '../logic/stlGenerator';
import { useHistoryStore, HistoryEntry } from '../stores/historyStore';
import BraillePlate, { FlatCellInfo } from '../components/BraillePlate';
import SettingsModal from '../components/SettingsModal';
import HistoryModal from '../components/HistoryModal';
import EditReadingModal from '../components/EditReadingModal';

const converter = new BrailleConverter();

// 接頭符セット（これらは次のセルと一組で改行させない）
const PREFIX_MARKS = new Set([
  JSON.stringify(DAKUTEN_MARK),
  JSON.stringify(HANDAKUTEN_MARK),
  JSON.stringify(YOON_MARK),
  JSON.stringify(YOON_DAKU_MARK),
  JSON.stringify(YOON_HANDAKU_MARK),
  JSON.stringify(NUM_INDICATOR),
  JSON.stringify(FOREIGN_INDICATOR),
]);

function splitCellsWithRules(allCells: FlatCellInfo[], maxChars: number, lang: BrailleLanguage = 'ja'): FlatCellInfo[][] {
  if (maxChars <= 0 || allCells.length === 0) return [];

  // 行をまたぐときの継続マーク：日本語=ー、英語=ハイフン
  const LONG_VOWEL_CELL: FlatCellInfo = lang === 'en'
    ? { dots: HYPHEN_MARK, char: '-', wordIdx: -1, orig: '(-)' }
    : { dots: BRAILLE_MAP['ー'], char: 'ー', wordIdx: -1, orig: '(ー)' };

  // --- Step 1: allCells を「トークン」に分割 ---
  // トークン種別: forced-newline / space / word(セル配列)
  type Token =
    | { kind: 'newline' }
    | { kind: 'space' }
    | { kind: 'word'; cells: FlatCellInfo[] };

  const tokens: Token[] = [];
  let wordBuf: FlatCellInfo[] = [];
  const flushWord = () => {
    if (wordBuf.length > 0) { tokens.push({ kind: 'word', cells: wordBuf }); wordBuf = []; }
  };
  for (const cell of allCells) {
    if (cell.isNewLine)       { flushWord(); tokens.push({ kind: 'newline' }); }
    else if (cell.wordIdx === -1) { flushWord(); tokens.push({ kind: 'space' }); }
    else                          { wordBuf.push(cell); }
  }
  flushWord();

  // --- Step 2: word 内を音節単位（接頭符+本字は不分割）にグループ化 ---
  const toSyllableUnits = (cells: FlatCellInfo[]): FlatCellInfo[][] => {
    const units: FlatCellInfo[][] = [];
    let i = 0;
    while (i < cells.length) {
      const isPrefix = PREFIX_MARKS.has(JSON.stringify(cells[i].dots));
      if (isPrefix && i + 1 < cells.length) { units.push([cells[i], cells[i + 1]]); i += 2; }
      else                                   { units.push([cells[i]]); i += 1; }
    }
    return units;
  };

  // --- Step 3: 行レイアウト ---
  const lines: FlatCellInfo[][] = [];
  let cur: FlatCellInfo[] = [];

  // 行末の空白を除去してコミット
  const commitLine = () => {
    while (cur.length > 0 && cur[cur.length - 1].wordIdx === -1) cur.pop();
    if (cur.length > 0) lines.push([...cur]);
    cur = [];
  };

  for (const token of tokens) {
    if (token.kind === 'newline') { commitLine(); continue; }

    if (token.kind === 'space') {
      // 行頭・満行のときは追加しない（末尾はコミット時に除去）
      if (cur.length > 0 && cur.length < maxChars) {
        cur.push({ dots: SPACE_MARK, char: ' ', wordIdx: -1, orig: '(Space)' });
      }
      continue;
    }

    // --- word トークン ---
    const units     = toSyllableUnits(token.cells);
    const wordSize  = units.reduce((s, u) => s + u.length, 0);

    if (wordSize <= maxChars) {
      // ── 規則1: 単語は1行に収まる → 収まらなければ次の行へ ──
      if (cur.length + wordSize <= maxChars) {
        cur.push(...units.flat());
      } else {
        commitLine();                 // 末尾スペースを除去して改行
        cur.push(...units.flat());
      }
    } else {
      // ── 規則2: 単語が1行を超える（3行以上またがりうる）→ ー で継続 ──
      // 行末の暫定スペースを先に除去
      while (cur.length > 0 && cur[cur.length - 1].wordIdx === -1) cur.pop();

      let remaining = [...units];
      while (remaining.length > 0) {
        const available = maxChars - cur.length;
        if (available <= 0) { commitLine(); continue; }

        // 貪欲に音節単位を詰める（最後の単位でなければ ー 用に1マス確保）
        let k = 0;
        while (k < remaining.length) {
          const uSize  = remaining[k].length;
          const isLast = k === remaining.length - 1;
          const need   = uSize + (isLast ? 0 : 1); // ー 分
          if (cur.length + need <= maxChars) { cur.push(...remaining[k]); k++; }
          else break;
        }

        if (k === 0) {
          // 現在行に1単位も入らない
          if (cur.length > 0) { commitLine(); continue; }
          // 空行でも入らない（maxChars が極端に小さい）→ 強制挿入
          cur.push(...remaining[0]);
          k = 1;
        }

        remaining = remaining.slice(k);
        if (remaining.length > 0) {
          // まだ続く → ー を追加して改行
          if (cur.length < maxChars) cur.push({ ...LONG_VOWEL_CELL });
          commitLine();
        }
      }
    }
  }

  // 残りをフラッシュ
  while (cur.length > 0 && cur[cur.length - 1].wordIdx === -1) cur.pop();
  if (cur.length > 0) lines.push(cur);

  return lines;
}

function buildFlatCells(mappedData: WordMapping[]): FlatCellInfo[] {
  const flat: FlatCellInfo[] = [];

  mappedData.forEach((item, wordIdx) => {
    // 改行マーカーはスキップ（セルなし・スペースなし）
    if (item.orig === '\n') return;

    // 段落先頭（2マスインデント）の前に強制改行マーカーを挿入（最初の段落を除く）
    if (item.isParagraphStart && flat.length > 0) {
      flat.push({ dots: SPACE_MARK, char: '\n', wordIdx: -1, orig: '(NewLine)', isNewLine: true });
    }

    for (const cell of item.cells) {
      flat.push({ ...cell, wordIdx, orig: item.orig });
    }

    // 次のアイテムが改行マーカー・インデント・末尾・助詞・助動詞の場合はスペースを挿入しない
    const next = mappedData[wordIdx + 1];
    const skipSpace =
      !next ||
      next.orig === '\n' ||
      next.isParagraphStart ||
      item.isParagraphStart ||
      next.pos === '助詞' ||
      next.pos === '助動詞';

    if (!skipSpace) {
      flat.push({ dots: SPACE_MARK, char: ' ', wordIdx: -1, orig: '(Space)' });
    }
  });

  return flat;
}

const INPUT_RATIO_MIN = 0.25;
const INPUT_RATIO_MAX = 0.75;
const INPUT_RATIO_DEFAULT = 0.35;

export default function HomeScreen() {
  const { history, settings, initialized, init, addEntry, clearHistory, updateSettings } =
    useHistoryStore();
  const { height: screenHeight } = useWindowDimensions();

  const [inputText, setInputText]           = useState('');
  const [mappedData, setMappedData]         = useState<WordMapping[]>([]);
  const [plates, setPlates]                 = useState<FlatCellInfo[][][]>([]);
  const [isSaving, setIsSaving]             = useState(false);
  const [loadProgress, setLoadProgress]     = useState<number>(() => getKuromojiProgress());

  // モーダル表示フラグ
  const [showSettings, setShowSettings]     = useState(false);
  const [showHistory, setShowHistory]       = useState(false);
  const [showEditReading, setShowEditReading] = useState(false);

  // 読み修正対象
  const [editingIndex, setEditingIndex]     = useState(-1);

  // 入力パネルの高さ比率（ドラッグで変更）
  const [inputRatio, setInputRatioState]    = useState(INPUT_RATIO_DEFAULT);
  const inputRatioRef   = useRef(INPUT_RATIO_DEFAULT);
  const dragStartRatioRef = useRef(INPUT_RATIO_DEFAULT);
  const screenHeightRef = useRef(screenHeight);
  useEffect(() => { screenHeightRef.current = screenHeight; }, [screenHeight]);

  const setInputRatio = useCallback((v: number) => {
    inputRatioRef.current = v;
    setInputRatioState(v);
  }, []);

  const panResponder = useRef(PanResponder.create({
    onStartShouldSetPanResponder: () => true,
    onMoveShouldSetPanResponder: () => true,
    onPanResponderGrant: () => {
      dragStartRatioRef.current = inputRatioRef.current;
    },
    onPanResponderMove: (_, gs) => {
      const newRatio = dragStartRatioRef.current - gs.dy / screenHeightRef.current;
      inputRatioRef.current = Math.max(INPUT_RATIO_MIN, Math.min(INPUT_RATIO_MAX, newRatio));
      setInputRatioState(inputRatioRef.current);
    },
  })).current;

  const mappedDataRef = useRef(mappedData);
  mappedDataRef.current = mappedData;

  const tokenizerReady = loadProgress >= 1;

  // kuromoji 準備完了時、日本語モードなら再変換
  useEffect(() => {
    if (tokenizerReady && inputText && settings.brailleLanguage === 'ja') {
      const data = converter.convertWithMapping(inputText, 'ja');
      setMappedData(data);
      renderPreview(data, settings.maxCharsPerLine, settings.maxLinesPerPlate, 'ja');
    }
  }, [tokenizerReady]); // eslint-disable-line react-hooks/exhaustive-deps

  // 言語設定変更時に再変換
  useEffect(() => {
    if (inputText) {
      const lang = settings.brailleLanguage;
      const data = converter.convertWithMapping(inputText, lang);
      setMappedData(data);
      renderPreview(data, settings.maxCharsPerLine, settings.maxLinesPerPlate, lang);
    }
  }, [settings.brailleLanguage]); // eslint-disable-line react-hooks/exhaustive-deps

  // 初期化
  useEffect(() => { init(); }, []);

  // kuromoji 初期化：150ms ポーリング + Promise完了で確実に反映
  useEffect(() => {
    if (getKuromojiProgress() >= 1) return; // 既に完了済み

    setLoadProgress(0.01); // バーをすぐに表示する

    initializeKuromoji()
      .then(() => setLoadProgress(1)) // Promise完了で確実に100%へ
      .catch((err) => console.warn('kuromoji init failed:', err));

    const id = setInterval(() => {
      const p = getKuromojiProgress();
      setLoadProgress(Math.max(p, 0.01));
      if (p >= 1) clearInterval(id);
    }, 150);

    return () => clearInterval(id);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // 点字プレビュー再計算
  const renderPreview = useCallback((data: WordMapping[], charsPerLine: number, linesPerPlate: number, lang: BrailleLanguage) => {
    const flat = buildFlatCells(data);
    const lines = splitCellsWithRules(flat, charsPerLine, lang);
    const newPlates: FlatCellInfo[][][] = [];
    for (let i = 0; i < lines.length; i += linesPerPlate) {
      newPlates.push(lines.slice(i, i + linesPerPlate));
    }
    setPlates(newPlates);
  }, []);

  const handleTextChange = useCallback((text: string) => {
    setInputText(text);
    if (!text) {
      setMappedData([]);
      setPlates([]);
      return;
    }
    const lang = settings.brailleLanguage;
    const data = converter.convertWithMapping(text, lang);
    setMappedData(data);
    renderPreview(data, settings.maxCharsPerLine, settings.maxLinesPerPlate, lang);
  }, [settings, renderPreview]);

  // 設定変更時にプレビュー再描画
  const handleSettingsUpdate = useCallback((patch: Partial<typeof settings>) => {
    updateSettings(patch);
    const next = { ...settings, ...patch };
    renderPreview(mappedDataRef.current, next.maxCharsPerLine, next.maxLinesPerPlate, next.brailleLanguage);
  }, [settings, updateSettings, renderPreview]);

  // 読み修正
  function openEditReading(wordIdx: number) {
    setEditingIndex(wordIdx);
    setShowEditReading(true);
  }

  function handleSaveReading(newReading: string) {
    if (editingIndex < 0) return;
    const updated = [...mappedDataRef.current];
    const item = updated[editingIndex];
    const newCells = converter.convertWithMapping(newReading, settings.brailleLanguage)
      .flatMap((w) => w.cells);
    updated[editingIndex] = {
      ...item,
      reading: newReading,
      cells: newCells,
      braille: newCells.map((c) => c.dots),
    };
    setMappedData(updated);
    renderPreview(updated, settings.maxCharsPerLine, settings.maxLinesPerPlate, settings.brailleLanguage);
    Toast.show({ type: 'success', text1: '読みを修正しました' });
  }

  // 履歴から復元
  function handleRestoreHistory(item: HistoryEntry) {
    handleSettingsUpdate({
      maxCharsPerLine: item.maxCharsPerLine,
      maxLinesPerPlate: item.maxLinesPerPlate,
      plateThickness: item.plateThickness,
    });
    setInputText(item.text);
    const lang = settings.brailleLanguage;
    const data = converter.convertWithMapping(item.text, lang);
    setMappedData(data);
    renderPreview(data, item.maxCharsPerLine, item.maxLinesPerPlate, lang);
    Toast.show({ type: 'success', text1: `履歴を復元しました: ${item.timestamp}` });
  }

  // ZIP 保存 & 共有
  async function handleSave() {
    if (mappedData.length === 0) {
      Toast.show({ type: 'error', text1: 'データがありません' });
      return;
    }
    setIsSaving(true);
    try {
      await addEntry(inputText);

      // プレートデータをBrailleCell[][]形式に変換
      const plateCells = plates.map((plateLine) =>
        plateLine.map((line) =>
          line.map((c): BrailleCell => ({ dots: c.dots, char: c.char }))
        )
      );

      const base64 = await generatePackageFromPlates(plateCells, {
        baseThickness: settings.plateThickness,
        dotHeight: settings.dotHeight,
        originalText: inputText,
      });

      const timestamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 15);
      const filename = `tenji_export_${timestamp}.zip`;
      const fileUri = (FileSystem.documentDirectory ?? '') + filename;

      await FileSystem.writeAsStringAsync(fileUri, base64, {
        encoding: FileSystem.EncodingType.Base64,
      });

      await Sharing.shareAsync(fileUri, {
        mimeType: 'application/zip',
        dialogTitle: 'ZIPファイルを保存',
      });

      Toast.show({ type: 'success', text1: '書き出し完了', text2: filename });
    } catch (err) {
      console.error(err);
      Toast.show({ type: 'error', text1: '保存に失敗しました', text2: String(err) });
    } finally {
      setIsSaving(false);
    }
  }

  const editingItem = editingIndex >= 0 && editingIndex < mappedData.length
    ? mappedData[editingIndex]
    : null;

  return (
    <SafeAreaView style={styles.root}>
      {/* ヘッダー */}
      <View style={styles.header}>
        <Image source={require('../../assets/logo.png')} style={styles.logoImage} resizeMode="contain" />
        <View style={styles.headerActions}>
          <Pressable onPress={() => setShowHistory(true)} style={styles.iconBtn}>
            <MaterialIcons name="history" size={24} color={AppColors.PRIMARY} />
          </Pressable>
          <Pressable onPress={() => setShowSettings(true)} style={styles.iconBtn}>
            <MaterialIcons name="settings" size={24} color={AppColors.PRIMARY} />
          </Pressable>
          <Pressable onPress={handleSave} style={styles.iconBtn} disabled={isSaving}>
            {isSaving
              ? <ActivityIndicator size="small" color={AppColors.PRIMARY} />
              : <MaterialIcons name="save-alt" size={24} color={AppColors.PRIMARY} />
            }
          </Pressable>
        </View>
      </View>

      {/* 点字プレビュー */}
      <ScrollView style={styles.previewArea} contentContainerStyle={styles.previewContent}>
        {plates.length === 0 ? (
          <Text style={styles.placeholder}>テキストを入力すると点字プレビューが表示されます</Text>
        ) : (
          plates.map((plateLines, i) => (
            <BraillePlate
              key={i}
              plateIndex={i}
              lines={plateLines}
              onCellPress={openEditReading}
            />
          ))
        )}
      </ScrollView>

      {/* 入力エリア */}
      <View style={[styles.inputPanel, { height: screenHeight * inputRatio }]}>
        {/* ドラッグハンドル */}
        <View {...panResponder.panHandlers} style={styles.dragHandleArea}>
          <View style={styles.dragHandle} />
        </View>
        <Text style={styles.inputLabel}>入力テキスト</Text>
        <View style={styles.inputCard}>
          {settings.brailleLanguage === 'ja' && loadProgress > 0 && loadProgress < 1 && (
            <View style={styles.progressWrapper}>
              <View style={styles.progressHeader}>
                <Text style={styles.progressLabel}>辞書を読み込み中...</Text>
                <Text style={styles.progressPercent}>{Math.round(loadProgress * 100)}%</Text>
              </View>
              <View style={styles.progressTrack}>
                <View style={[styles.progressFill, { width: `${loadProgress * 100}%` as any }]} />
              </View>
            </View>
          )}
          <TextInput
            style={styles.textInput}
            value={inputText}
            onChangeText={handleTextChange}
            placeholder={settings.brailleLanguage === 'en' ? 'Enter text here...' : 'ここに日本語を入力...'}
            placeholderTextColor={AppColors.TEXT_SUB}
            multiline
            textAlignVertical="top"
          />
          <Pressable
            style={({ pressed }) => [styles.saveBtn, pressed && styles.saveBtnPressed]}
            onPress={handleSave}
            disabled={isSaving}
          >
            {isSaving
              ? <ActivityIndicator color={AppColors.SURFACE} />
              : <>
                  <MaterialIcons name="save" size={18} color={AppColors.SURFACE} />
                  <Text style={styles.saveBtnText}>保存</Text>
                </>
            }
          </Pressable>
        </View>
      </View>

      {/* モーダル */}
      <SettingsModal
        visible={showSettings}
        settings={settings}
        onClose={() => setShowSettings(false)}
        onUpdate={handleSettingsUpdate}
      />
      <HistoryModal
        visible={showHistory}
        history={history}
        onClose={() => setShowHistory(false)}
        onRestore={handleRestoreHistory}
        onClear={clearHistory}
      />
      {editingItem && (
        <EditReadingModal
          visible={showEditReading}
          origWord={editingItem.orig}
          currentReading={editingItem.reading}
          onClose={() => setShowEditReading(false)}
          onSave={handleSaveReading}
        />
      )}

      <Toast />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: AppColors.BACKGROUND,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: AppColors.BACKGROUND,
  },
  logoImage: {
    height: 32,
    width: 140,
  },
  headerActions: {
    flexDirection: 'row',
  },
  iconBtn: {
    padding: 8,
  },
  previewArea: {
    flex: 1,
  },
  previewContent: {
    padding: 16,
    flexGrow: 1,
  },
  placeholder: {
    textAlign: 'center',
    color: AppColors.TEXT_SUB,
    marginTop: 40,
    fontSize: 14,
  },
  inputPanel: {
    borderTopLeftRadius: 30,
    borderTopRightRadius: 30,
    backgroundColor: AppColors.SURFACE,
    paddingHorizontal: 20,
    paddingBottom: 8,
    paddingTop: 0,
  },
  dragHandleArea: {
    alignItems: 'center',
    justifyContent: 'center',
    height: 28,
    width: '100%',
  },
  dragHandle: {
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: 'rgba(0,0,0,0.18)',
  },
  inputLabel: {
    fontSize: 12,
    color: AppColors.TEXT_SUB,
    marginBottom: 8,
  },
  inputCard: {
    flex: 1,
    backgroundColor: AppColors.SURFACE,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 10,
    elevation: 4,
    padding: 20,
  },
  progressWrapper: {
    marginBottom: 10,
  },
  progressHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  progressLabel: {
    fontSize: 11,
    color: AppColors.TEXT_SUB,
  },
  progressPercent: {
    fontSize: 11,
    color: AppColors.PRIMARY,
    fontWeight: '600',
  },
  progressTrack: {
    height: 4,
    borderRadius: 2,
    backgroundColor: 'rgba(0,0,0,0.08)',
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: 2,
    backgroundColor: AppColors.PRIMARY,
  },
  textInput: {
    flex: 1,
    fontSize: 16,
    color: AppColors.TEXT_MAIN,
  },
  saveBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    backgroundColor: AppColors.PRIMARY,
    borderRadius: 12,
    paddingVertical: 12,
    marginTop: 12,
  },
  saveBtnPressed: {
    opacity: 0.8,
  },
  saveBtnText: {
    color: AppColors.SURFACE,
    fontSize: 16,
    fontWeight: '500',
  },
});
