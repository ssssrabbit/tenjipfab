"""Tenji: Japanese braille -> projected dots on a surface."""
import difflib
import time

import bpy
from bpy.props import (BoolProperty, CollectionProperty, EnumProperty, FloatProperty, IntProperty,
                       PointerProperty, StringProperty)
from bpy.types import Operator, Panel, PropertyGroup, UIList

from tenji.geometry import Dims

from . import core

# ---------------------------------------------------------------- 自動更新(任意。既定はオフ。デバウンス付き。スレッドは使わない)

DEBOUNCE = 0.15          # 入力が止まってからこの秒数後にまとめて更新する
_state = {"convert": False, "last": 0.0, "busy": False}


def request(convert: bool = False) -> None:
    """プロパティが変わったときに呼ぶ。連続した変更は1回の更新にまとめる。"""
    if _state["busy"]:
        return
    if convert:
        _state["convert"] = True
    _state["last"] = time.monotonic()
    if not bpy.app.timers.is_registered(_tick):
        bpy.app.timers.register(_tick, first_interval=DEBOUNCE)


def _tick():
    wait = _state["last"] + DEBOUNCE - time.monotonic()
    if wait > 0:
        return wait
    scene = bpy.context.scene
    s = getattr(scene, "tenji", None)
    convert, _state["convert"] = _state["convert"], False
    if s is None or not s.live:
        return None
    _state["busy"] = True
    try:
        update_all(scene, s, convert=convert)
    except Exception as e:                      # 入力途中の状態で例外を出さない
        s.warn = f"エラー: {e}"
    finally:
        _state["busy"] = False
    return None


def on_text(self, context):
    request(convert=True)


def on_param(self, context):
    request()


# ---------------------------------------------------------------- データ

class TenjiWord(PropertyGroup):
    orig: StringProperty()
    reading: StringProperty(name="読み", update=on_param)
    auto_reading: StringProperty()                       # 辞書が返した読み(手動で変えたか判定する)
    pos: StringProperty()
    para: BoolProperty()
    attach: BoolProperty()
    typed_gap: IntProperty(default=-1)                   # テキストに手で入れた空白のマス数(-1=入れていない)
    gap: EnumProperty(
        name="後ろの空白", default="AUTO", update=on_param,
        items=[("AUTO", "自動", "点字の規則で決める"), ("0", "なし", "この語の後ろを空けない"),
               ("1", "1マス", "この語の後ろを1マス空ける"), ("2", "2マス", "この語の後ろを2マス空ける")])


class TenjiSettings(PropertyGroup):
    text: StringProperty(name="テキスト", default="", update=on_text, options={"TEXTEDIT_UPDATE"})
    words: CollectionProperty(type=TenjiWord)
    word_index: IntProperty()
    target: PointerProperty(name="対象モデル", type=bpy.types.Object, update=on_param)
    frame: PointerProperty(name="投影枠(Empty)", type=bpy.types.Object, update=on_param)
    dots: PointerProperty(name="作業中の点字", type=bpy.types.Object)       # 更新のたびに作り直す点のメッシュ
    cells_per_line: IntProperty(name="1行のセル数", default=10, min=1, update=on_param)
    layout_mode: EnumProperty(
        name="折り返し", default="RULES", update=on_param,
        items=[("RULES", "点字の規則で折り返す", "語を行にまたがせない。長すぎる語は音節で切り、行末に「ー」を付ける"),
               ("FIXED", "1行のセル数で並べる", "セルを左から並べ、1行のセル数に達したら折り返す(語の途中でも折り返す)")])
    align: EnumProperty(name="配置", update=on_param, items=[("LEFT", "左揃え", ""), ("CENTER", "中央揃え", "")])
    auto_space: BoolProperty(name="空白を自動で入れる", default=True, update=on_param,
                             description="オン: 分かち書きの空白を点字の規則で自動で入れる。オフ: テキストに手で入れた空白だけを使う")
    live: BoolProperty(name="自動で更新", default=False,
                       description="テキストや設定を変えるたびに、分かち書き・点字変換・モデル上の生成をやり直す。重いモデルでは、オフのまま「更新」を使う")
    dot_pitch: FloatProperty(name="点間 (mm)", default=2.4, min=0.1, update=on_param)
    cell_pitch: FloatProperty(name="セル間 (mm)", default=6.0, min=0.1, update=on_param)
    line_pitch: FloatProperty(name="行間 (mm)", default=10.0, min=0.1, update=on_param)
    dot_diameter: FloatProperty(name="点径 (mm)", default=1.5, min=0.1, update=on_param)
    dot_height: FloatProperty(name="点高さ (mm)", default=0.3, min=0.05, update=on_param)
    embed: FloatProperty(name="埋め込み (mm)", default=0.2, min=0.0, update=on_param)
    print_size_mm: FloatProperty(name="出力サイズ (mm)", default=0.0, min=0.0, update=on_param,
                                 description="対象モデルの最長辺を出力時に何mmにするか。0=シーン単位をそのまま使う")
    warn_angle: FloatProperty(name="警告角度(°)", default=45.0, min=1.0, max=89.0, update=on_param)
    report: StringProperty()
    warn: StringProperty()


