# Data Model: Multi-Agent Game Analysis System

**Date**: 2025-12-16
**Branch**: `001-multi-agent-game-analyzer`

## Overview

本文档定义系统中所有核心数据实体的结构、字段、关系和验证规则。所有模型使用 Pydantic v2 实现，支持 JSON Schema 导出用于 contract testing。

## Entity Relationship Diagram

```
┌─────────────────┐
│   PlaySession   │
├─────────────────┤
│ id              │
│ config          │──────┐
│ start_time      │      │
│ end_time        │      │
│ status          │      │
│ action_log ─────┼──────┼──► ActionCommand[]
│ memory_refs ────┼──────┼──► MemoryModuleRef[]
│ documents ──────┼──────┼──► GeneratedDocument[]
└─────────────────┘      │
                         │
┌─────────────────┐      │
│  SessionConfig  │◄─────┘
├─────────────────┤
│ window_region   │
│ max_steps       │
│ strategy        │
│ output_dir      │
│ log_level       │
└─────────────────┘

┌─────────────────┐     ┌─────────────────┐
│  ActionCommand  │     │  MechanicsState │
├─────────────────┤     ├─────────────────┤
│ id              │     │ damage_events   │──► DamageEvent[]
│ step            │     │ economy_events  │──► EconomyEvent[]
│ action_type     │     │ core_loop       │
│ coordinates     │     │ level_structure │
│ duration        │     │ identified_at   │
│ timestamp       │     └─────────────────┘
│ result          │
└─────────────────┘     ┌─────────────────┐
                        │   UIFlowGraph   │
┌─────────────────┐     ├─────────────────┤
│  AnalysisLog    │     │ nodes ──────────┼──► UINode[]
├─────────────────┤     │ edges ──────────┼──► UIEdge[]
│ step            │     │ current_screen  │
│ timestamp       │     └─────────────────┘
│ observation     │
│ screenshot_path │     ┌─────────────────┐
└─────────────────┘     │  ArtStyleState  │
                        ├─────────────────┤
┌─────────────────┐     │ color_palette   │──► Color[]
│GeneratedDocument│     │ style_tags      │
├─────────────────┤     │ effect_patterns │
│ id              │     │ reference_games │
│ doc_type        │     └─────────────────┘
│ content         │
│ version         │
│ qa_status       │
│ qa_feedback     │
│ created_at      │
└─────────────────┘
```

## Core Entities

### 1. PlaySession

表示单次自动游戏会话。

```python
from enum import Enum
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional
import uuid

class SessionStatus(str, Enum):
    """会话状态"""
    PENDING = "pending"        # 待开始
    RUNNING = "running"        # 运行中
    PAUSED = "paused"          # 已暂停
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"          # 失败
    CANCELLED = "cancelled"    # 已取消

class PlayStrategy(str, Enum):
    """游戏策略"""
    EXPLORATION = "exploration"  # 探索优先
    COMPLETION = "completion"    # 通关优先

class LogLevel(str, Enum):
    """日志级别"""
    MINIMAL = "minimal"      # 仅错误
    DETAILED = "detailed"    # 每步决策
    DEBUG = "debug"          # 完整调试

class WindowRegion(BaseModel):
    """窗口区域定义"""
    x: int = Field(..., ge=0, description="左上角 X 坐标")
    y: int = Field(..., ge=0, description="左上角 Y 坐标")
    width: int = Field(..., gt=0, description="宽度")
    height: int = Field(..., gt=0, description="高度")

class SessionConfig(BaseModel):
    """会话配置"""
    window_region: WindowRegion
    max_steps: int = Field(default=100, ge=1, le=1000, description="最大步数")
    strategy: PlayStrategy = Field(default=PlayStrategy.EXPLORATION)
    output_dir: Path = Field(default=Path("./output"))
    log_level: LogLevel = Field(default=LogLevel.DETAILED)
    video_segment_duration: float = Field(default=3.0, ge=2.0, le=5.0, description="视频片段时长(秒)")

class PlaySession(BaseModel):
    """游戏会话"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    config: SessionConfig
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: SessionStatus = Field(default=SessionStatus.PENDING)
    current_step: int = Field(default=0, ge=0)
    action_log: list["ActionCommand"] = Field(default_factory=list)
    analysis_log: list["AnalysisLog"] = Field(default_factory=list)
```

### 2. ActionCommand

表示单个游戏操作指令。

