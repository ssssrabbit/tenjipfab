import logging
import sys
import os
import traceback
from datetime import datetime

# --- ログ監視用の設定 (Memory Handler) ---
class ListLogHandler(logging.Handler):
    """ログをメモリ上に保持してUIで表示可能にするハンドラ"""
    def __init__(self):
        super().__init__()
        self.log_records = []

    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_records.append(msg)
            # ログが多すぎたら古いのを消す
            if len(self.log_records) > 500:
                self.log_records.pop(0)
        except Exception:
            self.handleError(record)

# ルートロガーの設定
list_handler = ListLogHandler()
list_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(list_handler)
logging.getLogger().setLevel(logging.INFO)

logging.info("--- App Logic Initializing ---")
logging.info(f"Python Version: {sys.version}")

import flet as ft

# Fletバージョン記録
try:
    logging.info(f"Flet Version: {ft.version}")
except:
    pass

# グローバル変数としてモジュールを保持
modules = {}

def load_modules():
    """モジュールをインポートし、失敗したらエラーを投げる"""
    global modules
    try:
        import styles
        import braille_logic
        import stl_generator
        import history_manager
        
        modules['styles'] = styles
        modules['braille_logic'] = braille_logic
        modules['stl_generator'] = stl_generator
        modules['history_manager'] = history_manager
        logging.info("Modules loaded successfully.")
    except ImportError as e:
        logging.error(f"Module load failed: {e}")
        raise ImportError(f"Failed to load modules: {e}")