def dims_of(s: TenjiSettings) -> Dims:
    return Dims(s.dot_pitch, s.cell_pitch, s.line_pitch, s.dot_diameter, s.dot_height, s.embed)


def effective_gap(s: TenjiSettings, w) -> "int | None":
    """語の後ろの空白マス数。優先順: 一覧で指定した値 > テキストに手で入れた空白 > 自動(規則)。None=規則で決める。"""
    if w.gap != "AUTO":
        return int(w.gap)
    if w.typed_gap >= 0:
        return w.typed_gap
    return None if s.auto_space else 0


def words_of(s: TenjiSettings):
    return [(w.orig, w.reading, w.pos, w.para, w.attach, effective_gap(s, w)) for w in s.words]


# ---------------------------------------------------------------- 変換と生成

def convert_words(s: TenjiSettings, reset: bool) -> None:
    """テキストを分かち書きして語の一覧を作る。reset=False のときは、手で直した読み・空白を同じ語に引き継ぐ。
    テキストに手で入れた空白は、直前の語の「後ろの空白」(typed_gap)になる。"""
    from tenji.japanese import convert, fold_whitespace
    new = fold_whitespace(convert(s.text))
    old = [(w.orig, w.reading, w.auto_reading, w.gap) for w in s.words]
    keep: dict[int, tuple[str, str]] = {}                  # 新しい語の番号 -> (引き継ぐ読み or "", 引き継ぐ空白)
    if not reset and old:
        sm = difflib.SequenceMatcher(None, [o[0] for o in old], [m.orig for m, _ in new], autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                for k in range(i2 - i1):
                    o_orig, o_read, o_auto, o_gap = old[i1 + k]
                    keep[j1 + k] = (o_read if o_read != o_auto else "", o_gap)
    prev_index = s.word_index
    s.words.clear()
    for j, (m, typed) in enumerate(new):
        w = s.words.add()
        w.orig, w.pos, w.para, w.attach = m.orig, m.pos or "", m.is_paragraph_start, m.attach_prev
        w.typed_gap = typed
        w.auto_reading = m.reading
        read, gap = keep.get(j, ("", "AUTO"))
        w.reading = read or m.reading
        w.gap = gap
    s.word_index = min(prev_index, max(len(s.words) - 1, 0))


def layout_lines(s: TenjiSettings):
    return core.words_to_lines(words_of(s), s.cells_per_line, s.layout_mode)


def generate_now(scene, s: TenjiSettings) -> dict:
    lines = layout_lines(s)
    rep = core.generate(scene, lines=lines, target=s.target, frame=s.frame, dims=dims_of(s), align=s.align,
                        k=core.bu_per_mm(scene, s.target, s.print_size_mm), warn_angle_deg=s.warn_angle, dots=s.dots)
    s.dots = rep["obj"]
    s.report = f"{rep['dots_created']}/{rep['dots_expected']}点 / {len(lines)}行 / 最大入射角 {rep['max_incidence_deg']}°"
    warn = []
    if rep["missed_count"]:
        warn.append(f"モデルに当たらない点: {rep['missed_count']}点")
    if rep["steep_count"]:
        warn.append(f"急斜面(>{s.warn_angle:g}°): {rep['steep_count']}点")
    s.warn = "\n".join(warn)
    return rep


def update_all(scene, s: TenjiSettings, convert: bool = True) -> None:
    """分かち書き・点字変換・モデル上の生成を、いまのテキストと設定でやり直す。"""
    if convert or len(s.words) == 0:
        convert_words(s, reset=False)
    if s.target and s.frame and (len(s.words) or s.dots):
        generate_now(scene, s)                      # テキストを空にしたときは、点も空にする


# ---------------------------------------------------------------- オペレーター

class TENJI_OT_convert(Operator):
    bl_idname = "tenji.convert"
    bl_label = "読みを作り直す"
    bl_description = "テキストを分かち書きして読み一覧を作り直す(手で直した読み・空白はリセットされる)"

    def execute(self, context):
        s = context.scene.tenji
        convert_words(s, reset=True)
        if s.target and s.frame and len(s.words):
            generate_now(context.scene, s)
        return {"FINISHED"}


class TENJI_OT_create_frame(Operator):
    bl_idname = "tenji.create_frame"
    bl_label = "投影枠を作成"
    bl_description = "対象モデルの上に Empty を置く。ローカル -Z が投影方向、+X が読む方向、-Y が次の行"

    def execute(self, context):
        s = context.scene.tenji
        e = bpy.data.objects.new("Tenji_Frame", None)
        e.empty_display_type = "ARROWS"
        e.empty_display_size = 10 * core.bu_per_mm(context.scene, s.target, s.print_size_mm)
        if s.target:
            from mathutils import Vector
            corners = [s.target.matrix_world @ Vector(c) for c in s.target.bound_box]
            top = max(c.z for c in corners)
            cx = sum(c.x for c in corners) / 8
            cy = sum(c.y for c in corners) / 8
            e.location = (cx, cy, top + 20 * core.bu_per_mm(context.scene, s.target, s.print_size_mm))
        else:
            e.location = context.scene.cursor.location
        context.scene.collection.objects.link(e)
        s.frame = e
        return {"FINISHED"}


def place_frame_from_view(context) -> None:
    """今の3Dビューの向きに投影枠を合わせる(枠が無ければ作る)。"""
    from mathutils import Matrix, Vector
    s = context.scene.tenji
    scene = context.scene
    rv3d = context.region_data
    k = core.bu_per_mm(scene, s.target, s.print_size_mm)
    rot = rv3d.view_rotation.to_matrix()                 # 列 = 画面の右 / 上 / 手前 (ワールド座標)
    view_dir = -(rot @ Vector((0, 0, 1)))                # 視線(奥向き)
    # 画面中央から視線方向へレイを飛ばし、対象モデル上の点を探す
    center = rv3d.view_location - view_dir * rv3d.view_distance * 2.0
    dg = context.evaluated_depsgraph_get()
    t_inv = s.target.matrix_world.inverted()
    ok, loc, _, _ = s.target.evaluated_get(dg).ray_cast(t_inv @ center, (t_inv.to_3x3() @ view_dir).normalized())
    hit = s.target.matrix_world @ loc if ok else rv3d.view_location
    origin = hit - view_dir * (20 * k)                   # モデルの手前20mmから。「中央揃え」ならブロックの中心がここになる
    fr = s.frame
    if fr is None:
        fr = bpy.data.objects.new("Tenji_Frame", None)
        fr.empty_display_type = "ARROWS"
        scene.collection.objects.link(fr)
    fr.empty_display_size = 10 * k
    fr.matrix_world = Matrix.Translation(origin) @ rot.to_4x4()
    s.align = "CENTER"
    s.frame = fr
    request()


class TENJI_OT_place_here(Operator):
    bl_idname = "tenji.place_here"
    bl_label = "選択モデルに点字作成"
    bl_description = ("選択中のモデルの、今 3Dビューの中央に見えている場所に点字を作る。画面の右が読む方向、下が次の行、"
                      "奥の面に向かって載る。載せたい面を正面に向けてから押す。もう一度押すと、今の点字をその場所へ移す")

    @classmethod
    def poll(cls, context):
        ob = context.active_object
        return (context.region_data is not None and ob is not None and ob.type == "MESH"
                and ob.select_get() and not ob.name.startswith("Tenji_"))

    def execute(self, context):
        s = context.scene.tenji
        s.target = context.active_object
        place_frame_from_view(context)
        if s.text or len(s.words):
            update_all(context.scene, s)
        return {"FINISHED"}


class TENJI_OT_create_frame_from_view(Operator):
    bl_idname = "tenji.create_frame_from_view"
    bl_label = "視点から枠を作成"
    bl_description = "対象モデル(詳細で指定)に対して、今の3Dビューの向きに投影枠を合わせる"

    @classmethod
    def poll(cls, context):
        return context.region_data is not None and context.scene.tenji.target is not None

    def execute(self, context):
        place_frame_from_view(context)
        return {"FINISHED"}


class TENJI_OT_generate(Operator):
    bl_idname = "tenji.generate"
    bl_label = "更新"
    bl_description = "いまのテキストと設定で、分かち書き・点字変換・モデル上の生成をやり直す"

    @classmethod
    def poll(cls, context):
        s = context.scene.tenji
        return s.target and s.frame and (len(s.text) > 0 or len(s.words) > 0)

    def execute(self, context):
        s = context.scene.tenji
        update_all(context.scene, s)
        self.report({"WARNING" if s.warn else "INFO"}, s.report + ("  " + s.warn.replace("\n", " / ") if s.warn else ""))
        return {"FINISHED"}


class TENJI_OT_new_label(Operator):
    bl_idname = "tenji.new_label"
    bl_label = "新規点字"
    bl_description = ("今の点字を確定して残し(Tenji_Label という名前の通常のメッシュになる)、テキストを空にして新しい点字を作り始める。"
                      "対象モデル・枠・サイズの設定はそのまま使う。確定しないと、次の更新で今の点字は上書きされる")

    @classmethod
    def poll(cls, context):
        return context.scene.tenji.dots is not None

    def execute(self, context):
        s = context.scene.tenji
        s.dots.name = "Tenji_Label"          # 同名があれば Blender が .001 を付ける
        _state["busy"] = True
        try:
            s.dots = None
            s.text = ""
            s.words.clear()
            s.report = ""
            s.warn = ""
        finally:
            _state["busy"] = False
        return {"FINISHED"}


class TENJI_OT_verify(Operator):
    bl_idname = "tenji.verify"
    bl_label = "検証(逆読み)"
    bl_description = "生成されたメッシュから点を読み戻し、期待する点字と一致するか確認する"

    @classmethod
    def poll(cls, context):
        return context.scene.tenji.dots is not None

    def execute(self, context):
        s = context.scene.tenji
        rep = core.verify(context.scene, s.dots)
        s.report = ("OK: " if rep["ok"] else "不一致: ") + " / ".join(rep["decoded"])
        self.report({"INFO" if rep["ok"] else "ERROR"}, s.report)
        return {"FINISHED"}


# ---------------------------------------------------------------- UI

class TENJI_UL_words(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        label = item.orig if item.orig.strip() else ("¶" if item.para else "↵")
        row = layout.split(factor=0.28, align=True)
        row.label(text=label)
        if item.orig in ("", "\n"):
            return
        sub = row.split(factor=0.62, align=True)
        sub.prop(item, "reading", text="")
        sub.prop(item, "gap", text="")


class TENJI_PT_main(Panel):
    bl_label = "点字"
    bl_idname = "TENJI_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tenji"

    def draw(self, context):
        s = context.scene.tenji
        col = self.layout.column()
        if not s.frame:
            ob = context.active_object
            if ob is None or ob.type != "MESH" or not ob.select_get() or ob.name.startswith("Tenji_"):
                col.label(text="① モデルを選択してください", icon="INFO")
            else:
                col.label(text="② 面を正面に向けて押す", icon="INFO")
        elif not s.text.strip():
            col.label(text="③ テキストを入力してください", icon="INFO")
        col.operator("tenji.place_here", icon="VIEW3D")
        col.prop(s, "text")
        if len(s.words):
            col.template_list("TENJI_UL_words", "", s, "words", s, "word_index", rows=6, maxrows=14)
            col.label(text="空白はテキストに直接入力できる", icon="INFO")
            col.label(text="右の列: 語の後ろの空白(個別に指定)")
            col.operator("tenji.convert", icon="FILE_REFRESH")
        col.separator()
        col.prop(s, "cells_per_line")
        col.prop(s, "layout_mode", text="")
        col.prop(s, "align")
        col.prop(s, "auto_space")
        col.separator()
        row = col.row(align=True)
        row.prop(s, "live", toggle=True, icon="FILE_REFRESH")
        row.operator("tenji.generate", text="更新")
        col.operator("tenji.verify")
        col.operator("tenji.new_label", icon="ADD")
        if s.report:
            col.label(text=s.report, icon="INFO")
        for line in s.warn.split("\n") if s.warn else []:
            for i in range(0, len(line), 16):                  # パネル幅に収まるよう折り返して全部表示する
                col.label(text=line[i:i + 16], icon="ERROR" if i == 0 else "BLANK1")


class TENJI_PT_detail(Panel):
    """詳細(対象モデルと投影枠。通常は「選択モデルに点字作成」が自動で設定する)"""
    bl_label = "詳細(対象・枠)"
    bl_idname = "TENJI_PT_detail"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tenji"
    bl_parent_id = "TENJI_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        s = context.scene.tenji
        col = self.layout.column()
        col.prop(s, "target")
        row = col.row(align=True)
        row.prop(s, "frame", text="枠")
        row.operator("tenji.create_frame", text="", icon="ADD")
        col.operator("tenji.create_frame_from_view")


class TENJI_PT_size(Panel):
    """サイズ(アコーディオンで折りたためる)"""
    bl_label = "サイズ"
    bl_idname = "TENJI_PT_size"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tenji"
    bl_parent_id = "TENJI_PT_main"

    def draw(self, context):
        s = context.scene.tenji
        col = self.layout.column()
        for p in ("dot_pitch", "cell_pitch", "line_pitch", "dot_diameter", "dot_height", "embed", "print_size_mm", "warn_angle"):
            col.prop(s, p)


CLASSES = (TenjiWord, TenjiSettings, TENJI_OT_convert, TENJI_OT_create_frame, TENJI_OT_create_frame_from_view, TENJI_OT_place_here,
           TENJI_OT_generate, TENJI_OT_new_label, TENJI_OT_verify, TENJI_UL_words, TENJI_PT_main, TENJI_PT_detail, TENJI_PT_size)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)
    bpy.types.Scene.tenji = PointerProperty(type=TenjiSettings)


def unregister():
    if bpy.app.timers.is_registered(_tick):
        bpy.app.timers.unregister(_tick)
    del bpy.types.Scene.tenji
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