```python
class ActionType(str, Enum):
    """操作类型"""
    CLICK = "click"          # 单击
    DRAG = "drag"            # 拖动
    PRESS = "press"          # 长按
    WAIT = "wait"            # 等待
    END = "end"              # 结束会话

class NormalizedCoordinate(BaseModel):
    """归一化坐标 (0-1000)"""
    x: int = Field(..., ge=0, le=1000, description="X 坐标 (0-1000)")
    y: int = Field(..., ge=0, le=1000, description="Y 坐标 (0-1000)")

class ActionResult(str, Enum):
    """操作结果"""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"

class ActionCommand(BaseModel):
    """操作指令"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    step: int = Field(..., ge=0, description="步骤序号")
    action_type: ActionType
    start_coord: NormalizedCoordinate
    end_coord: Optional[NormalizedCoordinate] = Field(
        default=None,
        description="拖动操作的终点坐标"
    )
    duration: float = Field(
        default=0.1,
        ge=0,
        le=10.0,
        description="操作持续时间(秒)"
    )
    timestamp: datetime = Field(default_factory=datetime.now)
    result: Optional[ActionResult] = None
    reasoning: Optional[str] = Field(
        default=None,
        description="AI 决策理由"
    )
```

### 3. AnalysisLog

时间戳观察日志。

```python
class AnalysisLog(BaseModel):
    """分析日志条目"""
    step: int = Field(..., ge=0)
    timestamp: datetime = Field(default_factory=datetime.now)
    observation: str = Field(..., min_length=1, description="观察描述")
    screenshot_path: Optional[Path] = None
    video_segment_path: Optional[Path] = None
```

### 4. MechanicsState

游戏机制分析状态。

```python
class DamageEvent(BaseModel):
    """伤害事件"""
    step: int
    timestamp: datetime
    source: str = Field(..., description="伤害来源 (玩家/敌人/环境)")
    target: str = Field(..., description="伤害目标")
    hp_before: Optional[int] = None
    hp_after: Optional[int] = None
    damage: Optional[int] = None
    skill_name: Optional[str] = None

class EconomyEvent(BaseModel):
    """经济事件"""
    step: int
    timestamp: datetime
    event_type: str = Field(..., description="earn/spend")
    currency_type: str = Field(..., description="货币类型 (金币/钻石/能量等)")
    amount: int
    source: Optional[str] = Field(default=None, description="来源/用途")

class LevelStructure(str, Enum):
    """关卡结构类型"""
    WAVE_BASED = "wave_based"        # 波数制
    ENDLESS = "endless"              # 无尽模式
    STAGE_SELECT = "stage_select"    # 关卡选择
    LINEAR = "linear"                # 线性推进
    ROGUELIKE = "roguelike"          # Roguelike
    UNKNOWN = "unknown"

class MechanicsState(BaseModel):
    """机制状态"""
    damage_events: list[DamageEvent] = Field(default_factory=list)
    economy_events: list[EconomyEvent] = Field(default_factory=list)
    core_loop: Optional[str] = Field(
        default=None,
        description="核心循环描述 (如: 战斗→拾取→升级→下一关)"
    )
    level_structure: LevelStructure = Field(default=LevelStructure.UNKNOWN)
    identified_mechanics: list[str] = Field(
        default_factory=list,
        description="已识别的机制列表"
    )
    last_updated: datetime = Field(default_factory=datetime.now)
```

### 5. UIFlowGraph

UI 流程图状态。

```python
class UINode(BaseModel):
    """UI 节点 (屏幕)"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="屏幕名称")
    screen_type: str = Field(..., description="屏幕类型 (menu/gameplay/popup/etc)")
    first_seen_step: int
    screenshot_path: Optional[Path] = None
    description: Optional[str] = None

class UIEdge(BaseModel):
    """UI 边 (转换)"""
    from_node: str = Field(..., description="源节点 ID")
    to_node: str = Field(..., description="目标节点 ID")
    trigger: str = Field(..., description="触发动作描述")
    step: int = Field(..., description="首次观察到的步骤")

class UIFlowGraph(BaseModel):
    """UI 流程图"""
    nodes: list[UINode] = Field(default_factory=list)
    edges: list[UIEdge] = Field(default_factory=list)
    current_screen: Optional[str] = Field(
        default=None,
        description="当前屏幕节点 ID"
    )

    def add_node(self, node: UINode) -> None:
        """添加节点 (去重)"""
        if not any(n.name == node.name for n in self.nodes):
            self.nodes.append(node)

    def add_edge(self, edge: UIEdge) -> None:
        """添加边 (去重)"""
        if not any(
            e.from_node == edge.from_node and
            e.to_node == edge.to_node and
            e.trigger == edge.trigger
            for e in self.edges
        ):
            self.edges.append(edge)
```

