"""
tools_scene.py — 场景编辑工具
==============================
更多 Blender 场景操作工具：创建对象、修改材质、设置渲染等。
"""
    requested = engine.upper()

    # Blender 版本之间 EEVEE 的枚举名不同：
    # - 旧版: BLENDER_EEVEE
    # - 新版: BLENDER_EEVEE_NEXT
    # 用户输入 "EEVEE" 时做自动兼容。
    available = {
        item.identifier
        for item in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items
    }

    alias_candidates = {
        "EEVEE": ["BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"],
        "WORKBENCH": ["BLENDER_WORKBENCH"],
    }

    if requested in available:
        resolved = requested
    else:
        resolved = ""
        for candidate in alias_candidates.get(requested, []):
            if candidate in available:
                resolved = candidate
                break

    if not resolved:
        return {"error": f"不支持的渲染引擎: {engine}，当前可用: {sorted(available)}"}

    bpy.context.scene.render.engine = resolved
    return {"render_engine": resolved}


# ---------------------------------------------------------------------------
# 对象创建
# ---------------------------------------------------------------------------

def create_primitive(primitive_type: str = "cube", location: tuple = (0, 0, 0), name: str = "") -> dict:
    """创建基础几何体。

    Args:
        primitive_type: 几何体类型 — cube, sphere, cylinder, cone, plane, torus, monkey
        location: (x, y, z) 位置
        name: 对象名称（可选）

    Returns:
        创建结果 dict。
    """
    import bpy

    type_map = {
        "cube": "mesh.primitive_cube_add",
        "sphere": "mesh.primitive_uv_sphere_add",
        "cylinder": "mesh.primitive_cylinder_add",
        "cone": "mesh.primitive_cone_add",
        "plane": "mesh.primitive_plane_add",
        "torus": "mesh.primitive_torus_add",
        "monkey": "mesh.primitive_monkey_add",
        "ico_sphere": "mesh.primitive_ico_sphere_add",
        "grid": "mesh.primitive_grid_add",
        "circle": "mesh.primitive_circle_add",
    }

    op_name = type_map.get(primitive_type.lower())
    if op_name is None:
        return {"error": f"不支持的几何体类型: {primitive_type}，支持: {list(type_map.keys())}"}

    try:
        bpy.ops.mesh.primitive_cube_add(location=location) if primitive_type == "cube" else \
        bpy.ops.mesh.primitive_uv_sphere_add(location=location) if primitive_type == "sphere" else \
        bpy.ops.mesh.primitive_cylinder_add(location=location) if primitive_type == "cylinder" else \
        bpy.ops.mesh.primitive_cone_add(location=location) if primitive_type == "cone" else \
        bpy.ops.mesh.primitive_plane_add(location=location) if primitive_type == "plane" else \
        bpy.ops.mesh.primitive_torus_add(location=location) if primitive_type == "torus" else \
        bpy.ops.mesh.primitive_monkey_add(location=location) if primitive_type == "monkey" else \
        bpy.ops.mesh.primitive_ico_sphere_add(location=location) if primitive_type == "ico_sphere" else \
        bpy.ops.mesh.primitive_grid_add(location=location) if primitive_type == "grid" else \
        bpy.ops.mesh.primitive_circle_add(location=location)
    except Exception as exc:
        return {"error": f"创建几何体失败: {exc}"}

    obj = bpy.context.active_object
    if obj and name:
        obj.name = name

    result = {
        "created": primitive_type,
        "name": obj.name if obj else "(未知)",
        "location": location,
    }
    log.info("创建几何体: %s", result)
    return result


def delete_object(name: str) -> dict:
    """删除指定对象。

    Args:
        name: 对象名称。
    """
    import bpy
    obj = bpy.data.objects.get(name)
    if obj is None:
        return {"error": f"未找到对象: {name}"}

    obj_type = obj.type
    # 如果对象有数据，也删除数据块
    if obj.data and obj.data.users == 1:
        data_name = obj.data.name
        bpy.data.objects.remove(obj, do_unlink=True)
        # 尝试清理孤立数据
        data = bpy.data.meshes.get(data_name)
        if data:
            bpy.data.meshes.remove(data)
    else:
        bpy.data.objects.remove(obj, do_unlink=True)

    return {"deleted": name, "type": obj_type}


def rename_object(old_name: str, new_name: str) -> dict:
    """重命名对象。

    Args:
        old_name: 当前名称。
        new_name: 新名称。
    """
    import bpy
    obj = bpy.data.objects.get(old_name)
    if obj is None:
        return {"error": f"未找到对象: {old_name}"}

    obj.name = new_name
    return {"old_name": old_name, "new_name": new_name}


# ---------------------------------------------------------------------------
# 材质操作
# ---------------------------------------------------------------------------

def assign_material(object_name: str, color: tuple = (1, 0.5, 0.5, 1)) -> dict:
    """给对象分配一个新材质。

    Args:
        object_name: 对象名称。
        color: (R, G, B, A) 颜色值，每分量 0-1。
    """
    import bpy

    obj = bpy.data.objects.get(object_name)
    if obj is None:
        return {"error": f"未找到对象: {object_name}"}

    # 创建材质
    mat = bpy.data.materials.new(name=f"{object_name}_material")
    mat.diffuse_color = color[:4]
    mat.use_nodes = True

    # 分配材质
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

    return {
        "object": object_name,
        "material": mat.name,
        "color": color[:4],
    }


# ---------------------------------------------------------------------------
# 渲染设置
# ---------------------------------------------------------------------------

def set_render_engine(engine: str) -> dict:
    """设置渲染引擎。

    Args:
        engine: 'CYCLES', 'EEVEE', 'BLENDER_EEVEE_NEXT', 或 'WORKBENCH'
    """
    import bpy
    valid = {'CYCLES', 'BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT', 'BLENDER_WORKBENCH'}
    if engine.upper() not in valid:
        return {"error": f"不支持的渲染引擎: {engine}，支持: {list(valid)}"}

    bpy.context.scene.render.engine = engine.upper()
    return {"render_engine": engine.upper()}


def set_render_resolution(width: int = 1920, height: int = 1080) -> dict:
    """设置渲染分辨率。

    Args:
        width: 宽度（像素）
        height: 高度（像素）
    """
    import bpy
    scene = bpy.context.scene
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    return {"resolution": [width, height]}
