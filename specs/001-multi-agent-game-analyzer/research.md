# Research: Multi-Agent Game Analysis System

**Date**: 2025-12-16
**Branch**: `001-multi-agent-game-analyzer`

## Technology Decisions

### 1. AI Framework: LangChain + LangGraph

**Decision**: 使用 LangChain 1.0+ + LangGraph 1.0+ + google-genai 1.50+

**Rationale**:
- LangChain 1.0+ 提供统一的 Agent 抽象 (`create_agent`)
- LangGraph 1.0+ 提供成熟的状态机管理，适合多智能体协作的循环工作流
- google-genai 是 Google 官方统一 SDK，支持 Gemini 3 Pro Preview
- 内置重试、回退等容错机制

**Alternatives Considered**:
- AutoGen: 多智能体框架，但与 LangChain 生态整合较弱
- CrewAI: 专注多智能体，但状态管理不如 LangGraph 灵活
- 原生 Gemini SDK: 需要手动实现状态机和智能体协调

**Compatible Versions**:
```
langchain>=1.0
langgraph>=1.0
google-genai>=1.50
```

### 2. AI Model: Google Gemini

**Decision**: 使用 Gemini 3 Pro Preview 作为主力模型

**Rationale**:
- **gemini-3-pro-preview** 是最新的预览版模型，提供最强的推理能力
- 原生视频理解能力，无需额外的视觉处理
- 2M+ Token 上下文窗口，支持长会话记忆
- 多模态输入（图像、视频、文本）
- 结构化输出支持（JSON mode）
- 更强的视觉理解和游戏场景分析能力

**Model Selection**:
| Agent | Model | Reason |
|-------|-------|--------|
| Player-Agent | gemini-2.0-flash | 实时响应，低延迟，操作决策 |
| Mechanics-Analyst | gemini-3-pro-preview | 最强推理，复杂数值分析 |
| UI-Agent | gemini-3-pro-preview | 高精度界面识别，状态判断 |
| Art-Agent | gemini-3-pro-preview | 深度视觉分析，风格描述 |
| Doc-Writer | gemini-3-pro-preview | 高质量长文本生成 |
| QA-Critic | gemini-3-pro-preview | 深度推理验证，一致性检查 |

**Note**: Player-Agent 保留使用 gemini-2.0-flash 以确保实时响应性能，其他需要深度分析的 Agent 使用最新的 gemini-3-pro-preview。

### 3. Screen Capture: mss

**Decision**: 使用 mss 库进行屏幕捕获

**Rationale**:
- 毫秒级捕获速度，满足 30+ FPS 要求
- 跨平台支持（虽然本项目 Windows-only）
- 支持区域捕获，避免全屏开销
- 纯 Python 实现，无复杂依赖

**Alternatives Considered**:
- pyautogui: 捕获速度较慢（~10 FPS）
- win32gui: Windows 专用，API 复杂
- OBS/FFmpeg: 过于重量级

### 4. Video Processing: OpenCV

**Decision**: 使用 opencv-python 最新版本

**Rationale**:
- 用户指定使用最新版本
- 成熟的视频编解码支持
- 图像处理功能（用于 OCR 预处理、血条检测）
- 广泛的社区支持和文档

**Key Features Used**:
- VideoWriter: 合成视频片段
- resize/crop: 图像预处理
- color space conversion: 色彩分析
- contour detection: UI 元素检测

### 5. Input Simulation: pydirectinput

**Decision**: 使用 pydirectinput 进行输入模拟

**Rationale**:
- DirectX 级别输入，可穿透大多数游戏
- 支持鼠标（点击、拖动、长按）和键盘
- 简单 API，易于集成
- 比 pyautogui 更底层，兼容性更好

**Limitations**:
- Windows-only
- 某些反作弊系统可能仍会拦截
- 需要管理员权限（某些场景）

### 6. Package Management: uv

**Decision**: 使用 uv 进行依赖管理

**Rationale**:
- 用户指定的版本控制工具
- 比 pip 快 10-100 倍
- 兼容 pyproject.toml
- 内置虚拟环境管理
- 支持 lock 文件确保可重现性

**Project Setup**:
```bash
uv init game-design-agent
uv add langchain==1.2.1
uv add langgraph langchain-google-genai
uv add opencv-python mss pydirectinput
uv add pydantic typer rich
uv add --dev pytest pytest-asyncio ruff mypy
```

### 7. CLI Framework: Typer + Rich

**Decision**: 使用 Typer 构建 CLI，Rich 美化输出