def main(page: ft.Page):
    print("--- Main Function Called ---") # コンソール強制出力
    logging.info("--- Main Function Called ---")
    logging.info(f"Platform: {page.platform}")

    # --- 緊急時用エラー表示関数 ---
    def show_boot_error(err_msg):
        logging.critical(f"Boot Error: {err_msg}")
        page.clean()
        page.bgcolor = "#FF3B30"
        page.add(
            ft.Column([
                ft.Text("Startup Error", size=24, weight="bold", color="white"),
                ft.Container(height=20),
                ft.Text(err_msg, color="white", selectable=True),
                ft.ElevatedButton("Copy Logs", on_click=lambda e: page.set_clipboard("\n".join(list_handler.log_records))),
                ft.ElevatedButton("Reload", on_click=lambda e: page.window.reload())
            ], alignment="center", horizontal_alignment="center", scroll=ft.ScrollMode.ADAPTIVE)
        )
        page.update()

    # --- モジュール読み込み試行 ---
    try:
        load_modules()
    except Exception as e:
        traceback.print_exc()
        show_boot_error(f"Module Load Error:\n{str(e)}\n\n{traceback.format_exc()}")
        return

    # モジュール展開
    AppColors = modules['styles'].AppColors
    TextStyles = modules['styles'].TextStyles
    ComponentStyles = modules['styles'].ComponentStyles
    BrailleConverter = modules['braille_logic'].BrailleConverter
    SPACE_MARK = modules['braille_logic'].SPACE_MARK
    DAKUTEN_MARK = modules['braille_logic'].DAKUTEN_MARK
    HANDAKUTEN_MARK = modules['braille_logic'].HANDAKUTEN_MARK
    NUM_INDICATOR = modules['braille_logic'].NUM_INDICATOR
    FOREIGN_INDICATOR = modules['braille_logic'].FOREIGN_INDICATOR
    YOON_MARK = modules['braille_logic'].YOON_MARK
    YOON_DAKU_MARK = modules['braille_logic'].YOON_DAKU_MARK
    YOON_HANDAKU_MARK = modules['braille_logic'].YOON_HANDAKU_MARK
    STLGenerator = modules['stl_generator'].STLGenerator
    HistoryManager = modules['history_manager'].HistoryManager

    # --- アプリ設定 ---
    page.title = "Tenji P-Fab"
    page.bgcolor = AppColors.BACKGROUND
    page.theme_mode = ft.ThemeMode.LIGHT
    
    # ウィンドウサイズ設定（PC用、プロパティが存在しない場合は無視）
    try:
        page.window.width = 390
        page.window.height = 844
    except:
        pass 
    page.padding = 0

    # --- ロジック初期化 ---
    try:
        converter = BrailleConverter()
        stl_generator = STLGenerator()
        history_manager = HistoryManager(page)
    except Exception as e:
        msg = f"Logic Init Error:\n{str(e)}\n{traceback.format_exc()}"
        logging.error(msg)
        show_boot_error(msg)
        return

    # 状態管理
    state = {
        "current_mapped_data": [],
        "editing_index": -1
    }
    
    settings = {
        "max_chars_per_line": 10,
        "max_lines_per_plate": 4,
        "plate_thickness": 0.6, 
        "use_quick_save": False
    }

    # UI参照用Ref
    txt_input_ref = ft.Ref[ft.TextField]()
    edit_field_ref = ft.Ref[ft.TextField]()
    chars_slider_ref = ft.Ref[ft.Slider]()
    lines_slider_ref = ft.Ref[ft.Slider]()

    thickness_slider_ref = ft.Ref[ft.Slider]()
    thickness_label_ref = ft.Ref[ft.Text]()
    chars_label_ref = ft.Ref[ft.Text]()
    lines_label_ref = ft.Ref[ft.Text]()

    # --- ヘルパー関数 ---

    def show_snackbar(message, is_error=False):
        """SnackBarをOverlayを使って表示"""
        try:
            # 既存のSnackBarがあれば削除
            for control in page.overlay[:]:
                if isinstance(control, ft.SnackBar):
                    page.overlay.remove(control)
            
            snack = ft.SnackBar(
                content=ft.Text(message),
                bgcolor=AppColors.ERROR if is_error else None,
            )
            page.overlay.append(snack)
            snack.open = True
            page.update()
        except Exception as e:
            logging.error(f"SnackBar Error: {e}")

    def open_dialog(dlg):
        try:
            if dlg not in page.overlay:
                page.overlay.append(dlg)
            dlg.open = True
            page.update()
        except Exception as e:
            logging.error(f"Open Dialog Error: {e}")

    def close_dialog(dlg):
        try:
            dlg.open = False
            page.update()
        except Exception as e:
            logging.error(f"Close Dialog Error: {e}")

    # --- 設定同期用関数 ---
    def sync_settings_ui():
        """現在のsettings辞書の値をUI（スライダー等）に反映させる"""
        try:
            if chars_slider_ref.current:
                val = int(settings["max_chars_per_line"])
                chars_slider_ref.current.value = val
                chars_slider_ref.current.label = f"{val}"
                if chars_label_ref.current: chars_label_ref.current.value = f"{val}文字"
            
            if lines_slider_ref.current:
                val = int(settings["max_lines_per_line"] if "max_lines_per_line" in settings else settings.get("max_lines_per_plate", 3))
                lines_slider_ref.current.value = val
                lines_slider_ref.current.label = f"{val}"
                if lines_label_ref.current: lines_label_ref.current.value = f"{val}行"

            if thickness_slider_ref.current:
                val = float(settings["plate_thickness"])
                thickness_slider_ref.current.value = val
                thickness_slider_ref.current.label = f"{val:.1f}mm"
                if thickness_label_ref.current: thickness_label_ref.current.value = f"{val:.1f}mm"
            
            page.update()
        except Exception as e:
            logging.warning(f"Sync UI Warning: {e}")

    # --- ログ表示機能 ---
    def show_debug_logs(e):
        log_content = "\n".join(list_handler.log_records)
        log_view = ft.AlertDialog(
            title=ft.Text("Debug Logs"),
            content=ft.Column([
                ft.Container(
                    content=ft.Text(log_content, size=10, font_family="monospace", selectable=True),
                    bgcolor=ft.Colors.BLACK87,
                    padding=10,
                    border_radius=5,
                    width=300,
                    height=300,
                )
            ], tight=True, scroll=ft.ScrollMode.AUTO),
            actions=[
                ft.TextButton("Copy", on_click=lambda e: page.set_clipboard(log_content)),
                ft.TextButton("Close", on_click=lambda e: close_dialog(log_view))
            ]
        )
        open_dialog(log_view)

    # --- 設定ロード ---
    try:
        saved_config = history_manager.load_settings()
        if saved_config:
            settings.update({k: v for k, v in saved_config.items() if k in settings})
        
        if sys.platform == "darwin": 
            settings["use_quick_save"] = True
    except Exception as e:
        logging.warning(f"Config Load Warning: {e}")

    # --- UI Components ---
    
    braille_display_area = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=10)

    def _make_dot(is_active):
        return ft.Container(
            width=8, height=8,
            bgcolor=AppColors.DOT_ACTIVE if is_active else AppColors.DOT_INACTIVE,
            border_radius=ft.BorderRadius(4, 4, 4, 4),
        )

    # --- ロジック群 ---
    def split_cells_with_rules(all_cells, max_chars):
        lines = []
        current_line = []
        units = []
        i = 0
        prefix_marks_vals = {
            tuple(DAKUTEN_MARK), tuple(HANDAKUTEN_MARK), tuple(YOON_MARK),
            tuple(YOON_DAKU_MARK), tuple(YOON_HANDAKU_MARK), tuple(NUM_INDICATOR), tuple(FOREIGN_INDICATOR)
        }
        
        while i < len(all_cells):
            cell = all_cells[i]
            cell_dots_tuple = tuple(cell['dots'])
            is_prefix = (cell_dots_tuple in prefix_marks_vals)
            
            if is_prefix and i + 1 < len(all_cells):
                units.append([cell, all_cells[i+1]])
                i += 2
            else:
                units.append([cell])
                i += 1
                
        for unit in units:
            unit_len = len(unit)
            if len(current_line) + unit_len > max_chars:
                if len(current_line) > 0:
                    lines.append(current_line)
                    current_line = []
            current_line.extend(unit)
        if current_line:
            lines.append(current_line)
        return lines

    def save_reading_edit(e):
        try:
            if state["editing_index"] < 0: return
            new_reading = edit_field_ref.current.value
            
            # 【修正点1】空文字も許容するように条件を変更（if new_reading: を削除）
            # 空文字の場合、kana_to_cells は空リストを返すので点字も消えます
            state["current_mapped_data"][state["editing_index"]]['reading'] = new_reading
            new_cells = converter.kana_to_cells(new_reading)
            state["current_mapped_data"][state["editing_index"]]['cells'] = new_cells
            state["current_mapped_data"][state["editing_index"]]['braille'] = [c['dots'] for c in new_cells]
            
            render_braille_preview()
            
            msg = "読みを修正しました" if new_reading else "読みを消去しました"
            show_snackbar(msg)
            close_dialog(edit_dialog)
            
        except Exception as ex:
            logging.error(f"Save reading error: {ex}")
            show_snackbar("エラーが発生しました", is_error=True)

    # 編集ダイアログ定義
    edit_dialog = ft.AlertDialog(
        title=ft.Text("読みの修正"),
        content=ft.TextField(ref=edit_field_ref, autofocus=True, label="読み（ひらがな）"),
        actions=[
            ft.TextButton("キャンセル", on_click=lambda e: close_dialog(edit_dialog)),
            ft.TextButton("保存", on_click=save_reading_edit),
        ],
    )

    def open_edit_dialog(index):
        state["editing_index"] = index
        item = state["current_mapped_data"][index]
        edit_dialog.title = ft.Text(f"「{item['orig']}」の読みを修正")
        if edit_field_ref.current:
            edit_field_ref.current.value = item['reading']
        open_dialog(edit_dialog)

    def render_braille_preview():
        try:
            braille_display_area.controls.clear()
            
            flat_cells_all = []
            
            # 【修正点2】中身が空のアイテム（消去された単語）を除外したインデックスリストを作成
            # これにより、空の単語の前後に無駄なスペースが入るのを防ぎます
            valid_indices = [
                i for i, item in enumerate(state["current_mapped_data"]) 
                if item['cells'] and len(item['cells']) > 0
            ]
            
            for i, word_idx in enumerate(valid_indices):
                item = state["current_mapped_data"][word_idx]
                
                # 点字セルを追加
                for cell in item['cells']:
                    flat_cells_all.append({
                        'dots': cell['dots'],
                        'char': cell['char'],
                        'word_idx': word_idx, # クリック時のために元のインデックスを保持
                        'orig': item['orig']
                    })
                
                # 最後の有効な単語でなければスペースを追加
                if i < len(valid_indices) - 1:
                    flat_cells_all.append({
                        'dots': SPACE_MARK, 'char': ' ', 'word_idx': -1, 'orig': '(Space)'
                    })
            
            chars_per_line = int(settings["max_chars_per_line"])
            lines_per_plate = int(settings["max_lines_per_plate"])
            
            lines = split_cells_with_rules(flat_cells_all, chars_per_line)
            plates = [lines[i:i + lines_per_plate] for i in range(0, len(lines), lines_per_plate)]

            for i, plate_lines in enumerate(plates):
                plate_num = i + 1
                plate_content_controls = []
                
                for line_cells in plate_lines:
                    row_controls = []
                    for cell_info in line_cells:
                        cell_dots = cell_info['dots']
                        char_str = cell_info['char']
                        word_idx = cell_info['word_idx']
                        
                        col1 = ft.Column(spacing=2, controls=[_make_dot(cell_dots[0]), _make_dot(cell_dots[1]), _make_dot(cell_dots[2])])
                        col2 = ft.Column(spacing=2, controls=[_make_dot(cell_dots[3]), _make_dot(cell_dots[4]), _make_dot(cell_dots[5])])
                        
                        cell_ui = ft.Container(
                            content=ft.Column([
                                ft.Container(
                                    content=ft.Row([col1, col2], spacing=2),
                                    padding=4,
                                    bgcolor=AppColors.SURFACE,
                                    border_radius=ft.BorderRadius(4, 4, 4, 4),
                                    shadow=ft.BoxShadow(blur_radius=1, color=ft.Colors.with_opacity(0.1, "#000000")),
                                ),
                                ft.Text(char_str, style=TextStyles.READING, text_align=ft.TextAlign.CENTER, width=20)
                            ], spacing=2, alignment=ft.MainAxisAlignment.CENTER),
                            on_click=lambda e, idx=word_idx: open_edit_dialog(idx) if idx != -1 else None,
                        )
                        row_controls.append(cell_ui)
                    
                    plate_content_controls.append(
                        ft.Row(row_controls, spacing=8, alignment=ft.MainAxisAlignment.START, scroll=ft.ScrollMode.ALWAYS)
                    )

                plate_ui = ft.Column([
                    ft.Text(f"Plate #{plate_num}", style=TextStyles.PLATE_LABEL),
                    ft.Container(
                        content=ft.Column(plate_content_controls, spacing=10),
                        padding=10, 
                        bgcolor=ft.Colors.WHITE54,
                        border_radius=ft.BorderRadius(8, 8, 8, 8),
                        border=ft.Border.all(1, ft.Colors.BLACK12)
                    ),
                ], spacing=2)
                braille_display_area.controls.append(plate_ui)
            page.update()
        except Exception as e:
            logging.error(f"Render Error: {e}")
            show_snackbar("描画エラーが発生しました", is_error=True)

    # --- 履歴・保存 ---
    def restore_history_item(item):
        try:
            # 1. 設定の復元
            settings["max_chars_per_line"] = int(item.get("max_chars_per_line", 10))
            settings["max_lines_per_plate"] = int(item.get("max_lines_per_plate", 3))
            settings["plate_thickness"] = float(item.get("plate_thickness", 0.6))
            
            # 2. UIへの反映 (スライダー位置などを同期)
            sync_settings_ui()
            
            # 3. テキストとデータの復元
            restored_text = item.get("text", "")
            if txt_input_ref.current:
                txt_input_ref.current.value = restored_text

            # 編集済みデータがあればそれを使う（手動修正を復元）
            if item.get("mapped_data"):
                state["current_mapped_data"] = item["mapped_data"]
                render_braille_preview()
            else:
                update_braille_from_input(restored_text)
                
            show_snackbar(f"履歴を復元しました: {item.get('timestamp')}")
        except Exception as ex:
            logging.error(f"Restore Error: {ex}")
            traceback.print_exc()
            show_snackbar("復元に失敗しました", is_error=True)

    def show_history_dialog(e):
        try:
            history_list = history_manager.get_history()
            if not history_list:
                content = ft.Text("履歴はありません", text_align=ft.TextAlign.CENTER)
            else:
                list_items = []
                for idx, item in enumerate(history_list):
                    preview_text = item.get("text", "")[:15] + "..." if len(item.get("text", "")) > 15 else item.get("text", "")
                    meta_info = f"{item.get('timestamp')} | {item.get('max_chars_per_line')}文字/{item.get('max_lines_per_plate')}行/{item.get('plate_thickness')}mm"
                    list_items.append(
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.HISTORY),
                            title=ft.Text(preview_text, weight=ft.FontWeight.BOLD),
                            subtitle=ft.Text(meta_info, size=12),
                            on_click=lambda e, it=item: [restore_history_item(it), close_dialog(history_dlg)]
                        )
                    )
                content = ft.Column(list_items, scroll=ft.ScrollMode.AUTO, height=300)
            
            history_dlg = ft.AlertDialog(
                title=ft.Text("保存履歴 (最新50件)"),
                content=content,
                actions=[
                    ft.TextButton("閉じる", on_click=lambda e: close_dialog(history_dlg)),
                    ft.TextButton("履歴クリア", on_click=lambda e: [history_manager.clear_history(), close_dialog(history_dlg), show_snackbar("履歴を消去しました")])
                ],
            )
            open_dialog(history_dlg)
        except Exception as ex:
            logging.error(f"History Dialog Error: {ex}")
            show_snackbar("履歴読み込みエラー", is_error=True)

    def update_braille_from_input(text):
        try:
            if not text:
                state["current_mapped_data"] = []
                braille_display_area.controls.clear()
                page.update()
                return
            state["current_mapped_data"] = converter.convert_with_mapping(text)
            render_braille_preview()
        except Exception as e:
            logging.error(f"Conversion Error: {e}")

    def get_structured_data_for_export():
        flat_cells_all = []
        for word_idx, item in enumerate(state["current_mapped_data"]):
            # エクスポート時も空データを除外するかどうかですが、
            # プレビューと一致させるため、空のセルリストを持つものはスキップします
            if not item['cells']:
                continue
                
            for cell in item['cells']:
                flat_cells_all.append(cell) 
            
            # 次の「有効な」要素がある場合のみスペースを入れたいが、
            # 簡易的に末尾以外にはスペースを入れる（ただし厳密にはプレビューと同じロジックが望ましい）
            # ここでは既存ロジックを維持しつつ、もし問題があれば valid_indices 方式に合わせる
            if word_idx < len(state["current_mapped_data"]) - 1:
                flat_cells_all.append({'dots': SPACE_MARK, 'char': ' '})
                
        lines = split_cells_with_rules(flat_cells_all, settings["max_chars_per_line"])
        lines_per_plate = settings["max_lines_per_plate"]
        plates = [lines[i:i + lines_per_plate] for i in range(0, len(lines), lines_per_plate)]
        return plates

    def handle_save_button_click(e):
        # print("DEBUG: handle_save_button_click called")
        logging.info("Action: Save button clicked")
        if not state["current_mapped_data"]:
            show_snackbar("データがありません", is_error=True)
            return
        
        # 保存前に履歴に追加 (現在の状態をスナップショット保存)
        try:
            current_text = txt_input_ref.current.value if txt_input_ref.current else ""
            history_manager.add_entry(current_text, settings, state["current_mapped_data"])
        except Exception as he:
            logging.error(f"History Save Error: {he}")
        try:
            # UI更新を強制
            page.update()

            # 設定またはプラットフォームに応じて保存方法を分岐
            # macOSの場合はfile_pickerがNoneになっているのでelseへ落ち、handle_quick_saveへ行くはず
            if settings["use_quick_save"] or page.platform in [ft.PagePlatform.IOS, ft.PagePlatform.ANDROID]:
                logging.info("Routing to Quick Save")
                handle_quick_save()
            else:
                if file_picker:
                    logging.info("Opening FilePicker")
                    try:
                        file_picker.save_file(dialog_title="パッケージを保存", file_name="tenji_package.zip")
                    except Exception as e:
                        logging.error(f"FilePicker Failed: {e}")
                        # FilePicker失敗時はQuickSaveへフォールバック
                        handle_quick_save()
                else:
                    logging.info("FilePicker not available, using Quick Save")
                    handle_quick_save()
                    
        except Exception as ex:
            logging.error(f"Save Button Critical Error: {ex}")
            traceback.print_exc()
            show_snackbar(f"保存処理エラー: {str(ex)}", is_error=True)