### 6. ArtStyleState

美术风格分析状态。

```python
class Color(BaseModel):
    """颜色定义"""
    hex: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$", description="HEX 颜色值")
    name: Optional[str] = Field(default=None, description="颜色名称")
    percentage: float = Field(default=0, ge=0, le=100, description="占比百分比")

class EffectPattern(BaseModel):
    """特效模式"""
    name: str = Field(..., description="特效名称")
    description: str
    observed_at_steps: list[int] = Field(default_factory=list)

class ArtStyleState(BaseModel):
    """美术风格状态"""
    color_palette: list[Color] = Field(
        default_factory=list,
        max_length=10,
        description="主色板 (最多 10 色)"
    )
    style_tags: list[str] = Field(
        default_factory=list,
        description="风格标签 (如: pixel_art, hand_drawn, 3d_rendered)"
    )
    effect_patterns: list[EffectPattern] = Field(
        default_factory=list,
        description="特效模式"
    )
    ui_style: Optional[str] = Field(
        default=None,
        description="UI 风格描述"
    )
    character_style: Optional[str] = Field(
        default=None,
        description="角色风格描述"
    )
    reference_games: list[str] = Field(
        default_factory=list,
        description="参考游戏"
    )
    last_updated: datetime = Field(default_factory=datetime.now)
```

### 7. GeneratedDocument

生成的文档。

```python
class DocumentType(str, Enum):
    """文档类型"""
    GDD = "gdd"                    # 游戏策划案
    NUMERICAL = "numerical"        # 数值分析
    ART_REPORT = "art_report"      # 美术风格报告

class QAStatus(str, Enum):
    """QA 状态"""
    PENDING = "pending"            # 待审核
    PASSED = "passed"              # 通过
    FAILED = "failed"              # 未通过
    REVISED = "revised"            # 已修订

class QAFeedback(BaseModel):
    """QA 反馈"""
    timestamp: datetime = Field(default_factory=datetime.now)
    issues: list[str] = Field(default_factory=list, description="发现的问题")
    suggestions: list[str] = Field(default_factory=list, description="改进建议")
    missing_sections: list[str] = Field(default_factory=list, description="缺失章节")

class GeneratedDocument(BaseModel):
    """生成的文档"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    doc_type: DocumentType
    title: str
    content: str = Field(..., min_length=1)
    version: int = Field(default=1, ge=1)
    qa_status: QAStatus = Field(default=QAStatus.PENDING)
    qa_feedback: Optional[QAFeedback] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    file_path: Optional[Path] = None
```

## Validation Rules

### Session Validation

| Field | Rule | Error Message |
|-------|------|---------------|
| max_steps | 1 ≤ value ≤ 1000 | "Max steps must be between 1 and 1000" |
| window_region.width | > 0 | "Window width must be positive" |
| window_region.height | > 0 | "Window height must be positive" |
| video_segment_duration | 2.0 ≤ value ≤ 5.0 | "Video duration must be 2-5 seconds" |

### Coordinate Validation

| Field | Rule | Error Message |
|-------|------|---------------|
| x | 0 ≤ value ≤ 1000 | "X coordinate must be 0-1000" |
| y | 0 ≤ value ≤ 1000 | "Y coordinate must be 0-1000" |

### Color Validation

| Field | Rule | Error Message |
|-------|------|---------------|
| hex | matches `^#[0-9A-Fa-f]{6}$` | "Invalid hex color format" |
| percentage | 0 ≤ value ≤ 100 | "Percentage must be 0-100" |

## State Transitions

### PlaySession Status

```
PENDING ──► RUNNING ──► COMPLETED
    │           │
    │           ├──► PAUSED ──► RUNNING
    │           │
    │           └──► FAILED
    │
    └──► CANCELLED
```

### GeneratedDocument QA Status

```
PENDING ──► PASSED
    │
    └──► FAILED ──► REVISED ──► PENDING
```

## JSON Schema Export

所有 Pydantic 模型支持导出 JSON Schema：

```python
# 导出示例
schema = ActionCommand.model_json_schema()
with open("contracts/action-command.json", "w") as f:
    json.dump(schema, f, indent=2)
```

导出的 Schema 用于：
1. Contract testing - 验证 Agent 输出符合约定
2. 文档生成 - 自动生成 API 文档
3. 前端类型生成 - 未来 Web 界面开发
