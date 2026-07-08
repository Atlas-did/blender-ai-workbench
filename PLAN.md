# AIWork 项目上下文与详细计划

## 一、项目背景总结

目标是把 Blender 做成一个“AI IDE 工作台”：

- 左侧：项目/文件区
- 中间：3D 视图
- 右侧：AI 聊天区
- 底部：执行台与日志区

这个项目不是一开始复刻 VS Code，而是先做一个能形成闭环的 Blender AI 工作台：
用户提问 → 插件读取 Blender 上下文 → AI 分析 → 必要时调用工具 → 用户确认 → 执行 Blender 操作 → 返回结果。

## 二、总体结论

- 可行性：中等偏高
- 最现实的第一阶段是“Blender 内的 AI 工作台”，不是完整 IDE
- MCP 和 AI 编排层优先复用现成方案，不重写协议
- Blender 插件只负责 UI、上下文、确认、状态、执行入口
- 重计算、模型调用、复杂编排尽量放到本地服务层

## 三、MVP 范围

### 必做

1. 右侧 AI 聊天面板
2. 场景上下文采集
3. 工具调用层接入
4. 1~3 个高频 Blender 工具
5. 文件读取能力
6. 日志输出与错误提示
7. 会话保存
8. 操作前确认机制

### 暂不做

- 真终端
- 完整内嵌编辑器
- 自由拖拽复杂布局
- 多标签文件系统
- 复杂差异对比
- 大规模项目索引

## 四、第一版推荐流程

1. 用户输入问题
2. 插件自动收集 Blender 上下文
3. 发送到本地 AI / 服务层
4. AI 决定是否调用工具
5. 涉及修改时弹出确认
6. 执行 Blender 操作
7. 结果回写到聊天区和日志区

## 五、模块拆分

### 1. 插件入口与注册层

文件职责：

- `__init__.py`
- `manifest.py`
- `preferences.py`

功能：注册、注销、插件偏好设置、全局初始化。

### 2. 状态与存储层

文件职责：

- `state.py`
- `settings.py`
- `storage.py`
- `schemas.py`

功能：会话状态、消息记录、配置保存、历史恢复。

### 3. 聊天 UI 层

文件职责：

- `ui/ui_chat.py`
- `ui/ui_history.py`
- `ui/ui_context.py`
- `ui/ui_logs.py`

功能：聊天输入、消息流、工具调用卡片、上下文摘要、日志显示。

### 4. 上下文采集层

文件职责：

- `context_scene.py`
- `context_project.py`
- `context_builder.py`

功能：采集当前文件、场景、选中对象、渲染设置、帧范围等信息。

### 5. 工具执行层

文件职责：

- `tools_registry.py`
- `tools_scene.py`
- `tools_python.py`
- `tools_files.py`
- `executor.py`

功能：注册工具、校验参数、执行工具、返回结果。

### 6. 安全与日志层

文件职责：

- `security.py`
- `audit.py`
- `logging_ui.py`

功能：风险分级、执行确认、审计日志、错误记录。

## 六、建议的第一批工具

1. `get_scene_info`
2. `select_objects`
3. `move_active_object`
4. `set_object_visibility`
5. `read_text_file`
6. `run_python_snippet`

## 七、推荐 API 设计原则

- 所有返回值都使用结构化对象
- 工具参数先校验再执行
- 写操作必须声明风险等级
- 高风险工具必须确认
- 聊天消息与工具调用分开记录
- 上下文内容要可配置，不要过量注入

## 八、开发排期建议

### 2 周版

- 第 1 周：插件骨架、聊天面板、上下文采集、基础通信、一个工具闭环
- 第 2 周：确认机制、文件读取、日志面板、会话保存、错误处理

### 1 周版

- 只做最小证明：聊天、上下文、一个工具、确认、日志

## 九、第一版原型界面

### 左侧

项目区：文件树、最近脚本、当前场景摘要

### 中间

Blender 3D 视图，保持原生工作流

### 右侧

