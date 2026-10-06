import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { getLocales } from 'expo-localization';
import { NativeModules, Platform } from 'react-native';
import { BrailleLanguage } from '../logic/brailleLogic';

/**
 * デバイスのシステム言語を返す。UI テキストの切り替えに使う。
 * 点字の翻訳言語（settings.brailleLanguage）とは独立している。
 */
export function getUILocale(): 'en' | 'ja' {
  try {
    const lang = getLocales()?.[0]?.languageCode ?? '';
    if (lang.startsWith('en')) return 'en';
    if (lang.startsWith('ja')) return 'ja';
  } catch {}
  try {
    if (Platform.OS === 'ios') {
      const tag = NativeModules.SettingsManager?.settings?.AppleLanguages?.[0] ?? '';
      if (tag.startsWith('en')) return 'en';
      if (tag.startsWith('ja')) return 'ja';
    }
  } catch {}
  return 'ja';
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
  brailleLanguage: BrailleLanguage; // 点字の翻訳言語（UIとは独立）
}

const DEFAULT_SETTINGS: AppSettings = {
  maxCharsPerLine: 10,
  maxLinesPerPlate: 3,
  plateThickness: 1.0,
  dotHeight: 0.4,
  historyLimit: 20,
  brailleLanguage: 'ja',
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
  } catch {}
}

async function loadSettings(): Promise<AppSettings> {
  try {
    const raw = await AsyncStorage.getItem(CONFIG_KEY);
    // 初回インストール: デバイスロケールで点字言語を初期化
    if (!raw) {
      return { ...DEFAULT_SETTINGS, brailleLanguage: getUILocale() };
    }
    const parsed = JSON.parse(raw);
    if (typeof parsed !== 'object' || parsed === null) {
      return { ...DEFAULT_SETTINGS, brailleLanguage: getUILocale() };
    }
    // 保存済みの点字言語をそのまま使う（ユーザー設定を尊重）
    if (!parsed.brailleLanguage) {
      parsed.brailleLanguage = getUILocale();
    }
    if (parsed.dotHeight == null) {
      parsed.dotHeight = DEFAULT_SETTINGS.dotHeight;
    }
    return { ...DEFAULT_SETTINGS, ...parsed };
  } catch {
    return { ...DEFAULT_SETTINGS, brailleLanguage: getUILocale() };
  }
}

async function saveSettings(settings: AppSettings): Promise<void> {
  try {
    await AsyncStorage.setItem(CONFIG_KEY, JSON.stringify(settings));
  } catch {}
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