# ... (前略) ...

    def handle_quick_save():
        logging.info("Action: handle_quick_save executing")
        try:
            import tempfile
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tenji_export_{timestamp}.zip"
            
            # 保存先の決定ロジック
            if page.platform == ft.PagePlatform.IOS:
                # iOSの場合: ユーザーが見える 'Documents' フォルダを指定
                # os.path.expanduser("~") はアプリのサンドボックスルートを指すため、その下のDocumentsを使う
                base_dir = os.path.join(os.path.expanduser("~"), "Documents")
                if not os.path.exists(base_dir):
                    os.makedirs(base_dir)
                save_path = os.path.join(base_dir, filename)
            elif page.platform == ft.PagePlatform.ANDROID:
                 # Androidの場合: 外部ストレージのDownloadフォルダなどを狙う必要があるが、
                 # 最近のAndroid制限により、FilePickerを使わない場合は内部ストレージになることが多い。
                 # ここでは一旦従来のtempか、特定パスを指定
                 # ※AndroidはFilePicker経由が確実ですが、QuickSaveなら以下を試行
                 base_dir = "/storage/emulated/0/Download"
                 if os.path.exists(base_dir):
                     save_path = os.path.join(base_dir, filename)
                 else:
                     save_path = os.path.join(tempfile.gettempdir(), filename)
            else:
                # PC/Mac: ユーザーの "Downloads" フォルダ
                base_dir = os.path.join(os.path.expanduser("~"), "Downloads")
                # 万が一 Downloads が存在しない場合 (サーバー環境など) は Temp へ
                if not os.path.exists(base_dir):
                    base_dir = tempfile.gettempdir()
            
            save_path = os.path.join(base_dir, filename)
            logging.info(f"Generating STL/ZIP to: {save_path}")
            _perform_export(save_path)
            
            # 完了メッセージ（パスが長いのでファイル名だけ表示）
            show_snackbar(f"保存完了: {filename}\n('ファイル'アプリで確認してください)")
            logging.info(f"Quick save success: {save_path}")
            
        except Exception as ex:
            logging.error(f"Quick Save Error: {ex}")
            traceback.print_exc()
            show_snackbar(f"保存失敗: {str(ex)}", is_error=True)

    def _perform_export(path):
        plates_data = get_structured_data_for_export()
        original_txt = txt_input_ref.current.value if txt_input_ref.current else ""
        stl_generator.generate_package_from_plates(
            plates_data, path, 
            original_text_str=original_txt,
            base_thickness=settings["plate_thickness"]
        )

    def on_file_picked(e):
        if e.path:
            try:
                _perform_export(e.path)
                show_snackbar(f"保存しました: {os.path.basename(e.path)}")
            except Exception as ex:
                logging.error(f"Export Error: {ex}")
                show_snackbar(f"エラー: {str(ex)}", is_error=True)

    # FilePickerの設定
    file_picker = None
    if 0:
        if page.platform == ft.PagePlatform.MACOS:
            file_picker = None
        elif settings["use_quick_save"] or page.platform in [ft.PagePlatform.IOS, ft.PagePlatform.ANDROID]:
            file_picker = ft.FilePicker()
            file_picker.on_result = on_file_picked
            page.overlay.append(file_picker)
        else:
            file_picker = None

    def show_settings(e):
        # 現在の設定値をスライダーに反映
        sync_settings_ui()
        
        def on_chars_change(e):
            val = int(e.control.value)
            if chars_label_ref.current: chars_label_ref.current.value = f"{val}文字"
            if chars_slider_ref.current: chars_slider_ref.current.label = f"{val}"
            settings["max_chars_per_line"] = val
            history_manager.save_settings(settings)
            page.update()

        def on_lines_change(e):
            val = int(e.control.value)
            if lines_label_ref.current: lines_label_ref.current.value = f"{val}行"
            if lines_slider_ref.current: lines_slider_ref.current.label = f"{val}"
            settings["max_lines_per_plate"] = val
            history_manager.save_settings(settings)
            page.update()

        def on_thick_change(e):
            val = float(e.control.value)
            if thickness_label_ref.current: thickness_label_ref.current.value = f"{val:.1f}mm"
            if thickness_slider_ref.current: thickness_slider_ref.current.label = f"{val:.1f}mm"
            settings["plate_thickness"] = val
            history_manager.save_settings(settings)
            page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("出力設定"),
            content=ft.Column([
                ft.Text("1行あたりの文字数"),
                ft.Row([
                    ft.Slider(ref=chars_slider_ref, min=5, max=30, divisions=25, on_change=on_chars_change, expand=True),
                    ft.Text(ref=chars_label_ref, width=60, text_align=ft.TextAlign.RIGHT)
                ]),
                ft.Text("1プレートあたりの行数"),
                ft.Row([
                    ft.Slider(ref=lines_slider_ref, min=1, max=20, divisions=19, on_change=on_lines_change, expand=True),
                    ft.Text(ref=lines_label_ref, width=60, text_align=ft.TextAlign.RIGHT)
                ]),
                ft.Text("プレートの厚さ (mm)"),
                ft.Row([
                    ft.Slider(ref=thickness_slider_ref, min=0.4, max=2.0, divisions=16, on_change=on_thick_change, expand=True),
                    ft.Text(ref=thickness_label_ref, width=60, text_align=ft.TextAlign.RIGHT)
                ]),
            ], height=300, tight=True),
            actions=[ft.TextButton("閉じる", on_click=lambda e: [close_dialog(dlg), render_braille_preview()])],
        )
        open_dialog(dlg)
        # ダイアログが開いた直後に値を同期
        sync_settings_ui()

    # デザイン変更: 入力フィールドをコンテナで包み、背景色とボーダーを設定
    txt_input = ft.TextField(
        ref=txt_input_ref,
        multiline=True, min_lines=3, max_lines=5,
        hint_text="ここに日本語を入力...",
        border=ft.InputBorder.NONE, # TextField自体の枠線は消す
        filled=True,
        bgcolor=AppColors.SURFACE, # テキストエリアは白
        border_radius=ft.BorderRadius(10, 10, 10, 10), # 角丸
        text_style=TextStyles.BODY,
        on_change=lambda e: update_braille_from_input(e.control.value),
        content_padding=20, # パディングで見やすく
        width=None, # 親のSTRETCHに従わせるためNoneまたは指定なし
    )

    header_actions = [
        ft.IconButton(icon=ft.Icons.HISTORY, icon_color=AppColors.PRIMARY, tooltip="履歴", on_click=lambda e: show_history_dialog(e)),
        ft.IconButton(icon=ft.Icons.SETTINGS, icon_color=AppColors.PRIMARY, tooltip="設定", on_click=lambda e: show_settings(e)),
        # ft.IconButton(icon=ft.Icons.SAVE_ALT, icon_color=AppColors.PRIMARY, tooltip="保存", on_click=handle_save_button_click)
    ]
    try:
        logo_widget = ft.Image(src="logo.png", height=40, fit="contain", error_content=ft.Text("Tenji P-Fab", style=TextStyles.HEADER))
    except:
        logo_widget = ft.Text("Tenji P-Fab", style=TextStyles.HEADER)

    header = ft.Container(
        content=ft.Row([
            # ft.IconButton(icon=ft.Icons.MENU, icon_color=AppColors.PRIMARY, on_click=show_drawer),
            logo_widget,
            ft.Row(header_actions, spacing=10),
                #[
                #header_actions,
                #ft.IconButton(icon=ft.Icons.SAVE_ALT, icon_color=AppColors.PRIMARY, on_click=handle_save_button_click),
            #])
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=ft.Padding(left=10, top=50, right=10, bottom=10),
        bgcolor=AppColors.BACKGROUND
    )

    body_content = ft.Column([
        ft.Container(
            content=ft.Column([
                ft.Text("点字プレビュー", style=TextStyles.CAPTION),
                ft.Container(
                    content=braille_display_area,
                    expand=True,
                    padding=10, 
                    alignment=ft.Alignment(-1, -1),
                )
            ]),
            expand=True, 
            bgcolor=AppColors.BACKGROUND,
        ),
        # 入力エリア: デザイン修正 (幅広・パディング縮小・高さ自動調整)
        ft.Container(
            content=ft.Column([
                ft.Text("入力テキスト", style=TextStyles.CAPTION),
                ft.Container(
                    content=ft.Column([
                        txt_input, 
                        ft.Container(height=10),
                        ft.Row([
                            ft.ElevatedButton(
                                "保存", icon=ft.Icons.SAVE,
                                style=ComponentStyles.MAIN_BUTTON_STYLE,
                                on_click=handle_save_button_click,
                                expand=True
                            )
                        ])
                    ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH), # 中身を引き伸ばす
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.STRETCH), # 中身を引き伸ばす
            # expand=Falseにして高さを自動調整（プレビューエリアを広くする）
            expand=False, 
            padding=5, # パディングを減らして横幅を確保
            border_radius=ft.BorderRadius(30, 30, 0, 0),
            bgcolor=ft.Colors.GREY_200, 
        )
    ], spacing=0, expand=True)

    page.add(
        ft.Column([header, body_content], expand=True, spacing=0)
    )

    # 最後に確実に更新
    page.update()

if __name__ == "__main__":
    assets_path = os.path.join(os.getcwd(), "assets")
    if not os.path.exists(assets_path):
        os.makedirs(assets_path)
    
    # ft.app で起動
    try:
        ft.app(target=main, assets_dir="assets")
    except Exception:
        ft.run(target=main, assets_dir="assets")