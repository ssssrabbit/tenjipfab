import re

# 特殊符定義
DAKUTEN_MARK      = [0,0,0,0,1,0] # 5の点
HANDAKUTEN_MARK   = [0,0,0,0,0,1] # 6の点
YOON_MARK         = [0,0,0,1,0,0] # 4の点
YOON_DAKU_MARK    = [0,0,0,1,1,0] # 4,5の点
YOON_HANDAKU_MARK = [0,0,0,1,0,1] # 4,6の点
NUM_INDICATOR     = [0,0,1,1,1,1] # 数符
FOREIGN_INDICATOR = [0,0,0,0,1,1] # 外字符
SPACE_MARK        = [0,0,0,0,0,0] # スペース

# 基本点字マッピング
BRAILLE_MAP = {
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
}

SPECIAL_KANA_RULES = {
    'が': ('DAKU', 'か'), 'ぎ': ('DAKU', 'き'), 'ぐ': ('DAKU', 'く'), 'げ': ('DAKU', 'け'), 'ご': ('DAKU', 'こ'),
    'ざ': ('DAKU', 'さ'), 'じ': ('DAKU', 'し'), 'ず': ('DAKU', 'す'), 'ぜ': ('DAKU', 'せ'), 'ぞ': ('DAKU', 'そ'),
    'だ': ('DAKU', 'た'), 'ぢ': ('DAKU', 'ち'), 'づ': ('DAKU', 'つ'), 'で': ('DAKU', 'て'), 'ど': ('DAKU', 'と'),
    'ば': ('DAKU', 'は'), 'び': ('DAKU', 'ひ'), 'ぶ': ('DAKU', 'ふ'), 'べ': ('DAKU', 'へ'), 'ぼ': ('DAKU', 'ほ'),
    'ぱ': ('HANDAKU', 'は'), 'ぴ': ('HANDAKU', 'ひ'), 'ぷ': ('HANDAKU', 'ふ'), 'ぺ': ('HANDAKU', 'へ'), 'ぽ': ('HANDAKU', 'ほ'),
    'きゃ': ('YOON', 'か'), 'きゅ': ('YOON', 'く'), 'きょ': ('YOON', 'こ'),
    'しゃ': ('YOON', 'さ'), 'しゅ': ('YOON', 'す'), 'しょ': ('YOON', 'そ'),
    'ちゃ': ('YOON', 'た'), 'ちゅ': ('YOON', 'つ'), 'ちょ': ('YOON', 'と'),
    'にゃ': ('YOON', 'な'), 'にゅ': ('YOON', 'ぬ'), 'にょ': ('YOON', 'の'),
    'ひゃ': ('YOON', 'は'), 'ひゅ': ('YOON', 'ふ'), 'ひょ': ('YOON', 'ほ'),
    'みゃ': ('YOON', 'ま'), 'みゅ': ('YOON', 'む'), 'みょ': ('YOON', 'も'),
    'りゃ': ('YOON', 'ら'), 'りゅ': ('YOON', 'る'), 'りょ': ('YOON', 'ろ'),
    'ぎゃ': ('YOON_DAKU', 'か'), 'ぎゅ': ('YOON_DAKU', 'く'), 'ぎょ': ('YOON_DAKU', 'こ'),
    'じゃ': ('YOON_DAKU', 'さ'), 'じゅ': ('YOON_DAKU', 'す'), 'じょ': ('YOON_DAKU', 'そ'),
    'ぢゃ': ('YOON_DAKU', 'た'), 'ぢゅ': ('YOON_DAKU', 'つ'), 'ぢょ': ('YOON_DAKU', 'と'),
    'びゃ': ('YOON_DAKU', 'は'), 'びゅ': ('YOON_DAKU', 'ふ'), 'びょ': ('YOON_DAKU', 'ほ'),
    'ぴゃ': ('YOON_HANDAKU', 'は'), 'ぴゅ': ('YOON_HANDAKU', 'ふ'), 'ぴょ': ('YOON_HANDAKU', 'ほ'),
}

# 安全なインポート処理
try:
    from janome.tokenizer import Tokenizer
    JANOME_AVAILABLE = True
except ImportError:
    JANOME_AVAILABLE = False
    Tokenizer = None

