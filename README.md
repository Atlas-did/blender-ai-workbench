# AIWork — Blender AI 工作台

把 Blender 变成一个 AI 辅助的 3D 工作台。

## 界面布局

| 区域 | 功能 |
|------|------|
| 左侧 | 项目文件树 / 脚本列表 |
| 中间 | Blender 原生 3D 视图 |
| 右侧 | AI 聊天面板 |
| 底部 | 执行日志 |

## 核心流程

```
用户提问 → 采集场景上下文 → AI 分析 → 调用工具 → 确认执行 → 返回结果
```

## 内置工具

| 工具 | 风险 | 功能 |
|------|------|------|
| `get_scene_info` | LOW | 获取场景基本信息 |
| `select_objects` | MEDIUM | 按名称选中对象 |
| `move_active_object` | MEDIUM | 移动活动对象到指定坐标 |
| `set_object_visibility` | MEDIUM | 设置对象可见性 |
| `read_text_file` | LOW | 读取文本数据块 |

## 安装

```bash
# 复制到 Blender 用户 addons 目录
cp -r aiwork/ "%APPDATA%/Blender Foundation/Blender/4.5/scripts/addons/"
```

或通过 Blender → Edit → Preferences → Add-ons → Install from Disk → 选择 `aiwork/` 文件夹。

## 配置

**必填：** 在 Blender 偏好设置中填入 API 信息：

| 设置 | 说明 | 示例 |
|------|------|------|
| API 地址 | OpenAI 兼容端点 | `https://api.moonshot.cn/v1` (Kimi) |
| API Key | 你的密钥 | `sk-...` |
| 模型名称 | LLM 模型 ID | `moonshot-v1-auto` |

支持所有 OpenAI 兼容 API：Kimi、Ollama、vLLM、Groq 等。

## 兼容

- Blender ≥ 4.2
- Python ≥ 3.11

## 开发

```bash
# 目录结构
aiwork/
├── __init__.py          # 插件入口
├── settings.py          # 默认配置
├── schemas.py           # 数据结构
├── state.py             # 运行时状态
├── preferences.py       # 偏好设置面板
├── storage.py           # 持久化
├── context_scene.py     # 场景采集
├── context_project.py   # 工程采集
├── context_builder.py   # 上下文聚合
├── tools_registry.py    # 工具注册中心
├── executor.py          # 工具调度器
├── api_client.py        # LLM API 通信
├── mcp_client.py        # MCP 通信
├── security.py          # 安全策略
├── audit.py             # 审计日志
├── ui/                  # UI 绘制
├── operators/           # Blender Operator
├── panels/              # Blender Panel
├── services/            # 后台服务
└── tests/               # 测试
```

## License

MIT
