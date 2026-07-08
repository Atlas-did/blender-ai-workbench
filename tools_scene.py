"""
tools_scene.py — 场景编辑工具
==============================
更多 Blender 场景操作工具：创建对象、修改材质、设置渲染等。
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def create_primitive(primitive_type: str = "cube", location=(0, 0, 0), name: str = "") -> dict:
    """创建基础几何体。"""
    import bpy

    ops_map = {
        "cube": bpy.ops.mesh.primitive_cube_add,
        "sphere": bpy.ops.mesh.primitive_uv_sphere_add,
        "cylinder": bpy.ops.mesh.primitive_cylinder_add,
        "cone": bpy.ops.mesh.primitive_cone_add,
        "plane": bpy.ops.mesh.primitive_plane_add,
        "torus": bpy.ops.mesh.primitive_torus_add,
        "monkey": bpy.ops.mesh.primitive_monkey_add,
        "ico_sphere": bpy.ops.mesh.primitive_ico_sphere_add,
        "grid": bpy.ops.mesh.primitive_grid_add,
        "circle": bpy.ops.mesh.primitive_circle_add,
    }

    op = ops_map.get(primitive_type.lower())
    if op is None:
        return {"error": f"不支持的几何体类型: {primitive_type}，支持: {list(ops_map.keys())}"}

    try:
        op(location=location)
        obj = bpy.context.active_object
        if obj and name:
            obj.name = name
        return {"created": primitive_type, "name": obj.name if obj else "(未知)", "location": location}
    except Exception as exc:
        return {"error": f"创建几何体失败: {exc}"}


def delete_object(name: str) -> dict:
    """删除指定对象。"""
    import bpy
    obj = bpy.data.objects.get(name)
    if obj is None:
        return {"error": f"未找到对象: {name}"}

    obj_type = obj.type
    data = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if data and data.users == 0 and hasattr(data, "name"):
        try:
            bpy.data.meshes.remove(data)
        except Exception:
            pass
    return {"deleted": name, "type": obj_type}


def rename_object(old_name: str, new_name: str) -> dict:
    """重命名对象。"""
    import bpy
    obj = bpy.data.objects.get(old_name)
    if obj is None:
        return {"error": f"未找到对象: {old_name}"}
    obj.name = new_name
    return {"old_name": old_name, "new_name": new_name}


def assign_material(object_name: str, color=(1, 0.5, 0.5, 1)) -> dict:
    """给对象分配新材质。"""
    import bpy
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        return {"error": f"未找到对象: {object_name}"}
    if not hasattr(obj, "data") or not hasattr(obj.data, "materials"):
        return {"error": f"对象 {object_name} 不支持材质"}

    mat = bpy.data.materials.new(name=f"{object_name}_material")
    mat.diffuse_color = color[:4]
    mat.use_nodes = True

    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

    return {"object": object_name, "material": mat.name, "color": color[:4]}


def set_render_engine(engine: str) -> dict:
    """设置渲染引擎。"""
    import bpy
    valid = {"CYCLES", "BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "BLENDER_WORKBENCH", "EEVEE"}
    requested = engine.upper()

    # EEVEE 兼容
    if requested == "EEVEE":
        available = {
            item.identifier
            for item in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items
        }
        if "BLENDER_EEVEE_NEXT" in available:
            requested = "BLENDER_EEVEE_NEXT"
        elif "BLENDER_EEVEE" in available:
            requested = "BLENDER_EEVEE"

    if requested not in valid:
        return {"error": f"不支持的渲染引擎: {engine}，支持: {list(valid)}"}

    bpy.context.scene.render.engine = requested
    return {"render_engine": requested}


def set_render_resolution(width: int = 1920, height: int = 1080) -> dict:
    """设置渲染分辨率。"""
    import bpy
    scene = bpy.context.scene
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    return {"resolution": [width, height]}