class BrailleConverter:
    def __init__(self):
        self.use_kakasi = False # UI互換用変数
        self.tokenizer = None
        self.error_msg = ""
        
        if JANOME_AVAILABLE:
            try:
                self.tokenizer = Tokenizer()
                self.use_kakasi = True
            except Exception as e:
                self.error_msg = str(e)
                print(f"Janome Init Error: {e}")
        else:
            self.error_msg = "Module 'janome' not found"

    def convert_with_mapping(self, text):
        result_data = []
        current_index = 0
        if not text: return []

        if self.use_kakasi and self.tokenizer:
            try:
                # Janomeで形態素解析
                tokens = self.tokenizer.tokenize(text)
                for token in tokens:
                    orig_word = token.surface
                    # 読み(カタカナ)を取得
                    reading_kata = token.reading if token.reading != '*' else token.surface
                    # カタカナ -> ひらがな変換
                    reading = self._katakana_to_hiragana(reading_kata)
                    
                    word_len = len(orig_word)
                    start = current_index
                    end = current_index + word_len
                    current_index += word_len

                    cells = self.kana_to_cells(reading)
                    
                    dots_only = [c['dots'] for c in cells]

                    result_data.append({
                        'orig': orig_word,
                        'reading': reading,
                        'braille': dots_only,
                        'cells': cells,
                        'start': start,
                        'end': end
                    })
            except Exception as e:
                print(f"Tokenize Error: {e}")
                result_data = self._fallback_convert(text)
        else:
            result_data = self._fallback_convert(text)

        return result_data

    def _fallback_convert(self, text):
        """フォールバック（そのままひらがなとして処理）"""
        result_data = []
        current_index = 0
        for char in text:
            cells = self.kana_to_cells(char)
            result_data.append({
                'orig': char,
                'reading': char,
                'braille': [c['dots'] for c in cells],
                'cells': cells,
                'start': current_index,
                'end': current_index + 1
            })
            current_index += 1
        return result_data

    def _katakana_to_hiragana(self, text):
        """カタカナをひらがなに変換"""
        result = ""
        for char in text:
            code = ord(char)
            if 0x30A1 <= code <= 0x30F6:
                result += chr(code - 0x60)
            else:
                result += char
        return result

    def kana_to_cells(self, text):
        cells = []
        
        # 修正: 空文字またはスペースのみの場合は空のセルリストを返す
        if text is None or text == "":
            return cells
            
        # スペースのみの場合はスペースのセルを返す
        if text.strip() == "":
             # スペースの数だけ空白セルを追加
            for _ in text:
                cells.append({'dots': SPACE_MARK, 'char': ' '})
            return cells

        mode = "kana"
        i = 0
        while i < len(text):
            char = text[i]
            pair_char = text[i:i+2]
            
            if len(pair_char) == 2 and pair_char in SPECIAL_KANA_RULES:
                rule, base_char = SPECIAL_KANA_RULES[pair_char]
                self._add_special_cells(cells, rule, base_char, pair_char)
                i += 2
                continue

            if char in SPECIAL_KANA_RULES:
                rule, base_char = SPECIAL_KANA_RULES[char]
                self._add_special_cells(cells, rule, base_char, char)
                i += 1
                continue

            if char.isdigit():
                if mode != "number":
                    cells.append({'dots': NUM_INDICATOR, 'char': '#'})
                    mode = "number"
                cells.append({'dots': BRAILLE_MAP.get(char, SPACE_MARK), 'char': char})
            elif re.match(r'[a-zA-Z]', char):
                if mode != "foreign":
                    cells.append({'dots': FOREIGN_INDICATOR, 'char': '外'})
                    mode = "foreign"
                cells.append({'dots': BRAILLE_MAP.get(char.lower(), SPACE_MARK), 'char': char})
            elif char in BRAILLE_MAP:
                if mode != "kana": mode = "kana"
                # text.strip() == "" チェックで全体の空白は弾かれているが、
                # ここでは辞書にあるなら追加する方針。
                cells.append({'dots': BRAILLE_MAP[char], 'char': char})
            else:
                pass 
            i += 1
        return cells

    def _add_special_cells(self, cells, rule, base_char, display_char):
        mark = SPACE_MARK
        mark_char = ""
        
        if rule == 'DAKU': 
            mark = DAKUTEN_MARK
            mark_char = "゛"
        elif rule == 'HANDAKU': 
            mark = HANDAKUTEN_MARK
            mark_char = "゜"
        elif rule == 'YOON': 
            mark = YOON_MARK
            mark_char = "拗"
        elif rule == 'YOON_DAKU': 
            mark = YOON_DAKU_MARK
            mark_char = "拗゛"
        elif rule == 'YOON_HANDAKU': 
            mark = YOON_HANDAKU_MARK
            mark_char = "拗゜"
        
        cells.append({'dots': mark, 'char': mark_char})
        cells.append({'dots': BRAILLE_MAP.get(base_char, SPACE_MARK), 'char': base_char})