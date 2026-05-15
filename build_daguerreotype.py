"""
Giroux Daguerreotype Camera (1839) — v2 procedural generator.
Adds: bevels, brass screws, sliding-rail guides, leather strap, engraved Giroux
nameplate, Daguerre red anti-forgery seal, two-element Chevalier achromat with
Waterhouse stop, PBR image-textured materials, full hotspot annotations.json.

Run via build.sh, or directly:
    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python build_daguerreotype.py -- --out dist/
"""

import bpy, bmesh, math, os, sys, json
from mathutils import Vector

# ---------- CLI ----------
argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--") + 1:]
else:
    argv = []
out_dir = "dist"
for i, a in enumerate(argv):
    if a == "--out" and i + 1 < len(argv):
        out_dir = argv[i + 1]
out_dir = os.path.abspath(out_dir)
TEX_DIR = os.path.join(out_dir, "textures")
os.makedirs(out_dir, exist_ok=True)
os.makedirs(TEX_DIR, exist_ok=True)

ASSET_NAME = "daguerreotype_giroux_1839"

# ---------- Scene reset ----------
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.unit_settings.system = 'METRIC'
scn.unit_settings.length_unit = 'METERS'
scn.render.fps = 30
scn.frame_start = 1
scn.frame_end = 600

# ============================================================
# Material helpers
# ============================================================

def load_tex(path):
    if not os.path.isfile(path):
        return None
    img = bpy.data.images.load(path, check_existing=True)
    return img


