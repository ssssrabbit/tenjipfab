/**
 * Custom kuromoji loader for React Native (Expo).
 *
 * Bypasses kuromoji's built-in NodeDictionaryLoader (needs `fs`) and
 * BrowserDictionaryLoader (needs XHR + zlibjs, both broken in Hermes) by:
 *   1. Reading .dat.gz files via expo-file-system (returns base64)
 *   2. Decompressing with pako
 *   3. Feeding ArrayBuffers directly to kuromoji's internal DynamicDictionaries
 *   4. Building a Tokenizer from those dictionaries
 */

import * as FileSystem from 'expo-file-system/legacy';
import { inflate } from 'pako';

// Import kuromoji internals (pure JS, no Node.js deps)
// eslint-disable-next-line @typescript-eslint/no-require-imports
const DynamicDictionaries = require('kuromoji/src/dict/DynamicDictionaries');
// eslint-disable-next-line @typescript-eslint/no-require-imports
const Tokenizer = require('kuromoji/src/Tokenizer');
// eslint-disable-next-line @typescript-eslint/no-require-imports
const TokenInfoDictionary = require('kuromoji/src/dict/TokenInfoDictionary');
// eslint-disable-next-line @typescript-eslint/no-require-imports
const ByteBuffer = require('kuromoji/src/util/ByteBuffer');

/**
 * Hermes JS engine limits plain objects to 196607 properties.
 * kuromoji's TokenInfoDictionary.target_map is a {} with ~200k+ integer keys (IPAdic).
 * We patch loadTargetMap to use a Map-backed Proxy so bracket-notation access
 * (used by TokenInfoDictionary and ViterbiBuilder) still works transparently.
 */
function makeMapProxy(): Record<string | symbol, any> {
  const backing = new Map<string, any>();
  return new Proxy(Object.create(null) as Record<string | symbol, any>, {
    get(_: any, key: string | symbol): any {
      return backing.get(String(key));
    },
    set(_: any, key: string | symbol, value: any): boolean {
      backing.set(String(key), value);
      return true;
    },
    has(_: any, key: string | symbol): boolean {
      return backing.has(String(key));
    },
  });
}

TokenInfoDictionary.prototype.loadTargetMap = function (array_buffer: any) {
  const buffer = new ByteBuffer(array_buffer);
  buffer.position = 0;
  this.target_map = makeMapProxy();
  buffer.readInt(); // map_keys_size
  while (true) {
    if (buffer.buffer.length < buffer.position + 1) break;
    const key = buffer.readInt();
    const map_values_size = buffer.readInt();
    for (let i = 0; i < map_values_size; i++) {
      const value = buffer.readInt();
      this.addMapping(key, value);
    }
  }
  return this;
};

/** Convert a base64 string to Uint8Array */
function base64ToUint8Array(b64: string): Uint8Array {
  const binary = atob(b64);
  const len = binary.length;
  const buf = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    buf[i] = binary.charCodeAt(i);
  }
  return buf;
}

/** Read a .dat.gz file from the filesystem and decompress it */
async function readAndDecompress(filePath: string): Promise<ArrayBuffer> {
  const b64 = await FileSystem.readAsStringAsync(filePath, {
    encoding: FileSystem.EncodingType.Base64,
  });
  const compressed = base64ToUint8Array(b64);
  const decompressed = inflate(compressed);
  return decompressed.buffer as ArrayBuffer;
}

/**
 * Build a kuromoji Tokenizer using expo-file-system + pako.
 * @param dicDir  Directory containing the .dat.gz dictionary files (must end with '/')
 * @param onProgress  Called after each file is decompressed with (completedCount, totalCount)
 */
export async function buildTokenizerRN(
  dicDir: string,
  onProgress?: (completed: number, total: number) => void,
): Promise<any> {
  const p = (name: string) => dicDir + name;

  // 逐次処理: inflate はCPU同期処理のため、ファイルごとにawaitして
  // JSスレッドのブロックを分散させ、UI更新を可能にする
  const FILE_NAMES = [
    'base.dat.gz', 'check.dat.gz', 'tid.dat.gz', 'tid_pos.dat.gz',
    'tid_map.dat.gz', 'cc.dat.gz', 'unk.dat.gz', 'unk_pos.dat.gz',
    'unk_map.dat.gz', 'unk_char.dat.gz', 'unk_compat.dat.gz', 'unk_invoke.dat.gz',
  ];
  const buffers: ArrayBuffer[] = [];
  for (let i = 0; i < FILE_NAMES.length; i++) {
    buffers.push(await readAndDecompress(p(FILE_NAMES[i])));
    onProgress?.(i + 1, FILE_NAMES.length);
  }

  const [
    baseBuffer,
    checkBuffer,
    tidBuffer,
    tidPosBuffer,
    tidMapBuffer,
    ccBuffer,
    unkBuffer,
    unkPosBuffer,
    unkMapBuffer,
    unkCharBuffer,
    unkCompatBuffer,
    unkInvokeBuffer,
  ] = buffers;

  const dic = new DynamicDictionaries();
  dic.loadTrie(new Int32Array(baseBuffer), new Int32Array(checkBuffer));
  dic.loadTokenInfoDictionaries(
    new Uint8Array(tidBuffer),
    new Uint8Array(tidPosBuffer),
    new Uint8Array(tidMapBuffer),
  );
  dic.loadConnectionCosts(new Int16Array(ccBuffer));
  dic.loadUnknownDictionaries(
    new Uint8Array(unkBuffer),
    new Uint8Array(unkPosBuffer),
    new Uint8Array(unkMapBuffer),
    new Uint8Array(unkCharBuffer),
    new Uint32Array(unkCompatBuffer),
    new Uint8Array(unkInvokeBuffer),
  );

  return new Tokenizer(dic);
}