AI 助手：聊天、上下文摘要、工具调用结果

### 底部

执行台：日志、任务进度、错误输出

## 十、后续推荐顺序

1. 插件骨架
2. 聊天面板
3. 上下文采集
4. 工具调用
5. 确认机制
6. 日志
7. 会话保存
8. 文件读取
9. 项目树
10. 终端 / 编辑器增强

## 十一、权限与目录建议

当前工作区已经放到 `C:\Users\finef\blender\aiwork`，这是更适合开发的位置：

- 不会像 `Program Files` 那样频繁触发管理员权限限制
- 更适合 Blender、VS Code、Python 直接读写
- 调试、保存、打包更顺畅

## 十二、下一步建议

如果马上开始落地，推荐顺序是：

1. 先搭插件骨架和配置保存
2. 做聊天面板
3. 做上下文收集
4. 做一个最简单的工具，比如选中对象或改位置
5. 加确认框
6. 加日志面板
7. 加会话保存
8. 再补文件读取

## 十三、插件代码骨架文件清单

下面是第一版建议的代码骨架文件清单。先把文件和职责分开，后续再逐个补实现。

### 根目录文件

- `__init__.py`
- `manifest.py`
- `preferences.py`
- `state.py`
- `settings.py`
- `storage.py`
- `schemas.py`
- `security.py`
- `audit.py`
- `executor.py`
- `api_client.py`
- `mcp_client.py`
- `context_builder.py`
- `context_scene.py`
- `context_project.py`
- `tools_registry.py`
- `tools_scene.py`
- `tools_python.py`
- `tools_files.py`

### UI 目录

- `ui/ui_chat.py`
- `ui/ui_history.py`
- `ui/ui_context.py`
- `ui/ui_logs.py`
- `ui/ui_settings.py`
- `ui/ui_common.py`

### Operators 目录

- `operators/op_chat_send.py`
- `operators/op_chat_retry.py`
- `operators/op_chat_clear.py`
- `operators/op_tool_execute.py`
- `operators/op_tool_confirm.py`
- `operators/op_tool_cancel.py`
- `operators/op_refresh_context.py`
- `operators/op_open_file.py`

### Panels 目录

- `panels/panel_chat.py`
- `panels/panel_context.py`
- `panels/panel_files.py`
- `panels/panel_logs.py`
- `panels/panel_settings.py`

### Services 目录

- `services/service_bridge.py`
- `services/service_worker.py`
- `services/service_events.py`
- `services/service_stream.py`

### 资源与测试目录

- `resources/icons/`
- `resources/templates/`
- `tests/test_context.py`
- `tests/test_tools.py`
- `tests/test_storage.py`

## 十四、每个文件的职责说明

### 根目录

- `__init__.py`：插件入口，负责注册、注销和统一初始化。
- `manifest.py`：插件元信息，包含名称、版本、作者、兼容范围。
- `preferences.py`：插件设置，保存 API 地址、Key、模型名、MCP 地址等。
- `state.py`：运行时状态容器，保存当前会话、消息、连接状态、错误信息。
- `settings.py`：默认配置与常量定义。
- `storage.py`：本地持久化读写，负责会话和设置保存恢复。
- `schemas.py`：数据结构定义，包含 Session、Message、ToolCall、ContextSnapshot。
- `security.py`：安全策略、风险分级、确认规则。
- `audit.py`：审计日志记录与导出。
- `executor.py`：工具执行总入口，统一调度工具和返回结果。
- `api_client.py`：LLM 通信封装，后续接 OpenAI、Ollama 或其他服务。
- `mcp_client.py`：MCP 通信封装，后续接 Blender MCP 或本地桥接服务。
- `context_builder.py`：上下文聚合器，把场景、项目、选择集拼成标准上下文。
- `context_scene.py`：场景信息采集，负责 scene、object、frame、render 等数据。
- `context_project.py`：工程信息采集，负责文件路径、目录、脚本、资源等数据。
- `tools_registry.py`：工具注册中心，维护工具定义、参数 schema、风险等级。
- `tools_scene.py`：与场景相关的工具，如选中、移动、可见性、对象属性修改。
- `tools_python.py`：Python 执行类工具，负责运行脚本片段。
- `tools_files.py`：文件类工具，负责读取文本、预览脚本、列出文件。