**Rationale**:
- Typer 基于类型注解自动生成 CLI
- Rich 提供进度条、表格、语法高亮
- 两者配合良好，广泛使用
- 符合 FR-021 进度反馈要求

### 8. Data Validation: Pydantic v2

**Decision**: 使用 Pydantic v2 进行数据验证

**Rationale**:
- Constitution 要求使用 Pydantic
- v2 性能大幅提升
- 与 LangChain 深度集成
- 支持 JSON Schema 导出（用于 contract tests）

### 9. OCR: 待定

**Decision**: 需要进一步评估

**Options**:
1. **PaddleOCR**: 中英文支持好，但依赖重
2. **EasyOCR**: 简单易用，精度中等
3. **Tesseract**: 经典方案，需要预处理
4. **Gemini Vision**: 直接让模型识别文字

**Recommendation**: 优先使用 Gemini Vision 进行 OCR，因为：
- 减少额外依赖
- 上下文理解更好（不仅识别文字，还理解含义）
- 中英文混合场景表现好

如果性能或成本成为问题，再考虑本地 OCR 作为优化。

### 10. Logging: Python logging + Rich

**Decision**: 使用标准 logging 模块配合 Rich handler

**Rationale**:
- 符合 FR-028 三级日志要求
- Rich 提供彩色终端输出
- 可配置文件输出用于调试
- 支持结构化日志（JSON 格式）

**Log Levels Mapping**:
| 配置级别 | Python Level | 内容 |
|---------|--------------|------|
| minimal | ERROR | 仅错误 |
| detailed | INFO | 每步决策、API 调用 |
| debug | DEBUG | 含截图/视频存档路径 |

## Architecture Decisions

### State Machine Design (LangGraph)

```
┌─────────────┐
│   START     │
└──────┬──────┘
       ▼
┌─────────────┐
│  OBSERVE    │◄─────────────────────┐
│ (capture)   │                      │
└──────┬──────┘                      │
       ▼                             │
┌─────────────┐                      │
│   THINK     │                      │
│ (Player)    │                      │
└──────┬──────┘                      │
       ▼                             │
┌─────────────┐                      │
│    ACT      │                      │
│ (execute)   │                      │
└──────┬──────┘                      │
       ▼                             │
┌─────────────┐                      │
│   RECORD    │                      │
│ (capture)   │                      │
└──────┬──────┘                      │
       ▼                             │
┌─────────────────────────────────┐  │
│          ANALYZE (parallel)      │  │
│  ┌──────────┬──────────┬──────┐ │  │
│  │Mechanics │ UI-Agent │ Art  │ │  │
│  └──────────┴──────────┴──────┘ │  │
└──────────────┬──────────────────┘  │
               ▼                     │
┌─────────────────┐                  │
│  MEMORY UPDATE  │                  │
└──────┬──────────┘                  │
       ▼                             │
   ┌───────┐    No                   │
   │ Done? ├─────────────────────────┘
   └───┬───┘
       │ Yes
       ▼
┌─────────────┐
│  DOC-WRITE  │
└──────┬──────┘
       ▼
┌─────────────┐
│  QA-CRITIC  │
└──────┬──────┘
       ▼
   ┌───────┐    No
   │ Pass? ├──────► (back to DOC-WRITE)
   └───┬───┘
       │ Yes
       ▼
┌─────────────┐
│    END      │
└─────────────┘
```

### Memory Module Design

每个内存模块独立管理，支持：
- 追加（append）: 添加新观察
- 摘要（summarize）: 超过阈值时压缩历史
- 导出（export）: 输出为 JSON/Markdown
- 清理（clear）: 会话结束后释放

```python
class MemoryModule(ABC):
    max_entries: int
    entries: list[Entry]

    def append(self, entry: Entry) -> None: ...
    def summarize(self) -> str: ...
    def export(self, path: Path) -> None: ...
    def clear(self) -> None: ...
```

## Open Questions (Resolved)

| Question | Resolution |
|----------|------------|
| 数据持久化 | 本地文件系统 (JSON + Markdown) |
| API 失败处理 | 重试 3 次 + 用户决定 |
| 用户界面 | CLI (初期) |
| 会话恢复 | 低优先级 (Demo 阶段) |
| 日志级别 | 三级可配置 |

## Next Steps

1. 创建 data-model.md 定义 Pydantic 模型
2. 创建 contracts/ 目录包含 JSON Schema
3. 创建 quickstart.md 快速入门指南
4. 生成 tasks.md 任务列表