def base_material(name, base_color=(0.5, 0.5, 0.5), metallic=0.0, roughness=0.5,
                  transmission=0.0, alpha=1.0, emission=(0, 0, 0, 1), emission_strength=0.0,
                  color_tex=None, normal_tex=None, roughness_tex=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (400, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (100, 0)
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    bsdf.inputs["Base Color"].default_value = (*base_color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    for k in ("Transmission Weight", "Transmission"):
        if k in bsdf.inputs:
            bsdf.inputs[k].default_value = transmission; break
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = 1.52
    bsdf.inputs["Alpha"].default_value = alpha
    if "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = emission
    if "Emission Strength" in bsdf.inputs:
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    if alpha < 1.0 or transmission > 0.0:
        mat.blend_method = 'BLEND'
    if color_tex:
        img = load_tex(color_tex)
        if img:
            tx = nt.nodes.new("ShaderNodeTexImage"); tx.location = (-300, 200); tx.image = img
            nt.links.new(tx.outputs["Color"], bsdf.inputs["Base Color"])
    if roughness_tex:
        img = load_tex(roughness_tex)
        if img:
            tx = nt.nodes.new("ShaderNodeTexImage"); tx.location = (-300, 0); tx.image = img
            img.colorspace_settings.name = 'Non-Color'
            nt.links.new(tx.outputs["Color"], bsdf.inputs["Roughness"])
    if normal_tex:
        img = load_tex(normal_tex)
        if img:
            img.colorspace_settings.name = 'Non-Color'
            tx = nt.nodes.new("ShaderNodeTexImage"); tx.location = (-500, -200); tx.image = img
            nm = nt.nodes.new("ShaderNodeNormalMap"); nm.location = (-200, -200); nm.inputs["Strength"].default_value = 0.8
            nt.links.new(tx.outputs["Color"], nm.inputs["Color"])
            nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


MAT = {
    "mahogany": base_material("Mahogany", (0.32, 0.12, 0.06), 0.0, 0.50,
                              color_tex=os.path.join(TEX_DIR, "mahogany_color.png"),
                              normal_tex=os.path.join(TEX_DIR, "mahogany_normal.png")),
    "mahogany2": base_material("MahoganyLight", (0.42, 0.18, 0.09), 0.0, 0.55,
                               color_tex=os.path.join(TEX_DIR, "mahogany_color.png"),
                               normal_tex=os.path.join(TEX_DIR, "mahogany_normal.png")),
    "brass": base_material("Brass", (0.85, 0.65, 0.30), 1.0, 0.28,
                           color_tex=os.path.join(TEX_DIR, "brass_color.png")),
    "brass_dark": base_material("BrassDark", (0.55, 0.42, 0.18), 1.0, 0.40,
                                color_tex=os.path.join(TEX_DIR, "brass_color.png")),
    "barrel_inner_black": base_material("BarrelInner", (0.02, 0.02, 0.02), 0.0, 0.95),
    "glass": base_material("OpticalGlass", (0.92, 0.95, 0.98), 0.0, 0.02, transmission=1.0, alpha=0.25),
    "ground_glass": base_material("GroundGlass", (0.85, 0.85, 0.82), 0.0, 0.75, transmission=0.55, alpha=0.55,
                                  normal_tex=os.path.join(TEX_DIR, "ground_glass_normal.png")),
    "silver_polished": base_material("SilverPolished", (0.96, 0.96, 0.94), 1.0, 0.04),
    "silver_iodized":  base_material("SilverIodized",  (0.88, 0.82, 0.45), 0.7, 0.35),
    "silver_developed":base_material("SilverDeveloped",(0.78, 0.74, 0.62), 0.85, 0.18),
    "silver_fixed":    base_material("SilverFixed",    (0.85, 0.83, 0.75), 0.9, 0.12),
    "boulevard_plate": base_material(
        "BoulevardPlate", (0.6, 0.55, 0.45), 0.85, 0.18,
        color_tex=os.path.join(TEX_DIR, "boulevard_du_temple_1838.png")),
    "boulevard_proj": base_material(
        "BoulevardProjection", (0.7, 0.65, 0.55), 0.0, 0.9, alpha=0.85,
        color_tex=os.path.join(TEX_DIR, "boulevard_du_temple_inverted.png"),
        emission=(0.7, 0.65, 0.55, 1.0), emission_strength=0.5),
    "leather": base_material("Leather", (0.26, 0.15, 0.08), 0.0, 0.65,
                             color_tex=os.path.join(TEX_DIR, "leather_color.png")),
    "darkslide": base_material("DarkSlide", (0.10, 0.08, 0.07), 0.0, 0.6),
    "ray": base_material("LightRay", (1.0, 0.95, 0.65), 0.0, 1.0, alpha=0.30,
                         emission=(1.0, 0.95, 0.65, 1.0), emission_strength=2.0),
    "iron": base_material("Iron", (0.30, 0.30, 0.32), 1.0, 0.5),
    "iodine_box": base_material("IodineBoxWood", (0.45, 0.30, 0.18), 0.0, 0.55),
    "hg_box": base_material("MercuryBoxWood", (0.35, 0.22, 0.12), 0.0, 0.55),
    "mercury": base_material("Mercury", (0.78, 0.80, 0.85), 1.0, 0.05),
    "iodine_vap": base_material("IodineVapor", (0.55, 0.45, 0.10), 0.0, 1.0, alpha=0.35,
                                emission=(0.55, 0.45, 0.10, 1.0), emission_strength=0.6),
    "fix_water": base_material("FixingBath", (0.65, 0.75, 0.85), 0.0, 0.2, alpha=0.55, transmission=0.7),
    "tripod": base_material("TripodWood", (0.20, 0.10, 0.05), 0.0, 0.6,
                            color_tex=os.path.join(TEX_DIR, "mahogany_color.png")),
    "seal_red": base_material("DaguerreSealRed", (0.55, 0.05, 0.04), 0.0, 0.4,
                              emission=(0.20, 0.01, 0.0, 1.0), emission_strength=0.15),
    "seal_text": base_material("SealText", (0.95, 0.92, 0.78), 1.0, 0.35),
}

# ============================================================
# Geometry helpers
# ============================================================

def apply_bevel(obj, width=0.0025, segments=2):
    mod = obj.modifiers.new("Bevel", type='BEVEL')
    mod.width = width
    mod.segments = segments
    mod.limit_method = 'ANGLE'
    mod.angle_limit = math.radians(30)
    return mod


def new_cube(name, size, location, parent=None, material=None, scale=(1, 1, 1), rotation=(0, 0, 0), bevel=True):
    # Build cube vertices manually so non-uniform "size" bakes into mesh data
    # without relying on bpy.ops.object.transform_apply (which in some Blender
    # 5.x build configurations also resets location unexpectedly).
    sx, sy, sz = size
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    mesh = bpy.data.meshes.new(name + "_mesh")
    verts = [
        (-hx, -hy, -hz), ( hx, -hy, -hz), ( hx,  hy, -hz), (-hx,  hy, -hz),
        (-hx, -hy,  hz), ( hx, -hy,  hz), ( hx,  hy,  hz), (-hx,  hy,  hz),
    ]
    faces = [
        (0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
        (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0),
    ]
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.scale = scale
    obj.rotation_euler = rotation
    if parent: obj.parent = parent
    if material: obj.data.materials.append(material)
    if bevel: apply_bevel(obj)
    return obj


def new_cylinder(name, radius, depth, location, parent=None, material=None,
                 rotation=(0, 0, 0), verts=48, bevel=False, bevel_w=0.0008):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, location=location, vertices=verts)
    obj = bpy.context.active_object
    obj.name = name
    obj.rotation_euler = rotation
    if parent: obj.parent = parent
    if material: obj.data.materials.append(material)
    if bevel: apply_bevel(obj, width=bevel_w, segments=2)
    return obj


def new_sphere_cap(name, radius, cap_h, location, parent=None, material=None, rotation=(0, 0, 0), segs=32):
    """Convex spherical cap centered on Y axis after rotation."""
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=(0, 0, 0), segments=segs, ring_count=segs // 2)
    obj = bpy.context.active_object
    obj.name = name
    # Trim everything below z=radius-cap_h
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    plane_z = radius - cap_h
    to_delete = [v for v in bm.verts if v.co.z < plane_z]
    bmesh.ops.delete(bm, geom=to_delete, context='VERTS')
    # Add cap rim at z=plane_z
    bm.to_mesh(obj.data); bm.free()
    obj.location = location
    obj.rotation_euler = rotation
    if parent: obj.parent = parent
    if material: obj.data.materials.append(material)
    return obj


def new_torus_ring(name, major_r, minor_r, location, parent=None, material=None, rotation=(0, 0, 0), majors=48, minors=12):
    bpy.ops.mesh.primitive_torus_add(major_radius=major_r, minor_radius=minor_r,
                                     major_segments=majors, minor_segments=minors,
                                     location=location, rotation=rotation)
    obj = bpy.context.active_object
    obj.name = name
    if parent: obj.parent = parent
    if material: obj.data.materials.append(material)
    return obj


def new_empty(name, location=(0, 0, 0), parent=None):
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=location)
    e = bpy.context.active_object
    e.name = name
    if parent: e.parent = parent
    return e


def brass_screw(name, location, parent, head_r=0.0045, head_h=0.0018, mat=MAT["brass"]):
    head = new_cylinder(name, head_r, head_h, location, parent=parent, material=mat, rotation=(math.radians(90), 0, 0), verts=20)
    # Slot: small thin cube
    slot = new_cube(name + "_slot", (head_r * 1.6, 0.0006, head_r * 0.25), (location[0], location[1] + head_h * 0.55, location[2]),
                    parent=parent, material=MAT["brass_dark"], bevel=False)
    slot.parent = head
    slot.location = (0, head_h * 0.6, 0)
    return head


def text_mesh(name, body, size=0.012, extrude=0.001, location=(0, 0, 0), rotation=(0, 0, 0), parent=None, material=None):
    bpy.ops.object.text_add(location=location, rotation=rotation)
    t = bpy.context.active_object
    t.name = name
    t.data.body = body
    t.data.size = size
    t.data.extrude = extrude
    t.data.align_x = 'CENTER'
    t.data.align_y = 'CENTER'
    # Convert to mesh so glTF embeds geometry (text curves don't always export cleanly)
    bpy.ops.object.convert(target='MESH')
    if parent: t.parent = parent
    if material: t.data.materials.append(material)
    return t


def set_extras(obj, data):
    for k, v in data.items():
        obj[k] = v


def world_pos(obj):
    return list(obj.matrix_world.translation)


# ============================================================
# Build hierarchy
# ============================================================

ROOT = new_empty("DaguerreotypeCamera")
set_extras(ROOT, {
    "title_ja": "Giroux ダゲレオタイプ・カメラ (1839)",
    "title_en": "Giroux Daguerreotype Camera (1839)",
    "designer": "Louis-Jacques-Mandé Daguerre",
    "maker": "Alphonse Giroux et Cie, Paris",
    "lens": "Chevalier achromat, FL≈380mm, f/14",
    "format": "Plaque entière 165×216 mm",
})

# ---- Outer box ----
OUTER = new_empty("OuterBox", parent=ROOT)
outer_body = new_cube("OuterBox_Body", (0.305, 0.260, 0.305), (0, -0.130, 0.0), parent=OUTER, material=MAT["mahogany"])
set_extras(outer_body, {"desc_ja": "外箱(マホガニー)。前面にレンズボードを保持し、内箱を摺動可能に受ける。",
                       "desc_en": "Outer mahogany box holding the lens board and sliding inner box."})

lens_board = new_cube("LensBoard", (0.305, 0.012, 0.305), (0, -0.260, 0.0), parent=OUTER, material=MAT["mahogany2"])
set_extras(lens_board, {"desc_ja": "レンズボード。中央に Chevalier アクロマートを装着。",
                       "desc_en": "Lens board carrying the Chevalier achromatic lens."})

# Brass corner screws on lens board (4 corners)
for sx, sz in [(-0.135, -0.135), (0.135, -0.135), (-0.135, 0.135), (0.135, 0.135)]:
    brass_screw(f"LensBoard_Screw_{sx:+.2f}_{sz:+.2f}", (sx, -0.255, sz), parent=OUTER)

# Brass corner screws on outer body (top edge x4)
for sx in (-0.140, 0.140):
    for sy in (-0.250, -0.010):
        brass_screw(f"Outer_TopScrew_{sx:+.2f}_{sy:+.2f}", (sx, sy, 0.150), parent=OUTER)

# Brass slide-rails on outer box top (sliding-box guides)
rail_l = new_cube("SlideRail_L", (0.006, 0.250, 0.004), (-0.144, -0.130, 0.152), parent=OUTER, material=MAT["brass"], bevel=False)
rail_r = new_cube("SlideRail_R", (0.006, 0.250, 0.004),  (0.144, -0.130, 0.152), parent=OUTER, material=MAT["brass"], bevel=False)

# Brass top handle
handle_arch = new_torus_ring("BrassHandle", 0.040, 0.0035, (0, -0.130, 0.180), parent=OUTER, material=MAT["brass"],
                              rotation=(0, math.radians(90), 0))

# Leather carrying strap arcing over the top
def leather_strap(parent):
    bpy.ops.curve.primitive_bezier_curve_add()
    cu = bpy.context.active_object
    cu.name = "LeatherStrap"
    spline = cu.data.splines[0]
    spline.bezier_points[0].co = (-0.150, -0.130, 0.155)
    spline.bezier_points[0].handle_left = (-0.180, -0.130, 0.155)
    spline.bezier_points[0].handle_right = (-0.080, -0.130, 0.260)
    spline.bezier_points[1].co = (0.150, -0.130, 0.155)
    spline.bezier_points[1].handle_left = (0.080, -0.130, 0.260)
    spline.bezier_points[1].handle_right = (0.180, -0.130, 0.155)
    cu.data.bevel_depth = 0.006
    cu.data.bevel_resolution = 3
    cu.data.extrude = 0.012
    bpy.ops.object.convert(target='MESH')
    cu.parent = parent
    cu.data.materials.append(MAT["leather"])
    return cu

leather_strap(OUTER)

# ---- Lens barrel (Chevalier achromat: convex crown + concave flint, Waterhouse stop) ----
BARREL = new_empty("LensBarrel", location=(0, -0.260, 0.0), parent=OUTER)
barrel_flange = new_cylinder("Barrel_Flange", 0.058, 0.014, (0, 0, 0), parent=BARREL,
                             material=MAT["brass"], rotation=(math.radians(90), 0, 0), verts=48)
barrel_tube = new_cylinder("Barrel_Tube", 0.038, 0.092, (0, -0.054, 0), parent=BARREL,
                           material=MAT["brass"], rotation=(math.radians(90), 0, 0), verts=48)
barrel_inner = new_cylinder("Barrel_Inner", 0.034, 0.088, (0, -0.054, 0), parent=BARREL,
                            material=MAT["barrel_inner_black"], rotation=(math.radians(90), 0, 0), verts=48)
# Front crown-glass convex element
front_cap = new_sphere_cap("LensElement_FrontConvex", 0.040, 0.012, (0, -0.100, 0),
                           parent=BARREL, material=MAT["glass"], rotation=(math.radians(-90), 0, 0))
set_extras(front_cap, {"desc_ja": "前玉:クラウンガラス凸レンズ。Chevalier アクロマートの集光要素。",
                       "desc_en": "Front crown-glass convex element of the Chevalier achromat."})
# Rear flint-glass concave meniscus (modeled as a thin flat disc with negative-curvature look)
rear_disc = new_cylinder("LensElement_RearMeniscus", 0.030, 0.005, (0, -0.078, 0),
                         parent=BARREL, material=MAT["glass"], rotation=(math.radians(90), 0, 0), verts=48)
set_extras(rear_disc, {"desc_ja": "後玉:フリントガラス凹メニスカス。色収差を補正する。",
                       "desc_en": "Rear flint-glass concave meniscus correcting chromatic aberration."})
# Waterhouse-style fixed stop (annulus) just behind the rear element
stop_outer = new_cylinder("LensStop_Disk", 0.034, 0.0012, (0, -0.072, 0),
                          parent=BARREL, material=MAT["brass_dark"], rotation=(math.radians(90), 0, 0), verts=48)
# Drill the central aperture: a hole via Boolean would be ideal but simpler: smaller bright cylinder on top
stop_hole = new_cylinder("LensStop_Aperture", 0.014, 0.0016, (0, -0.072, 0),
                          parent=BARREL, material=MAT["barrel_inner_black"], rotation=(math.radians(90), 0, 0), verts=32)
set_extras(stop_outer, {"desc_ja": "固定絞り (Waterhouse 型)。f/14 相当の開口。",
                       "desc_en": "Fixed Waterhouse-style stop providing the f/14 aperture."})

# Lens cap (rotates / pivots)
CAP_PIVOT = new_empty("LensCap_Pivot", location=(0, -0.098, 0.058), parent=BARREL)
lens_cap_body = new_cylinder("LensCap", 0.047, 0.011, (0, 0, -0.058), parent=CAP_PIVOT,
                             material=MAT["brass_dark"], rotation=(math.radians(90), 0, 0), verts=48)
lens_cap_knob = new_cylinder("LensCap_Knob", 0.008, 0.012, (0, 0.008, -0.058), parent=CAP_PIVOT,
                             material=MAT["brass"], rotation=(math.radians(90), 0, 0), verts=16)
set_extras(lens_cap_body, {"desc_ja": "真鍮レンズキャップ。回転式で機械シャッターを兼ねる(1839年仕様)。",
                          "desc_en": "Brass swivel lens cap doubling as the shutter (1839 spec)."})

# ---- Giroux maker's plate (engraved brass) ----
maker_plate = new_cube("MakersPlate", (0.140, 0.0015, 0.040), (0, -0.266, -0.110), parent=OUTER,
                      material=MAT["brass"], bevel=False)
maker_text_1 = text_mesh("MakerText_1", "DAGUERRÉOTYPE", size=0.0075, extrude=0.0006,
                         location=(0, -0.2665, -0.103), rotation=(math.radians(90), 0, 0),
                         parent=OUTER, material=MAT["brass_dark"])
maker_text_2 = text_mesh("MakerText_2", "ALPHONSE GIROUX ET CIE", size=0.0058, extrude=0.0006,
                         location=(0, -0.2665, -0.112), rotation=(math.radians(90), 0, 0),
                         parent=OUTER, material=MAT["brass_dark"])
maker_text_3 = text_mesh("MakerText_3", "RUE DU COQ-ST-HONORÉ · PARIS", size=0.0045, extrude=0.0006,
                         location=(0, -0.2665, -0.119), rotation=(math.radians(90), 0, 0),
                         parent=OUTER, material=MAT["brass_dark"])
set_extras(maker_plate, {
    "desc_ja": "Giroux 製造銘板。住所「Rue du Coq-Saint-Honoré, No.7 à Paris」が刻まれる。",
    "desc_en": "Giroux maker's plate engraved with the Paris workshop address.",
})

# ---- Daguerre red wax anti-forgery seal ----
seal_base = new_cylinder("DaguerreSeal_Base", 0.018, 0.002, (0.095, -0.266, -0.110), parent=OUTER,
                         material=MAT["seal_red"], rotation=(math.radians(90), 0, 0), verts=32)
seal_text = text_mesh("DaguerreSeal_Text", "L.J.M.D.", size=0.0045, extrude=0.0004,
                      location=(0.095, -0.2675, -0.110), rotation=(math.radians(90), 0, 0),
                      parent=OUTER, material=MAT["seal_text"])
set_extras(seal_base, {
    "desc_ja": "Daguerre の赤蝋封印。Giroux 製を Daguerre 本人が認証した『公式機』の証であり、反偽造のため貼付された。",
    "desc_en": "Daguerre's red wax anti-forgery seal authenticating the genuine Giroux unit.",
})

# ---- Inner box (sliding focus) ----
INNER = new_empty("InnerBox", parent=ROOT)
inner_body = new_cube("InnerBox_Body", (0.290, 0.250, 0.290), (0, 0.135, 0.0), parent=INNER, material=MAT["mahogany2"])
set_extras(inner_body, {"desc_ja": "内箱。外箱内部を前後に摺動して焦点を合わせる。",
                       "desc_en": "Inner box that slides front-back within the outer box to focus."})
# Brass guide pegs on inner box sides (cosmetic)
for sx in (-0.137, 0.137):
    for sy in (0.05, 0.20):
        brass_screw(f"Inner_GuidePeg_{sx:+.2f}_{sy:+.2f}", (sx, sy, 0.140), parent=INNER)

# Ground-glass focusing screen with brass-edged frame
GG = new_empty("GroundGlass_Anchor", location=(0, 0.262, 0.0), parent=INNER)
gg_frame_top = new_cube("GG_Frame_Top", (0.235, 0.005, 0.012), (0, 0, 0.090), parent=GG, material=MAT["mahogany2"])
gg_frame_bot = new_cube("GG_Frame_Bot", (0.235, 0.005, 0.012), (0, 0, -0.090), parent=GG, material=MAT["mahogany2"])
gg_frame_lf  = new_cube("GG_Frame_L",   (0.012, 0.005, 0.190), (-0.115, 0, 0),  parent=GG, material=MAT["mahogany2"])
gg_frame_rt  = new_cube("GG_Frame_R",   (0.012, 0.005, 0.190), ( 0.115, 0, 0),  parent=GG, material=MAT["mahogany2"])
ground_glass = new_cube("GroundGlass", (0.220, 0.003, 0.170), (0, 0, 0), parent=GG, material=MAT["ground_glass"], bevel=False)
set_extras(ground_glass, {
    "desc_ja": "スリ硝子焦点板。倒立像をここで確認し、構図/ピントが決まったらホルダーに差し替える。",
    "desc_en": "Ground-glass focusing screen; image is composed, then swapped for the plate holder.",
})

# Plate holder (off-camera initially)
HOLDER = new_empty("PlateHolder", location=(0.5, 0.262, 0.0), parent=ROOT)
holder_frame = new_cube("HolderFrame", (0.232, 0.020, 0.182), (0, 0, 0), parent=HOLDER, material=MAT["mahogany"])
holder_rim = new_cube("HolderFrame_Rim", (0.232, 0.005, 0.022), (0, 0.010, 0.092), parent=HOLDER, material=MAT["brass"])
set_extras(holder_frame, {
    "desc_ja": "プレートホルダー枠。銀板とダークスライドを保持する木製アセンブリ。",
    "desc_en": "Plate holder frame — wooden assembly carrying silver plate and dark slide.",
})

DARKSLIDE_ANCHOR = new_empty("DarkSlide_Anchor", location=(0, 0, 0), parent=HOLDER)
dark_slide = new_cube("DarkSlide", (0.220, 0.0035, 0.180), (0, 0.005, 0), parent=DARKSLIDE_ANCHOR, material=MAT["darkslide"])
ds_handle = new_cube("DarkSlide_Handle", (0.040, 0.008, 0.008), (0, 0.008, 0.094),
                     parent=DARKSLIDE_ANCHOR, material=MAT["brass_dark"])
set_extras(dark_slide, {
    "desc_ja": "ダークスライド。露光時のみ引き抜き、再挿入して感光板を遮光する。",
    "desc_en": "Dark slide — pulled out only for exposure, then reinserted to shield the plate.",
})

def make_plate(name, mat, parent):
    return new_cube(name, (0.216, 0.0015, 0.165), (0, -0.005, 0), parent=parent, material=mat, bevel=False)

plate_polished = make_plate("SilverPlate_Polished", MAT["silver_polished"], HOLDER)
plate_iodized  = make_plate("SilverPlate_Iodized",  MAT["silver_iodized"],  HOLDER)
plate_developed= make_plate("SilverPlate_Developed",MAT["silver_developed"],HOLDER)
plate_fixed    = make_plate("SilverPlate_Fixed",    MAT["boulevard_plate"], HOLDER)
set_extras(plate_polished, {"desc_ja": "銀メッキ銅板(研磨済み)。鏡面で均一感光を実現。",
                            "desc_en": "Polished silver-on-copper plate; mirror finish ensures even sensitization."})
set_extras(plate_iodized,  {"desc_ja": "ヨウ素感光後の板。淡黄色のヨウ化銀(AgI)層が光に感じる。",
                            "desc_en": "Plate after iodine sensitization; pale-yellow AgI layer is light-sensitive."})
set_extras(plate_developed,{"desc_ja": "水銀蒸気現像後。露光部に Hg-Ag アマルガムが沈着し像が顕れる。",
                            "desc_en": "After mercury-vapor development; Hg-Ag amalgam reveals the image."})
set_extras(plate_fixed,    {"desc_ja": "定着完了。残留 AgI 除去で像が安定。テクスチャは Daguerre《Boulevard du Temple》(1838)。",
                            "desc_en": "Fixed plate; texture: Daguerre's 'Boulevard du Temple' (1838) — first photo with people."})
for p in (plate_iodized, plate_developed, plate_fixed):
    p.scale = (0, 0, 0)

# ---- Tripod (3 legs + top) ----
TRIPOD = new_empty("Tripod", parent=ROOT)
tripod_top = new_cylinder("Tripod_Top", 0.090, 0.022, (0, 0, -0.170), parent=TRIPOD, material=MAT["tripod"])
for i, ang in enumerate((0, 120, 240)):
    rad = math.radians(ang)
    leg = new_cylinder(f"Tripod_Leg{i+1}", 0.014, 0.85,
                       (0.07 * math.cos(rad), 0.07 * math.sin(rad), -0.600),
                       parent=TRIPOD, material=MAT["tripod"],
                       rotation=(math.radians(13) * math.cos(rad + math.pi / 2),
                                 math.radians(13) * math.sin(rad + math.pi / 2), 0), verts=12)

# ---- Optical-rays visualization (hidden) ----
RAYS = new_empty("OpticalRays", parent=ROOT)
RAYS.scale = (0, 0, 0)
bpy.ops.mesh.primitive_cone_add(radius1=0.20, radius2=0.030, depth=0.6,
                                location=(0, -0.6, 0.05), rotation=(math.radians(-90), 0, 0), vertices=24)
incoming = bpy.context.active_object; incoming.name = "IncomingCone"
incoming.parent = RAYS; incoming.data.materials.append(MAT["ray"])
bpy.ops.mesh.primitive_cone_add(radius1=0.030, radius2=0.130, depth=0.52,
                                location=(0, 0.0, 0.0), rotation=(math.radians(-90), 0, 0), vertices=24)
refracted = bpy.context.active_object; refracted.name = "RefractedCone"
refracted.parent = RAYS; refracted.data.materials.append(MAT["ray"])
proj = new_cube("ProjectedImagePlane", (0.220, 0.002, 0.170), (0, 0.260, 0.0), parent=RAYS,
                material=MAT["boulevard_proj"], rotation=(0, math.radians(180), math.radians(180)), bevel=False)
set_extras(proj, {"desc_ja": "焦点面に結ぶ倒立像。スリ硝子上で確認される。",
                  "desc_en": "Inverted image at the focal plane, visible on the ground glass."})

# ---- Chemistry station ----
CHEM = new_empty("ChemStation", location=(0.9, 0, -0.165), parent=ROOT)
iodine_box = new_cube("IodineBox", (0.25, 0.20, 0.10), (-0.30, 0, 0.05), parent=CHEM, material=MAT["iodine_box"])
iodine_text = text_mesh("IodineBox_Label", "Iode", size=0.018, extrude=0.0005,
                        location=(-0.30, 0, 0.105), rotation=(0, 0, 0), parent=CHEM, material=MAT["brass_dark"])
iodine_vap = new_cube("IodineVapor", (0.22, 0.18, 0.04), (-0.30, 0, 0.085), parent=CHEM,
                       material=MAT["iodine_vap"], bevel=False)
iodine_vap.scale = (0, 0, 0)
set_extras(iodine_box, {"desc_ja": "ヨウ素感光箱。底に置いたヨウ素結晶の蒸気で板表面に AgI 層を形成する。",
                       "desc_en": "Iodine sensitizing box; iodine crystal vapor forms AgI on the plate."})

hg_box = new_cube("MercuryBox", (0.25, 0.20, 0.12), (0, 0, 0.06), parent=CHEM, material=MAT["hg_box"])
hg_pool = new_cube("MercuryPool", (0.22, 0.18, 0.01), (0, 0, 0.115), parent=CHEM, material=MAT["mercury"], bevel=False)
hg_lamp = new_cylinder("MercuryBox_Lamp", 0.022, 0.040, (0, -0.085, 0.015), parent=CHEM, material=MAT["brass"])
set_extras(hg_box, {"desc_ja": "水銀現像箱。下部のアルコールランプで水銀を約60℃に加熱、蒸気で潜像を顕在化。",
                   "desc_en": "Mercury developing box; spirit lamp heats Hg to ~60°C, vapor reveals the latent image."})

fix_tray = new_cube("FixingTray", (0.30, 0.22, 0.04), (0.32, 0, 0.02), parent=CHEM, material=MAT["iron"])
fix_water = new_cube("FixingBath", (0.28, 0.20, 0.025), (0.32, 0, 0.035), parent=CHEM, material=MAT["fix_water"], bevel=False)
set_extras(fix_tray, {"desc_ja": "定着トレイ。食塩水(初期)→チオ硫酸ナトリウム(Herschel, 1839末)で残留 AgI を除去。",
                     "desc_en": "Fixing tray; salt brine (early) → hyposulfite of soda (Herschel, late 1839)."})

# ============================================================
# Annotations — compute world positions BEFORE animations are added
# ============================================================
bpy.context.view_layer.update()

ANNOTATIONS_DEF = [
    ("outer_box", outer_body, (0, -0.13, 0.16),
     "外箱(マホガニー)。前面にレンズボードを保持し、内箱を摺動可能に受ける二重木箱構造の外側半分。",
     "Outer mahogany box. Holds the lens board and slidingly receives the inner box.",
     ["Gernsheim 1969 pp.65-72", "George Eastman Museum object record"], None, None),
    ("lens_assembly", BARREL, (0, -0.10, 0),
     "Chevalier 製アクロマート(凸クラウン+凹フリント)。FL≈380mm、f/14。1839年Giroux付属仕様。",
     "Chevalier achromatic doublet (convex crown + concave flint), FL≈380mm, f/14.",
     ["Eder 1945 §VI", "Pohl 1854 retrospective"], None, None),
    ("waterhouse_stop", stop_outer, (0, 0, 0.02),
     "固定絞り(Waterhouse 型)。f/14 相当の開口で、当時としては相対的に大きな絞り値だが感光板の鈍さを補う。",
     "Fixed Waterhouse-style stop giving f/14 — relatively slow but the period's plates demanded it.",
     [], None, None),
    ("lens_cap", lens_cap_body, (0, 0, 0.05),
     "真鍮スイベル式キャップ。機械式シャッターが無い1839年は、これを手で回して開閉するのが「露光」だった。",
     "Brass swivel cap — the only shutter in 1839; manually rotated to open/close the exposure.",
     [], None, None),
    ("makers_plate", maker_plate, (0, 0, 0),
     "Giroux 製造銘板。「Daguerréotype / Alphonse Giroux et Cie / Rue du Coq-Saint-Honoré No.7 à Paris」が刻印される。",
     "Giroux maker's plate engraved with the Paris workshop address.",
     ["George Eastman Museum collection record"], None, None),
    ("daguerre_seal", seal_base, (0, 0, 0),
     "Daguerre の赤蝋封印。Giroux 製を Daguerre 本人が認証した『公式機』の印で、反偽造の役割を果たした。",
     "Daguerre's red wax anti-forgery seal authenticating the genuine Giroux unit.",
     ["Buerger 1989 ch.2"], None, None),
    ("inner_box", inner_body, (0, 0, 0.15),
     "内箱。外箱内を前後にスライドさせて焦点を合わせる。レンズ-像距離 ≈ FL(無限遠時)。",
     "Inner sliding box used for focusing (image distance ≈ FL at infinity).",
     [], None, None),
    ("ground_glass", ground_glass, (0, 0.005, 0),
     "スリ硝子焦点板。倒立像を結像させて構図とピントを確認した後、ホルダーに差し替える。",
     "Ground-glass focusing screen for composition; swapped with the plate holder before exposure.",
     [], None, None),
    ("plate_holder", holder_frame, (0, 0.02, 0),
     "プレートホルダー。研磨済み銀板を差し込み、ダークスライドで遮光して運搬する木製アセンブリ。",
     "Plate holder; wooden assembly carrying the polished silver plate behind a dark slide.",
     [], None, None),
    ("dark_slide", dark_slide, (0, 0.01, 0.08),
     "ダークスライド。露光時のみ引き抜き、再挿入して感光板を遮光する。",
     "Dark slide — withdrawn only during exposure to admit light to the plate.",
     [], None, None),
    ("silver_plate", plate_polished, (0, 0, 0),
     "銀メッキ銅板。研磨 → ヨウ素感光 → 露光 → 水銀現像 → 定着の5工程を経て1点物の銀像写真となる。",
     "Silver-on-copper plate; undergoes polish → iodine → expose → mercury develop → fix.",
     [], None, None),
    ("iodine_box", iodine_box, (0, 0, 0.10),
     "ヨウ素感光箱。底のヨウ素結晶からの蒸気で板表面に AgI 層を生成。",
     "Iodine sensitizing box; iodine crystal vapor forms an AgI layer on the plate surface.",
     [], "2 Ag(s) + I₂(g) → 2 AgI(s)", "ヨウ素蒸気は粘膜刺激性。換気必須。"),
    ("mercury_box", hg_box, (0, 0, 0.12),
     "水銀現像箱。アルコールランプで水銀を約60℃に加熱、蒸気で潜像を顕在化する。",
     "Mercury developing box; spirit lamp heats Hg to ~60°C; vapor reveals the latent image.",
     [], "Hg(g) + Ag⁰(露光部) → Hg·Ag アマルガム",
     "⚠ 水銀蒸気は強力な中枢神経毒。19世紀のダゲレオタイピストには水銀中毒の事例が多数報告。現代では絶対に再現してはならない。"),
    ("fix_tray", fix_tray, (0, 0, 0.05),
     "定着トレイ。当初は食塩水、Herschel の提案(1839末)以降はチオ硫酸ナトリウムで未反応 AgI を除去。",
     "Fixing tray; salt brine (early) → hyposulfite of soda (Herschel, late 1839) removes unreacted AgI.",
     [], "AgI + 2 Na₂S₂O₃ → Na₃[Ag(S₂O₃)₂] + NaI",
     "チオ硫酸ナトリウムは比較的安全だが、酸と混合すると SO₂ を発生する。"),
    ("tripod", TRIPOD, (0, 0, -0.15),
     "三脚。長時間露光に必須の固定要素。当時は重い専用木製三脚が用いられた。",
     "Wooden tripod — essential for the multi-minute exposures of the era.",
     [], None, None),
]

# Compute world positions by manually accumulating parent chain (independent
# of any later animation; matrix_world can be unreliable for objects modified
# by later ops that mutate selection).
def compute_world_pos(obj):
    pos = Vector((0, 0, 0))
    cur = obj
    while cur is not None:
        pos = pos + Vector(cur.location)
        cur = cur.parent
    return pos

PRE_ANN = []
for (aid, target, offset, ja, en, srcs, chem, safety) in ANNOTATIONS_DEF:
    base = compute_world_pos(target)
    pos_blender = [base.x + offset[0], base.y + offset[1], base.z + offset[2]]
    # Convert from Blender Z-up (X right, Y forward, Z up) to glTF Y-up
    # (X right, Y up, Z back): (Xb, Yb, Zb) -> (Xb, Zb, -Yb).
    pos_gltf = [pos_blender[0], pos_blender[2], -pos_blender[1]]
    PRE_ANN.append({"id": aid, "position": pos_gltf, "ja": ja, "en": en,
                    "sources": srcs, "chemistry": chem, "safety": safety})

# ============================================================
# Animations (16 clips, identical to v1 structure)
# ============================================================

REST = {}
def store_rest(obj):
    return {"loc": tuple(obj.location), "rot": tuple(obj.rotation_euler), "scl": tuple(obj.scale)}

ANIMATED_REFS = [OUTER, INNER, BARREL, CAP_PIVOT, GG, HOLDER, DARKSLIDE_ANCHOR,
                 front_cap, rear_disc, lens_cap_body, ground_glass, holder_frame, dark_slide,
                 plate_polished, plate_iodized, plate_developed, plate_fixed,
                 RAYS, incoming, refracted, proj, iodine_vap, ROOT]
for o in set(ANIMATED_REFS):
    REST[o.name] = store_rest(o)

CLIPS = []
def new_clip(name, length_seconds):
    fps = scn.render.fps
    length_frames = max(1, int(round(length_seconds * fps)))
    start = 1 if not CLIPS else CLIPS[-1][2] + 5
    end = start + length_frames
    CLIPS.append((name, start, end))
    if end > scn.frame_end: scn.frame_end = end + 30
    return start, end


def get_or_create_action(obj, clip_name):
    action_name = f"{obj.name}|{clip_name}"
    act = bpy.data.actions.get(action_name) or bpy.data.actions.new(action_name)
    if not obj.animation_data: obj.animation_data_create()
    obj.animation_data.action = act
    return act


def key(obj, frame, loc=None, rot=None, scl=None):
    if loc is not None:
        obj.location = loc; obj.keyframe_insert("location", frame=frame)
    if rot is not None:
        obj.rotation_euler = rot; obj.keyframe_insert("rotation_euler", frame=frame)
    if scl is not None:
        obj.scale = scl; obj.keyframe_insert("scale", frame=frame)


def restore_rest(obj):
    r = REST.get(obj.name)
    if r is None:
        REST[obj.name] = store_rest(obj); return
    obj.location = r["loc"]; obj.rotation_euler = r["rot"]; obj.scale = r["scl"]


def push_clip_to_nla(clip_name, objs):
    for obj in objs:
        if not obj.animation_data or not obj.animation_data.action: continue
        act = obj.animation_data.action
        track = obj.animation_data.nla_tracks.new()
        track.name = clip_name
        track.strips.new(clip_name, int(act.frame_range[0]), act)
        obj.animation_data.action = None


def end_clip(name, objs):
    push_clip_to_nla(name, objs)
    for obj in objs: restore_rest(obj)


# 00_Idle
s, e = new_clip("00_Idle", 0.1)
get_or_create_action(ROOT, "00_Idle")
key(ROOT, s, loc=tuple(ROOT.location)); key(ROOT, e, loc=tuple(ROOT.location))
end_clip("00_Idle", [ROOT])

# 10_Explode
s, e = new_clip("10_Explode", 2.0)
explode_objs = [OUTER, INNER, BARREL, CAP_PIVOT, GG, HOLDER, front_cap, rear_disc, lens_cap_body, dark_slide]
explode_targets = {
    OUTER: (0, -0.25, 0), INNER: (0, 0.25, 0), BARREL: (0, -0.20, 0), CAP_PIVOT: (0, -0.10, 0),
    GG: (0, 0.20, 0.25), HOLDER: (0, 0.45, -0.10),
    front_cap: (0, -0.10, 0.10), rear_disc: (0, 0.05, 0.10), lens_cap_body: (0, -0.10, 0.10),
    dark_slide: (0, 0, 0.30),
}
for obj in explode_objs:
    get_or_create_action(obj, "10_Explode")
    rest = REST[obj.name]["loc"]; tgt = explode_targets[obj]
    key(obj, s, loc=rest)
    key(obj, e, loc=(rest[0]+tgt[0], rest[1]+tgt[1], rest[2]+tgt[2]))
end_clip("10_Explode", explode_objs)

# 11_Reassemble
s, e = new_clip("11_Reassemble", 2.0)
for obj in explode_objs:
    get_or_create_action(obj, "11_Reassemble")
    rest = REST[obj.name]["loc"]; tgt = explode_targets[obj]
    key(obj, s, loc=(rest[0]+tgt[0], rest[1]+tgt[1], rest[2]+tgt[2]))
    key(obj, e, loc=rest)
end_clip("11_Reassemble", explode_objs)

# 20 / 21 optical path
for nm, sv, ev in [("20_OpticalPath_Show", (0,0,0), (1,1,1)), ("21_OpticalPath_Hide", (1,1,1), (0,0,0))]:
    s, e = new_clip(nm, 1.5 if nm.startswith("20") else 1.0)
    get_or_create_action(RAYS, nm); key(RAYS, s, scl=sv); key(RAYS, e, scl=ev)
    end_clip(nm, [RAYS])

# 30 InsertHolder
s, e = new_clip("30_Workflow_InsertHolder", 2.0)
gg_rest = REST[GG.name]["loc"]; h_rest = REST[HOLDER.name]["loc"]
get_or_create_action(GG, "30_Workflow_InsertHolder")
key(GG, s, loc=gg_rest)
key(GG, (s+e)//2, loc=(gg_rest[0], gg_rest[1], gg_rest[2]+0.30))
key(GG, e, loc=(gg_rest[0], gg_rest[1]+0.35, gg_rest[2]+0.30))
get_or_create_action(HOLDER, "30_Workflow_InsertHolder")
key(HOLDER, s, loc=h_rest); key(HOLDER, e, loc=(0, 0.262, 0.0))
end_clip("30_Workflow_InsertHolder", [GG, HOLDER])

# 31 PullDarkSlide
s, e = new_clip("31_Workflow_PullDarkSlide", 1.0)
get_or_create_action(DARKSLIDE_ANCHOR, "31_Workflow_PullDarkSlide")
key(DARKSLIDE_ANCHOR, s, loc=(0, 0, 0)); key(DARKSLIDE_ANCHOR, e, loc=(0, 0, 0.22))
end_clip("31_Workflow_PullDarkSlide", [DARKSLIDE_ANCHOR])

# 32 RemoveCap
rest_rot = REST[CAP_PIVOT.name]["rot"]
s, e = new_clip("32_Workflow_RemoveCap", 0.8)
get_or_create_action(CAP_PIVOT, "32_Workflow_RemoveCap")
key(CAP_PIVOT, s, rot=rest_rot)
key(CAP_PIVOT, e, rot=(rest_rot[0]-math.radians(95), rest_rot[1], rest_rot[2]))
end_clip("32_Workflow_RemoveCap", [CAP_PIVOT])

# 33 Expose
s, e = new_clip("33_Workflow_Expose", 3.0)
get_or_create_action(RAYS, "33_Workflow_Expose")
key(RAYS, s, scl=(1,1,1)); key(RAYS, (s+e)//2, scl=(1.05,1.05,1.05)); key(RAYS, e, scl=(1,1,1))
end_clip("33_Workflow_Expose", [RAYS])

# 34 ReplaceCap
s, e = new_clip("34_Workflow_ReplaceCap", 0.8)
get_or_create_action(CAP_PIVOT, "34_Workflow_ReplaceCap")
key(CAP_PIVOT, s, rot=(rest_rot[0]-math.radians(95), rest_rot[1], rest_rot[2]))
key(CAP_PIVOT, e, rot=rest_rot)
end_clip("34_Workflow_ReplaceCap", [CAP_PIVOT])

# 35 PushDarkSlide
s, e = new_clip("35_Workflow_PushDarkSlide", 1.0)
get_or_create_action(DARKSLIDE_ANCHOR, "35_Workflow_PushDarkSlide")
key(DARKSLIDE_ANCHOR, s, loc=(0, 0, 0.22)); key(DARKSLIDE_ANCHOR, e, loc=(0, 0, 0))
end_clip("35_Workflow_PushDarkSlide", [DARKSLIDE_ANCHOR])

# 36 RemoveHolder
s, e = new_clip("36_Workflow_RemoveHolder", 2.0)
get_or_create_action(HOLDER, "36_Workflow_RemoveHolder")
key(HOLDER, s, loc=(0, 0.262, 0.0)); key(HOLDER, e, loc=REST[HOLDER.name]["loc"])
get_or_create_action(GG, "36_Workflow_RemoveHolder")
key(GG, s, loc=(gg_rest[0], gg_rest[1]+0.35, gg_rest[2]+0.30))
key(GG, (s+e)//2, loc=(gg_rest[0], gg_rest[1], gg_rest[2]+0.30))
key(GG, e, loc=gg_rest)
end_clip("36_Workflow_RemoveHolder", [HOLDER, GG])

# 40 Chem_Polish
s, e = new_clip("40_Chem_Polish", 1.5)
get_or_create_action(plate_polished, "40_Chem_Polish")
key(plate_polished, s, scl=(1,1,1)); key(plate_polished, (s+e)//2, scl=(1.02,1,1.02)); key(plate_polished, e, scl=(1,1,1))
end_clip("40_Chem_Polish", [plate_polished])

# 41 Chem_Iodize
s, e = new_clip("41_Chem_Iodize", 2.0)
get_or_create_action(HOLDER, "41_Chem_Iodize")
key(HOLDER, s, loc=REST[HOLDER.name]["loc"]); key(HOLDER, e, loc=(0.6, 0, -0.10))
get_or_create_action(plate_polished, "41_Chem_Iodize")
key(plate_polished, s, scl=(1,1,1)); key(plate_polished, (s+e)*2//3, scl=(1,1,1)); key(plate_polished, e, scl=(0,0,0))
get_or_create_action(plate_iodized, "41_Chem_Iodize")
key(plate_iodized, s, scl=(0,0,0)); key(plate_iodized, (s+e)*2//3, scl=(0,0,0)); key(plate_iodized, e, scl=(1,1,1))
get_or_create_action(iodine_vap, "41_Chem_Iodize")
key(iodine_vap, s, scl=(0,0,0)); key(iodine_vap, (s+e)//2, scl=(1,1,1)); key(iodine_vap, e, scl=(0.6,1,0.6))
end_clip("41_Chem_Iodize", [HOLDER, plate_polished, plate_iodized, iodine_vap])
REST[plate_polished.name]["scl"] = (0,0,0); REST[plate_iodized.name]["scl"] = (1,1,1)
REST[HOLDER.name]["loc"] = (0.6, 0, -0.10)

# 42 Chem_Develop_Hg
s, e = new_clip("42_Chem_Develop_Hg", 3.0)
get_or_create_action(HOLDER, "42_Chem_Develop_Hg")
key(HOLDER, s, loc=(0.6, 0, -0.10)); key(HOLDER, e, loc=(0.9, 0, -0.05))
get_or_create_action(plate_iodized, "42_Chem_Develop_Hg")
key(plate_iodized, s, scl=(1,1,1)); key(plate_iodized, (s+e)*2//3, scl=(1,1,1)); key(plate_iodized, e, scl=(0,0,0))
get_or_create_action(plate_developed, "42_Chem_Develop_Hg")
key(plate_developed, s, scl=(0,0,0)); key(plate_developed, (s+e)//2, scl=(0,0,0)); key(plate_developed, e, scl=(1,1,1))
end_clip("42_Chem_Develop_Hg", [HOLDER, plate_iodized, plate_developed])
REST[plate_iodized.name]["scl"] = (0,0,0); REST[plate_developed.name]["scl"] = (1,1,1)
REST[HOLDER.name]["loc"] = (0.9, 0, -0.05)

# 43 Chem_Fix
s, e = new_clip("43_Chem_Fix", 2.0)
get_or_create_action(HOLDER, "43_Chem_Fix")
key(HOLDER, s, loc=(0.9, 0, -0.05)); key(HOLDER, e, loc=(1.22, 0, -0.10))
get_or_create_action(plate_developed, "43_Chem_Fix")
key(plate_developed, s, scl=(1,1,1)); key(plate_developed, (s+e)//2, scl=(1,1,1)); key(plate_developed, e, scl=(0,0,0))
get_or_create_action(plate_fixed, "43_Chem_Fix")
key(plate_fixed, s, scl=(0,0,0)); key(plate_fixed, (s+e)//2, scl=(0,0,0)); key(plate_fixed, e, scl=(1,1,1))
end_clip("43_Chem_Fix", [HOLDER, plate_developed, plate_fixed])
REST[plate_developed.name]["scl"] = (0,0,0); REST[plate_fixed.name]["scl"] = (1,1,1)
REST[HOLDER.name]["loc"] = (1.22, 0, -0.10)

# 44 Chem_Reveal
s, e = new_clip("44_Chem_Reveal", 1.5)
get_or_create_action(plate_fixed, "44_Chem_Reveal")
key(plate_fixed, s, scl=(1,1,1)); key(plate_fixed, (s+e)//2, scl=(1.10,1.0,1.10)); key(plate_fixed, e, scl=(1,1,1))
end_clip("44_Chem_Reveal", [plate_fixed])

# ============================================================
# Camera & light (preview)
# ============================================================
bpy.ops.object.camera_add(location=(1.2, -1.4, 0.7), rotation=(math.radians(70), 0, math.radians(40)))
cam = bpy.context.active_object; cam.name = "PreviewCamera"; scn.camera = cam
bpy.ops.object.light_add(type='SUN', location=(2, -2, 4)); bpy.context.active_object.data.energy = 3.0
world = bpy.data.worlds.new("World") if not bpy.data.worlds else bpy.data.worlds[0]
scn.world = world; world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.05, 0.06, 0.08, 1.0); bg.inputs[1].default_value = 1.0

# Reset to rest pose at frame 1
for name, rest in REST.items():
    obj = bpy.data.objects.get(name)
    if obj:
        obj.location = rest["loc"]; obj.rotation_euler = rest["rot"]
plate_polished.scale = (1,1,1); plate_iodized.scale = (0,0,0)
plate_developed.scale = (0,0,0); plate_fixed.scale = (0,0,0)
HOLDER.location = (0.5, 0.262, 0.0); RAYS.scale = (0,0,0); iodine_vap.scale = (0,0,0)
scn.frame_set(1)

# ============================================================
# Annotations write
# ============================================================
ann_path = os.path.join(out_dir, "annotations.json")
with open(ann_path, "w", encoding="utf-8") as f:
    json.dump({
        "asset": ASSET_NAME,
        "title_ja": "Giroux ダゲレオタイプ・カメラ (1839)",
        "title_en": "Giroux Daguerreotype Camera (1839)",
        "clips": [{"name": n, "frame_start": s, "frame_end": e} for n, s, e in CLIPS],
        "annotations": PRE_ANN,
    }, f, ensure_ascii=False, indent=2)
print(f"[ok] annotations -> {ann_path}")

# ============================================================
# Export
# ============================================================
blend_path = os.path.join(out_dir, f"{ASSET_NAME}.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print(f"[ok] saved {blend_path}")

glb_path = os.path.join(out_dir, f"{ASSET_NAME}.glb")
bpy.ops.object.select_all(action='SELECT')
try:
    bpy.ops.export_scene.gltf(
        filepath=glb_path, export_format='GLB',
        export_animations=True, export_animation_mode='NLA_TRACKS',
        export_extras=True, export_apply=True, export_yup=True,
        use_selection=False,
    )
except TypeError:
    bpy.ops.export_scene.gltf(filepath=glb_path, export_format='GLB',
                              export_animations=True, export_extras=True)
print(f"[ok] exported {glb_path}")

usdz_path = os.path.join(out_dir, f"{ASSET_NAME}.usdz")
try:
    bpy.ops.wm.usd_export(
        filepath=usdz_path, export_animation=True,
        export_textures_mode='NEW', export_materials=True,
        selected_objects_only=False, export_custom_properties=True,
    )
    print(f"[ok] exported {usdz_path}")
except Exception as ex:
    print(f"[warn] usdz export failed: {ex}")

print("[done] v2 build complete:", out_dir)