### UI 目录

- `ui_chat.py`：聊天主界面绘制，包含消息流、输入框、发送按钮。
- `ui_history.py`：会话历史显示与切换。
- `ui_context.py`：上下文摘要展示，例如文件名、场景名、选中对象。
- `ui_logs.py`：日志与执行反馈展示。
- `ui_settings.py`：设置页 UI，显示 API、MCP 和行为开关。
- `ui_common.py`：UI 公共组件、样式帮助函数、复用控件。

### Operators 目录

- `op_chat_send.py`：发送聊天消息。
- `op_chat_retry.py`：重试上一条回复或工具链。
- `op_chat_clear.py`：清空当前会话。
- `op_tool_execute.py`：执行工具调用。
- `op_tool_confirm.py`：确认危险操作。
- `op_tool_cancel.py`：取消待执行操作。
- `op_refresh_context.py`：刷新当前上下文。
- `op_open_file.py`：打开或预览文件。

### Panels 目录

- `panel_chat.py`：右侧聊天面板入口。
- `panel_context.py`：上下文面板入口。
- `panel_files.py`：文件树面板入口。
- `panel_logs.py`：日志面板入口。
- `panel_settings.py`：设置面板入口。

### Services 目录

- `service_bridge.py`：Blender 与本地服务之间的总桥接。
- `service_worker.py`：后台任务与异步执行。
- `service_events.py`：事件分发与消息总线。
- `service_stream.py`：流式响应接收与分片更新。

## 十五、最小可运行目录结构

下面是第一版建议的最小目录结构。这个版本只保证“能跑通闭环”，不追求完整功能。

```text
aiwork/
├─ __init__.py
├─ manifest.py
├─ preferences.py
├─ state.py
├─ settings.py
├─ storage.py
├─ schemas.py
├─ security.py
├─ audit.py
├─ executor.py
├─ api_client.py
├─ mcp_client.py
├─ context_builder.py
├─ context_scene.py
├─ context_project.py
├─ tools_registry.py
├─ tools_scene.py
├─ tools_python.py
├─ tools_files.py
├─ ui/
│  ├─ ui_chat.py
│  ├─ ui_history.py
│  ├─ ui_context.py
│  ├─ ui_logs.py
│  ├─ ui_settings.py
│  └─ ui_common.py
├─ operators/
│  ├─ op_chat_send.py
│  ├─ op_chat_retry.py
│  ├─ op_chat_clear.py
│  ├─ op_tool_execute.py
│  ├─ op_tool_confirm.py
│  ├─ op_tool_cancel.py
│  ├─ op_refresh_context.py
│  └─ op_open_file.py
├─ panels/
│  ├─ panel_chat.py
│  ├─ panel_context.py
│  ├─ panel_files.py
│  ├─ panel_logs.py
│  └─ panel_settings.py
├─ services/
│  ├─ service_bridge.py
│  ├─ service_worker.py
│  ├─ service_events.py
│  └─ service_stream.py
├─ resources/
│  ├─ icons/
│  └─ templates/
└─ tests/
	├─ test_context.py
	├─ test_tools.py
	└─ test_storage.py
```

## 十六、后续逐文件骨架设计顺序

接下来建议按下面顺序进入逐文件骨架设计：

1. `__init__.py`
2. `manifest.py`
3. `preferences.py`
4. `state.py`
5. `schemas.py`
6. `ui/ui_chat.py`
7. `panels/panel_chat.py`
8. `context_builder.py`
9. `tools_registry.py`
10. `executor.py`
11. `storage.py`
12. `services/service_bridge.py`

这样可以先把插件最核心的“启动、状态、UI、上下文、工具执行、存储”链路搭起来，再补细节。
