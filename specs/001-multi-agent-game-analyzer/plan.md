# Implementation Plan: Multi-Agent Game Analysis System

**Branch**: `001-multi-agent-game-analyzer` | **Date**: 2025-12-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-multi-agent-game-analyzer/spec.md`

## Summary

构建一个多智能体 AI 系统，自动试玩 Windows 小游戏（微信/抖音），通过视觉感知分析游戏机制，生成专业的游戏策划文档（GDD、数值分析表、美术风格报告）。系统采用 LangGraph 状态机编排 6 个专业智能体（Player、Mechanics、UI、Art、Doc-Writer、QA-Critic），使用 **Gemini 3 Pro Preview** 作为主力多模态模型进行深度视觉理解和推理。

## Technical Context

**Language/Version**: Python 3.11+
**Package Manager**: uv (用于依赖版本控制)
**Primary Dependencies**:
- langchain==1.2.1 (AI 编排框架)
- langgraph (与 langchain 1.2.1 兼容版本，状态机管理)
- langchain-google-genai (Gemini 模型集成)
- google-generativeai (Gemini API 直接调用)
- opencv-python (最新版本，视频处理)
- mss (高速屏幕截图)
- pydirectinput (Windows 输入模拟)
- pydantic>=2.0 (数据验证)
- typer (CLI 框架)
- rich (终端美化输出)

**Storage**: 本地文件系统 (JSON + Markdown)
**Testing**: pytest + pytest-asyncio
**Target Platform**: Windows 10/11 桌面环境
**Project Type**: Single (CLI 应用)
**Performance Goals**:
- Agent Loop: <10 秒/步
- 屏幕捕获: 30+ FPS
- 视频编码: <2 秒/5秒片段
- 文档生成: <5 分钟/会话

**AI Models**:
- gemini-3-pro-preview (主力模型: Mechanics/UI/Art/Doc-Writer/QA-Critic)
- gemini-2.0-flash (Player-Agent: 实时响应)

**Constraints**:
- Gemini 上下文窗口限制 (需要内存分页/摘要)
- Windows-only (pydirectinput 依赖)
- 需要网络连接 (Gemini API)

**Scale/Scope**: 单用户本地工具，支持 50-100 步游戏会话

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Requirement | Status | Notes |
|-----------|-------------|--------|-------|
| I. Code Quality | Type hints + Pydantic models | ✅ PASS | 使用 Pydantic v2 进行数据验证 |
| I. Code Quality | Modular agents | ✅ PASS | 6 个独立 Agent 模块设计 |
| I. Code Quality | Error handling for external APIs | ✅ PASS | FR-024 定义了重试机制 |
| II. Testing | Test-first development | ✅ PASS | pytest 配置，contract tests 要求 |
| II. Testing | Integration tests for agent communication | ✅ PASS | LangGraph 状态转换测试 |
| II. Testing | Contract tests for JSON schemas | ✅ PASS | Agent 输出 schema 验证 |
| III. UX Consistency | Progress visibility | ✅ PASS | FR-021 要求进度反馈 |
| III. UX Consistency | Error clarity | ✅ PASS | FR-024 定义错误处理流程 |
| IV. Performance | Agent loop <10s | ✅ PASS | SC-001 验证指标 |
| IV. Performance | 30+ FPS capture | ✅ PASS | FR-001 + mss 实现 |
| IV. Performance | Memory management | ✅ PASS | FR-012 分离内存模块 |

**Gate Status**: ✅ ALL PASS - 可以进入 Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/001-multi-agent-game-analyzer/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (JSON schemas)
│   ├── action-command.json
│   ├── mechanics-state.json
│   ├── ui-flow-graph.json
│   ├── art-style-state.json
│   └── generated-document.json
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── __init__.py
├── main.py                    # CLI 入口
├── config.py                  # 配置管理
├── models/                    # Pydantic 数据模型
│   ├── __init__.py
│   ├── session.py             # PlaySession, ActionCommand
│   ├── analysis.py            # MechanicsState, UIFlowGraph, ArtStyleState
│   └── document.py            # GeneratedDocument
├── agents/                    # 智能体实现
│   ├── __init__.py
│   ├── base.py                # BaseAgent 抽象类
│   ├── player.py              # Player-Agent (游戏操作)
│   ├── mechanics.py           # Mechanics-Analyst (机制分析)
│   ├── ui_flow.py             # UI-Agent (界面流程)
│   ├── art_style.py           # Art-Agent (美术风格)
│   ├── doc_writer.py          # Doc-Writer (文档生成)
│   └── qa_critic.py           # QA-Critic (质量审查)
├── capture/                   # 屏幕捕获模块
│   ├── __init__.py
│   ├── screen.py              # mss 封装
│   └── video.py               # OpenCV 视频合成
├── control/                   # 输入控制模块
│   ├── __init__.py
│   └── input.py               # pydirectinput 封装
├── memory/                    # 内存管理模块
│   ├── __init__.py
│   ├── play_log.py            # 游戏日志
│   ├── mechanics_state.py     # 机制状态
│   ├── ui_flow_graph.py       # UI 流程图
│   └── art_style_state.py     # 美术风格状态
├── orchestrator/              # LangGraph 编排
│   ├── __init__.py
│   ├── graph.py               # 状态机定义
│   └── nodes.py               # 节点实现
├── output/                    # 文档输出
│   ├── __init__.py
│   ├── gdd.py                 # GDD 生成
│   ├── numerical.py           # 数值分析生成
│   └── art_report.py          # 美术报告生成
└── utils/                     # 工具函数
    ├── __init__.py
    ├── logging.py             # 日志配置
    ├── ocr.py                 # OCR 工具
    └── retry.py               # 重试逻辑

tests/
├── __init__.py
├── conftest.py                # pytest fixtures
├── contract/                  # Contract tests
│   ├── test_action_schema.py
│   ├── test_mechanics_schema.py
│   └── test_ui_flow_schema.py
├── integration/               # Integration tests
│   ├── test_agent_pipeline.py
│   └── test_langgraph_flow.py
└── unit/                      # Unit tests
    ├── test_capture.py
    ├── test_control.py
    ├── test_memory.py
    └── test_agents.py
```

**Structure Decision**: 采用 Single project 结构，CLI 应用无需前后端分离。模块按职责划分：agents（智能体）、capture（捕获）、control（控制）、memory（内存）、orchestrator（编排）、output（输出）。

## Complexity Tracking

> **No violations - all requirements align with Constitution principles**

| Aspect | Complexity Level | Justification |
|--------|------------------|---------------|
| 6 Agents | Medium | 每个 Agent 职责单一，接口清晰，符合 modularity 原则 |
| LangGraph 状态机 | Medium | 标准编排模式，有完善文档支持 |
| 多模块内存 | Low | 简单的分离存储，避免单体内存膨胀 |
