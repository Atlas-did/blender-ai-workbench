"""
tools_registry.py — 工具注册中心
=================================
维护所有可用工具的定义、参数 schema、风险等级。
供 executor 查询和校验，供 UI 展示可用工具列表。

每个工具的注册格式：
    {
        "name": str,
        "description": str,
        "parameters": [ToolParameter, ...],
        "risk_level": RiskLevel,
        "handler": callable,   # 实际执行的函数
    }
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from .schemas import RiskLevel, ToolDefinition, ToolParameter

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 全局注册表
# ---------------------------------------------------------------------------
_tools: dict[str, dict] = {}


def register_tool(
    name: str,
    description: str,
    parameters: list[ToolParameter],
    risk_level: RiskLevel,
    handler: Callable[..., Any],
) -> None:
    """注册一个工具。

    Args:
        name: 工具唯一名称。
        description: 工具功能描述（会发给 AI）。
        parameters: 参数列表。
        risk_level: 风险等级。
        handler: 实际执行函数，签名为 handler(**kwargs) -> Any。
    """
    if name in _tools:
        log.warning("工具 '%s' 已存在，将被覆盖", name)

    _tools[name] = {
        "definition": ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
            risk_level=risk_level,
        ),
        "handler": handler,
    }
    log.info("工具已注册: %s (风险: %s)", name, risk_level.value)


def unregister_tool(name: str) -> None:
    """注销一个工具。"""
    if name in _tools:
        del _tools[name]
        log.info("工具已注销: %s", name)


def get_tool(name: str) -> Optional[dict]:
    """获取单个工具的定义 + handler。"""
    return _tools.get(name)


def get_tool_definition(name: str) -> Optional[ToolDefinition]:
    """获取单个工具的定义（不含 handler）。"""
    entry = _tools.get(name)
    return entry["definition"] if entry else None


def get_all_tools() -> list[dict]:
    """获取所有已注册工具。"""
    return list(_tools.values())


def get_all_definitions() -> list[ToolDefinition]:
    """获取所有工具的定义列表（用于发送给 AI）。"""
    return [entry["definition"] for entry in _tools.values()]


def list_tool_names() -> list[str]:
    """列出所有工具名。"""
    return list(_tools.keys())


def validate_arguments(tool_name: str, arguments: dict[str, Any]) -> tuple[bool, str]:
    """校验工具参数。

    Returns:
        (is_valid, error_message): 校验结果。
    """
    entry = _tools.get(tool_name)
    if entry is None:
        return False, f"未知工具: {tool_name}"

    definition: ToolDefinition = entry["definition"]
    for param in definition.parameters:
        if param.required and param.name not in arguments:
            return False, f"缺少必需参数: {param.name}"

        if param.name in arguments:
            value = arguments[param.name]
            # 简单类型校验
            type_map = {
                "string": str,
                "number": (int, float),
                "boolean": bool,
                "object": (dict, list),
                "array": list,
            }
            expected = type_map.get(param.param_type)
            if expected and not isinstance(value, expected):
                return False, (
                    f"参数 {param.name} 类型错误: "
                    f"期望 {param.param_type}, 实际 {type(value).__name__}"
                )

    return True, ""


def execute_tool(tool_name: str, arguments: dict[str, Any]) -> Any:
    """执行一个已注册的工具。

    Returns:
        工具 handler 的返回值。

    Raises:
        ValueError: 工具不存在或参数校验失败。
    """
    entry = _tools.get(tool_name)
    if entry is None:
        raise ValueError(f"未知工具: {tool_name}")

    is_valid, error = validate_arguments(tool_name, arguments)
    if not is_valid:
        raise ValueError(f"参数校验失败: {error}")

    handler = entry["handler"]
    try:
        return handler(**arguments)
    except Exception as exc:
        log.exception("工具 '%s' 执行失败", tool_name)
        raise


# ---------------------------------------------------------------------------
# 内置工具注册
# ---------------------------------------------------------------------------

def register_builtin_tools() -> None:
    """注册首批内置工具。"""

    # ---- get_scene_info ----
    register_tool(
        name="get_scene_info",
        description="获取当前场景的基本信息：场景名、对象数量、当前帧、渲染引擎等。",
        parameters=[],  # 无参数
        risk_level=RiskLevel.LOW,
        handler=_tool_get_scene_info,
    )

    # ---- select_objects ----
    register_tool(
        name="select_objects",
        description="按名称选择对象。支持单个名称或名称列表。",
        parameters=[
            ToolParameter(
                name="names",
                param_type="array",
                description="要选择的对象名称列表，如 ['Cube', 'Sphere']",
                required=True,
            ),
        ],
        risk_level=RiskLevel.MEDIUM,
        handler=_tool_select_objects,
    )

    # ---- move_active_object ----
    register_tool(
        name="move_active_object",
        description="移动当前活动对象到指定坐标 (x, y, z)。",
        parameters=[
            ToolParameter(name="x", param_type="number", description="X 坐标", required=True),
            ToolParameter(name="y", param_type="number", description="Y 坐标", required=True),
            ToolParameter(name="z", param_type="number", description="Z 坐标", required=True),
        ],
        risk_level=RiskLevel.MEDIUM,
        handler=_tool_move_active_object,
    )

    # ---- set_object_visibility ----
    register_tool(
        name="set_object_visibility",
        description="设置指定对象的可见性。",
        parameters=[
            ToolParameter(name="name", param_type="string", description="对象名称", required=True),
            ToolParameter(name="visible", param_type="boolean", description="是否可见", required=True),
        ],
        risk_level=RiskLevel.MEDIUM,
        handler=_tool_set_object_visibility,
    )

    # ---- read_text_file ----
    register_tool(
        name="read_text_file",
        description="读取 Blender 文本编辑器中的数据块内容。",
        parameters=[
            ToolParameter(
                name="text_name",
                param_type="string",
                description="文本数据块名称",
                required=True,
            ),
        ],
        risk_level=RiskLevel.LOW,
        handler=_tool_read_text_file,
    )

    # ---- create_primitive ----
    register_tool(
        name="create_primitive",
        description="创建基础几何体。支持: cube, sphere, cylinder, cone, plane, torus, monkey, ico_sphere, grid, circle。",
        parameters=[
            ToolParameter(name="primitive_type", param_type="string", description="几何体类型", required=True),
            ToolParameter(name="location", param_type="array", description="[x, y, z] 位置坐标", required=False, default=[0, 0, 0]),
            ToolParameter(name="name", param_type="string", description="对象名称（可选）", required=False, default=""),
        ],
        risk_level=RiskLevel.MEDIUM,
        handler=_tool_create_primitive,
    )

    # ---- delete_object ----
    register_tool(
        name="delete_object",
        description="删除指定名称的对象。",
        parameters=[
            ToolParameter(name="name", param_type="string", description="要删除的对象名称", required=True),
        ],
        risk_level=RiskLevel.HIGH,
        handler=_tool_delete_object,
    )

    # ---- rename_object ----
    register_tool(
        name="rename_object",
        description="重命名指定对象。",
        parameters=[
            ToolParameter(name="old_name", param_type="string", description="当前名称", required=True),
            ToolParameter(name="new_name", param_type="string", description="新名称", required=True),
        ],
        risk_level=RiskLevel.MEDIUM,
        handler=_tool_rename_object,
    )

    # ---- assign_material ----
    register_tool(
        name="assign_material",
        description="给对象创建一个新的彩色材质。",
        parameters=[
            ToolParameter(name="object_name", param_type="string", description="对象名称", required=True),
            ToolParameter(name="color", param_type="array", description="[R, G, B, A] 颜色值 (0-1)", required=False, default=[1, 0.5, 0.5, 1]),
        ],
        risk_level=RiskLevel.MEDIUM,
        handler=_tool_assign_material,
    )

    # ---- set_render_engine ----
    register_tool(
        name="set_render_engine",
        description="切换渲染引擎。支持: CYCLES, BLENDER_EEVEE, BLENDER_EEVEE_NEXT, BLENDER_WORKBENCH。",
        parameters=[
            ToolParameter(name="engine", param_type="string", description="渲染引擎名称", required=True),
        ],
        risk_level=RiskLevel.MEDIUM,
        handler=_tool_set_render_engine,
    )

    # ---- set_render_resolution ----
    register_tool(
        name="set_render_resolution",
        description="设置渲染输出分辨率。",
        parameters=[
            ToolParameter(name="width", param_type="number", description="宽度（像素）", required=False, default=1920),
            ToolParameter(name="height", param_type="number", description="高度（像素）", required=False, default=1080),
        ],
        risk_level=RiskLevel.MEDIUM,
        handler=_tool_set_render_resolution,
    )

    # ---- list_directory ----
    register_tool(
        name="list_directory",
        description="列出工作区目录中的文件和子目录。",
        parameters=[
            ToolParameter(name="directory", param_type="string", description="目录路径（相对路径）", required=False, default="."),
        ],
        risk_level=RiskLevel.MEDIUM,
        handler=_tool_list_directory,
    )

    # ---- read_file ----
    register_tool(
        name="read_file",
        description="读取工作区内的文本文件内容。",
        parameters=[
            ToolParameter(name="filepath", param_type="string", description="文件路径（相对路径）", required=True),
        ],
        risk_level=RiskLevel.MEDIUM,
        handler=_tool_read_file,
    )

    # ---- write_file ----
    register_tool(
        name="write_file",
        description="写入文本文件到工作区内。高风险操作，需要用户确认。",
        parameters=[
            ToolParameter(name="filepath", param_type="string", description="文件路径（相对路径）", required=True),
            ToolParameter(name="content", param_type="string", description="要写入的文本内容", required=True),
        ],
        risk_level=RiskLevel.HIGH,
        handler=_tool_write_file,
    )

    # ---- run_python ----
    register_tool(
        name="run_python",
        description="在受限沙箱中执行 Python 代码片段。可访问 bpy/bmesh/math/mathutils。高风险操作，需要用户确认。",
        parameters=[
            ToolParameter(name="code", param_type="string", description="Python 代码", required=True),
            ToolParameter(name="timeout", param_type="number", description="超时秒数", required=False, default=10),
        ],
        risk_level=RiskLevel.HIGH,
        handler=_tool_run_python,
    )

    log.info("内置工具注册完成，共 %d 个工具", len(_tools))


# ---------------------------------------------------------------------------
# 内置工具 handler 实现
# ---------------------------------------------------------------------------

def _tool_get_scene_info() -> dict:
    """get_scene_info handler。"""
    import bpy
    scene = bpy.context.scene
    return {
        "scene_name": scene.name,
        "object_count": len(scene.objects),
        "selected_count": len(bpy.context.selected_objects),
        "current_frame": scene.frame_current,
        "frame_range": [scene.frame_start, scene.frame_end],
        "render_engine": scene.render.engine,
    }


def _tool_select_objects(names: list[str]) -> dict:
    """select_objects handler。"""
    import bpy

    if isinstance(names, str):
        names = [names]
    elif not isinstance(names, list):
        return {"error": "names 必须是字符串或字符串列表"}

    # 先取消所有选择
    bpy.ops.object.select_all(action='DESELECT')

    found = []
    not_found = []
    for name in names:
        obj = bpy.data.objects.get(name)
        if obj:
            obj.select_set(True)
            found.append(name)
        else:
            not_found.append(name)

    # 设置最后一个找到的为活动对象
    if found:
        bpy.context.view_layer.objects.active = bpy.data.objects[found[-1]]

    return {"selected": found, "not_found": not_found}


def _tool_move_active_object(x: float, y: float, z: float) -> dict:
    """move_active_object handler。"""
    import bpy
    obj = bpy.context.active_object
    if obj is None:
        return {"error": "没有活动对象"}
    old_loc = (obj.location.x, obj.location.y, obj.location.z)
    obj.location = (x, y, z)
    return {"object": obj.name, "from": old_loc, "to": (x, y, z)}


def _tool_set_object_visibility(name: str, visible: bool) -> dict:
    """set_object_visibility handler。"""
    import bpy
    obj = bpy.data.objects.get(name)
    if obj is None:
        return {"error": f"未找到对象: {name}"}
    obj.hide_set(not visible)
    return {"object": name, "visible": visible}


def _tool_read_text_file(text_name: str) -> dict:
    """read_text_file handler。"""
    import bpy
    text_block = bpy.data.texts.get(text_name)
    if text_block is None:
        return {"error": f"未找到文本块: {text_name}"}
    return {
        "name": text_name,
        "lines": len(text_block.lines),
        "content": text_block.as_string(),
    }


def _tool_create_primitive(primitive_type: str = "cube", location=None, name: str = "") -> dict:
    """create_primitive handler。"""
    from .tools_scene import create_primitive
    if location is None:
        location = [0, 0, 0]
    if isinstance(location, (list, tuple)):
        location = tuple(location[:3])
    return create_primitive(primitive_type=primitive_type, location=location, name=name)


def _tool_delete_object(name: str) -> dict:
    """delete_object handler。"""
    from .tools_scene import delete_object
    return delete_object(name=name)


def _tool_rename_object(old_name: str, new_name: str) -> dict:
    """rename_object handler。"""
    from .tools_scene import rename_object
    return rename_object(old_name=old_name, new_name=new_name)


def _tool_assign_material(object_name: str, color=None) -> dict:
    """assign_material handler。"""
    from .tools_scene import assign_material
    if color is None:
        color = [1, 0.5, 0.5, 1]
    if isinstance(color, (list, tuple)):
        color = tuple(color[:4])
    return assign_material(object_name=object_name, color=color)


def _tool_set_render_engine(engine: str) -> dict:
    """set_render_engine handler。"""
    from .tools_scene import set_render_engine
    return set_render_engine(engine=engine)


def _tool_set_render_resolution(width: int = 1920, height: int = 1080) -> dict:
    """set_render_resolution handler。"""
    from .tools_scene import set_render_resolution
    return set_render_resolution(width=width, height=height)


def _tool_list_directory(directory: str = ".") -> dict:
    """list_directory handler。"""
    from .tools_files import list_directory
    return list_directory(directory=directory)


def _tool_read_file(filepath: str) -> dict:
    """read_file handler。"""
    from .tools_files import read_file
    return read_file(filepath=filepath)


def _tool_write_file(filepath: str, content: str) -> dict:
    """write_file handler。"""
    from .tools_files import write_file
    return write_file(filepath=filepath, content=content)


def _tool_run_python(code: str, timeout: int = 10) -> dict:
    """run_python handler。"""
    from .tools_python import run_python_snippet
    return run_python_snippet(code=code, timeout=timeout)
