import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { NativeModules, Platform } from 'react-native';
import { BrailleLanguage } from '../logic/brailleLogic';

function detectDefaultBrailleLanguage(): BrailleLanguage {
  try {
    // Intl API を先に試す（Hermes では iOS/Android 両方で動作）
    const locale = Intl.DateTimeFormat().resolvedOptions().locale;
    if (locale.startsWith('ja')) return 'ja';

    // iOS フォールバック: NativeModules.SettingsManager
    if (Platform.OS === 'ios') {
      const langs: string[] | undefined =
        NativeModules.SettingsManager?.settings?.AppleLanguages;
      const appleLocale: string | undefined =
        NativeModules.SettingsManager?.settings?.AppleLocale;
      const tag = langs?.[0] ?? appleLocale ?? '';
      if (tag.startsWith('ja')) return 'ja';
    }
  } catch {
    // fall through
  }
  return 'en';
}

const HISTORY_KEY = 'tenji_pfab_history_v1';
const CONFIG_KEY  = 'tenji_pfab_config_v1';

export interface HistoryEntry {
  text: string;
  timestamp: string;
  maxCharsPerLine: number;
  maxLinesPerPlate: number;
  plateThickness: number;
}

export interface AppSettings {
  maxCharsPerLine: number;
  maxLinesPerPlate: number;
  plateThickness: number;
  dotHeight: number;
  historyLimit: number;
  brailleLanguage: BrailleLanguage;
}

const DEFAULT_SETTINGS: AppSettings = {
  maxCharsPerLine: 10,
  maxLinesPerPlate: 3,
  plateThickness: 1.0,
  dotHeight: 0.4,
  historyLimit: 20,
  brailleLanguage: detectDefaultBrailleLanguage(),
};

// ---- AsyncStorage helpers ----

async function loadHistory(): Promise<HistoryEntry[]> {
  try {
    const raw = await AsyncStorage.getItem(HISTORY_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

async function saveHistory(history: HistoryEntry[]): Promise<void> {
  try {
    await AsyncStorage.setItem(HISTORY_KEY, JSON.stringify(history));
  } catch {
    // ストレージエラーは無視（メモリ上の状態は保持）
  }
}

async function loadSettings(): Promise<AppSettings> {
  try {
    const raw = await AsyncStorage.getItem(CONFIG_KEY);
    if (!raw) return { ...DEFAULT_SETTINGS };
    const parsed = JSON.parse(raw);
    if (typeof parsed !== 'object' || parsed === null) return { ...DEFAULT_SETTINGS };
    // brailleLanguage が保存されていない（機能追加前の設定）場合はロケールから検出
    if (!parsed.brailleLanguage) {
      parsed.brailleLanguage = detectDefaultBrailleLanguage();
    }
    // dotHeight が保存されていない（機能追加前の設定）場合はデフォルト値を使用
    if (parsed.dotHeight == null) {
      parsed.dotHeight = DEFAULT_SETTINGS.dotHeight;
    }
    return { ...DEFAULT_SETTINGS, ...parsed };
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
}

async function saveSettings(settings: AppSettings): Promise<void> {
  try {
    await AsyncStorage.setItem(CONFIG_KEY, JSON.stringify(settings));
  } catch {
    // ストレージエラーは無視
  }
}

// ---- Zustand store ----

interface HistoryStoreState {
  history: HistoryEntry[];
  settings: AppSettings;
  initialized: boolean;

  init: () => Promise<void>;
  addEntry: (text: string) => Promise<void>;
  clearHistory: () => Promise<void>;
  updateSettings: (patch: Partial<AppSettings>) => Promise<void>;
}

export const useHistoryStore = create<HistoryStoreState>((set, get) => ({
  history: [],
  settings: { ...DEFAULT_SETTINGS },
  initialized: false,

  init: async () => {
    if (get().initialized) return;
    const [history, settings] = await Promise.all([loadHistory(), loadSettings()]);
    set({ history, settings, initialized: true });
  },

  addEntry: async (text: string) => {
    const { history, settings } = get();
    const now = new Date();
    const timestamp =
      `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ` +
      `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

    const entry: HistoryEntry = {
      text,
      timestamp,
      maxCharsPerLine: settings.maxCharsPerLine,
      maxLinesPerPlate: settings.maxLinesPerPlate,
      plateThickness: settings.plateThickness,
    };

    // 重複排除: 先頭エントリが同テキスト＆同設定ならタイムスタンプだけ更新
    let updated = [...history];
    if (updated.length > 0) {
      const last = updated[0];
      if (
        last.text === text &&
        last.maxCharsPerLine === entry.maxCharsPerLine &&
        last.maxLinesPerPlate === entry.maxLinesPerPlate
      ) {
        updated[0] = { ...last, timestamp };
        await saveHistory(updated);
        set({ history: updated });
        return;
      }
    }

    updated.unshift(entry);
    if (updated.length > settings.historyLimit) {
      updated = updated.slice(0, settings.historyLimit);
    }

    await saveHistory(updated);
    set({ history: updated });
  },

  clearHistory: async () => {
    await saveHistory([]);
    set({ history: [] });
  },

  updateSettings: async (patch: Partial<AppSettings>) => {
    const merged = { ...get().settings, ...patch };
    await saveSettings(merged);
    set({ settings: merged });
  },
}));
