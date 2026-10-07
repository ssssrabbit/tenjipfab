# Runs inside Blender (background): enable the INSTALLED extension and generate braille on a plane. Fails loudly.
import bpy

bpy.ops.preferences.addon_enable(module="bl_ext.user_default.tenji_pfab")
import bl_ext.user_default.tenji_pfab as T
import janome

assert ".local/lib" in janome.__file__, f"Janome must come from the extension's bundled wheel: {janome.__file__}"
assert "/user_default/tenji_pfab/" in T.__file__, T.__file__

sc = bpy.context.scene
sc.unit_settings.scale_length = 0.001
sc.unit_settings.length_unit = "MILLIMETERS"
bpy.ops.mesh.primitive_plane_add(size=100, location=(0, 0, 0))
plate = bpy.context.active_object
fr = bpy.data.objects.new("Tenji_Frame", None)
sc.collection.objects.link(fr)
fr.location = (0, 0, 30)
s = sc.tenji
s.target, s.frame, s.align, s.cells_per_line = plate, fr, "CENTER", 10
s.text = "点字ラベル、確認。"
T.convert_words(s, reset=True)
assert [w.orig for w in s.words] == ["点字", "ラベル", "、", "確認", "。"], [w.orig for w in s.words]
rep = T.generate_now(sc, s)
v = T.core.verify(sc)
assert rep["dots_created"] == rep["dots_expected"] == 40, rep
assert v["ok"], v
for op in ("place_here", "new_label", "generate", "verify", "convert"):
    assert hasattr(bpy.ops.tenji, op), op
print("SMOKE OK:", s.report, v["decoded"])
